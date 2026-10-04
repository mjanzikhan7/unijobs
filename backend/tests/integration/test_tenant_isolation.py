"""One candidate must never see, or touch, another candidate's rows.

Parameterised over every owned endpoint rather than written out per resource, so adding a fifth
owned model means adding one line here - and forgetting to means a visible gap in this list
rather than a silent leak in production.

The detail assertions expect **404, not 403**. A 403 on someone else's id confirms the row
exists, which is itself a disclosure; filtering at the queryset makes it indistinguishable from
a row that was never there.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from jobs.models import SavedJob, SavedSearch
from screening.models import CandidateProfile, Ruleset
from tests.factories import (
    ApplicationFactory,
    CandidateProfileFactory,
    JobFactory,
    SavedJobFactory,
    SavedSearchFactory,
    ScreeningFactory,
)

pytestmark = pytest.mark.django_db


def _make_rows(owner: Any, ruleset: Ruleset) -> dict[str, Any]:
    """Give one user a row in every owned model."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    return {
        "saved-jobs": SavedJobFactory(owner=owner, job=job),
        "applications": ApplicationFactory(owner=owner, job=job),
        "saved-searches": SavedSearchFactory(owner=owner, name=f"{owner.username} search"),
        "profiles": CandidateProfileFactory(owner=owner),
    }


_ENDPOINTS = ("saved-jobs", "applications", "saved-searches", "profiles")


@pytest.fixture
def rows(candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset) -> dict[str, Any]:
    """A row in every owned model, for each of two unrelated candidates."""
    return {
        "mine": _make_rows(candidate_user, ruleset),
        "theirs": _make_rows(second_candidate_user, ruleset),
    }


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_a_list_shows_only_your_own_rows(
    candidate_client: APIClient, rows: dict[str, Any], endpoint: str
) -> None:
    response = candidate_client.get(f"/api/{endpoint}/")

    results = response.json()["results"]
    assert [row["id"] for row in results] == [rows["mine"][endpoint].pk]


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_another_users_row_is_not_found(
    candidate_client: APIClient, rows: dict[str, Any], endpoint: str
) -> None:
    theirs = rows["theirs"][endpoint]

    assert candidate_client.get(f"/api/{endpoint}/{theirs.pk}/").status_code == 404


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_another_users_row_cannot_be_patched(
    candidate_client: APIClient, rows: dict[str, Any], endpoint: str
) -> None:
    theirs = rows["theirs"][endpoint]

    response = candidate_client.patch(f"/api/{endpoint}/{theirs.pk}/", {}, format="json")

    assert response.status_code == 404


@pytest.mark.parametrize("endpoint", _ENDPOINTS)
def test_another_users_row_cannot_be_deleted(
    candidate_client: APIClient, rows: dict[str, Any], endpoint: str
) -> None:
    theirs = rows["theirs"][endpoint]

    assert candidate_client.delete(f"/api/{endpoint}/{theirs.pk}/").status_code == 404


def test_a_created_row_belongs_to_the_caller_not_the_payload(
    candidate_client: APIClient, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """Ownership comes from the token, so naming someone else in the body changes nothing."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)

    response = candidate_client.post(
        "/api/saved-jobs/", {"job": job.pk, "owner": second_candidate_user.pk}, format="json"
    )

    assert response.status_code == 201
    assert SavedJob.objects.get(pk=response.json()["id"]).owner.username == "candidate"


def test_two_candidates_can_save_the_same_job(
    candidate_client: APIClient, second_candidate_client: APIClient, ruleset: Ruleset
) -> None:
    """The old OneToOne made this a 400. It is ordinary behaviour, not a conflict."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)

    first = candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")
    second = second_candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    assert (first.status_code, second.status_code) == (201, 201)
    assert SavedJob.objects.filter(job=job).count() == 2


def test_saving_the_same_job_twice_is_still_refused_for_one_owner(
    candidate_client: APIClient, ruleset: Ruleset
) -> None:
    """Per-owner uniqueness survives - and returns 400, not a 500 from the database."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    response = candidate_client.post("/api/saved-jobs/", {"job": job.pk}, format="json")

    assert response.status_code == 400


def test_two_candidates_can_name_a_search_the_same_thing(
    candidate_client: APIClient, second_candidate_client: APIClient
) -> None:
    """`name` was globally unique, which is only defensible with one account."""
    payload = {"name": "Lecturer roles", "query": "sponsorable=true"}

    first = candidate_client.post("/api/saved-searches/", payload, format="json")
    second = second_candidate_client.post("/api/saved-searches/", payload, format="json")

    assert (first.status_code, second.status_code) == (201, 201)
    assert SavedSearch.objects.filter(name="Lecturer roles").count() == 2


def test_two_candidates_can_each_hold_an_active_profile(
    candidate_user: Any, second_candidate_user: Any
) -> None:
    """The old constraint was global; a second candidate's profile hit an IntegrityError."""
    CandidateProfileFactory(owner=candidate_user, is_active=True)
    CandidateProfileFactory(owner=second_candidate_user, is_active=True)

    assert CandidateProfile.objects.filter(is_active=True).count() == 2


def test_the_job_list_does_not_report_another_users_save(
    candidate_client: APIClient, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """`is_saved` was an unscoped EXISTS - it answered "did anyone save this"."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(owner=second_candidate_user, job=job)

    response = candidate_client.get("/api/jobs/")

    assert response.json()["results"][0]["is_saved"] is False


def test_the_job_detail_does_not_leak_another_users_application_id(
    candidate_client: APIClient, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """The worst of the three: the leaked id was a handle you could then PATCH."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    theirs = ApplicationFactory(owner=second_candidate_user, job=job)

    body = candidate_client.get(f"/api/jobs/{job.pk}/").json()

    assert body["application_id"] is None
    assert candidate_client.get(f"/api/applications/{theirs.pk}/").status_code == 404


def test_the_pipeline_board_shows_only_your_own_statuses(
    candidate_client: APIClient, candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """The board is per candidate: two people applying to one job track it separately."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    ApplicationFactory(owner=candidate_user, job=job, status="APPLIED")
    ApplicationFactory(owner=second_candidate_user, job=job, status="OFFER")

    columns = candidate_client.get("/api/applications/board/").json()["columns"]

    by_status = {column["status"]: column["applications"] for column in columns}
    assert len(by_status["APPLIED"]) == 1
    assert by_status["OFFER"] == []


def test_saved_filter_matches_only_your_own_saves(
    candidate_client: APIClient, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """`?saved=true` filtered on `saved__isnull`, which ignored who had saved it."""
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(owner=second_candidate_user, job=job)

    response = candidate_client.get("/api/jobs/?saved=true")

    assert response.json()["results"] == []
