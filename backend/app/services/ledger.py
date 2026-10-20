"""Farmer ledger: balances plus the most recent deliveries, advances and payouts.

The balances are always exact (computed over all rows). Each list is capped at `limit` newest
entries with its full count alongside; the paginated list endpoints give the rest.
"""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.payout_rules import outstanding_advance
from app.persistence import queries
from app.persistence.models import Advance, Delivery, Farmer, Payout


@dataclass(frozen=True)
class FarmerLedger:
    farmer: Farmer
    total_advances: Decimal
    total_recovered: Decimal
    outstanding_advance: Decimal
    limit: int
    deliveries_total: int
    advances_total: int
    payouts_total: int
    deliveries: list[Delivery]
    advances: list[Advance]
    payouts: list[Payout]


def _count(session: Session, model, farmer_id: int) -> int:
    return session.scalar(select(func.count()).where(model.farmer_id == farmer_id))


def list_advances(session: Session, farmer_id: int, limit: int, offset: int):
    queries.get_farmer(session, farmer_id)
    items = session.scalars(
        select(Advance)
        .where(Advance.farmer_id == farmer_id)
        .order_by(Advance.given_on.desc(), Advance.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(items), _count(session, Advance, farmer_id)


def farmer_ledger(session: Session, farmer_id: int, limit: int) -> FarmerLedger:
    farmer = queries.get_farmer(session, farmer_id)
    total = queries.total_advances(session, farmer_id)
    recovered = queries.recovered_advances(session, farmer_id)
    deliveries = session.scalars(
        queries.delivery_query()
        .where(Delivery.farmer_id == farmer_id)
        .order_by(Delivery.delivered_on.desc(), Delivery.id.desc())
        .limit(limit)
    )
    advances, advances_total = list_advances(session, farmer_id, limit, 0)
    payouts = session.scalars(
        select(Payout)
        .where(Payout.farmer_id == farmer_id)
        .options(joinedload(Payout.farmer))
        .order_by(Payout.week_start.desc())
        .limit(limit)
    )
    return FarmerLedger(
        farmer=farmer,
        total_advances=total,
        total_recovered=recovered,
        outstanding_advance=outstanding_advance(total, recovered),
        limit=limit,
        deliveries_total=_count(session, Delivery, farmer_id),
        advances_total=advances_total,
        payouts_total=_count(session, Payout, farmer_id),
        deliveries=list(deliveries.unique()),
        advances=advances,
        payouts=list(payouts),
    )
