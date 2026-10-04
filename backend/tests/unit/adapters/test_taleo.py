"""Taleo adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.taleo import TaleoAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_DURHAM_URL = (
    "https://durham.taleo.net/careersection/du_ext/jobsearch.ftl?lang=en&portal=10105010224"
)


def durham(html_fixture: Any) -> TaleoAdapter:
    """An adapter wired to both of Durham's real (redacted) result pages."""
    pages = [
        response(html_fixture("taleo/durham-page1-2026-09-04.html"), _DURHAM_URL),
        response(html_fixture("taleo/durham-page2-2026-09-04.html"), _DURHAM_URL),
    ]
    return TaleoAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(responses={}, paginated_responses={_DURHAM_URL: pages}),
    )


def test_taleo_follows_pagination_to_find_every_vacancy(html_fixture: Any) -> None:
    """25 + 2 across 2 pages - the site's own 'Next' click gets page 2."""
    adapter = durham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DURHAM_URL))

    assert len(vacancies) == 27


def test_taleo_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = durham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DURHAM_URL))

    engineer = next(
        v for v in vacancies if "Senior Mechanical Building Services Project Engineer" in v.title
    )
    assert engineer.department == "PI - Engineering Services"
    assert engineer.salary_raw == "£47,389-£56,535 per annum"
    assert engineer.reference == "26001210"
    assert engineer.source_url == (
        "https://durham.taleo.net/careersection/du_mob/jobdetail.ftl"
        "?job=26001210&tz=GMT%2B00%3A00&tzname=UTC"
    )


def test_taleo_tags_every_vacancy_with_the_institution(html_fixture: Any) -> None:
    adapter = durham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DURHAM_URL))

    assert all(v.institution_slug == "university-of-test" for v in vacancies)


def test_taleo_is_detected_from_its_host() -> None:
    probe_result = ProbeResult(
        url=_DURHAM_URL, status_code=200, html="<p>Loading…</p>", final_url=_DURHAM_URL
    )

    adapter_class = detect_adapter(ref(_DURHAM_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.TALEO


def test_a_page_with_no_taleo_host_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert TaleoAdapter.detect(ref(), probe_result) is False
