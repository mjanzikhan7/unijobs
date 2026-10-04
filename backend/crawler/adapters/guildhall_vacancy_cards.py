"""Guildhall School of Music & Drama's own careers listing cards, on ``gsmd.ac.uk`` itself.

Recognise it by the institution's own host - a bespoke Vue build with no third-party ATS
underneath it.
Quirk: the listing is client-rendered but each vacancy's detail page is plain server-rendered
HTML - the same listing/detail split as Norwich and Leeds Arts. Every field lives in one clean
``<dl>`` matched by label text; the closing date is read from its machine-readable ``<time
datetime="...">`` attribute rather than the text beside it.
Browser: yes - for the listing only; detail pages are plain HTTP.
Example: https://www.gsmd.ac.uk/jobs - Guildhall School of Music & Drama.
"""

from __future__ import annotations

from datetime import date
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_LISTING_LINK_SELECTOR = 'a[href*="/about-guildhall/vacancies/"]'


@register_adapter
class GuildhallVacancyCardsAdapter(BaseAdapter):
    """Renders the listing for titles/links, then a plain fetch of each detail page."""

    platform: ClassVar[Platform] = Platform.GUILDHALL_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Guildhall's own host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "gsmd.ac.uk" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the listing for every card's link, then fetch each detail page plainly."""
        url = institution.careers_url
        listing = self.render(url, wait_for_selector=_LISTING_LINK_SELECTOR)
        self.guard(listing.text, url)
        base_url = listing.url or url

        soup = soup_of(listing.text)
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        for link in soup.select(_LISTING_LINK_SELECTOR):
            if not isinstance(link, Tag):
                continue
            href = str(link.get("href") or "")
            if not href:
                continue
            source_url = absolutise(base_url, href)
            if source_url in seen:
                continue
            seen.add(source_url)

            vacancy = self._read_detail(source_url, institution)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _read_detail(self, url: str, institution: InstitutionRef) -> RawVacancy | None:
        """One vacancy's detail page - plain HTTP, no browser needed."""
        response = self.http.get(url)
        self.guard(response.text, url)
        soup = soup_of(response.text)

        heading = soup.find("h1")
        title = cell_text(heading) if isinstance(heading, Tag) else ""
        if not title:
            return None

        fields: dict[str, Tag] = {}
        for term in soup.find_all("dt"):
            if not isinstance(term, Tag):
                continue
            label = cell_text(term).rstrip(":").casefold()
            value = term.find_next_sibling("dd")
            if isinstance(value, Tag):
                fields[label] = value

        closing_date: date | None = None
        closing_dd = fields.get("closing date")
        if closing_dd is not None:
            time_tag = closing_dd.find("time")
            if isinstance(time_tag, Tag):
                raw = time_tag.get("datetime")
                if raw:
                    closing_date = date.fromisoformat(str(raw)[:10])

        return RawVacancy(
            source_url=url,
            title=title,
            institution_slug=institution.slug,
            location_raw=cell_text(fields.get("location")),
            salary_raw=cell_text(fields.get("salary information")),
            contract_raw=cell_text(fields.get("contract")),
            closing_date=closing_date,
            strategy=self.strategy,
        )
