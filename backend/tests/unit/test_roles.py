"""Role mechanics: how an account gets one, and what happens when it has none.

The "no account row" path matters more than it looks. It is the state a user reaches if a signal
is bypassed or a migration half-runs, and it must resolve towards *less* access, never more.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User

from accounts.enums import Role
from accounts.models import UserAccount
from accounts.services import backfill_missing_accounts, ensure_account, role_of
from api.permissions import ADMIN_ONLY, EVERY_ROLE, STAFF, RoleRequired


class _Request:
    def __init__(self, user: Any, method: str = "GET") -> None:
        self.user = user
        self.method = method


class _View:
    def __init__(self, **attributes: Any) -> None:
        self.action = attributes.pop("action", None)
        for key, value in attributes.items():
            setattr(self, key, value)


@pytest.mark.django_db
def test_a_new_user_gets_a_candidate_account() -> None:
    user = User.objects.create_user(username="new", password="x")

    assert user.account.role == Role.CANDIDATE
    assert role_of(user) is Role.CANDIDATE


@pytest.mark.django_db
def test_a_new_superuser_gets_an_admin_account() -> None:
    """`createsuperuser` is how the first operator exists, so it must not land as a candidate."""
    user = User.objects.create_superuser(username="root", password="x", email="")

    assert user.account.role == Role.ADMIN


@pytest.mark.django_db
def test_a_user_without_an_account_falls_back_to_least_privilege() -> None:
    user = User.objects.create_user(username="orphan", password="x")
    UserAccount.objects.filter(user=user).delete()
    user.refresh_from_db()

    assert role_of(user) is Role.CANDIDATE


@pytest.mark.django_db
def test_backfill_creates_only_the_missing_rows() -> None:
    kept = User.objects.create_user(username="kept", password="x")
    orphan = User.objects.create_user(username="orphan", password="x")
    UserAccount.objects.filter(user=orphan).delete()

    assert backfill_missing_accounts() == 1
    assert UserAccount.objects.filter(user=kept).count() == 1
    assert UserAccount.objects.filter(user=orphan).count() == 1


@pytest.mark.django_db
def test_ensure_account_is_idempotent() -> None:
    user = User.objects.create_user(username="twice", password="x")

    first = ensure_account(user)
    second = ensure_account(user)

    assert first.pk == second.pk


def test_role_of_an_anonymous_caller_is_none() -> None:
    class Anonymous:
        is_authenticated = False

    assert role_of(Anonymous()) is None  # type: ignore[arg-type]


class _User:
    is_authenticated = True

    def __init__(self, role: Role) -> None:
        self.account = type("Account", (), {"role": role.value})()
        self.pk = 1


@pytest.mark.parametrize(
    ("role", "expected"),
    [(Role.ADMIN, True), (Role.MANAGER, True), (Role.CANDIDATE, False)],
)
def test_staff_views_exclude_candidates(role: Role, expected: bool) -> None:
    view = _View(required_roles=STAFF)

    assert RoleRequired().has_permission(_Request(_User(role)), view) is expected


def test_a_view_with_no_declaration_denies_even_an_admin() -> None:
    """The default-deny posture is the point: no declaration means nobody, not everybody."""
    assert RoleRequired().has_permission(_Request(_User(Role.ADMIN)), _View()) is False


def test_write_roles_narrow_only_unsafe_methods() -> None:
    view = _View(required_roles=STAFF, required_roles_write=ADMIN_ONLY)
    manager = _User(Role.MANAGER)

    assert RoleRequired().has_permission(_Request(manager, "GET"), view) is True
    assert RoleRequired().has_permission(_Request(manager, "POST"), view) is False


def test_a_named_action_overrides_the_method_rule() -> None:
    """`review-queue` is a GET but an operator's tool - method alone cannot express that."""
    view = _View(
        required_roles=EVERY_ROLE,
        required_roles_by_action={"review_queue": STAFF},
        action="review_queue",
    )

    assert RoleRequired().has_permission(_Request(_User(Role.CANDIDATE)), view) is False
    assert RoleRequired().has_permission(_Request(_User(Role.MANAGER)), view) is True


def test_an_unnamed_action_falls_through_to_the_floor() -> None:
    view = _View(
        required_roles=EVERY_ROLE,
        required_roles_by_action={"review_queue": STAFF},
        action="list",
    )

    assert RoleRequired().has_permission(_Request(_User(Role.CANDIDATE)), view) is True
