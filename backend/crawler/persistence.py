"""Writing crawl records to the database.

Kept apart from :mod:`crawler.http`, so the HTTP client stays free of Django. Adapters and
their tests never use this module.
"""

from __future__ import annotations

import logging

from django.core.exceptions import SynchronousOnlyOperation

from crawler.cache import CacheEntry
from crawler.models import RawResponse
from crawler.types import FetchResponse

logger = logging.getLogger(__name__)


class DatabaseResponseRecorder:
    """Records fetch details and gives the values for conditional requests.

    Both methods survive ``SynchronousOnlyOperation`` instead of crashing a crawl.
    """

    def record(self, entry: CacheEntry, response: FetchResponse) -> None:
        """Store metadata for one cached body, keyed by its content hash."""
        try:
            RawResponse.objects.update_or_create(
                cache_key=entry.key,
                defaults={
                    "url": entry.url[:1000],
                    "sha256": entry.sha256,
                    "status_code": response.status_code,
                    "content_type": response.content_type[:200],
                    "etag": response.headers.get("etag", "")[:300],
                    "last_modified": response.headers.get("last-modified", "")[:200],
                    "byte_size": entry.byte_size,
                    "fetched_at": entry.stored_at,
                    "storage_path": str(entry.path)[:500],
                },
            )
        except SynchronousOnlyOperation:
            logger.warning(
                "could not record fetch metadata for %s: a browser session is open in this "
                "thread. The body is still cached to disk; only this response's metadata row "
                "and its conditional-request validators are skipped.",
                entry.url,
            )

    def validators_for(self, url: str) -> tuple[str, str]:
        """Return ``(etag, last_modified)`` from the newest saved fetch of ``url``.

        Returns ``("", "")`` instead of raising. That means a full fetch instead of a conditional
        one,
        which is always a correct fallback.
        """
        try:
            row = (
                RawResponse.objects.filter(url=url[:1000])
                .order_by("-fetched_at")
                .values("etag", "last_modified")
                .first()
            )
        except SynchronousOnlyOperation:
            logger.warning(
                "could not read cached validators for %s: a browser session is open in this "
                "thread. Fetching it in full instead of conditionally.",
                url,
            )
            return "", ""
        if row is None:
            return "", ""
        return row["etag"] or "", row["last_modified"] or ""

    def cache_key_for(self, url: str) -> str | None:
        """Return the cache key of the newest saved fetch of ``url``, or ``None``.

        When the server answers 304 ("not changed"), this is the content it means.
        """
        try:
            row = (
                RawResponse.objects.filter(url=url[:1000])
                .order_by("-fetched_at")
                .values("cache_key")
                .first()
            )
        except SynchronousOnlyOperation:
            logger.warning(
                "could not read the cache key for %s: a browser session is open in this "
                "thread. A 304 here will be answered with empty text instead of the cached body.",
                url,
            )
            return None
        return row["cache_key"] if row else None
