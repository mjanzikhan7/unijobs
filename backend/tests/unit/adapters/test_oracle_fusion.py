"""Oracle Fusion Cloud Recruiting adapter tests, against cached fixtures."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from crawler.adapters.oracle_fusion import OracleFusionAdapter
from crawler.exceptions import ParseError
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_HW_URL = "https://enzj.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX"
_HW_LIST_URL = (
    "https://enzj.fa.em3.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    "?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX,limit=50,offset=0"
)
_HW_PAGE_HTML = (
    '<html><body data-apibaseurl="https://enzj.fa.em3.oraclecloud.com">Loading…</body></html>'
)

_BHAM_URL = "https://edzz.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_6001"
_BHAM_LIST_BASE = (
    "https://edzz.fa.em3.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    "?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_6001,limit=50,offset="
)
_BHAM_PAGE_HTML = (
    '<html><body data-apibaseurl="https://edzz.fa.em3.oraclecloud.com">Loading…</body></html>'
)


def heriot_watt(html_fixture: Any) -> OracleFusionAdapter:
    """An adapter wired to Heriot-Watt's real (trimmed) list, one real detail, one default."""
    return OracleFusionAdapter(
        http=FixtureHttpClient(
            responses={
                _HW_URL: response(_HW_PAGE_HTML, _HW_URL),
                _HW_LIST_URL: response(
                    html_fixture("oracle_fusion/heriotwatt-list-2026-08-25.json"), _HW_LIST_URL
                ),
            },
            default=response(html_fixture("oracle_fusion/heriotwatt-detail-4964-2026-08-25.json")),
        )
    )


def birmingham(html_fixture: Any) -> OracleFusionAdapter:
    """An adapter wired to Birmingham's real listing, split across two real pages."""
    page1_url = f"{_BHAM_LIST_BASE}0"
    page2_url = f"{_BHAM_LIST_BASE}2"
    return OracleFusionAdapter(
        http=FixtureHttpClient(
            responses={
                _BHAM_URL: response(_BHAM_PAGE_HTML, _BHAM_URL),
                page1_url: response(
                    html_fixture("oracle_fusion/birmingham-list-page1-2026-08-25.json"), page1_url
                ),
                page2_url: response(
                    html_fixture("oracle_fusion/birmingham-list-page2-2026-08-25.json"), page2_url
                ),
            },
            default=response(html_fixture("oracle_fusion/birmingham-detail-9771-2026-08-25.json")),
        )
    )


def test_oracle_fusion_reads_every_real_vacancy(html_fixture: Any) -> None:
    adapter = heriot_watt(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HW_URL))

    assert len(vacancies) == 3


def test_oracle_fusion_pages_past_the_first_batch(html_fixture: Any) -> None:
    """Birmingham's real listing has more vacancies than fit in one page.

    A single fetch would have silently under-counted; `TotalJobsCount` is what tells this
    adapter there is a second page to ask for at all.
    """
    adapter = birmingham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BHAM_URL))

    assert len(vacancies) == 4
    assert {v.reference for v in vacancies} == {"9771", "9852", "9853", "9855"}


def test_oracle_fusion_reads_the_real_detail_fields(html_fixture: Any) -> None:
    adapter = heriot_watt(html_fixture)

    vacancies = adapter.list_vacancies(ref(_HW_URL))

    stewardship = next(v for v in vacancies if v.reference == "4964")
    assert stewardship.title == "Stewardship Officer"
    assert stewardship.location_raw == "Edinburgh, Midlothian, United Kingdom"
    assert stewardship.salary_raw == "Grade 5 (£26,707 - £31,236)"
    assert stewardship.contract_raw == "Full time"
    assert stewardship.closing_date == date(2026, 9, 15)
    assert (
        stewardship.source_url
        == "https://enzj.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/job/4964"
    )


def test_oracle_fusion_leaves_salary_blank_rather_than_guess_at_unlabelled_prose(
    html_fixture: Any,
) -> None:
    """Regression: Birmingham's real template never labels its salary at all.

    Heriot-Watt's template does (`<strong>Grade and Salary:</strong>`), and it would have been
    easy to assume every tenant's description follows the same shape. It does not - Birmingham's
    real advert opens with free-flowing prose, no bold labels of any kind - and nothing here
    tries to guess a figure out of that rather than admit it found none.
    """
    adapter = birmingham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BHAM_URL))

    professor = next(v for v in vacancies if v.reference == "9771")
    assert professor.salary_raw == ""
    assert "School of Engineering" in professor.description_text


