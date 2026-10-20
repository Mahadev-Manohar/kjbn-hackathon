from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

D = Decimal
WEEK = "2026-10-19"  # Monday; "today" in API tests is Tuesday 2026-10-20


def ledger(api, farmer_id):
    return api.client.get(f"/api/v1/farmers/{farmer_id}/ledger").json()


def test_payout_statement_shows_every_line_and_the_arithmetic(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "1500.00")
    api.delivery(farmer_id, crop_id, gross_kg="100", moisture="14", delivered_on="2026-10-19")
    api.delivery(farmer_id, crop_id, gross_kg="50", moisture="16", delivered_on="2026-10-20")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-12")  # previous week: excluded

    payout = api.generate_payout(farmer_id)
    assert payout["status"] == "Draft"
    assert payout["week_start"] == WEEK and payout["week_end"] == "2026-10-25"
    assert [line["delivered_on"] for line in payout["deliveries"]] == ["2026-10-19", "2026-10-20"]
    assert payout["gross_amount"] == "3576.00"  # 2400.00 + 1176.00
    assert payout["recovery_cap"] == "1072.80"  # 30% of gross
    assert payout["outstanding_before"] == "1500.00"
    assert payout["advance_deduction"] == "1072.80"  # lesser of 1500.00 and 1072.80
    assert payout["net_amount"] == "2503.20"
    assert payout["outstanding_after"] == "427.20"
    line_total = sum(D(line["amount"]) for line in payout["deliveries"])
    assert line_total == D(payout["gross_amount"])
    assert D(payout["gross_amount"]) - D(payout["advance_deduction"]) == D(payout["net_amount"])


def test_advance_is_reduced_only_when_the_payout_is_finalised(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "1500.00")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    assert ledger(api, farmer_id)["outstanding_advance"] == "1500.00"  # Draft changes nothing

    finalised = api.action(f"/payouts/{payout['id']}/finalise")
    assert finalised["status"] == "Finalised" and finalised["finalised_at"]
    assert finalised["advance_deduction"] == "720.00"
    assert ledger(api, farmer_id)["outstanding_advance"] == "780.00"

    paid = api.action(f"/payouts/{payout['id']}/mark-paid")
    assert paid["status"] == "Paid" and paid["paid_at"]
    assert (
        ledger(api, farmer_id)["outstanding_advance"] == "780.00"
    )  # paying does not recover again


def test_advance_larger_than_30_percent_is_recovered_over_several_payouts(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "5000.00")
    expected_outstanding = ["4280.00", "3560.00", "2840.00"]
    for week, day, outstanding in zip(
        ("2026-10-05", "2026-10-12", "2026-10-19"),
        ("2026-10-05", "2026-10-12", "2026-10-19"),
        expected_outstanding,
        strict=True,
    ):
        api.delivery(farmer_id, crop_id, delivered_on=day)  # 100 kg x 24 = 2400
        payout = api.generate_payout(farmer_id, week)
        finalised = api.action(f"/payouts/{payout['id']}/finalise")
        assert finalised["advance_deduction"] == "720.00"
        assert ledger(api, farmer_id)["outstanding_advance"] == outstanding


def test_last_payout_recovers_only_what_is_still_owed(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "100.00")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    finalised = api.action(f"/payouts/{payout['id']}/finalise")
    assert finalised["advance_deduction"] == "100.00"
    assert ledger(api, farmer_id)["outstanding_advance"] == "0.00"


def test_two_drafts_cannot_over_recover_one_advance(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "1000.00")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-12")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    older = api.generate_payout(farmer_id, "2026-10-12")
    newer = api.generate_payout(farmer_id, "2026-10-19")
    assert older["advance_deduction"] == newer["advance_deduction"] == "720.00"  # both see 1000

    api.action(f"/payouts/{older['id']}/finalise")
    refreshed = api.client.get(f"/api/v1/payouts/{newer['id']}").json()
    assert refreshed["outstanding_before"] == "280.00"
    assert refreshed["advance_deduction"] == "280.00"
    finalised = api.action(f"/payouts/{newer['id']}/finalise")
    assert finalised["advance_deduction"] == "280.00"
    assert ledger(api, farmer_id)["outstanding_advance"] == "0.00"


