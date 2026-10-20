from decimal import Decimal

D = Decimal


def test_create_delivery_returns_full_breakdown(api, world):
    delivery = api.delivery(
        world["farmer"]["id"], world["crop"]["id"], gross_kg="100", moisture="17.6"
    )
    assert delivery["kind"] == "DELIVERY"
    assert delivery["crop_name"] == "Maize"
    assert delivery["deduction_pct"] == "3.00"
    assert delivery["deduction_kg"] == "3.000"
    assert delivery["net_kg"] == "97.000"
    assert delivery["applied_price"] == "24.00"
    assert delivery["amount"] == "2328.00"
    assert delivery["price_list_entry_id"] is not None
    assert delivery["payout_id"] is None


def test_breakdown_parts_add_up_across_awkward_weights(api, world):
    delivery = api.delivery(
        world["farmer"]["id"], world["crop"]["id"], gross_kg="33.333", moisture="16.5"
    )
    assert D(delivery["deduction_kg"]) + D(delivery["net_kg"]) == D(delivery["gross_kg"])
    assert D(delivery["net_kg"]) * D(delivery["applied_price"]) == D(delivery["amount"]) or (
        abs(D(delivery["net_kg"]) * D(delivery["applied_price"]) - D(delivery["amount"]))
        <= D("0.005")
    )


def test_preview_matches_saved_delivery_and_saves_nothing(api, world):
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"], moisture="16.2")
    preview = api.post("/deliveries/preview", body, expected=200)
    assert api.client.get("/api/v1/deliveries").json()["total"] == 0

    saved = api.post("/deliveries", body)
    for field in ("deduction_pct", "deduction_kg", "net_kg", "applied_price", "amount"):
        assert preview[field] == saved[field]
    assert preview["moisture_threshold"] == "14.00"


def test_moisture_exactly_at_threshold_has_no_deduction(api, world):
    delivery = api.delivery(world["farmer"]["id"], world["crop"]["id"], moisture="14")
    assert delivery["deduction_pct"] == "0.00"


def test_moisture_just_below_next_percent_point_is_not_deducted(api, world):
    crop = api.crop("Turmeric", threshold="14", maximum="22", grades=("A",))
    api.price(crop["id"], "A", "100.00", "2026-01-01")
    delivery = api.delivery(world["farmer"]["id"], crop["id"], moisture="14.99")
    assert delivery["deduction_pct"] == "0.00"


