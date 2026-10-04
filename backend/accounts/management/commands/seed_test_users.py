"""``manage.py seed_test_users``: create the accounts the browser tests sign in with.

Creates ``e2e-candidate`` (CANDIDATE) and ``e2e-admin`` (ADMIN), confirmed and active, with the
password in ``E2E_PASSWORD``. Safe to repeat. It refuses to run when ``DEBUG`` is off, so it can
never add a known password to a production database.
"""

from __future__ import annotations

import os
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.enums import Role
from accounts.services import ensure_account

TEST_USERS = {"e2e-candidate": Role.CANDIDATE, "e2e-admin": Role.ADMIN}


class Command(BaseCommand):
    """Create or reset the browser test accounts."""

    help = "Create the e2e-candidate and e2e-admin accounts (development and CI only)."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create each account, or reset its role and password."""
        if not settings.DEBUG:
            raise CommandError("Refusing to create test accounts while DEBUG is off.")
        password = os.environ.get("E2E_PASSWORD", "e2e-password")
        for username, role in TEST_USERS.items():
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@example.test"}
            )
            user.is_active = True
            user.set_password(password)
            user.save()
            account = ensure_account(user)
            account.role = role
            account.email_verified_at = account.email_verified_at or timezone.now()
            account.save(update_fields=["role", "email_verified_at"])
            action = "created" if created else "reset"
            self.stdout.write(self.style.SUCCESS(f"{username}: {action}, role {role}"))
