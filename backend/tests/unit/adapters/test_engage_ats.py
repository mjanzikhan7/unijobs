"""engage|ats adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.engage_ats import EngageAtsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_STANDREWS_CAREERS_URL = "https://www.st-andrews.ac.uk/jobs/"
_STANDREWS_ENC_URL = "https://www.vacancies.st-andrews.ac.uk/V2/Vacancy/Index?enc=TOKEN"
_LSE_LOGIN_URL = "https://jobs.lse.ac.uk/V2/Login"
_LSE_ENC_URL = "https://jobs.lse.ac.uk/V2/Vacancy/Index?enc=TOKEN"
_STRATH_LOGIN_URL = "https://strathvacancies.engageats.co.uk/"
_STRATH_ENC_URL = "https://strathvacancies.engageats.co.uk/V2/Vacancy/Index?enc=TOKEN"
_EXTERNAL_LINK_SELECTOR = 'a[href*="Vacancy/Index"], [onclick="RedirectToExternalVacancy()"]'


def standrews_engage(html_fixture: Any) -> EngageAtsAdapter:
    """St Andrews: its own site links straight to the listing - no login dance needed.

    Real, complete fixture set: all three pages the tenant's own pager reports, 10 + 10 + 7.
    """
    page1 = response(
        html_fixture("engage_ats/st-andrews-vacancy-page1-2026-08-26.html"), _STANDREWS_ENC_URL
    )
    page2 = response(
        html_fixture("engage_ats/st-andrews-vacancy-page2-2026-08-26.html"), _STANDREWS_ENC_URL
    )
    page3 = response(
        html_fixture("engage_ats/st-andrews-vacancy-page3-2026-08-26.html"), _STANDREWS_ENC_URL
    )
    browser = FixtureBrowserSession(
        responses={_STANDREWS_CAREERS_URL: page1},
        paginated_responses={_STANDREWS_ENC_URL: [page1, page2, page3]},
    )
    return EngageAtsAdapter(http=FixtureHttpClient(responses={}), browser=browser)


def test_engage_ats_reads_every_vacancy_across_every_page(html_fixture: Any) -> None:
    """Real St Andrews case: 27 openings advertised, spread 10/10/7 across three pages."""
    adapter = standrews_engage(html_fixture)

    vacancies = adapter.list_vacancies(ref(_STANDREWS_CAREERS_URL))

    assert len(vacancies) == 27
    assert len({v.reference for v in vacancies}) == 27


def test_engage_ats_clicks_the_static_link_not_a_login_button(html_fixture: Any) -> None:
    """St Andrews' own page has no login button at all - only the plain static link."""
    adapter = standrews_engage(html_fixture)

    adapter.list_vacancies(ref(_STANDREWS_CAREERS_URL))

    browser = adapter.browser
    assert isinstance(browser, FixtureBrowserSession)
    assert browser.clicked == [(_STANDREWS_CAREERS_URL, _EXTERNAL_LINK_SELECTOR)]


def test_engage_ats_reads_the_real_row_fields(html_fixture: Any) -> None:
    adapter = standrews_engage(html_fixture)

    vacancies = adapter.list_vacancies(ref(_STANDREWS_CAREERS_URL))

    cleaners = next(v for v in vacancies if v.reference == "461120")
    assert cleaners.title == "Cleaners - MC1229"
    assert cleaners.department == "Estates"
    assert cleaners.salary_raw == "£25,353 per annum pro rata"
    assert cleaners.source_url == (
        "https://www.vacancies.st-andrews.ac.uk/Vacancies/W/3414/0/461120/889/cleaners-mc1229"
    )


def test_engage_ats_does_not_guess_a_date_out_of_ongoing(html_fixture: Any) -> None:
    """Real case: this tenant writes "Ongoing" for no closing date - never parsed as one."""
    adapter = standrews_engage(html_fixture)

    vacancies = adapter.list_vacancies(ref(_STANDREWS_CAREERS_URL))

    cleaners = next(v for v in vacancies if v.reference == "461120")
    assert cleaners.closing_date is None


