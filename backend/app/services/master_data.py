"""Farmers, crops, price list and advances: simple records with a few guarded rules."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.clock import Clock
from app.domain.errors import ConflictError, InvalidInputError, RuleViolationError
from app.persistence import queries
from app.persistence.models import Advance, Crop, CropGrade, Farmer, PriceListEntry
from app.services import payouts

logger = logging.getLogger("app.services.master_data")


def create_farmer(session: Session, **fields) -> Farmer:
    farmer = Farmer(**fields)
    session.add(farmer)
    session.commit()
    logger.info("farmer_created", extra={"farmer_id": farmer.id})
    return farmer


def update_farmer(session: Session, farmer_id: int, **fields) -> Farmer:
    farmer = queries.lock_farmer(session, farmer_id)
    for name, value in fields.items():
        setattr(farmer, name, value)
    session.commit()
    logger.info("farmer_updated", extra={"farmer_id": farmer_id})
    return farmer


def list_farmers(session: Session, search: str | None, limit: int, offset: int):
    query = select(Farmer)
    if search:
        pattern = f"%{search}%"
        query = query.where(Farmer.name.ilike(pattern) | Farmer.village.ilike(pattern))
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(query.order_by(Farmer.name, Farmer.id).limit(limit).offset(offset))
    return list(items), total


def create_crop(
    session: Session, name: str, threshold: Decimal, max_moisture: Decimal, grades: list[str]
) -> Crop:
    _require_moisture_limits(threshold, max_moisture)
    if session.scalar(select(Crop.id).where(func.lower(Crop.name) == name.lower())):
        raise ConflictError(f"Crop '{name}' already exists", code="crop_exists", crop=name)
    crop = Crop(name=name, base_moisture_threshold=threshold, max_moisture_accepted=max_moisture)
    crop.grades = [CropGrade(grade=grade) for grade in grades]
    session.add(crop)
    session.commit()
    logger.info("crop_created", extra={"crop_id": crop.id})
    return queries.get_crop(session, crop.id)


def update_crop_limits(
    session: Session, crop_id: int, threshold: Decimal | None, max_moisture: Decimal | None
) -> Crop:
    crop = queries.get_crop(session, crop_id)
    new_threshold = crop.base_moisture_threshold if threshold is None else threshold
    new_max = crop.max_moisture_accepted if max_moisture is None else max_moisture
    _require_moisture_limits(new_threshold, new_max)
    # Existing deliveries keep their frozen breakdown, so this only affects new deliveries.
    crop.base_moisture_threshold = new_threshold
    crop.max_moisture_accepted = new_max
    session.commit()
    logger.info("crop_limits_updated", extra={"crop_id": crop_id})
    return crop


def add_crop_grade(session: Session, crop_id: int, grade: str) -> Crop:
    crop = queries.get_crop(session, crop_id)
    if grade in {existing.grade for existing in crop.grades}:
        raise ConflictError(
            f"Grade '{grade}' already exists for {crop.name}", code="grade_exists", crop_id=crop_id
        )
    session.add(CropGrade(crop_id=crop_id, grade=grade))
    session.commit()
    return queries.get_crop(session, crop_id)


def list_crops(session: Session) -> list[Crop]:
    return list(
        session.scalars(select(Crop).options(selectinload(Crop.grades)).order_by(Crop.name))
    )


def _require_moisture_limits(threshold: Decimal, max_moisture: Decimal) -> None:
    if max_moisture <= threshold:
        raise InvalidInputError(
            "max_moisture_accepted must be greater than base_moisture_threshold",
            field="max_moisture_accepted",
        )


def add_price(
    session: Session, crop_id: int, grade: str, price: Decimal, effective_from: date
) -> PriceListEntry:
    """Append a price. Entries are never overwritten; back-dating is allowed because every
    delivery froze the price it used (rule 3)."""
    crop = queries.get_crop(session, crop_id)
    if grade not in {existing.grade for existing in crop.grades}:
        raise InvalidInputError(
            f"Grade '{grade}' is not allowed for {crop.name}", field="grade", crop_id=crop_id
        )
    duplicate = session.scalar(
        select(PriceListEntry.id).where(
            PriceListEntry.crop_id == crop_id,
            PriceListEntry.grade == grade,
            PriceListEntry.effective_from == effective_from,
        )
    )
    if duplicate:
        raise ConflictError(
            f"A price for {crop.name} grade {grade} effective {effective_from.isoformat()} "
            "already exists; add a new entry with a different effective date",
            code="price_exists",
            crop_id=crop_id,
            grade=grade,
        )
    entry = PriceListEntry(
        crop_id=crop_id, grade=grade, price_per_kg=price, effective_from=effective_from
    )
    session.add(entry)
    session.commit()
    logger.info(
        "price_added",
        extra={"crop_id": crop_id, "grade": grade, "price_entry_id": entry.id},
    )
    return entry


def list_prices(session: Session, crop_id: int | None, grade: str | None, limit: int, offset: int):
    query = select(PriceListEntry)
    if crop_id is not None:
        query = query.where(PriceListEntry.crop_id == crop_id)
    if grade is not None:
        query = query.where(PriceListEntry.grade == grade)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(
        query.order_by(
            PriceListEntry.crop_id,
            PriceListEntry.grade,
            PriceListEntry.effective_from.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(items), total


def record_advance(
    session: Session, farmer_id: int, amount: Decimal, given_on: date, clock: Clock
) -> Advance:
    queries.lock_farmer(session, farmer_id)
    if given_on > clock.today:
        raise RuleViolationError(
            f"Advance date {given_on.isoformat()} is in the future",
            code="advance_in_future",
            farmer_id=farmer_id,
        )
    advance = Advance(farmer_id=farmer_id, amount=amount, given_on=given_on)
    session.add(advance)
    session.flush()
    payouts.refresh_draft_payouts(session, farmer_id)
    session.commit()
    logger.info("advance_recorded", extra={"farmer_id": farmer_id, "advance_id": advance.id})
    return advance
