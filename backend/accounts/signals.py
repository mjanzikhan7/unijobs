"""Give every new user an account row.

Users are created in several places (``createsuperuser``, sign-up, tests, the shell), and a
signal is the one hook they all pass through.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import ensure_account


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="accounts.create_user_account")
def create_user_account(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Create the account row for a newly created user."""
    if created:
        ensure_account(instance)
