"""Structured logs with a request id.

Every request gets an id: the one the gateway sends in ``X-Request-ID``, or a new one. The id
goes into every log line written while the request runs, and back to the client in the
response header, so one problem can be followed from nginx to Django to the log store.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime

from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "X-Request-ID"

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def current_request_id() -> str:
    """Return the id of the request being handled, or ``-`` outside a request."""
    return _request_id.get()


class RequestIdMiddleware:
    """Give every request an id, and return it in the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Keep the next handler."""
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Set the id for this request, then pass the request on."""
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class RequestIdFilter(logging.Filter):
    """Add the current request id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach ``request_id`` and keep the record."""
        record.request_id = current_request_id()
        return True


_STANDARD_FIELDS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, ready for a log store such as Loki or Elasticsearch."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as a JSON string."""
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_FIELDS:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)
