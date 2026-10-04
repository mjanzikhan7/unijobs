"""Project configuration: settings, Celery wiring and the root URL conf."""

from __future__ import annotations

from config.celery import app as celery_app

__all__ = ["celery_app"]
