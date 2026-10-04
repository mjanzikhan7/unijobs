"""LIPA vacancy cards adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.lipa_vacancy_cards import LipaVacancyCardsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_LIPA_URL = "https://lipa.ac.uk/about-us/working-here/"


def lipa(html_fixture: Any) -> LipaVacancyCardsAdapter:
    """An adapter wired to LIPA's real (redacted) rendered page."""
    html = html_fixture("lipa_vacancy_cards/lipa-2026-09-04.html")
    return LipaVacancyCardsAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(responses={_LIPA_URL: response(html, _LIPA_URL)}),
    )


def test_lipa_reads_the_real_vacancy(html_fixture: Any) -> None:
    """Real case: 1 open vacancy, everything needed already on the card itself."""
    adapter = lipa(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LIPA_URL))

    assert len(vacancies) == 1
    vacancy = vacancies[0]
    assert vacancy.title == "Technician (Live Sound)"
    assert vacancy.salary_raw == "£28,778 - £31,236 per annum"
    assert vacancy.hours_raw == "Full-time, 37.5 hours per week"
    assert vacancy.closing_date == date(2026, 9, 11)
    assert (
        vacancy.source_url == "https://lipa.ac.uk/about-us/working-here/jobs/technician-live-sound/"
    )


def test_lipa_is_detected_from_its_job_item_container(html_fixture: Any) -> None:
    html = html_fixture("lipa_vacancy_cards/lipa-2026-09-04.html")
    probe_result = ProbeResult(url=_LIPA_URL, status_code=200, html=html, final_url=_LIPA_URL)

    adapter_class = detect_adapter(ref(_LIPA_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.LIPA_VACANCY_CARDS


def test_a_page_with_no_lipa_job_item_container_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert LipaVacancyCardsAdapter.detect(ref(), probe_result) is False
