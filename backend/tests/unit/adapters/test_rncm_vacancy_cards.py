"""Royal Northern College of Music adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.rncm_vacancy_cards import RncmVacancyCardsAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_RNCM_URL = "https://www.rncm.ac.uk/about/job-vacancies/"


def rncm(html_fixture: Any) -> RncmVacancyCardsAdapter:
    """An adapter wired to RNCM's real (redacted), plain-HTTP-fetched listing page."""
    return RncmVacancyCardsAdapter(
        http=FixtureHttpClient(
            responses={
                _RNCM_URL: response(
                    html_fixture("rncm_vacancy_cards/listing-2026-09-04.html"), _RNCM_URL
                )
            }
        )
    )


def test_rncm_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 2 vacancies, no repeating card markup, only ``<h3><a>`` + one ``<p>``."""
    adapter = rncm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RNCM_URL))

    assert len(vacancies) == 2


def test_rncm_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = rncm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RNCM_URL))

    library = next(v for v in vacancies if v.title == "Library Assistant")
    assert "£23,742" in library.salary_raw
    assert library.closing_date == date(2026, 9, 14)
    assert library.source_url == "https://www.rncm.ac.uk/jobs/library-assistant/"


def test_rncm_strips_the_leading_clock_time_before_parsing_the_closing_date(
    html_fixture: Any,
) -> None:
    """Regression against a trap caught before this adapter shipped.

    "12 Noon, Monday 14 September 2026" fed to ``parse_uk_date`` unchanged silently returns
    2012-09-14, not 2026-09-14 - confirmed live.
    """
    adapter = rncm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RNCM_URL))

    library = next(v for v in vacancies if v.title == "Library Assistant")
    assert library.closing_date is not None
    assert library.closing_date.year == 2026


def test_rncm_leaves_an_open_ended_closing_date_blank(html_fixture: Any) -> None:
    """One real vacancy publishes "Open until filled" - no date to parse, left blank."""
    adapter = rncm(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RNCM_URL))

    apprentice = next(v for v in vacancies if "Apprenticeship" in v.title)
    assert apprentice.closing_date is None


def test_rncm_is_detected_from_its_host() -> None:
    probe_result = ProbeResult(
        url=_RNCM_URL, status_code=200, html="<p>Loading…</p>", final_url=_RNCM_URL
    )

    adapter_class = detect_adapter(ref(_RNCM_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.RNCM_VACANCY_CARDS


def test_a_host_with_no_rncm_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert RncmVacancyCardsAdapter.detect(ref(), probe_result) is False
