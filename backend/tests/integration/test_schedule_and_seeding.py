"""The beat schedule across the BST/GMT boundary - plus seeding and the digest.

The time zone test matters more than it looks. A schedule set in July that moves by an hour in
November would run every crawl an hour early or late for five months, and nothing would warn us.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from crawler.enums import CrawlRunStatus
from crawler.models import CrawlRun
from crawler.services import sweep_stalled_runs
from institutions.models import Institution
from institutions.seeds.loader import seed_institutions
from jobs.digest import build_digest, send_digest_email
from jobs.enums import ApplicationStatus
from screening.enums import SponsorVerdict
from screening.models import InstitutionSponsorMatch, Ruleset
from screening.seeds.loader import seed_ruleset, seed_sponsor_matches, verdict_for
from tests.factories import (
    ApplicationFactory,
    CrawlRunFactory,
    JobFactory,
    SavedJobFactory,
    SavedSearchFactory,
    ScreeningFactory,
)

pytestmark = pytest.mark.django_db

LONDON = ZoneInfo("Europe/London")


def test_the_schedule_is_expressed_in_london_time() -> None:
    """UTC would drift by an hour every winter."""
    assert settings.CELERY_TIMEZONE == "Europe/London"


def test_celery_is_not_left_in_utc() -> None:
    """``CELERY_ENABLE_UTC`` must be off for the timezone to be honoured."""
    assert settings.CELERY_ENABLE_UTC is False


def test_the_scheduled_crawl_fires_three_times_a_day_evenly_spaced() -> None:
    schedule = settings.CELERY_BEAT_SCHEDULE["scheduled-crawl"]["schedule"]

    hours = sorted(schedule.hour)
    assert (hours, schedule.minute) == ([6, 14, 22], {0})
    gaps = [hours[1] - hours[0], hours[2] - hours[1], (hours[0] + 24) - hours[2]]
    assert gaps == [8, 8, 8]


FIVE_TO_SIX_LOCAL = [
    pytest.param("2026-07-15 04:55:00", id="BST"),
    pytest.param("2026-11-15 05:55:00", id="GMT"),
]

SIX_LOCAL = [
    pytest.param("2026-07-15 05:00:00", id="BST"),
    pytest.param("2026-11-15 06:00:00", id="GMT"),
]


@pytest.mark.parametrize("frozen_utc", FIVE_TO_SIX_LOCAL)
def test_the_next_firing_is_five_minutes_away_on_both_sides_of_the_clock_change(
    frozen_utc: str,
) -> None:
    """Five minutes to six, local, in July and in November."""
    schedule = settings.CELERY_BEAT_SCHEDULE["scheduled-crawl"]["schedule"]

    with freeze_time(frozen_utc):
        yesterdays_run = timezone.localtime(timezone.now()).replace(
            hour=6, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        seconds_until_next = schedule.is_due(yesterdays_run).next

    assert 0 < seconds_until_next <= 300


@pytest.mark.parametrize("frozen_utc", SIX_LOCAL)
def test_the_schedule_is_due_at_six_local_in_both_seasons(frozen_utc: str) -> None:
    """A schedule set in July must not fire at 05:00 in November."""
    schedule = settings.CELERY_BEAT_SCHEDULE["scheduled-crawl"]["schedule"]

    with freeze_time(frozen_utc):
        due = schedule.is_due(timezone.now() - timedelta(days=1)).is_due

    assert due is True


@pytest.mark.parametrize("frozen_utc", ["2026-07-15 05:00:00", "2026-11-15 06:00:00"])
def test_the_schedule_fires_at_the_same_local_hour_all_year(frozen_utc: str) -> None:
    """The same rule from the other side: the local hour is six in summer and in winter."""
    with freeze_time(frozen_utc):
        local_hour = timezone.localtime(timezone.now()).hour

    assert local_hour == 6


def test_a_scheduled_crawl_is_skipped_when_one_is_already_running() -> None:
    """UC-02 E1. Queueing it would produce two crawls back to back."""
    from crawler.tasks import scheduled_crawl

    CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    assert scheduled_crawl()["skipped"] is True


def test_a_skipped_scheduled_crawl_names_the_run_that_blocked_it() -> None:
    from crawler.tasks import scheduled_crawl

    active = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    assert scheduled_crawl()["active_run_id"] == active.pk


def test_a_run_whose_worker_stopped_is_marked_incomplete() -> None:
    """UC-01 E5. And an incomplete run never closes anything."""
    stale = timezone.now() - timedelta(minutes=settings.CRAWLER["RUN_STALE_AFTER_MINUTES"] + 10)
    CrawlRunFactory(status=CrawlRunStatus.RUNNING, heartbeat_at=stale, started_at=stale)

    sweep_stalled_runs()

    assert CrawlRun.objects.get().status == CrawlRunStatus.INCOMPLETE


def test_a_run_still_reporting_is_left_alone() -> None:
    CrawlRunFactory(status=CrawlRunStatus.RUNNING, heartbeat_at=timezone.now())

    sweep_stalled_runs()

    assert CrawlRun.objects.get().status == CrawlRunStatus.RUNNING


def test_an_incomplete_run_says_why_it_closed_nothing() -> None:
    stale = timezone.now() - timedelta(minutes=settings.CRAWLER["RUN_STALE_AFTER_MINUTES"] + 10)
    CrawlRunFactory(status=CrawlRunStatus.RUNNING, heartbeat_at=stale, started_at=stale)

    sweep_stalled_runs()

    assert "No jobs were closed" in CrawlRun.objects.get().error_detail


def test_seeding_loads_the_whole_estate() -> None:
    result = seed_institutions()

    assert result.created == Institution.objects.count() > 150


def test_every_seeded_institution_has_a_careers_url() -> None:
    """A crawlable estate is the point; an institution with no URL is dead weight."""
    seed_institutions()

    assert not Institution.objects.filter(careers_url="").exists()


def test_seeding_twice_changes_nothing_the_second_time() -> None:
    """``make seed`` twice is a no-op."""
    seed_institutions()

    second = seed_institutions()

    assert (second.created, second.updated) == (0, 0)


def test_seeding_does_not_undo_a_human_decision() -> None:
    """Re-seeding must not re-enable a portal somebody disabled for timing out."""
    seed_institutions()
    institution = Institution.objects.first()
    Institution.objects.filter(pk=institution.pk).update(
        crawl_enabled=False, adapter_override="JOBTRAIN"
    )

    seed_institutions()
    institution.refresh_from_db()

    assert (institution.crawl_enabled, institution.adapter_override) == (False, "JOBTRAIN")


def test_seeding_creates_the_ruleset() -> None:
    ruleset, created = seed_ruleset()

    assert created is True and ruleset.figures.count() == 10


def test_seeding_never_replaces_an_existing_ruleset(ruleset: Ruleset) -> None:
    """Replacing it in place would make every stored verdict inexplicable."""
    _, created = seed_ruleset()

    assert created is False


def test_the_seeded_ruleset_carries_the_verified_figures() -> None:
    ruleset, _ = seed_ruleset()

    assert ruleset.figure("soc_2134_going_rate") == 54700


def test_seeding_records_the_known_sponsor_matches() -> None:
    seed_institutions()

    counts = seed_sponsor_matches()

    assert counts["seeded"] > 150


def test_most_institutions_do_not_need_a_human_decision() -> None:
    """The review queue is for the handful that genuinely need looking at, not all 167."""
    seed_institutions()

    counts = seed_sponsor_matches()

    assert counts["needs_review"] < 20


def test_an_institution_on_the_register_is_confirmed() -> None:
    seed_institutions()
    seed_sponsor_matches()

    match = InstitutionSponsorMatch.objects.get(institution__slug="university-of-cambridge")

    assert match.verdict == SponsorVerdict.CONFIRMED


def test_a_confirmed_institution_carries_its_legal_name() -> None:
    seed_institutions()
    seed_sponsor_matches()

    match = InstitutionSponsorMatch.objects.get(institution__slug="university-of-cambridge")

    assert match.registered_legal_name == "The University of Cambridge"


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (
            {
                "register_status": "ON REGISTER",
                "routes": "Skilled Worker",
                "type_rating": "Worker (A rating)",
            },
            SponsorVerdict.CONFIRMED,
        ),
        (
            {
                "register_status": "ON REGISTER",
                "routes": "Skilled Worker",
                "type_rating": "Worker (B rating)",
            },
            SponsorVerdict.B_RATED,
        ),
        (
            {
                "register_status": "ON REGISTER",
                "routes": "Government Authorised Exchange",
                "type_rating": "Temporary Worker (A rating)",
            },
            SponsorVerdict.OTHER_ROUTE_ONLY,
        ),
        ({"register_status": "NOT FOUND"}, SponsorVerdict.NOT_FOUND),
        ({"register_status": "UNCONFIRMED"}, SponsorVerdict.NOT_FOUND),
        ({"register_status": "VIA PARENT"}, SponsorVerdict.NOT_FOUND),
    ],
)
def test_seed_register_status_maps_to_a_verdict(
    record: dict[str, str], expected: SponsorVerdict
) -> None:
    verdict, _ = verdict_for(record)

    assert verdict is expected


@pytest.mark.parametrize("status", ["UNCONFIRMED", "VIA PARENT", "NOT FOUND"])
def test_anything_not_squarely_on_the_register_goes_to_a_human(status: str) -> None:
    """Via-parent status needs someone to identify the parent. No matcher will guess UKRI."""
    _, needs_review = verdict_for({"register_status": status})

    assert needs_review is True


def test_nothing_is_sent_when_there_is_nothing_to_say(ruleset: Ruleset) -> None:
    """UC-10. An email that says "nothing today" teaches you to ignore the sender."""
    send_digest_email()

    assert mail.outbox == []


def test_the_digest_reports_a_saved_job_closing_soon(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory(closing_date=timezone.localdate() + timedelta(days=3))
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(job=job)

    content = build_digest(owner=user)

    assert len(content.closing_soon) == 1


def test_the_digest_ignores_a_saved_job_closing_far_away(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory(closing_date=timezone.localdate() + timedelta(days=90))
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(job=job)

    content = build_digest(owner=user)

    assert content.closing_soon == []


def test_closing_soon_items_are_ordered_by_closing_date(user: Any, ruleset: Ruleset) -> None:
    """UC-10. Ascending: Thursday's deadline goes above next Tuesday's."""
    later = JobFactory(closing_date=timezone.localdate() + timedelta(days=6))
    sooner = JobFactory(closing_date=timezone.localdate() + timedelta(days=2))
    for job in (later, sooner):
        ScreeningFactory(job=job, ruleset=ruleset)
        SavedJobFactory(job=job)

    content = build_digest(owner=user)

    assert content.closing_soon[0].pk == sooner.pk


def test_the_digest_reports_an_action_that_is_due(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    ApplicationFactory(
        job=job,
        status=ApplicationStatus.APPLIED,
        next_action="Chase HR",
        next_action_due=timezone.localdate(),
    )

    content = build_digest(owner=user)

    assert len(content.actions_due) == 1


def test_the_digest_is_sent_when_there_is_something_to_say(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory(closing_date=timezone.localdate() + timedelta(days=3))
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(job=job)

    send_digest_email()

    assert len(mail.outbox) == 1


def test_the_digest_names_the_job_closing_soon(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory(
        title="Research Software Engineer", closing_date=timezone.localdate() + timedelta(days=3)
    )
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(job=job)

    send_digest_email()

    assert "Research Software Engineer" in mail.outbox[0].body


def test_a_saved_search_contributes_its_new_matches(user: Any, ruleset: Ruleset) -> None:
    SavedSearchFactory(name="Everything", query="")
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)

    content = build_digest(owner=user)

    assert content.new_matches and content.new_matches[0][0] == "Everything"


@freeze_time("2026-08-23 06:30:00")
def test_the_digest_horizon_is_configurable(user: Any, ruleset: Ruleset) -> None:
    job = JobFactory(closing_date=date(2026, 8, 30))
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(job=job)

    content = build_digest(owner=user)

    assert len(content.closing_soon) == 1
