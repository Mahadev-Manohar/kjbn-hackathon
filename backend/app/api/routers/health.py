import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.errors import error_response
from app.domain.clock import utc_now

router = APIRouter(tags=["health"])
logger = logging.getLogger("app.health")


@router.get("/health")
def health(session: DbSession):
    """Liveness plus a database round-trip."""
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.error("health_check_failed", exc_info=True)
        return error_response(503, "database_unavailable", "The database is not reachable")
    return {"status": "ok", "database": "ok", "time": utc_now().isoformat()}
