from datetime import date
from decimal import Decimal

import pytest

from app.domain.delivery_calculations import (
    PriceCandidate,
    calculate_deduction_percentage,
    calculate_delivery_breakdown,
    select_applicable_price,
)
from app.domain.errors import InvalidInputError, RuleViolationError

D = Decimal


@pytest.mark.parametrize(
    ("moisture", "expected"),
    [
        ("14.00", "0"),
        ("14.99", "0"),
        ("15.00", "1"),
        ("17.60", "3"),
        ("24.99", "10"),
    ],
)
def test_deduction_percentage(moisture, expected):
    result = calculate_deduction_percentage(D(moisture), D("14"), D("25"))
    assert result == D(expected)


def test_maximum_accepted_moisture_is_allowed():
    assert calculate_deduction_percentage(D("25"), D("14"), D("25")) == D("10")


def test_moisture_above_maximum_is_rejected():
    with pytest.raises(RuleViolationError, match="maximum accepted"):
        calculate_deduction_percentage(D("25.01"), D("14"), D("25"))


def test_zero_moisture_is_rejected():
    with pytest.raises(InvalidInputError, match="greater than zero"):
        calculate_deduction_percentage(D("0"), D("14"), D("25"))


def test_latest_applicable_price_is_selected():
    entries = [
        PriceCandidate(1, date(2026, 1, 1), D("20.00")),
        PriceCandidate(2, date(2026, 3, 1), D("22.00")),
        PriceCandidate(3, date(2026, 5, 1), D("24.00")),
    ]

    selected = select_applicable_price(entries, date(2026, 4, 1))

    assert selected.id == 2
    assert selected.price_per_kg == D("22.00")


def test_price_effective_on_delivery_date_is_eligible():
    entries = [
        PriceCandidate(1, date(2026, 3, 1), D("20.00")),
        PriceCandidate(2, date(2026, 4, 1), D("22.00")),
    ]

    selected = select_applicable_price(entries, date(2026, 4, 1))

    assert selected.id == 2


def test_missing_applicable_price_is_rejected():
    entries = [PriceCandidate(1, date(2026, 5, 1), D("24.00"))]

    with pytest.raises(RuleViolationError, match="No applicable price"):
        select_applicable_price(entries, date(2026, 4, 1))


def test_delivery_breakdown():
    result = calculate_delivery_breakdown(
        gross_kg=D("100.000"),
        moisture=D("17.60"),
        threshold=D("14"),
        max_moisture=D("25"),
        price_per_kg=D("24.00"),
    )

    assert result.deduction_pct == D("3")
    assert result.deduction_kg == D("3.000")
    assert result.net_kg == D("97.000")
    assert result.amount == D("2328.00")


def test_deduction_weight_uses_half_up_rounding():
    result = calculate_delivery_breakdown(
        gross_kg=D("10.001"),
        moisture=D("15"),
        threshold=D("14"),
        max_moisture=D("25"),
        price_per_kg=D("1.00"),
    )

    assert result.deduction_kg == D("0.100")
    assert result.net_kg == D("9.901")


def test_amount_uses_half_up_rounding():
    result = calculate_delivery_breakdown(
        gross_kg=D("1.000"),
        moisture=D("14"),
        threshold=D("14"),
        max_moisture=D("25"),
        price_per_kg=D("2.345"),
    )

    assert result.amount == D("2.35")


def test_zero_gross_weight_is_rejected():
    with pytest.raises(InvalidInputError, match="Gross weight"):
        calculate_delivery_breakdown(D("0"), D("14"), D("14"), D("25"), D("24"))


def test_non_positive_price_is_rejected():
    with pytest.raises(InvalidInputError, match="Price per kg"):
        calculate_delivery_breakdown(D("10"), D("14"), D("14"), D("25"), D("0"))


def test_invalid_crop_moisture_limits_are_rejected():
    with pytest.raises(InvalidInputError, match="Invalid crop moisture limits"):
        calculate_deduction_percentage(D("10"), D("14"), D("14"))


def test_deduction_weight_tie_rounds_half_up_not_to_even():
    # 1% of 0.050 kg is exactly 0.0005 kg: half-up gives 0.001 (banker's rounding would give 0.000)
    result = calculate_delivery_breakdown(
        gross_kg=D("0.050"),
        moisture=D("15"),
        threshold=D("14"),
        max_moisture=D("25"),
        price_per_kg=D("10.00"),
    )
    assert result.deduction_kg == D("0.001")
    assert result.net_kg == D("0.049")


def test_breakdown_invariants_hold_for_many_random_inputs():
    """net = gross - deduction exactly; amount = net x price rounded half-up to paise."""
    import random

    rng = random.Random(4)
    for _ in range(3000):
        gross = D(rng.randint(1, 9_999_999)) / D(1000)
        moisture = D(rng.randint(1, 2500)) / D(100)
        price = D(rng.randint(1, 1_000_000)) / D(100)
        result = calculate_delivery_breakdown(gross, moisture, D("14"), D("25"), price)
        assert result.deduction_kg + result.net_kg == gross.quantize(D("0.001"))
        assert result.amount == (result.net_kg * price).quantize(
            D("0.01"), rounding="ROUND_HALF_UP"
        )
        assert D("0") <= result.deduction_pct <= D("10")
        expected_pct = min(max((moisture - D("14")) // D(1), D(0)), D(10))
        assert result.deduction_pct == expected_pct
