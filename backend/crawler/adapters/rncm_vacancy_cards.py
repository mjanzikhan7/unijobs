"""Royal Northern College of Music's own careers listing, on ``rncm.ac.uk`` itself.

Recognise it by the institution's own host - a bespoke WordPress page with no card markup at
all.
Quirk: no repeating ``class``/``data-`` attribute marks a vacancy; read from a free-text
``<strong>Label:</strong> value<br>`` block instead. The closing date opens with a clock time
("12 Noon, ...") that would make ``parse_uk_date`` misread "12" as part of the year; stripped
with a small regex first - unlike RCM, no machine-readable attribute exists here.
Example: https://www.rncm.ac.uk/about/job-vacancies/ - Royal Northern College of Music.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import NavigableString, Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_LEADING_CLOCK_TIME_RE = re.compile(
    r"^\s*\d{1,2}([:.]\d{2})?\s*(noon|midnight|am|pm)\s*,?\s*", re.IGNORECASE
)


def _field_value(label_tag: Tag) -> str:
    """Text between one ``<strong>`` label and the next ``<br>`` or ``<strong>``."""
    parts: list[str] = []
    for sibling in label_tag.next_siblings:
        if isinstance(sibling, Tag) and sibling.name in ("br", "strong"):
            break
        if isinstance(sibling, NavigableString):
            parts.append(str(sibling))
        elif isinstance(sibling, Tag):
            parts.append(sibling.get_text())
    return "".join(parts).strip()


def _labelled_fields(paragraph: Tag) -> dict[str, str]:
    fields: dict[str, str] = {}
    for strong in paragraph.find_all("strong"):
        if not isinstance(strong, Tag):
            continue
        label = cell_text(strong).rstrip(":").casefold()
        fields[label] = _field_value(strong)
    return fields


@register_adapter
class RncmVacancyCardsAdapter(BaseAdapter):
    """Plain HTTP fetch of the one listing page - no browser needed, confirmed live."""

    platform: ClassVar[Platform] = Platform.RNCM_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise RNCM's own host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "rncm.ac.uk" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Plain-fetch the one listing page and read every ``<h3><a>`` + fields paragraph."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for heading in soup.find_all("h3"):
            if not isinstance(heading, Tag):
                continue
            link = heading.find("a", href=True)
            title = cell_text(link) if isinstance(link, Tag) else ""
            if not title or not isinstance(link, Tag):
                continue

            paragraph = heading.find_next_sibling("p")
            fields = _labelled_fields(paragraph) if isinstance(paragraph, Tag) else {}

            closing_raw = _LEADING_CLOCK_TIME_RE.sub("", fields.get("closing date", ""))

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    salary_raw=fields.get("salary grade", ""),
                    closing_date=parse_uk_date(closing_raw) if closing_raw else None,
                    strategy=self.strategy,
                )
            )
        return vacancies
