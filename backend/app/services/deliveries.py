"""Delivery use cases: preview, create, edit and credit/debit notes."""

import logging
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain import note_rules
from app.domain.clock import Clock
from app.domain.delivery_rules import CropRules, DeliveryQuote, DeliveryRequest, quote_delivery
from app.domain.payout_rules import week_start
from app.persistence import queries
from app.persistence.models import Crop, Delivery, DeliveryKind
from app.services import payouts

logger = logging.getLogger("app.services.deliveries")


def _crop_rules(crop: Crop) -> CropRules:
    return CropRules(
        name=crop.name,
        allowed_grades=frozenset(grade.grade for grade in crop.grades),
        moisture_threshold=crop.base_moisture_threshold,
        max_moisture=crop.max_moisture_accepted,
    )


def _quote(session: Session, crop: Crop, request: DeliveryRequest, clock: Clock) -> DeliveryQuote:
    prices = queries.price_candidates(session, crop.id, request.grade)
    return quote_delivery(request, _crop_rules(crop), prices, clock.today)


def _frozen_fields(quote: DeliveryQuote) -> dict:
    """Breakdown columns stored on the delivery row (rule 3)."""
    return asdict(quote)


def _farmer_of(session: Session, delivery_id: int) -> int:
    """Find the farmer to lock before reading the delivery itself."""
    farmer_id = session.scalar(select(Delivery.farmer_id).where(Delivery.id == delivery_id))
    if farmer_id is None:
        queries.get_delivery(session, delivery_id)  # raises NotFoundError
    return farmer_id


def preview_delivery(
    session: Session,
    crop_id: int,
    request: DeliveryRequest,
    farmer_id: int | None,
    clock: Clock,
) -> tuple[Crop, DeliveryQuote]:
    """Same calculation as create, nothing saved."""
    crop = queries.get_crop(session, crop_id)
    quote = _quote(session, crop, request, clock)
    if farmer_id is not None:
        queries.get_farmer(session, farmer_id)
        note_rules.ensure_week_open_for_delivery(
            request.delivered_on, queries.frozen_week_starts(session, farmer_id)
        )
    return crop, quote


def create_delivery(
    session: Session, farmer_id: int, crop_id: int, request: DeliveryRequest, clock: Clock
) -> Delivery:
    queries.lock_farmer(session, farmer_id)
    crop = queries.get_crop(session, crop_id)
    quote = _quote(session, crop, request, clock)
    note_rules.ensure_week_open_for_delivery(
        request.delivered_on, queries.frozen_week_starts(session, farmer_id)
    )

    delivery = Delivery(
        farmer_id=farmer_id,
        crop_id=crop_id,
        grade=request.grade,
        kind=DeliveryKind.DELIVERY,
        delivered_on=request.delivered_on,
        **_frozen_fields(quote),
    )
    session.add(delivery)
    session.flush()
    payouts.refresh_draft_for_week(session, farmer_id, week_start(request.delivered_on))
    session.commit()
    logger.info(
        "delivery_created",
        extra={
            "farmer_id": farmer_id,
            "delivery_id": delivery.id,
            "crop_id": crop_id,
            "amount": str(quote.amount),
        },
    )
    return queries.get_delivery(session, delivery.id)


def update_delivery(
    session: Session, delivery_id: int, request: DeliveryRequest, clock: Clock
) -> Delivery:
    farmer_id = _farmer_of(session, delivery_id)
    queries.lock_farmer(session, farmer_id)
    delivery = queries.get_delivery(session, delivery_id)
    payout_status = delivery.payout.status.value if delivery.payout else None
    note_rules.ensure_delivery_editable(delivery.kind.value, payout_status)

    crop = queries.get_crop(session, delivery.crop_id)
    quote = _quote(session, crop, request, clock)
    old_week = week_start(delivery.delivered_on)
    new_week = week_start(request.delivered_on)
    if new_week != old_week:
        note_rules.ensure_week_open_for_delivery(
            request.delivered_on, queries.frozen_week_starts(session, farmer_id)
        )
        delivery.payout_id = None

    delivery.grade = request.grade
    delivery.delivered_on = request.delivered_on
    for name, value in _frozen_fields(quote).items():
        setattr(delivery, name, value)
    session.flush()
    payouts.refresh_draft_for_week(session, farmer_id, old_week)
    if new_week != old_week:
        payouts.refresh_draft_for_week(session, farmer_id, new_week)
    session.commit()
    logger.info("delivery_updated", extra={"farmer_id": farmer_id, "delivery_id": delivery_id})
    return queries.get_delivery(session, delivery_id)


def create_note(
    session: Session, delivery_id: int, kind: str, amount: Decimal, reason: str, clock: Clock
) -> Delivery:
    farmer_id = _farmer_of(session, delivery_id)
    queries.lock_farmer(session, farmer_id)
    original = queries.get_delivery(session, delivery_id)

    signed_amount = note_rules.signed_note_amount(kind, amount)
    note_rules.ensure_note_target(
        original.kind.value, original.payout.status.value if original.payout else None
    )
    booked_on = note_rules.note_effective_date(
        clock.today, queries.frozen_week_starts(session, farmer_id)
    )

    note = Delivery(
        farmer_id=farmer_id,
        crop_id=original.crop_id,
        grade=original.grade,
        kind=DeliveryKind(kind),
        amount=signed_amount,
        delivered_on=booked_on,
        references_delivery_id=original.id,
        reason=reason,
    )
    session.add(note)
    session.flush()
    payouts.refresh_draft_for_week(session, farmer_id, week_start(booked_on))
    session.commit()
    logger.info(
        "note_created",
        extra={
            "farmer_id": farmer_id,
            "delivery_id": note.id,
            "original_delivery_id": delivery_id,
            "kind": kind,
            "amount": str(signed_amount),
        },
    )
    return queries.get_delivery(session, note.id)


def list_deliveries(
    session: Session,
    farmer_id: int | None,
    crop_id: int | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
):
    query = queries.delivery_query()
    if farmer_id is not None:
        query = query.where(Delivery.farmer_id == farmer_id)
    if crop_id is not None:
        query = query.where(Delivery.crop_id == crop_id)
    if date_from is not None:
        query = query.where(Delivery.delivered_on >= date_from)
    if date_to is not None:
        query = query.where(Delivery.delivered_on <= date_to)
    total = session.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = session.scalars(
        query.order_by(Delivery.delivered_on.desc(), Delivery.id.desc()).limit(limit).offset(offset)
    )
    return list(items.unique()), total
