"""Contensis CMS jobs adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.contensis_jobs import ContensisJobsAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_KCL_URL = "https://www.kcl.ac.uk/jobs/search"


def kcl(html_fixture: Any) -> ContensisJobsAdapter:
    """An adapter wired to all 10 of King's real (redacted) result pages."""
    responses = {
        _KCL_URL: response(html_fixture("contensis_jobs/kcl-page1-2026-09-04.html"), _KCL_URL)
    }
    for page in range(2, 11):
        page_url = f"{_KCL_URL}?page={page}"
        responses[page_url] = response(
            html_fixture(f"contensis_jobs/kcl-page{page}-2026-09-04.html"), page_url
        )
    return ContensisJobsAdapter(http=FixtureHttpClient(responses=responses))


def test_contensis_jobs_follows_pagination_to_find_every_vacancy(html_fixture: Any) -> None:
    """99 vacancies across 10 pages of 10 - read from ``pagingInfo.pageCount``, not guessed."""
    adapter = kcl(html_fixture)

    vacancies = adapter.list_vacancies(ref(_KCL_URL))

    assert len(vacancies) == 99


def test_contensis_jobs_tags_every_vacancy_with_the_institution(html_fixture: Any) -> None:
    adapter = kcl(html_fixture)

    vacancies = adapter.list_vacancies(ref(_KCL_URL))

    assert all(v.institution_slug == "university-of-test" for v in vacancies)


def test_contensis_jobs_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = kcl(html_fixture)

    vacancies = adapter.list_vacancies(ref(_KCL_URL))

    star = next(v for v in vacancies if v.reference == "155766")
    assert star.title == "A-STAR Research Assistant"
    assert star.department == "St John's Institute of Dermatology"
    assert star.category == "Research"
    assert star.location_raw == "St Thomas Hospital"
    assert star.salary_raw == (
        "£39,076 – £43,909 per annum inclusive of London Weighting Allowance"  # noqa: RUF001
    )
    assert star.posted_date == date(2026, 8, 18)
    assert star.closing_date == date(2026, 9, 6)
    assert star.source_url == "https://www.kcl.ac.uk/jobs/155766-a-star-research-assistant"


def test_contensis_jobs_never_populates_extra(html_fixture: Any) -> None:
    """No blanket dict-dump of the raw entry - only the fields this adapter explicitly reads.

    Confirmed live, `contactPhoneText` on this real data is a named individual's email address
    (a King's data-entry quirk, not a phone number) - personal contact data this project has no
    use for. This adapter reads named fields one at a time rather than copying the raw entry
    into `RawVacancy.extra`, specifically so a field like that can never end up there by accident.
    """
    adapter = kcl(html_fixture)

    vacancies = adapter.list_vacancies(ref(_KCL_URL))

    assert all(v.extra == {} for v in vacancies)


def test_contensis_jobs_is_detected_from_its_redux_data_signature(html_fixture: Any) -> None:
    html = html_fixture("contensis_jobs/kcl-page1-2026-09-04.html")
    probe_result = ProbeResult(url=_KCL_URL, status_code=200, html=html, final_url=_KCL_URL)

    adapter_class = detect_adapter(ref(_KCL_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.CONTENSIS_JOBS


def test_a_page_with_no_contensis_jobs_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert ContensisJobsAdapter.detect(ref(), probe_result) is False
