"""App configuration for :mod:`institutions`."""

from __future__ import annotations

from django.apps import AppConfig


class InstitutionsConfig(AppConfig):
    """Institutions and their careers portals."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "institutions"
