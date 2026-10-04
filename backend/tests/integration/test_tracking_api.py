"""Saved jobs, the application pipeline and saved searches.

The pipeline's job is to record *when* things happened, not just what state they are in. That is
what makes "how long do these employers take to reply" answerable later.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from jobs.enums import GHOSTED_AFTER_DAYS, ApplicationStatus
from jobs.models import Application, ApplicationStatusEvent, SavedJob
from jobs.services import flag_ghosted, transition_application
from screening.models import Ruleset
from tests.factories import ApplicationFactory, JobFactory, SavedJobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


def test_a_job_can_be_saved(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    assert response.status_code == 201


def test_saving_the_same_job_twice_is_refused(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    auth_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    response = auth_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    assert response.status_code == 400


def test_saved_jobs_are_ordered_by_closing_date(auth_client: APIClient, ruleset: Ruleset) -> None:
    """UC-05: the one closing on Thursday matters more than the one closing next month."""
    soon = JobFactory(closing_date=timezone.localdate() + timedelta(days=2))
    later = JobFactory(closing_date=timezone.localdate() + timedelta(days=60))
    for job in (later, soon):
        ScreeningFactory(job=job, ruleset=ruleset)
        SavedJobFactory(job=job)

    response = auth_client.get("/api/saved-jobs/")

    assert response.json()["results"][0]["job"] == soon.pk


def test_a_saved_job_can_be_tagged(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.post(
        "/api/saved-jobs/", {"job": job.pk, "tags": ["shortlist", "russell-group"]}, format="json"
    )

    assert response.json()["tags"] == ["shortlist", "russell-group"]


def test_a_saved_job_can_be_removed(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    saved = SavedJobFactory(job=job)

    auth_client.delete(f"/api/saved-jobs/{saved.pk}/")

    assert SavedJob.objects.count() == 0


def test_the_board_returns_every_column_in_order(auth_client: APIClient, ruleset: Ruleset) -> None:
    response = auth_client.get("/api/applications/board/")

    assert [column["status"] for column in response.json()["columns"]] == [
        "FOUND",
        "READY",
        "APPLIED",
        "ACKNOWLEDGED",
        "INTERVIEW",
        "OFFER",
        "REJECTED",
        "GHOSTED",
    ]


def test_an_application_appears_in_its_column(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    ApplicationFactory(job=job, status=ApplicationStatus.APPLIED)

    response = auth_client.get("/api/applications/board/")
    applied = next(c for c in response.json()["columns"] if c["status"] == "APPLIED")

    assert len(applied["applications"]) == 1


def test_moving_a_card_records_the_transition(auth_client: APIClient, ruleset: Ruleset) -> None:
    """UC-06: timestamps are what make response-rate analysis possible later."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job)

    auth_client.post(
        f"/api/applications/{application.pk}/move/", {"status": "APPLIED"}, format="json"
    )

    assert ApplicationStatusEvent.objects.filter(to_status="APPLIED").count() == 1


def test_a_transition_records_where_it_came_from(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job, status=ApplicationStatus.READY)

    auth_client.post(
        f"/api/applications/{application.pk}/move/", {"status": "APPLIED"}, format="json"
    )

    assert ApplicationStatusEvent.objects.get().from_status == "READY"


def test_moving_to_applied_stamps_the_application_date(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job)

    auth_client.post(
        f"/api/applications/{application.pk}/move/", {"status": "APPLIED"}, format="json"
    )
    application.refresh_from_db()

    assert application.applied_at is not None


def test_moving_to_an_acknowledgement_stamps_the_response_date(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job, status=ApplicationStatus.APPLIED)

    auth_client.post(
        f"/api/applications/{application.pk}/move/", {"status": "ACKNOWLEDGED"}, format="json"
    )
    application.refresh_from_db()

    assert application.response_at is not None


