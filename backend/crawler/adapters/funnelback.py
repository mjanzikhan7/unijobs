"""Funnelback (Squiz Cloud) search-powered careers listings.

Recognise it by the ``funnelback`` string appearing anywhere in the page - its own hosted search
backend is referenced in every result's tracking redirect link.
Quirk: the real target URL is not the link's own ``href`` (a tracking redirect) but its ``title``
attribute. Plain server-rendered HTML, no browser needed. Pagination follows the "Next" link
rather than a computed page count.
Example: https://www.derby.ac.uk/jobs/current-vacancies/ - University of Derby.
"""

from __future__ import annotations

from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_MAX_PAGES = 20


@register_adapter
class FunnelbackAdapter(BaseAdapter):
    """Plain HTTP, ``start_rank`` pagination, reads each result's ``course-teaser-key-stat``s."""

    platform: ClassVar[Platform] = Platform.FUNNELBACK

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Funnelback's own hosted search backend."""
        return "funnelback" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Follow the "Next" link across pages, reading every ``search-result`` directly."""
        url = institution.careers_url
        vacancies: list[RawVacancy] = []
        next_url: str | None = url
        for _ in range(_MAX_PAGES):
            if next_url is None:
                break
            response = self.http.get(next_url)
            self.guard(response.text, next_url)
            base_url = response.url or next_url

            soup = soup_of(response.text)
            for card in soup.find_all("section", class_="search-result"):
                if not isinstance(card, Tag):
                    continue
                vacancy = self._read_card(card, base_url, institution)
                if vacancy is not None:
                    vacancies.append(vacancy)

            next_url = self._next_page_url(soup, base_url)
        return vacancies

    @staticmethod
    def _next_page_url(soup: Tag, base_url: str) -> str | None:
        """The pagination link whose own ``title`` attribute says "Next" - absent on the last."""
        link = soup.find("a", attrs={"title": "Next"}, href=True)
        if not isinstance(link, Tag):
            return None
        return absolutise(base_url, str(link["href"]))

    def _read_card(
        self, card: Tag, base_url: str, institution: InstitutionRef
    ) -> RawVacancy | None:
        link = card.select_one(".search-result-heading .h5 a")
        title = cell_text(link) if isinstance(link, Tag) else ""
        target = str(link.get("title") or "") if isinstance(link, Tag) else ""
        if not title or not target:
            return None
        source_url = absolutise(base_url, target)

        fields: dict[str, str] = {}
        for stat in card.find_all(class_="course-teaser-key-stat"):
            if not isinstance(stat, Tag):
                continue
            label_tag = stat.find(class_="course-teaser-key-stat-label")
            value_tag = stat.find(class_="course-teaser-key-stat-content")
            if not isinstance(label_tag, Tag) or not isinstance(value_tag, Tag):
                continue
            fields[cell_text(label_tag).casefold()] = cell_text(value_tag)

        closing_raw = fields.get("closing date", "")
        reference = source_url.rstrip("/").rsplit("/", 1)[-1]

        return RawVacancy(
            source_url=source_url,
            title=title,
            institution_slug=institution.slug,
            reference=reference,
            hours_raw=fields.get("post type", ""),
            contract_raw=fields.get("contract type", ""),
            salary_raw=fields.get("salary", ""),
            closing_date=parse_uk_date(closing_raw) if closing_raw else None,
            strategy=self.strategy,
        )
