"""Rules 4, 5 and 6: weekly payouts, advance recovery and payout lifecycle."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.domain.errors import ConflictError, RuleViolationError

ZERO = Decimal("0.00")
TWO_DP = Decimal("0.01")
ADVANCE_RECOVERY_RATE = Decimal("0.30")

DRAFT = "Draft"
FINALISED = "Finalised"
PAID = "Paid"
FROZEN_STATUSES = frozenset({FINALISED, PAID})


@dataclass(frozen=True)
class PayoutTotals:
    gross_amount: Decimal
    advance_deduction: Decimal
    net_amount: Decimal


def week_start(day: date) -> date:
    """Monday of the Monday-Sunday week containing `day`."""
    return day - timedelta(days=day.weekday())


def week_end(day: date) -> date:
    """Sunday of the Monday-Sunday week containing `day`."""
    return week_start(day) + timedelta(days=6)


def require_monday(day: date) -> date:
    if day.weekday() != 0:
        raise RuleViolationError(
            f"{day.isoformat()} is not a Monday; payout weeks run Monday to Sunday",
            code="week_start_not_monday",
        )
    return day


def require_week_started(start: date, today: date) -> None:
    if start > today:
        raise RuleViolationError(
            f"Week starting {start.isoformat()} has not started yet",
            code="week_in_future",
        )


def outstanding_advance(total_advances: Decimal, recovered: Decimal) -> Decimal:
    """Advances given minus recoveries on Finalised or Paid payouts only (rule 5)."""
    return max(total_advances - recovered, ZERO)


def recovery_cap(gross_amount: Decimal) -> Decimal:
    """30% of gross rounded half-up to paise; zero when gross is not positive."""
    if gross_amount <= ZERO:
        return ZERO
    return (gross_amount * ADVANCE_RECOVERY_RATE).quantize(TWO_DP, rounding=ROUND_HALF_UP)


def advance_recovery(gross_amount: Decimal, outstanding: Decimal) -> Decimal:
    """Lesser of the outstanding advance and 30% of gross, never negative."""
    if outstanding <= ZERO:
        return ZERO
    return min(outstanding, recovery_cap(gross_amount))


def compute_payout(line_amounts: Iterable[Decimal], outstanding: Decimal) -> PayoutTotals:
    """Gross is the sum of line amounts (notes are signed), so net = gross - deduction exactly."""
    gross = sum(line_amounts, ZERO)
    deduction = advance_recovery(gross, outstanding)
    return PayoutTotals(gross, deduction, gross - deduction)


def require_has_lines(line_count: int, start: date) -> None:
    if line_count == 0:
        raise RuleViolationError(
            f"No unpaid deliveries for the week starting {start.isoformat()}",
            code="no_deliveries_in_week",
        )


def ensure_draft(status: str) -> None:
    if status != DRAFT:
        raise ConflictError(
            f"Payout is {status} and can no longer be changed",
            code="payout_immutable",
        )


def ensure_can_finalise(status: str) -> None:
    if status != DRAFT:
        raise ConflictError(
            f"Only a Draft payout can be finalised; this one is {status}",
            code="invalid_payout_transition",
        )


def ensure_can_mark_paid(status: str) -> None:
    if status != FINALISED:
        raise ConflictError(
            f"Only a Finalised payout can be marked paid; this one is {status}",
            code="invalid_payout_transition",
        )
