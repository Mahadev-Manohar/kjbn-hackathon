from app.api.deps import get_session
from app.core.config import settings
from app.main import app


def edit(api, delivery_id, **changes):
    body = {"grade": "A", "gross_kg": "100", "moisture": "14", "delivered_on": "2026-10-19"}
    return api.client.put(f"/api/v1/deliveries/{delivery_id}", json={**body, **changes})


def test_moving_a_draft_delivery_to_another_week_updates_both_drafts(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-12")
    mover = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    older = api.generate_payout(farmer_id, "2026-10-12")
    newer = api.generate_payout(farmer_id, "2026-10-19")
    assert older["gross_amount"] == newer["gross_amount"] == "2400.00"

    assert edit(api, mover["id"], delivered_on="2026-10-13").status_code == 200
    older_after = api.client.get(f"/api/v1/payouts/{older['id']}").json()
    assert older_after["gross_amount"] == "4800.00"
    # the newer week lost its only delivery, so its Draft disappears instead of lingering empty
    assert api.client.get(f"/api/v1/payouts/{newer['id']}").status_code == 404


def test_delivery_cannot_be_moved_into_a_finalised_week(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.delivery(farmer_id, crop_id, delivered_on="2026-10-12")
    api.action(f"/payouts/{api.generate_payout(farmer_id, '2026-10-12')['id']}/finalise")
    mover = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")

    response = edit(api, mover["id"], delivered_on="2026-10-13")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "week_already_finalised"
    assert (
        api.client.get(f"/api/v1/deliveries/{mover['id']}").json()["delivered_on"] == "2026-10-19"
    )


def test_editing_into_a_future_date_or_bad_values_changes_nothing(api, world):
    delivery = api.delivery(world["farmer"]["id"], world["crop"]["id"])
    assert edit(api, delivery["id"], delivered_on="2026-10-21").status_code == 422
    assert edit(api, delivery["id"], moisture="26").status_code == 422
    assert edit(api, delivery["id"], grade="Z").status_code == 422
    assert edit(api, 9999).status_code == 404
    stored = api.client.get(f"/api/v1/deliveries/{delivery['id']}").json()
    assert stored["amount"] == delivery["amount"]


def test_payout_list_filters(api, world):
    crop_id = world["crop"]["id"]
    first = world["farmer"]["id"]
    second = api.farmer("Meena Devi", "9000000002")["id"]
    for farmer_id in (first, second):
        api.delivery(farmer_id, crop_id, delivered_on="2026-10-12")
        api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    api.action(f"/payouts/{api.generate_payout(first, '2026-10-12')['id']}/finalise")
    api.generate_payout(first)
    api.generate_payout(second)

    def total(**params):
        return api.client.get("/api/v1/payouts", params=params).json()["total"]

    assert total() == 3
    assert total(farmer_id=first) == 2
    assert total(status="Finalised") == 1
    assert total(status="Draft", farmer_id=second) == 1
    assert total(week_start="2026-10-19") == 2
    assert api.client.get("/api/v1/payouts", params={"status": "Bogus"}).status_code == 422


def test_delivery_list_crop_filter(api, world):
    farmer_id = world["farmer"]["id"]
    other = api.crop("Turmeric", threshold="12", maximum="22", grades=("A",))
    api.price(other["id"], "A", "100.00", "2026-01-01")
    api.delivery(farmer_id, world["crop"]["id"])
    api.delivery(farmer_id, other["id"])
    result = api.client.get("/api/v1/deliveries", params={"crop_id": other["id"]}).json()
    assert [d["crop_name"] for d in result["items"]] == ["Turmeric"]


def test_health_reports_503_when_the_database_is_down(client, caplog):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise ConnectionError("database down")

        def close(self):
            pass

    app.dependency_overrides[get_session] = lambda: BrokenSession()
    try:
        response = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert any(r.getMessage() == "health_check_failed" for r in caplog.records)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"


def test_test_clock_header_is_ignored_when_disabled(api, world, monkeypatch):
    monkeypatch.setattr(settings, "allow_test_clock", False)
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-19")
    response = api.client.post(
        "/api/v1/deliveries", json=body, headers={"X-Test-Clock": "2020-01-01"}
    )
    assert response.status_code == 201  # the 2020 override was not applied


def test_small_amounts_round_half_up_to_paise(api, world):
    # 0.001 kg at Rs 24.00 = 0.024 -> 0.02; 0.021 kg -> 0.504 -> 0.50; 0.023 -> 0.552 -> 0.55
    results = {
        gross: api.delivery(world["farmer"]["id"], world["crop"]["id"], gross_kg=gross)["amount"]
        for gross in ("0.001", "0.021", "0.023")
    }
    assert results == {"0.001": "0.02", "0.021": "0.50", "0.023": "0.55"}


def test_delivery_list_farmer_filter(api, world):
    crop_id = world["crop"]["id"]
    other = api.farmer("Meena Devi", "9000000002")
    api.delivery(world["farmer"]["id"], crop_id)
    api.delivery(other["id"], crop_id)
    result = api.client.get("/api/v1/deliveries", params={"farmer_id": other["id"]}).json()
    assert result["total"] == 1 and result["items"][0]["farmer_id"] == other["id"]
