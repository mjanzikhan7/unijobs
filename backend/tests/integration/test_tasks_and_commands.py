"""Celery tasks and the management commands.

Tasks run eagerly here (``CELERY_TASK_ALWAYS_EAGER``), so orchestration can be asserted without
a worker.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone

from crawler.cache import DiskRawCache
from crawler.enums import CrawlRunStatus
from crawler.models import CrawlRun, RawResponse
from crawler.persistence import DatabaseResponseRecorder
from crawler.types import FetchResponse
from institutions.models import Institution
from jobs.enums import Discipline
from jobs.models import Application, Job
from screening.models import JobScreening, Ruleset
from tests.factories import (
    ApplicationFactory,
    CrawlRunFactory,
    InstitutionFactory,
    JobFactory,
)

pytestmark = pytest.mark.django_db


def test_a_fetch_is_recorded_against_its_cache_key(tmp_path: Any) -> None:
    cache = DiskRawCache(root=tmp_path)
    entry = cache.store("https://a.ac.uk/jobs", "<html>x</html>")
    response = FetchResponse(
        url="https://a.ac.uk/jobs",
        status_code=200,
        text="<html>x</html>",
        headers={"content-type": "text/html", "etag": '"abc"'},
    )

    DatabaseResponseRecorder().record(entry, response)

    assert RawResponse.objects.get().cache_key == entry.key


def test_a_recorded_etag_becomes_a_conditional_request_next_time(tmp_path: Any) -> None:
    """This is what turns an unchanged page into a 304 instead of a full download."""
    cache = DiskRawCache(root=tmp_path)
    entry = cache.store("https://a.ac.uk/jobs", "<html>x</html>")
    recorder = DatabaseResponseRecorder()
    recorder.record(
        entry,
        FetchResponse(
            url="https://a.ac.uk/jobs",
            status_code=200,
            text="<html>x</html>",
            headers={"etag": '"abc"', "last-modified": "Wed, 12 Aug 2026 09:00:00 GMT"},
        ),
    )

    assert recorder.validators_for("https://a.ac.uk/jobs") == (
        '"abc"',
        "Wed, 12 Aug 2026 09:00:00 GMT",
    )


def test_a_url_never_fetched_has_no_validators() -> None:
    assert DatabaseResponseRecorder().validators_for("https://a.ac.uk/jobs") == ("", "")


def test_recording_the_same_body_twice_keeps_one_row(tmp_path: Any) -> None:
    """Content-addressed keys: the nightly re-fetch of an unchanged page is one row."""
    cache = DiskRawCache(root=tmp_path)
    entry = cache.store("https://a.ac.uk/jobs", "<html>x</html>")
    response = FetchResponse(url="https://a.ac.uk/jobs", status_code=200, text="<html>x</html>")
    recorder = DatabaseResponseRecorder()

    recorder.record(entry, response)
    recorder.record(entry, response)

    assert RawResponse.objects.count() == 1


def test_the_stalled_run_sweep_task_marks_a_dead_run(ruleset: Ruleset) -> None:
    from crawler.tasks import sweep_stalled_runs_task

    stale = timezone.now() - timedelta(days=1)
    CrawlRunFactory(status=CrawlRunStatus.RUNNING, heartbeat_at=stale, started_at=stale)

    sweep_stalled_runs_task()

    assert CrawlRun.objects.get().status == CrawlRunStatus.INCOMPLETE


def test_the_prune_task_deletes_expired_cache_rows(ruleset: Ruleset) -> None:
    from crawler.tasks import prune_raw_cache

    RawResponse.objects.create(
        cache_key="old",
        url="https://a.ac.uk/jobs",
        sha256="x",
        storage_path="/tmp/old",
        fetched_at=timezone.now() - timedelta(days=200),
    )

    prune_raw_cache()

    assert RawResponse.objects.count() == 0


def test_the_prune_task_keeps_recent_cache_rows(ruleset: Ruleset) -> None:
    from crawler.tasks import prune_raw_cache

    RawResponse.objects.create(
        cache_key="fresh",
        url="https://a.ac.uk/jobs",
        sha256="x",
        storage_path="/tmp/fresh",
        fetched_at=timezone.now(),
    )

    prune_raw_cache()

    assert RawResponse.objects.count() == 1


def test_the_ghosting_task_flags_a_silent_application(ruleset: Ruleset) -> None:
    from jobs.tasks import flag_ghosted_applications

    ApplicationFactory(status="APPLIED", applied_at=timezone.now() - timedelta(days=30))

    flag_ghosted_applications()

    assert Application.objects.get().ghosted_flagged is True


def test_the_screening_task_screens_everything_unscreened(ruleset: Ruleset) -> None:
    from crawler.tasks import screen_run_changes

    run = CrawlRunFactory()
    JobFactory.create_batch(3)

    screen_run_changes(run.pk)

    assert JobScreening.objects.count() == 3


def test_the_screening_task_also_indexes_what_it_screens(ruleset: Ruleset) -> None:
    """A crawled job's ``search_vector`` had no other path to get built at all - this is it."""
    from crawler.tasks import screen_run_changes

    run = CrawlRunFactory()
    JobFactory.create_batch(3)

    screen_run_changes(run.pk)

    assert Job.objects.filter(search_vector__isnull=True).count() == 0


