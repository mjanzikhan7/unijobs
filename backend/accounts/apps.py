"""App configuration for :mod:`accounts`."""

from __future__ import annotations

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """User roles and verification state."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self) -> None:
        """Register the signal and the startup check."""
        from accounts import checks, signals  # noqa: F401  (imported for the side effect)
