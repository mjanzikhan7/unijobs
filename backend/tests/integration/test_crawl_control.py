"""Pausing, resuming, cancelling and restarting a crawl run.

Control is cooperative, not preemptive. Fetching a live page mid-institution cannot be safely
interrupted without breaking the adapter contract - "never a partial list" - so a paused or
cancelled run only ever affects institutions that have not started yet. What already ran keeps
its real result; what has not is deferred or skipped.

The one invariant every test here ultimately protects is the closure safety rule: a job is only
ever closed on an ``OK`` outcome, so an institution skipped by cancellation must never look like
a successful crawl that legitimately found nothing.
"""

from __future__ import annotations

import pytest

from crawler.enums import CrawlLogLevel, CrawlOutcome, CrawlRunStatus
from crawler.models import CrawlLogEntry, CrawlRun, CrawlRunInstitution
from crawler.services import (
    InvalidRunTransition,
    NothingToRetry,
    RunAlreadyActive,
    cancel_run,
    log_event,
    pause_run,
    restart_run,
    resume_run,
    start_run,
)
from tests.factories import CrawlRunFactory, CrawlRunInstitutionFactory, InstitutionFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_real_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate restart_run() from a real crawl attempt.

    It dispatches the new run exactly like the API does; these tests assert the bookkeeping -
    scope resolution, status transitions - not a full crawl.
    """
    monkeypatch.setattr("crawler.tasks.dispatch_run_task.delay", lambda *args, **kwargs: None)


def test_pausing_a_running_run_marks_it_paused() -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    pause_run(run)

    run.refresh_from_db()
    assert run.status == CrawlRunStatus.PAUSED


def test_a_paused_run_still_holds_the_active_slot() -> None:
    """A paused run has not finished - a second crawl must still be refused."""
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)
    pause_run(run)

    with pytest.raises(RunAlreadyActive):
        start_run()


def test_pausing_a_run_that_is_not_running_is_refused() -> None:
    """Pausing a finished run would silently do nothing useful."""
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)

    with pytest.raises(InvalidRunTransition):
        pause_run(run)


def test_resuming_a_paused_run_marks_it_running() -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)

    resume_run(run)

    run.refresh_from_db()
    assert run.status == CrawlRunStatus.RUNNING


def test_resuming_a_run_that_is_not_paused_is_refused() -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    with pytest.raises(InvalidRunTransition):
        resume_run(run)


@pytest.mark.parametrize("status", [CrawlRunStatus.RUNNING, CrawlRunStatus.PAUSED])
def test_cancelling_a_live_run_marks_it_cancelled(status: CrawlRunStatus) -> None:
    """Cancel works from either RUNNING or PAUSED."""
    run = CrawlRunFactory(status=status)

    cancel_run(run)

    run.refresh_from_db()
    assert run.status == CrawlRunStatus.CANCELLED
    assert run.finished_at is not None


def test_cancelling_a_finished_run_is_refused() -> None:
    """There is nothing left to stop."""
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)

    with pytest.raises(InvalidRunTransition):
        cancel_run(run)


def test_a_cancelled_run_no_longer_holds_the_active_slot() -> None:
    """Cancelling must free the slot immediately so a new crawl can start."""
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    cancel_run(run)

    start_run()


def test_restart_all_starts_a_fresh_run_over_the_whole_estate() -> None:
    """A full restart is not scoped to whatever the original run covered."""
    InstitutionFactory.create_batch(3)
    original = CrawlRunFactory(status=CrawlRunStatus.CANCELLED, institution_ids=[])

    new_run = restart_run(original, scope="all")

    assert new_run.pk != original.pk
    assert new_run.status == CrawlRunStatus.RUNNING
    assert new_run.institutions_total == 3


def test_restart_failures_retries_only_institutions_that_were_not_ok() -> None:
    """The point of a targeted retry: don't re-hammer the ones that were fine."""
    ok_institution = InstitutionFactory()
    broken_institution = InstitutionFactory()
    unreached_institution = InstitutionFactory()
    original = CrawlRunFactory(
        status=CrawlRunStatus.CANCELLED,
        institution_ids=[ok_institution.pk, broken_institution.pk, unreached_institution.pk],
    )
    CrawlRunInstitutionFactory(run=original, institution=ok_institution, outcome=CrawlOutcome.OK)
    CrawlRunInstitutionFactory(
        run=original, institution=broken_institution, outcome=CrawlOutcome.TIMEOUT
    )

    new_run = restart_run(original, scope="failures")

    assert set(new_run.institution_ids) == {broken_institution.pk, unreached_institution.pk}
    assert new_run.institutions_total == 2


def test_restart_failures_with_nothing_to_retry_is_refused() -> None:
    """A run with every institution OK has nothing worth restarting."""
    institution = InstitutionFactory()
    original = CrawlRunFactory(status=CrawlRunStatus.COMPLETE, institution_ids=[institution.pk])
    CrawlRunInstitutionFactory(run=original, institution=institution, outcome=CrawlOutcome.OK)

    with pytest.raises(NothingToRetry):
        restart_run(original, scope="failures")


def test_restart_of_a_live_run_cancels_it_first() -> None:
    """Restarting mid-run does not leave two runs claiming the active slot."""
    InstitutionFactory.create_batch(2)
    original = CrawlRunFactory(status=CrawlRunStatus.PAUSED, institution_ids=[])

    restart_run(original, scope="all")

    original.refresh_from_db()
    assert original.status == CrawlRunStatus.CANCELLED


