"""Webrecruit careers portals.

Recognise it by the "Powered by: Webrecruit" footer credit - a different vendor from this
project's own ``ITRENT`` adapter, despite the similar name.
Quirk: plain server-rendered HTML, well-labelled, no browser needed. The read-only description
page's id is never a real ``href`` on the listing (only inside an ``onclick`` share-icon call);
read instead from the "Apply Now" button's own ``href``, which carries the identical id.
Example: https://jobs.uwtsd.ac.uk/Home - University of Wales Trinity Saint David.
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

_APPLY_NOW_ID_RE = re.compile(r"/ApplyNow/([\w-]+)")


def _labelled_fields(article: Tag) -> dict[str, str]:
    fields: dict[str, str] = {}
    for row in article.find_all("div", class_="vacancy-details-headers"):
        if not isinstance(row, Tag):
            continue
        label_tag = row.find(class_="vacancy-header-text")
        value_tag = row.find(class_="vacancy-body-text")
        if not isinstance(label_tag, Tag) or not isinstance(value_tag, Tag):
            continue
        fields[cell_text(label_tag).casefold()] = cell_text(value_tag)
    return fields


@register_adapter
class WebrecruitAdapter(BaseAdapter):
    """Plain HTTP fetch of the one listing page - no browser needed, confirmed live."""

    platform: ClassVar[Platform] = Platform.WEBRECRUIT

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Webrecruit's own footer credit."""
        return "powered by: webrecruit" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Plain-fetch the one listing page and read every ``<article>`` card directly."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for article in soup.find_all("article", attrs={"aria-label": True}):
            if not isinstance(article, Tag):
                continue
            title_tag = article.find(class_="vacancy-job-title")
            title = cell_text(title_tag) if isinstance(title_tag, Tag) else ""
            apply_link = article.find("a", href=_APPLY_NOW_ID_RE)
            id_match = (
                _APPLY_NOW_ID_RE.search(str(apply_link["href"]))
                if isinstance(apply_link, Tag)
                else None
            )
            if not title or id_match is None:
                continue

            fields = _labelled_fields(article)
            closing_raw = fields.get("closing date", "")

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, f"/JobDescription/{id_match.group(1)}"),
                    title=title,
                    institution_slug=institution.slug,
                    reference=fields.get("job ref", ""),
                    category=fields.get("function", ""),
                    location_raw=fields.get("location", ""),
                    salary_raw=fields.get("salary", ""),
                    contract_raw=fields.get("type", ""),
                    hours_raw=fields.get("hours", ""),
                    closing_date=parse_uk_date(closing_raw) if closing_raw else None,
                    strategy=self.strategy,
                )
            )
        return vacancies
