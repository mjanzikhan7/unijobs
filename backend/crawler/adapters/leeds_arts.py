"""Leeds Arts University's own careers listing cards, on ``leeds-art.ac.uk`` itself.

Recognise it by the institution's own host and ``/about-us/jobs`` path.
Quirk: the listing is client-rendered but each vacancy's detail page is plain server-rendered
HTML - the same split Norwich's adapter established, including the same header-nav-link hang
trap in Playwright's ``wait_for_selector``. No reference is published.
Browser: yes - for the listing only; detail pages are plain HTTP.
Example: https://www.leeds-art.ac.uk/about-us/jobs - Leeds Arts University.
"""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import urldefrag

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_LISTING_LINK_SELECTOR = 'a[href*="/about-us/jobs/"]'


@register_adapter
class LeedsArtsAdapter(BaseAdapter):
    """Renders the listing for titles/links, then a plain fetch of each detail page."""

    platform: ClassVar[Platform] = Platform.LEEDS_ARTS_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Leeds Arts's own host and careers path."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "leeds-art.ac.uk" in url and "/about-us/jobs" in url

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
            title_tag = link.find("h3")
            title = cell_text(title_tag) if isinstance(title_tag, Tag) else cell_text(link)
            href = str(link.get("href") or "")
            if not title or not href:
                continue
            source_url = absolutise(base_url, href)
            bare_target, _ = urldefrag(source_url)
            bare_base, _ = urldefrag(base_url)
            if source_url in seen or bare_target.rstrip("/") == bare_base.rstrip("/"):
                continue
            seen.add(source_url)

            vacancy = self._read_detail(source_url, title, institution)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _read_detail(self, url: str, title: str, institution: InstitutionRef) -> RawVacancy | None:
        """One vacancy's detail page - plain HTTP, no browser needed."""
        response = self.http.get(url)
        self.guard(response.text, url)
        soup = soup_of(response.text)

        fields: dict[str, str] = {}
        for section in soup.find_all("section"):
            if not isinstance(section, Tag):
                continue
            paragraphs = section.find_all("p")
            if len(paragraphs) < 2:
                continue
            label = cell_text(paragraphs[0]).casefold()
            value = cell_text(paragraphs[1])
            if label and value:
                fields[label] = value

        return RawVacancy(
            source_url=url,
            title=title,
            institution_slug=institution.slug,
            salary_raw=fields.get("salary", ""),
            hours_raw=fields.get("hours", ""),
            contract_raw=fields.get("contract", ""),
            closing_date=parse_uk_date(fields.get("closing date")),
            strategy=self.strategy,
        )
