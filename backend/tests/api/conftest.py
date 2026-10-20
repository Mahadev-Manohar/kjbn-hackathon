from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.persistence.database import engine

BACKEND_DIR = Path(__file__).resolve().parents[2]

# The fixed "today" for API tests, a Tuesday. Override per request with the X-Test-Clock header.
TODAY = "2026-10-20"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Build the schema from the real Alembic migrations, so they are tested too."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables(migrated_database):
    yield
    with engine.begin() as connection:
        names = connection.execute(
            text(
                "SELECT string_agg(quote_ident(tablename), ',') FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).scalar()
        connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False, headers={"X-Test-Clock": TODAY}) as c:
        yield c


class Api:
    """Small helpers that build data through the public API, like a real client would."""

    def __init__(self, client: TestClient):
        self.client = client

    def post(self, path: str, body: dict, expected: int = 201, **kwargs):
        response = self.client.post(f"/api/v1{path}", json=body, **kwargs)
        assert response.status_code == expected, response.text
        return response.json()

    def farmer(self, name: str = "Arun Kumar", phone: str = "9000000001") -> dict:
        return self.post("/farmers", {"name": name, "phone": phone, "village": "Greenfield"})

    def crop(self, name: str = "Maize", threshold="14", maximum="25", grades=("A", "B", "C")):
        return self.post(
            "/crops",
            {
                "name": name,
                "base_moisture_threshold": threshold,
                "max_moisture_accepted": maximum,
                "grades": list(grades),
            },
        )

    def price(self, crop_id: int, grade: str, price: str, effective_from: str) -> dict:
        return self.post(
            "/price-list",
            {
                "crop_id": crop_id,
                "grade": grade,
                "price_per_kg": price,
                "effective_from": effective_from,
            },
        )

    def advance(self, farmer_id: int, amount: str, given_on: str = "2026-09-01") -> dict:
        return self.post(f"/farmers/{farmer_id}/advances", {"amount": amount, "given_on": given_on})

    def delivery_body(self, farmer_id, crop_id, **overrides) -> dict:
        body = {
            "farmer_id": farmer_id,
            "crop_id": crop_id,
            "grade": "A",
            "gross_kg": "100",
            "moisture": "14",
            "delivered_on": "2026-10-19",
        }
        return {**body, **overrides}

    def delivery(self, farmer_id, crop_id, expected: int = 201, **overrides):
        return self.post(
            "/deliveries", self.delivery_body(farmer_id, crop_id, **overrides), expected=expected
        )

    def generate_payout(self, farmer_id: int, week_start: str = "2026-10-19", expected: int = 201):
        return self.post(
            "/payouts", {"farmer_id": farmer_id, "week_start": week_start}, expected=expected
        )

    def action(self, path: str, expected: int = 200, **kwargs):
        response = self.client.post(f"/api/v1{path}", **kwargs)
        assert response.status_code == expected, response.text
        return response.json()


@pytest.fixture
def api(client) -> Api:
    return Api(client)


@pytest.fixture
def world(api):
    """A farmer, Maize (threshold 14, max 25) and a Rs 24.00/kg grade-A price from January."""
    farmer = api.farmer()
    crop = api.crop()
    api.price(crop["id"], "A", "24.00", "2026-01-01")
    api.price(crop["id"], "B", "22.00", "2026-01-01")
    return {"farmer": farmer, "crop": crop}