def test_the_search_vector_task_indexes_the_corpus(ruleset: Ruleset) -> None:
    from jobs.tasks import refresh_search_vectors_task

    JobFactory.create_batch(3)

    assert refresh_search_vectors_task() == 3


def test_dispatching_a_run_with_no_institutions_closes_it(ruleset: Ruleset) -> None:
    """A run over an empty estate finishes rather than hanging in RUNNING forever."""
    from crawler.tasks import dispatch_run

    run = CrawlRunFactory()

    dispatch_run(run)
    run.refresh_from_db()

    assert run.status == CrawlRunStatus.COMPLETE


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("JOBTRAIN", True),
        ("COREHR", False),
        ("COREHR_CATEGORISED", True),
        ("EPLOY", True),
        ("STONEFISH", False),
        ("WORKDAY", False),
        ("UNKNOWN", True),
    ],
)
def test_only_platforms_that_need_a_browser_get_one(platform: str, expected: bool) -> None:
    """Launching Chromium for a Stonefish tenant costs seconds and buys nothing."""
    from crawler.services import needs_browser

    institution = InstitutionFactory(platform=platform)

    assert needs_browser(institution) is expected


def test_an_adapter_override_decides_whether_a_browser_is_needed() -> None:
    from crawler.services import needs_browser

    institution = InstitutionFactory(platform="STONEFISH", adapter_override="JOBTRAIN")

    assert needs_browser(institution) is True


def test_seed_all_loads_the_estate() -> None:
    call_command("seed_all", stdout=StringIO())

    assert Institution.objects.count() > 150


def test_seed_all_is_safe_to_re_run() -> None:
    call_command("seed_all", stdout=StringIO())
    before = Institution.objects.count()

    call_command("seed_all", stdout=StringIO())

    assert Institution.objects.count() == before


def test_seed_all_reports_what_it_did() -> None:
    out = StringIO()

    call_command("seed_all", stdout=out)

    assert "institutions:" in out.getvalue()


def test_rescreen_recomputes_every_verdict(ruleset: Ruleset) -> None:
    JobFactory.create_batch(3)
    out = StringIO()

    call_command("rescreen", stdout=out)

    assert JobScreening.objects.count() == 3


def test_rescreen_reports_the_ruleset_it_used(ruleset: Ruleset) -> None:
    out = StringIO()

    call_command("rescreen", stdout=out)

    assert f"ruleset v{ruleset.version}" in out.getvalue()


def test_reclassify_disciplines_fixes_a_row_that_predates_the_taxonomy() -> None:
    job = JobFactory(title="Lecturer in Psychology", department="", category="")
    assert job.discipline == Discipline.OTHER
    out = StringIO()

    call_command("reclassify_disciplines", stdout=out)

    job.refresh_from_db()
    assert job.discipline == Discipline.PSYCHOLOGY


def test_reclassify_disciplines_reports_how_many_it_changed() -> None:
    JobFactory(title="Lecturer in Psychology", department="", category="")
    JobFactory(title="Front of House Assistant", department="", category="")
    out = StringIO()

    call_command("reclassify_disciplines", stdout=out)

    assert "reclassified 2 jobs" in out.getvalue()
    assert "1 disciplines changed" in out.getvalue()


def test_the_crawl_command_refuses_when_nothing_is_crawlable(ruleset: Ruleset) -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("crawl", stdout=StringIO())


def test_the_crawl_command_refuses_an_unknown_institution(ruleset: Ruleset) -> None:
    from django.core.management.base import CommandError

    InstitutionFactory()

    with pytest.raises(CommandError):
        call_command("crawl", "--slug", "not-a-real-place", stdout=StringIO())


def test_the_crawl_command_refuses_a_second_concurrent_run(ruleset: Ruleset) -> None:
    from django.core.management.base import CommandError

    InstitutionFactory()
    CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    with pytest.raises(CommandError):
        call_command("crawl", stdout=StringIO())


def test_refresh_sponsor_register_loads_a_local_csv(tmp_path: Any) -> None:
    csv_path = tmp_path / "register.csv"
    csv_path.write_text(
        "Organisation Name,Town/City,County,Type & Rating,Route\n"
        "The University of Cambridge,Cambridge,Cambridgeshire,Worker (A rating),Skilled Worker\n",
        encoding="utf-8",
    )
    out = StringIO()

    call_command("refresh_sponsor_register", "--file", str(csv_path), stdout=out)

    assert "loaded 1 register rows" in out.getvalue()


def test_refresh_sponsor_register_rejects_a_missing_file(tmp_path: Any) -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("refresh_sponsor_register", "--file", str(tmp_path / "nope.csv"))


def test_refresh_sponsor_register_needs_a_source() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("refresh_sponsor_register")
