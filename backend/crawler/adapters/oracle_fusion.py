"""Oracle Fusion Cloud Recruiting ("Candidate Experience") career sites.

Recognise it by an ``*.oraclecloud.com`` host serving ``/hcmUI/CandidateExperience/``, or the
``oraclecloud`` string on a custom-domain tenant's own rendered page.
Quirk: like Workday, a clean unauthenticated JSON REST API sits under the SPA - no browser
needed. The site's own ``siteNumber`` is read from the URL, not assumed to be ``CX``; the list
endpoint pages via ``offset``/``limit``, not a page number.
Example: https://enzj.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX - Heriot-Watt.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar
from urllib.parse import urlparse

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.extraction import cell_text, html_to_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_PAGE_SIZE = 50
_MAX_PAGES = 30

_SALARY_LABELS = ("grade and salary", "salary and grade", "salary")

_API_BASE_RE = re.compile(r'data-apibaseurl="(https?://[^"]+)"', re.IGNORECASE)


@register_adapter
class OracleFusionAdapter(BaseAdapter):
    """Calls the JSON REST API behind an Oracle Fusion Candidate Experience site."""

    platform: ClassVar[Platform] = Platform.ORACLE_FUSION

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise a Candidate Experience site from its host and path, or from its content.

        The content check finds sites on their own custom domain.
        """
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        if "oraclecloud.com" in url and "candidateexperience" in url:
            return True
        return "oraclecloud" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the tenant's own front door, then page through the list endpoint it names."""
        self.strategy = ExtractionStrategy.JSON_API
        page = self.http.get(institution.careers_url)
        base, site_number = self._site(page.url or institution.careers_url, page.text)

        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        offset = 0
        for _ in range(_MAX_PAGES):
            payload = self._fetch_list_page(base, site_number, offset=offset)
            requisitions = payload.get("requisitionList") or []
            if not requisitions:
                break
            for requisition in requisitions:
                req_id = str(requisition.get("Id") or "")
                if not req_id or req_id in seen:
                    continue
                seen.add(req_id)
                vacancies.append(
                    self._fetch_detail(base, site_number, req_id, institution=institution)
                )
            offset += len(requisitions)
            if offset >= int(payload.get("TotalJobsCount") or 0):
                break
        return vacancies

    @staticmethod
    def _site(page_url: str, html: str) -> tuple[str, str]:
        """The site's real API origin, and the ``siteNumber`` from the page URL.

        Uses the page's ``data-apibaseurl`` when it exists. A custom domain does not pass API
        requests through.
        """
        parts = urlparse(page_url)
        segments = [segment for segment in parts.path.split("/") if segment]
        try:
            site_number = segments[segments.index("sites") + 1]
        except (ValueError, IndexError) as exc:
            raise ParseError(
                f"No site number found in {page_url} — expected .../sites/<number>/...",
                url=page_url,
            ) from exc
        base = _api_base(html) or f"{parts.scheme}://{parts.netloc}"
        return base, site_number

    def _fetch_list_page(self, base: str, site_number: str, *, offset: int) -> dict[str, Any]:
        """One page of the search result - Oracle nests it inside `items[0]`."""
        finder = f"findReqs;siteNumber={site_number},limit={_PAGE_SIZE},offset={offset}"
        url = (
            f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList&finder={finder}"
        )
        return self._get_json(url)

    def _fetch_detail(
        self, base: str, site_number: str, req_id: str, *, institution: InstitutionRef
    ) -> RawVacancy:
        """Fetch one vacancy's own description - salary lives only here, never in the list."""
        url = (
            f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
            f"?expand=all&finder=ById;Id=%22{req_id}%22,siteNumber={site_number}"
        )
        detail = self._get_json(url)

        description_html = str(detail.get("ExternalDescriptionStr") or "")
        posted_raw = str(detail.get("ExternalPostedStartDate") or "")
        closing_raw = str(detail.get("ExternalPostedEndDate") or "")

        return RawVacancy(
            source_url=f"{base}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}",
            title=str(detail.get("Title") or "").strip(),
            institution_slug=institution.slug,
            department=str(detail.get("JobFunction") or ""),
            category=str(detail.get("Category") or ""),
            reference=req_id,
            location_raw=str(detail.get("PrimaryLocation") or ""),
            salary_raw=_labelled_paragraph(description_html, _SALARY_LABELS),
            contract_raw=str(detail.get("JobSchedule") or ""),
            description_html=description_html,
            description_text=html_to_text(description_html),
            posted_date=parse_uk_date(posted_raw) if posted_raw else None,
            closing_date=parse_uk_date(closing_raw) if closing_raw else None,
            strategy=ExtractionStrategy.JSON_API,
        )

    def _get_json(self, url: str) -> dict[str, Any]:
        """Fetch one JSON resource and return its `items[0]`, or raise `ParseError`.

        Every endpoint used here wraps its payload in a one-item `items` list.
        """
        response = self.http.get(url, headers={"Accept": "application/json"})
        self.guard(response.text, url)
        try:
            payload = json.loads(response.text)
        except ValueError as exc:
            raise ParseError(f"{url} did not return JSON", url=url) from exc
        items = payload.get("items") if isinstance(payload, dict) else None
        if not items or not isinstance(items[0], dict):
            raise ParseError(f"{url} returned no usable item", url=url)
        result: dict[str, Any] = items[0]
        return result


def _api_base(html: str) -> str | None:
    """The real Oracle API host the page's own bootstrap script names, or ``None``."""
    match = _API_BASE_RE.search(html)
    return match.group(1).rstrip("/") if match else None


def _labelled_paragraph(description_html: str, labels: tuple[str, ...]) -> str:
    """Read the rest of a ``<p><strong>Label:</strong> value</p>`` paragraph, by its label.

    Some sites never label the salary. We never try to guess it from unlabelled text.
    """
    soup = soup_of(description_html)
    for bold in soup.find_all(["strong", "b"]):
        if not isinstance(bold, Tag):
            continue
        label_text = cell_text(bold).rstrip(":").casefold()
        if not any(label in label_text for label in labels):
            continue
        paragraph = bold.find_parent("p")
        if not isinstance(paragraph, Tag):
            continue
        full_text = cell_text(paragraph)
        value = full_text[len(cell_text(bold)) :].strip(" :")
        if value:
            return value
    return ""
