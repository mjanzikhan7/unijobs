"""Liverpool Hope adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.liverpool_hope_vacancy_tables import LiverpoolHopeVacancyTablesAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_HOPE_URL = "https://www.hope.ac.uk/aboutus/jobopportunities/currentvacancies/"


def hope(html_fixture: Any) -> LiverpoolHopeVacancyTablesAdapter:
    """An adapter wired to Liverpool Hope's real (redacted), plain-HTTP-fetched listing page."""
    return LiverpoolHopeVacancyTablesAdapter(
        http=FixtureHttpClient(
            responses={
                _HOPE_URL: response(
                    html_fixture("liverpool_hope_vacancy_tables/listing-2026-09-04.html"),
                    _HOPE_URL,
                )
            }
        )
    )


def test_hope_reads_every_real_vacancy_across_all_category_tables(html_fixture: Any) -> None:
    """Real case: 2 vacancies total, spread across 5 category tables, most of them empty."""
    adapter = hope(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HOPE_URL))

    assert len(vacancies) == 2


def test_hope_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = hope(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HOPE_URL))

    catering = next(v for v in vacancies if v.title == "Catering Assistant")
    assert catering.reference == "9CAT1A"
    assert catering.category == "Professional Services vacancies"
    assert catering.closing_date == date(2026, 9, 22)
    assert catering.extra["closing_time"] == "5.00pm"


def test_hope_tells_a_header_row_from_a_data_row_by_its_link(html_fixture: Any) -> None:
    """Every real vacancy title is a link; no header cell ever is - that is the discriminator."""
    adapter = hope(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HOPE_URL))

    assert all(v.title not in ("Job Title", "") for v in vacancies)


def test_hope_is_detected_from_its_host() -> None:
    probe_result = ProbeResult(
        url=_HOPE_URL, status_code=200, html="<p>Loading…</p>", final_url=_HOPE_URL
    )

    adapter_class = detect_adapter(ref(_HOPE_URL), probe_result)

    assert (
        adapter_class is not None
        and adapter_class.platform is Platform.LIVERPOOL_HOPE_VACANCY_TABLES
    )


def test_a_host_with_no_hope_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert LiverpoolHopeVacancyTablesAdapter.detect(ref(), probe_result) is False
