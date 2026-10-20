"""FastAPI dependencies: database session and the request clock."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.clock import Clock, parse_clock_override, utc_now
from app.persistence.database import SessionLocal


def get_session() -> Generator[Session, None, None]:
    """One session per request. Services commit explicitly; an error leaves nothing written."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_clock(x_test_clock: Annotated[str | None, Header()] = None) -> Clock:
    """Wall clock, or the reviewer override from X-Test-Clock when enabled."""
    if x_test_clock and settings.allow_test_clock:
        return parse_clock_override(x_test_clock)
    return Clock(utc_now())


DbSession = Annotated[Session, Depends(get_session)]
RequestClock = Annotated[Clock, Depends(get_clock)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0, le=1_000_000)]
