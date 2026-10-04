"""Recording what happened, and reading back the totals.

Two rules for recording:

* **Never break the action being recorded.** A failed analytics write must not fail a search.
  Every recorder catches and logs its errors.
* **Never record content.** Search terms and ids, yes. CV text, names or email addresses, no.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.services import role_of
from analytics.domain import count_terms, normalise_query, terms_in
from analytics.enums import EventKind
from analytics.models import AnalyticsEvent, SearchTermDaily
from institutions.models import Institution
from jobs.enums import JobStatus
from jobs.models import Job

logger = logging.getLogger(__name__)


def record(
    kind: EventKind,
    *,
    actor: AbstractBaseUser | AnonymousUser | None = None,
    job: Job | None = None,
    institution: Institution | None = None,
    query: str = "",
    result_count: int | None = None,
    **payload: Any,
) -> AnalyticsEvent | None:
    """Write one event, or give up quietly.

    Returns the row, or ``None`` if it could not be written. The person whose action was being
    recorded never sees a failure here.
    """
    try:
        resolved_institution = institution or (job.institution if job else None)
        return AnalyticsEvent.objects.create(
            kind=str(kind),
            actor=actor if (actor is not None and actor.is_authenticated) else None,
            actor_role=str(role_of(actor) or ""),
            job=job,
            institution=resolved_institution,
            nation=resolved_institution.nation if resolved_institution else "",
            category=(job.category if job else ""),
            query=normalise_query(query),
            result_count=result_count,
            payload=payload,
        )
    except Exception:
        logger.exception("could not record a %s event", kind)
        return None


@transaction.atomic
def rebuild_search_terms(day: date) -> int:
    """Recalculate one day's term counts from the events table.

    The day is cleared and rebuilt, so running it twice gives the same answer, not double.
    """
    searches = list(
        AnalyticsEvent.objects.of_kind(EventKind.SEARCH)
        .by_candidates()
        .filter(occurred_at__date=day)
        .exclude(query="")
        .values_list("query", "actor_id")
    )

    counts = count_terms([query for query, _ in searches])

    searchers: dict[str, set[int | None]] = {}
    for query, actor_id in searches:
        for term in terms_in(query):
            searchers.setdefault(term, set()).add(actor_id)

    SearchTermDaily.objects.filter(day=day).delete()
    SearchTermDaily.objects.bulk_create(
        [
            SearchTermDaily(
                day=day,
                term=term,
                occurrences=occurrences,
                searchers=len(searchers.get(term, ())),
            )
            for term, occurrences in counts.items()
        ],
        batch_size=500,
    )
    return len(counts)


def prune_events(*, older_than_days: int) -> int:
    """Delete events older than the retention period, and return how many.

    Old usage data stops being useful long before it stops being a risk. The daily totals are kept,
    so long-term charts still work without knowing who did what.
    """
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = AnalyticsEvent.objects.filter(occurred_at__lt=cutoff).delete()
    return deleted


def _window(days: int) -> Any:
    """The start of a rolling window of ``days``."""
    return timezone.now() - timedelta(days=days)


def candidate_overview(*, days: int = 30) -> dict[str, Any]:
    """Headline counts for the candidate-activity dashboard."""
    events = AnalyticsEvent.objects.by_candidates().since(_window(days))
    per_kind = dict(
        events.values_list("kind").annotate(total=Count("id")).values_list("kind", "total")
    )

    searches = events.of_kind(EventKind.SEARCH)
    total_searches = searches.count()
    empty_searches = searches.filter(result_count=0).count()

    return {
        "days": days,
        "active_candidates": events.exclude(actor__isnull=True)
        .values("actor_id")
        .distinct()
        .count(),
        "searches": total_searches,
        "searches_with_no_results": empty_searches,
        "empty_search_rate": round(empty_searches / total_searches, 3) if total_searches else 0.0,
        "job_views": per_kind.get(str(EventKind.JOB_VIEW), 0),
        "saves": per_kind.get(str(EventKind.JOB_SAVE), 0),
        "applications": per_kind.get(str(EventKind.APPLY), 0),
        "cv_uploads": per_kind.get(str(EventKind.CV_UPLOAD), 0),
        "view_to_save_rate": _rate(
            per_kind.get(str(EventKind.JOB_SAVE), 0), per_kind.get(str(EventKind.JOB_VIEW), 0)
        ),
        "save_to_apply_rate": _rate(
            per_kind.get(str(EventKind.APPLY), 0), per_kind.get(str(EventKind.JOB_SAVE), 0)
        ),
    }


def _rate(numerator: int, denominator: int) -> float:
    """A ratio, or zero rather than a division error when nothing happened yet."""
    return round(numerator / denominator, 3) if denominator else 0.0


def activity_by_day(*, days: int = 30) -> list[dict[str, Any]]:
    """Daily counts per event kind, for the trend chart."""
    rows = (
        AnalyticsEvent.objects.by_candidates()
        .since(_window(days))
        .annotate(day=TruncDate("occurred_at"))
        .values("day", "kind")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    by_day: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = row["day"].isoformat()
        entry = by_day.setdefault(day, {"day": day})
        entry[row["kind"]] = row["total"]
    return list(by_day.values())


def word_cloud(*, days: int = 30, limit: int = 80) -> list[dict[str, Any]]:
    """The most searched terms, read from the daily totals.

    Summed, not counted. Counting rows would rank a term searched once on thirty days above one
    searched a thousand times yesterday.
    """
    rows = (
        SearchTermDaily.objects.filter(day__gte=_window(days).date())
        .values("term")
        .annotate(occurrences=Sum("occurrences"), searchers=Sum("searchers"))
        .order_by("-occurrences")[:limit]
    )
    return [
        {"term": row["term"], "occurrences": row["occurrences"], "searchers": row["searchers"]}
        for row in rows
    ]


def top_searches(*, days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
    """Whole search strings, not terms - what people actually typed."""
    rows = (
        AnalyticsEvent.objects.of_kind(EventKind.SEARCH)
        .by_candidates()
        .since(_window(days))
        .exclude(query="")
        .values("query")
        .annotate(
            searches=Count("id"),
            searchers=Count("actor_id", distinct=True),
            found_nothing=Count("id", filter=Q(result_count=0)),
        )
        .order_by("-searches")[:limit]
    )
    return list(rows)


def demand_by_dimension(field: str, *, days: int = 30, limit: int = 15) -> list[dict[str, Any]]:
    """What candidates engage with, grouped by one stored field.

    Counts views, saves and applications, not searches. A search shows what someone hoped to
    find. Engagement shows what they found worth their time.
    """
    rows = (
        AnalyticsEvent.objects.by_candidates()
        .of_kind(EventKind.JOB_VIEW, EventKind.JOB_SAVE, EventKind.APPLY)
        .since(_window(days))
        .exclude(**{f"{field}": ""})
        .values(field)
        .annotate(
            views=Count("id", filter=Q(kind=str(EventKind.JOB_VIEW))),
            saves=Count("id", filter=Q(kind=str(EventKind.JOB_SAVE))),
            applications=Count("id", filter=Q(kind=str(EventKind.APPLY))),
            total=Count("id"),
        )
        .order_by("-total")[:limit]
    )
    return [{"value": row[field], **{k: v for k, v in row.items() if k != field}} for row in rows]


def institution_engagement(*, days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
    """Which institutions candidates are actually looking at."""
    rows = (
        AnalyticsEvent.objects.by_candidates()
        .since(_window(days))
        .exclude(institution__isnull=True)
        .values("institution__slug", "institution__name")
        .annotate(
            views=Count("id", filter=Q(kind=str(EventKind.JOB_VIEW))),
            saves=Count("id", filter=Q(kind=str(EventKind.JOB_SAVE))),
            applications=Count("id", filter=Q(kind=str(EventKind.APPLY))),
            total=Count("id"),
        )
        .order_by("-total")[:limit]
    )
    return [
        {
            "slug": row["institution__slug"],
            "name": row["institution__name"],
            "views": row["views"],
            "saves": row["saves"],
            "applications": row["applications"],
            "total": row["total"],
        }
        for row in rows
    ]


def posting_trends(*, days: int = 90, limit: int = 20) -> dict[str, Any]:
    """How institutions are posting, read from the jobs themselves.

    `first_seen_at` already says when a vacancy appeared. Saving a second copy as events could give
    two numbers that disagree.
    """
    since = _window(days)
    per_institution = (
        Job.objects.filter(first_seen_at__gte=since)
        .values("institution__slug", "institution__name")
        .annotate(
            posted=Count("id"),
            open_now=Count("id", filter=Q(status=JobStatus.OPEN)),
            closed=Count("id", filter=Q(status=JobStatus.DISAPPEARED)),
            withdrawn=Count("id", filter=Q(status=JobStatus.WITHDRAWN)),
        )
        .order_by("-posted")[:limit]
    )

    by_day = (
        Job.objects.filter(first_seen_at__gte=since)
        .annotate(day=TruncDate("first_seen_at"))
        .values("day")
        .annotate(posted=Count("id"))
        .order_by("day")
    )

    return {
        "days": days,
        "institutions": [
            {
                "slug": row["institution__slug"],
                "name": row["institution__name"],
                "posted": row["posted"],
                "open_now": row["open_now"],
                "closed": row["closed"],
                "withdrawn": row["withdrawn"],
            }
            for row in per_institution
        ],
        "by_day": [{"day": row["day"].isoformat(), "posted": row["posted"]} for row in by_day],
        "totals": {
            "posted": Job.objects.filter(first_seen_at__gte=since).count(),
            "open_now": Job.objects.filter(status=JobStatus.OPEN).count(),
            "institutions_posting": Job.objects.filter(first_seen_at__gte=since)
            .values("institution_id")
            .distinct()
            .count(),
        },
    }
