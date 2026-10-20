from decimal import Decimal

from scripts.seed import seed


def payouts_by_farmer_week(client):
    items = client.get("/api/v1/payouts", params={"limit": 100}).json()["items"]
    return {(p["farmer_name"], p["week_start"]): p for p in items}


def test_seed_creates_rule_consistent_demo_data(client):
    seed()

    payouts = payouts_by_farmer_week(client)
    assert len(payouts) == 6
    paid = payouts[("Arun Kumar", "2026-09-28")]
    # 450 kg @ 24.00 + (320.5 kg - 2%) @ 24.00 = 10800.00 + 7538.16
    assert paid["status"] == "Paid" and paid["gross_amount"] == "18338.16"
    assert paid["recovery_cap"] == paid["advance_deduction"] == "5501.45"  # 30% of gross
    assert payouts[("Meena Devi", "2026-09-28")]["advance_deduction"] == "800.00"  # lesser of
    assert payouts[("Arun Kumar", "2026-10-05")]["status"] == "Finalised"
    assert payouts[("Arun Kumar", "2026-10-12")]["status"] == "Draft"
    assert not any(farmer == "Ravi Selvan" for farmer, _ in payouts)  # left for reviewers

    for payout in payouts.values():
        statement = client.get(f"/api/v1/payouts/{payout['id']}").json()
        lines = sum(Decimal(line["amount"]) for line in statement["deliveries"])
        assert lines == Decimal(statement["gross_amount"])
        net = Decimal(statement["gross_amount"]) - Decimal(statement["advance_deduction"])
        assert net == Decimal(statement["net_amount"])


def test_seed_includes_price_history_and_a_correction_note(client):
    seed()
    maize_a = client.get("/api/v1/price-list", params={"crop_id": 1, "grade": "A"}).json()["items"]
    assert [p["price_per_kg"] for p in maize_a] == ["25.50", "24.00"]  # history kept, newest first

    arun = client.get("/api/v1/farmers/1/ledger").json()
    notes = [d for d in arun["deliveries"] if d["kind"] == "CREDIT_NOTE"]
    assert len(notes) == 1 and notes[0]["references_delivery_id"] is not None
    # outstanding advance reflects only Finalised/Paid recoveries (rule 5)
    assert Decimal(arun["outstanding_advance"]) == Decimal("25000.00") - Decimal(
        arun["total_recovered"]
    )


def test_seed_is_idempotent(client):
    seed()
    before = client.get("/api/v1/deliveries", params={"limit": 200}).json()["total"]
    farmers_before = client.get("/api/v1/farmers").json()["total"]
    seed()
    assert client.get("/api/v1/deliveries", params={"limit": 200}).json()["total"] == before
    assert client.get("/api/v1/farmers").json()["total"] == farmers_before
    assert len(payouts_by_farmer_week(client)) == 6
