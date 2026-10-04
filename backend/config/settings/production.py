"""Production settings.

Strict on purpose. A missing secret stops the container. It never falls back to a
development default.
"""

from __future__ import annotations

import os
import secrets

from config.env import env_bool, env_int, env_list, env_secret
from config.settings.base import *  # noqa: F403
from config.settings.base import DATABASES

DEBUG = False

if os.environ.get("DJANGO_COLLECTSTATIC"):
    # The image build collects static files before any secret exists. A random key means
    # that setting this flag at run time can never leave a known key in use.
    SECRET_KEY = secrets.token_urlsafe(64)
else:
    SECRET_KEY = env_secret("DJANGO_SECRET_KEY", min_length=50)
    DATABASES["default"]["PASSWORD"] = env_secret("POSTGRES_PASSWORD")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]

SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "")
CORS_ALLOW_CREDENTIALS = False
