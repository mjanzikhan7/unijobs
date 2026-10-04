"""App configuration for :mod:`jobs`."""

from __future__ import annotations

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Vacancies, saves and the application pipeline."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"
