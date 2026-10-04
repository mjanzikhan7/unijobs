"""Typed access to the crawler settings.

``settings.CRAWLER`` is a plain dict, so a type checker sees every value as ``object``. This
dataclass checks the politeness numbers once, in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings


@dataclass(frozen=True, slots=True)
class CrawlerConfig:
    """Every knob the crawler has, with a real type on it."""

    contact_email: str
    user_agent_name: str
    host_concurrency: int
    min_host_delay_seconds: float
    host_delay_jitter_seconds: float
    request_timeout_seconds: float
    max_retries: int
    raw_cache_dir: Path
    raw_cache_ttl_days: int
    playwright_enabled: bool
    playwright_timeout_ms: int
    run_stale_after_minutes: int
    max_detail_fetches_per_institution: int

    @property
    def user_agent(self) -> str:
        """A User-Agent that says who we are and how to contact us.

        A site's IT staff should be able to see who is crawling them and ask us to stop.
        """
        return f"{self.user_agent_name}/1.0 (+mailto:{self.contact_email})"


def crawler_config() -> CrawlerConfig:
    """Read ``settings.CRAWLER`` into a typed object."""
    raw: dict[str, Any] = settings.CRAWLER
    return CrawlerConfig(
        contact_email=str(raw["CONTACT_EMAIL"]),
        user_agent_name=str(raw["USER_AGENT_NAME"]),
        host_concurrency=int(raw["HOST_CONCURRENCY"]),
        min_host_delay_seconds=float(raw["MIN_HOST_DELAY_SECONDS"]),
        host_delay_jitter_seconds=float(raw["HOST_DELAY_JITTER_SECONDS"]),
        request_timeout_seconds=float(raw["REQUEST_TIMEOUT_SECONDS"]),
        max_retries=int(raw["MAX_RETRIES"]),
        raw_cache_dir=Path(str(raw["RAW_CACHE_DIR"])),
        raw_cache_ttl_days=int(raw["RAW_CACHE_TTL_DAYS"]),
        playwright_enabled=bool(raw["PLAYWRIGHT_ENABLED"]),
        playwright_timeout_ms=int(raw["PLAYWRIGHT_TIMEOUT_MS"]),
        run_stale_after_minutes=int(raw["RUN_STALE_AFTER_MINUTES"]),
        max_detail_fetches_per_institution=int(raw["MAX_DETAIL_FETCHES_PER_INSTITUTION"]),
    )
