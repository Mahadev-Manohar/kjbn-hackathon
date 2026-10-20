"""Time helpers. Timestamps are stored in UTC; business dates are IST (Asia/Kolkata)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.domain.errors import InvalidInputError

IST = ZoneInfo("Asia/Kolkata")


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_ist_date(moment: datetime) -> date:
    """The calendar date in IST for an aware datetime. Naive values are rejected."""
    if moment.tzinfo is None:
        raise ValueError("Clock values must be timezone-aware")
    return moment.astimezone(IST).date()


@dataclass(frozen=True)
class Clock:
    """A fixed instant for one request. Real requests use the wall clock; reviewers may override."""

    now: datetime

    @property
    def today(self) -> date:
        return to_ist_date(self.now)


def parse_clock_override(raw: str) -> Clock:
    """Parse an X-Test-Clock value: a full ISO datetime, or a date meaning noon IST that day.

    A datetime without an offset is read as IST.
    """
    try:
        if len(raw) == 10:
            moment = datetime.combine(date.fromisoformat(raw), time(12, 0), tzinfo=IST)
        else:
            moment = datetime.fromisoformat(raw)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=IST)
    except ValueError as error:
        raise InvalidInputError(
            "X-Test-Clock must be an ISO date (2026-10-20) or datetime (2026-10-20T10:00:00+05:30)",
            field="X-Test-Clock",
        ) from error
    return Clock(moment.astimezone(UTC))
