"""AUB's careers-page vacancy cards adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.aub_vacancy_cards import AubVacancyCardsAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_AUB_URL = "https://aub.ac.uk/working-at-aub/vacancies"


def aub(html_fixture: Any) -> AubVacancyCardsAdapter:
    html = html_fixture("aub_vacancy_cards/aub-vacancies-2026-08-25.html")
    return AubVacancyCardsAdapter(
        http=FixtureHttpClient(responses={_AUB_URL: response(html, _AUB_URL)})
    )


def test_aub_reads_every_card_on_the_page(html_fixture: Any) -> None:
    adapter = aub(html_fixture)

    vacancies = adapter.list_vacancies(ref(_AUB_URL))

    assert len(vacancies) == 5


def test_aub_never_touches_the_disallowed_ats_domain(html_fixture: Any) -> None:
    """The regression this pins down: every source URL must stay on `aub.ac.uk` itself."""
    adapter = aub(html_fixture)

    vacancies = adapter.list_vacancies(ref(_AUB_URL))

    assert all(v.source_url.startswith("https://aub.ac.uk/") for v in vacancies)
    assert all("employment.aub.ac.uk" not in v.source_url for v in vacancies)


def test_aub_reads_a_full_summary_line(html_fixture: Any) -> None:
    """Salary, hours, contract and reference all come from one card's own summary text."""
    adapter = aub(html_fixture)

    vacancies = adapter.list_vacancies(ref(_AUB_URL))

    servicedesk = next(v for v in vacancies if v.title == "ServiceDesk Technician")
    assert servicedesk.salary_raw == "£25,804 per annum"
    assert servicedesk.hours_raw == "37 hours per week"
    assert servicedesk.contract_raw == "permanent"
    assert servicedesk.reference == "AD1656"
    assert servicedesk.institution_slug == "university-of-test"


def test_aub_reads_a_partial_summary_line_without_hours_or_contract(html_fixture: Any) -> None:
    """Some cards carry only a salary and a reference - nothing is guessed for the rest."""
    adapter = aub(html_fixture)

    vacancies = adapter.list_vacancies(ref(_AUB_URL))

    tutors = next(v for v in vacancies if "Visiting Tutors" in v.title)
    assert tutors.salary_raw == "£31.82 per hour"
    assert tutors.reference == "AD1616"
    assert tutors.hours_raw == ""
    assert tutors.contract_raw == ""


def test_aub_is_detected_from_its_card_summary_lines(html_fixture: Any) -> None:
    html = html_fixture("aub_vacancy_cards/aub-vacancies-2026-08-25.html")
    probe_result = ProbeResult(url=_AUB_URL, status_code=200, html=html, final_url=_AUB_URL)

    adapter_class = detect_adapter(ref(_AUB_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.AUB_VACANCY_CARDS


def test_a_page_with_no_card_summaries_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Working here</p>", final_url=CAREERS_URL
    )

    assert AubVacancyCardsAdapter.detect(ref(), probe_result) is False
