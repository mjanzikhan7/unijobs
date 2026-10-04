"""Guildhall School of Music & Drama adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.guildhall_vacancy_cards import GuildhallVacancyCardsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_GSMD_URL = "https://www.gsmd.ac.uk/jobs"
_GSMD_HEAD_URL = "https://www.gsmd.ac.uk/about-guildhall/vacancies/head-of-student-services"
_GSMD_SITS_URL = "https://www.gsmd.ac.uk/about-guildhall/vacancies/sits-technical-manager"
_GSMD_DEPUTY_URL = (
    "https://www.gsmd.ac.uk/about-guildhall/vacancies/deputy-head-of-student-services-operations"
)


def gsmd(html_fixture: Any) -> GuildhallVacancyCardsAdapter:
    """An adapter wired to Guildhall's real (redacted) listing and all 3 real detail pages."""
    listing_html = html_fixture("guildhall_vacancy_cards/listing-2026-09-04.html")
    head_html = html_fixture(
        "guildhall_vacancy_cards/detail-head-of-student-services-2026-09-04.html"
    )
    sits_html = html_fixture(
        "guildhall_vacancy_cards/detail-sits-technical-manager-2026-09-04.html"
    )
    deputy_html = html_fixture(
        "guildhall_vacancy_cards/detail-deputy-head-of-student-services-operations-2026-09-04.html"
    )
    return GuildhallVacancyCardsAdapter(
        http=FixtureHttpClient(
            responses={
                _GSMD_HEAD_URL: response(head_html, _GSMD_HEAD_URL),
                _GSMD_SITS_URL: response(sits_html, _GSMD_SITS_URL),
                _GSMD_DEPUTY_URL: response(deputy_html, _GSMD_DEPUTY_URL),
            }
        ),
        browser=FixtureBrowserSession(responses={_GSMD_URL: response(listing_html, _GSMD_URL)}),
    )


def test_guildhall_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 3 cards, one listing page, no pagination observed."""
    adapter = gsmd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GSMD_URL))

    assert len(vacancies) == 3


def test_guildhall_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = gsmd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GSMD_URL))

    head = next(v for v in vacancies if v.source_url == _GSMD_HEAD_URL)
    assert head.title == "Head of Student Services"
    assert "£59,060" in head.salary_raw
    assert head.contract_raw == "Permanent, Full Time (35 hours per week)"
    assert head.location_raw == "London, UK"
    assert head.closing_date == date(2026, 9, 21)


def test_guildhall_reads_the_closing_date_from_the_machine_readable_attribute(
    html_fixture: Any,
) -> None:
    """Read directly, not the human-readable text beside it.

    So this never depends on ``parse_uk_date``'s fuzzy matching at all.
    """
    adapter = gsmd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GSMD_URL))

    for vacancy in vacancies:
        assert vacancy.closing_date == date(2026, 9, 21)


def test_guildhall_is_detected_from_its_host() -> None:
    probe_result = ProbeResult(
        url=_GSMD_URL, status_code=200, html="<p>Loading…</p>", final_url=_GSMD_URL
    )

    adapter_class = detect_adapter(ref(_GSMD_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.GUILDHALL_VACANCY_CARDS


def test_a_host_with_no_guildhall_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert GuildhallVacancyCardsAdapter.detect(ref(), probe_result) is False
