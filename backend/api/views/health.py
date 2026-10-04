"""Liveness and readiness.

No sign-in needed. The container health check calls it, and it has no token.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Report whether the process can serve traffic."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        summary="Health check",
        responses={200: dict, 503: dict},
        auth=[],
    )
    def get(self, request: Request) -> Response:
        """Return ``ok`` when the database answers, ``degraded`` when it does not."""
        checks: dict[str, Any] = {"database": False}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                checks["database"] = cursor.fetchone() == (1,)
        except Exception:
            logger.exception("health check could not reach the database")

        healthy = checks["database"]
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