def test_restart_scoped_to_a_narrow_original_run_does_not_widen_to_the_whole_estate() -> None:
    """Restarting a `--slug`-scoped run must not silently crawl everyone else too."""
    scoped_institution = InstitutionFactory()
    InstitutionFactory()
    original = CrawlRunFactory(
        status=CrawlRunStatus.CANCELLED, institution_ids=[scoped_institution.pk]
    )

    new_run = restart_run(original, scope="all")

    assert new_run.institution_ids == [scoped_institution.pk]
    assert new_run.institutions_total == 1


def test_log_event_is_persisted_against_the_run() -> None:
    run = CrawlRunFactory()

    log_event(run, "started", level=CrawlLogLevel.INFO)

    entry = CrawlLogEntry.objects.get(run=run)
    assert entry.message == "started"
    assert entry.level == CrawlLogLevel.INFO


def test_log_event_records_the_institution_when_given_one() -> None:
    run = CrawlRunFactory()
    institution = InstitutionFactory()

    log_event(run, "crawled", institution=institution)

    entry = CrawlLogEntry.objects.get(run=run)
    assert entry.institution_id == institution.pk


def test_log_event_survives_the_institution_being_deleted() -> None:
    """Old log history must not vanish because an institution was later removed."""
    run = CrawlRunFactory()
    institution = InstitutionFactory()
    log_event(run, "crawled", institution=institution)

    institution.delete()

    entry = CrawlLogEntry.objects.get(run=run)
    assert entry.institution_id is None
    assert entry.message == "crawled"


def test_pause_writes_a_log_entry() -> None:
    """Control actions are themselves log-worthy events, not just crawl outcomes."""
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    pause_run(run)

    assert CrawlLogEntry.objects.filter(run=run, message__icontains="paused").exists()


def test_resume_writes_a_log_entry() -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)

    resume_run(run)

    assert CrawlLogEntry.objects.filter(run=run, message__icontains="resumed").exists()


def test_cancel_writes_a_log_entry() -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    cancel_run(run)

    assert CrawlLogEntry.objects.filter(run=run, message__icontains="cancelled").exists()


def test_await_runnable_returns_immediately_when_the_run_is_running() -> None:
    """The common case must not pay a polling cost."""
    from crawler.services import await_runnable

    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)
    calls: list[float] = []

    decision = await_runnable(run.pk, sleep=calls.append)

    assert decision == "proceed"
    assert calls == []


def test_await_runnable_returns_cancelled_immediately_without_waiting() -> None:
    """Cancellation must not make a not-yet-started institution wait around."""
    from crawler.services import await_runnable

    run = CrawlRunFactory(status=CrawlRunStatus.CANCELLED)
    calls: list[float] = []

    decision = await_runnable(run.pk, sleep=calls.append)

    assert decision == "cancelled"
    assert calls == []


def test_await_runnable_waits_while_paused_then_proceeds_once_resumed() -> None:
    """Resuming mid-wait must be picked up without the caller doing anything."""
    from crawler.services import await_runnable

    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)
    calls = 0

    def fake_sleep(seconds: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            CrawlRun.objects.filter(pk=run.pk).update(status=CrawlRunStatus.RUNNING)

    decision = await_runnable(run.pk, poll_seconds=0, sleep=fake_sleep)

    assert decision == "proceed"
    assert calls == 2


def test_await_runnable_waits_while_paused_then_sees_a_cancel() -> None:
    """Cancelling while paused must also be picked up mid-wait."""
    from crawler.services import await_runnable

    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)

    def fake_sleep(seconds: float) -> None:
        CrawlRun.objects.filter(pk=run.pk).update(status=CrawlRunStatus.CANCELLED)

    decision = await_runnable(run.pk, poll_seconds=0, sleep=fake_sleep)

    assert decision == "cancelled"


def test_await_runnable_gives_up_after_the_time_budget_rather_than_waiting_forever() -> None:
    """A pause that outlives the task's time budget must not hang the run forever.

    The task holding a worker slot has a soft time limit; waiting past it would just crash the
    task uncontrolled. Giving up cleanly and skipping the institution for this run - retriable
    afterwards via restart_run(scope="failures") - is the safer failure mode.
    """
    from crawler.services import await_runnable

    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)

    decision = await_runnable(
        run.pk, poll_seconds=0, max_wait_seconds=0, sleep=lambda seconds: None
    )

    assert decision == "cancelled"


def test_a_cancelled_run_skips_an_unstarted_institution_without_crawling_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The institution must never be fetched once its run is cancelled."""
    from crawler.tasks import crawl_institution_task

    institution = InstitutionFactory()
    run = CrawlRunFactory(status=CrawlRunStatus.CANCELLED)

    def _must_not_be_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("crawl_institution was called on a cancelled run")

    monkeypatch.setattr("crawler.tasks.crawl_institution", _must_not_be_called)

    result = crawl_institution_task.run(run.pk, institution.pk)

    assert result["outcome"] == CrawlOutcome.SKIPPED.value
    row = CrawlRunInstitution.objects.get(run=run, institution=institution)
    assert row.outcome == CrawlOutcome.SKIPPED
    assert row.permits_closure is False


def test_a_skipped_institution_never_permits_closure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The one invariant this whole feature must not be allowed to break."""
    from crawler.tasks import crawl_institution_task

    institution = InstitutionFactory()
    run = CrawlRunFactory(status=CrawlRunStatus.CANCELLED)
    monkeypatch.setattr(
        "crawler.tasks.crawl_institution",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    crawl_institution_task.run(run.pk, institution.pk)

    row = CrawlRunInstitution.objects.get(run=run, institution=institution)
    assert row.outcome not in {CrawlOutcome.OK}
    assert row.permits_closure is False
