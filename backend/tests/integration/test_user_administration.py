"""Managing accounts.

The two refusals are the point. An admin who changes their own role by mistake can lock the last
operator out of every console screen, recoverable only from a shell on the server.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.enums import Role
from accounts.services import role_of
from tests.factories import InstitutionFactory

pytestmark = pytest.mark.django_db


def test_an_admin_lists_accounts(auth_client: APIClient, candidate_user: Any) -> None:
    rows = auth_client.get("/api/users/").json()["results"]

    assert {row["username"] for row in rows} >= {"operator", "candidate"}


def test_the_list_reports_each_role(auth_client: APIClient, candidate_user: Any) -> None:
    rows = auth_client.get("/api/users/").json()["results"]

    by_name = {row["username"]: row["role"] for row in rows}
    assert (by_name["operator"], by_name["candidate"]) == ("ADMIN", "CANDIDATE")


def test_a_password_is_never_returned(auth_client: APIClient, candidate_user: Any) -> None:
    rows = auth_client.get("/api/users/").json()["results"]

    assert all("password" not in row for row in rows)


def test_a_manager_can_read_but_not_change(manager_client: APIClient, candidate_user: Any) -> None:
    """Knowing who is in the system is part of running it; changing them is not."""
    assert manager_client.get("/api/users/").status_code == 200
    assert (
        manager_client.post(
            f"/api/users/{candidate_user.pk}/set-role/", {"role": "ADMIN"}, format="json"
        ).status_code
        == 403
    )


def test_a_candidate_cannot_see_the_account_list(candidate_client: APIClient) -> None:
    assert candidate_client.get("/api/users/").status_code == 403


def test_an_admin_can_create_an_account(auth_client: APIClient) -> None:
    response = auth_client.post(
        "/api/users/",
        {
            "username": "newperson",
            "email": "newperson@example.test",
            "password": "a-perfectly-fine-passphrase",
            "role": "MANAGER",
        },
        format="json",
    )

    assert response.status_code == 201
    assert role_of(User.objects.get(username="newperson")) is Role.MANAGER


def test_an_admin_created_account_can_sign_in_immediately(auth_client: APIClient) -> None:
    """No verification round trip: the admin confirmed the address by other means."""
    auth_client.post(
        "/api/users/",
        {
            "username": "newperson",
            "email": "newperson@example.test",
            "password": "a-perfectly-fine-passphrase",
        },
        format="json",
    )

    response = APIClient().post(
        "/api/auth/login/",
        {"username": "newperson", "password": "a-perfectly-fine-passphrase"},
        format="json",
    )

    assert "token" in response.json()


def test_a_duplicate_username_is_refused(auth_client: APIClient, candidate_user: Any) -> None:
    response = auth_client.post(
        "/api/users/",
        {
            "username": candidate_user.username,
            "email": "other@example.test",
            "password": "a-perfectly-fine-passphrase",
        },
        format="json",
    )

    assert response.status_code == 400


def test_a_created_account_cannot_be_a_superuser(auth_client: APIClient) -> None:
    """`is_superuser` is not a field here, so naming it changes nothing."""
    auth_client.post(
        "/api/users/",
        {
            "username": "newperson",
            "email": "newperson@example.test",
            "password": "a-perfectly-fine-passphrase",
            "is_superuser": True,
            "is_staff": True,
        },
        format="json",
    )

    user = User.objects.get(username="newperson")
    assert (user.is_superuser, user.is_staff) == (False, False)


def test_an_admin_can_change_someone_elses_role(
    auth_client: APIClient, candidate_user: Any
) -> None:
    response = auth_client.post(
        f"/api/users/{candidate_user.pk}/set-role/", {"role": "MANAGER"}, format="json"
    )

    assert response.status_code == 200
    assert role_of(User.objects.get(pk=candidate_user.pk)) is Role.MANAGER


def test_an_admin_cannot_change_their_own_role(auth_client: APIClient, user: Any) -> None:
    """A plausible slip that locks the last operator out of every console screen."""
    response = auth_client.post(
        f"/api/users/{user.pk}/set-role/", {"role": "CANDIDATE"}, format="json"
    )

    assert response.status_code == 409
    assert role_of(User.objects.get(pk=user.pk)) is Role.ADMIN


def test_an_unknown_role_is_refused(auth_client: APIClient, candidate_user: Any) -> None:
    response = auth_client.post(
        f"/api/users/{candidate_user.pk}/set-role/", {"role": "SUPERUSER"}, format="json"
    )

    assert response.status_code == 400


def test_an_admin_can_assign_institutions_to_a_recruiter(
    auth_client: APIClient, recruiter_user: Any
) -> None:
    one, two = InstitutionFactory(), InstitutionFactory()

    response = auth_client.post(
        f"/api/users/{recruiter_user.pk}/set-institutions/",
        {"institutions": [one.slug, two.slug]},
        format="json",
    )

    assert response.status_code == 200
    assert {row["slug"] for row in response.json()["assigned_institutions"]} == {
        one.slug,
        two.slug,
    }


def test_reassigning_replaces_the_previous_set(auth_client: APIClient, recruiter_user: Any) -> None:
    old, new = InstitutionFactory(), InstitutionFactory()
    old.recruiters.add(recruiter_user)

    auth_client.post(
        f"/api/users/{recruiter_user.pk}/set-institutions/",
        {"institutions": [new.slug]},
        format="json",
    )

    assert list(recruiter_user.assigned_institutions.values_list("slug", flat=True)) == [new.slug]


def test_assigning_institutions_to_a_non_recruiter_is_refused(
    auth_client: APIClient, candidate_user: Any
) -> None:
    institution = InstitutionFactory()

    response = auth_client.post(
        f"/api/users/{candidate_user.pk}/set-institutions/",
        {"institutions": [institution.slug]},
        format="json",
    )

    assert response.status_code == 409


def test_an_unknown_institution_slug_is_refused(
    auth_client: APIClient, recruiter_user: Any
) -> None:
    response = auth_client.post(
        f"/api/users/{recruiter_user.pk}/set-institutions/",
        {"institutions": ["not-a-real-institution"]},
        format="json",
    )

    assert response.status_code == 400


def test_a_manager_cannot_assign_institutions(
    manager_client: APIClient, recruiter_user: Any
) -> None:
    institution = InstitutionFactory()

    response = manager_client.post(
        f"/api/users/{recruiter_user.pk}/set-institutions/",
        {"institutions": [institution.slug]},
        format="json",
    )

    assert response.status_code == 403


def test_deactivating_stops_the_account_working(
    auth_client: APIClient, candidate_user: Any, candidate_client: APIClient
) -> None:
    auth_client.post(f"/api/users/{candidate_user.pk}/deactivate/")

    candidate_user.refresh_from_db()
    assert candidate_user.is_active is False
    assert not Token.objects.filter(user=candidate_user).exists()
    assert candidate_client.get("/api/jobs/").status_code == 401


def test_an_admin_cannot_deactivate_themselves(auth_client: APIClient, user: Any) -> None:
    assert auth_client.post(f"/api/users/{user.pk}/deactivate/").status_code == 409


def test_reactivating_restores_access(auth_client: APIClient, candidate_user: Any) -> None:
    auth_client.post(f"/api/users/{candidate_user.pk}/deactivate/")

    auth_client.post(f"/api/users/{candidate_user.pk}/reactivate/")

    candidate_user.refresh_from_db()
    assert candidate_user.is_active is True


def test_an_admin_can_set_a_password(auth_client: APIClient, candidate_user: Any) -> None:
    response = auth_client.post(
        f"/api/users/{candidate_user.pk}/set-password/",
        {"password": "a-perfectly-fine-passphrase"},
        format="json",
    )

    assert response.status_code == 204
    candidate_user.refresh_from_db()
    assert candidate_user.check_password("a-perfectly-fine-passphrase")


def test_setting_a_password_revokes_existing_tokens(
    auth_client: APIClient, candidate_user: Any
) -> None:
    Token.objects.get_or_create(user=candidate_user)

    auth_client.post(
        f"/api/users/{candidate_user.pk}/set-password/",
        {"password": "a-perfectly-fine-passphrase"},
        format="json",
    )

    assert not Token.objects.filter(user=candidate_user).exists()


def test_a_weak_password_is_refused(auth_client: APIClient, candidate_user: Any) -> None:
    response = auth_client.post(
        f"/api/users/{candidate_user.pk}/set-password/", {"password": "password"}, format="json"
    )

    assert response.status_code == 400
