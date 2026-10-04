"""Webrecruit adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.webrecruit import WebrecruitAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_UWTSD_URL = "https://jobs.uwtsd.ac.uk/Home"


def uwtsd(html_fixture: Any) -> WebrecruitAdapter:
    """An adapter wired to UWTSD's real (redacted), plain-HTTP-fetched listing page."""
    return WebrecruitAdapter(
        http=FixtureHttpClient(
            responses={
                _UWTSD_URL: response(
                    html_fixture("webrecruit/uwtsd-listing-2026-09-04.html"), _UWTSD_URL
                )
            }
        )
    )


def test_webrecruit_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 4 cards, one page, no pagination control observed."""
    adapter = uwtsd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_UWTSD_URL))

    assert len(vacancies) == 4


def test_webrecruit_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = uwtsd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_UWTSD_URL))

    lecturer = next(
        v
        for v in vacancies
        if v.title == "Senior Lecturer for L4 Therapy Assistant Practitioner Apprenticeship"
    )
    assert lecturer.reference == "51754"
    assert lecturer.location_raw == "Swansea"
    assert "£48,822" in lecturer.salary_raw
    assert lecturer.contract_raw == "Fixed Term Contract"
    assert lecturer.hours_raw == "14.8"
    assert lecturer.category == "Academic"
    assert lecturer.closing_date == date(2026, 9, 11)
    assert lecturer.source_url == "https://jobs.uwtsd.ac.uk/JobDescription/R003qYKGM4U"


def test_webrecruit_uses_the_job_description_link_not_the_send_to_friend_link(
    html_fixture: Any,
) -> None:
    """The "Send to a Friend" link carries a different id for the same vacancy - never used."""
    adapter = uwtsd(html_fixture)

    vacancies = adapter.list_vacancies(ref(_UWTSD_URL))

    assert all("JobDescription" in v.source_url for v in vacancies)
    assert all("SendToFriend" not in v.source_url for v in vacancies)


def test_webrecruit_is_detected_from_its_footer_credit(html_fixture: Any) -> None:
    html = html_fixture("webrecruit/uwtsd-listing-2026-09-04.html")
    probe_result = ProbeResult(url=_UWTSD_URL, status_code=200, html=html, final_url=_UWTSD_URL)

    adapter_class = detect_adapter(ref(_UWTSD_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.WEBRECRUIT


def test_a_page_with_no_webrecruit_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert WebrecruitAdapter.detect(ref(), probe_result) is False
