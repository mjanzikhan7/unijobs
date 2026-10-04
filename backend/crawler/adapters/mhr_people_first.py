"""MHR People First careers portals.

Recognise it by the ``jobs.people-first.com`` host, not by page content: the plain probe fetch
that detection runs against sees an empty Angular shell with no component markup at all.
Quirk: salary is sometimes the literal text "Competitive"; kept verbatim in ``salary_raw``. No
closing date is published on the listing.
Browser: yes - the listing is entirely client-rendered.
Example: https://bruford.jobs.people-first.com/jobs/search - Rose Bruford College.
"""

from __future__ import annotations

from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_RESULTS_SELECTOR = ".MhrJobListResult-title"


@register_adapter
class MhrPeopleFirstAdapter(BaseAdapter):
    """Renders the one listing page and reads every ``MhrJobList-result`` card directly."""

    platform: ClassVar[Platform] = Platform.MHR_PEOPLE_FIRST

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the vendor's own tenant-subdomain host - content is never in the raw probe."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "jobs.people-first.com" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the one page and read every ``MhrJobList-result`` card - no pagination seen."""
        url = institution.careers_url
        response = self.render(url, wait_for_selector=_RESULTS_SELECTOR)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("li", class_="MhrJobList-result"):
            if not isinstance(card, Tag):
                continue
            title_tag = card.find(class_="MhrJobListResult-title")
            title = cell_text(title_tag) if isinstance(title_tag, Tag) else ""
            link = card.find("a", class_="MhrJobListResult-link", href=True)
            if not title or not isinstance(link, Tag):
                continue

            salary_tag = card.find(class_="MhrJobListResult-salary")
            location_tag = card.find(class_="MhrJobListResult-locationText")

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    salary_raw=cell_text(salary_tag) if isinstance(salary_tag, Tag) else "",
                    location_raw=cell_text(location_tag) if isinstance(location_tag, Tag) else "",
                    strategy=self.strategy,
                )
            )
        return vacancies
