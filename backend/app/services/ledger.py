"""Farmer ledger: every delivery, advance and payout plus the derived outstanding advance."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
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
    deliveries: list[Delivery]
    advances: list[Advance]
    payouts: list[Payout]


def farmer_ledger(session: Session, farmer_id: int) -> FarmerLedger:
    farmer = queries.get_farmer(session, farmer_id)
    total = queries.total_advances(session, farmer_id)
    recovered = queries.recovered_advances(session, farmer_id)
    deliveries = session.scalars(
        queries.delivery_query()
        .where(Delivery.farmer_id == farmer_id)
        .order_by(Delivery.delivered_on.desc(), Delivery.id.desc())
    )
    advances = session.scalars(
        select(Advance)
        .where(Advance.farmer_id == farmer_id)
        .order_by(Advance.given_on.desc(), Advance.id.desc())
    )
    payouts = session.scalars(
        select(Payout)
        .where(Payout.farmer_id == farmer_id)
        .options(joinedload(Payout.farmer))
        .order_by(Payout.week_start.desc())
    )
    return FarmerLedger(
        farmer=farmer,
        total_advances=total,
        total_recovered=recovered,
        outstanding_advance=outstanding_advance(total, recovered),
        deliveries=list(deliveries.unique()),
        advances=list(advances),
        payouts=list(payouts),
    )
