"""Workday portals.

**Recognise it by** a ``*.myworkdayjobs.com`` host.

**The quirk that matters - for once, a pleasant one.** The UI is a single-page app, but it is
driven by a documented JSON API at ``/wday/cxs/{tenant}/{site}/jobs``. Calling that directly is
faster and dramatically more stable than rendering the app, and it paginates cleanly.

**Working example.** ``https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs`` →
``https://lse.wd3.myworkdayjobs.com/wday/cxs/lse/LSEJobs/jobs``
"""

from __future__ import annotations

import json
from typing import Any, ClassVar
from urllib.parse import urlparse

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.extraction import absolutise, html_to_text, parse_uk_date
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

PAGE_SIZE = 20
MAX_PAGES = 50


@register_adapter
class WorkdayAdapter(BaseAdapter):
    """Calls the JSON API behind the Workday UI."""

    platform: ClassVar[Platform] = Platform.WORKDAY

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Workday from its host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "myworkdayjobs.com" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Page through the JSON endpoint until every vacancy is collected."""
        api_url = self.api_url(institution.careers_url)
        self.strategy = ExtractionStrategy.JSON_API

        vacancies: list[RawVacancy] = []
        offset = 0
        for _ in range(MAX_PAGES):
            payload = self._fetch_page(api_url, offset)
            postings = payload.get("jobPostings") or []
            if not postings:
                break
            for posting in postings:
                vacancy = self._to_vacancy(
                    posting, institution=institution, careers_url=institution.careers_url
                )
                if vacancy is not None:
                    vacancies.append(vacancy)
            offset += PAGE_SIZE
            if offset >= int(payload.get("total") or 0):
                break

        return vacancies

    @staticmethod
    def api_url(careers_url: str) -> str:
        """Translate a Workday UI URL into its ``cxs`` JSON endpoint.

        ``https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs`` becomes
        ``https://lse.wd3.myworkdayjobs.com/wday/cxs/lse/LSEJobs/jobs``. The tenant is the first
        label of the host; the site is the last path segment that is not a locale.
        """
        parts = urlparse(careers_url)
        tenant = parts.netloc.split(".")[0]
        segments = [segment for segment in parts.path.split("/") if segment]
        site = next(
            (segment for segment in reversed(segments) if not _looks_like_locale(segment)),
            "",
        )
        if not tenant or not site:
            raise ParseError(f"Cannot derive a Workday API URL from {careers_url}", url=careers_url)
        return f"{parts.scheme}://{parts.netloc}/wday/cxs/{tenant}/{site}/jobs"

    def _fetch_page(self, api_url: str, offset: int) -> dict[str, Any]:
        """Fetch one page of results, or raise ``ParseError`` if it is not JSON."""
        response = self.http.post(
            api_url,
            json={"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            payload = json.loads(response.text)
        except ValueError as exc:
            raise ParseError(f"{api_url} did not return JSON", url=api_url) from exc
        if not isinstance(payload, dict):
            raise ParseError(
                f"{api_url} returned {type(payload).__name__}, not an object", url=api_url
            )
        return payload

    def _to_vacancy(
        self, posting: dict[str, Any], *, institution: InstitutionRef, careers_url: str
    ) -> RawVacancy | None:
        """Convert one Workday posting into a vacancy."""
        title = str(posting.get("title") or "").strip()
        path = str(posting.get("externalPath") or "").strip()
        if not title or not path:
            return None

        posted_raw = str(posting.get("postedOn") or "")
        description_html = str(posting.get("jobDescription") or "")

        return RawVacancy(
            source_url=absolutise(careers_url, path),
            title=title,
            institution_slug=institution.slug,
            reference=str(bullets[0]) if (bullets := posting.get("bulletFields")) else "",
            location_raw=str(posting.get("locationsText") or ""),
            description_html=description_html,
            description_text=html_to_text(description_html),
            posted_date=parse_uk_date(posted_raw) if "ago" not in posted_raw.casefold() else None,
            strategy=ExtractionStrategy.JSON_API,
            extra={"posted_raw": posted_raw} if posted_raw else {},
        )


def _looks_like_locale(segment: str) -> bool:
    """Whether a path segment is a locale such as ``en-US``."""
    return len(segment) == 5 and segment[2] == "-"
