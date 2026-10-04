"""Luminate (Sitebuilder job widget), a UK arts-sector jobs board on its own subdomain.

Recognise it by a ``jobs.luminate.ac.uk`` host - every tenant on its own domain, so the host
alone is enough.
Quirk: every vacancy is already in the plain HTTP response; no browser needed. Fields are read
by their own Font Awesome icon class, not by position. No pager observed on the one tenant
checked, so none is implemented.
Example: https://jobs.luminate.ac.uk/v2/leedsconservatoirejobs - Leeds Conservatoire.
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

_ICON_FIELDS: tuple[tuple[str, str], ...] = (
    ("fa-map-marker-alt", "location"),
    ("fa-wallet", "salary"),
    ("fa-tag", "category"),
    ("fa-clock", "contract"),
    ("fa-calendar-times", "closing_date"),
    ("fa-list-alt", "reference"),
)

_TRAILING_RELATIVE_HINT_RE = re.compile(r"\s*\(.*\)\s*$")


@register_adapter
class LuminateAdapter(BaseAdapter):
    """Reads every vacancy card straight off the plain HTML - no session, no browser."""

    platform: ClassVar[Platform] = Platform.LUMINATE

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Luminate from its own dedicated host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "luminate.ac.uk" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the one page and read every ``sitebuilder-job-results-item`` card on it."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("div", class_="sitebuilder-job-results-item"):
            if not isinstance(card, Tag):
                continue
            vacancy = self._read_card(card, institution, base_url=base_url)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _read_card(
        self, card: Tag, institution: InstitutionRef, *, base_url: str
    ) -> RawVacancy | None:
        """One card's title, detail link and icon-labelled fields."""
        link = card.find("a", href=True)
        title_tag = card.find("h3", class_="sitebuilder-job-results-item-title")
        title = cell_text(title_tag if isinstance(title_tag, Tag) else None)
        if not isinstance(link, Tag) or not title:
            return None

        fields = self._icon_labelled_fields(card)
        closing_date_raw = _TRAILING_RELATIVE_HINT_RE.sub("", fields.get("closing_date", ""))
        return RawVacancy(
            source_url=absolutise(base_url, str(link.get("href") or "")),
            title=title,
            institution_slug=institution.slug,
            category=fields.get("category", ""),
            reference=fields.get("reference", ""),
            location_raw=fields.get("location", ""),
            salary_raw=fields.get("salary", ""),
            contract_raw=fields.get("contract", ""),
            closing_date=parse_uk_date(closing_date_raw),
            strategy=self.strategy,
        )

    @staticmethod
    def _icon_labelled_fields(card: Tag) -> dict[str, str]:
        """Every ``<i class="far fa-{icon}">`` line's value, keyed by the field the icon names."""
        fields: dict[str, str] = {}
        for icon_class, field_name in _ICON_FIELDS:
            icon = card.find("i", class_=icon_class)
            if not isinstance(icon, Tag):
                continue
            line = icon.find_parent("div")
            span = line.find("span") if isinstance(line, Tag) else None
            if isinstance(span, Tag):
                fields[field_name] = cell_text(span)
        return fields
