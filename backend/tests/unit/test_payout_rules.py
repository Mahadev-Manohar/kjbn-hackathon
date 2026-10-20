from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.errors import ConflictError, RuleViolationError
from app.domain.payout_rules import (
    advance_recovery,
    compute_payout,
    ensure_can_finalise,
    ensure_can_mark_paid,
    ensure_draft,
    outstanding_advance,
    require_has_lines,
    require_monday,
    require_week_started,
    week_end,
    week_start,
)

D = Decimal


@pytest.mark.parametrize(
    ("day", "expected_start"),
    [
        (date(2026, 10, 19), date(2026, 10, 19)),  # Monday
        (date(2026, 10, 21), date(2026, 10, 19)),  # Wednesday
        (date(2026, 10, 25), date(2026, 10, 19)),  # Sunday still belongs to the same week
        (date(2026, 10, 26), date(2026, 10, 26)),  # next Monday starts a new week
    ],
)
def test_week_boundaries_are_monday_to_sunday(day, expected_start):
    assert week_start(day) == expected_start
    assert week_end(day) == expected_start + timedelta(days=6)


def test_week_crossing_month_end():
    assert week_end(date(2026, 10, 28)) == date(2026, 11, 1)


def test_non_monday_week_start_is_rejected():
    with pytest.raises(RuleViolationError) as caught:
        require_monday(date(2026, 10, 20))
    assert caught.value.code == "week_start_not_monday"
    assert require_monday(date(2026, 10, 19)) == date(2026, 10, 19)


def test_week_that_has_not_started_is_rejected():
    with pytest.raises(RuleViolationError):
        require_week_started(date(2026, 10, 26), today=date(2026, 10, 25))
    require_week_started(date(2026, 10, 26), today=date(2026, 10, 26))


def test_week_without_deliveries_is_rejected():
    with pytest.raises(RuleViolationError) as caught:
        require_has_lines(0, date(2026, 10, 19))
    assert caught.value.code == "no_deliveries_in_week"
    require_has_lines(1, date(2026, 10, 19))


def test_recovery_is_capped_at_30_percent_of_gross():
    assert advance_recovery(D("1000.00"), D("5000.00")) == D("300.00")


def test_recovery_is_capped_at_outstanding_balance():
    assert advance_recovery(D("1000.00"), D("120.50")) == D("120.50")


def test_recovery_when_outstanding_equals_cap():
    assert advance_recovery(D("1000.00"), D("300.00")) == D("300.00")


def test_recovery_cap_rounds_half_up():
    # 30% of 0.05 = 0.015 -> 0.02
    assert advance_recovery(D("0.05"), D("100.00")) == D("0.02")


@pytest.mark.parametrize(("gross", "outstanding"), [("0", "100"), ("1000", "0"), ("-50", "100")])
def test_no_recovery_without_gross_or_advance(gross, outstanding):
    assert advance_recovery(D(gross), D(outstanding)) == D("0.00")


def test_payout_totals_net_equals_gross_minus_deduction():
    totals = compute_payout([D("2328.00"), D("100.10"), D("-28.10")], D("10000"))
    assert totals.gross_amount == D("2400.00")
    assert totals.advance_deduction == D("720.00")
    assert totals.net_amount == D("1680.00")


def test_empty_payout_has_zero_totals():
    totals = compute_payout([], D("500"))
    assert (totals.gross_amount, totals.advance_deduction, totals.net_amount) == (D(0), D(0), D(0))


def test_negative_gross_from_debit_notes_recovers_nothing():
    totals = compute_payout([D("-200.00")], D("500"))
    assert totals.advance_deduction == D("0.00")
    assert totals.net_amount == D("-200.00")


def test_large_advance_is_recovered_at_30_percent_over_several_payouts():
    total_advance = D("5000.00")
    recovered = D("0.00")
    deductions = []
    for gross in (D("1000.00"), D("2000.00"), D("1500.00")):
        totals = compute_payout([gross], outstanding_advance(total_advance, recovered))
        deductions.append(totals.advance_deduction)
        recovered += totals.advance_deduction
    assert deductions == [D("300.00"), D("600.00"), D("450.00")]
    assert outstanding_advance(total_advance, recovered) == D("3650.00")


def test_final_payout_recovers_only_what_is_left():
    totals = compute_payout([D("1000.00")], D("80.00"))
    assert totals.advance_deduction == D("80.00")


def test_outstanding_never_negative():
    assert outstanding_advance(D("100"), D("150")) == D("0.00")


def test_outstanding_unchanged_while_nothing_is_recovered():
    # Draft payouts are excluded by the caller; only Finalised/Paid recoveries are subtracted.
    assert outstanding_advance(D("1500.00"), D("0")) == D("1500.00")


@pytest.mark.parametrize("status", ["Finalised", "Paid"])
def test_finalised_or_paid_payout_is_immutable(status):
    with pytest.raises(ConflictError) as caught:
        ensure_draft(status)
    assert caught.value.code == "payout_immutable"


def test_draft_payout_is_changeable():
    ensure_draft("Draft")


@pytest.mark.parametrize("status", ["Finalised", "Paid"])
def test_only_draft_can_be_finalised(status):
    with pytest.raises(ConflictError):
        ensure_can_finalise(status)
    ensure_can_finalise("Draft")


@pytest.mark.parametrize("status", ["Draft", "Paid"])
def test_only_finalised_can_be_marked_paid(status):
    with pytest.raises(ConflictError):
        ensure_can_mark_paid(status)
    ensure_can_mark_paid("Finalised")
