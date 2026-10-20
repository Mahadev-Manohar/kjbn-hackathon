"""Rules 1, 2, 3 and 7: validate a delivery request and compute its frozen breakdown."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.delivery_calculations import (
    PriceCandidate,
    calculate_delivery_breakdown,
    select_applicable_price,
)
from app.domain.errors import InvalidInputError, RuleViolationError

THREE_DP = Decimal("0.001")
TWO_DP = Decimal("0.01")
MAX_WEIGHT_DECIMALS = 3
MAX_MOISTURE_DECIMALS = 2


@dataclass(frozen=True)
class CropRules:
    name: str
    allowed_grades: frozenset[str]
    moisture_threshold: Decimal
    max_moisture: Decimal


@dataclass(frozen=True)
class DeliveryRequest:
    grade: str
    gross_kg: Decimal
    moisture: Decimal
    delivered_on: date


@dataclass(frozen=True)
class DeliveryQuote:
    """Everything stored on a delivery row, or shown in a preview."""

    gross_kg: Decimal
    moisture: Decimal
    deduction_pct: Decimal
    deduction_kg: Decimal
    net_kg: Decimal
    applied_price: Decimal
    price_list_entry_id: int
    amount: Decimal


def _decimal_places(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def require_positive_finite(value: Decimal, field: str, max_decimals: int) -> None:
    if not value.is_finite():
        raise InvalidInputError(f"{field} must be a finite number", field=field)
    if value <= 0:
        raise InvalidInputError(f"{field} must be greater than zero", field=field)
    if _decimal_places(value) > max_decimals:
        raise InvalidInputError(
            f"{field} allows at most {max_decimals} decimal places", field=field
        )


def validate_delivery_request(request: DeliveryRequest, crop: CropRules, today: date) -> None:
    """Rule 7: allowed grade, positive weight and moisture, no future date."""
    if request.grade not in crop.allowed_grades:
        allowed = ", ".join(sorted(crop.allowed_grades))
        raise InvalidInputError(
            f"Grade '{request.grade}' is not allowed for {crop.name}; allowed grades: {allowed}",
            field="grade",
        )
    require_positive_finite(request.gross_kg, "gross_kg", MAX_WEIGHT_DECIMALS)
    require_positive_finite(request.moisture, "moisture", MAX_MOISTURE_DECIMALS)
    if request.delivered_on > today:
        raise RuleViolationError(
            f"Delivery date {request.delivered_on.isoformat()} is in the future",
            code="delivery_in_future",
            field="delivered_on",
        )


def quote_delivery(
    request: DeliveryRequest,
    crop: CropRules,
    price_entries: Iterable[PriceCandidate],
    today: date,
) -> DeliveryQuote:
    """Validate and price a delivery. Used for both preview and save, so they cannot diverge."""
    validate_delivery_request(request, crop, today)

    try:
        price = select_applicable_price(price_entries, request.delivered_on)
    except RuleViolationError as error:
        raise RuleViolationError(
            f"No price list entry for {crop.name} grade {request.grade} "
            f"effective on or before {request.delivered_on.isoformat()}",
            code="price_not_found",
            crop=crop.name,
            grade=request.grade,
        ) from error

    breakdown = calculate_delivery_breakdown(
        gross_kg=request.gross_kg,
        moisture=request.moisture,
        threshold=crop.moisture_threshold,
        max_moisture=crop.max_moisture,
        price_per_kg=price.price_per_kg,
    )
    # Fixed scales match the stored columns, so preview and saved record read identically.
    return DeliveryQuote(
        gross_kg=request.gross_kg.quantize(THREE_DP),
        moisture=request.moisture.quantize(TWO_DP),
        deduction_pct=breakdown.deduction_pct.quantize(TWO_DP),
        deduction_kg=breakdown.deduction_kg,
        net_kg=breakdown.net_kg,
        applied_price=price.price_per_kg.quantize(TWO_DP),
        price_list_entry_id=price.id,
        amount=breakdown.amount,
    )
