"""Local development settings."""

from __future__ import annotations

from config.settings.base import *  # noqa: F403
from config.settings.base import CSRF_TRUSTED_ORIGINS, REST_FRAMEWORK

DEBUG = True
ALLOWED_HOSTS = ["*"]

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, "http://frontend:5173"]