def test_moving_to_the_same_column_records_nothing(ruleset: Ruleset) -> None:
    """A drag that lands where it started is not a transition."""
    application = ApplicationFactory(status=ApplicationStatus.APPLIED)

    transition_application(application, to_status=ApplicationStatus.APPLIED)

    assert ApplicationStatusEvent.objects.count() == 0


def test_an_unknown_status_is_rejected(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job)

    response = auth_client.post(
        f"/api/applications/{application.pk}/move/", {"status": "NONSENSE"}, format="json"
    )

    assert response.status_code == 400


def test_a_next_action_and_due_date_can_be_set(auth_client: APIClient, ruleset: Ruleset) -> None:
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    application = ApplicationFactory(job=job)

    auth_client.patch(
        f"/api/applications/{application.pk}/",
        {"next_action": "Chase HR", "next_action_due": "2026-09-15"},
        format="json",
    )
    application.refresh_from_db()

    assert application.next_action == "Chase HR"


def test_an_application_untouched_past_the_window_is_flagged(ruleset: Ruleset) -> None:
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=GHOSTED_AFTER_DAYS + 1),
    )

    flag_ghosted()

    assert Application.objects.get().ghosted_flagged is True


def test_a_flagged_application_is_not_moved(ruleset: Ruleset) -> None:
    """The candidate decides when to give up on an employer, not a cron job."""
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=GHOSTED_AFTER_DAYS + 1),
    )

    flag_ghosted()

    assert Application.objects.get().status == ApplicationStatus.APPLIED


def test_an_application_inside_the_window_is_not_flagged(ruleset: Ruleset) -> None:
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=GHOSTED_AFTER_DAYS - 1),
    )

    flag_ghosted()

    assert Application.objects.get().ghosted_flagged is False


def test_an_application_exactly_on_the_boundary_is_flagged(ruleset: Ruleset) -> None:
    """Boundary values on every threshold: one below, exactly on, one above."""
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=GHOSTED_AFTER_DAYS),
    )

    flag_ghosted()

    assert Application.objects.get().ghosted_flagged is True


def test_an_application_that_got_a_reply_is_never_flagged(ruleset: Ruleset) -> None:
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=60),
        response_at=timezone.now() - timedelta(days=30),
    )

    flag_ghosted()

    assert Application.objects.get().ghosted_flagged is False


def test_a_late_reply_clears_the_ghosted_flag(ruleset: Ruleset) -> None:
    """Employers do sometimes reply after five weeks."""
    application = ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=60),
        ghosted_flagged=True,
    )

    transition_application(application, to_status=ApplicationStatus.INTERVIEW)

    assert Application.objects.get().ghosted_flagged is False


def test_a_search_can_be_saved(auth_client: APIClient, ruleset: Ruleset) -> None:
    response = auth_client.post(
        "/api/saved-searches/",
        {"name": "Sponsorable RSE roles", "query": "sponsorable=true&q=research+software"},
        format="json",
    )

    assert response.status_code == 201


def test_a_saved_search_stores_the_query_string_verbatim(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """So a saved search and a bookmarked URL can never drift apart."""
    query = "sponsorable=true&min_fitness=70&nation=SCOTLAND"

    response = auth_client.post(
        "/api/saved-searches/", {"name": "Scotland", "query": query}, format="json"
    )

    assert response.json()["query"] == query


def test_a_saved_search_feeds_the_digest_by_default(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    response = auth_client.post(
        "/api/saved-searches/", {"name": "Everything", "query": ""}, format="json"
    )

    assert response.json()["digest_enabled"] is True


@freeze_time("2026-08-23 09:00:00")
def test_ghosting_is_evaluated_against_a_passed_in_clock(ruleset: Ruleset) -> None:
    """No sleeps: freezegun for time, and the rule takes the clock as an argument."""
    ApplicationFactory(
        status=ApplicationStatus.APPLIED,
        applied_at=timezone.now() - timedelta(days=GHOSTED_AFTER_DAYS + 1),
    )

    flagged = flag_ghosted(now=timezone.now())

    assert flagged == 1
