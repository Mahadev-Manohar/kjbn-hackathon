"""Reusable database reads and the per-farmer lock. No business decisions live here."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.logging import bind_log_context
from app.domain.delivery_calculations import PriceCandidate
from app.domain.errors import NotFoundError
from app.domain.payout_rules import FROZEN_STATUSES, week_end
from app.persistence.models import (
    Advance,
    Crop,
    Delivery,
    Farmer,
    Payout,
    PayoutStatus,
    PriceListEntry,
)

FROZEN_PAYOUT_STATUSES = [PayoutStatus(status) for status in FROZEN_STATUSES]


def lock_farmer(session: Session, farmer_id: int) -> Farmer:
    """Serialise every money-affecting change for one farmer (SELECT ... FOR UPDATE).

    Delivery entry, notes, advances and payout generate/finalise all take this lock first, so
    a payout can never be finalised while a delivery for the same farmer is half-written.
    """
    farmer = session.scalar(select(Farmer).where(Farmer.id == farmer_id).with_for_update())
    if farmer is None:
        raise NotFoundError(f"Farmer {farmer_id} not found", farmer_id=farmer_id)
    bind_log_context(farmer_id=farmer_id)
    return farmer


def get_farmer(session: Session, farmer_id: int) -> Farmer:
    farmer = session.get(Farmer, farmer_id)
    if farmer is None:
        raise NotFoundError(f"Farmer {farmer_id} not found", farmer_id=farmer_id)
    bind_log_context(farmer_id=farmer_id)
    return farmer


def get_crop(session: Session, crop_id: int) -> Crop:
    crop = session.scalar(select(Crop).where(Crop.id == crop_id).options(selectinload(Crop.grades)))
    if crop is None:
        raise NotFoundError(f"Crop {crop_id} not found", crop_id=crop_id)
    bind_log_context(crop_id=crop_id)
    return crop


def price_candidates(session: Session, crop_id: int, grade: str) -> list[PriceCandidate]:
    rows = session.execute(
        select(PriceListEntry.id, PriceListEntry.effective_from, PriceListEntry.price_per_kg).where(
            PriceListEntry.crop_id == crop_id, PriceListEntry.grade == grade
        )
    )
    return [PriceCandidate(row.id, row.effective_from, row.price_per_kg) for row in rows]


def delivery_query():
    return select(Delivery).options(joinedload(Delivery.crop), joinedload(Delivery.payout))


def get_delivery(session: Session, delivery_id: int) -> Delivery:
    delivery = session.scalar(
        delivery_query().where(Delivery.id == delivery_id).execution_options(populate_existing=True)
    )
    if delivery is None:
        raise NotFoundError(f"Delivery {delivery_id} not found", delivery_id=delivery_id)
    bind_log_context(delivery_id=delivery_id, farmer_id=delivery.farmer_id)
    return delivery


def payout_query():
    return select(Payout).options(
        joinedload(Payout.farmer),
        selectinload(Payout.deliveries).joinedload(Delivery.crop),
    )


def get_payout(session: Session, payout_id: int) -> Payout:
    payout = session.scalar(
        payout_query().where(Payout.id == payout_id).execution_options(populate_existing=True)
    )
    if payout is None:
        raise NotFoundError(f"Payout {payout_id} not found", payout_id=payout_id)
    bind_log_context(payout_id=payout_id, farmer_id=payout.farmer_id)
    return payout


def find_payout(session: Session, farmer_id: int, week_start: date) -> Payout | None:
    return session.scalar(
        select(Payout).where(Payout.farmer_id == farmer_id, Payout.week_start == week_start)
    )


def frozen_week_starts(session: Session, farmer_id: int) -> set[date]:
    return set(
        session.scalars(
            select(Payout.week_start).where(
                Payout.farmer_id == farmer_id, Payout.status.in_(FROZEN_PAYOUT_STATUSES)
            )
        )
    )


def total_advances(session: Session, farmer_id: int) -> Decimal:
    return session.scalar(
        select(func.coalesce(func.sum(Advance.amount), 0)).where(Advance.farmer_id == farmer_id)
    )


def recovered_advances(session: Session, farmer_id: int) -> Decimal:
    """Advance recovered so far: deductions on Finalised and Paid payouts only (rule 5)."""
    return session.scalar(
        select(func.coalesce(func.sum(Payout.advance_deduction), 0)).where(
            Payout.farmer_id == farmer_id, Payout.status.in_(FROZEN_PAYOUT_STATUSES)
        )
    )


def unassigned_lines_in_week(session: Session, farmer_id: int, week_start: date) -> list[Delivery]:
    return list(
        session.scalars(
            select(Delivery).where(
                Delivery.farmer_id == farmer_id,
                Delivery.payout_id.is_(None),
                Delivery.delivered_on >= week_start,
                Delivery.delivered_on <= week_end(week_start),
            )
        )
    )
