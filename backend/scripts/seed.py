"""Load realistic, invented sample data. Safe to run repeatedly.

Reference data (farmers, crops, grades, prices, advances) is inserted only where missing.
Demo activity (deliveries, payouts, a correction note) is created through the same services
the API uses, so every figure obeys the business rules, and only when no deliveries exist yet.

Run from the backend directory:
    python -m scripts.seed
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.clock import Clock
from app.domain.delivery_rules import DeliveryRequest
from app.persistence.database import SessionLocal
from app.persistence.models import (
    Advance,
    Crop,
    CropGrade,
    Delivery,
    Farmer,
    PriceListEntry,
)
from app.services import deliveries, payouts

logger = logging.getLogger("scripts.seed")

# Demo activity is created "as of" this instant so the rules (no future dates, week started)
# hold no matter when the seed runs.
SEED_NOW = Clock(datetime(2026, 10, 20, 4, 30, tzinfo=UTC))  # 10:00 IST, Tuesday

# All names, phone numbers and bank references are invented.
FARMERS = [
    ("Arun Kumar", "9000000001", "Greenfield", "SEED-BANK-001"),
    ("Meena Devi", "9000000002", "Riverbend", "SEED-BANK-002"),
    ("Ravi Selvan", "9000000003", "Hillview", "SEED-BANK-003"),
    ("Lakshmi Narayanan", "9000000004", "Greenfield", "SEED-BANK-004"),
    ("Kavitha Raj", "9000000005", "Lakeside", "SEED-BANK-005"),
]

# name, moisture threshold %, maximum accepted moisture %
CROPS = [
    ("Maize", Decimal("14.00"), Decimal("25.00")),
    ("Turmeric", Decimal("12.00"), Decimal("22.00")),
    ("Groundnut", Decimal("10.00"), Decimal("20.00")),
]
GRADES = ("A", "B", "C")

# Illustrative seed prices, not official market prices: (crop, grade, price per kg, from).
PRICES = [
    *(
        (crop, grade, Decimal(price), date(2026, 1, 1))
        for crop, by_grade in {
            "Maize": {"A": "24.00", "B": "22.00", "C": "20.00"},
            "Turmeric": {"A": "120.00", "B": "110.00", "C": "100.00"},
            "Groundnut": {"A": "65.00", "B": "60.00", "C": "55.00"},
        }.items()
        for grade, price in by_grade.items()
    ),
    # Later revisions: the old entries stay, so history is visible and old deliveries keep theirs.
    ("Maize", "A", Decimal("25.50"), date(2026, 10, 5)),
    ("Turmeric", "A", Decimal("125.00"), date(2026, 10, 1)),
]

# phone, amount, given on. Arun's is large so the 30%-of-gross cap applies for several weeks;
# Meena's is small so the "lesser of" rule recovers it in one payout.
ADVANCES = [
    ("9000000001", Decimal("25000.00"), date(2026, 9, 1)),
    ("9000000002", Decimal("800.00"), date(2026, 9, 5)),
    ("9000000003", Decimal("2000.00"), date(2026, 9, 20)),
]

# phone, crop, grade, gross kg, moisture %, delivered on. Moisture cases: at threshold, just
# below the next whole point (14.99), whole-point deductions (15.00, 17.60, 12.50 vs 10).
DELIVERIES = [
    ("9000000001", "Maize", "A", "450.000", "14.00", date(2026, 9, 29)),
    ("9000000001", "Maize", "A", "320.500", "16.20", date(2026, 9, 30)),
    ("9000000001", "Maize", "A", "500.000", "15.00", date(2026, 10, 6)),
    ("9000000001", "Maize", "B", "280.000", "14.99", date(2026, 10, 8)),
    ("9000000001", "Maize", "A", "610.250", "17.60", date(2026, 10, 13)),
    ("9000000002", "Turmeric", "A", "80.000", "12.00", date(2026, 9, 30)),
    ("9000000002", "Turmeric", "A", "95.500", "13.40", date(2026, 10, 7)),
    ("9000000002", "Turmeric", "B", "60.000", "12.80", date(2026, 10, 14)),
    ("9000000003", "Groundnut", "A", "150.000", "12.50", date(2026, 10, 9)),
    ("9000000003", "Groundnut", "C", "200.000", "10.00", date(2026, 10, 15)),
]

# phone, week start (Monday), how far to take the payout: draft, finalised or paid.
PAYOUTS = [
    ("9000000001", date(2026, 9, 28), "paid"),
    ("9000000002", date(2026, 9, 28), "paid"),
    ("9000000001", date(2026, 10, 5), "finalised"),
    ("9000000002", date(2026, 10, 5), "finalised"),
    ("9000000001", date(2026, 10, 12), "draft"),
    ("9000000002", date(2026, 10, 12), "draft"),
]


def _get_or_create(session: Session, model, lookup: dict, values: dict):
    row = session.scalar(select(model).filter_by(**lookup))
    if row is None:
        row = model(**lookup, **values)
        session.add(row)
        session.flush()
    return row


def seed_reference_data(session: Session) -> None:
    farmers = {}
    for name, phone, village, bank in FARMERS:
        farmers[phone] = _get_or_create(
            session,
            Farmer,
            {"phone": phone},
            {"name": name, "village": village, "bank_reference": bank},
        )

    crops = {}
    for name, threshold, maximum in CROPS:
        crop = _get_or_create(
            session,
            Crop,
            {"name": name},
            {"base_moisture_threshold": threshold, "max_moisture_accepted": maximum},
        )
        crops[name] = crop
        for grade in GRADES:
            _get_or_create(session, CropGrade, {"crop_id": crop.id, "grade": grade}, {})

    for crop_name, grade, price, effective_from in PRICES:
        _get_or_create(
            session,
            PriceListEntry,
            {"crop_id": crops[crop_name].id, "grade": grade, "effective_from": effective_from},
            {"price_per_kg": price},
        )

    for phone, amount, given_on in ADVANCES:
        farmer = farmers[phone]
        exists = session.scalar(
            select(Advance.id).where(
                Advance.farmer_id == farmer.id,
                Advance.amount == amount,
                Advance.given_on == given_on,
            )
        )
        if exists is None:
            session.add(Advance(farmer_id=farmer.id, amount=amount, given_on=given_on))
    session.commit()


def seed_demo_activity(session: Session) -> bool:
    """Create deliveries, payouts and a note. Returns False if activity already exists."""
    if session.scalar(select(func.count()).select_from(Delivery)):
        return False

    farmer_ids = {f.phone: f.id for f in session.scalars(select(Farmer))}
    crop_ids = {c.name: c.id for c in session.scalars(select(Crop))}

    first_delivery = None
    for phone, crop, grade, gross_kg, moisture, delivered_on in DELIVERIES:
        request = DeliveryRequest(grade, Decimal(gross_kg), Decimal(moisture), delivered_on)
        created = deliveries.create_delivery(
            session, farmer_ids[phone], crop_ids[crop], request, SEED_NOW
        )
        first_delivery = first_delivery or created

    for phone, week_start, stage in PAYOUTS:
        payout = payouts.generate_payout(session, farmer_ids[phone], week_start, SEED_NOW)
        if stage in ("finalised", "paid"):
            payout = payouts.finalise_payout(session, payout.id, SEED_NOW)
        if stage == "paid":
            payouts.mark_paid(session, payout.id, SEED_NOW)

    # A correction to a delivery in an already-finalised payout, as the rules require.
    deliveries.create_note(
        session,
        first_delivery.id,
        "CREDIT_NOTE",
        Decimal("125.00"),
        "Weighbridge re-check found 5 kg more",
        SEED_NOW,
    )
    return True


def seed() -> None:
    with SessionLocal() as session:
        seed_reference_data(session)
        created = seed_demo_activity(session)
    logger.info("seed_complete", extra={"demo_activity_created": created})


if __name__ == "__main__":
    from app.core.logging import configure_logging

    configure_logging("INFO")
    seed()
