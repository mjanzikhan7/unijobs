"""Adding, editing, withdrawing and deleting jobs.

The shape confirmed with the user: manual jobs get full CRUD, crawled jobs get status changes
only. Both halves matter - the second is what stops an administrator's edit from looking applied
and then silently vanishing on the next crawl.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from crawler.differ import ExistingJob, diff_vacancies, vacancy_content_hash
from crawler.enums import CrawlOutcome
from crawler.types import RawVacancy
from jobs.enums import JobSource, JobStatus
from jobs.models import Job
from screening.models import Ruleset
from tests.factories import InstitutionFactory, JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def crawled_job(ruleset: Ruleset) -> Job:
    job = JobFactory(source=JobSource.PORTAL)
    ScreeningFactory(job=job, ruleset=ruleset)
    return job


@pytest.fixture
def manual_job(auth_client: APIClient, ruleset: Ruleset) -> Job:
    institution = InstitutionFactory()
    response = auth_client.post(
        "/api/jobs/manual/",
        {
            "institution": institution.slug,
            "source_url": "https://jobs.test.ac.uk/by-hand/1",
            "title": "Lecturer in Physics",
            "salary_raw": "£45,000 to £52,000",
        },
        format="json",
    )
    assert response.status_code == 201
    return Job.objects.get(pk=response.json()["id"])


def test_a_manual_job_can_be_edited(auth_client: APIClient, manual_job: Job) -> None:
    response = auth_client.patch(
        f"/api/jobs/{manual_job.pk}/", {"title": "Senior Lecturer in Physics"}, format="json"
    )

    assert response.status_code == 200
    manual_job.refresh_from_db()
    assert manual_job.title == "Senior Lecturer in Physics"


def test_editing_a_manual_job_rescreens_it(auth_client: APIClient, manual_job: Job) -> None:
    """A corrected salary must move the threshold verdict, or the correction achieved nothing."""
    before = manual_job.screening.salary_min

    auth_client.patch(
        f"/api/jobs/{manual_job.pk}/", {"salary_raw": "£70,000 to £80,000"}, format="json"
    )

    manual_job.refresh_from_db()
    assert manual_job.screening.salary_min != before


def test_a_manual_job_can_be_deleted(auth_client: APIClient, manual_job: Job) -> None:
    assert auth_client.delete(f"/api/jobs/{manual_job.pk}/").status_code == 204
    assert not Job.objects.filter(pk=manual_job.pk).exists()


def test_identity_fields_are_not_editable(auth_client: APIClient, manual_job: Job) -> None:
    """`source_url` is half the upsert key - changing it would duplicate, not edit."""
    auth_client.patch(
        f"/api/jobs/{manual_job.pk}/",
        {"source_url": "https://elsewhere.test/9", "source": "PORTAL"},
        format="json",
    )

    manual_job.refresh_from_db()
    assert manual_job.source_url == "https://jobs.test.ac.uk/by-hand/1"
    assert manual_job.source == JobSource.MANUAL


def test_a_crawled_job_cannot_be_edited(auth_client: APIClient, crawled_job: Job) -> None:
    response = auth_client.patch(
        f"/api/jobs/{crawled_job.pk}/", {"title": "Something else"}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["extra"]["use"] == "withdraw"


def test_a_crawled_job_cannot_be_deleted(auth_client: APIClient, crawled_job: Job) -> None:
    """Deleting would last exactly until the next crawl, and would cascade to candidates."""
    response = auth_client.delete(f"/api/jobs/{crawled_job.pk}/")

    assert response.status_code == 409
    assert Job.objects.filter(pk=crawled_job.pk).exists()


def test_a_crawled_job_can_be_withdrawn(
    auth_client: APIClient, crawled_job: Job, user: Any
) -> None:
    response = auth_client.post(
        f"/api/jobs/{crawled_job.pk}/withdraw/", {"reason": "Filled internally"}, format="json"
    )

    assert response.status_code == 200
    crawled_job.refresh_from_db()
    assert crawled_job.status == JobStatus.WITHDRAWN
    assert crawled_job.withdrawn_by == user
    assert crawled_job.withdrawn_reason == "Filled internally"


def test_a_withdrawal_records_when_it_happened(auth_client: APIClient, crawled_job: Job) -> None:
    auth_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/", {}, format="json")

    crawled_job.refresh_from_db()
    assert crawled_job.withdrawn_at is not None


def test_a_withdrawn_job_can_be_reinstated(auth_client: APIClient, crawled_job: Job) -> None:
    auth_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/", {}, format="json")

    response = auth_client.post(f"/api/jobs/{crawled_job.pk}/reinstate/")

    assert response.status_code == 200
    crawled_job.refresh_from_db()
    assert crawled_job.status == JobStatus.OPEN
    assert (crawled_job.withdrawn_at, crawled_job.withdrawn_by) == (None, None)


def test_a_withdrawal_survives_the_next_successful_crawl(
    auth_client: APIClient, crawled_job: Job
) -> None:
    """End to end through the real differ, not just the pure unit case.

    This is the regression: `_upsert_job` sets status back to OPEN, so anything routed into
    `updated` would silently reopen.
    """
    auth_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/", {}, format="json")
    crawled_job.refresh_from_db()

    vacancy = RawVacancy(
        institution_slug=crawled_job.institution.slug,
        source_url=crawled_job.source_url,
        title=crawled_job.title,
    )
    result = diff_vacancies(
        fetched=[vacancy],
        existing=[
            ExistingJob(
                job_id=crawled_job.pk,
                source_url=crawled_job.source_url,
                content_hash=vacancy_content_hash(vacancy),
                status=crawled_job.status,
                is_withdrawn=True,
            )
        ],
        outcome=CrawlOutcome.OK,
    )

    assert result.updated == ()
    assert len(result.unchanged) == 1


def test_a_candidate_cannot_withdraw_a_job(candidate_client: APIClient, crawled_job: Job) -> None:
    assert candidate_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/").status_code == 403


def test_a_candidate_cannot_delete_a_job(candidate_client: APIClient, manual_job: Job) -> None:
    assert candidate_client.delete(f"/api/jobs/{manual_job.pk}/").status_code == 403


def test_a_manager_can_withdraw_a_job(manager_client: APIClient, crawled_job: Job) -> None:
    assert manager_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/").status_code == 200


@pytest.fixture
def recruiter_institution(recruiter_user: Any) -> Any:
    """The one institution the recruiter is assigned to."""
    institution = InstitutionFactory()
    institution.recruiters.add(recruiter_user)
    return institution


def test_a_recruiter_can_add_a_job_at_their_own_institution(
    recruiter_client: APIClient, recruiter_institution: Any, ruleset: Ruleset
) -> None:
    response = recruiter_client.post(
        "/api/jobs/manual/",
        {
            "institution": recruiter_institution.slug,
            "source_url": "https://jobs.test.ac.uk/by-hand/recruiter-1",
            "title": "Lecturer in Chemistry",
        },
        format="json",
    )

    assert response.status_code == 201


def test_a_recruiter_cannot_add_a_job_at_an_institution_they_are_not_assigned_to(
    recruiter_client: APIClient, ruleset: Ruleset
) -> None:
    other = InstitutionFactory()

    response = recruiter_client.post(
        "/api/jobs/manual/",
        {
            "institution": other.slug,
            "source_url": "https://jobs.test.ac.uk/by-hand/recruiter-2",
            "title": "Lecturer in Chemistry",
        },
        format="json",
    )

    assert response.status_code == 403


def test_a_recruiter_can_edit_a_manual_job_at_their_own_institution(
    recruiter_client: APIClient, recruiter_institution: Any, ruleset: Ruleset
) -> None:
    job = JobFactory(source=JobSource.MANUAL, institution=recruiter_institution)
    ScreeningFactory(job=job, ruleset=ruleset)

    response = recruiter_client.patch(
        f"/api/jobs/{job.pk}/", {"title": "Senior Lecturer in Chemistry"}, format="json"
    )

    assert response.status_code == 200


def test_a_recruiter_cannot_edit_a_manual_job_at_another_institution(
    recruiter_client: APIClient, ruleset: Ruleset
) -> None:
    job = JobFactory(source=JobSource.MANUAL, institution=InstitutionFactory())
    ScreeningFactory(job=job, ruleset=ruleset)

    response = recruiter_client.patch(
        f"/api/jobs/{job.pk}/", {"title": "Something else"}, format="json"
    )

    assert response.status_code == 403


def test_a_recruiter_can_withdraw_a_crawled_job_at_their_own_institution(
    recruiter_client: APIClient, recruiter_institution: Any, ruleset: Ruleset
) -> None:
    job = JobFactory(source=JobSource.PORTAL, institution=recruiter_institution)
    ScreeningFactory(job=job, ruleset=ruleset)

    response = recruiter_client.post(f"/api/jobs/{job.pk}/withdraw/", {}, format="json")

    assert response.status_code == 200


def test_a_recruiter_cannot_withdraw_a_crawled_job_at_another_institution(
    recruiter_client: APIClient, crawled_job: Job
) -> None:
    """`crawled_job` sits at its own fresh institution - the recruiter is assigned to none."""
    response = recruiter_client.post(f"/api/jobs/{crawled_job.pk}/withdraw/", {}, format="json")

    assert response.status_code == 403


def test_a_recruiter_cannot_create_an_institution(recruiter_client: APIClient) -> None:
    """Broadening `required_roles_write` must not leak into an action gated by its own role set."""
    response = recruiter_client.post(
        "/api/institutions/", {"name": "New University"}, format="json"
    )

    assert response.status_code == 403


def test_a_recruiter_cannot_trigger_a_crawl(
    recruiter_client: APIClient, recruiter_institution: Any
) -> None:
    response = recruiter_client.post(f"/api/institutions/{recruiter_institution.pk}/crawl/")

    assert response.status_code == 403


def test_source_is_a_facet_so_crawled_and_manual_are_distinguishable(
    auth_client: APIClient, crawled_job: Job, manual_job: Job
) -> None:
    """Managers were asked to be able to tell whether a job was crawled."""
    facets = auth_client.get("/api/jobs/facets/").json()["facets"]

    assert {row["value"] for row in facets["source"]} >= {"PORTAL", "MANUAL"}


def test_the_list_reports_where_each_job_came_from(
    auth_client: APIClient, crawled_job: Job, manual_job: Job
) -> None:
    rows = auth_client.get("/api/jobs/?status=OPEN").json()["results"]

    by_id = {row["id"]: row["source"] for row in rows}
    assert by_id[crawled_job.pk] == "PORTAL"
    assert by_id[manual_job.pk] == "MANUAL"
