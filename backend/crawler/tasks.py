"""Celery tasks for crawling.

One task per institution, each with its own error handling. A task that fails does not
affect the rest of the run.

The scheduled crawl *skips* when a run is already active. Queueing it would give two crawls
back to back, which is impolite to the universities and pointless.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from celery import chord, shared_task

from crawler.enums import CrawlTrigger
from crawler.models import CrawlRun
from crawler.services import (
    RunAlreadyActive,
    active_run,
    await_runnable,
    build_browser_session,
    build_http_client,
    crawl_institution,
    finalise_run,
    needs_browser,
    record_skipped_institution,
    start_run,
    sweep_stalled_runs,
)
from institutions.models import Institution

logger = logging.getLogger(__name__)


@shared_task(name="crawler.tasks.scheduled_crawl")
def scheduled_crawl() -> dict[str, Any]:
    """The scheduled run, three times a day (Europe/London): 06:00, 14:00 and 22:00.

    Skipped and logged when a run is already active. Never queued behind it.
    """
    try:
        run = start_run(trigger=CrawlTrigger.SCHEDULED)
    except RunAlreadyActive as exc:
        logger.info("scheduled crawl skipped; run %s is already active", exc.run.pk)
        return {"skipped": True, "active_run_id": exc.run.pk}

    dispatch_run(run)
    return {"skipped": False, "run_id": run.pk}


@shared_task(name="crawler.tasks.dispatch_run")
def dispatch_run_task(run_id: int, institution_ids: list[int] | None = None) -> int:
    """Fan a run out over its institutions."""
    run = CrawlRun.objects.get(pk=run_id)
    dispatch_run(run, institution_ids)
    return run.pk


def dispatch_run(run: CrawlRun, institution_ids: list[int] | None = None) -> None:
    """Queue one task per institution, then a callback to close the run."""
    queryset = Institution.objects.crawlable()
    if institution_ids:
        queryset = queryset.filter(pk__in=institution_ids)

    ids = list(queryset.values_list("pk", flat=True))
    if not ids:
        finalise_run(run)
        return

    chord([crawl_institution_task.s(run.pk, institution_id) for institution_id in ids])(
        finalise_run_task.s(run.pk)
    )


@shared_task(
    name="crawler.tasks.crawl_institution",
    bind=True,
    max_retries=0,
    soft_time_limit=600,
)
def crawl_institution_task(self: Any, run_id: int, institution_id: int) -> dict[str, Any]:
    """Crawl one institution.

    Retries happen inside the HTTP client, not at task level. Pause and cancel are checked before
    any network work.
    """
    run = CrawlRun.objects.get(pk=run_id)
    institution = Institution.objects.get(pk=institution_id)

    if await_runnable(run_id) == "cancelled":
        row = record_skipped_institution(
            run, institution, reason="Skipped: run was cancelled or the pause was not lifted."
        )
        return {
            "institution_id": institution_id,
            "outcome": row.outcome,
            "vacancies_found": 0,
        }

    http = build_http_client()
    browser_factory = (
        partial(build_browser_session, before_navigation=http.prepare_navigation)
        if needs_browser(institution)
        else None
    )
    try:
        result = crawl_institution(run, institution, http=http, browser_factory=browser_factory)
    finally:
        http.close()

    return {
        "institution_id": institution_id,
        "outcome": result.outcome,
        "vacancies_found": result.vacancies_found,
    }


@shared_task(name="crawler.tasks.finalise_run")
def finalise_run_task(results: list[dict[str, Any]], run_id: int) -> dict[str, Any]:
    """Close a run once every institution task has reported, and screen what changed."""
    run = CrawlRun.objects.get(pk=run_id)
    finalise_run(run)
    screen_run_changes.delay(run_id)
    return {"run_id": run_id, "institutions": len(results)}


@shared_task(name="crawler.tasks.screen_run_changes")
def screen_run_changes(run_id: int) -> dict[str, int]:
    """Screen every job this run created or changed, and refresh its search index.

    The index refresh is done here so a crawled job can be found as soon as screening ends, just
    like a manually added one.
    """
    from jobs.models import Job
    from jobs.services import refresh_search_vectors
    from screening.services import screen_jobs

    changed_job_ids = set(
        Job.objects.filter(revisions__crawl_run_id=run_id).values_list("pk", flat=True)
    )
    run = CrawlRun.objects.get(pk=run_id)
    new_job_ids = set(
        Job.objects.filter(
            institution__crawl_results__run=run, first_seen_at__gte=run.started_at
        ).values_list("pk", flat=True)
    )
    unscreened_ids = set(Job.objects.filter(screening__isnull=True).values_list("pk", flat=True))

    target = changed_job_ids | new_job_ids | unscreened_ids
    refresh_search_vectors(Job.objects.filter(pk__in=target))
    return screen_jobs(Job.objects.filter(pk__in=target))


@shared_task(name="crawler.tasks.screen_unscreened_jobs")
def screen_unscreened_jobs() -> dict[str, int]:
    """Screen every job that has no verdict yet, and refresh its search index.

    A crawl screens its jobs when the run finishes. If the run stops early (a restart, a
    worker that died), its new jobs wait here. They are hidden from search until screened.
    """
    from jobs.models import Job
    from jobs.services import refresh_search_vectors
    from screening.services import screen_jobs

    unscreened = Job.objects.filter(screening__isnull=True)
    if not unscreened.exists():
        return {"screened": 0, "changed": 0}
    ids = list(unscreened.values_list("pk", flat=True))
    refresh_search_vectors(Job.objects.filter(pk__in=ids))
    return screen_jobs(Job.objects.filter(pk__in=ids))


@shared_task(name="crawler.tasks.sweep_stalled_runs")
def sweep_stalled_runs_task() -> int:
    """Mark runs whose worker died as incomplete."""
    return sweep_stalled_runs()


@shared_task(name="crawler.tasks.prune_raw_cache")
def prune_raw_cache() -> int:
    """Delete cached bodies older than the configured TTL."""
    from datetime import timedelta

    from django.utils import timezone

    from crawler.cache import DiskRawCache
    from crawler.config import crawler_config
    from crawler.models import RawResponse

    config = crawler_config()
    removed = DiskRawCache(root=config.raw_cache_dir).prune(
        older_than_days=config.raw_cache_ttl_days
    )
    cutoff = timezone.now() - timedelta(days=config.raw_cache_ttl_days)
    RawResponse.objects.filter(fetched_at__lt=cutoff).delete()
    return removed


@shared_task(name="crawler.tasks.crawl_now")
def crawl_now(institution_ids: list[int] | None = None) -> dict[str, Any]:
    """Start a manual run from the CLI or the API and fan it out."""
    run = start_run(trigger=CrawlTrigger.MANUAL, institution_ids=institution_ids)
    dispatch_run(run, institution_ids)
    return {"run_id": run.pk}


def current_run_id() -> int | None:
    """The active run's id, for the API's 409 response."""
    run = active_run()
    return run.pk if run else None
