"""Fix command for the ``accounts.W001`` check.

The migration and the signal should make it unnecessary. When the check does fire, this is the
fix.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from accounts.services import backfill_missing_accounts


class Command(BaseCommand):
    """Give every user without an account row the default role for their kind."""

    help = "Create UserAccount rows for any users missing one."

    def handle(self, *args: Any, **options: Any) -> None:
        """Create the missing rows and report the count."""
        created = backfill_missing_accounts()
        self.stdout.write(f"user accounts: {created} created")
