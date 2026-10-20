"""Reviewers hit the API with hostile input; every such request must be a 4xx, never a 5xx."""

import itertools

import pytest

NASTY_STRINGS = [
    "",
    " ",
    "\u0000",
    "a\u0000b",
    "😀" * 10,
    "x" * 10_000,
    "'; DROP TABLE farmers; --",
    "<script>alert(1)</script>",
    "%",
    "\\",
    "../../etc/passwd",
]
NASTY_NUMBERS = [
    0,
    -1,
    1.5,
    10**18,
    10**40,
    -(10**40),
    1e308,
    "1e999",
    "NaN",
    "-Infinity",
    "0x10",
    True,
    None,
    [],
    {},
]
NASTY_DATES = [
    "0001-01-01",
    "0000-00-00",
    "9999-12-31",
    "10000-01-01",
    "2026-02-30",
    "2026-10-19T10:00:00",
    "1",
    None,
    [],
]
NASTY_IDS = ["0", "-1", "abc", "99999999999999999999999", "1.5", "%00", "1;2"]


def not_5xx(response, context):
    assert response.status_code < 500, (context, response.status_code, response.text[:300])
    assert response.headers["content-type"].startswith("application/json"), context


@pytest.fixture
def seeded(api, world):
    farmer_id, crop_id = world["farmer"]["id"], world["crop"]["id"]
    api.advance(farmer_id, "500.00")
    delivery = api.delivery(farmer_id, crop_id, delivered_on="2026-10-19")
    payout = api.generate_payout(farmer_id)
    return {
        "farmer": farmer_id,
        "crop": crop_id,
        "delivery": delivery["id"],
        "payout": payout["id"],
    }


def test_nasty_path_ids_never_crash(client, seeded):
    paths = [
        "/farmers/{}",
        "/farmers/{}/ledger",
        "/farmers/{}/advances",
        "/crops/{}",
        "/deliveries/{}",
        "/payouts/{}",
    ]
    for path, bad in itertools.product(paths, NASTY_IDS):
        not_5xx(client.get(f"/api/v1{path.format(bad)}"), (path, bad))
    for path, bad in itertools.product(
        ["/payouts/{}/finalise", "/payouts/{}/mark-paid", "/deliveries/{}/notes"], NASTY_IDS
    ):
        not_5xx(client.post(f"/api/v1{path.format(bad)}", json={}), (path, bad))
    not_5xx(client.put("/api/v1/deliveries/99999999999999999999", json={}), "put huge id")


def test_nasty_query_parameters_never_crash(client, seeded):
    for key, bad in itertools.product(
        [
            "limit",
            "offset",
            "farmer_id",
            "crop_id",
            "date_from",
            "date_to",
            "week_start",
            "status",
            "q",
            "grade",
        ],
        NASTY_STRINGS + ["99999999999999999999", "-5", "9999-12-31", "0001-01-01"],
    ):
        for path in ("/farmers", "/deliveries", "/payouts", "/price-list"):
            not_5xx(client.get(f"/api/v1{path}", params={key: bad}), (path, key, bad))


def test_nasty_farmer_and_crop_bodies_never_crash(client, seeded):
    for bad in NASTY_STRINGS:
        base = {"name": "A", "phone": "9000000009", "village": "V", "bank_reference": "b"}
        for field in ("name", "phone", "village", "bank_reference"):
            body = {**base, field: bad}
            not_5xx(client.post("/api/v1/farmers", json=body), ("farmer", field, bad))
            not_5xx(
                client.patch(f"/api/v1/farmers/{seeded['farmer']}", json={field: bad}),
                ("patch", field),
            )
        crop = {
            "name": bad,
            "base_moisture_threshold": "10",
            "max_moisture_accepted": "20",
            "grades": [bad],
        }
        not_5xx(client.post("/api/v1/crops", json=crop), ("crop", bad))
        not_5xx(
            client.post(f"/api/v1/crops/{seeded['crop']}/grades", json={"grade": bad}),
            ("grade", bad),
        )
    for bad in NASTY_NUMBERS:
        crop = {
            "name": "C",
            "base_moisture_threshold": bad,
            "max_moisture_accepted": bad,
            "grades": ["A"],
        }
        not_5xx(client.post("/api/v1/crops", json=crop), ("crop numbers", bad))
        not_5xx(
            client.patch(f"/api/v1/crops/{seeded['crop']}", json={"max_moisture_accepted": bad}),
            bad,
        )


