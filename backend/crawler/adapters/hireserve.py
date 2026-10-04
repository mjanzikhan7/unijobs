"""Hireserve portals (branded ``iCAMS``/``icamsbase`` in their own markup).

Recognise it by an ``/icamsbase/`` asset path, the string ``hireserve``, or a
``name="p_web_site_id"`` hidden field.
Quirk: the page carries its own tenant id in that hidden field, and a public, unauthenticated
JSON feed needs nothing else - no cookies, no token, no browser. Field labels are configured per
tenant, so read by keyword rather than a fixed key.
Example: https://jobs.aber.ac.uk/en/vacancies.html - Aberystwyth University.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, ClassVar
from urllib.parse import urlparse

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_WEB_SITE_ID_RE = re.compile(r'name="p_web_site_id"\s+value="(\d+)"', re.IGNORECASE)

_SALARY_KEYWORDS = ("salary",)
_CONTRACT_KEYWORDS = ("contract",)
_HOURS_KEYWORDS = ("hour",)
_LOCATION_KEYWORDS = ("location",)
_DEPARTMENT_KEYWORDS = ("depart", "faculty", "school", "directorate", "division")


@register_adapter
class HireserveAdapter(BaseAdapter):
    """One page fetched to find the tenant id, then one JSON feed for every vacancy."""

    platform: ClassVar[Platform] = Platform.HIRESERVE

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Hireserve from its asset path, host, or search-form tenant field."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        html = probe.lowered_html
        if "hireserve" in url or "hireserve" in html:
            return True
        return "icamsbase" in html or "p_web_site_id" in html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Scrape the tenant id off the listing page, then read the whole feed."""
        page_url = institution.careers_url
        page = self.http.get(page_url)
        self.guard(page.text, page_url)

        match = _WEB_SITE_ID_RE.search(page.text)
        if match is None:
            raise ParseError(f"No p_web_site_id found on {page_url}", url=page_url)
        web_site_id = match.group(1)

        parsed = urlparse(page.url or page_url)
        feed_url = (
            f"{parsed.scheme}://{parsed.netloc}/utf8/ic_job_feeds.feed_engine"
            f"?p_web_site_id={web_site_id}&p_published_to=WWW&p_language=DEFAULT&p_direct=Y"
            "&p_format=MOBILE&p_include_exclude_from_list=N&p_search=&p_summary=Y"
        )
        response = self.http.get(feed_url)
        self.strategy = ExtractionStrategy.JSON_API

        try:
            payload = json.loads(response.text)
        except ValueError as exc:
            raise ParseError(f"{feed_url} did not return JSON", url=feed_url) from exc
        if not isinstance(payload, dict):
            raise ParseError(
                f"{feed_url} returned {type(payload).__name__}, not an object", url=feed_url
            )

        vacancies: list[RawVacancy] = []
        for job in payload.get("jobs") or []:
            vacancy = self._to_vacancy(job, institution=institution)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _to_vacancy(self, job: dict[str, Any], *, institution: InstitutionRef) -> RawVacancy | None:
        """Convert one feed entry into a vacancy."""
        title = str(job.get("title") or "").strip()
        source_url = str(job.get("weblink") or "").strip()
        if not title or not source_url:
            return None

        closing_raw = str(
            (job.get("publication") or {}).get("internet", {}).get("closing_date") or ""
        )

        return RawVacancy(
            source_url=source_url,
            title=title,
            institution_slug=institution.slug,
            department=_classification(job, *_DEPARTMENT_KEYWORDS),
            reference=str(job.get("refno") or ""),
            location_raw=_classification(job, *_LOCATION_KEYWORDS),
            salary_raw=_classification(job, *_SALARY_KEYWORDS),
            closing_date=_parse_feed_date(closing_raw),
            contract_raw=_classification(job, *_CONTRACT_KEYWORDS),
            hours_raw=_classification(job, *_HOURS_KEYWORDS),
            strategy=self.strategy,
            extra={"vacancy_id": str(job.get("id") or ""), "closing_date_raw": closing_raw},
        )


def _parse_feed_date(value: str) -> date | None:
    """The feed writes ``YYYY-MM-DD HH:MM:SS``.

    Parsed directly rather than through the UK-advert (day-first) parser, which reads this
    year-first form as day-first too and silently swaps the month and day.
    """
    if not value or len(value) < 10:
        return None
    try:
        return date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
    except ValueError:
        return None


def _classification(job: dict[str, Any], *keywords: str) -> str:
    """The first classification value whose label contains any keyword.

    Tenants name the same field differently ("Salary", "Salary from", "Salary Range") and often
    carry a same-labelled-but-empty variant alongside the real one (Aberystwyth's "Salary Scale"
    next to "Salary") - matching by keyword and skipping empty matches handles both.
    """
    classifications = job.get("classifications")
    if not isinstance(classifications, dict):
        return ""
    for classification in classifications.values():
        name = str(classification.get("name") or "").casefold()
        if not any(keyword in name for keyword in keywords):
            continue
        values = classification.get("values") or []
        texts = [str(value.get("class_val") or "").strip() for value in values]
        texts = [text for text in texts if text]
        if texts:
            return ", ".join(texts)
    return ""
