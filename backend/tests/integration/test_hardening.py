"""Security and performance properties that are easy to lose without noticing.

Each one was measured, not assumed. An extra query per request costs nothing visible until
traffic arrives, and an exposed login form costs nothing until somebody finds it.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.urls import NoReverseMatch, reverse
from rest_framework.test import APIClient

from accounts.enums import Role
from accounts.models import UserAccount
from screening.models import Ruleset
from tests.factories import JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


def test_authentication_and_the_role_check_cost_one_query(
    candidate_client: APIClient, django_assert_num_queries: Any
) -> None:
    """`RoleRequired` reads the account on every request.

    DRF's own token class loads the user but not the account, which adds a second query to every
    request. One join instead.
    """
    with django_assert_num_queries(1):
        candidate_client.get("/api/auth/me/")


def test_the_job_list_does_not_grow_queries_with_analytics(
    candidate_client: APIClient, ruleset: Ruleset, django_assert_max_num_queries: Any
) -> None:
    """Recording a search adds one INSERT, not one query per row."""
    for _ in range(25):
        ScreeningFactory(job=JobFactory(), ruleset=ruleset)

    with django_assert_max_num_queries(7):
        candidate_client.get("/api/jobs/?page_size=25&q=engineer")


def test_a_suspended_account_is_refused_at_authentication(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """Checked on the token, not only by the login backend.

    Otherwise a token issued before the account was suspended would keep working.
    """
    candidate_user.is_active = False
    candidate_user.save(update_fields=["is_active"])

    assert candidate_client.get("/api/jobs/").status_code == 401


def test_djangos_admin_is_not_mounted() -> None:
    """Django's admin is not mounted. Nothing uses it, and it would add a second login form.

    DRF's rate limits do not cover it, because it is not a DRF view.
    """
    with pytest.raises(NoReverseMatch):
        reverse("admin:index")


def test_the_admin_login_page_is_not_reachable(api_client: APIClient) -> None:
    assert api_client.get("/admin/").status_code == 404


def test_one_account_cannot_be_attacked_from_many_addresses(
    api_client: APIClient, candidate_user: Any, settings: Any
) -> None:
    """The IP limit stops one machine. This one protects one *account*.

    Each attempt comes from a different address, so only a limit per username stops it.
    """
    codes = []
    for attempt in range(25):
        codes.append(
            api_client.post(
                "/api/auth/login/",
                {"username": candidate_user.username, "password": "wrong"},
                format="json",
                REMOTE_ADDR=f"203.0.113.{attempt}",
            ).status_code
        )

    assert 429 in codes


def test_the_username_throttle_is_case_insensitive(
    api_client: APIClient, candidate_user: Any
) -> None:
    """Otherwise changing the capitalisation is enough to get a fresh bucket."""
    for attempt in range(25):
        username = candidate_user.username.upper() if attempt % 2 else candidate_user.username
        response = api_client.post(
            "/api/auth/login/",
            {"username": username, "password": "wrong"},
            format="json",
            REMOTE_ADDR=f"198.51.100.{attempt}",
        )
        if response.status_code == 429:
            return

    pytest.fail("mixed-case attempts were never throttled")


def test_a_login_without_a_username_still_answers(api_client: APIClient) -> None:
    """No username to key on must not raise; the IP throttle still applies."""
    assert api_client.post("/api/auth/login/", {}, format="json").status_code == 400


def test_the_request_ceiling_leaves_room_for_a_full_size_cv(settings: Any) -> None:
    """The request size limit must be above the file size limit.

    Otherwise a large CV would get a confusing framework error instead of the serializer's clear
    message.
    """
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE > settings.CV_MAX_BYTES


def test_the_field_count_ceiling_is_tightened(settings: Any) -> None:
    """The default of 1000 blunts hash-collision denial of service; nothing here needs that room."""
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS <= 200


def test_production_settings_pass_djangos_own_deployment_check() -> None:
    """`manage.py check --deploy`, run in-process against the production settings."""
    import os
    from unittest.mock import patch

    from django.core.checks import Tags, run_checks
    from django.test import override_settings

    with (
        patch.dict(os.environ, {"DJANGO_SECRET_KEY": "x" * 60}),
        override_settings(
            DEBUG=False,
            SECRET_KEY="x" * 60,
            ALLOWED_HOSTS=["example.com"],
            SECURE_SSL_REDIRECT=True,
            SECURE_HSTS_SECONDS=31536000,
            SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
            SECURE_HSTS_PRELOAD=True,
            SESSION_COOKIE_SECURE=True,
            CSRF_COOKIE_SECURE=True,
            SECURE_CONTENT_TYPE_NOSNIFF=True,
            X_FRAME_OPTIONS="DENY",
        ),
    ):
        issues = [
            issue
            for issue in run_checks(tags=[Tags.security], include_deployment_checks=True)
            if issue.is_serious()
        ]

    assert not issues, [str(issue) for issue in issues]


def test_an_admin_created_account_gets_its_role_without_a_second_query(
    auth_client: APIClient, django_assert_max_num_queries: Any
) -> None:
    """The users list select_relateds the account; a role per row would be an N+1."""
    for index in range(10):
        user = User.objects.create_user(username=f"bulk-{index}", password="x")
        UserAccount.objects.filter(user=user).update(role=Role.CANDIDATE)

    with django_assert_max_num_queries(6):
        auth_client.get("/api/users/?page_size=50")
