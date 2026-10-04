"""University of Dundee's own careers listing, a Drupal Views build on ``dundee.ac.uk`` itself.

Recognise it by the ``card--job-opportunity`` class Drupal's own Views markup carries on every
result card.
Quirk: plain server-rendered HTML, no browser needed. No pager has been observed (12 live
results fit on one page), so none is implemented. No reference field is published on its own;
the URL slug is read instead of parsing it back out of the title text.
Example: https://www.dundee.ac.uk/work-for-us/jobs?search_api_fulltext= - University of Dundee.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CARD_SELECTOR = "article.card--job-opportunity"
_CLOSING_DATE_PREFIX_RE = re.compile(r"^closing date\s*:\s*", re.IGNORECASE)
_REFERENCE_FROM_URL_RE = re.compile(r"/([^/]+)/?$")


@register_adapter
class DundeeVacancyCardsAdapter(BaseAdapter):
    """Plain HTTP fetch of the one listing page - no browser needed, confirmed live."""

    platform: ClassVar[Platform] = Platform.DUNDEE_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Drupal's own ``card--job-opportunity`` class from this exact Views build."""
        return "card--job-opportunity" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Plain-fetch the one listing page and read every job-opportunity card directly."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.select(_CARD_SELECTOR):
            if not isinstance(card, Tag):
                continue
            link = card.select_one("h3.card__title a")
            if not isinstance(link, Tag):
                continue
            href = str(link.get("href") or "")
            title = cell_text(link)
            if not title or not href:
                continue
            source_url = absolutise(base_url, href)

            summary_text = cell_text(card.select_one(".card__summary"))
            closing_raw = _CLOSING_DATE_PREFIX_RE.sub("", summary_text)

            meta_text = cell_text(card.select_one("li.card__meta-item"))
            segments = [segment.strip() for segment in meta_text.split("|")]
            salary_raw = segments[0] if segments else ""
            location_raw = " | ".join(segments[1:])

            ref_match = _REFERENCE_FROM_URL_RE.search(href)

            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    reference=ref_match.group(1).upper() if ref_match else "",
                    salary_raw=salary_raw,
                    location_raw=location_raw,
                    closing_date=parse_uk_date(closing_raw) if closing_raw else None,
                    strategy=self.strategy,
                )
            )
        return vacancies
