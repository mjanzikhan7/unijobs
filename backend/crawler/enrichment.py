"""Filling in what a listing page left empty, by opening the vacancy's own page.

Some sites only show a title and a link in the list, and put the description and category on
the vacancy's page. Fitness scoring needs the description, and the category filters need the
category.

Limited per institution. The delay between requests does not change (it is the same
`HttpClient`), but the number of requests grows, so `max_fetches` limits it.
"""

from __future__ import annotations

import logging
from dataclasses import fields, replace

from crawler.adapters.base import BaseAdapter
from crawler.exceptions import AdapterError
from crawler.types import RawVacancy

logger = logging.getLogger(__name__)

MIN_DESCRIPTION_CHARS = 200

_ENRICHABLE_FIELDS: tuple[str, ...] = (
    "description_html",
    "description_text",
    "category",
    "department",
    "reference",
    "contract_raw",
    "hours_raw",
    "grade_raw",
)


def needs_detail_fetch(vacancy: RawVacancy) -> bool:
    """Whether a vacancy is thin enough to be worth spending a request on."""
    thin_description = len(vacancy.description_text.strip()) < MIN_DESCRIPTION_CHARS
    return thin_description or not vacancy.category


def _merge(listing: RawVacancy, detail: RawVacancy) -> RawVacancy:
    """Fill `listing`'s empty fields from `detail`. Never overwrites what the listing had.

    The listing page is trusted first, because the adapter was built and tested against it.
    """
    changes = {
        field.name: getattr(detail, field.name)
        for field in fields(listing)
        if field.name in _ENRICHABLE_FIELDS
        and not getattr(listing, field.name)
        and getattr(detail, field.name)
    }
    if not changes:
        return listing
    return replace(listing, **changes)


def enrich_missing_details(
    vacancies: list[RawVacancy],
    *,
    adapter: BaseAdapter,
    max_fetches: int,
) -> list[RawVacancy]:
    """Fill in the vacancies that gain the most, using at most `max_fetches` requests.

    The emptiest first. A vacancy with no description and no category gains more from one request
    than one that only lacks a category.
    """
    if max_fetches <= 0:
        return vacancies

    candidates = sorted(
        (vacancy for vacancy in vacancies if needs_detail_fetch(vacancy)),
        key=lambda vacancy: len(vacancy.description_text),
    )[:max_fetches]
    if not candidates:
        return vacancies

    enriched_by_url: dict[str, RawVacancy] = {}
    for vacancy in candidates:
        try:
            detail = replace(
                adapter.fetch_detail(vacancy.source_url), institution_slug=vacancy.institution_slug
            )
        except AdapterError as error:
            logger.info("could not enrich %s: %s", vacancy.source_url, error)
            continue
        except Exception:
            logger.exception("unexpected error enriching %s", vacancy.source_url)
            continue
        enriched_by_url[vacancy.source_url] = _merge(vacancy, detail)

    if not enriched_by_url:
        return vacancies
    return [enriched_by_url.get(vacancy.source_url, vacancy) for vacancy in vacancies]
