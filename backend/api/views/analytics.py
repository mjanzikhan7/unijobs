"""The insight dashboards.

**Totals only.** Each endpoint answers "what are candidates doing", never "what did this
candidate do". Row by row, the same data would show what one named person searched for and
when. An operator screen should not show that.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics import services
from api.permissions import STAFF

MAX_DAYS = 365
DEFAULT_DAYS = 30

MAX_ROWS = 500
DEFAULT_ROWS = 20


def _days(request: Request) -> int:
    """Read the window from the query string, clamped to something answerable."""
    try:
        requested = int(request.query_params.get("days", DEFAULT_DAYS))
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return max(1, min(requested, MAX_DAYS))


def _limit(request: Request, default: int = DEFAULT_ROWS) -> int:
    """Read a row limit from the query string, clamped to something serialisable."""
    try:
        requested = int(request.query_params.get("limit", default))
    except (TypeError, ValueError):
        return default
    return max(1, min(requested, MAX_ROWS))


_DAYS_PARAM = OpenApiParameter(
    "days",
    description=f"Rolling window, 1 to {MAX_DAYS} days. Default {DEFAULT_DAYS}.",
    required=False,
)

_LIMIT_PARAM = OpenApiParameter(
    "limit",
    description=f"Rows per list, 1 to {MAX_ROWS}. Default {DEFAULT_ROWS}.",
    required=False,
)


class CandidateInsightsView(APIView):
    """What candidates are searching for, looking at, saving and applying to."""

    required_roles = STAFF

    @extend_schema(parameters=[_DAYS_PARAM, _LIMIT_PARAM], responses={200: dict})
    def get(self, request: Request) -> Response:
        """Return the candidate activity dashboard, as totals only.

        The lists are top-N, for example "the twenty most common searches". The screen says so, so a
        short list is not read as a complete one.
        """
        days = _days(request)
        limit = _limit(request)
        return Response(
            {
                "days": days,
                "limit": limit,
                "overview": services.candidate_overview(days=days),
                "by_day": services.activity_by_day(days=days),
                "top_searches": services.top_searches(days=days, limit=limit),
                "by_nation": services.demand_by_dimension("nation", days=days, limit=limit),
                "by_category": services.demand_by_dimension("category", days=days, limit=limit),
                "institutions": services.institution_engagement(days=days, limit=limit),
            }
        )


class SearchCloudView(APIView):
    """The word cloud."""

    required_roles = STAFF

    @extend_schema(parameters=[_DAYS_PARAM], responses={200: dict})
    def get(self, request: Request) -> Response:
        """Return term weights, read from the daily rollup rather than the fact table."""
        days = _days(request)
        terms = services.word_cloud(days=days)
        return Response(
            {
                "days": days,
                "max_occurrences": max((row["occurrences"] for row in terms), default=0),
                "terms": terms,
            }
        )


class InstitutionInsightsView(APIView):
    """How the estate is posting, and which parts of it candidates engage with."""

    required_roles = STAFF

    @extend_schema(parameters=[_DAYS_PARAM, _LIMIT_PARAM], responses={200: dict})
    def get(self, request: Request) -> Response:
        """Return posting trends next to usage, so supply and demand appear together.

        This list should cover every institution, not the busiest twenty, so the default is higher.
        It is still under the ceiling.
        """
        days = _days(request)
        limit = _limit(request, default=MAX_ROWS)
        trends: dict[str, Any] = services.posting_trends(days=days, limit=limit)
        trends["limit"] = limit
        trends["engagement"] = services.institution_engagement(days=days, limit=limit)
        return Response(trends)
