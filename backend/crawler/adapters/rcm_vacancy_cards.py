"""Royal College of Music's own careers listing cards, on ``rcm.ac.uk`` itself.

Recognise it by the institution's own host - a bespoke build with no third-party ATS underneath
it.
Quirk: each card carries a machine-readable ``data-closing="YYMMDD"`` attribute, read directly
rather than parsed out of the human-readable text beside it. Contract type and salary share no
label, only position. The detail URL's own numeric id is read as the reference.
Example: https://www.rcm.ac.uk/about/jobs/ - Royal College of Music.
"""

from __future__ import annotations

import re
from datetime import date
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_REFERENCE_FROM_URL_RE = re.compile(r"jobtitle(\d+)", re.IGNORECASE)


def _parse_closing_attr(value: str) -> date | None:
    """``data-closing`` is ``YYMMDD`` against a 2000-based century - no ambiguity to resolve."""
    if not re.fullmatch(r"\d{6}", value):
        return None
    year = 2000 + int(value[0:2])
    month = int(value[2:4])
    day = int(value[4:6])
    return date(year, month, day)


@register_adapter
class RcmVacancyCardsAdapter(BaseAdapter):
    """Plain HTTP fetch of the one listing page - no browser needed, confirmed live."""

    platform: ClassVar[Platform] = Platform.RCM_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise RCM's own host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "rcm.ac.uk" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Plain-fetch the one listing page and read every ``div.job`` card directly."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("div", class_="job"):
            if not isinstance(card, Tag):
                continue
            link = card.find("a", href=True)
            title = cell_text(link) if isinstance(link, Tag) else ""
            if not title or not isinstance(link, Tag):
                continue
            href = str(link["href"])
            source_url = absolutise(base_url, href)

            paragraphs = [p for p in card.select("div.job-details > p") if isinstance(p, Tag)]
            contract_raw = cell_text(paragraphs[0]) if paragraphs else ""
            salary_raw = cell_text(paragraphs[1]) if len(paragraphs) > 1 else ""

            closing_date = _parse_closing_attr(str(card.get("data-closing") or ""))
            ref_match = _REFERENCE_FROM_URL_RE.search(href)

            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    reference=ref_match.group(1) if ref_match else "",
                    contract_raw=contract_raw,
                    salary_raw=salary_raw,
                    closing_date=closing_date,
                    strategy=self.strategy,
                )
            )
        return vacancies
