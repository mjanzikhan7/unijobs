"""API error handling.

Every error leaves in one shape, so the frontend has one thing to show:
``{"detail": str, "code": str, "extra": {...}}``.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ConflictError(drf_exceptions.APIException):
    """This request would repeat something that is already running.

    Used by ``POST /api/crawl-runs/`` when a run is active. ``extra`` holds the active run's id, so
    the UI can link to it.
    """

    status_code = 409
    default_detail = "That is already in progress."
    default_code = "conflict"

    def __init__(self, detail: str | None = None, extra: dict[str, Any] | None = None) -> None:
        """Attach structured context to a conflict."""
        super().__init__(detail)
        self.extra = extra or {}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Normalise every API error into one envelope."""
    if isinstance(exc, DjangoValidationError):
        exc = drf_exceptions.ValidationError(detail=list(exc.messages))

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    code = getattr(exc, "default_code", "error")
    if isinstance(detail, dict) and "detail" in detail:
        message = str(detail["detail"])
        code = getattr(detail["detail"], "code", code)
        payload: dict[str, Any] = {"detail": message, "code": code}
    else:
        payload = {"detail": "Validation failed.", "code": "invalid", "errors": detail}

    extra = getattr(exc, "extra", None)
    if extra:
        payload["extra"] = extra

    response.data = payload
    return response
