"""Hireful CMS-powered careers listings.

Recognise it by the ``hirefulcms.com`` string appearing anywhere in the page.
Quirk: cards are populated by client-side JS against a private CMS API well after the initial
HTML; calling that API directly returns ``401 Unauthorized``, so the rendered page is read
instead once ``h2.jobheadline`` is present. The reference is embedded inline in that heading,
extracted with a small regex. No pagination observed with only 5 vacancies on one page.
Browser: yes - cards are populated by client-side JS against a private CMS API.
Example: https://jobs.sussex.ac.uk/ - University of Sussex.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CARD_SELECTOR = "article.ed-collection-item"
_READY_SELECTOR = 'article.ed-collection-item a[href*="/job/"]'
_REFERENCE_RE = re.compile(r"Ref:\s*(\S+)", re.IGNORECASE)


def _labelled_value(card: Tag, label: str) -> str:
    """The ``<div>`` immediately following whichever ``<h3>`` names this label."""
    for heading in card.find_all("h3"):
        if not isinstance(heading, Tag):
            continue
        if cell_text(heading).casefold() != label:
            continue
        container = heading.find_parent("div", class_="ed-element")
        if not isinstance(container, Tag):
            continue
        value = container.find_next_sibling("div")
        if isinstance(value, Tag):
            return cell_text(value)
    return ""


@register_adapter
class HirefulCmsAdapter(BaseAdapter):
    """Renders the one listing page and reads every ``ed-collection-item`` card directly."""

    platform: ClassVar[Platform] = Platform.HIREFUL_CMS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Hireful CMS's own hosted content API reference."""
        return "hirefulcms" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the one page and read every ``ed-collection-item`` card's labelled fields."""
        url = institution.careers_url
        response = self.render(url, wait_for_selector=_READY_SELECTOR)
        self.guard(response.text, url)

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.select(_CARD_SELECTOR):
            if not isinstance(card, Tag):
                continue
            heading = card.find("h2", class_="jobheadline")
            title = cell_text(heading) if isinstance(heading, Tag) else ""
            link = card.find("a", href=re.compile(r"/job/"))
            if not title or not isinstance(link, Tag):
                continue

            ref_match = _REFERENCE_RE.search(title)
            closing_raw = _labelled_value(card, "closing date")

            vacancies.append(
                RawVacancy(
                    source_url=str(link["href"]),
                    title=title,
                    institution_slug=institution.slug,
                    reference=ref_match.group(1) if ref_match else "",
                    department=_labelled_value(card, "department"),
                    salary_raw=_labelled_value(card, "salary"),
                    closing_date=parse_uk_date(closing_raw) if closing_raw else None,
                    strategy=self.strategy,
                )
            )
        return vacancies
