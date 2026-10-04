"""Finding the adapter for an institution: fetch, detect, resolve.

See ``crawler.services`` for the full crawl of one institution.
"""

from __future__ import annotations

from crawler.adapters.base import BaseAdapter
from crawler.exceptions import NoAdapterFound
from crawler.registry import adapter_for_platform, detect_adapter
from crawler.types import BrowserSession, HttpClient, InstitutionRef, ProbeResult
from institutions.enums import Platform
from institutions.models import Institution


def institution_ref(institution: Institution) -> InstitutionRef:
    """Project a Django model onto the value object adapters receive."""
    return InstitutionRef(
        slug=institution.slug,
        name=institution.name,
        careers_url=institution.careers_url,
        platform=Platform(institution.effective_platform or Platform.UNKNOWN),
        website=institution.website,
    )


def probe_portal(ref: InstitutionRef, http: HttpClient) -> ProbeResult:
    """Fetch the careers page once, for detection to read."""
    response = http.get(ref.careers_url)
    return ProbeResult(
        url=ref.careers_url,
        status_code=response.status_code,
        html=response.text,
        headers=response.headers,
        final_url=response.url,
    )


def resolve_adapter(
    institution: Institution,
    ref: InstitutionRef,
    probe: ProbeResult,
    *,
    http: HttpClient,
    browser: BrowserSession | None,
) -> BaseAdapter:
    """Choose the adapter for an institution.

    A person's ``adapter_override`` always wins. Detection is a guess. Someone who has looked at
    the site is not.
    """
    if institution.adapter_override:
        adapter_class = adapter_for_platform(institution.adapter_override)
        if adapter_class is None:
            raise NoAdapterFound(
                f"adapter_override {institution.adapter_override!r} is not registered"
            )
    else:
        adapter_class = detect_adapter(ref, probe)
        if adapter_class is None:
            raise NoAdapterFound(f"No adapter recognised {ref.careers_url}")

    return adapter_class(http=http, browser=browser)