def test_week_with_no_deliveries_is_rejected(api, world):
    response = api.client.post(
        "/api/v1/payouts", json={"farmer_id": world["farmer"]["id"], "week_start": WEEK}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_deliveries_in_week"
    assert api.client.get("/api/v1/payouts").json()["total"] == 0


def test_payout_week_must_start_on_a_monday_that_has_begun(api, world):
    farmer_id = world["farmer"]["id"]
    tuesday = api.client.post(
        "/api/v1/payouts", json={"farmer_id": farmer_id, "week_start": "2026-10-20"}
    )
    future = api.client.post(
        "/api/v1/payouts", json={"farmer_id": farmer_id, "week_start": "2026-10-26"}
    )
    assert tuesday.json()["error"]["code"] == "week_start_not_monday"
    assert future.json()["error"]["code"] == "week_in_future"
    missing = api.client.post("/api/v1/payouts", json={"farmer_id": 999, "week_start": WEEK})
    assert missing.status_code == 404


def test_regenerating_a_draft_refreshes_it_and_creates_no_duplicate(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    first = api.generate_payout(farmer_id)
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-20")  # arrives while Draft exists

    second = api.generate_payout(farmer_id, expected=200)
    assert second["id"] == first["id"]
    assert len(second["deliveries"]) == 2
    assert second["gross_amount"] == "4800.00"
    assert api.client.get("/api/v1/payouts").json()["total"] == 1


def test_editing_a_draft_delivery_updates_the_draft_totals(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    api.client.put(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"grade": "A", "gross_kg": "200", "moisture": "14", "delivered_on": "2026-10-19"},
    )
    refreshed = api.client.get(f"/api/v1/payouts/{payout['id']}").json()
    assert refreshed["gross_amount"] == "4800.00"


def test_finalise_and_mark_paid_enforce_the_lifecycle(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    path = f"/api/v1/payouts/{payout['id']}"

    early_pay = api.client.post(f"{path}/mark-paid")
    assert early_pay.status_code == 409
    assert early_pay.json()["error"]["code"] == "invalid_payout_transition"

    api.action(f"/payouts/{payout['id']}/finalise")
    assert api.client.post(f"{path}/finalise").status_code == 409
    regenerate = api.client.post(
        "/api/v1/payouts", json={"farmer_id": farmer_id, "week_start": WEEK}
    )
    assert regenerate.status_code == 409
    assert regenerate.json()["error"]["code"] == "payout_immutable"

    api.action(f"/payouts/{payout['id']}/mark-paid")
    assert api.client.post(f"{path}/mark-paid").status_code == 409
    assert api.client.post("/api/v1/payouts/9999/finalise").status_code == 404


def test_finalised_payout_is_immutable_for_its_deliveries(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    api.action(f"/payouts/{payout['id']}/finalise")

    edit = api.client.put(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"grade": "A", "gross_kg": "1", "moisture": "14", "delivered_on": "2026-10-19"},
    )
    assert edit.status_code == 422 and edit.json()["error"]["code"] == "delivery_locked"

    late = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(farmer_id, crop_id, delivered_on="2026-10-20"),
    )
    assert late.status_code == 422 and late.json()["error"]["code"] == "week_already_finalised"
    unchanged = api.client.get(f"/api/v1/payouts/{payout['id']}").json()
    assert unchanged["gross_amount"] == "2400.00"


def test_credit_note_lands_in_the_next_payout(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    api.action(f"/payouts/{payout['id']}/finalise")

    note = api.post(
        f"/deliveries/{delivery['id']}/notes",
        {"kind": "CREDIT_NOTE", "amount": "120.50", "reason": "Weighbridge re-check"},
    )
    assert note["kind"] == "CREDIT_NOTE" and note["amount"] == "120.50"
    assert note["references_delivery_id"] == delivery["id"]
    assert note["delivered_on"] == "2026-10-26"  # the current week is finalised, so next Monday
    assert note["payout_id"] is None

    early = api.client.post(
        "/api/v1/payouts", json={"farmer_id": farmer_id, "week_start": "2026-10-26"}
    )
    assert early.json()["error"]["code"] == "week_in_future"

    later = api.post(
        "/payouts",
        {"farmer_id": farmer_id, "week_start": "2026-10-26"},
        headers={"X-Test-Clock": "2026-10-27"},
    )
    assert later["gross_amount"] == "120.50"
    assert [line["kind"] for line in later["deliveries"]] == ["CREDIT_NOTE"]
    assert api.client.get(f"/api/v1/payouts/{payout['id']}").json()["gross_amount"] == "2400.00"


def test_debit_note_is_deducted_in_the_next_payout(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    api.action(f"/payouts/{api.generate_payout(farmer_id)['id']}/finalise")
    api.post(
        f"/deliveries/{delivery['id']}/notes",
        {"kind": "DEBIT_NOTE", "amount": "100.00", "reason": "Overpaid weight"},
    )
    payout = api.post(
        "/payouts",
        {"farmer_id": farmer_id, "week_start": "2026-10-26"},
        headers={"X-Test-Clock": "2026-10-27"},
    )
    assert payout["gross_amount"] == "-100.00"
    assert payout["advance_deduction"] == "0.00"
    assert payout["net_amount"] == "-100.00"


def test_note_rules_are_enforced(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    url = f"/api/v1/deliveries/{delivery['id']}/notes"
    valid = {"kind": "CREDIT_NOTE", "amount": "10.00", "reason": "Correction"}

    not_finalised = api.client.post(url, json=valid)
    assert not_finalised.status_code == 422
    assert not_finalised.json()["error"]["code"] == "note_target_not_finalised"

    api.action(f"/payouts/{api.generate_payout(farmer_id)['id']}/finalise")
    for bad in (
        {**valid, "amount": "0"},
        {**valid, "amount": "-5"},
        {**valid, "amount": "1.005"},
        {**valid, "kind": "DELIVERY"},
        {**valid, "kind": "REFUND"},
        {**valid, "reason": ""},
        {**valid, "reason": "x" * 501},
    ):
        response = api.client.post(url, json=bad)
        assert response.status_code == 422, (bad, response.text)

    note = api.post(f"/deliveries/{delivery['id']}/notes", valid)
    on_note = api.client.post(f"/api/v1/deliveries/{note['id']}/notes", json=valid)
    assert on_note.status_code == 422
    assert on_note.json()["error"]["code"] == "note_target_invalid"
    assert api.client.post("/api/v1/deliveries/9999/notes", json=valid).status_code == 404


def test_advance_rules(api, world):
    farmer_id = world["farmer"]["id"]
    url = f"/api/v1/farmers/{farmer_id}/advances"
    for bad in (
        {"amount": "0", "given_on": "2026-10-01"},
        {"amount": "-10", "given_on": "2026-10-01"},
        {"amount": "10.001", "given_on": "2026-10-01"},
        {"amount": "abc", "given_on": "2026-10-01"},
        {"amount": "99999999999", "given_on": "2026-10-01"},
        {"amount": "10", "given_on": "tomorrow"},
    ):
        assert api.client.post(url, json=bad).status_code == 422, bad
    future = api.client.post(url, json={"amount": "10", "given_on": "2026-10-21"})
    assert future.json()["error"]["code"] == "advance_in_future"
    assert (
        api.client.post(
            "/api/v1/farmers/999/advances", json={"amount": "1", "given_on": "2026-10-01"}
        ).status_code
        == 404
    )

    api.advance(farmer_id, "500.00")
    api.advance(farmer_id, "250.50", "2026-10-05")
    summary = ledger(api, farmer_id)
    assert summary["total_advances"] == "750.50"
    assert summary["outstanding_advance"] == "750.50"
    assert len(summary["advances"]) == 2


def test_ledger_lists_deliveries_advances_payouts_and_outstanding(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "1000.00")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    api.action(f"/payouts/{payout['id']}/finalise")

    summary = ledger(api, farmer_id)
    assert summary["farmer"]["id"] == farmer_id
    assert summary["total_recovered"] == "720.00"
    assert summary["outstanding_advance"] == "280.00"
    assert summary["deliveries"][0]["payout_status"] == "Finalised"
    assert summary["payouts"][0]["status"] == "Finalised"
    assert api.client.get("/api/v1/farmers/999/ledger").status_code == 404


def test_concurrent_finalise_recovers_the_advance_exactly_once(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "1000.00")
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)

    def finalise(_):
        with TestClient(app, headers={"X-Test-Clock": "2026-10-20"}) as client:
            return client.post(f"/api/v1/payouts/{payout['id']}/finalise").status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(finalise, range(8)))
    assert sorted(statuses) == [200] + [409] * 7
    assert ledger(api, farmer_id)["total_recovered"] == "720.00"


def test_concurrent_payout_generation_creates_one_payout(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")

    def generate(_):
        with TestClient(app, headers={"X-Test-Clock": "2026-10-20"}) as client:
            return client.post(
                "/api/v1/payouts", json={"farmer_id": farmer_id, "week_start": WEEK}
            ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(generate, range(8)))
    assert set(statuses) <= {200, 201}
    assert api.client.get("/api/v1/payouts").json()["total"] == 1


def test_concurrent_deliveries_and_finalise_never_orphan_a_delivery(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)

    def act(index):
        with TestClient(app, headers={"X-Test-Clock": "2026-10-20"}) as client:
            if index == 0:
                return client.post(f"/api/v1/payouts/{payout['id']}/finalise").status_code
            return client.post(
                "/api/v1/deliveries",
                json=api.delivery_body(farmer_id, crop_id, delivered_on="2026-10-20"),
            ).status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(act, range(6)))
    assert statuses[0] == 200
    assert set(statuses[1:]) <= {201, 422}  # 422 = arrived after the week was finalised

    final = api.client.get(f"/api/v1/payouts/{payout['id']}").json()
    saved = api.client.get("/api/v1/deliveries", params={"limit": 50}).json()["items"]
    same_week = [d for d in saved if d["delivered_on"] >= WEEK]
    # every delivery in the week is either on the finalised payout, or was never saved
    assert all(d["payout_id"] == payout["id"] for d in same_week)
    assert D(final["gross_amount"]) == sum(D(d["amount"]) for d in same_week)


def test_ledger_caps_each_list_but_keeps_balances_exact(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    for day in range(1, 6):
        api.advance(farmer_id, "100.00", f"2026-09-0{day}")
    for day in ("2026-10-12", "2026-10-13", "2026-10-14"):
        api.delivery(farmer_id, crop_id, delivered_on=day)

    summary = api.client.get(f"/api/v1/farmers/{farmer_id}/ledger", params={"limit": 2}).json()
    assert summary["limit"] == 2
    assert (summary["deliveries_total"], summary["advances_total"]) == (3, 5)
    assert len(summary["deliveries"]) == 2 and len(summary["advances"]) == 2
    assert summary["deliveries"][0]["delivered_on"] == "2026-10-14"  # newest first
    assert summary["total_advances"] == summary["outstanding_advance"] == "500.00"  # not capped

    assert (
        api.client.get(f"/api/v1/farmers/{farmer_id}/ledger", params={"limit": 0}).status_code
        == 422
    )
    assert (
        api.client.get(f"/api/v1/farmers/{farmer_id}/ledger", params={"limit": 201}).status_code
        == 422
    )


def test_advances_list_is_paginated(api, world):
    farmer_id = world["farmer"]["id"]
    for day in range(1, 4):
        api.advance(farmer_id, f"{day}0.00", f"2026-09-0{day}")
    page = api.client.get(
        f"/api/v1/farmers/{farmer_id}/advances", params={"limit": 2, "offset": 2}
    ).json()
    assert page["total"] == 3 and [a["amount"] for a in page["items"]] == ["10.00"]
    assert api.client.get("/api/v1/farmers/999/advances").status_code == 404
