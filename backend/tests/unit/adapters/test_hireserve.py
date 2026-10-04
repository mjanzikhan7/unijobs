"""Hireserve adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from crawler.adapters.corehr import CoreHRAdapter
from crawler.adapters.hireserve import HireserveAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_HIRESERVE_PAGE_URL = "https://jobs.aber.ac.uk/en/vacancies.html"
_HIRESERVE_FEED_URL = (
    "https://jobs.aber.ac.uk/utf8/ic_job_feeds.feed_engine?p_web_site_id=4249"
    "&p_published_to=WWW&p_language=DEFAULT&p_direct=Y&p_format=MOBILE"
    "&p_include_exclude_from_list=N&p_search=&p_summary=Y"
)


def hireserve(html_fixture: Any) -> HireserveAdapter:
    """An adapter wired to the two-request Hireserve fixture pair."""
    return HireserveAdapter(
        http=FixtureHttpClient(
            responses={
                _HIRESERVE_PAGE_URL: response(
                    html_fixture("hireserve/aberystwyth-vacancies-2026-08-24.html"),
                    _HIRESERVE_PAGE_URL,
                ),
                _HIRESERVE_FEED_URL: response(
                    html_fixture("hireserve/aberystwyth-results-2026-08-24.json"),
                    _HIRESERVE_FEED_URL,
                    content_type="application/json",
                ),
            }
        )
    )


def test_hireserve_reads_every_vacancy_from_the_feed(html_fixture: Any) -> None:
    adapter = hireserve(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    assert len(vacancies) == 5
    assert vacancies[0].title == "Kitchen Assistant"


def test_hireserve_records_the_json_api_strategy(html_fixture: Any) -> None:
    adapter = hireserve(html_fixture)

    adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    assert adapter.strategy is ExtractionStrategy.JSON_API


def test_hireserve_keeps_the_source_url_the_feed_published(html_fixture: Any) -> None:
    adapter = hireserve(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    assert (
        vacancies[0].source_url
        == "https://jobs.aber.ac.uk/en/vacancy/kitchen-assistant-614470.html"
    )


def test_hireserve_reads_salary_regardless_of_which_classification_carries_it(
    html_fixture: Any,
) -> None:
    """Both classifications sit alongside an empty same-keyword one.

    One tenant's feed puts the real figure under "Salary", another under "Salary Scale" - each
    alongside an empty same-keyword classification, so an adapter that just takes the first
    "salary"-ish field would get the empty one half the time.
    """
    adapter = hireserve(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    by_title = {v.title: v for v in vacancies}
    assert by_title["Kitchen Assistant"].salary_raw == "£25,528.10 per annum pro rata"
    assert (
        by_title["Specialist Mentor -ASC"].salary_raw
        == "£33,001.64 - £38,784.49 per annum (pro rata)"
    )


def test_hireserve_reads_the_department_contract_and_hours(html_fixture: Any) -> None:
    adapter = hireserve(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    kitchen = next(v for v in vacancies if v.title == "Kitchen Assistant")
    assert kitchen.department == "Aberystwyth Arts Centre"
    assert kitchen.contract_raw == "Permanent"
    assert kitchen.hours_raw == "20"


def test_hireserve_parses_the_closing_date(html_fixture: Any) -> None:
    adapter = hireserve(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))

    assert vacancies[0].closing_date == date(2026, 9, 6)


def test_hireserve_raises_when_no_tenant_id_is_published(html_fixture: Any) -> None:
    adapter = HireserveAdapter(
        http=FixtureHttpClient(
            responses={
                _HIRESERVE_PAGE_URL: response("<html><body>No form here</body></html>"),
            }
        )
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_HIRESERVE_PAGE_URL))


def test_hireserve_is_detected_from_the_icamsbase_asset_path() -> None:
    """The listing page is a client-rendered shell; the asset path is what is reliable."""
    url = "https://jobs.aber.ac.uk/en/vacancies.html"
    institution_ref = InstitutionRef(slug="aber", name="Aberystwyth", careers_url=url)
    probe_result = ProbeResult(
        url=url,
        status_code=200,
        html='<html><body><script src="/icamsbase/js/global.js"></script></body></html>',
        final_url=url,
    )

    adapter_class = detect_adapter(institution_ref, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.HIRESERVE


_YORK_URL = "https://jobs.york.ac.uk/wd/plsql/wd_portal.show_page?p_web_site_id=3885&p_text_id=1763"


def test_york_is_detected_as_hireserve_not_corehr(html_fixture: Any) -> None:
    """Real York case: ``wd_portal.show_page`` is generic Oracle PL/SQL, not CoreHR-specific.

    York's careers URL sits on that same shape while being an unambiguous Hireserve tenant.
    Confirmed live (26 Aug 2026): ``hireserve`` and a working ``p_web_site_id`` field are both
    present on the page; neither ``corehr`` nor ``coreportal_erecruit`` appears anywhere.
    """
    probe_result = ProbeResult(
        url=_YORK_URL,
        status_code=200,
        html=html_fixture("hireserve/york-vacancies-2026-08-26.html"),
        final_url=_YORK_URL,
    )

    adapter_class = detect_adapter(ref(_YORK_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.HIRESERVE


def test_corehr_does_not_claim_a_page_carrying_hireserves_own_signature(html_fixture: Any) -> None:
    """CoreHR's ``detect()`` in isolation must bail out, not just lose the registry order."""
    probe_result = ProbeResult(
        url=_YORK_URL,
        status_code=200,
        html=html_fixture("hireserve/york-vacancies-2026-08-26.html"),
        final_url=_YORK_URL,
    )

    assert CoreHRAdapter.detect(ref(_YORK_URL), probe_result) is False
