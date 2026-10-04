"""Recording what people do, and reading back what it adds up to.

Two properties matter more than the counts themselves: recording must never be able to break the
action it is recording, and the dashboards must answer questions about *candidates* rather than
about a candidate.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.enums import EventKind
from analytics.models import AnalyticsEvent, SearchTermDaily
from analytics.services import (
    candidate_overview,
    prune_events,
    rebuild_search_terms,
    record,
    word_cloud,
)
from screening.models import Ruleset
from tests.factories import InstitutionFactory, JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def job(ruleset: Ruleset) -> Any:
    vacancy = JobFactory(category="Academic")
    ScreeningFactory(job=vacancy, ruleset=ruleset)
    return vacancy


def test_a_search_is_recorded(candidate_client: APIClient, job: Any) -> None:
    candidate_client.get("/api/jobs/?q=research+software+engineer")

    event = AnalyticsEvent.objects.get(kind=EventKind.SEARCH)
    assert event.query == "research software engineer"
    assert event.actor_role == "CANDIDATE"


def test_a_search_records_how_many_results_it_found(candidate_client: APIClient, job: Any) -> None:
    """The most actionable number on the dashboard is "searches that found nothing"."""
    candidate_client.get("/api/jobs/?q=zzzznothingmatchesthis")

    assert AnalyticsEvent.objects.get(kind=EventKind.SEARCH).result_count == 0


def test_viewing_a_job_is_recorded_with_its_dimensions(
    candidate_client: APIClient, job: Any
) -> None:
    """Nation and category are copied at write time: the job may change or be deleted later."""
    candidate_client.get(f"/api/jobs/{job.pk}/")

    event = AnalyticsEvent.objects.get(kind=EventKind.JOB_VIEW)
    assert event.job == job
    assert (event.institution, event.category) == (job.institution, "Academic")


def test_saving_and_unsaving_are_both_recorded(candidate_client: APIClient, job: Any) -> None:
    """A save that does not stick is a signal too."""
    created = candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")
    candidate_client.delete(f"/api/saved-jobs/{created.json()['id']}/")

    kinds = set(AnalyticsEvent.objects.values_list("kind", flat=True))
    assert {str(EventKind.JOB_SAVE), str(EventKind.JOB_UNSAVE)} <= kinds


def test_an_application_is_recorded(candidate_client: APIClient, job: Any) -> None:
    candidate_client.post("/api/applications/", {"job": job.pk}, format="json")

    assert AnalyticsEvent.objects.filter(kind=EventKind.APPLY, job=job).exists()


def test_operator_activity_is_recorded_but_not_counted_as_demand(
    auth_client: APIClient, job: Any
) -> None:
    """An administrator debugging an institution must not become its busiest week."""
    auth_client.get(f"/api/jobs/{job.pk}/")

    assert AnalyticsEvent.objects.filter(actor_role="ADMIN").exists()
    assert not AnalyticsEvent.objects.by_candidates().exists()


def test_a_failing_recorder_does_not_fail_the_search(candidate_client: APIClient, job: Any) -> None:
    """A search that 500s because analytics broke is a worse outcome than a missing row."""
    with patch(
        "analytics.services.AnalyticsEvent.objects.create", side_effect=RuntimeError("boom")
    ):
        response = candidate_client.get("/api/jobs/?q=python")

    assert response.status_code == 200
    assert not AnalyticsEvent.objects.exists()


def test_record_returns_none_rather_than_raising() -> None:
    with patch(
        "analytics.services.AnalyticsEvent.objects.create", side_effect=RuntimeError("boom")
    ):
        assert record(EventKind.SEARCH, query="python") is None


def test_a_cv_upload_records_counts_not_content(candidate_client: APIClient) -> None:
    """The extracted text is the most personal thing in the database. It stays out of here."""
    record(EventKind.CV_UPLOAD, skills_found=3, content_type="pdf")

    event = AnalyticsEvent.objects.get(kind=EventKind.CV_UPLOAD)
    assert event.payload == {"skills_found": 3, "content_type": "pdf"}


def test_deleting_a_user_keeps_the_aggregate_but_drops_the_link(
    candidate_client: APIClient, candidate_user: Any, job: Any
) -> None:
    """SET_NULL, not CASCADE: closing an account must not rewrite last month's trend."""
    candidate_client.get("/api/jobs/?q=python")
    candidate_user.delete()

    event = AnalyticsEvent.objects.get(kind=EventKind.SEARCH)
    assert event.actor is None
    assert event.query == "python"


