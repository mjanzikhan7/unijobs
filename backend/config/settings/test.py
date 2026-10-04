"""Test settings.

Tasks run straight away, so tests need no worker. Nothing may use the network:
``tests/conftest.py`` fails any test that opens a socket.
"""

from __future__ import annotations

from config.settings.base import *  # noqa: F403
from config.settings.base import BASE_DIR, CRAWLER, MIDDLEWARE

MIDDLEWARE = [item for item in MIDDLEWARE if "whitenoise" not in item]

DEBUG = False
SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["*", "testserver"]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DIGEST_ENABLED = True

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

MEDIA_ROOT = str(BASE_DIR / ".media-test")

CRAWLER = {
    **CRAWLER,
    "MIN_HOST_DELAY_SECONDS": 2.0,
    "HOST_DELAY_JITTER_SECONDS": 0.0,
    "PLAYWRIGHT_ENABLED": False,
    "RAW_CACHE_DIR": BASE_DIR / ".rawcache-test",
    "MAX_RETRIES": 3,
    "MAX_DETAIL_FETCHES_PER_INSTITUTION": 0,
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
