"""SuccessFactors adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from crawler.adapters.successfactors import SuccessFactorsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError, SiteOffline
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_SF_URL = "https://career2.successfactors.eu/careers?company=coventryun"


def successfactors(html_fixture: Any) -> tuple[SuccessFactorsAdapter, FixtureBrowserSession]:
    """An adapter and its browser, wired to the Coventry results fixture.

    The same fixture answers both the plain preliminary fetch `list_vacancies` now makes to
    tell the two themes apart (it already carries the classic theme's `id="searchresults"` /
    `jobTitle-link` markers) and the post-click browser render.
    """
    coventry_html = html_fixture("successfactors/coventry-results-2026-08-24.html")
    browser = FixtureBrowserSession(responses={_SF_URL: response(coventry_html, _SF_URL)})
    adapter = SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_SF_URL: response(coventry_html, _SF_URL)}),
        browser=browser,
    )
    return adapter, browser


def test_successfactors_clicks_search_before_reading_the_results(html_fixture: Any) -> None:
    adapter, browser = successfactors(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SF_URL))

    assert browser.clicked == [(_SF_URL, 'text="Search Jobs"')]
    assert len(vacancies) == 13


def test_successfactors_records_the_browser_html_strategy(html_fixture: Any) -> None:
    adapter, _ = successfactors(html_fixture)

    adapter.list_vacancies(ref(_SF_URL))

    assert adapter.strategy is ExtractionStrategy.BROWSER_HTML


def test_successfactors_builds_absolute_vacancy_urls(html_fixture: Any) -> None:
    adapter, _ = successfactors(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SF_URL))

    assert all(item.source_url.startswith(_SF_URL.split("/careers")[0]) for item in vacancies)


def test_successfactors_reads_the_posted_date_not_a_missing_closing_date(
    html_fixture: Any,
) -> None:
    """No closing-date column exists in this theme.

    Leaving ``closing_date`` as ``None`` is honest; the posted date it does carry still lands
    in a field, not lost as a raw string.
    """
    adapter, _ = successfactors(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SF_URL))

    assert vacancies[0].closing_date is None
    assert vacancies[0].posted_date is not None


def test_successfactors_raises_without_a_browser(html_fixture: Any) -> None:
    """No fallback to plain HTTP: the results genuinely do not exist before the click."""
    coventry_html = html_fixture("successfactors/coventry-results-2026-08-24.html")
    adapter = SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_SF_URL: response(coventry_html, _SF_URL)})
    )

    with pytest.raises(SiteOffline):
        adapter.list_vacancies(ref(_SF_URL))


def test_successfactors_raises_on_a_theme_it_does_not_recognise() -> None:
    """Neither theme's own markup, nor a results table once rendered - a sign-in wall, say."""
    unrecognised = response("<html><body>No results table here</body></html>")
    browser = FixtureBrowserSession(responses={_SF_URL: unrecognised})
    adapter = SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_SF_URL: unrecognised}), browser=browser
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_SF_URL))


def test_successfactors_is_detected_from_its_host() -> None:
    url = "https://career2.successfactors.eu/careers?company=coventryun"
    institution_ref = InstitutionRef(slug="coventry", name="Coventry", careers_url=url)
    probe_result = ProbeResult(
        url=url, status_code=200, html="<html><body>Loading…</body></html>", final_url=url
    )

    adapter_class = detect_adapter(institution_ref, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.SUCCESSFACTORS


def test_successfactors_is_detected_from_the_sapsf_alias_host() -> None:
    """Sheffield's tenant lives on `career55.sapsf.eu`.

    SAP's shorter alias domain, the same product, but a host that never contains the string
    "successfactors" at all.
    """
    url = "https://career55.sapsf.eu/career?career_company=universi38"
    institution_ref = InstitutionRef(slug="sheffield", name="Sheffield", careers_url=url)
    probe_result = ProbeResult(
        url=url, status_code=200, html="<html><body>Loading…</body></html>", final_url=url
    )

    adapter_class = detect_adapter(institution_ref, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.SUCCESSFACTORS


_DMU_URL = "https://careers.dmu.ac.uk/search/?q=&searchResultView=LIST"
_SHEFFIELD_URL = (
    "https://jobsite.sheffield.ac.uk/search/?q=&locationsearch=&searchResultView=LIST"
    "&markerViewed=&carouselIndex=&facetFilters=%7B%7D&pageNumber=0"
)
_OU_URL = "https://jobs.open.ac.uk/search/?q=&"


def dmu(html_fixture: Any) -> SuccessFactorsAdapter:
    """An adapter wired to all 3 of De Montfort's real (redacted) result pages.

    De Montfort never publishes a salary or a labelled footer field at all - the fixture
    proving the unlabelled-and-no-shape-match case stays blank, not guessed.
    """
    page1 = response(html_fixture("successfactors/dmu-csb-page1-2026-09-04.html"), _DMU_URL)
    pages = [
        response(html_fixture(f"successfactors/dmu-csb-page{n}-2026-09-04.html"), _DMU_URL)
        for n in (1, 2, 3)
    ]
    return SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_DMU_URL: page1}),
        browser=FixtureBrowserSession(responses={}, paginated_responses={_DMU_URL: pages}),
    )


