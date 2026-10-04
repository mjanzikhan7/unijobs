"""Tribepad Talent Acquisition Software careers portals.

Recognise it by the ``Powered by ... Tribepad Talent Acquisition Software`` footer credit.
Quirk: plain server-rendered HTML with proper ``schema.org`` microdata on every card, no browser
needed. Pagination is a plain page-number path segment, followed by the "Next" link's own text.
No reference is published; the detail URL's own numeric id is read instead.
Example: https://vacancies.bpp.com/jobs/search - BPP University.
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

_MAX_PAGES = 20
_APPLY_BY_PREFIX_RE = re.compile(r"^apply by\s*", re.IGNORECASE)
_POSTED_ON_PREFIX_RE = re.compile(r"^posted on\s*", re.IGNORECASE)
_REFERENCE_FROM_URL_RE = re.compile(r"/(\d+)/?$")


def _icon_paragraph(card: Tag, icon_class: str) -> str:
    """The text of whichever ``<p>`` holds an ``<i>`` tagged with this Font Awesome icon."""
    icon = card.find("i", class_=icon_class)
    if not isinstance(icon, Tag):
        return ""
    paragraph = icon.find_parent("p")
    return cell_text(paragraph) if isinstance(paragraph, Tag) else ""


@register_adapter
class TribepadAdapter(BaseAdapter):
    """Plain HTTP, page-numbered pagination, reads each ``li`` card's microdata directly."""

    platform: ClassVar[Platform] = Platform.TRIBEPAD

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Tribepad's own footer credit."""
        return "tribepad talent acquisition software" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Follow the plain page-numbered pagination, reading every card by its microdata."""
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
            for card in soup.select("ul.jobs > li"):
                if not isinstance(card, Tag):
                    continue
                vacancy = self._read_card(card, base_url, institution)
                if vacancy is not None:
                    vacancies.append(vacancy)

            next_url = self._next_page_url(soup, base_url)
        return vacancies

    @staticmethod
    def _next_page_url(soup: Tag, base_url: str) -> str | None:
        """The pagination link whose screen-reader-only text says "Next results page"."""
        for link in soup.select("div.pagination a[href]"):
            if not isinstance(link, Tag):
                continue
            if "next results page" in cell_text(link).casefold():
                return absolutise(base_url, str(link["href"]))
        return None

    def _read_card(
        self, card: Tag, base_url: str, institution: InstitutionRef
    ) -> RawVacancy | None:
        link = card.find("a", href=True)
        title_tag = card.find(class_="job-list-title")
        title = cell_text(title_tag) if isinstance(title_tag, Tag) else ""
        if not title or not isinstance(link, Tag):
            return None
        href = str(link["href"])
        source_url = absolutise(base_url, href)

        location_tag = card.find(attrs={"itemprop": "address"})
        contract_tag = card.find(attrs={"itemprop": "employmentType"})
        posted_tag = card.find(attrs={"itemprop": "datePosted"})

        posted_text = cell_text(posted_tag) if isinstance(posted_tag, Tag) else ""
        salary_raw = _icon_paragraph(card, "fa-wallet")
        closing_raw = _APPLY_BY_PREFIX_RE.sub("", _icon_paragraph(card, "fa-calendar"))
        posted_raw = _POSTED_ON_PREFIX_RE.sub("", posted_text)

        ref_match = _REFERENCE_FROM_URL_RE.search(href)

        return RawVacancy(
            source_url=source_url,
            title=title,
            institution_slug=institution.slug,
            reference=ref_match.group(1) if ref_match else "",
            location_raw=cell_text(location_tag) if isinstance(location_tag, Tag) else "",
            salary_raw=salary_raw,
            contract_raw=cell_text(contract_tag) if isinstance(contract_tag, Tag) else "",
            posted_date=parse_uk_date(posted_raw) if posted_raw else None,
            closing_date=parse_uk_date(closing_raw) if closing_raw else None,
            strategy=self.strategy,
        )
