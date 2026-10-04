"""App configuration for :mod:`crawler`."""

from __future__ import annotations

from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    """Crawling university careers portals."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "crawler"

    def ready(self) -> None:
        """Import the adapter package so every adapter registers itself."""
        from crawler import adapters  # noqa: F401
