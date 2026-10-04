"""Arts University Bournemouth's careers listing cards, on ``aub.ac.uk`` itself.

Recognise it by a repeated ``<p class="mt-2">Salary: ... | Ref: ...</p>`` summary line next to a
``/vacancies/`` link.
Quirk: AUB's real ATS is permanently robots-disallowed platform-wide; this CMS page, which
carries salary, hours, contract type and a reference in one line, is the only honest source.
Example: https://aub.ac.uk/working-at-aub/vacancies - Arts University Bournemouth.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CARD_SUMMARY_RE = re.compile(r'<p class="mt-2">\s*salary:', re.IGNORECASE)


def _parse_summary(text: str) -> dict[str, str]:
    """Split a ``Salary: X | Hours: Y | Ref: Z``-shaped line into a label/value map.

    Cards vary in which segments they carry - some have no ``Hours`` or ``Contract`` at all -
    so this reads whatever is actually there rather than assuming a fixed set of segments.
    """
    fields: dict[str, str] = {}
    for segment in text.split("|"):
        label, separator, value = segment.strip().partition(":")
        if separator and value.strip():
            fields[label.strip().casefold()] = value.strip()
    return fields


@register_adapter
class AubVacancyCardsAdapter(BaseAdapter):
    """Reads AUB's own careers-page vacancy cards, entirely off the disallowed ATS domain."""

    platform: ClassVar[Platform] = Platform.AUB_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the repeated card-summary line this page's markup always carries."""
        return bool(_CARD_SUMMARY_RE.search(probe.html)) and "/vacancies/" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Read every card's title link and its own summary line - no detail fetch, ever."""
        url = institution.careers_url
        page = self.http.get(url)
        self.guard(page.text, url)

        soup = soup_of(page.text)
        base = page.url or url
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()

        for summary_tag in soup.find_all("p", class_="mt-2"):
            if not isinstance(summary_tag, Tag):
                continue
            summary_text = cell_text(summary_tag)
            if not summary_text.casefold().startswith("salary"):
                continue

            card = summary_tag.find_parent("div")
            heading = card.find("h3") if isinstance(card, Tag) else None
            link = heading.find("a", href=True) if isinstance(heading, Tag) else None
            if not isinstance(link, Tag):
                continue

            title = cell_text(link)
            if not title:
                continue
            source_url = absolutise(base, str(link["href"]))
            if source_url in seen:
                continue
            seen.add(source_url)

            fields = _parse_summary(summary_text)
            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    salary_raw=fields.get("salary", ""),
                    hours_raw=fields.get("hours", ""),
                    contract_raw=fields.get("contract", ""),
                    reference=fields.get("ref", ""),
                )
            )
        return vacancies
