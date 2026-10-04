"""Pause/resume/cancel/restart and the logs endpoint over HTTP.

The service-layer tests in ``test_crawl_control.py`` prove the transitions and the scope
resolution are correct. These prove the same thing is actually reachable through the API with
the right status codes - a 409 the frontend can render, not a 500 it can only fail on.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from crawler.enums import CrawlOutcome, CrawlRunStatus
from tests.factories import CrawlRunFactory, CrawlRunInstitutionFactory, InstitutionFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_real_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate the control endpoints from a real crawl attempt.

    A restart dispatches exactly like starting a crawl does; these tests assert the HTTP
    contract, not a full crawl attempt.
    """
    monkeypatch.setattr("crawler.tasks.dispatch_run_task.delay", lambda *args, **kwargs: None)


def test_pause_returns_the_updated_run(auth_client: APIClient) -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/pause/")

    assert response.status_code == 200
    assert response.data["status"] == CrawlRunStatus.PAUSED.value


def test_pausing_a_finished_run_is_409(auth_client: APIClient) -> None:
    """Not 500 - the frontend has to be able to render this."""
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/pause/")

    assert response.status_code == 409


def test_resume_returns_the_updated_run(auth_client: APIClient) -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.PAUSED)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/resume/")

    assert response.status_code == 200
    assert response.data["status"] == CrawlRunStatus.RUNNING.value


def test_cancel_returns_the_updated_run(auth_client: APIClient) -> None:
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/cancel/")

    assert response.status_code == 200
    assert response.data["status"] == CrawlRunStatus.CANCELLED.value


def test_an_anonymous_request_cannot_control_a_run(api_client: APIClient) -> None:
    """Single-user app: everything is private by default."""
    run = CrawlRunFactory(status=CrawlRunStatus.RUNNING)

    response = api_client.post(f"/api/crawl-runs/{run.pk}/cancel/")

    assert response.status_code == 401


def test_restart_requires_a_scope(auth_client: APIClient) -> None:
    """A silent default would make the all-vs-failures choice for the user."""
    run = CrawlRunFactory(status=CrawlRunStatus.CANCELLED)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/restart/", {})

    assert response.status_code == 400


def test_restart_all_returns_202_with_the_new_run(auth_client: APIClient) -> None:
    InstitutionFactory.create_batch(2)
    run = CrawlRunFactory(status=CrawlRunStatus.CANCELLED, institution_ids=[])

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/restart/", {"scope": "all"})

    assert response.status_code == 202
    assert response.data["id"] != run.pk
    assert response.data["status"] == CrawlRunStatus.RUNNING.value


def test_restart_failures_with_nothing_outstanding_is_409(auth_client: APIClient) -> None:
    institution = InstitutionFactory()
    run = CrawlRunFactory(status=CrawlRunStatus.COMPLETE, institution_ids=[institution.pk])
    CrawlRunInstitutionFactory(run=run, institution=institution, outcome=CrawlOutcome.OK)

    response = auth_client.post(f"/api/crawl-runs/{run.pk}/restart/", {"scope": "failures"})

    assert response.status_code == 409


def test_the_run_detail_reports_how_many_are_retriable(auth_client: APIClient) -> None:
    """What the "Retry N failures" button reads its count from."""
    ok_institution = InstitutionFactory()
    broken_institution = InstitutionFactory()
    run = CrawlRunFactory(
        status=CrawlRunStatus.CANCELLED,
        institution_ids=[ok_institution.pk, broken_institution.pk],
    )
    CrawlRunInstitutionFactory(run=run, institution=ok_institution, outcome=CrawlOutcome.OK)
    CrawlRunInstitutionFactory(
        run=run, institution=broken_institution, outcome=CrawlOutcome.TIMEOUT
    )

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/")

    assert response.data["retriable_count"] == 1


def test_the_run_list_does_not_carry_the_retriable_count(auth_client: APIClient) -> None:
    """The list serializer is deliberately cheap - no per-row query."""
    CrawlRunFactory()

    response = auth_client.get("/api/crawl-runs/")

    assert "retriable_count" not in response.data["results"][0]


def test_logs_are_returned_oldest_first(auth_client: APIClient) -> None:
    from crawler.services import log_event

    run = CrawlRunFactory()
    log_event(run, "first")
    log_event(run, "second")

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/logs/")

    assert [entry["message"] for entry in response.data] == ["first", "second"]


def test_logs_after_an_id_only_returns_what_is_new(auth_client: APIClient) -> None:
    """The polling contract: re-fetch is incremental, not the whole history."""
    from crawler.services import log_event

    run = CrawlRunFactory()
    first = log_event(run, "first")
    log_event(run, "second")

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/logs/", {"after": first.pk})

    assert [entry["message"] for entry in response.data] == ["second"]


def test_logs_include_the_institution_name_when_there_is_one(auth_client: APIClient) -> None:
    from crawler.services import log_event

    run = CrawlRunFactory()
    institution = InstitutionFactory(name="University of Somewhere")
    log_event(run, "crawled", institution=institution)

    response = auth_client.get(f"/api/crawl-runs/{run.pk}/logs/")

    assert response.data[0]["institution_name"] == "University of Somewhere"
