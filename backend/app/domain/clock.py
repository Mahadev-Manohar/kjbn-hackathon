"""Time helpers. Timestamps are stored in UTC; business dates are IST (Asia/Kolkata)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_ist_date(moment: datetime) -> date:
    """The calendar date in IST for an aware datetime. Naive values are rejected."""
    if moment.tzinfo is None:
        raise ValueError("Clock values must be timezone-aware")
    return moment.astimezone(IST).date()