def test_successfactors_csb_follows_pagination_to_find_every_vacancy(html_fixture: Any) -> None:
    """21 vacancies across 3 pages (10 + 10 + 1) - the site's own 'Next' click gets pages 2-3."""
    adapter = dmu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DMU_URL))

    assert len(vacancies) == 21


def test_successfactors_csb_does_not_click_search(html_fixture: Any) -> None:
    """Unlike the classic theme, results are already in the DOM - no button to click at all."""
    adapter = dmu(html_fixture)
    browser = adapter.browser
    assert isinstance(browser, FixtureBrowserSession)

    adapter.list_vacancies(ref(_DMU_URL))

    assert browser.clicked == []


def test_successfactors_csb_leaves_unlabelled_fields_blank_with_no_shape_match(
    html_fixture: Any,
) -> None:
    """De Montfort labels nothing, and publishes no value that looks like a salary at all."""
    adapter = dmu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DMU_URL))

    director = next(
        v
        for v in vacancies
        if v.title == "Associate Director International (Strategy and Commercial)"
    )
    assert director.location_raw == "Leicester, GBR, LE1 9BH"
    assert director.salary_raw == ""
    assert director.contract_raw == ""
    assert director.source_url == (
        "https://careers.dmu.ac.uk/job/Associate-Director-International-%28Strategy-and-"
        "Commercial%29/641-en_GB"
    )


def test_successfactors_csb_reads_labelled_footer_fields(html_fixture: Any) -> None:
    """Open University labels its footer values - read by label text, not position."""
    html = html_fixture("successfactors/ou-csb-page1-2026-09-04.html")
    adapter = SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_OU_URL: response(html, _OU_URL)}),
        browser=FixtureBrowserSession(
            responses={}, paginated_responses={_OU_URL: [response(html, _OU_URL)]}
        ),
    )

    vacancies = adapter.list_vacancies(ref(_OU_URL))

    admin = next(v for v in vacancies if v.title == "Business Operations Administrator (Research)")
    assert admin.contract_raw == "Permanent"
    assert admin.closing_date == date(2026, 9, 8)
    assert admin.salary_raw == "£27,319 to £30,378 pro rata"


def test_successfactors_csb_reads_an_unlabelled_salary_by_its_own_shape(html_fixture: Any) -> None:
    """Sheffield labels nothing, but a comma-grouped number is unambiguously a salary anyway."""
    html = html_fixture("successfactors/sheffield-csb-page1-2026-09-04.html")
    adapter = SuccessFactorsAdapter(
        http=FixtureHttpClient(responses={_SHEFFIELD_URL: response(html, _SHEFFIELD_URL)}),
        browser=FixtureBrowserSession(
            responses={}, paginated_responses={_SHEFFIELD_URL: [response(html, _SHEFFIELD_URL)]}
        ),
    )

    vacancies = adapter.list_vacancies(ref(_SHEFFIELD_URL))

    exec_assistant = next(
        v for v in vacancies if v.title == "Executive Assistant to Centre Director"
    )
    assert exec_assistant.salary_raw == "32,080.00"
    assert exec_assistant.location_raw == "Sheffield, GBR,"
    assert exec_assistant.contract_raw == ""


def test_successfactors_csb_is_detected_from_its_react_root_and_a_successfactors_mention(
    html_fixture: Any,
) -> None:
    html = html_fixture("successfactors/dmu-csb-page1-2026-09-04.html")
    probe_result = ProbeResult(url=_DMU_URL, status_code=200, html=html, final_url=_DMU_URL)

    adapter_class = detect_adapter(ref(_DMU_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.SUCCESSFACTORS
