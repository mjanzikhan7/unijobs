"""Scheduled analytics work: yesterday's rollup, and forgetting old rows."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="analytics.tasks.roll_up_search_terms")
def roll_up_search_terms(days_back: int = 2) -> int:
    """Rebuild the term counts for the last two days.

    Two days, so a failed run or a restart does not leave a gap. Rebuilding is safe to repeat.
    """
    from datetime import timedelta

    from django.utils import timezone

    from analytics.services import rebuild_search_terms

    today = timezone.localdate()
    return sum(rebuild_search_terms(today - timedelta(days=offset)) for offset in range(days_back))


@shared_task(name="analytics.tasks.prune_analytics_events")
def prune_analytics_events() -> int:
    """Drop events past the retention window. The daily rollups survive."""
    from django.conf import settings

    from analytics.services import prune_events

    return prune_events(older_than_days=settings.ANALYTICS_RETENTION_DAYS)
