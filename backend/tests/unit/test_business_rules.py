
"""
Business-rule test specification for KJBN Problem 4.

These cases define expected behaviour from the official problem
requirements. M2 will implement the corresponding executable tests.
"""

import pytest


@pytest.mark.parametrize(
    ("moisture", "threshold", "expected_deduction_pct"),
    [
        (14.00, 14.00, 0),
        (14.99, 14.00, 0),
        (15.00, 14.00, 1),
        (17.60, 14.00, 3),
        (25.00, 14.00, 10),
    ],
)
def test_moisture_deduction_cases(
    moisture, threshold, expected_deduction_pct
):
    """Expected deduction percentage for threshold boundary cases."""
    pytest.skip("Specification only; implement in M2")


@pytest.mark.parametrize(
    ("gross_kg", "deduction_pct", "expected_deduction_kg"),
    [
        (100.000, 3, 3.000),
        (10.001, 3, 0.300),
        (1.000, 10, 0.100),
    ],
)
def test_deduction_weight_rounding_cases(
    gross_kg, deduction_pct, expected_deduction_kg
):
    """Deduction weight must use Decimal and half-up rounding to 3 dp."""
    pytest.skip("Specification only; implement in M2")


def test_price_selection_uses_latest_effective_date():
    """Select latest effective_from <= delivery date."""
    pytest.skip("Specification only; implement in M2")


def test_missing_effective_price_is_rejected():
    """Reject delivery when no applicable price exists."""
    pytest.skip("Specification only; implement in M2")


def test_delivery_amount_rounds_half_up_to_two_decimals():
    """Delivery amount must use Decimal and half-up rounding."""
    pytest.skip("Specification only; implement in M2")


def test_delivery_above_maximum_moisture_is_rejected():
    """Reject moisture above the crop's maximum accepted value."""
    pytest.skip("Specification only; implement in M2")


def test_future_delivery_date_is_rejected():
    """Reject future dates using an injectable clock."""
    pytest.skip("Specification only; implement in M2")


def test_advance_recovery_is_limited_to_30_percent_of_gross():
    """Recovery cannot exceed 30% of the gross payout."""
    pytest.skip("Specification only; implement in M2")


def test_advance_recovery_cannot_exceed_outstanding_balance():
    """Recovery cannot exceed the farmer's outstanding advances."""
    pytest.skip("Specification only; implement in M2")


def test_finalised_payout_is_immutable():
    """A finalised payout cannot be modified."""
    pytest.skip("Specification only; implement in M2")


def test_correction_note_is_included_in_a_later_payout():
    """Correction notes reference the original and enter a later payout."""
    pytest.skip("Specification only; implement in M2")
