"""The ownership backfill's owner-resolution rule.

The migration ran once, on the operator's own database, against rows that mattered - their saved
jobs and their application history. A wrong owner there is silent and unrecoverable, so the rule
that decides is worth pinning down: it must resolve the unambiguous cases and refuse the rest,
never fall back to "the first user we found".

Tested by calling the resolver directly with the live app registry rather than by replaying
migrations, which would mean taking on a test-only migration dependency to assert one function.
"""

from __future__ import annotations

import pytest
from django.apps import apps as live_apps
from django.contrib.auth.models import User

from jobs.migrations import _0004_helpers as helpers

pytestmark = pytest.mark.django_db


def test_a_lone_superuser_is_the_owner() -> None:
    """The ordinary case: one operator, who owns everything that already exists."""
    operator = User.objects.create_user(username="jkhan", is_superuser=True)
    User.objects.create_user(username="someone-else")

    assert helpers.sole_owner(live_apps).pk == operator.pk


def test_a_lone_user_is_the_owner_even_without_superuser() -> None:
    """An install whose only account was never promoted still has an unambiguous answer."""
    only = User.objects.create_user(username="only")

    assert helpers.sole_owner(live_apps).pk == only.pk


def test_two_superusers_are_refused() -> None:
    User.objects.create_user(username="one", is_superuser=True)
    User.objects.create_user(username="two", is_superuser=True)

    with pytest.raises(helpers.AmbiguousOwner, match="Cannot decide who owns"):
        helpers.sole_owner(live_apps)


def test_several_plain_users_are_refused() -> None:
    """The dangerous case: no superuser, several candidates, and no way to tell them apart."""
    User.objects.create_user(username="one")
    User.objects.create_user(username="two")

    with pytest.raises(helpers.AmbiguousOwner, match="Cannot decide who owns"):
        helpers.sole_owner(live_apps)


def test_no_users_at_all_is_refused() -> None:
    with pytest.raises(helpers.AmbiguousOwner):
        helpers.sole_owner(live_apps)
