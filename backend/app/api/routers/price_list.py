from fastapi import APIRouter, status

from app.api.deps import DbSession, Limit, Offset
from app.api.schemas import Page, PriceIn, PriceOut
from app.services import master_data

router = APIRouter(prefix="/price-list", tags=["price list"])


@router.post("", response_model=PriceOut, status_code=status.HTTP_201_CREATED)
def add_price(body: PriceIn, session: DbSession):
    """Append a price entry. Entries are never edited or deleted; history is the record."""
    return master_data.add_price(
        session, body.crop_id, body.grade, body.price_per_kg, body.effective_from
    )


@router.get("", response_model=Page[PriceOut])
def list_prices(
    session: DbSession,
    crop_id: int | None = None,
    grade: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
):
    """Price history, newest effective date first within each crop and grade."""
    items, total = master_data.list_prices(session, crop_id, grade, limit, offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
