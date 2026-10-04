"""Contensis CMS jobs pages, hydrated from an embedded ``window.REDUX_DATA`` blob.

Recognise it by a ``window.REDUX_DATA`` assignment whose payload carries a
``"contentTypeId":"jobVacancy"`` entry.
Quirk: the blob is a JS object literal, not strict JSON - bare ``undefined`` tokens are replaced
with ``null`` before parsing. Pagination is server-rendered too, behind a plain ``?page=N``.
Example: https://www.kcl.ac.uk/jobs/search - King's College London.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.extraction import absolutise, parse_uk_date
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_REDUX_DATA_RE = re.compile(r"window\.REDUX_DATA\s*=\s*")
_BARE_UNDEFINED_RE = re.compile(r"\bundefined\b")

_MAX_PAGES = 50


def _extract_redux_data(html: str) -> dict[str, Any] | None:
    """The page's own state blob, or ``None`` if this page carries none at all."""
    match = _REDUX_DATA_RE.search(html)
    if match is None:
        return None
    start = match.end()
    end = html.find("</script>", start)
    if end == -1:
        return None
    blob = _BARE_UNDEFINED_RE.sub("null", html[start:end])
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


@register_adapter
class ContensisJobsAdapter(BaseAdapter):
    """Reads every page of ``jobsSearch.entries`` straight out of the embedded state."""

    platform: ClassVar[Platform] = Platform.CONTENSIS_JOBS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Contensis's own content-model name for a vacancy, not any one host."""
        html = probe.lowered_html
        return "window.redux_data" in html and '"contenttypeid":"jobvacancy"' in html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch every page ``jobsSearch.pagingInfo`` says exists, reading each one's entries."""
        self.strategy = ExtractionStrategy.JSON_API
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)
        base_url = response.url or url

        vacancies = self._read_page(response.text, institution, base_url=base_url)
        job_search = self._job_search(response.text, url=url)
        page_count = int(job_search.get("pagingInfo", {}).get("pageCount") or 1)

        for page in range(2, min(page_count, _MAX_PAGES) + 1):
            page_url = f"{url}{'&' if '?' in url else '?'}page={page}"
            page_response = self.http.get(page_url)
            self.guard(page_response.text, page_url)
            vacancies.extend(
                self._read_page(
                    page_response.text, institution, base_url=page_response.url or page_url
                )
            )

        return vacancies

    def _job_search(self, html: str, *, url: str) -> dict[str, Any]:
        """The ``jobsSearch`` slice of the page's state, or a typed failure if it is missing."""
        data = _extract_redux_data(html)
        if data is None:
            raise ParseError(f"{url} carries no readable window.REDUX_DATA", url=url)
        job_search = data.get("jobsSearch")
        if not isinstance(job_search, dict):
            raise ParseError(f"{url} has no jobsSearch in its REDUX_DATA", url=url)
        return job_search

    def _read_page(
        self, html: str, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """Every entry on one fetched page, mapped from Contensis's own field names."""
        job_search = self._job_search(html, url=base_url)
        entries = job_search.get("entries")
        if not isinstance(entries, list):
            return []

        vacancies: list[RawVacancy] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            vacancy = self._vacancy_from_entry(entry, institution, base_url=base_url)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _vacancy_from_entry(
        self, entry: dict[str, Any], institution: InstitutionRef, *, base_url: str
    ) -> RawVacancy | None:
        """One ``jobVacancy`` entry's fields, by Contensis's own names for them."""
        title = str(entry.get("title") or "").strip()
        slug = str((entry.get("sys") or {}).get("slug") or "")
        if not title or not slug:
            return None

        description_fields = ("jobDescription", "furtherParticulars")
        description = "\n\n".join(
            str(entry[field]) for field in description_fields if entry.get(field)
        )
        vacancy_id = entry.get("vacancyID")

        return RawVacancy(
            source_url=absolutise(base_url, f"/jobs/{slug}"),
            title=title,
            institution_slug=institution.slug,
            department=str(entry.get("recruitmentDeptDescription") or ""),
            category=str(entry.get("recruitmentTypeDesc") or ""),
            reference=str(vacancy_id) if vacancy_id is not None else "",
            location_raw=str(entry.get("orgGroupLocationText") or ""),
            salary_raw=str(entry.get("gradeAndSalaryText") or ""),
            description_html=description,
            description_text=description,
            posted_date=parse_uk_date(entry.get("recruitExternalOpenDate")),
            closing_date=parse_uk_date(entry.get("recruitExternalCloseDate")),
            strategy=self.strategy,
        )
