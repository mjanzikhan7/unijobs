"""Crawl orchestration.

One institution per unit of work, each with its own error handling. One institution failing
must never stop the run. With 167 of them, one expired certificate cannot be allowed to end
the whole crawl.

The steps for each institution are always:

1. fetch the careers page and choose an adapter. If the page is blocked, or no adapter
   matches, try once more with a browser, because a JavaScript-only site looks unsupported
   until it is rendered;
2. list vacancies, catching only typed :class:`~crawler.exceptions.AdapterError`;
3. map the outcome. **Only** ``OK`` lets the differ close anything;
4. save new and changed jobs, write revisions, close what really disappeared;
5. screen whatever changed.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from django.db.models import F
from django.utils import timezone

from crawler.adapter_resolution import institution_ref, probe_portal, resolve_adapter
from crawler.browser import PlaywrightSession
from crawler.config import crawler_config
from crawler.crawl import crawl_one
from crawler.differ import diff_vacancies
from crawler.enums import CrawlOutcome
from crawler.institution_profile import enrich_institution_description
from crawler.models import CrawlRun, CrawlRunInstitution
from crawler.runs import (
    InvalidRunTransition,
    NothingToRetry,
    RunAlreadyActive,
    active_run,
    await_runnable,
    cancel_run,
    finalise_run,
    log_event,
    pause_run,
    record_skipped_institution,
    restart_run,
    resume_run,
    retriable_institution_ids,
    run_scope,
    run_totals,
    start_run,
    sweep_stalled_runs,
)
from crawler.runs import _institution_outcome_message as _institution_outcome_message
from crawler.runs import _outcome_log_level as _outcome_log_level
from crawler.sync import apply_diff, existing_jobs_for
from crawler.transport import build_browser_session, build_http_client, needs_browser
from crawler.types import HttpClient
from institutions.models import Institution

__all__ = [
    "InvalidRunTransition",
    "NothingToRetry",
    "RunAlreadyActive",
    "active_run",
    "apply_diff",
    "await_runnable",
    "build_browser_session",
    "build_http_client",
    "cancel_run",
    "crawl_institution",
    "crawl_one",
    "existing_jobs_for",
    "finalise_run",
    "institution_ref",
    "log_event",
    "needs_browser",
    "pause_run",
    "probe_portal",
    "record_skipped_institution",
    "resolve_adapter",
    "restart_run",
    "resume_run",
    "retriable_institution_ids",
    "run_scope",
    "run_totals",
    "start_run",
    "sweep_stalled_runs",
]


def crawl_institution(
    run: CrawlRun,
    institution: Institution,
    *,
    http: HttpClient,
    browser_factory: Callable[[], PlaywrightSession | None] | None = None,
) -> CrawlRunInstitution:
    """Crawl one institution, record the outcome, and apply the changes.

    The closing rule lives in :func:`crawler.differ.diff_vacancies`, not in an if-statement here.
    This takes a browser factory, not an open session, and closes the browser before any database
    call, because the database cannot be used while Playwright's event loop is running.
    """
    log_event(run, f"Crawling {institution.name}…", institution=institution)

    started = time.monotonic()
    browser = browser_factory() if browser_factory is not None else None
    try:
        result = crawl_one(
            institution,
            http=http,
            browser=browser,
            max_detail_fetches=crawler_config().max_detail_fetches_per_institution,
        )
    finally:
        if browser is not None:
            browser.stop()

    previous = (
        CrawlRunInstitution.objects.filter(institution=institution)
        .exclude(run=run)
        .order_by("-started_at")
        .values_list("vacancies_found", flat=True)
        .first()
    )

    diff = diff_vacancies(
        fetched=result.vacancies,
        existing=existing_jobs_for(institution),
        outcome=result.outcome,
    )
    created, updated, closed = apply_diff(run, institution, diff)

    if result.outcome == CrawlOutcome.OK and institution.platform != result.platform:
        Institution.objects.filter(pk=institution.pk).update(platform=result.platform.value)

    if enrich_institution_description(institution, http=http):
        Institution.objects.filter(pk=institution.pk, description="").update(
            description=institution.description
        )

    row = CrawlRunInstitution.objects.create(
        run=run,
        institution=institution,
        adapter=result.adapter,
        outcome=result.outcome,
        strategy=result.strategy,
        fallback_fired=result.fallback_fired,
        vacancies_found=len(result.vacancies),
        previous_vacancies_found=previous,
        jobs_new=created,
        jobs_updated=updated,
        jobs_closed=closed,
        duration_ms=int((time.monotonic() - started) * 1000),
        error_class=result.error_class,
        error_detail=(result.error_detail or diff.closure_skipped_reason)[:5000],
        raw_cache_keys=list(result.cache_keys),
        finished_at=timezone.now(),
    )

    log_event(
        run,
        _institution_outcome_message(institution, row),
        institution=institution,
        level=_outcome_log_level(result.outcome),
        extra={"outcome": result.outcome.value, "vacancies_found": len(result.vacancies)},
    )

    CrawlRun.objects.filter(pk=run.pk).update(
        heartbeat_at=timezone.now(), institutions_done=F("institutions_done") + 1
    )
    return row
