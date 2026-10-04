"""Norwich University of the Arts's own careers listing cards, on ``norwichuni.ac.uk`` itself.

Recognise it by a repeated card inside the "Current vacancies" section - a WordPress build with
no third-party ATS underneath it.
Quirk: the listing is client-rendered but each vacancy's detail page is plain server-rendered
HTML. Neither salary nor a reference is labelled; salary is read from whichever paragraph starts
with "Salary:", and the reference is the detail URL's own trailing slug.
Browser: yes - for the listing only; detail pages are plain HTTP.
Example: https://norwichuni.ac.uk/about-us/work-at-norwich/ - Norwich University of the Arts.
"""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urldefrag

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_LISTING_LINK_SELECTOR = 'a.block.group[href*="/about-us/work-at-norwich/"]'
_SALARY_PARAGRAPH_RE = re.compile(r"^salary\s*:\s*(.+)", re.IGNORECASE)
_REFERENCE_FROM_URL_RE = re.compile(r"/([^/]+)/?$")


@register_adapter
class NorwichVacancyCardsAdapter(BaseAdapter):
    """Renders the listing for titles/links, then a plain fetch of each detail page."""

    platform: ClassVar[Platform] = Platform.NORWICH_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the "Current vacancies" heading this page's marketing copy always carries."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "norwichuni.ac.uk" in url and "work-at-norwich" in url

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
            title = cell_text(link)
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

        salary_raw = ""
        for paragraph in soup.find_all("p"):
            if not isinstance(paragraph, Tag):
                continue
            match = _SALARY_PARAGRAPH_RE.match(cell_text(paragraph))
            if match:
                salary_raw = match.group(1).strip()
                break

        ref_match = _REFERENCE_FROM_URL_RE.search(url)
        return RawVacancy(
            source_url=url,
            title=title,
            institution_slug=institution.slug,
            reference=ref_match.group(1) if ref_match else "",
            salary_raw=salary_raw,
            strategy=self.strategy,
        )
