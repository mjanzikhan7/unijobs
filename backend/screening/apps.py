"""App configuration for :mod:`screening`."""

from __future__ import annotations

from django.apps import AppConfig


class ScreeningConfig(AppConfig):
    """Sponsorship and salary screening."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "screening"
