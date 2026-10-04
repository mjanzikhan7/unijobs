"""A candidate account must not reach the operator's half of the API.

The completeness check at the bottom is the load-bearing part: it enumerates the router rather
than a hand-written list, so registering a new admin viewset without covering it here fails
immediately instead of the next time somebody thinks to look.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from accounts.enums import Role
from api.urls import router

_ADMIN_URLS: tuple[str, ...] = (
    "/api/crawl-runs/",
    "/api/crawl-runs/active/",
    "/api/sponsor-matches/",
    "/api/institutions/review-queue/",
    "/api/institutions/register-search/?q=leeds",
    "/api/rulesets/",
    "/api/users/",
)

_CANDIDATE_URLS: tuple[str, ...] = (
    "/api/jobs/",
    "/api/jobs/facets/",
    "/api/institutions/",
    "/api/saved-jobs/",
    "/api/applications/",
    "/api/saved-searches/",
    "/api/profiles/",
    "/api/cvs/",
    "/api/auth/me/",
)


@pytest.mark.django_db
@pytest.mark.parametrize("url", _ADMIN_URLS)
def test_a_candidate_is_refused(candidate_client: APIClient, url: str) -> None:
    assert candidate_client.get(url).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url", _ADMIN_URLS)
def test_the_operator_is_allowed(auth_client: APIClient, url: str) -> None:
    """The mirror of the test above: proof the 403s are about role, not a broken URL."""
    assert auth_client.get(url).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("url", _CANDIDATE_URLS)
def test_a_candidate_reaches_their_own_surface(candidate_client: APIClient, url: str) -> None:
    assert candidate_client.get(url).status_code == 200


@pytest.mark.django_db
def test_a_candidate_cannot_add_a_job(candidate_client: APIClient) -> None:
    """Writes are staff-only even where the read is not."""
    response = candidate_client.post("/api/jobs/manual/", {}, format="json")

    assert response.status_code == 403


@pytest.mark.django_db
def test_a_manager_cannot_change_threshold_figures(manager_client: APIClient) -> None:
    """Managers read the ruleset in force; moving the figures moves every verdict."""
    assert manager_client.get("/api/rulesets/").status_code == 200
    assert manager_client.post("/api/rulesets/", {}, format="json").status_code == 403


@pytest.mark.django_db
def test_a_candidate_cannot_start_a_crawl(candidate_client: APIClient) -> None:
    assert candidate_client.post("/api/crawl-runs/", {}, format="json").status_code == 403


def test_every_registered_viewset_is_accounted_for() -> None:
    """No viewset may be neither candidate-facing nor covered by the refusal list above.

    Enumerates the router, so a newly registered admin viewset fails here rather than shipping
    untested.
    """
    covered_prefixes = {url.split("/")[2] for url in _ADMIN_URLS + _CANDIDATE_URLS}

    uncovered = [
        prefix
        for prefix, viewset, _ in router.registry
        if prefix not in covered_prefixes
        and Role.CANDIDATE not in set(getattr(viewset, "required_roles", ()) or ())
    ]

    assert not uncovered, (
        f"These viewsets are not exercised by this test: {uncovered}. Add each to _ADMIN_URLS "
        f"(if candidates must be refused) or _CANDIDATE_URLS."
    )
