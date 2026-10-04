"""Liverpool Hope University's own careers listing tables, on ``hope.ac.uk`` itself.

Recognise it by the institution's own host - a bespoke CMS page with no third-party ATS
underneath it.
Quirk: one table per category, most carrying only a header row, no data rows. A header row is
told apart from a data row by whether its first cell contains a link. Closing date and time are
two separate published columns; time is kept in ``extra`` rather than dropped.
Example: https://www.hope.ac.uk/aboutus/jobopportunities/currentvacancies/ - Liverpool Hope.
"""

from __future__ import annotations

from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform


@register_adapter
class LiverpoolHopeVacancyTablesAdapter(BaseAdapter):
    """Plain HTTP fetch of the one listing page - no browser needed, confirmed live."""

    platform: ClassVar[Platform] = Platform.LIVERPOOL_HOPE_VACANCY_TABLES

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Liverpool Hope's own host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "hope.ac.uk" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Plain-fetch the one listing page and read every category table's data rows."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        soup = soup_of(response.text)
        vacancies: list[RawVacancy] = []
        for heading in soup.find_all("h2"):
            if not isinstance(heading, Tag):
                continue
            category = cell_text(heading)
            table = heading.find_next_sibling("table")
            if not isinstance(table, Tag):
                continue
            vacancies.extend(self._read_table(table, category, base_url, institution))
        return vacancies

    def _read_table(
        self, table: Tag, category: str, base_url: str, institution: InstitutionRef
    ) -> list[RawVacancy]:
        vacancies: list[RawVacancy] = []
        for row in table.find_all("tr"):
            if not isinstance(row, Tag):
                continue
            cells = [cell for cell in row.find_all(["th", "td"]) if isinstance(cell, Tag)]
            if len(cells) < 4:
                continue
            link = cells[0].find("a", href=True)
            if not isinstance(link, Tag):
                continue

            title = cell_text(link)
            reference = cell_text(cells[1])
            closing_date = parse_uk_date(cell_text(cells[2]))
            closing_time = cell_text(cells[3])

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    category=category,
                    reference=reference,
                    closing_date=closing_date,
                    strategy=self.strategy,
                    extra={"closing_time": closing_time} if closing_time else {},
                )
            )
        return vacancies
