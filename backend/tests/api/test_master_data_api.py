def test_farmer_crud_search_and_pagination(api):
    for index, (name, village) in enumerate(
        [("Arun Kumar", "Greenfield"), ("Meena Devi", "Riverbend"), ("Ravi Selvan", "Hillview")]
    ):
        api.post("/farmers", {"name": name, "phone": f"900000000{index}", "village": village})
    page = api.client.get("/api/v1/farmers", params={"limit": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 2
    found = api.client.get("/api/v1/farmers", params={"q": "river"}).json()
    assert [f["name"] for f in found["items"]] == ["Meena Devi"]

    farmer_id = page["items"][0]["id"]
    updated = api.client.patch(f"/api/v1/farmers/{farmer_id}", json={"village": "Newtown"})
    assert updated.status_code == 200 and updated.json()["village"] == "Newtown"
    assert api.client.get("/api/v1/farmers/999").status_code == 404
    assert api.client.patch("/api/v1/farmers/999", json={"village": "x"}).status_code == 404


def test_farmer_validation(api):
    good = {"name": "Arun", "phone": "9000000001", "village": "Greenfield"}
    for bad in (
        {**good, "name": ""},
        {**good, "name": "   "},
        {**good, "name": "x" * 151},
        {**good, "phone": "12345"},
        {**good, "phone": "phone-number"},
        {**good, "village": None},
        {**good, "role": "admin"},
        {"name": "Arun"},
    ):
        assert api.client.post("/api/v1/farmers", json=bad).status_code == 422, bad
    created = api.client.post("/api/v1/farmers", json={**good, "name": "  Arun  "})
    assert created.status_code == 201 and created.json()["name"] == "Arun"


def test_sql_metacharacters_are_stored_as_text_not_executed(api):
    name = "Robert'); DROP TABLE farmers;--"
    created = api.post("/farmers", {"name": name, "phone": "9000000001", "village": "Greenfield"})
    assert api.client.get(f"/api/v1/farmers/{created['id']}").json()["name"] == name
    assert api.client.get("/api/v1/farmers", params={"q": "'; --"}).status_code == 200


def test_crop_creation_and_limits(api):
    crop = api.crop("Groundnut", threshold="10", maximum="20", grades=("A", "B", "A"))
    assert crop["grades"] == ["A", "B"]  # duplicates collapsed
    assert api.client.get(f"/api/v1/crops/{crop['id']}").json()["name"] == "Groundnut"
    assert len(api.client.get("/api/v1/crops").json()) == 1

    duplicate = api.client.post(
        "/api/v1/crops",
        json={
            "name": "groundnut",
            "base_moisture_threshold": "10",
            "max_moisture_accepted": "20",
            "grades": ["A"],
        },
    )
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "crop_exists"

    inverted = api.client.post(
        "/api/v1/crops",
        json={
            "name": "Rice",
            "base_moisture_threshold": "20",
            "max_moisture_accepted": "10",
            "grades": ["A"],
        },
    )
    assert inverted.status_code == 422

    raised = api.client.patch(f"/api/v1/crops/{crop['id']}", json={"max_moisture_accepted": "22"})
    assert raised.status_code == 200 and raised.json()["max_moisture_accepted"] == "22.00"
    too_low = api.client.patch(f"/api/v1/crops/{crop['id']}", json={"max_moisture_accepted": "9"})
    assert too_low.status_code == 422

    grade = api.client.post(f"/api/v1/crops/{crop['id']}/grades", json={"grade": "C"})
    assert grade.status_code == 201 and grade.json()["grades"] == ["A", "B", "C"]
    again = api.client.post(f"/api/v1/crops/{crop['id']}/grades", json={"grade": "C"})
    assert again.status_code == 409
    assert api.client.get("/api/v1/crops/999").status_code == 404


def test_crop_limit_change_does_not_alter_existing_deliveries(api, world):
    delivery = api.delivery(
        world["farmer"]["id"], world["crop"]["id"], moisture="17.6", gross_kg="100"
    )
    api.client.patch(f"/api/v1/crops/{world['crop']['id']}", json={"base_moisture_threshold": "16"})
    stored = api.client.get(f"/api/v1/deliveries/{delivery['id']}").json()
    assert stored["deduction_pct"] == "3.00" and stored["amount"] == "2328.00"


def test_price_history_is_append_only_and_ordered(api, world):
    crop_id = world["crop"]["id"]
    api.price(crop_id, "A", "25.00", "2026-06-01")
    api.price(crop_id, "A", "26.00", "2026-03-01")  # back-dated entry slots into history

    history = api.client.get("/api/v1/price-list", params={"crop_id": crop_id, "grade": "A"}).json()
    assert [(p["effective_from"], p["price_per_kg"]) for p in history["items"]] == [
        ("2026-06-01", "25.00"),
        ("2026-03-01", "26.00"),
        ("2026-01-01", "24.00"),
    ]
    # never overwritten: no update or delete routes exist
    entry_id = history["items"][0]["id"]
    assert api.client.put(f"/api/v1/price-list/{entry_id}", json={}).status_code == 405 or (
        api.client.put(f"/api/v1/price-list/{entry_id}", json={}).status_code == 404
    )
    assert api.client.delete(f"/api/v1/price-list/{entry_id}").status_code in (404, 405)


def test_duplicate_price_date_is_rejected_not_overwritten(api, world):
    crop_id = world["crop"]["id"]
    response = api.client.post(
        "/api/v1/price-list",
        json={
            "crop_id": crop_id,
            "grade": "A",
            "price_per_kg": "99.00",
            "effective_from": "2026-01-01",
        },
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "price_exists"
    prices = api.client.get("/api/v1/price-list", params={"crop_id": crop_id, "grade": "A"}).json()
    assert [p["price_per_kg"] for p in prices["items"]] == ["24.00"]


def test_price_validation(api, world):
    crop_id = world["crop"]["id"]
    good = {"crop_id": crop_id, "grade": "A", "price_per_kg": "30", "effective_from": "2026-05-01"}
    for bad in (
        {**good, "price_per_kg": "0"},
        {**good, "price_per_kg": "-1"},
        {**good, "price_per_kg": "1.005"},
        {**good, "price_per_kg": "1e9"},
        {**good, "price_per_kg": "NaN"},
        {**good, "effective_from": "soon"},
        {**good, "grade": "Z"},
    ):
        assert api.client.post("/api/v1/price-list", json=bad).status_code == 422, bad
    assert api.client.post("/api/v1/price-list", json={**good, "crop_id": 999}).status_code == 404
