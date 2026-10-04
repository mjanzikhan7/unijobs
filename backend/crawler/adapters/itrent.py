"""MHR iTrent "WebRecruitment" portals.

Recognise it by a ``*_webrecruitment`` or ``*_web`` tenant-folder path segment, or the string
``itrent`` in the page.
Quirk: the search page is a client-rendered shell whose JS fetches a JSON endpoint using a
session token minted fresh on every visit - two plain HTTP requests, no browser: scrape the
token, then ask the endpoint directly. A marketing page's pinned ``WVID`` link goes stale, so
one is re-derived live every crawl instead when the careers URL is just the tenant's root.
Example: https://jobs.napier.ac.uk/mthrprod_webrecruitment/ - Edinburgh Napier University.
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
from crawler.extraction import html_to_text
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_PAGE_SIZE = 200

_WVID_IN_URL_RE = re.compile(r"/([A-Za-z0-9]+)\.open\?.*?\bwvid=([^&]+)", re.IGNORECASE)
_DISCOVERY_LINK_RE = re.compile(r'href="([A-Za-z0-9]+)\.open\?wvid=([^"]+)"', re.IGNORECASE)
_USESSION_RE = re.compile(r"USESSION=([0-9A-Fa-f]+)")


@register_adapter
class ITrentAdapter(BaseAdapter):
    """Two plain HTTP requests: mint a session, then ask the JSON endpoint for everything."""

    platform: ClassVar[Platform] = Platform.ITRENT

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise iTrent from its tenant path or its host, not a bare "itrent" substring.

        A substring match also catches an unrelated HR-intranet mention.
        """
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        html = probe.lowered_html
        return "webitrent.com" in url or "_webrecruitment" in url or "webitrent.com" in html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Mint a session against the search page, then read every result in one JSON call."""
        base, template, wvid = self._resolve_entry(institution.careers_url)
        open_url = f"{base}/wrd/run/{template}.open?WVID={wvid}"
        opened = self.http.get(open_url)

        session_match = _USESSION_RE.search(opened.text)
        if session_match is None or "security violation" in opened.text.casefold():
            self.guard(opened.text, open_url)
            raise ParseError(f"{open_url} did not yield a usable session", url=open_url)
        session = session_match.group(1)

        json_url = (
            f"{base}/wrd/run/ETREC106GF.json?WVID={wvid}&USESSION={session}"
            f"&LANG=USA&RESULTS_PP={_PAGE_SIZE}"
        )
        response = self.http.get(
            json_url,
            headers={
                "Referer": f"{open_url}&USESSION={session}",
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
        )
        self.strategy = ExtractionStrategy.JSON_API

        try:
            payload = json.loads(response.text)
        except ValueError as exc:
            raise ParseError(f"{json_url} did not return JSON", url=json_url) from exc
        if not isinstance(payload, dict):
            raise ParseError(
                f"{json_url} returned {type(payload).__name__}, not an object", url=json_url
            )

        search = payload.get("search") or {}
        results = payload.get("results") or []
        total = int(search.get("total_rec") or 0)
        if total > len(results):
            raise ParseError(
                f"{json_url} reported {total} vacancies but returned only {len(results)}",
                url=json_url,
            )

        vacancies: list[RawVacancy] = []
        for item in results:
            vacancy = self._to_vacancy(item, institution=institution, open_url=open_url)
            if vacancy is not None:
                vacancies.append(vacancy)
        return vacancies

    def _resolve_entry(self, careers_url: str) -> tuple[str, str, str]:
        """Return ``(tenant_base, open_template, wvid)`` for the search page to open.

        A careers URL that already names a web view (``.open?WVID=...``) is trusted as-is -
        someone chose it deliberately. Otherwise the tenant's default redirect is followed to
        find a web view that is live right now, rather than one frozen on a marketing page.
        """
        base = self._tenant_base(careers_url)
        direct = _WVID_IN_URL_RE.search(careers_url)
        if direct:
            return base, direct.group(1), direct.group(2)

        discovery_url = f"{base}/wrd/run/etrec002gf.open"
        landing = self.http.get(discovery_url)
        self.guard(landing.text, discovery_url)
        found = _DISCOVERY_LINK_RE.search(landing.text)
        if found is None:
            raise ParseError(f"{discovery_url} published no live web-view link", url=discovery_url)
        return base, found.group(1), found.group(2)

    @staticmethod
    def _tenant_base(careers_url: str) -> str:
        """The tenant root: scheme, host, and the ``*_webrecruitment`` path segment."""
        parsed = urlparse(careers_url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        tenant = next(
            (
                segment
                for segment in segments
                if segment.casefold().endswith(("_webrecruitment", "_web"))
            ),
            None,
        )
        if tenant is None:
            raise ParseError(
                f"No *_webrecruitment or *_web tenant segment in {careers_url}", url=careers_url
            )
        return f"{parsed.scheme}://{parsed.netloc}/{tenant}"

    def _to_vacancy(
        self, item: dict[str, Any], *, institution: InstitutionRef, open_url: str
    ) -> RawVacancy | None:
        """Convert one JSON result into a vacancy.

        ``source_url`` is the search page URL plus ``VACANCY_ID``, not the feed's own ``bu_send``
        link, which is session-decorated.
        """
        title = str(item.get("job_title") or "").strip()
        vacancy_id = str(item.get("vacancy_id") or "").strip()
        if not title or not vacancy_id:
            return None

        source_url = f"{open_url}&VACANCY_ID={vacancy_id}"
        description_html = str(item.get("job_description") or "")
        closing_raw = str(item.get("app_close_d") or "")

        return RawVacancy(
            source_url=source_url,
            title=title,
            institution_slug=institution.slug,
            department=str(item.get("region_id") or ""),
            reference=str(item.get("vacancy_ref") or ""),
            location_raw=str(item.get("location_id") or ""),
            salary_raw=str(item.get("salary") or ""),
            description_html=description_html,
            description_text=html_to_text(description_html) if description_html else "",
            closing_date=_parse_closing_date(closing_raw),
            contract_raw=str(item.get("basis_id") or ""),
            hours_raw=str(item.get("con_hrs") or ""),
            strategy=self.strategy,
            extra={"vacancy_id": vacancy_id, "app_close_d_raw": closing_raw},
        )


def _parse_closing_date(value: str) -> date | None:
    """MHR returns ``app_close_d`` as ``YYYYMMDD`` with no separators, or ``""`` when unset."""
    if not value or len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return None
