"""Confirm an account's address without sending an email.

For when mail is not set up, did not arrive, or the person lost access to the address.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.enums import Role
from accounts.services import ensure_account


class Command(BaseCommand):
    """Mark a user's address confirmed and let them sign in."""

    help = "Confirm a user's email address and activate the account."

    def add_arguments(self, parser: Any) -> None:
        """Take the username, and optionally the role to put them in."""
        parser.add_argument("username")
        parser.add_argument(
            "--role",
            choices=Role.values(),
            help="Also set the role. Left alone when not given.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Activate the account, reporting what changed."""
        username = options["username"]
        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"No user named {username!r}.")

        account = ensure_account(user)
        if options["role"]:
            account.role = Role(options["role"])
        account.email_verified_at = account.email_verified_at or timezone.now()
        account.save(update_fields=["role", "email_verified_at"])

        user.is_active = True
        user.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS(f"{username}: confirmed, active, role {account.role}"))