def test_delivery_on_exact_effective_date_uses_new_price(api, world):
    api.price(world["crop"]["id"], "A", "26.00", "2026-10-10")
    on_day = api.delivery(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-10")
    day_before = api.delivery(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-09")
    assert on_day["applied_price"] == "26.00"
    assert day_before["applied_price"] == "24.00"


def test_back_dated_price_does_not_change_existing_deliveries(api, world):
    delivery = api.delivery(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-12")
    api.price(world["crop"]["id"], "A", "30.00", "2026-10-01")  # back-dated, applies retroactively

    stored = api.client.get(f"/api/v1/deliveries/{delivery['id']}").json()
    assert stored["applied_price"] == "24.00"
    assert stored["amount"] == delivery["amount"]
    assert stored["price_list_entry_id"] == delivery["price_list_entry_id"]

    later = api.delivery(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-12")
    assert later["applied_price"] == "30.00"


def test_missing_price_names_the_combination(api, world):
    response = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], grade="C"),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "price_not_found"
    assert "Maize" in error["message"] and "grade C" in error["message"]


def test_delivery_before_first_price_is_rejected(api, world):
    response = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(
            world["farmer"]["id"], world["crop"]["id"], delivered_on="2025-12-31"
        ),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "price_not_found"


def test_moisture_above_crop_maximum_is_rejected(api, world):
    response = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], moisture="25.01"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "moisture_above_maximum"
    assert api.client.get("/api/v1/deliveries").json()["total"] == 0


def test_future_delivery_is_rejected_against_the_request_clock(api, world):
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-21")
    response = api.client.post("/api/v1/deliveries", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "delivery_in_future"

    # Moving the reviewer clock forward makes the same request valid.
    accepted = api.client.post(
        "/api/v1/deliveries", json=body, headers={"X-Test-Clock": "2026-10-21T09:00:00+05:30"}
    )
    assert accepted.status_code == 201


def test_grade_not_allowed_for_crop_is_rejected(api, world):
    response = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], grade="Z"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_unknown_farmer_and_crop_return_404(api, world):
    missing_farmer = api.client.post(
        "/api/v1/deliveries", json=api.delivery_body(999, world["crop"]["id"])
    )
    missing_crop = api.client.post(
        "/api/v1/deliveries", json=api.delivery_body(world["farmer"]["id"], 999)
    )
    assert missing_farmer.status_code == 404
    assert missing_crop.status_code == 404
    assert missing_farmer.json()["error"]["code"] == "not_found"


def test_malformed_input_is_a_422_never_a_500(api, world):
    path = "/api/v1/deliveries"
    base = api.delivery_body(world["farmer"]["id"], world["crop"]["id"])
    bad_bodies = [
        {**base, "gross_kg": "abc"},
        {**base, "gross_kg": None},
        {**base, "gross_kg": -5},
        {**base, "gross_kg": 0},
        {**base, "gross_kg": "NaN"},
        {**base, "gross_kg": "Infinity"},
        {**base, "gross_kg": 1e30},
        {**base, "gross_kg": "10.0001"},
        {**base, "moisture": 0},
        {**base, "moisture": "-1"},
        {**base, "moisture": 101},
        {**base, "moisture": "14.123"},
        {**base, "moisture": True},
        {**base, "delivered_on": "20-10-2026"},
        {**base, "delivered_on": "2026-13-45"},
        {**base, "grade": ""},
        {**base, "grade": "A; DROP TABLE farmers"},
        {**base, "farmer_id": "x"},
        {**base, "farmer_id": 10**30},
        {**base, "unexpected": 1},
    ]
    for body in bad_bodies:
        response = api.client.post(path, json=body)
        assert response.status_code in (404, 422), (body, response.status_code, response.text)
        assert "error" in response.json()

    for raw in ("not json", "[]", "null", ""):
        response = api.client.post(path, content=raw, headers={"Content-Type": "application/json"})
        assert response.status_code == 422, raw
    assert api.client.get("/api/v1/deliveries").json()["total"] == 0


def test_error_response_shape_is_consistent(api, world):
    validation = api.client.post("/api/v1/deliveries", json={})
    domain = api.client.post(
        "/api/v1/deliveries",
        json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], moisture="30"),
    )
    not_found = api.client.get("/api/v1/deliveries/12345")
    unknown_route = api.client.get("/api/v1/nope")
    for response in (validation, domain, not_found, unknown_route):
        error = response.json()["error"]
        assert set(error) == {"code", "message", "details", "request_id"}
        assert error["request_id"] == response.headers["X-Request-ID"]
    assert validation.json()["error"]["code"] == "validation_error"
    assert validation.json()["error"]["details"]["fields"]


def test_request_id_header_is_echoed_when_supplied(api):
    response = api.client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"


def test_list_deliveries_filters_and_paginates(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    for day in ("2026-10-12", "2026-10-13", "2026-10-14"):
        api.delivery(farmer_id, crop_id, delivered_on=day)
    page = api.client.get("/api/v1/deliveries", params={"limit": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 2 and page["limit"] == 2
    assert page["items"][0]["delivered_on"] == "2026-10-14"  # newest first

    filtered = api.client.get(
        "/api/v1/deliveries", params={"date_from": "2026-10-13", "date_to": "2026-10-13"}
    ).json()
    assert filtered["total"] == 1

    assert api.client.get("/api/v1/deliveries", params={"limit": 1000}).status_code == 422
    assert api.client.get("/api/v1/deliveries", params={"offset": -1}).status_code == 422


def test_editing_a_delivery_refreezes_the_breakdown(api, world):
    delivery = api.delivery(world["farmer"]["id"], world["crop"]["id"], moisture="14")
    response = api.client.put(
        f"/api/v1/deliveries/{delivery['id']}",
        json={"grade": "B", "gross_kg": "200", "moisture": "16", "delivered_on": "2026-10-19"},
    )
    assert response.status_code == 200
    edited = response.json()
    assert (edited["grade"], edited["applied_price"], edited["deduction_pct"]) == (
        "B",
        "22.00",
        "2.00",
    )
    assert edited["amount"] == "4312.00"  # 196 kg x 22


def test_json_numbers_are_read_exactly_not_through_binary_floats(api, world):
    # 33.333 and 16.5 sent as JSON numbers (not strings) must be stored exactly
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"])
    body.update({"gross_kg": 33.333, "moisture": 16.5})
    delivery = api.post("/deliveries", body)
    assert delivery["gross_kg"] == "33.333" and delivery["moisture"] == "16.50"
    assert delivery["deduction_kg"] == "0.667" and delivery["net_kg"] == "32.666"
    assert delivery["amount"] == "783.98"  # 32.666 x 24.00 = 783.984
