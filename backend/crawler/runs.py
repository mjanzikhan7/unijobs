"""The life of a crawl run: create, pause, resume, cancel, restart and close.

The crawl of one institution is in ``crawler.services``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Literal

from django.db.models import F
from django.utils import timezone

from crawler.config import crawler_config
from crawler.enums import (
    ACTIVE_RUN_STATUSES,
    CrawlLogLevel,
    CrawlOutcome,
    CrawlRunStatus,
    CrawlTrigger,
)
from crawler.models import CrawlLogEntry, CrawlRun, CrawlRunInstitution
from institutions.models import Institution

logger = logging.getLogger(__name__)


class RunAlreadyActive(RuntimeError):
    """A crawl is already in progress. Concurrent runs are not permitted."""

    def __init__(self, run: CrawlRun) -> None:
        """Carry the active run so callers can link to it rather than just refusing."""
        super().__init__(f"Crawl run {run.pk} is already running")
        self.run = run


class InvalidRunTransition(RuntimeError):
    """A control action was tried from a status that does not allow it.

    We refuse loudly, instead of doing nothing, so the caller knows its idea of the state was wrong.
    """

    def __init__(self, run: CrawlRun, action: str) -> None:
        """Name the run, its status, and what was attempted."""
        super().__init__(f"Cannot {action} run {run.pk}: it is {run.status}")
        self.run = run
        self.action = action


class NothingToRetry(RuntimeError):
    """A ``restart_run(scope="failures")`` found no institution that needs retrying."""

    def __init__(self, run: CrawlRun) -> None:
        """Name the run that had nothing outstanding."""
        super().__init__(f"Run {run.pk} has no institutions needing a retry")
        self.run = run


def active_run() -> CrawlRun | None:
    """Return the run that holds the active slot: running or paused.

    A paused run is not finished. It must still stop a second crawl from starting.
    """
    return CrawlRun.objects.filter(status__in=ACTIVE_RUN_STATUSES).order_by("-started_at").first()


def log_event(
    run: CrawlRun,
    message: str,
    *,
    institution: Institution | None = None,
    level: CrawlLogLevel = CrawlLogLevel.INFO,
    extra: Mapping[str, object] | None = None,
) -> CrawlLogEntry:
    """Write one saved log line for a run.

    ``extra`` is a plain dict, not ``**kwargs``, so its keys can never clash with
    ``institution`` or ``level``.
    """
    return CrawlLogEntry.objects.create(
        run=run, institution=institution, level=level, message=message, extra=extra or {}
    )


_WARNING_OUTCOMES = frozenset(
    {
        CrawlOutcome.BLOCKED,
        CrawlOutcome.OFFLINE,
        CrawlOutcome.TIMEOUT,
        CrawlOutcome.PARSE_ERROR,
        CrawlOutcome.NO_ADAPTER,
    }
)


def _outcome_log_level(outcome: CrawlOutcome) -> CrawlLogLevel:
    """Map a crawl outcome onto how loudly the live log should show it."""
    return CrawlLogLevel.WARNING if outcome in _WARNING_OUTCOMES else CrawlLogLevel.INFO


def _institution_outcome_message(institution: Institution, row: CrawlRunInstitution) -> str:
    """One line summarising what happened, including the reason when it went wrong."""
    outcome = CrawlOutcome(row.outcome)
    summary = f"{institution.name}: {outcome.label} — {row.vacancies_found} found"
    if outcome == CrawlOutcome.OK:
        summary += f" (+{row.jobs_new} new, ~{row.jobs_updated} updated, -{row.jobs_closed} closed)"
    if row.error_detail:
        summary += f" — {row.error_detail}"
    return summary


def pause_run(run: CrawlRun) -> CrawlRun:
    """Pause a running crawl.

    Institutions that are already being fetched finish normally. Stopping a request half way could
    save a partial list. Only institutions that have not started yet wait, in
    :func:`await_runnable`.
    """
    if CrawlRunStatus(run.status) != CrawlRunStatus.RUNNING:
        raise InvalidRunTransition(run, "pause")
    run.status = CrawlRunStatus.PAUSED
    run.save(update_fields=["status"])
    log_event(run, f"Run {run.pk} paused.")
    return run


def resume_run(run: CrawlRun) -> CrawlRun:
    """Resume a paused crawl. Institutions waiting in :func:`await_runnable` pick this up."""
    if CrawlRunStatus(run.status) != CrawlRunStatus.PAUSED:
        raise InvalidRunTransition(run, "resume")
    run.status = CrawlRunStatus.RUNNING
    run.save(update_fields=["status"])
    log_event(run, f"Run {run.pk} resumed.")
    return run


def cancel_run(run: CrawlRun) -> CrawlRun:
    """Cancel a running or paused crawl.

    Institutions already being fetched finish and record their real outcome. All others record
    ``SKIPPED`` when their turn comes, never ``OK``, so no jobs are closed for them.
    """
    if CrawlRunStatus(run.status) not in ACTIVE_RUN_STATUSES:
        raise InvalidRunTransition(run, "cancel")
    run.status = CrawlRunStatus.CANCELLED
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "finished_at"])
    log_event(run, f"Run {run.pk} cancelled.")
    return run


def run_scope(run: CrawlRun) -> list[int]:
    """The institutions this run covers - the whole crawlable estate if it was unscoped."""
    return list(run.institution_ids) or list(
        Institution.objects.crawlable().values_list("pk", flat=True)
    )


def retriable_institution_ids(run: CrawlRun) -> list[int]:
    """Institutions in this run that did not come back ``OK``.

    Includes ones that a cancellation stopped before they started. They have no
    :class:`CrawlRunInstitution` row, which is why they still need a look.
    """
    ok_ids = set(
        CrawlRunInstitution.objects.filter(run=run, outcome=CrawlOutcome.OK).values_list(
            "institution_id", flat=True
        )
    )
    return [pk for pk in run_scope(run) if pk not in ok_ids]


def restart_run(run: CrawlRun, *, scope: str) -> CrawlRun:
    """Start a new run for ``"all"`` (the run's original institutions) or ``"failures"``.

    Never widens a limited run to every institution. Raises :class:`NothingToRetry` instead of
    starting a run with no institutions.
    """
    if run.is_active:
        cancel_run(run)

    if scope == "failures":
        institution_ids = retriable_institution_ids(run)
        if not institution_ids:
            raise NothingToRetry(run)
    else:
        institution_ids = run_scope(run)

    new_run = start_run(trigger=CrawlTrigger.MANUAL, institution_ids=institution_ids)
    log_event(new_run, f"Restarted from run {run.pk} (scope: {scope}).")

    from crawler.tasks import dispatch_run_task

    dispatch_run_task.delay(new_run.pk, institution_ids)
    return new_run


PAUSE_MAX_WAIT_SECONDS = 300.0
PAUSE_POLL_SECONDS = 5.0


def await_runnable(
    run_id: int,
    *,
    poll_seconds: float = PAUSE_POLL_SECONDS,
    max_wait_seconds: float = PAUSE_MAX_WAIT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> Literal["proceed", "cancelled"]:
    """Hold an institution task that has not started while its run is paused.

    Returns ``"proceed"`` once the run is running again, or ``"cancelled"`` if it was cancelled
    or the wait is longer than ``max_wait_seconds``. ``sleep`` can be replaced in tests.
    """
    waited = 0.0
    while True:
        status = CrawlRunStatus(CrawlRun.objects.values_list("status", flat=True).get(pk=run_id))
        if status == CrawlRunStatus.CANCELLED:
            return "cancelled"
        if status != CrawlRunStatus.PAUSED:
            return "proceed"
        if waited >= max_wait_seconds:
            return "cancelled"
        sleep(poll_seconds)
        waited += poll_seconds


def record_skipped_institution(
    run: CrawlRun, institution: Institution, *, reason: str
) -> CrawlRunInstitution:
    """Record an institution as skipped, without contacting it.

    Used when a run is cancelled, or a pause lasts too long, before this institution's turn.
    ``SKIPPED`` never closes jobs, so this institution's jobs are not touched.
    """
    row = CrawlRunInstitution.objects.create(
        run=run,
        institution=institution,
        outcome=CrawlOutcome.SKIPPED,
        error_detail=reason,
        finished_at=timezone.now(),
    )
    CrawlRun.objects.filter(pk=run.pk).update(institutions_done=F("institutions_done") + 1)
    log_event(run, reason, institution=institution, level=CrawlLogLevel.WARNING)
    return row


def start_run(
    *, trigger: CrawlTrigger = CrawlTrigger.MANUAL, institution_ids: list[int] | None = None
) -> CrawlRun:
    """Create a run and count the work it will do.

    Returns straight away. Celery does the work, so ``POST /api/crawl-runs/`` stays fast for any
    number of institutions.
    """
    existing = active_run()
    if existing is not None:
        raise RunAlreadyActive(existing)

    queryset = Institution.objects.crawlable()
    if institution_ids:
        queryset = queryset.filter(pk__in=institution_ids)

    resolved_ids = list(queryset.values_list("pk", flat=True))
    scope_to_store = resolved_ids if institution_ids else []

    run = CrawlRun.objects.create(
        trigger=trigger, institutions_total=len(resolved_ids), institution_ids=scope_to_store
    )
    logger.info("started crawl run %s over %s institutions", run.pk, run.institutions_total)
    return run


def finalise_run(run: CrawlRun) -> CrawlRun:
    """Close a run and add up its totals.

    A run the user cancelled stays ``CANCELLED``.
    """
    results = list(run.institution_results.all())
    run.institutions_done = len(results)
    run.jobs_new = sum(result.jobs_new for result in results)
    run.jobs_updated = sum(result.jobs_updated for result in results)
    run.jobs_closed = sum(result.jobs_closed for result in results)
    if CrawlRunStatus(run.status) == CrawlRunStatus.RUNNING:
        run.status = CrawlRunStatus.COMPLETE
    run.finished_at = run.finished_at or timezone.now()
    run.save()
    log_event(run, f"Run {run.pk} finished ({run.status}).", extra=run_totals(run))
    return run


def run_totals(run: CrawlRun) -> dict[str, int]:
    """The numbers shown in a run summary."""
    return {
        "institutions_total": run.institutions_total,
        "institutions_done": run.institutions_done,
        "jobs_new": run.jobs_new,
        "jobs_updated": run.jobs_updated,
        "jobs_closed": run.jobs_closed,
    }


def sweep_stalled_runs() -> int:
    """Mark runs whose worker died as ``INCOMPLETE``.

    An incomplete run never closes jobs. Institutions it did not reach simply have no result row.
    """
    cutoff = timezone.now() - timedelta(minutes=crawler_config().run_stale_after_minutes)
    stalled = CrawlRun.objects.filter(status=CrawlRunStatus.RUNNING, heartbeat_at__lt=cutoff)
    count = stalled.count()
    stalled.update(
        status=CrawlRunStatus.INCOMPLETE,
        finished_at=timezone.now(),
        error_detail="Worker stopped responding; run marked incomplete. No jobs were closed.",
    )
    return count
