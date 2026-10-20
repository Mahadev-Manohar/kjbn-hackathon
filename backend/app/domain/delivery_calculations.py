from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.domain.errors import InvalidInputError, RuleViolationError

ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
MAX_DEDUCTION_PCT = Decimal("10")
THREE_DP = Decimal("0.001")
TWO_DP = Decimal("0.01")


@dataclass(frozen=True)
class PriceCandidate:
    """A price entry already filtered to the requested crop and grade."""

    id: int
    effective_from: date
    price_per_kg: Decimal


@dataclass(frozen=True)
class DeliveryBreakdown:
    """Calculated values to freeze on a delivery record."""

    deduction_pct: Decimal
    deduction_kg: Decimal
    net_kg: Decimal
    amount: Decimal


def select_applicable_price(
    entries: Iterable[PriceCandidate],
    delivered_on: date,
) -> PriceCandidate:
    """Choose the latest price effective on or before the delivery date."""
    applicable = [entry for entry in entries if entry.effective_from <= delivered_on]

    if not applicable:
        raise RuleViolationError(
            "No applicable price exists for this delivery date",
            code="price_not_found",
        )

    return max(applicable, key=lambda entry: entry.effective_from)


def calculate_deduction_percentage(
    moisture: Decimal,
    threshold: Decimal,
    max_moisture: Decimal,
) -> Decimal:
    """Calculate the moisture deduction percentage."""
    if moisture <= ZERO:
        raise InvalidInputError("Moisture must be greater than zero")

    if moisture > max_moisture:
        raise RuleViolationError(
            "Moisture exceeds the maximum accepted value",
            code="moisture_above_maximum",
        )

    if threshold < ZERO or max_moisture <= threshold:
        raise InvalidInputError("Invalid crop moisture limits")

    if moisture <= threshold:
        return ZERO

    excess = moisture - threshold
    whole_percentage_points = excess.to_integral_value(rounding=ROUND_FLOOR)

    return min(whole_percentage_points, MAX_DEDUCTION_PCT)


def calculate_delivery_breakdown(
    gross_kg: Decimal,
    moisture: Decimal,
    threshold: Decimal,
    max_moisture: Decimal,
    price_per_kg: Decimal,
) -> DeliveryBreakdown:
    """Calculate deduction weight, net weight, and delivery amount."""
    if gross_kg <= ZERO:
        raise InvalidInputError("Gross weight must be greater than zero")

    if price_per_kg <= ZERO:
        raise InvalidInputError("Price per kg must be greater than zero")

    deduction_pct = calculate_deduction_percentage(
        moisture=moisture,
        threshold=threshold,
        max_moisture=max_moisture,
    )

    deduction_kg = (gross_kg * deduction_pct / ONE_HUNDRED).quantize(
        THREE_DP, rounding=ROUND_HALF_UP
    )

    net_kg = (gross_kg - deduction_kg).quantize(
        THREE_DP,
        rounding=ROUND_HALF_UP,
    )

    amount = (net_kg * price_per_kg).quantize(
        TWO_DP,
        rounding=ROUND_HALF_UP,
    )

    return DeliveryBreakdown(
        deduction_pct=deduction_pct,
        deduction_kg=deduction_kg,
        net_kg=net_kg,
        amount=amount,
    )
