"""The University of Cambridge's own careers table (a custom Drupal Views build).

Recognise it by the specific Drupal Views column ids this build's table uses together -
``view-title-table-column``, ``view-field-category-table-column`` and
``view-field-closing-date-table-column``.
Quirk: unlike almost everything else in this registry, a blank search server-renders every
vacancy in one response - no browser, no pagination.
Example: https://www.cam.ac.uk/jobs/search?search_api_views_fulltext= - University of Cambridge.
"""

from __future__ import annotations

from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_COLUMNS = {
    "view-title-table-column": "title",
    "view-field-department-location-table-column": "department",
    "view-field-salary-table-column": "salary",
    "view-field-category-table-column": "category",
    "view-created-table-column": "posted",
    "view-field-closing-date-table-column": "closing",
    "view-field-reference-table-column": "reference",
}

_REQUIRED_COLUMNS_FOR_DETECTION = (
    "view-title-table-column",
    "view-field-category-table-column",
    "view-field-closing-date-table-column",
)


@register_adapter
class CambridgeViewsTableAdapter(BaseAdapter):
    """Reads a server-rendered Views table over plain HTTP - no browser, no pagination."""

    platform: ClassVar[Platform] = Platform.CAMBRIDGE_VIEWS_TABLE

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the table by its column header ids, all three together."""
        html = probe.lowered_html
        return all(column in html for column in _REQUIRED_COLUMNS_FOR_DETECTION)

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the blank-search listing and read its table - every row, one request."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)

        soup = soup_of(response.text)
        table = soup.find("table")
        if not isinstance(table, Tag):
            return []

        vacancies: list[RawVacancy] = []
        for row in table.find_all("tr"):
            vacancy = self._vacancy_from_row(
                row, institution=institution, base_url=response.url or url
            )
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _vacancy_from_row(
        self, row: Tag, *, institution: InstitutionRef, base_url: str
    ) -> RawVacancy | None:
        """Build one vacancy from a ``<tr>``, keyed by each cell's ``headers`` attribute.

        ``headers`` can hold several values in HTML5, so BeautifulSoup always returns a list,
        even here where each cell names only one. Do not assume it is a string.
        """
        cells: dict[str, Tag] = {}
        for cell in row.find_all(["td", "th"]):
            if not isinstance(cell, Tag):
                continue
            header_ids = cell.get("headers") or []
            if isinstance(header_ids, str):
                header_ids = [header_ids]
            field = next((_COLUMNS[h] for h in header_ids if h in _COLUMNS), None)
            if field is not None:
                cells[field] = cell

        title_cell = cells.get("title")
        if title_cell is None:
            return None
        link = title_cell.find("a", href=True)
        if not isinstance(link, Tag):
            return None
        title = cell_text(link)
        if not title:
            return None

        department_cell = cells.get("department")
        category_cell = cells.get("category")

        return RawVacancy(
            source_url=absolutise(base_url, str(link["href"])),
            title=title,
            institution_slug=institution.slug,
            department=cell_text(department_cell) if department_cell else "",
            category=cell_text(category_cell) if category_cell else "",
            reference=cell_text(cells.get("reference")) if "reference" in cells else "",
            salary_raw=cell_text(cells.get("salary")) if "salary" in cells else "",
            posted_date=parse_uk_date(cell_text(cells.get("posted")))
            if "posted" in cells
            else None,
            closing_date=parse_uk_date(cell_text(cells.get("closing")))
            if "closing" in cells
            else None,
            strategy=self.strategy,
        )
