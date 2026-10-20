from datetime import date
from decimal import Decimal

import pytest

from app.domain.errors import InvalidInputError, RuleViolationError
from app.domain.note_rules import (
    ensure_delivery_editable,
    ensure_note_target,
    ensure_week_open_for_delivery,
    note_effective_date,
    signed_note_amount,
)

D = Decimal


@pytest.mark.parametrize("payout_status", [None, "Draft"])
def test_delivery_outside_frozen_payout_is_editable(payout_status):
    ensure_delivery_editable("DELIVERY", payout_status)


@pytest.mark.parametrize("payout_status", ["Finalised", "Paid"])
def test_delivery_in_finalised_payout_cannot_be_edited(payout_status):
    with pytest.raises(RuleViolationError) as caught:
        ensure_delivery_editable("DELIVERY", payout_status)
    assert caught.value.code == "delivery_locked"
    assert "credit or debit note" in caught.value.message


def test_notes_cannot_be_edited():
    with pytest.raises(RuleViolationError):
        ensure_delivery_editable("CREDIT_NOTE", None)


def test_new_delivery_cannot_join_a_finalised_week():
    frozen = {date(2026, 10, 12)}
    with pytest.raises(RuleViolationError) as caught:
        ensure_week_open_for_delivery(date(2026, 10, 18), frozen)  # Sunday of that week
    assert caught.value.code == "week_already_finalised"
    ensure_week_open_for_delivery(date(2026, 10, 19), frozen)  # next Monday is open


def test_credit_note_is_positive_and_debit_note_negative():
    assert signed_note_amount("CREDIT_NOTE", D("50.00")) == D("50.00")
    assert signed_note_amount("DEBIT_NOTE", D("50.00")) == D("-50.00")


@pytest.mark.parametrize("amount", ["0", "-5", "NaN", "10.005"])
def test_invalid_note_amount_is_rejected(amount):
    with pytest.raises(InvalidInputError):
        signed_note_amount("CREDIT_NOTE", D(amount))


def test_unknown_note_kind_is_rejected():
    with pytest.raises(InvalidInputError):
        signed_note_amount("REFUND", D("5"))


def test_note_must_reference_a_finalised_delivery():
    ensure_note_target("DELIVERY", "Finalised")
    ensure_note_target("DELIVERY", "Paid")
    with pytest.raises(RuleViolationError) as caught:
        ensure_note_target("DELIVERY", "Draft")
    assert caught.value.code == "note_target_not_finalised"
    with pytest.raises(RuleViolationError):
        ensure_note_target("DELIVERY", None)


def test_note_cannot_reference_another_note():
    with pytest.raises(RuleViolationError) as caught:
        ensure_note_target("CREDIT_NOTE", "Finalised")
    assert caught.value.code == "note_target_invalid"


def test_note_lands_today_when_current_week_is_open():
    assert note_effective_date(date(2026, 10, 21), frozen_week_starts=set()) == date(2026, 10, 21)


def test_note_moves_to_next_open_week_when_current_week_is_finalised():
    frozen = {date(2026, 10, 19)}
    assert note_effective_date(date(2026, 10, 21), frozen) == date(2026, 10, 26)


def test_note_skips_several_consecutive_finalised_weeks():
    frozen = {date(2026, 10, 19), date(2026, 10, 26)}
    assert note_effective_date(date(2026, 10, 21), frozen) == date(2026, 11, 2)
