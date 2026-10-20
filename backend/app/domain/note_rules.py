"""Rule 6: edit protection for finalised deliveries and credit/debit note corrections."""

from collections.abc import Collection
from datetime import date, timedelta
from decimal import Decimal

from app.domain.errors import InvalidInputError, RuleViolationError
from app.domain.payout_rules import FROZEN_STATUSES, week_start

CREDIT_NOTE = "CREDIT_NOTE"
DEBIT_NOTE = "DEBIT_NOTE"
DELIVERY = "DELIVERY"


def ensure_delivery_editable(kind: str, payout_status: str | None) -> None:
    """Only plain deliveries outside Finalised/Paid payouts may be edited."""
    if kind != DELIVERY:
        raise RuleViolationError("Notes cannot be edited", code="note_not_editable")
    if payout_status in FROZEN_STATUSES:
        raise RuleViolationError(
            f"Delivery belongs to a {payout_status} payout and cannot be edited; "
            "issue a credit or debit note instead",
            code="delivery_locked",
        )


def ensure_week_open_for_delivery(delivered_on: date, frozen_week_starts: Collection[date]) -> None:
    """A new delivery cannot join a week whose payout is already Finalised or Paid."""
    if week_start(delivered_on) in frozen_week_starts:
        raise RuleViolationError(
            f"The payout for the week of {week_start(delivered_on).isoformat()} is already "
            "finalised; record a credit or debit note instead",
            code="week_already_finalised",
        )


def signed_note_amount(kind: str, amount: Decimal) -> Decimal:
    """Credit notes add to the farmer (positive); debit notes deduct (negative)."""
    if kind not in (CREDIT_NOTE, DEBIT_NOTE):
        raise InvalidInputError("Note kind must be CREDIT_NOTE or DEBIT_NOTE", field="kind")
    if not amount.is_finite() or amount <= 0:
        raise InvalidInputError("Note amount must be greater than zero", field="amount")
    if amount != amount.quantize(Decimal("0.01")):
        raise InvalidInputError("Note amount allows at most 2 decimal places", field="amount")
    return amount if kind == CREDIT_NOTE else -amount


def ensure_note_target(original_kind: str, original_payout_status: str | None) -> None:
    """Notes correct a delivery that already sits in a Finalised or Paid payout."""
    if original_kind != DELIVERY:
        raise RuleViolationError(
            "A note must reference an original delivery, not another note",
            code="note_target_invalid",
        )
    if original_payout_status not in FROZEN_STATUSES:
        raise RuleViolationError(
            "The referenced delivery is not in a finalised payout; edit the delivery instead",
            code="note_target_not_finalised",
        )


def note_effective_date(today: date, frozen_week_starts: Collection[date]) -> date:
    """Date a note is booked on: today, or the next Monday whose week is still open."""
    day = today
    while week_start(day) in frozen_week_starts:
        day = week_start(day) + timedelta(days=7)
    return day
