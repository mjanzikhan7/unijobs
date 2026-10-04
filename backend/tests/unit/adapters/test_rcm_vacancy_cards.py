"""Royal College of Music adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.rcm_vacancy_cards import RcmVacancyCardsAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_RCM_URL = "https://www.rcm.ac.uk/about/jobs/"


def rcm(html_fixture: Any) -> RcmVacancyCardsAdapter:
    """An adapter wired to RCM's real (redacted), plain-HTTP-fetched listing page."""
    return RcmVacancyCardsAdapter(
        http=FixtureHttpClient(
            responses={
                _RCM_URL: response(
                    html_fixture("rcm_vacancy_cards/listing-2026-09-04.html"), _RCM_URL
                )
            }
        )
    )


def test_rcm_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 2 cards, one page, no pagination control observed."""
    adapter = rcm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RCM_URL))

    assert len(vacancies) == 2


def test_rcm_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = rcm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RCM_URL))

    hr = next(v for v in vacancies if v.title == "HR Advisor")
    assert hr.reference == "53384"
    assert hr.contract_raw == "Permanent"
    assert "£39,608" in hr.salary_raw
    assert hr.closing_date == date(2026, 9, 16)
    assert hr.source_url == (
        "https://www.rcm.ac.uk/about/jobs/currentvacancies/details/jobtitle53384en.aspx"
    )


def test_rcm_closing_date_comes_from_the_data_attribute_not_fuzzy_parsed_prose(
    html_fixture: Any,
) -> None:
    """The human-readable text never states a year; the ``data-closing`` attribute does."""
    adapter = rcm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RCM_URL))

    innovation = next(v for v in vacancies if v.title == "Innovation Associate")
    assert innovation.closing_date == date(2026, 9, 14)


def test_rcm_is_detected_from_its_host() -> None:
    probe_result = ProbeResult(
        url=_RCM_URL, status_code=200, html="<p>Loading…</p>", final_url=_RCM_URL
    )

    adapter_class = detect_adapter(ref(_RCM_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.RCM_VACANCY_CARDS


def test_a_host_with_no_rcm_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert RcmVacancyCardsAdapter.detect(ref(), probe_result) is False
