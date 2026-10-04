"""Creating, editing and deleting institutions, and reaching an institution's jobs.

The delete rule carries the risk here. `Job.institution` cascades, so deleting an institution
that has jobs would take every candidate's saved copies and application history with it -
silently, and with nothing to restore from.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from institutions.enums import Platform
from institutions.models import Institution
from jobs.models import Job
from screening.models import Ruleset
from tests.factories import (
    ApplicationFactory,
    InstitutionFactory,
    JobFactory,
    SavedJobFactory,
    ScreeningFactory,
)

pytestmark = pytest.mark.django_db


def test_an_admin_can_add_an_institution(auth_client: APIClient) -> None:
    response = auth_client.post(
        "/api/institutions/",
        {
            "name": "University of Somewhere",
            "nation": "SCOTLAND",
            "city": "Aberdeen",
            "careers_url": "https://somewhere.ac.uk/jobs",
        },
        format="json",
    )

    assert response.status_code == 201
    assert Institution.objects.filter(name="University of Somewhere").exists()


def test_the_slug_is_derived_not_supplied(auth_client: APIClient) -> None:
    """`slug` is the natural key seeding matches on, so it is never client-controlled."""
    response = auth_client.post(
        "/api/institutions/",
        {"name": "University of Somewhere", "slug": "something-else"},
        format="json",
    )

    assert response.json()["slug"] == "university-of-somewhere"


def test_a_manager_cannot_add_an_institution(manager_client: APIClient) -> None:
    response = manager_client.post(
        "/api/institutions/", {"name": "University of Somewhere"}, format="json"
    )

    assert response.status_code == 403


def test_a_manager_can_change_how_an_institution_is_crawled(
    manager_client: APIClient,
) -> None:
    institution = InstitutionFactory()

    response = manager_client.patch(
        f"/api/institutions/{institution.pk}/", {"crawl_enabled": False}, format="json"
    )

    assert response.status_code == 200
    institution.refresh_from_db()
    assert institution.crawl_enabled is False


def test_a_manager_cannot_rename_an_institution(manager_client: APIClient) -> None:
    """Names are seed data; a crawl cannot restore one that was mistyped."""
    institution = InstitutionFactory(name="University of Test 1")

    manager_client.patch(f"/api/institutions/{institution.pk}/", {"name": "Renamed"}, format="json")

    institution.refresh_from_db()
    assert institution.name == "University of Test 1"


def test_an_admin_can_rename_an_institution(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    auth_client.patch(f"/api/institutions/{institution.pk}/", {"name": "Renamed"}, format="json")

    institution.refresh_from_db()
    assert institution.name == "Renamed"


def test_moving_the_careers_url_clears_the_detected_platform(auth_client: APIClient) -> None:
    """Otherwise the next crawl hits the new portal with the old portal's adapter."""
    institution = InstitutionFactory(platform=Platform.STONEFISH)

    auth_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"careers_url": "https://elsewhere.ac.uk/vacancies"},
        format="json",
    )

    institution.refresh_from_db()
    assert institution.platform == Platform.UNKNOWN


def test_an_unchanged_careers_url_leaves_the_platform_alone(auth_client: APIClient) -> None:
    institution = InstitutionFactory(platform=Platform.STONEFISH)

    auth_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"careers_url": institution.careers_url, "notes": "checked"},
        format="json",
    )

    institution.refresh_from_db()
    assert institution.platform == Platform.STONEFISH


def test_an_empty_institution_can_be_deleted(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    assert auth_client.delete(f"/api/institutions/{institution.pk}/").status_code == 204
    assert not Institution.objects.filter(pk=institution.pk).exists()


def test_an_institution_with_jobs_cannot_be_deleted(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    institution = InstitutionFactory()
    job = JobFactory(institution=institution)
    ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.delete(f"/api/institutions/{institution.pk}/")

    assert response.status_code == 409
    assert response.json()["extra"]["jobs"] == 1
    assert Institution.objects.filter(pk=institution.pk).exists()


def test_refusing_the_delete_protects_candidate_data(
    auth_client: APIClient, candidate_user: Any, ruleset: Ruleset
) -> None:
    """The reason the 409 exists: the cascade reaches saved jobs and applications."""
    institution = InstitutionFactory()
    job = JobFactory(institution=institution)
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(owner=candidate_user, job=job)
    ApplicationFactory(owner=candidate_user, job=job)

    auth_client.delete(f"/api/institutions/{institution.pk}/")

    assert Job.objects.filter(pk=job.pk).exists()
    assert candidate_user.saved_jobs.count() == 1
    assert candidate_user.applications.count() == 1


def test_a_manager_cannot_delete_an_institution(manager_client: APIClient) -> None:
    institution = InstitutionFactory()

    assert manager_client.delete(f"/api/institutions/{institution.pk}/").status_code == 403


def test_a_candidate_can_list_institutions(candidate_client: APIClient) -> None:
    InstitutionFactory()

    assert candidate_client.get("/api/institutions/").status_code == 200


def test_an_institution_can_be_fetched_by_slug(candidate_client: APIClient) -> None:
    """The shared page addresses institutions by the same key its URL uses."""
    institution = InstitutionFactory()

    response = candidate_client.get(f"/api/institutions/?slug={institution.slug}")

    assert [row["slug"] for row in response.json()["results"]] == [institution.slug]


def test_that_institutions_jobs_are_reachable_by_the_same_slug(
    candidate_client: APIClient, ruleset: Ruleset
) -> None:
    """`/jobs/?institution=<slug>` is what the institution page links to."""
    wanted = InstitutionFactory()
    other = InstitutionFactory()
    for institution in (wanted, other):
        job = JobFactory(institution=institution)
        ScreeningFactory(job=job, ruleset=ruleset)

    response = candidate_client.get(f"/api/jobs/?institution={wanted.slug}")

    rows = response.json()["results"]
    assert [row["institution_slug"] for row in rows] == [wanted.slug]


def test_the_institution_list_reports_its_open_job_count(
    candidate_client: APIClient, ruleset: Ruleset
) -> None:
    """The count is what makes the link on the institution list worth clicking."""
    institution = InstitutionFactory()
    job = JobFactory(institution=institution)
    ScreeningFactory(job=job, ruleset=ruleset)

    rows = candidate_client.get(f"/api/institutions/?slug={institution.slug}").json()["results"]

    assert rows[0]["open_jobs"] == 1
