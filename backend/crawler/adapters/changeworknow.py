"""ChangeWorkNow / ISW recruitment portals.

Recognise it by an ``isw.changeworknow.co.uk`` host serving a ``/vms/e/careers/`` path.
Quirk: every vacancy is already in the plain HTTP response, no session or JS needed. No pager
has been observed on the one tenant checked (16 vacancies, one page), so none is implemented -
a larger tenant may need one added.
Example: https://isw.changeworknow.co.uk/hartpury/vms/e/careers/search/new - Hartpury University.
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

_VACANCY_ID_RE = re.compile(r"/positions/([^/?#]+)/?$")

_CONTRACT_KEYWORDS = ("contract type",)
_CLOSING_DATE_KEYWORDS = ("closing date",)
_SALARY_KEYWORDS = ("salary",)


@register_adapter
class ChangeWorkNowAdapter(BaseAdapter):
    """Reads every vacancy card straight off the plain HTML - no session, no browser."""

    platform: ClassVar[Platform] = Platform.CHANGEWORKNOW

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise ChangeWorkNow/ISW from its host and careers path."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "changeworknow.co.uk" in url and "/vms/e/careers" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the one page and read every ``position_opening`` card on it."""
        response = self.http.get(institution.careers_url)
        self.guard(response.text, institution.careers_url)
        base_url = response.url or institution.careers_url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("div", class_="position_opening"):
            if not isinstance(card, Tag):
                continue
            link = card.find("a", href=True)
            if not isinstance(link, Tag):
                continue
            title = cell_text(link)
            if not title:
                continue
            source_url = absolutise(base_url, str(link.get("href") or ""))
            id_match = _VACANCY_ID_RE.search(source_url)

            fields = self._labelled_fields(card)
            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    reference=id_match.group(1) if id_match else "",
                    contract_raw=_by_keyword(fields, _CONTRACT_KEYWORDS),
                    salary_raw=_by_keyword(fields, _SALARY_KEYWORDS),
                    closing_date=parse_uk_date(_by_keyword(fields, _CLOSING_DATE_KEYWORDS)),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _labelled_fields(card: Tag) -> dict[str, str]:
        """Every ``<p><strong>Label</strong>: value</p>`` pair inside one vacancy card."""
        fields: dict[str, str] = {}
        for paragraph in card.find_all("p"):
            if not isinstance(paragraph, Tag):
                continue
            label = paragraph.find("strong")
            if not isinstance(label, Tag):
                continue
            label_text = cell_text(label).casefold()
            full_text = cell_text(paragraph)
            value = full_text[len(cell_text(label)) :].lstrip(": ").strip()
            fields[label_text] = value
        return fields


def _by_keyword(fields: dict[str, str], keywords: tuple[str, ...]) -> str:
    """The first field whose label contains any of ``keywords``."""
    for label, value in fields.items():
        if any(keyword in label for keyword in keywords):
            return value
    return ""
