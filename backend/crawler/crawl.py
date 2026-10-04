"""Fetching one institution's vacancies, and turning every failure into a typed outcome.

See ``crawler.services`` for the full crawl: fetch, detect, list, diff, save, screen.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from crawler.adapter_resolution import institution_ref, probe_portal, resolve_adapter
from crawler.adapters.base import BaseAdapter
from crawler.differ import deduplicate
from crawler.enrichment import enrich_missing_details
from crawler.enums import CrawlOutcome, ExtractionStrategy
from crawler.exceptions import AdapterError, outcome_for
from crawler.registry import detect_adapter
from crawler.types import BrowserSession, HttpClient, ProbeResult, RawVacancy
from institutions.enums import Platform
from institutions.models import Institution

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class InstitutionOutcome:
    """What happened when one institution was crawled."""

    outcome: CrawlOutcome
    vacancies: tuple[RawVacancy, ...] = ()
    strategy: ExtractionStrategy = ExtractionStrategy.NONE
    adapter: str = ""
    platform: Platform = Platform.UNKNOWN
    fallback_fired: bool = False
    error_class: str = ""
    error_detail: str = ""
    cache_keys: tuple[str, ...] = ()


def crawl_one(
    institution: Institution,
    *,
    http: HttpClient,
    browser: BrowserSession | None,
    max_detail_fetches: int = 0,
) -> InstitutionOutcome:
    """Fetch one institution's vacancies, and turn a failure into an outcome.

    The only place in the crawl where a broad ``except`` is allowed. An unexpected error becomes
    ``PARSE_ERROR``, which never closes jobs, so an adapter bug cannot delete anybody's jobs.
    """
    ref = institution_ref(institution)
    if not ref.careers_url:
        return InstitutionOutcome(
            outcome=CrawlOutcome.SKIPPED, error_detail="No careers URL configured."
        )

    adapter: BaseAdapter | None = None
    probe_fallback_fired = False
    try:
        probe = probe_portal(ref, http)

        if (
            browser is not None
            and not institution.adapter_override
            and detect_adapter(ref, probe) is None
        ):
            rendered = browser.render(ref.careers_url)
            probe = ProbeResult(
                url=ref.careers_url,
                status_code=rendered.status_code,
                html=rendered.text,
                headers=rendered.headers,
                final_url=rendered.url,
            )
            probe_fallback_fired = True

        adapter = resolve_adapter(institution, ref, probe, http=http, browser=browser)
        vacancies = deduplicate(adapter.list_vacancies(ref))
        vacancies = enrich_missing_details(
            vacancies, adapter=adapter, max_fetches=max_detail_fetches
        )
    except AdapterError as error:
        return InstitutionOutcome(
            outcome=outcome_for(error),
            adapter=type(adapter).__name__ if adapter else "",
            error_class=type(error).__name__,
            error_detail=str(error),
            cache_keys=_cache_keys(http),
        )
    except Exception as error:
        logger.exception("unexpected error crawling %s", institution.slug)
        return InstitutionOutcome(
            outcome=CrawlOutcome.PARSE_ERROR,
            adapter=type(adapter).__name__ if adapter else "",
            error_class=type(error).__name__,
            error_detail=str(error),
            cache_keys=_cache_keys(http),
        )

    return InstitutionOutcome(
        outcome=CrawlOutcome.OK if vacancies else CrawlOutcome.ZERO_RESULTS,
        vacancies=tuple(vacancies),
        strategy=adapter.strategy,
        adapter=type(adapter).__name__,
        platform=adapter.platform,
        fallback_fired=probe_fallback_fired or adapter.fallback_fired,
        cache_keys=_cache_keys(http),
    )


def _cache_keys(http: HttpClient) -> tuple[str, ...]:
    """Collect and reset the cache keys written during one institution's crawl."""
    keys = getattr(http, "cache_keys", None)
    if not isinstance(keys, list):
        return ()
    collected = tuple(keys)
    keys.clear()
    return collected
