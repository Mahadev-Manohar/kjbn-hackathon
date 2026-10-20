"""Structured JSON logging with a per-request correlation id."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
# Domain identifiers (farmer_id, crop_id, ...) attached to every log line of the current request.
log_context_var: ContextVar[dict] = ContextVar("log_context")


def bind_log_context(**identifiers: object) -> None:
    """Add identifiers to the current request's log context. No-op outside a request."""
    try:
        log_context_var.get().update(identifiers)
    except LookupError:
        pass


# Attributes every LogRecord has; anything else was passed through `extra=` and is emitted.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "context"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        payload.update(getattr(record, "context", {}))
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _install_context_record_factory() -> None:
    """Stamp the request's domain identifiers onto each record as it is created."""
    previous = logging.getLogRecordFactory()

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        record.context = dict(log_context_var.get({}))
        return record

    logging.setLogRecordFactory(factory)


def configure_logging(level: str) -> None:
    _install_context_record_factory()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Uvicorn's access log duplicates our request log line.
    logging.getLogger("uvicorn.access").disabled = True
