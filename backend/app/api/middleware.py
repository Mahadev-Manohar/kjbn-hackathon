"""Request correlation id and one structured log line per request (no bodies, no secrets)."""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.api.errors import handle_unexpected_error
from app.core.logging import log_context_var, request_id_var

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 64


def _request_id_from(request: Request) -> str:
    supplied = request.headers.get(REQUEST_ID_HEADER, "")
    # Only trust short, printable client ids; anything else would pollute the logs.
    if supplied.isprintable() and 0 < len(supplied) <= MAX_REQUEST_ID_LENGTH:
        return supplied
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_id_from(request)
        token = request_id_var.set(request_id)
        context_token = log_context_var.set({})
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception as error:  # last resort: keep the id and shape on a 500
                response = await handle_unexpected_error(request, error)
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_var.reset(token)
            log_context_var.reset(context_token)
