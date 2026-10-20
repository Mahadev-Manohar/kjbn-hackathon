from datetime import date

from fastapi import APIRouter, status

from app.api.deps import DbSession, Limit, Offset, RequestClock
from app.api.schemas import (
    DeliveryDetails,
    DeliveryIn,
    DeliveryOut,
    DeliveryPreviewIn,
    DeliveryPreviewOut,
    NoteIn,
    Page,
)
from app.domain.delivery_rules import DeliveryRequest
from app.persistence import queries
from app.services import deliveries

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


def _request(body: DeliveryDetails) -> DeliveryRequest:
    return DeliveryRequest(
        grade=body.grade,
        gross_kg=body.gross_kg,
        moisture=body.moisture,
        delivered_on=body.delivered_on,
    )


@router.post("/preview", response_model=DeliveryPreviewOut)
def preview_delivery(body: DeliveryPreviewIn, session: DbSession, clock: RequestClock):
    """Price and deductions for a delivery without saving it."""
    crop, quote = deliveries.preview_delivery(
        session, body.crop_id, _request(body), body.farmer_id, clock
    )
    return DeliveryPreviewOut(
        crop_id=crop.id,
        crop_name=crop.name,
        grade=body.grade,
        delivered_on=body.delivered_on,
        moisture_threshold=crop.base_moisture_threshold,
        **vars(quote),
    )


@router.post("", response_model=DeliveryOut, status_code=status.HTTP_201_CREATED)
def create_delivery(body: DeliveryIn, session: DbSession, clock: RequestClock):
    return deliveries.create_delivery(session, body.farmer_id, body.crop_id, _request(body), clock)


@router.get("", response_model=Page[DeliveryOut])
def list_deliveries(
    session: DbSession,
    farmer_id: int | None = None,
    crop_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
):
    items, total = deliveries.list_deliveries(
        session, farmer_id, crop_id, date_from, date_to, limit, offset
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{delivery_id}", response_model=DeliveryOut)
def get_delivery(delivery_id: int, session: DbSession):
    return queries.get_delivery(session, delivery_id)


@router.put("/{delivery_id}", response_model=DeliveryOut)
def update_delivery(
    delivery_id: int, body: DeliveryDetails, session: DbSession, clock: RequestClock
):
    """Edit a delivery that is not in a Finalised or Paid payout; its breakdown is re-frozen."""
    return deliveries.update_delivery(session, delivery_id, _request(body), clock)


@router.post(
    "/{delivery_id}/notes", response_model=DeliveryOut, status_code=status.HTTP_201_CREATED
)
def create_note(delivery_id: int, body: NoteIn, session: DbSession, clock: RequestClock):
    """Credit or debit note correcting a delivery in a Finalised or Paid payout."""
    return deliveries.create_note(
        session, delivery_id, body.kind.value, body.amount, body.reason, clock
    )
