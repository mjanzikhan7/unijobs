"""Norwich vacancy cards adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.norwich_vacancy_cards import NorwichVacancyCardsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_NORWICH_URL = "https://norwichuni.ac.uk/about-us/work-at-norwich/"
_NORWICH_DETAIL_URL = "https://norwichuni.ac.uk/about-us/work-at-norwich/a1119/"


def norwich(html_fixture: Any) -> NorwichVacancyCardsAdapter:
    """An adapter wired to Norwich's real (redacted) listing and its one detail page."""
    listing_html = html_fixture("norwich_vacancy_cards/norwich-list-2026-09-04.html")
    detail_html = html_fixture("norwich_vacancy_cards/norwich-detail-a1119-2026-09-04.html")
    return NorwichVacancyCardsAdapter(
        http=FixtureHttpClient(
            responses={_NORWICH_DETAIL_URL: response(detail_html, _NORWICH_DETAIL_URL)}
        ),
        browser=FixtureBrowserSession(
            responses={_NORWICH_URL: response(listing_html, _NORWICH_URL)}
        ),
    )


def test_norwich_reads_the_real_vacancy(html_fixture: Any) -> None:
    """Real case: 1 open vacancy, salary read from free-flowing prose, ref from the URL."""
    adapter = norwich(html_fixture)

    vacancies = adapter.list_vacancies(ref(_NORWICH_URL))

    assert len(vacancies) == 1
    vacancy = vacancies[0]
    assert vacancy.title == "Student Resident Assistant"
    assert vacancy.salary_raw == "£15.51 per hour"
    assert vacancy.reference == "a1119"
    assert vacancy.source_url == _NORWICH_DETAIL_URL


def test_norwich_is_detected_from_its_host_and_path() -> None:
    probe_result = ProbeResult(
        url=_NORWICH_URL, status_code=200, html="<p>Loading…</p>", final_url=_NORWICH_URL
    )

    adapter_class = detect_adapter(ref(_NORWICH_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.NORWICH_VACANCY_CARDS


def test_a_norwich_host_with_no_careers_path_is_not_detected() -> None:
    url = "https://norwichuni.ac.uk/some/other/page"
    probe_result = ProbeResult(url=url, status_code=200, html="<p>Nothing</p>", final_url=url)

    assert NorwichVacancyCardsAdapter.detect(ref(url), probe_result) is False