def test_deleting_a_job_keeps_the_event(candidate_client: APIClient, job: Any) -> None:
    candidate_client.get(f"/api/jobs/{job.pk}/")
    job.delete()

    assert AnalyticsEvent.objects.filter(kind=EventKind.JOB_VIEW).exists()


def test_the_rollup_counts_terms_for_a_day(candidate_user: Any) -> None:
    for query in ["python django", "python", "welding"]:
        record(EventKind.SEARCH, actor=candidate_user, query=query)

    rebuild_search_terms(timezone.localdate())

    counts = dict(SearchTermDaily.objects.values_list("term", "occurrences"))
    assert counts["python"] == 2
    assert counts["welding"] == 1


def test_the_rollup_counts_distinct_searchers(
    candidate_user: Any, second_candidate_user: Any
) -> None:
    """A term ten people used is a trend; a term one person used ten times is a person."""
    record(EventKind.SEARCH, actor=candidate_user, query="python")
    record(EventKind.SEARCH, actor=candidate_user, query="python")
    record(EventKind.SEARCH, actor=second_candidate_user, query="python")

    rebuild_search_terms(timezone.localdate())

    row = SearchTermDaily.objects.get(term="python")
    assert (row.occurrences, row.searchers) == (3, 2)


def test_rebuilding_twice_does_not_double_count(candidate_user: Any) -> None:
    """Idempotent, so an overlapping or retried run is free."""
    record(EventKind.SEARCH, actor=candidate_user, query="python")

    rebuild_search_terms(timezone.localdate())
    rebuild_search_terms(timezone.localdate())

    assert SearchTermDaily.objects.get(term="python").occurrences == 1


def test_operator_searches_stay_out_of_the_cloud(user: Any, candidate_user: Any) -> None:
    record(EventKind.SEARCH, actor=user, query="debugging stonefish")
    record(EventKind.SEARCH, actor=candidate_user, query="python")

    rebuild_search_terms(timezone.localdate())

    assert set(SearchTermDaily.objects.values_list("term", flat=True)) == {"python"}


def test_the_word_cloud_sums_across_days(candidate_user: Any) -> None:
    """One row per (day, term), so counting rows would rank a rare-but-persistent term first."""
    today = timezone.localdate()
    SearchTermDaily.objects.create(day=today, term="python", occurrences=10, searchers=4)
    SearchTermDaily.objects.create(
        day=today - timedelta(days=1), term="python", occurrences=5, searchers=2
    )
    SearchTermDaily.objects.create(
        day=today - timedelta(days=1), term="welding", occurrences=1, searchers=1
    )

    cloud = word_cloud(days=7)

    assert cloud[0] == {"term": "python", "occurrences": 15, "searchers": 6}


def test_pruning_drops_old_events_and_keeps_recent_ones(candidate_user: Any) -> None:
    old = record(EventKind.SEARCH, actor=candidate_user, query="old")
    AnalyticsEvent.objects.filter(pk=old.pk).update(
        occurred_at=timezone.now() - timedelta(days=400)
    )
    record(EventKind.SEARCH, actor=candidate_user, query="recent")

    assert prune_events(older_than_days=365) == 1
    assert list(AnalyticsEvent.objects.values_list("query", flat=True)) == ["recent"]


def test_pruning_leaves_the_rollups_alone(candidate_user: Any) -> None:
    """Long-range charts keep working without the row saying which person did what."""
    SearchTermDaily.objects.create(
        day=timezone.localdate() - timedelta(days=400), term="python", occurrences=9, searchers=3
    )

    prune_events(older_than_days=365)

    assert SearchTermDaily.objects.count() == 1


def test_the_overview_reports_the_funnel(candidate_client: APIClient, job: Any) -> None:
    candidate_client.get(f"/api/jobs/{job.pk}/")
    candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    overview = candidate_overview(days=30)

    assert overview["job_views"] == 1
    assert overview["saves"] == 1
    assert overview["view_to_save_rate"] == 1.0


