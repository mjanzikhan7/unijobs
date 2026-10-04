"""The crawl console API and authentication."""

from __future__ import annotations

import time
from typing import Any

import pytest
from rest_framework.test import APIClient

from crawler.enums import CrawlOutcome, CrawlRunStatus
from crawler.models import CrawlRun
from jobs.enums import JobStatus
from screening.models import Ruleset
from tests.factories import (
    CrawlRunFactory,
    CrawlRunInstitutionFactory,
    InstitutionFactory,
    JobFactory,
    ScreeningFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_real_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the API tests from actually fanning a crawl out.

    ``POST /crawl-runs/`` is meant to return before any work happens, so the test asserts the
    response - not the crawl.
    """
    monkeypatch.setattr("crawler.tasks.dispatch_run_task.delay", lambda *args, **kwargs: None)


@pytest.mark.parametrize(
    "path",
    [
        "/api/jobs/",
        "/api/institutions/",
        "/api/crawl-runs/",
        "/api/saved-jobs/",
        "/api/applications/",
        "/api/saved-searches/",
        "/api/rulesets/",
        "/api/profiles/",
        "/api/auth/me/",
    ],
)
def test_an_anonymous_request_is_refused(api_client: APIClient, path: str) -> None:
    """Single-user application: everything is private by default."""
    assert api_client.get(path).status_code == 401


def test_the_health_check_is_open(api_client: APIClient) -> None:
    """The container healthcheck has no token."""
    assert api_client.get("/api/health/").status_code == 200


def test_a_valid_token_is_accepted(auth_client: APIClient, ruleset: Ruleset) -> None:
    assert auth_client.get("/api/jobs/").status_code == 200


def test_login_returns_a_token(api_client: APIClient, user: Any) -> None:
    response = api_client.post(
        "/api/auth/login/",
        {"username": user.username, "password": "not-a-real-password"},
        format="json",
    )

    assert "token" in response.json()


def test_login_with_a_wrong_password_is_refused(api_client: APIClient, user: Any) -> None:
    response = api_client.post(
        "/api/auth/login/", {"username": user.username, "password": "wrong"}, format="json"
    )

    assert response.status_code == 401


def test_a_failed_login_does_not_say_which_half_was_wrong(api_client: APIClient, user: Any) -> None:
    response = api_client.post(
        "/api/auth/login/", {"username": "nobody", "password": "wrong"}, format="json"
    )

    assert response.json()["detail"] == "Incorrect username or password."


def test_starting_a_crawl_is_accepted_not_completed(auth_client: APIClient) -> None:
    """202: the work happens elsewhere."""
    InstitutionFactory()

    assert auth_client.post("/api/crawl-runs/", {}, format="json").status_code == 202


def test_starting_a_crawl_returns_the_run_id(auth_client: APIClient) -> None:
    """So the UI can subscribe to progress immediately."""
    InstitutionFactory()

    response = auth_client.post("/api/crawl-runs/", {}, format="json")

    assert response.json()["id"] == CrawlRun.objects.get().pk


def test_starting_a_crawl_returns_before_any_crawling_happens(
    auth_client: APIClient,
) -> None:
    """Under 500ms regardless of estate size, because it does no work."""
    InstitutionFactory.create_batch(50)

    started = time.monotonic()
    auth_client.post("/api/crawl-runs/", {}, format="json")
    elapsed = time.monotonic() - started

    assert elapsed < 0.5


def test_a_new_run_counts_the_institutions_it_will_cover(auth_client: APIClient) -> None:
    InstitutionFactory.create_batch(5)

    response = auth_client.post("/api/crawl-runs/", {}, format="json")

    assert response.json()["institutions_total"] == 5


def test_a_run_can_be_scoped_to_named_institutions(auth_client: APIClient) -> None:
    """UC-01 A2: crawl one institution from its row rather than the whole estate."""
    InstitutionFactory(slug="university-of-bath")
    InstitutionFactory(slug="university-of-york")

    response = auth_client.post(
        "/api/crawl-runs/", {"institutions": ["university-of-bath"]}, format="json"
    )

    assert response.json()["institutions_total"] == 1


def test_crawling_a_single_institution_from_its_row_works(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    response = auth_client.post(f"/api/institutions/{institution.pk}/crawl/")

    assert response.status_code == 202


def test_a_second_concurrent_run_is_refused(auth_client: APIClient) -> None:
    """Concurrent runs would double every request to every university."""
    InstitutionFactory()
    auth_client.post("/api/crawl-runs/", {}, format="json")

    response = auth_client.post("/api/crawl-runs/", {}, format="json")

    assert response.status_code == 409


def test_the_refusal_links_to_the_run_in_progress(auth_client: APIClient) -> None:
    """Refusing without saying where to look is a dead end."""
    InstitutionFactory()
    first = auth_client.post("/api/crawl-runs/", {}, format="json").json()

    response = auth_client.post("/api/crawl-runs/", {}, format="json")

    assert response.json()["extra"]["active_run_id"] == first["id"]


def test_the_active_run_endpoint_reports_the_run_in_progress(
    auth_client: APIClient,
) -> None:
    """Drives the disabled state on the crawl button."""
    InstitutionFactory()
    auth_client.post("/api/crawl-runs/", {}, format="json")

    assert auth_client.get("/api/crawl-runs/active/").json()["run"] is not None


def test_the_active_run_endpoint_reports_nothing_when_idle(auth_client: APIClient) -> None:
    assert auth_client.get("/api/crawl-runs/active/").json()["run"] is None


def test_the_console_lists_every_institution(auth_client: APIClient) -> None:
    InstitutionFactory.create_batch(3)

    assert auth_client.get("/api/institutions/").json()["count"] == 3


def test_the_console_shows_the_last_crawl_outcome(auth_client: APIClient) -> None:
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(institution=institution, outcome=CrawlOutcome.TIMEOUT)

    response = auth_client.get("/api/institutions/")

    assert response.json()["results"][0]["last_crawl"]["outcome"] == "TIMEOUT"


def test_the_console_distinguishes_a_drop_to_zero_from_a_quiet_estate(
    auth_client: APIClient,
) -> None:
    """At the API level. The console must show these outcomes clearly apart."""
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(
        institution=institution,
        outcome=CrawlOutcome.ZERO_RESULTS,
        vacancies_found=0,
        previous_vacancies_found=40,
    )

    response = auth_client.get("/api/institutions/")

    assert response.json()["results"][0]["last_crawl"]["dropped_to_zero"] is True


def test_the_console_shows_the_error_detail(auth_client: APIClient) -> None:
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(
        institution=institution,
        outcome=CrawlOutcome.PARSE_ERROR,
        error_class="ParseError",
        error_detail="Could not find the results table.",
    )

    response = auth_client.get("/api/institutions/")

    assert response.json()["results"][0]["last_crawl"]["error_detail"] == (
        "Could not find the results table."
    )


def test_an_adapter_override_can_be_set(auth_client: APIClient) -> None:
    """UC-07: a human who has looked at the portal beats detection."""
    institution = InstitutionFactory()

    auth_client.patch(
        f"/api/institutions/{institution.pk}/", {"adapter_override": "JOBTRAIN"}, format="json"
    )
    institution.refresh_from_db()

    assert institution.adapter_override == "JOBTRAIN"


def test_crawling_can_be_disabled_for_an_institution(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    auth_client.patch(
        f"/api/institutions/{institution.pk}/", {"crawl_enabled": False}, format="json"
    )
    institution.refresh_from_db()

    assert institution.crawl_enabled is False


def test_the_institution_name_cannot_be_edited_from_the_crawl_console(
    manager_client: APIClient,
) -> None:
    """Names come from the seed, so the console does not rewrite them.

    An admin *can*, on the institution admin screen. That is a separate permission on purpose.
    Note that `make seed` matches on slug and will put the seeded name back. The console is a
    manager's tool, so it keeps the old rule.
    """
    institution = InstitutionFactory(name="University of Bath")

    manager_client.patch(
        f"/api/institutions/{institution.pk}/", {"name": "Somewhere Else"}, format="json"
    )
    institution.refresh_from_db()

    assert institution.name == "University of Bath"


def test_the_diff_partitions_new_changed_and_disappeared(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(run=run, institution=institution)
    ScreeningFactory(job=JobFactory(institution=institution), ruleset=ruleset)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/diff/")

    assert set(response.json()) == {"run", "new", "changed", "disappeared"}


def test_a_job_first_seen_in_this_run_is_new(auth_client: APIClient, ruleset: Ruleset) -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(run=run, institution=institution)
    ScreeningFactory(job=JobFactory(institution=institution), ruleset=ruleset)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/diff/")

    assert len(response.json()["new"]) == 1


def test_a_job_closed_by_this_run_appears_as_disappeared(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    from django.utils import timezone

    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(run=run, institution=institution)
    job = JobFactory(
        institution=institution,
        status=JobStatus.DISAPPEARED,
        disappeared_at=timezone.now(),
        first_seen_at=run.started_at - timezone.timedelta(days=7),
    )
    ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/diff/")

    assert len(response.json()["disappeared"]) == 1


def test_new_and_changed_never_overlap(auth_client: APIClient, ruleset: Ruleset) -> None:
    """A job that first appeared in this run is new, not changed."""
    from jobs.models import JobRevision

    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)
    institution = InstitutionFactory()
    CrawlRunInstitutionFactory(run=run, institution=institution)
    job = JobFactory(institution=institution)
    ScreeningFactory(job=job, ruleset=ruleset)
    JobRevision.objects.create(
        job=job, crawl_run=run, field="salary_raw", value_before="a", value_after="b"
    )

    payload = auth_client.get(f"/api/crawl-runs/{run.pk}/diff/").json()

    assert payload["changed"] == []


def test_the_run_detail_lists_every_institution_result(auth_client: APIClient) -> None:
    run = CrawlRunFactory()
    CrawlRunInstitutionFactory.create_batch(3, run=run)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/")

    assert len(response.json()["institution_results"]) == 3


def test_a_run_result_says_whether_it_permitted_closure(auth_client: APIClient) -> None:
    """The console explains why nothing was closed, rather than staying silent about it."""
    run = CrawlRunFactory()
    CrawlRunInstitutionFactory(run=run, outcome=CrawlOutcome.TIMEOUT)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/")

    assert response.json()["institution_results"][0]["permits_closure"] is False


def test_institution_results_put_problems_first(auth_client: APIClient) -> None:
    """UC-07: rows that need attention are surfaced at the top."""
    run = CrawlRunFactory()
    healthy = InstitutionFactory(slug="healthy", name="AAA Healthy University")
    broken = InstitutionFactory(slug="broken", name="ZZZ Broken University")
    CrawlRunInstitutionFactory(run=run, institution=healthy, outcome=CrawlOutcome.OK)
    CrawlRunInstitutionFactory(run=run, institution=broken, outcome=CrawlOutcome.TIMEOUT)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/institutions/")

    assert response.json()[0]["institution_slug"] == "broken"
