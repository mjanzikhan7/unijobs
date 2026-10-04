"""Startup check that no user is missing a role.

A user with no account row is treated as ``CANDIDATE``. That is safe, but an admin would lose
access without any message. This check shows it. It is a warning, not an error, because an
error would also block the ``migrate`` that fixes it.
"""

from __future__ import annotations

from typing import Any

from django.apps import AppConfig
from django.core.checks import Warning as CheckWarning
from django.core.checks import register
from django.db.utils import DatabaseError


@register("accounts")
def check_every_user_has_an_account(
    app_configs: list[AppConfig] | None, **kwargs: Any
) -> list[CheckWarning]:
    """Warn if any active user lacks a ``UserAccount``."""
    from django.contrib.auth import get_user_model

    try:
        missing = list(
            get_user_model()
            .objects.filter(is_active=True, account__isnull=True)
            .values_list("username", flat=True)[:10]
        )
    except DatabaseError:
        return []

    if not missing:
        return []

    return [
        CheckWarning(
            f"{len(missing)} active user(s) have no UserAccount and resolve to CANDIDATE: "
            f"{', '.join(missing)}",
            hint="Run `manage.py backfill_user_accounts`.",
            id="accounts.W001",
        )
    ]
