"""``DatabaseResponseRecorder`` under an open browser session.

The conditional-request cache it backs is a politeness optimisation, not a correctness
requirement - an unchanged page costs a full fetch instead of a 304 if this cannot be read, and
that is a fine outcome. Crashing the institution's whole crawl because a browser happened to be
open in the same thread when this ran is not: this is the failure that made every crawl needing
Chromium report ``PARSE_ERROR`` with zero vacancies, discovered when a real crawl of Abertay
University (an adapter that fetches detail pages over HTTP while its listing browser session is
still open) hit exactly this path in production.
"""

from __future__ import annotations

import pytest

from crawler.browser import PlaywrightSession
from crawler.cache import CacheEntry
from crawler.models import RawResponse
from crawler.persistence import DatabaseResponseRecorder
from crawler.types import FetchResponse
from tests.factories import CrawlRunFactory  # noqa: F401 - ensures django_db fixtures are set up

pytestmark = pytest.mark.django_db


def _entry(url: str = "https://jobs.test.ac.uk/vacancy/1") -> CacheEntry:
    from datetime import UTC, datetime
    from pathlib import Path

    return CacheEntry(
        key="abc123",
        url=url,
        sha256="deadbeef",
        byte_size=100,
        stored_at=datetime.now(UTC),
        path=Path("/tmp/abc123.html"),
    )


def _response(url: str = "https://jobs.test.ac.uk/vacancy/1") -> FetchResponse:
    return FetchResponse(url=url, status_code=200, text="<html></html>", headers={"etag": '"v1"'})


def test_validators_for_reads_normally_with_no_browser_open() -> None:
    """The common case: no degradation needed."""
    recorder = DatabaseResponseRecorder()
    recorder.record(_entry(), _response())

    etag, _last_modified = recorder.validators_for("https://jobs.test.ac.uk/vacancy/1")

    assert etag == '"v1"'


def test_validators_for_degrades_to_empty_rather_than_crashing_while_a_browser_is_open() -> None:
    """The actual regression.

    A missed conditional-request opportunity is invisible in the crawl console. A crashed
    institution is not - it shows up as PARSE_ERROR with zero vacancies, for every institution
    whose adapter fetches anything over HTTP while its browser session is still open.
    """
    recorder = DatabaseResponseRecorder()
    recorder.record(_entry(), _response())

    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session.start()
    try:
        etag, last_modified = recorder.validators_for("https://jobs.test.ac.uk/vacancy/1")
    finally:
        session.stop()

    assert (etag, last_modified) == ("", "")


def test_record_degrades_silently_rather_than_crashing_while_a_browser_is_open() -> None:
    """The write side of the same problem."""
    recorder = DatabaseResponseRecorder()
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session.start()
    try:
        recorder.record(_entry(url="https://jobs.test.ac.uk/vacancy/2"), _response())
    finally:
        session.stop()

    assert True


def test_a_write_that_could_not_land_is_not_silently_lost_forever() -> None:
    """Once the browser closes, the same URL can still be recorded normally.

    This is what makes the degradation acceptable: it costs one missed cache entry, not a
    permanently blind spot for that URL.
    """
    recorder = DatabaseResponseRecorder()
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session.start()
    session.stop()

    recorder.record(_entry(url="https://jobs.test.ac.uk/vacancy/3"), _response())

    assert RawResponse.objects.filter(url="https://jobs.test.ac.uk/vacancy/3").exists()
