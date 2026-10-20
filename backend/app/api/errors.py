"""One error response shape for every failure.

{"error": {"code": ..., "message": ..., "details": {...}, "request_id": ...}}

- Malformed request bodies/params  -> 422 validation_error (FastAPI/pydantic)
- Typed domain errors              -> 422 / 404 / 409 by class
- Database integrity/availability  -> 409 / 503
- Anything else                    -> 500 internal_error, no internals leaked
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var
from app.domain.errors import (
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    RuleViolationError,
)

logger = logging.getLogger("app.errors")

STATUS_BY_DOMAIN_ERROR: dict[type[DomainError], int] = {
    InvalidInputError: 422,
    RuleViolationError: 422,
    NotFoundError: 404,
    ConflictError: 409,
}


def error_response(status: int, code: str, message: str, details: dict | None = None):
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id_var.get(),
        }
    }
    return JSONResponse(status_code=status, content=body)


def _domain_status(error: DomainError) -> int:
    for error_type, status in STATUS_BY_DOMAIN_ERROR.items():
        if isinstance(error, error_type):
            return status
    return 500


async def handle_domain_error(request: Request, error: DomainError):
    status = _domain_status(error)
    logger.warning(
        "domain_error",
        extra={
            "code": error.code,
            "reason": error.message,
            "status": status,
            "path": request.url.path,
            **error.details,
        },
    )
    return error_response(status, error.code, error.message, error.details)


async def handle_validation_error(request: Request, error: RequestValidationError):
    problems = [
        {
            "field": ".".join(str(part) for part in item["loc"] if part not in ("body", "query")),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    logger.warning(
        "validation_error",
        extra={"path": request.url.path, "problems": [p["field"] for p in problems]},
    )
    return error_response(
        422, "validation_error", "Request validation failed", {"fields": problems}
    )


async def handle_http_exception(request: Request, error: StarletteHTTPException):
    codes = {404: "not_found", 405: "method_not_allowed"}
    code = codes.get(error.status_code, "http_error")
    return error_response(error.status_code, code, str(error.detail))


async def handle_integrity_error(request: Request, error: IntegrityError):
    # The original statement and parameters stay in the log, never in the response.
    logger.warning(
        "integrity_error", extra={"path": request.url.path, "reason": str(error.orig)[:300]}
    )
    return error_response(
        409, "conflict", "The change conflicts with existing data (duplicate or still referenced)"
    )


async def handle_data_error(request: Request, error: DataError):
    logger.warning("data_error", extra={"path": request.url.path, "reason": str(error.orig)[:300]})
    return error_response(
        422, "value_out_of_range", "A value is outside the range the system can store"
    )


async def handle_operational_error(request: Request, error: OperationalError):
    logger.error("database_unavailable", extra={"path": request.url.path}, exc_info=error)
    return error_response(503, "database_unavailable", "The database is temporarily unavailable")


async def handle_unexpected_error(request: Request, error: Exception):
    logger.error("unhandled_exception", extra={"path": request.url.path}, exc_info=error)
    return error_response(500, "internal_error", "An unexpected error occurred")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(DataError, handle_data_error)
    app.add_exception_handler(OperationalError, handle_operational_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
