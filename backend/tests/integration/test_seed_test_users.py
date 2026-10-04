"""The browser test accounts."""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

from accounts.services import role_of

pytestmark = pytest.mark.django_db


def test_creates_a_candidate_and_an_admin(settings: Any) -> None:
    settings.DEBUG = True

    call_command("seed_test_users")

    assert str(role_of(User.objects.get(username="e2e-candidate"))) == "CANDIDATE"
    assert str(role_of(User.objects.get(username="e2e-admin"))) == "ADMIN"
    assert User.objects.get(username="e2e-admin").check_password("e2e-password")


def test_is_safe_to_repeat(settings: Any) -> None:
    settings.DEBUG = True

    call_command("seed_test_users")
    call_command("seed_test_users")

    assert User.objects.filter(username__startswith="e2e-").count() == 2


def test_refuses_to_run_with_debug_off(settings: Any) -> None:
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_test_users")
    assert not User.objects.filter(username__startswith="e2e-").exists()
