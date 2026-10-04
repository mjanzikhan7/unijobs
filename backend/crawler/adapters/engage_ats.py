"""engage|ats (Havas People) recruitment portals.

Recognise it by "Powered by engage|ats" or "Havas People" text, or a ``/V2/Login`` or
``/V2/Vacancy/`` path anywhere on the page, including inside a link.
Quirk: the listing lives behind a per-session encrypted token minted client-side; one tenant
(St Andrews) instead publishes a plain link straight to it. Pagination is browser-driven
throughout - see :meth:`crawler.browser.PlaywrightSession.render_each_page`. Fields are read by
label keyword, not exact text, since labels are tenant-configured.
Browser: yes - the listing only exists after a browser mints or clicks its way to it.
Example: https://jobs.lse.ac.uk/V2/Login - London School of Economics.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import FetchResponse, InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_RESULTS_SELECTOR = "#searchResult-parent"

_EXTERNAL_LINK_SELECTOR = 'a[href*="Vacancy/Index"], [onclick="RedirectToExternalVacancy()"]'

_NEXT_PAGE_SELECTOR = "#search-results-pagination-next:not(.disabled-button)"

_MAX_PAGES = 20

_LAST_PAGE_RE = re.compile(
    r'id="search-results-pagination-last"[^>]*data-pageno="(\d+)"', re.IGNORECASE
)

_VACANCY_ID_RE = re.compile(r"btn-view-job-(\d+)")

_DEPARTMENT_KEYWORDS = ("school", "unit", "department", "faculty", "directorate", "division")
_TYPE_KEYWORDS = ("type",)
_CLOSING_DATE_KEYWORDS = ("closing date",)
_SALARY_RE = re.compile(r"salary\s*:\s*(.+)$", re.IGNORECASE)


@register_adapter
class EngageAtsAdapter(BaseAdapter):
    """Mints the external-vacancies token via a browser, then reads every page it pages to."""

    platform: ClassVar[Platform] = Platform.ENGAGE_ATS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise engage|ats from its own branding, or a `/V2/Login`/`/V2/Vacancy/` mention."""
        html = probe.lowered_html
        if "powered by engage|ats" in html or "havas people" in html:
            return True
        return "v2/login" in html or "v2/vacancy" in html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Land on the real listing, then read every page its own pager reports."""
        landing = self.render_after_click(
            institution.careers_url,
            click_selector=_EXTERNAL_LINK_SELECTOR,
            wait_for_selector=_RESULTS_SELECTOR,
        )
        self.guard(landing.text, institution.careers_url)

        pages = [landing]
        total_pages_match = _LAST_PAGE_RE.search(landing.text)
        has_more_pages = total_pages_match and int(total_pages_match.group(1)) > 1
        if self.browser is not None and has_more_pages:
            pages = self.browser.render_each_page(
                landing.url,
                wait_for_selector=_RESULTS_SELECTOR,
                next_selector=_NEXT_PAGE_SELECTOR,
                max_pages=_MAX_PAGES,
            )

        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        for page in pages:
            for vacancy in self._parse(page, institution):
                if vacancy.reference and vacancy.reference in seen:
                    continue
                seen.add(vacancy.reference)
                vacancies.append(vacancy)
        return vacancies

    def _parse(self, page: FetchResponse, institution: InstitutionRef) -> list[RawVacancy]:
        """Read every vacancy card on one already-rendered page."""
        soup = soup_of(page.text)
        vacancies: list[RawVacancy] = []
        for heading in soup.find_all("div", class_="ats-heading-font"):
            if not isinstance(heading, Tag):
                continue
            title = cell_text(heading)
            if not title:
                continue
            row = heading.find_parent("div", class_=_is_vacancy_card)
            if not isinstance(row, Tag):
                continue

            view_button = row.find("button", id=_VACANCY_ID_RE)
            if not isinstance(view_button, Tag):
                continue
            id_match = _VACANCY_ID_RE.match(str(view_button.get("id") or ""))
            reference = id_match.group(1) if id_match else ""
            source_url = str(view_button.get("data-param1") or "").strip()
            if not source_url:
                continue

            fields = self._labelled_fields(row)
            description = self._free_text(row)

            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    department=_by_keyword(fields, _DEPARTMENT_KEYWORDS),
                    category=_by_keyword(fields, _TYPE_KEYWORDS),
                    reference=reference,
                    salary_raw=_salary_from(description),
                    closing_date=parse_uk_date(_by_keyword(fields, _CLOSING_DATE_KEYWORDS)),
                    description_text=description,
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _labelled_fields(row: Tag) -> dict[str, str]:
        """Every ``<span class="font-weight-bold">Label: </span>Value`` pair inside one card."""
        fields: dict[str, str] = {}
        for field_div in row.find_all("div", class_="ats-normal-font"):
            if not isinstance(field_div, Tag):
                continue
            label = field_div.find("span", class_="font-weight-bold")
            if not isinstance(label, Tag):
                continue
            label_text = cell_text(label).rstrip(":").strip()
            full_text = cell_text(field_div)
            value = full_text[len(cell_text(label)) :].strip()
            fields[label_text.casefold()] = value
        return fields

    @staticmethod
    def _free_text(row: Tag) -> str:
        """The one ``ats-normal-font`` block with no label - free prose, salary sometimes in it."""
        for field_div in row.find_all("div", class_="ats-normal-font"):
            if not isinstance(field_div, Tag):
                continue
            if field_div.find("span", class_="font-weight-bold") is not None:
                continue
            return cell_text(field_div)
        return ""


def _is_vacancy_card(class_value: str | None) -> bool:
    """Each vacancy's own wrapper carries both ``row`` and ``p-3``, never just one alone."""
    classes = (class_value or "").split()
    return "row" in classes and "p-3" in classes


def _by_keyword(fields: dict[str, str], keywords: tuple[str, ...]) -> str:
    """The first field whose label contains any of ``keywords``, matched case-insensitively."""
    for label, value in fields.items():
        if any(keyword in label for keyword in keywords):
            return value
    return ""


def _salary_from(description: str) -> str:
    """Read a ``Salary: ...`` prefix out of the free-text description, or ``""`` if absent.

    Not every vacancy's free text labels its salary at all - confirmed live, several LSE and
    Strathclyde adverts never do - and nothing here tries to guess one out of unlabelled prose.
    """
    match = _SALARY_RE.search(description)
    return match.group(1).strip() if match else ""