def test_engage_ats_is_detected_from_a_static_link_on_the_universitys_own_page(
    html_fixture: Any,
) -> None:
    """Real St Andrews case: its own `/jobs/` page is plain marketing content that links out."""
    html = html_fixture("engage_ats/st-andrews-landing-2026-08-26.html")
    probe_result = ProbeResult(
        url=_STANDREWS_CAREERS_URL,
        status_code=200,
        html=html,
        final_url=_STANDREWS_CAREERS_URL,
    )

    adapter_class = detect_adapter(ref(_STANDREWS_CAREERS_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ENGAGE_ATS


def lse_engage(html_fixture: Any) -> EngageAtsAdapter:
    """LSE: only the JS-bound button exists, no static link.

    Trimmed to one page on purpose - the real tenant has 7, but multi-page merging is already
    covered by the St Andrews test above; this fixture exists for field extraction and to prove
    the click selector finds the button when there is no static link to find instead.
    """
    page1 = response(html_fixture("engage_ats/lse-vacancy-page1-2026-08-26.html"), _LSE_ENC_URL)
    browser = FixtureBrowserSession(
        responses={_LSE_LOGIN_URL: page1},
        paginated_responses={_LSE_ENC_URL: [page1]},
    )
    return EngageAtsAdapter(http=FixtureHttpClient(responses={}), browser=browser)


def test_engage_ats_clicks_the_js_bound_button_when_no_static_link_exists(
    html_fixture: Any,
) -> None:
    adapter = lse_engage(html_fixture)

    adapter.list_vacancies(ref(_LSE_LOGIN_URL))

    browser = adapter.browser
    assert isinstance(browser, FixtureBrowserSession)
    assert browser.clicked == [(_LSE_LOGIN_URL, _EXTERNAL_LINK_SELECTOR)]


def test_engage_ats_reads_a_tenant_that_labels_the_classification_not_the_department(
    html_fixture: Any,
) -> None:
    """Real LSE case: "Job Type" and "Closing Date" are the only two labelled fields.

    Confirmed live: LSE's template never labels salary at all, unlike St Andrews'.
    """
    adapter = lse_engage(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LSE_LOGIN_URL))

    assistant_prof = next(v for v in vacancies if v.reference == "472496")
    assert assistant_prof.category == "Academic"
    assert assistant_prof.department == ""
    assert assistant_prof.salary_raw == ""
    assert assistant_prof.closing_date == date(2026, 10, 11)


def test_engage_ats_is_detected_from_the_login_pages_own_branding(html_fixture: Any) -> None:
    html = html_fixture("engage_ats/lse-login-2026-08-26.html")
    probe_result = ProbeResult(
        url=_LSE_LOGIN_URL, status_code=200, html=html, final_url=_LSE_LOGIN_URL
    )

    adapter_class = detect_adapter(ref(_LSE_LOGIN_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ENGAGE_ATS


def strathclyde_engage(html_fixture: Any) -> EngageAtsAdapter:
    """Strathclyde: labels the organisational unit "Department", not "School/Unit" or "Job Type"."""
    page1 = response(
        html_fixture("engage_ats/strathclyde-vacancy-page1-2026-08-26.html"), _STRATH_ENC_URL
    )
    browser = FixtureBrowserSession(
        responses={_STRATH_LOGIN_URL: page1},
        paginated_responses={_STRATH_ENC_URL: [page1]},
    )
    return EngageAtsAdapter(http=FixtureHttpClient(responses={}), browser=browser)


def test_engage_ats_reads_a_tenant_that_labels_the_department_not_the_classification(
    html_fixture: Any,
) -> None:
    adapter = strathclyde_engage(html_fixture)

    vacancies = adapter.list_vacancies(ref(_STRATH_LOGIN_URL))

    pdra = next(v for v in vacancies if v.reference == "473009")
    assert pdra.department == "Physics"
    assert pdra.category == ""
    assert pdra.closing_date == date(2026, 10, 21)


def test_engage_ats_is_detected_from_its_own_login_page(html_fixture: Any) -> None:
    html = html_fixture("engage_ats/strathclyde-login-2026-08-26.html")
    probe_result = ProbeResult(
        url=_STRATH_LOGIN_URL, status_code=200, html=html, final_url=_STRATH_LOGIN_URL
    )

    adapter_class = detect_adapter(ref(_STRATH_LOGIN_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ENGAGE_ATS


def test_a_page_with_no_engage_ats_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Working here</p>", final_url=CAREERS_URL
    )

    assert EngageAtsAdapter.detect(ref(), probe_result) is False
