"""Weekly payout use cases: generate, finalise, mark paid. Rules come from app.domain."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.domain import payout_rules
from app.domain.clock import Clock
from app.persistence import queries
from app.persistence.models import Delivery, Payout, PayoutStatus

logger = logging.getLogger("app.services.payouts")


def outstanding_for(session: Session, farmer_id: int) -> Decimal:
    return payout_rules.outstanding_advance(
        queries.total_advances(session, farmer_id), queries.recovered_advances(session, farmer_id)
    )


def sync_payout(session: Session, payout: Payout) -> int:
    """Attach the farmer's unassigned deliveries for the week, then recompute the totals.

    Returns the number of lines. Only called for Draft payouts (the callers check).
    """
    session.flush()
    for line in queries.unassigned_lines_in_week(session, payout.farmer_id, payout.week_start):
        line.payout_id = payout.id
    session.flush()
    amounts = list(session.scalars(select(Delivery.amount).where(Delivery.payout_id == payout.id)))
    outstanding = outstanding_for(session, payout.farmer_id)
    totals = payout_rules.compute_payout(amounts, outstanding)
    payout.outstanding_before = outstanding
    payout.gross_amount = totals.gross_amount
    payout.advance_deduction = totals.advance_deduction
    payout.net_amount = totals.net_amount
    return len(amounts)


def refresh_draft_for_week(session: Session, farmer_id: int, week_start: date) -> None:
    """Keep an existing Draft in step with delivery/note changes; drop it when it empties."""
    payout = queries.find_payout(session, farmer_id, week_start)
    if payout is None or payout.status != PayoutStatus.DRAFT:
        return
    if sync_payout(session, payout) == 0:
        session.execute(delete(Payout).where(Payout.id == payout.id))
        session.expunge(payout)


def refresh_draft_payouts(session: Session, farmer_id: int) -> None:
    weeks = session.scalars(
        select(Payout.week_start).where(
            Payout.farmer_id == farmer_id, Payout.status == PayoutStatus.DRAFT
        )
    ).all()
    for week_start in weeks:
        refresh_draft_for_week(session, farmer_id, week_start)


def generate_payout(session: Session, farmer_id: int, week_start: date, clock: Clock) -> Payout:
    """Create the Draft for a farmer-week, or refresh the existing Draft (idempotent)."""
    queries.lock_farmer(session, farmer_id)
    payout_rules.require_monday(week_start)
    payout_rules.require_week_started(week_start, clock.today)

    payout = queries.find_payout(session, farmer_id, week_start)
    if payout is not None:
        payout_rules.ensure_draft(payout.status.value)
    else:
        payout = Payout(farmer_id=farmer_id, week_start=week_start, status=PayoutStatus.DRAFT)
        session.add(payout)
    line_count = sync_payout(session, payout)
    payout_rules.require_has_lines(line_count, week_start)
    session.commit()
    logger.info(
        "payout_generated",
        extra={"farmer_id": farmer_id, "payout_id": payout.id, "week_start": str(week_start)},
    )
    return queries.get_payout(session, payout.id)


def finalise_payout(session: Session, payout_id: int, clock: Clock) -> Payout:
    farmer_id = _farmer_of(session, payout_id)
    queries.lock_farmer(session, farmer_id)
    payout = queries.get_payout(session, payout_id)
    payout_rules.ensure_can_finalise(payout.status.value)

    # Re-sync under the lock so late deliveries are not orphaned and the recovery uses the
    # outstanding advance as it stands now, not when the Draft was generated.
    line_count = sync_payout(session, payout)
    payout_rules.require_has_lines(line_count, payout.week_start)
    payout.status = PayoutStatus.FINALISED
    payout.finalised_at = clock.now
    session.flush()
    refresh_draft_payouts(session, farmer_id)
    session.commit()
    logger.info(
        "payout_finalised",
        extra={
            "farmer_id": farmer_id,
            "payout_id": payout_id,
            "advance_deduction": str(payout.advance_deduction),
        },
    )
    return queries.get_payout(session, payout_id)


def mark_paid(session: Session, payout_id: int, clock: Clock) -> Payout:
    farmer_id = _farmer_of(session, payout_id)
    queries.lock_farmer(session, farmer_id)
    payout = queries.get_payout(session, payout_id)
    payout_rules.ensure_can_mark_paid(payout.status.value)
    payout.status = PayoutStatus.PAID
    payout.paid_at = clock.now
    session.commit()
    logger.info("payout_paid", extra={"farmer_id": farmer_id, "payout_id": payout_id})
    return queries.get_payout(session, payout_id)


def list_payouts(
    session: Session,
    farmer_id: int | None,
    status: PayoutStatus | None,
    week_start: date | None,
    limit: int,
    offset: int,
):
    query = select(Payout)
    if farmer_id is not None:
        query = query.where(Payout.farmer_id == farmer_id)
    if status is not None:
        query = query.where(Payout.status == status)
    if week_start is not None:
        query = query.where(Payout.week_start == week_start)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    items = session.scalars(
        query.options(joinedload(Payout.farmer))
        .order_by(Payout.week_start.desc(), Payout.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(items), total


def _farmer_of(session: Session, payout_id: int) -> int:
    """Find the farmer to lock before reading the payout itself (avoids a lock-order race)."""
    farmer_id = session.scalar(select(Payout.farmer_id).where(Payout.id == payout_id))
    if farmer_id is None:
        queries.get_payout(session, payout_id)  # raises NotFoundError with the right message
    return farmer_id
