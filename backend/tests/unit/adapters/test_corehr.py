"""CoreHR adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.corehr import CoreHRAdapter
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import ref, response

_SHU_FORM_URL = "https://my.corehr.com/pls/shurecruit/erq_search_package.search_form"
_SHU_SUBMIT_URL = (
    "https://my.corehr.com/pls/shurecruit/erq_search_version_4.start_search_with_params"
)


def corehr_shu(html_fixture: Any) -> CoreHRAdapter:
    """Sheffield Hallam: a blank search-form page, then its own submission's real results."""
    return CoreHRAdapter(
        http=FixtureHttpClient(
            responses={
                _SHU_FORM_URL: response(
                    html_fixture("corehr/sheffield-hallam-search-form-2026-08-25.html"),
                    _SHU_FORM_URL,
                ),
                _SHU_SUBMIT_URL: response(
                    html_fixture("corehr/sheffield-hallam-results-2026-08-25.html"),
                    _SHU_SUBMIT_URL,
                ),
            }
        )
    )


def test_corehr_submits_the_blank_search_form_before_reading_results(html_fixture: Any) -> None:
    """Real Sheffield Hallam case: the careers URL is an empty form, not a results page.

    Submitting only the "obvious" fields (company, internal/external) gets a 403 for real - the
    tenant expects every one of the form's own hidden fields present, blank ones included.
    """
    adapter = corehr_shu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SHU_FORM_URL))

    assert len(vacancies) == 28
    assert _SHU_SUBMIT_URL in adapter.http.requested  # type: ignore[attr-defined]


def test_corehr_reads_the_real_row_shape(html_fixture: Any) -> None:
    adapter = corehr_shu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SHU_FORM_URL))

    tutor = next(v for v in vacancies if "Aerospace Engineering" in v.title)
    assert tutor.salary_raw == "Grade 6 - £32,080 to £38,784 per annum (depending on experience)"
    assert tutor.source_url.endswith("119107")


def test_corehr_reads_a_results_page_that_also_carries_a_maintenance_notice(
    html_fixture: Any,
) -> None:
    """Real Liverpool case - the same false-positive shape as the iTrent maintenance test above.

    The results page carries a banner about a scheduled *future* maintenance window while still
    returning real vacancies underneath it (the tenant's own count claims 47 exist; this fixture
    is trimmed to just page one's 5, with the "next page" form removed so the test stays about
    the banner rather than pagination, which is covered separately). Treating the banner as
    fatal on its own would report a working tenant as OFFLINE on every crawl.
    """
    url = "https://my.corehr.com/pls/ulivrecruit/erq_search_version_4.start_search_with_params"
    adapter = CoreHRAdapter(
        http=FixtureHttpClient(
            responses={
                url: response(
                    html_fixture(
                        "corehr/liverpool-results-with-maintenance-banner-2026-08-25.html"
                    ),
                    url,
                )
            }
        )
    )

    vacancies = adapter.list_vacancies(ref(url))

    assert len(vacancies) == 5
