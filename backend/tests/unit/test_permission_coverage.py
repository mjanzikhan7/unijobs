"""Every routed view must say who it serves.

``RoleRequired`` denies a view that declares no ``required_roles``, which fails safe but only at
request time - and a 403 nobody exercises is a 403 nobody notices. This asserts the declaration
exists at import time instead, so a new endpoint is covered the moment it is registered rather
than the first time someone happens to call it.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from accounts.enums import Role
from api.permissions import RoleRequired

_PUBLIC: frozenset[str] = frozenset(
    {
        "HealthView",
        "MetricsView",
        "LoginView",
        "RegisterView",
        "VerifyEmailView",
        "PasswordResetRequestView",
        "PasswordResetConfirmView",
        "ConfirmEmailChangeView",
    }
)

_FIRST_PARTY_PREFIX = "api."


def _iter_view_classes(patterns: list[Any], seen: set[str]) -> list[type]:
    """Collect every distinct view class reachable from the URL conf."""
    found: list[type] = []
    for entry in patterns:
        if isinstance(entry, URLResolver):
            found.extend(_iter_view_classes(entry.url_patterns, seen))
            continue
        if not isinstance(entry, URLPattern):
            continue

        view_class = getattr(entry.callback, "cls", None) or getattr(
            entry.callback, "view_class", None
        )
        if view_class is None or view_class.__name__ in seen:
            continue
        seen.add(view_class.__name__)
        found.append(view_class)
    return found


def _routed_views() -> list[type]:
    return [
        view
        for view in _iter_view_classes(get_resolver().url_patterns, set())
        if view.__module__.startswith(_FIRST_PARTY_PREFIX)
    ]


def test_the_url_conf_actually_resolves_views() -> None:
    """Guard the guard: an empty walk would make every assertion below vacuous."""
    assert len(_routed_views()) >= 10


@pytest.mark.parametrize("view_class", _routed_views(), ids=lambda cls: cls.__name__)
def test_every_view_declares_who_it_serves(view_class: type) -> None:
    """Each routed view names its roles, or is on the public allowlist - never neither."""
    name = view_class.__name__
    declared = getattr(view_class, "required_roles", None)

    if name in _PUBLIC:
        assert declared is None, f"{name} is on the public allowlist but also declares roles"
        return

    assert declared is not None, (
        f"{name} declares no `required_roles`, so RoleRequired will deny every request to it. "
        f"Add one, or add {name} to _PUBLIC with a reason."
    )
    assert set(declared) <= set(Role), f"{name} declares an unknown role: {declared}"


@pytest.mark.parametrize("view_class", _routed_views(), ids=lambda cls: cls.__name__)
def test_narrower_declarations_are_subsets(view_class: type) -> None:
    """A write or per-action rule may only narrow ``required_roles``, never widen it.

    Widening here would be invisible: the floor looks restrictive while the override quietly
    grants more.
    """
    declared = getattr(view_class, "required_roles", None)
    if declared is None:
        return
    allowed = set(declared)

    write = getattr(view_class, "required_roles_write", None)
    if write is not None:
        assert set(write) <= allowed, f"{view_class.__name__} widens access for writes"

    for action, roles in (getattr(view_class, "required_roles_by_action", None) or {}).items():
        assert set(roles) <= allowed, (
            f"{view_class.__name__}.{action} widens access beyond required_roles"
        )


def test_the_default_permission_is_role_required(settings: Any) -> None:
    """The whole scheme rests on this being the project-wide default."""
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == ["api.permissions.RoleRequired"]


def test_an_undeclared_view_is_denied() -> None:
    """The failure mode itself: no declaration means no access, for anyone."""

    class Undeclared:
        action = None

    class Anyone:
        is_authenticated = True

    assert RoleRequired().has_permission(_FakeRequest(Anyone()), Undeclared()) is False


class _FakeRequest:
    def __init__(self, user: Any) -> None:
        self.user = user
        self.method = "GET"
