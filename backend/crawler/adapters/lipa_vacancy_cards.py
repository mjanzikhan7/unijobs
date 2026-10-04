"""Liverpool Institute for Performing Arts's own careers listing cards, on ``lipa.ac.uk`` itself.

Recognise it by a repeated ``a.job-item`` card inside a ``div.job-item-container`` - an Umbraco
CMS block with no third-party ATS underneath it.
Quirk: the listing is client-rendered, but every field lives in the card itself once rendered -
no per-vacancy detail fetch needed. No reference is published; left blank rather than guessed.
Browser: yes - the listing is entirely client-rendered.
Example: https://lipa.ac.uk/about-us/working-here/ - Liverpool Institute for Performing Arts.
"""

from __future__ import annotations

from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CARD_WAIT_SELECTOR = "a.job-item"


def _labelled_spans(card: Tag) -> dict[str, str]:
    """Every ``<span><strong>Label:</strong> value</span>`` line, keyed by its label."""
    fields: dict[str, str] = {}
    for span in card.find_all("span"):
        if not isinstance(span, Tag) or span.find("strong") is None:
            continue
        label, separator, value = cell_text(span).partition(":")
        if separator and value.strip():
            fields[label.strip().casefold()] = value.strip()
    return fields


@register_adapter
class LipaVacancyCardsAdapter(BaseAdapter):
    """Renders LIPA's own careers page and reads its ``job-item`` cards directly."""

    platform: ClassVar[Platform] = Platform.LIPA_VACANCY_CARDS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the ``job-item-container`` block this page's markup always carries."""
        return "job-item-container" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the one page and read every ``job-item`` card - no detail fetch, ever."""
        url = institution.careers_url
        response = self.render(url, wait_for_selector=_CARD_WAIT_SELECTOR)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("a", class_="job-item", href=True):
            if not isinstance(card, Tag):
                continue
            title_span = card.find("span")
            title = cell_text(title_span) if isinstance(title_span, Tag) else ""
            if not title:
                continue

            fields = _labelled_spans(card)
            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(card["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    salary_raw=fields.get("salary", ""),
                    hours_raw=fields.get("hours", ""),
                    closing_date=parse_uk_date(fields.get("closing date")),
                    strategy=self.strategy,
                )
            )
        return vacancies
