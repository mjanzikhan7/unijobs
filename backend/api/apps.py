"""App configuration for :mod:`api`."""

from __future__ import annotations

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """The REST API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