def test_oracle_fusion_never_requests_the_same_vacancy_twice(html_fixture: Any) -> None:
    adapter = birmingham(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BHAM_URL))

    assert len({v.source_url for v in vacancies}) == len(vacancies)


_CSG_URL = "https://jobs.citystgeorges.ac.uk/en/sites/CX_1001"
_CSG_REAL_BASE = "https://iahmme.fa.ocs.oraclecloud.com:443"


def test_oracle_fusion_resolves_the_real_api_host_off_a_custom_domain_page(
    html_fixture: Any,
) -> None:
    """Real City St George's case: the page's own host does not proxy the API at all.

    Confirmed live: ``jobs.citystgeorges.ac.uk/hcmRestApi/...`` answers with a redirect, not
    JSON, while the host the page's own ``data-apibaseurl`` names answers with real data.
    """
    html = html_fixture("oracle_fusion/city-st-georges-listing-2026-08-26.html")

    base, site_number = OracleFusionAdapter._site(_CSG_URL, html)

    assert base == _CSG_REAL_BASE
    assert site_number == "CX_1001"


def test_oracle_fusion_calls_the_real_api_host_not_the_custom_domain(html_fixture: Any) -> None:
    """End-to-end: `list_vacancies` must never call the custom domain's own `/hcmRestApi/...`.

    `FixtureHttpClient` only knows the real host's URLs - a client that called the custom
    domain's API path instead would get `SiteOffline` (no fixture registered), not a result.
    """
    list_url = (
        f"{_CSG_REAL_BASE}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        "?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1001,limit=50,offset=0"
    )
    adapter = OracleFusionAdapter(
        http=FixtureHttpClient(
            responses={
                _CSG_URL: response(
                    html_fixture("oracle_fusion/city-st-georges-listing-2026-08-26.html"), _CSG_URL
                ),
                list_url: response(json.dumps({"items": [{"requisitionList": []}]}), list_url),
            }
        )
    )

    vacancies = adapter.list_vacancies(ref(_CSG_URL))

    assert vacancies == []
    assert list_url in adapter.http.requested  # type: ignore[attr-defined]


def test_oracle_fusion_is_detected_from_its_host_and_path() -> None:
    probe_result = ProbeResult(
        url=_HW_URL, status_code=200, html="<html><body>Loading…</body></html>", final_url=_HW_URL
    )

    adapter_class = detect_adapter(ref(_HW_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ORACLE_FUSION


def test_oracle_fusion_is_detected_on_a_custom_domain_tenant_from_page_content(
    html_fixture: Any,
) -> None:
    """Real City St George's case: the visited URL never mentions ``oraclecloud`` at all.

    ``jobs.citystgeorges.ac.uk`` serves the same Oracle Fusion Candidate Experience product from
    its own custom domain - the host+path check alone cannot see it, but the rendered page's own
    ``data-apibaseurl`` and favicon links still carry the real ``oraclecloud.com`` API host.
    """
    url = "https://jobs.citystgeorges.ac.uk/en/sites/CX_1001"
    probe_result = ProbeResult(
        url=url,
        status_code=200,
        html=html_fixture("oracle_fusion/city-st-georges-listing-2026-08-26.html"),
        final_url=url,
    )

    adapter_class = detect_adapter(ref(url), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ORACLE_FUSION


def test_a_bare_oraclecloud_host_with_no_candidate_experience_path_is_not_detected() -> None:
    url = "https://enzj.fa.em3.oraclecloud.com/some/other/product"
    probe_result = ProbeResult(
        url=url, status_code=200, html="<html><body>Loading…</body></html>", final_url=url
    )

    assert OracleFusionAdapter.detect(ref(url), probe_result) is False


def test_oracle_fusion_fails_loudly_when_the_url_has_no_site_number() -> None:
    bad_url = "https://enzj.fa.em3.oraclecloud.com/hcmUI/CandidateExperience/en/"
    adapter = OracleFusionAdapter(
        http=FixtureHttpClient(responses={bad_url: response("<html></html>", bad_url)})
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(bad_url))
