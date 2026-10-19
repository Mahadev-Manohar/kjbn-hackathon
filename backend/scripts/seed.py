"""Load deterministic development seed data.

Run from the backend directory with:
    python -m scripts.seed
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.persistence.database import SessionLocal
from app.persistence.models import Advance, Crop, CropGrade, Farmer, PriceListEntry

FARMERS = [
    {
        "name": "Arun Kumar",
        "phone": "9000000001",
        "village": "Greenfield",
        "bank_reference": "SEED-BANK-001",
    },
    {
        "name": "Meena Devi",
        "phone": "9000000002",
        "village": "Riverbend",
        "bank_reference": "SEED-BANK-002",
    },
    {
        "name": "Ravi Selvan",
        "phone": "9000000003",
        "village": "Hillview",
        "bank_reference": "SEED-BANK-003",
    },
]

CROPS = [
    {
        "name": "Maize",
        "base_moisture_threshold": Decimal("14.00"),
        "max_moisture_accepted": Decimal("25.00"),
    },
    {
        "name": "Turmeric",
        "base_moisture_threshold": Decimal("12.00"),
        "max_moisture_accepted": Decimal("22.00"),
    },
    {
        "name": "Groundnut",
        "base_moisture_threshold": Decimal("10.00"),
        "max_moisture_accepted": Decimal("20.00"),
    },
]

GRADES = ("A", "B", "C")
PRICE_EFFECTIVE_FROM = date(2026, 1, 1)

# Illustrative seed prices, not official market prices.
BASE_PRICES = {
    "Maize": {"A": "24.00", "B": "22.00", "C": "20.00"},
    "Turmeric": {"A": "120.00", "B": "110.00", "C": "100.00"},
    "Groundnut": {"A": "65.00", "B": "60.00", "C": "55.00"},
}

ADVANCES = [
    {"phone": "9000000001", "amount": Decimal("1500.00"), "given_on": date(2026, 9, 1)},
    {"phone": "9000000002", "amount": Decimal("800.00"), "given_on": date(2026, 9, 5)},
]


def seed() -> None:
    """Insert missing seed records without duplicating existing records."""
    with SessionLocal.begin() as session:
        farmers_by_phone = {}
        for data in FARMERS:
            farmer = session.scalar(
                select(Farmer).where(Farmer.phone == data["phone"])
            )
            if farmer is None:
                farmer = Farmer(**data)
                session.add(farmer)
                session.flush()
            farmers_by_phone[farmer.phone] = farmer

        crops_by_name = {}
        for data in CROPS:
            crop = session.scalar(select(Crop).where(Crop.name == data["name"]))
            if crop is None:
                crop = Crop(**data)
                session.add(crop)
                session.flush()
            crops_by_name[crop.name] = crop

        for _crop_name, crop in crops_by_name.items():
            for grade in GRADES:
                existing_grade = session.scalar(
                    select(CropGrade).where(
                        CropGrade.crop_id == crop.id,
                        CropGrade.grade == grade,
                    )
                )
                if existing_grade is None:
                    session.add(CropGrade(crop_id=crop.id, grade=grade))

        session.flush()

        for crop_name, prices in BASE_PRICES.items():
            crop = crops_by_name[crop_name]
            for grade, price in prices.items():
                existing_price = session.scalar(
                    select(PriceListEntry).where(
                        PriceListEntry.crop_id == crop.id,
                        PriceListEntry.grade == grade,
                        PriceListEntry.effective_from == PRICE_EFFECTIVE_FROM,
                    )
                )
                if existing_price is None:
                    session.add(
                        PriceListEntry(
                            crop_id=crop.id,
                            grade=grade,
                            price_per_kg=Decimal(price),
                            effective_from=PRICE_EFFECTIVE_FROM,
                        )
                    )

        for data in ADVANCES:
            farmer = farmers_by_phone[data["phone"]]
            existing_advance = session.scalar(
                select(Advance).where(
                    Advance.farmer_id == farmer.id,
                    Advance.amount == data["amount"],
                    Advance.given_on == data["given_on"],
                )
            )
            if existing_advance is None:
                session.add(
                    Advance(
                        farmer_id=farmer.id,
                        amount=data["amount"],
                        given_on=data["given_on"],
                    )
                )

    print("Seed data loaded successfully.")


if __name__ == "__main__":
    seed()