def test_nasty_price_advance_delivery_and_payout_bodies_never_crash(client, seeded):
    farmer, crop = seeded["farmer"], seeded["crop"]
    for bad in NASTY_NUMBERS + NASTY_STRINGS:
        not_5xx(
            client.post(
                "/api/v1/price-list",
                json={
                    "crop_id": crop,
                    "grade": "A",
                    "price_per_kg": bad,
                    "effective_from": "2026-05-01",
                },
            ),
            ("price", bad),
        )
        not_5xx(
            client.post(
                "/api/v1/price-list",
                json={
                    "crop_id": bad,
                    "grade": "A",
                    "price_per_kg": "1",
                    "effective_from": "2026-05-02",
                },
            ),
            ("price crop", bad),
        )
        not_5xx(
            client.post(
                "/api/v1/price-list",
                json={
                    "crop_id": crop,
                    "grade": bad,
                    "price_per_kg": "1",
                    "effective_from": "2026-05-03",
                },
            ),
            ("price grade", bad),
        )
        not_5xx(
            client.post(
                f"/api/v1/farmers/{farmer}/advances", json={"amount": bad, "given_on": "2026-10-01"}
            ),
            ("advance", bad),
        )
        delivery = {
            "farmer_id": farmer,
            "crop_id": crop,
            "grade": "A",
            "gross_kg": "10",
            "moisture": "14",
            "delivered_on": "2026-10-19",
        }
        for field in ("farmer_id", "crop_id", "grade", "gross_kg", "moisture"):
            not_5xx(
                client.post("/api/v1/deliveries", json={**delivery, field: bad}),
                ("delivery", field, bad),
            )
            not_5xx(
                client.post("/api/v1/deliveries/preview", json={**delivery, field: bad}),
                ("preview", field, bad),
            )
        not_5xx(
            client.post(
                f"/api/v1/deliveries/{seeded['delivery']}/notes",
                json={"kind": "CREDIT_NOTE", "amount": bad, "reason": "reason"},
            ),
            ("note", bad),
        )
        not_5xx(
            client.post(
                f"/api/v1/deliveries/{seeded['delivery']}/notes",
                json={"kind": "CREDIT_NOTE", "amount": "1", "reason": bad},
            ),
            ("note reason", bad),
        )
        not_5xx(
            client.put(
                f"/api/v1/deliveries/{seeded['delivery']}", json={**delivery, "gross_kg": bad}
            ),
            ("edit", bad),
        )
        not_5xx(
            client.post("/api/v1/payouts", json={"farmer_id": bad, "week_start": "2026-10-19"}),
            ("payout farmer", bad),
        )
    for bad in NASTY_DATES:
        not_5xx(
            client.post(
                "/api/v1/price-list",
                json={"crop_id": crop, "grade": "A", "price_per_kg": "1", "effective_from": bad},
            ),
            ("price date", bad),
        )
        not_5xx(
            client.post(
                f"/api/v1/farmers/{farmer}/advances", json={"amount": "1", "given_on": bad}
            ),
            ("advance date", bad),
        )
        delivery = {
            "farmer_id": farmer,
            "crop_id": crop,
            "grade": "A",
            "gross_kg": "10",
            "moisture": "14",
            "delivered_on": bad,
        }
        not_5xx(client.post("/api/v1/deliveries", json=delivery), ("delivery date", bad))
        not_5xx(client.post("/api/v1/deliveries/preview", json=delivery), ("preview date", bad))
        not_5xx(
            client.post("/api/v1/payouts", json={"farmer_id": farmer, "week_start": bad}),
            ("payout week", bad),
        )


def test_extreme_but_valid_dates_never_crash(client, seeded, api):
    farmer, crop = seeded["farmer"], seeded["crop"]
    clock = {"X-Test-Clock": "9999-12-31"}  # a far-future "today" exercises week arithmetic limits
    for day in ("0001-01-01", "0001-01-07", "9999-12-25", "9999-12-31"):
        not_5xx(
            client.post(
                "/api/v1/price-list",
                json={"crop_id": crop, "grade": "B", "price_per_kg": "1", "effective_from": day},
            ),
            ("extreme price date", day),
        )
        body = {
            "farmer_id": farmer,
            "crop_id": crop,
            "grade": "B",
            "gross_kg": "10",
            "moisture": "14",
            "delivered_on": day,
        }
        not_5xx(
            client.post("/api/v1/deliveries", json=body, headers=clock), ("extreme delivery", day)
        )
        not_5xx(
            client.post(
                "/api/v1/payouts", json={"farmer_id": farmer, "week_start": day}, headers=clock
            ),
            ("extreme week", day),
        )
        not_5xx(
            client.post(
                f"/api/v1/farmers/{farmer}/advances",
                json={"amount": "1", "given_on": day},
                headers=clock,
            ),
            ("extreme advance", day),
        )
    for raw in (
        "0001-01-01T00:00:00+14:00",
        "9999-12-31T23:59:59-12:00",
        "garbage",
        "",
        "2026-10-19T10:00",
    ):
        not_5xx(
            client.post(
                "/api/v1/deliveries/preview",
                json={
                    "farmer_id": farmer,
                    "crop_id": crop,
                    "grade": "A",
                    "gross_kg": "1",
                    "moisture": "14",
                    "delivered_on": "2026-10-19",
                },
                headers={"X-Test-Clock": raw},
            ),
            ("clock", raw),
        )
