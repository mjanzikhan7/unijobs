"""MHR People First HR adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.mhr_people_first import MhrPeopleFirstAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_ROSE_BRUFORD_URL = (
    "https://bruford.jobs.people-first.com/jobs/search?distance=300&allLocations=false"
)


def rose_bruford(html_fixture: Any) -> MhrPeopleFirstAdapter:
    """An adapter wired to Rose Bruford's real (redacted) rendered page."""
    html = html_fixture("mhr_people_first/rose-bruford-2026-09-04.html")
    return MhrPeopleFirstAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(
            responses={_ROSE_BRUFORD_URL: response(html, _ROSE_BRUFORD_URL)}
        ),
    )


def test_mhr_people_first_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 3 cards, one page, no pagination."""
    adapter = rose_bruford(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ROSE_BRUFORD_URL))

    assert len(vacancies) == 3


def test_mhr_people_first_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = rose_bruford(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ROSE_BRUFORD_URL))

    cleaner = next(v for v in vacancies if v.title == "Cleaning Operative")
    assert cleaner.salary_raw == "Competitive"
    assert "Sidcup" in cleaner.location_raw
    assert cleaner.source_url == (
        "https://bruford.jobs.people-first.com/jobs/details/"
        "recruitment%2Fjobdetails%2F9508d138-4fa3-4b8e-b38d-1a0003511ce0"
    )


def test_mhr_people_first_is_detected_from_its_host(html_fixture: Any) -> None:
    html = html_fixture("mhr_people_first/rose-bruford-2026-09-04.html")
    probe_result = ProbeResult(
        url=_ROSE_BRUFORD_URL, status_code=200, html=html, final_url=_ROSE_BRUFORD_URL
    )

    adapter_class = detect_adapter(ref(_ROSE_BRUFORD_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.MHR_PEOPLE_FIRST


def test_mhr_people_first_is_detected_even_from_the_bare_unrendered_shell(
    html_fixture: Any,
) -> None:
    """Regression: an earlier detect relied on a class name only a browser ever renders.

    That fell through to ``NO_ADAPTER`` on every real crawl despite passing every fixture test
    built against post-render HTML. The real probe never renders - confirmed live, it sees only
    a ~1.7KB empty Angular shell with no component markup at all.
    """
    empty_shell = "<html><body><app-root></app-root></body></html>"
    probe_result = ProbeResult(
        url=_ROSE_BRUFORD_URL, status_code=200, html=empty_shell, final_url=_ROSE_BRUFORD_URL
    )

    adapter_class = detect_adapter(ref(_ROSE_BRUFORD_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.MHR_PEOPLE_FIRST


def test_a_page_with_no_mhr_people_first_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert MhrPeopleFirstAdapter.detect(ref(), probe_result) is False
