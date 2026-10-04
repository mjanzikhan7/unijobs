"""Celery application.

The schedule is ``settings.CELERY_BEAT_SCHEDULE``. Times are Europe/London, so 06:00 means
06:00 local time in summer and winter.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("hejobs")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