def test_the_overview_survives_an_empty_platform() -> None:
    """Every ratio divides by something that may legitimately be zero."""
    overview = candidate_overview(days=30)

    assert overview["searches"] == 0
    assert overview["empty_search_rate"] == 0.0
    assert overview["save_to_apply_rate"] == 0.0


def test_the_dashboard_endpoints_are_staff_only(candidate_client: APIClient) -> None:
    for path in ("candidates", "institutions", "search-cloud"):
        assert candidate_client.get(f"/api/insights/{path}/").status_code == 403


def test_an_operator_reads_the_dashboards(auth_client: APIClient, job: Any) -> None:
    for path in ("candidates", "institutions", "search-cloud"):
        assert auth_client.get(f"/api/insights/{path}/").status_code == 200


def test_the_dashboards_return_aggregates_not_rows(
    auth_client: APIClient, candidate_client: APIClient, candidate_user: Any, job: Any
) -> None:
    """An operator screen is not the place to put "what is this named person looking for"."""
    candidate_user.username = "zzidentifiablepersonzz"
    candidate_user.email = "zzidentifiablepersonzz@example.test"
    candidate_user.save(update_fields=["username", "email"])
    candidate_client.get("/api/jobs/?q=python")

    serialised = str(auth_client.get("/api/insights/candidates/").json())

    assert candidate_user.username not in serialised
    assert candidate_user.email not in serialised
    assert "active_candidates" in serialised


def test_the_window_is_clamped(auth_client: APIClient) -> None:
    """One request must not ask the database to scan everything ever recorded."""

    def days_for(value: str) -> int:
        body = auth_client.get(f"/api/insights/candidates/?days={value}").json()
        return int(body["overview"]["days"])

    assert days_for("99999") == 365
    assert days_for("nonsense") == 30
    assert days_for("-5") == 1


def test_the_trends_table_is_not_capped_at_twenty(auth_client: APIClient, ruleset: Ruleset) -> None:
    """The estate is hundreds of institutions, and this table is meant to be all of them.

    A default of twenty made the page look like it had stopped loading - the count said 132 and
    the table showed 20, with nothing explaining the gap.
    """
    for _ in range(25):
        vacancy = JobFactory(institution=InstitutionFactory())
        ScreeningFactory(job=vacancy, ruleset=ruleset)

    body = auth_client.get("/api/insights/institutions/").json()

    assert len(body["institutions"]) == 25


def test_the_row_limit_is_clamped(auth_client: APIClient) -> None:
    """The parameter is a client's; an unbounded one asks the server to serialise everything."""
    assert auth_client.get("/api/insights/institutions/?limit=99999").json()["limit"] == 500
    assert auth_client.get("/api/insights/institutions/?limit=nonsense").json()["limit"] == 500
    assert auth_client.get("/api/insights/candidates/?limit=-4").json()["limit"] == 1


def test_the_candidate_lists_stay_top_n(auth_client: APIClient, candidate_user: Any) -> None:
    """These are genuinely "the busiest twenty", not a truncated everything."""
    for index in range(30):
        record(EventKind.SEARCH, actor=candidate_user, query=f"query number {index}")

    body = auth_client.get("/api/insights/candidates/").json()

    assert len(body["top_searches"]) == 20
    assert body["limit"] == 20


def test_a_caller_can_ask_for_more_rows(auth_client: APIClient, candidate_user: Any) -> None:
    for index in range(30):
        record(EventKind.SEARCH, actor=candidate_user, query=f"query number {index}")

    body = auth_client.get("/api/insights/candidates/?limit=30").json()

    assert len(body["top_searches"]) == 30


def test_institution_posting_trends_come_from_the_jobs_themselves(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """No second copy of a number the database already holds - two copies can disagree."""
    institution = InstitutionFactory()
    for _ in range(3):
        vacancy = JobFactory(institution=institution)
        ScreeningFactory(job=vacancy, ruleset=ruleset)

    body = auth_client.get("/api/insights/institutions/").json()

    row = next(r for r in body["institutions"] if r["slug"] == institution.slug)
    assert row["posted"] == 3
