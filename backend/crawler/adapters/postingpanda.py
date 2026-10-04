"""PostingPanda careers portals.

Recognise it by ``postingpanda.blob.core.windows.net`` asset URLs - the vendor's own CDN.
Quirk: an AngularJS app; a plain fetch sees only unrendered template placeholders. Each card
labels its fields by icon filename, not text. The description is genuinely truncated
server-side mid-word, so only the icon-tagged fields are read, never the description.
Browser: yes - an AngularJS app, plain fetch sees only template placeholders.
Example: https://vacancies.soas.ac.uk/ - SOAS University of London.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_RESULTS_SELECTOR = "div.jobListing"

_ICON_FIELDS: tuple[tuple[str, str], ...] = (
    ("location.svg", "location"),
    ("clock.svg", "contract"),
    ("salary.svg", "salary"),
)


def _icon_src_ends_with(icon_name: str) -> Callable[[str | None], bool]:
    """A BeautifulSoup ``src`` matcher bound to one icon filename, not the loop that built it."""
    return lambda src: src is not None and src.endswith(icon_name)


def _icon_labelled_fields(card: Tag) -> dict[str, str]:
    """Every ``<p><img src=".../{icon}"> value</p>`` line, keyed by the field its icon names."""
    fields: dict[str, str] = {}
    for icon_name, field_name in _ICON_FIELDS:
        img = card.find("img", src=_icon_src_ends_with(icon_name))
        paragraph = img.find_parent("p") if isinstance(img, Tag) else None
        if isinstance(paragraph, Tag):
            fields[field_name] = cell_text(paragraph)
    return fields


@register_adapter
class PostingPandaAdapter(BaseAdapter):
    """Renders the one listing page and reads every ``jobListing`` card directly."""

    platform: ClassVar[Platform] = Platform.POSTINGPANDA

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise PostingPanda from its own asset CDN."""
        return "postingpanda.blob.core.windows.net" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the one page and read every ``jobListing`` card - no pagination observed."""
        url = institution.careers_url
        response = self.render(url, wait_for_selector=_RESULTS_SELECTOR)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("div", class_="jobListing"):
            if not isinstance(card, Tag):
                continue
            link = card.find("a", href=True)
            title = cell_text(link) if isinstance(link, Tag) else ""
            if not title or not isinstance(link, Tag):
                continue

            fields = _icon_labelled_fields(card)
            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    location_raw=fields.get("location", ""),
                    contract_raw=fields.get("contract", ""),
                    salary_raw=fields.get("salary", ""),
                    strategy=self.strategy,
                )
            )
        return vacancies
