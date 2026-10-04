"""App configuration for :mod:`analytics`."""

from __future__ import annotations

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Usage events and the aggregates built from them."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"
