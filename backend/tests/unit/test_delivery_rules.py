from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain.clock import to_ist_date
from app.domain.delivery_calculations import PriceCandidate
from app.domain.delivery_rules import CropRules, DeliveryRequest, quote_delivery
from app.domain.errors import InvalidInputError, RuleViolationError

D = Decimal
TODAY = date(2026, 10, 20)
MAIZE = CropRules("Maize", frozenset({"A", "B", "C"}), D("14"), D("25"))
PRICES = [
    PriceCandidate(1, date(2026, 1, 1), D("24.00")),
    PriceCandidate(2, date(2026, 10, 1), D("26.00")),
]


def request(**overrides) -> DeliveryRequest:
    values = {
        "grade": "A",
        "gross_kg": D("100"),
        "moisture": D("14"),
        "delivered_on": TODAY,
    }
    return DeliveryRequest(**{**values, **overrides})


def test_quote_freezes_full_breakdown():
    quote = quote_delivery(
        request(moisture=D("17.6"), delivered_on=date(2026, 10, 2)), MAIZE, PRICES, TODAY
    )
    assert quote.deduction_pct == D("3")
    assert quote.deduction_kg == D("3.000")
    assert quote.net_kg == D("97.000")
    assert quote.applied_price == D("26.00")
    assert quote.price_list_entry_id == 2
    assert quote.amount == D("2522.00")


def test_breakdown_parts_add_up():
    quote = quote_delivery(request(gross_kg=D("33.333"), moisture=D("16.5")), MAIZE, PRICES, TODAY)
    assert quote.deduction_kg + quote.net_kg == quote.gross_kg


def test_delivery_on_exact_effective_from_uses_new_price():
    quote = quote_delivery(request(delivered_on=date(2026, 10, 1)), MAIZE, PRICES, TODAY)
    assert quote.price_list_entry_id == 2


def test_day_before_effective_from_uses_previous_price():
    quote = quote_delivery(request(delivered_on=date(2026, 9, 30)), MAIZE, PRICES, TODAY)
    assert quote.price_list_entry_id == 1


def test_back_dated_price_entry_selected_for_matching_delivery_date():
    prices = [*PRICES, PriceCandidate(3, date(2026, 9, 15), D("25.00"))]
    quote = quote_delivery(request(delivered_on=date(2026, 9, 20)), MAIZE, prices, TODAY)
    assert quote.price_list_entry_id == 3


def test_missing_price_message_names_crop_grade_and_date():
    with pytest.raises(RuleViolationError) as caught:
        quote_delivery(request(delivered_on=date(2025, 12, 31)), MAIZE, PRICES, TODAY)
    assert caught.value.code == "price_not_found"
    assert "Maize" in caught.value.message
    assert "grade A" in caught.value.message
    assert "2025-12-31" in caught.value.message


def test_no_price_entries_at_all_is_rejected():
    with pytest.raises(RuleViolationError, match="No price list entry"):
        quote_delivery(request(), MAIZE, [], TODAY)


def test_grade_outside_allowed_list_is_rejected():
    with pytest.raises(InvalidInputError, match="not allowed for Maize"):
        quote_delivery(request(grade="D"), MAIZE, PRICES, TODAY)


def test_grade_matching_is_case_sensitive():
    with pytest.raises(InvalidInputError):
        quote_delivery(request(grade="a"), MAIZE, PRICES, TODAY)


@pytest.mark.parametrize("weight", ["0", "-1", "NaN", "Infinity", "10.0001"])
def test_invalid_weight_is_rejected(weight):
    with pytest.raises(InvalidInputError):
        quote_delivery(request(gross_kg=D(weight)), MAIZE, PRICES, TODAY)


@pytest.mark.parametrize("moisture", ["0", "-0.5", "NaN", "14.999"])
def test_invalid_moisture_is_rejected(moisture):
    with pytest.raises(InvalidInputError):
        quote_delivery(request(moisture=D(moisture)), MAIZE, PRICES, TODAY)


def test_moisture_above_crop_maximum_is_rejected():
    with pytest.raises(RuleViolationError) as caught:
        quote_delivery(request(moisture=D("25.01")), MAIZE, PRICES, TODAY)
    assert caught.value.code == "moisture_above_maximum"


def test_moisture_exactly_at_maximum_is_accepted_with_capped_deduction():
    quote = quote_delivery(request(moisture=D("25")), MAIZE, PRICES, TODAY)
    assert quote.deduction_pct == D("10")


def test_delivery_dated_today_is_accepted():
    assert quote_delivery(request(delivered_on=TODAY), MAIZE, PRICES, TODAY)


def test_future_delivery_date_is_rejected():
    with pytest.raises(RuleViolationError) as caught:
        quote_delivery(request(delivered_on=date(2026, 10, 21)), MAIZE, PRICES, TODAY)
    assert caught.value.code == "delivery_in_future"


def test_ist_date_rolls_over_before_utc_midnight():
    # 19:00 UTC on 20 Oct is 00:30 IST on 21 Oct.
    assert to_ist_date(datetime(2026, 10, 20, 19, 0, tzinfo=UTC)) == date(2026, 10, 21)


def test_naive_clock_value_is_rejected():
    with pytest.raises(ValueError):
        to_ist_date(datetime(2026, 10, 20, 12, 0))


@pytest.mark.parametrize(
    "raw",
    [
        "0001-01-01T00:00:00+14:00",  # overflows converting to UTC
        "9999-12-31T23:59:59+00:00",  # valid UTC, but the IST date would be year 10000
        "9999-12-31T23:59:59-12:00",
        "yesterday",
        "",
        "2026-13-01",
    ],
)
def test_unrepresentable_clock_overrides_are_input_errors_not_crashes(raw):
    from app.domain.clock import parse_clock_override

    with pytest.raises(InvalidInputError, match="X-Test-Clock"):
        parse_clock_override(raw)


def test_clock_override_forms_resolve_to_the_expected_ist_date():
    from app.domain.clock import parse_clock_override

    assert parse_clock_override("2026-10-20").today == date(2026, 10, 20)
    assert parse_clock_override("2026-10-20T23:30:00").today == date(2026, 10, 20)  # naive = IST
    assert parse_clock_override("2026-10-20T20:00:00+00:00").today == date(2026, 10, 21)
