"""The web app signs in with an HttpOnly session cookie, protected by CSRF."""

from __future__ import annotations

from typing import Any

import pytest
from django.conf import settings
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

_PASSWORD = "a-long-test-password-1"


@pytest.fixture
def person(candidate_user: Any) -> Any:
    candidate_user.set_password(_PASSWORD)
    candidate_user.save()
    return candidate_user


def _browser() -> APIClient:
    """A client that checks CSRF, like a real browser session."""
    return APIClient(enforce_csrf_checks=True)


def _sign_in(client: APIClient, person: Any) -> Any:
    return client.post(
        "/api/auth/login/",
        {"username": person.username, "password": _PASSWORD, "session": True},
        format="json",
    )


def test_a_session_sign_in_sends_no_token(person: Any) -> None:
    response = _sign_in(_browser(), person)

    assert response.status_code == 200
    assert "token" not in response.json()


def test_the_session_cookie_cannot_be_read_by_javascript(person: Any) -> None:
    response = _sign_in(_browser(), person)

    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"


def test_the_session_signs_requests_in(person: Any) -> None:
    client = _browser()
    _sign_in(client, person)

    response = client.get("/api/auth/me/")

    assert response.status_code == 200
    assert response.json()["username"] == person.username
    assert settings.CSRF_COOKIE_NAME in response.cookies


def test_a_change_without_the_csrf_token_is_refused(person: Any) -> None:
    client = _browser()
    _sign_in(client, person)

    response = client.post("/api/auth/logout/")

    assert response.status_code == 403


def test_a_change_with_the_csrf_token_is_accepted(person: Any) -> None:
    client = _browser()
    _sign_in(client, person)
    csrf = client.get("/api/auth/me/").cookies[settings.CSRF_COOKIE_NAME].value

    response = client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=csrf)

    assert response.status_code == 204
    assert client.get("/api/auth/me/").status_code in (401, 403)


def test_scripts_still_get_a_token_without_session(person: Any) -> None:
    response = APIClient().post(
        "/api/auth/login/", {"username": person.username, "password": _PASSWORD}, format="json"
    )

    assert len(response.json()["token"]) == 40


def test_a_password_change_keeps_this_session_and_ends_the_others(person: Any) -> None:
    this_device, other_device = _browser(), _browser()
    _sign_in(this_device, person)
    _sign_in(other_device, person)
    csrf = this_device.get("/api/auth/me/").cookies[settings.CSRF_COOKIE_NAME].value

    response = this_device.post(
        "/api/account/password/",
        {"current_password": _PASSWORD, "new_password": "another-long-password-2"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )

    assert response.status_code == 200
    assert "token" not in response.json()
    assert this_device.get("/api/auth/me/").status_code == 200
    assert other_device.get("/api/auth/me/").status_code in (401, 403)
