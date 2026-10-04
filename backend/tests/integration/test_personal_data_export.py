"""A person can download everything the service holds about them, and nothing else."""

from __future__ import annotations

import json
from typing import Any

import pytest
from rest_framework.test import APIClient

from tests.factories import ApplicationFactory, SavedJobFactory, SavedSearchFactory

pytestmark = pytest.mark.django_db


def _export(client: APIClient) -> dict[str, Any]:
    response = client.get("/api/account/export/")
    assert response.status_code == 200
    return json.loads(response.content)


def test_the_export_is_a_file_download(candidate_client: APIClient) -> None:
    response = candidate_client.get("/api/account/export/")

    assert response["Content-Type"] == "application/json"
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["Cache-Control"] == "no-store"


def test_the_export_holds_the_account_and_everything_it_owns(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    SavedJobFactory(owner=candidate_user, note="Ask about the start date")
    ApplicationFactory(owner=candidate_user, notes="Sent on Monday")
    SavedSearchFactory(owner=candidate_user, name="Bath, research")

    data = _export(candidate_client)

    assert data["account"]["username"] == candidate_user.username
    assert data["account"]["email"] == candidate_user.email
    assert [saved["note"] for saved in data["saved_jobs"]] == ["Ask about the start date"]
    assert [app["notes"] for app in data["applications"]] == ["Sent on Monday"]
    assert [search["name"] for search in data["saved_searches"]] == ["Bath, research"]


def test_the_export_never_contains_another_persons_data(
    candidate_client: APIClient, second_candidate_user: Any
) -> None:
    SavedJobFactory(owner=second_candidate_user, note="Private to someone else")
    ApplicationFactory(owner=second_candidate_user, notes="Private to someone else")

    data = _export(candidate_client)

    assert data["saved_jobs"] == []
    assert data["applications"] == []
    assert "Private to someone else" not in json.dumps(data)


def test_the_export_needs_a_signed_in_person() -> None:
    response = APIClient().get("/api/account/export/")

    assert response.status_code == 401
