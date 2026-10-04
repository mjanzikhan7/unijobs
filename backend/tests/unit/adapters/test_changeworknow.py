"""ChangeWorkNow / ISW adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.changeworknow import ChangeWorkNowAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_HARTPURY_URL = "https://isw.changeworknow.co.uk/hartpury/vms/e/careers/search/new"


def hartpury(html_fixture: Any) -> ChangeWorkNowAdapter:
    return ChangeWorkNowAdapter(
        http=FixtureHttpClient(
            responses={
                _HARTPURY_URL: response(
                    html_fixture("changeworknow/hartpury-vacancies-2026-08-26.html"),
                    _HARTPURY_URL,
                )
            }
        )
    )


def test_changeworknow_reads_every_vacancy_from_one_plain_fetch(html_fixture: Any) -> None:
    """Real Hartpury case: all 16 vacancies are already in the plain HTTP response."""
    adapter = hartpury(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HARTPURY_URL))

    assert len(vacancies) == 16


def test_changeworknow_reads_the_real_row_fields(html_fixture: Any) -> None:
    adapter = hartpury(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HARTPURY_URL))

    lecturer = next(v for v in vacancies if "A-Level Lecturer in Physics" in v.title)
    assert lecturer.contract_raw == "Fixed Term"
    assert lecturer.closing_date == date(2026, 8, 28)
    assert lecturer.salary_raw == (
        "£15,388 - £26,895 per annum (Dependent on qualifications and experience)"
    )
    assert lecturer.reference == "cr3t03CefgTBy0CzfdUT4w"
    assert lecturer.source_url == (
        "https://isw.changeworknow.co.uk/hartpury/vms/e/careers/positions/cr3t03CefgTBy0CzfdUT4w"
    )


def test_changeworknow_is_detected_from_its_host_and_path() -> None:
    probe_result = ProbeResult(
        url=_HARTPURY_URL,
        status_code=200,
        html="<html><body>Loading…</body></html>",
        final_url=_HARTPURY_URL,
    )

    adapter_class = detect_adapter(ref(_HARTPURY_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.CHANGEWORKNOW


def test_a_changeworknow_host_with_no_careers_path_is_not_detected() -> None:
    url = "https://isw.changeworknow.co.uk/hartpury/some/other/page"
    probe_result = ProbeResult(url=url, status_code=200, html="<p>Nothing</p>", final_url=url)

    assert ChangeWorkNowAdapter.detect(ref(url), probe_result) is False
