"""Choosing and building the HTTP client and browser session for a crawl.

See ``crawler.services`` for the full crawl of one institution.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from crawler.browser import BrowserUnavailable, PlaywrightSession
from crawler.cache import DiskRawCache
from crawler.config import crawler_config
from crawler.http import PoliteHttpClient
from crawler.persistence import DatabaseResponseRecorder
from crawler.rate_limit import HostDelayPolicy
from institutions.enums import Platform
from institutions.models import Institution

logger = logging.getLogger(__name__)


def build_http_client() -> PoliteHttpClient:
    """Build the production HTTP client from settings."""
    config = crawler_config()
    return PoliteHttpClient(
        user_agent=config.user_agent,
        cache=DiskRawCache(root=config.raw_cache_dir),
        recorder=DatabaseResponseRecorder(),
        timeout_seconds=config.request_timeout_seconds,
        max_retries=config.max_retries,
        delay_policy=HostDelayPolicy(
            min_delay_seconds=config.min_host_delay_seconds,
            jitter_seconds=config.host_delay_jitter_seconds,
        ),
    )


_BROWSER_PLATFORMS: dict[Platform, str] = {
    Platform.JOBTRAIN: "listing shows 0 jobs matching until its JS has run",
    Platform.COREHR_CATEGORISED: "its marketing-page discovery step still benefits from one",
    Platform.EPLOY: "listing is client-rendered",
    Platform.SUCCESSFACTORS: "listing is client-rendered",
    Platform.ENGAGE_ATS: "listing only exists after a browser mints its token",
    Platform.LIPA_VACANCY_CARDS: "listing is entirely client-rendered",
    Platform.NORWICH_VACANCY_CARDS: "listing only; its detail pages are plain HTTP",
    Platform.LEEDS_ARTS_VACANCY_CARDS: "listing only; its detail pages are plain HTTP",
    Platform.TALEO: "listing is client-rendered, same shape as Jobtrain",
    Platform.POSTINGPANDA: "AngularJS app; a plain fetch sees only template placeholders",
    Platform.MHR_PEOPLE_FIRST: "modern Angular app, entirely client-rendered",
    Platform.GUILDHALL_VACANCY_CARDS: "listing only; its detail pages are plain HTTP",
    Platform.HIREFUL_CMS: "cards populated by client-side JS against a private CMS API",
    Platform.UNKNOWN: "detection may land on a platform that needs one",
}


def needs_browser(institution: Institution) -> bool:
    """Whether this institution's platform needs Chromium to show its list.

    A platform that is not set yet counts as ``UNKNOWN``. The command line and the Celery task both
    use this, so they always agree.
    """
    platform = institution.effective_platform
    return platform == "" or platform in _BROWSER_PLATFORMS


def build_browser_session(
    before_navigation: Callable[[str], None] | None = None,
) -> PlaywrightSession | None:
    """Start a browser session, or return ``None`` when the browser is turned off.

    ``None`` instead of an error. Most sites work over plain HTTP, so a missing browser should only
    affect the few sites that need one.
    """
    config = crawler_config()
    if not config.playwright_enabled:
        return None
    session = PlaywrightSession(
        user_agent=config.user_agent,
        timeout_ms=config.playwright_timeout_ms,
        before_navigation=before_navigation,
    )
    try:
        session.start()
    except BrowserUnavailable:
        logger.warning("playwright unavailable; JS-rendered portals will be skipped")
        return None
    return session
