"""Shared fixture-response helpers for every per-adapter test file in this package."""

from __future__ import annotations

from crawler.types import FetchResponse, InstitutionRef

CAREERS_URL = "https://jobs.test.ac.uk/jobs"


def response(text: str, url: str = CAREERS_URL, content_type: str = "text/html") -> FetchResponse:
    """Build a fixture response."""
    return FetchResponse(
        url=url, status_code=200, text=text, headers={"content-type": content_type}
    )


def ref(careers_url: str = CAREERS_URL) -> InstitutionRef:
    """An institution reference."""
    return InstitutionRef(
        slug="university-of-test", name="University of Test", careers_url=careers_url
    )
