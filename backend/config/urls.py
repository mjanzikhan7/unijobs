"""Root URL configuration. Everything is under ``/api/``.

Django's admin is **not** mounted by default. Nothing here uses it, and it would add a second
login form without the API's rate limits.

Set ``DJANGO_ENABLE_DJANGO_ADMIN=1`` to mount it for debugging.
"""

from __future__ import annotations

from django.urls import include, path

from config.env import env_bool

urlpatterns = [
    path("api/", include("api.urls")),
]

if env_bool("DJANGO_ENABLE_DJANGO_ADMIN", False):
    from django.contrib import admin

    urlpatterns.insert(0, path("admin/", admin.site.urls))
