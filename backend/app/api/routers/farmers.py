from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, Limit, Offset, RequestClock
from app.api.schemas import (
    AdvanceIn,
    AdvanceOut,
    FarmerBase,
    FarmerIn,
    FarmerOut,
    FarmerUpdate,
    LedgerOut,
    Page,
)
from app.persistence import queries
from app.services import ledger, master_data

router = APIRouter(prefix="/farmers", tags=["farmers"])


def _with_outstanding(session, farmers) -> list[FarmerOut]:
    """Attach each farmer's derived outstanding advance (two grouped queries for the batch)."""
    outstanding = queries.outstanding_by_farmer(session, [farmer.id for farmer in farmers])
    return [
        FarmerOut(
            **FarmerBase.model_validate(farmer).model_dump(),
            outstanding_advance=outstanding[farmer.id],
        )
        for farmer in farmers
    ]


@router.post("", response_model=FarmerOut, status_code=status.HTTP_201_CREATED)
def create_farmer(body: FarmerIn, session: DbSession):
    return _with_outstanding(session, [master_data.create_farmer(session, **body.model_dump())])[0]


@router.get("", response_model=Page[FarmerOut])
def list_farmers(
    session: DbSession,
    limit: Limit = 50,
    offset: Offset = 0,
    q: Annotated[str | None, Query(max_length=100, description="Name or village contains")] = None,
):
    items, total = master_data.list_farmers(session, q, limit, offset)
    return Page(items=_with_outstanding(session, items), total=total, limit=limit, offset=offset)


@router.get("/{farmer_id}", response_model=FarmerOut)
def get_farmer(farmer_id: int, session: DbSession):
    return _with_outstanding(session, [queries.get_farmer(session, farmer_id)])[0]


@router.patch("/{farmer_id}", response_model=FarmerOut)
def update_farmer(farmer_id: int, body: FarmerUpdate, session: DbSession):
    farmer = master_data.update_farmer(session, farmer_id, **body.model_dump(exclude_unset=True))
    return _with_outstanding(session, [farmer])[0]


@router.post(
    "/{farmer_id}/advances", response_model=AdvanceOut, status_code=status.HTTP_201_CREATED
)
def record_advance(farmer_id: int, body: AdvanceIn, session: DbSession, clock: RequestClock):
    return master_data.record_advance(session, farmer_id, body.amount, body.given_on, clock)


@router.get("/{farmer_id}/advances", response_model=Page[AdvanceOut])
def list_advances(farmer_id: int, session: DbSession, limit: Limit = 50, offset: Offset = 0):
    items, total = ledger.list_advances(session, farmer_id, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{farmer_id}/ledger", response_model=LedgerOut)
def get_ledger(farmer_id: int, session: DbSession, limit: Limit = 50):
    """Exact balances plus the newest `limit` deliveries, advances and payouts.

    Page through the rest with GET /deliveries, /payouts (filter by farmer_id) and
    GET /farmers/{id}/advances.
    """
    return ledger.farmer_ledger(session, farmer_id, limit)
