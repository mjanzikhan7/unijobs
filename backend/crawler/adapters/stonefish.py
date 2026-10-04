"""Stonefish Software Web Builder portals.

Recognise it by ``<meta name="Generator" content="Stonefish Software Web Builder">``.
Quirk: the search page's results come back through an ASP.NET postback a plain HTTP client
cannot trigger, so a naive crawl of it returns an empty page with a 200 - go straight at the
category listing instead, which is server-rendered and complete.
Example: https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx?cat=-1 - University of Bath.
"""

from __future__ import annotations

from typing import ClassVar
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.extraction import (
    absolutise,
    cell_text,
    looks_like_vacancy_link,
    parse_uk_date,
    soup_of,
)
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_ALL_CATEGORIES_QUERY = "cat=-1"

_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("job title", "vacancy", "post", "position", "title", "role"),
    "reference": ("reference", "ref", "vacancy reference", "job reference", "ref no"),
    "salary": ("salary", "salary range", "grade and salary", "remuneration"),
    "closing_date": ("closing date", "closes", "closing", "deadline"),
    "department": ("department", "faculty", "school", "location"),
    "contract": ("contract", "contract type", "type", "duration"),
}


@register_adapter
class StonefishAdapter(BaseAdapter):
    """Reads the department-grouped category listing over plain HTTP."""

    platform: ClassVar[Platform] = Platform.STONEFISH

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Stonefish from its generator meta tag, or from its URL shape."""
        if "stonefish" in probe.lowered_html:
            return True
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "vacancies.aspx" in url or "vacancydetails.aspx" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the all-categories listing and parse every row."""
        url = self.listing_url(institution.careers_url)
        response = self.http.get(url)
        self.guard(response.text, url)

        structured = self.structured_vacancies(response, institution)
        if structured is not None:
            return structured

        self.strategy = ExtractionStrategy.HTML
        return self._parse_listing(response.text, institution, base_url=response.url or url)

    @staticmethod
    def listing_url(careers_url: str) -> str:
        """Rewrite a careers URL onto the all-categories listing.

        A tenant's careers link often points at ``search.aspx``. Sending the crawl there
        produces a confident, empty, wrong answer - the results arrive through an ASP.NET
        postback - so the page *and* the query are both replaced, never merged.
        """
        parts = urlparse(careers_url)
        segments = parts.path.split("/")
        if segments and segments[-1].casefold().endswith(".aspx"):
            segments[-1] = "vacancies.aspx"
            path = "/".join(segments)
        else:
            path = parts.path.rstrip("/") + "/vacancies.aspx"
        return urlunparse(parts._replace(path=path, query=_ALL_CATEGORIES_QUERY, fragment=""))

    def _parse_listing(
        self, html: str, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """Parse the department-grouped tables, falling back to link scanning."""
        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()

        for table in soup.find_all("table"):
            department = self._department_for(table)
            columns = self._column_map(table)
            if "title" not in columns:
                continue
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if not cells or (row.find("th") and not row.find("td")):
                    continue
                vacancy = self._vacancy_from_row(
                    cells,
                    columns,
                    institution=institution,
                    department=department,
                    base_url=base_url,
                )
                if vacancy is not None and vacancy.source_url not in seen:
                    seen.add(vacancy.source_url)
                    vacancies.append(vacancy)

        if not vacancies:
            vacancies = self._parse_links(soup, institution, base_url=base_url, seen=seen)

        return vacancies

    @staticmethod
    def _department_for(table: Tag) -> str:
        """Find the heading a table sits under; Stonefish groups vacancies by department."""
        for previous in table.find_all_previous(["h1", "h2", "h3", "h4", "caption"], limit=1):
            if isinstance(previous, Tag):
                return cell_text(previous)
        return ""

    @staticmethod
    def _column_map(table: Tag) -> dict[str, int]:
        """Map field names onto column indices using the table's own header labels."""
        header_row = table.find("tr")
        if not isinstance(header_row, Tag):
            return {}
        headers = [
            cell_text(cell).casefold()
            for cell in header_row.find_all(["th", "td"])
            if isinstance(cell, Tag)
        ]
        columns: dict[str, int] = {}
        for field, aliases in _COLUMN_ALIASES.items():
            for index, header in enumerate(headers):
                if any(alias == header or alias in header for alias in aliases):
                    columns.setdefault(field, index)
                    break
        return columns

    def _vacancy_from_row(
        self,
        cells: list[Tag],
        columns: dict[str, int],
        *,
        institution: InstitutionRef,
        department: str,
        base_url: str,
    ) -> RawVacancy | None:
        """Build one vacancy from a table row, or ``None`` if the row is not a vacancy."""

        def value(field: str) -> str:
            index = columns.get(field)
            if index is None or index >= len(cells):
                return ""
            return cell_text(cells[index])

        title_index = columns.get("title", 0)
        if title_index >= len(cells):
            return None
        link = cells[title_index].find("a", href=True)
        if not isinstance(link, Tag):
            return None
        href = str(link.get("href") or "")
        title = cell_text(link)
        if not looks_like_vacancy_link(title, href):
            return None

        return RawVacancy(
            source_url=absolutise(base_url, href),
            title=title,
            institution_slug=institution.slug,
            department=value("department") or department,
            reference=value("reference"),
            salary_raw=value("salary"),
            location_raw=value("department") if "department" in columns else "",
            contract_raw=value("contract"),
            closing_date=parse_uk_date(value("closing_date")),
            strategy=ExtractionStrategy.HTML,
        )

    def _parse_links(
        self,
        soup: BeautifulSoup,
        institution: InstitutionRef,
        *,
        base_url: str,
        seen: set[str],
    ) -> list[RawVacancy]:
        """Last resort: scan for vacancy-detail links when the tenant uses divs, not tables."""
        vacancies: list[RawVacancy] = []
        for link in soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue
            href = str(link.get("href") or "")
            if "vacancydetails" not in href.casefold() and "vacancyid" not in href.casefold():
                continue
            title = cell_text(link)
            if not looks_like_vacancy_link(title, href):
                continue
            url = absolutise(base_url, href)
            if url in seen:
                continue
            seen.add(url)
            vacancies.append(
                RawVacancy(
                    source_url=url,
                    title=title,
                    institution_slug=institution.slug,
                    strategy=ExtractionStrategy.HTML,
                )
            )
        if not vacancies and "vacanc" not in str(soup).casefold():
            raise ParseError(f"{base_url} does not look like a Stonefish listing", url=base_url)
        return vacancies
