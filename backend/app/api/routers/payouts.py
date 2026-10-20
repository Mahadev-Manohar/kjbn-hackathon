from datetime import date

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession, Limit, Offset, RequestClock
from app.api.schemas import Page, PayoutGenerateIn, PayoutOut, PayoutStatementOut
from app.persistence import queries
from app.persistence.models import PayoutStatus
from app.services import payouts

router = APIRouter(prefix="/payouts", tags=["payouts"])


def _statement(payout) -> PayoutStatementOut:
    statement = PayoutStatementOut.model_validate(payout)
    statement.deliveries.sort(key=lambda line: (line.delivered_on, line.id))
    return statement


@router.post("", response_model=PayoutStatementOut, status_code=status.HTTP_201_CREATED)
def generate_payout(
    body: PayoutGenerateIn, session: DbSession, clock: RequestClock, response: Response
):
    """Create the Draft payout for a farmer and Monday, or refresh the existing Draft."""
    existed = queries.find_payout(session, body.farmer_id, body.week_start) is not None
    payout = payouts.generate_payout(session, body.farmer_id, body.week_start, clock)
    if existed:
        response.status_code = status.HTTP_200_OK
    return _statement(payout)


@router.get("", response_model=Page[PayoutOut])
def list_payouts(
    session: DbSession,
    farmer_id: int | None = None,
    status: PayoutStatus | None = None,
    week_start: date | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    items, total = payouts.list_payouts(session, farmer_id, status, week_start, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{payout_id}", response_model=PayoutStatementOut)
def get_payout(payout_id: int, session: DbSession):
    """The weekly statement: every line and the arithmetic down to the net amount."""
    return _statement(queries.get_payout(session, payout_id))


@router.post("/{payout_id}/finalise", response_model=PayoutStatementOut)
def finalise_payout(payout_id: int, session: DbSession, clock: RequestClock):
    return _statement(payouts.finalise_payout(session, payout_id, clock))


@router.post("/{payout_id}/mark-paid", response_model=PayoutStatementOut)
def mark_paid(payout_id: int, session: DbSession, clock: RequestClock):
    return _statement(payouts.mark_paid(session, payout_id, clock))
