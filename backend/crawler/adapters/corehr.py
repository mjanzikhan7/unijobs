"""CoreHR recruitment portals - the "search v4" engine.

Recognise it by ``wd_portal.show_page`` or ``plsql`` in the path; ``detect()`` bails out first if
the page carries Hireserve's own signature, since that generic Oracle PL/SQL shape is not unique
to CoreHR.
Quirk: the published URL is a blank search form; a plain POST with every hidden field present but
blank is a genuine, unfiltered "every vacancy" search, no browser needed. Pagination is not
optional - CoreHR's own ordering is unstable run to run, so a single page mis-closes real jobs.
Example: https://www.shu.ac.uk/jobs - Sheffield Hallam University.
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

_VACANCY_ID_RE = re.compile(r"viewTheJobSpec\('(\d+)'\)")

_DETAIL_URL_PREFIX_RE = re.compile(r'l_url\s*=\s*"([^"]+)"')

_DISPLAYING_RE = re.compile(r"Displaying\s+\d+\s+to\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)


def _hidden_inputs(form_block: str) -> dict[str, str]:
    """Every hidden field's name and value inside one ``<form>`` block.

    Attribute order inside ``<input>`` differs between sites, so each attribute is read on its own.
    """
    fields: dict[str, str] = {}
    for tag in re.finditer(r"<input\s+([^>]*)>", form_block, re.IGNORECASE):
        attrs = tag.group(1)
        if not re.search(r'type="hidden"', attrs, re.IGNORECASE):
            continue
        name_match = re.search(r'name="([^"]*)"', attrs)
        if name_match is None:
            continue
        value_match = re.search(r'value="([^"]*)"', attrs)
        fields[name_match.group(1)] = value_match.group(1) if value_match else ""
    return fields


def _named_form(html: str, name: str, *, base_url: str) -> tuple[str, dict[str, str]] | None:
    """A named form's absolute action URL and its hidden fields, or ``None`` if absent."""
    pattern = re.compile(
        rf'<form\s+name="{re.escape(name)}"[^>]*action="([^"]+)"[^>]*>(.*?)</form>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    if match is None:
        return None
    return absolutise(base_url, match.group(1)), _hidden_inputs(match.group(2))


_MAX_PAGES = 20


@register_adapter
class CoreHRAdapter(BaseAdapter):
    """Submits the blank "everything" search, then reads every page of v4 results."""

    platform: ClassVar[Platform] = Platform.COREHR

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise CoreHR from its PL/SQL endpoint shape, but not Hireserve.

        Hireserve uses a similar URL shape, so its signature is checked first and wins.
        """
        html = probe.lowered_html
        if "hireserve" in html or "p_web_site_id" in html:
            return False
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        if "wd_portal.show_page" in url or "/pls/" in url or "corehr" in url:
            return True
        return "wd_portal.show_page" in html or "coreportal_erecruit" in html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Submit the blank search form (if the careers URL is one), then page through it."""
        url = institution.careers_url
        response = self.http.get(url)
        html, base_url = response.text, response.url or url

        submission = _named_form(html, "callErecruitDoSearch", base_url=base_url)
        if submission is not None:
            action_url, fields = submission
            response = self.http.post(action_url, data=fields)
            html, base_url = response.text, response.url or action_url

        vacancies: list[RawVacancy] = []
        for page_html, page_base_url in self._paginate(html, base_url):
            vacancies.extend(self._parse(page_html, institution, base_url=page_base_url))

        if not vacancies:
            self.guard(html, base_url)
        return vacancies

    def _paginate(self, html: str, base_url: str) -> list[tuple[str, str]]:
        """Every page of one search, starting from an already-fetched first page.

        Shared with :class:`crawler.adapters.corehr_categorised.CoreHRCategorisedAdapter`,
        whose own category pages are v4 search results in exactly this same shape.
        """
        pages = [(html, base_url)]
        for _ in range(_MAX_PAGES):
            shown, total = _paging_totals(html)
            if shown is None or shown >= total:
                break
            forward = _named_form(html, "searchv4navigateresultsforward", base_url=base_url)
            if forward is None:
                break
            action_url, fields = forward
            response = self.http.post(action_url, data=fields)
            html, base_url = response.text, response.url or action_url
            pages.append((html, base_url))
        return pages

    def _parse(self, html: str, institution: InstitutionRef, *, base_url: str) -> list[RawVacancy]:
        """Read the v4 engine's real result rows.

        A nested table per vacancy, a JavaScript ``onclick`` in place of a plain link, and its
        other fields in labelled cell pairs (``"Pay Scale :" | "STANDARD GRADE 7"``) rather
        than fixed table columns.
        """
        prefix_match = _DETAIL_URL_PREFIX_RE.search(html)
        if prefix_match is None:
            return []
        detail_prefix = prefix_match.group(1)

        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        for row in soup.find_all("td", class_="erq_searchv4_result_row"):
            if not isinstance(row, Tag):
                continue
            title_link = row.find("a", class_="erq_searchv4_big_anchor")
            if not isinstance(title_link, Tag):
                continue
            id_match = _VACANCY_ID_RE.search(str(title_link.get("href") or ""))
            if id_match is None:
                continue
            source_url = absolutise(base_url, detail_prefix + id_match.group(1))
            if source_url in seen:
                continue
            seen.add(source_url)

            title = cell_text(title_link)
            if not title:
                continue

            location_cell = row.find("td", class_="erq_searchv4_heading2")
            closing_raw = self._labelled_value(row, "Closing Date")

            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    location_raw=(
                        cell_text(location_cell) if isinstance(location_cell, Tag) else ""
                    ),
                    reference=id_match.group(1),
                    salary_raw=self._labelled_value(row, "Salary"),
                    grade_raw=self._labelled_value(row, "Pay Scale"),
                    closing_date=parse_uk_date(closing_raw) if closing_raw else None,
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _labelled_value(row: Tag, label: str) -> str:
        """Read a value from this tenant's ``<td>Label :</td><td>Value</td>`` cell pairs."""
        for cell in row.find_all("td", class_="erq_searchv4_heading5_label"):
            if not isinstance(cell, Tag):
                continue
            if label.casefold() not in cell_text(cell).casefold():
                continue
            value_cell = cell.find_next_sibling("td")
            return cell_text(value_cell) if isinstance(value_cell, Tag) else ""
        return ""


def _paging_totals(html: str) -> tuple[int | None, int]:
    """Read "Displaying 1 to 100 of 102" as ``(100, 102)``.

    ``(None, 0)`` when the page has no such summary. Then there is nothing more to fetch.
    """
    match = _DISPLAYING_RE.search(html)
    if match is None:
        return None, 0
    return int(match.group(1)), int(match.group(2))
