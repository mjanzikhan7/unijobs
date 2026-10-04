"""Rails-based jobs board adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.rails_jobs_board import RailsJobsBoardAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_GLASGOW_URL = (
    "https://www.jobs.gla.ac.uk/jobs?sort_type=relevance&query=&selected_locations=&submit=Search"
)
_GLASGOW_PAGE2_URL = (
    "https://www.jobs.gla.ac.uk/jobs?page=2&query=&selected_locations=&sort_type=relevance"
    "&submit=Search"
)
_GLASGOW_PAGE3_URL = (
    "https://www.jobs.gla.ac.uk/jobs?page=3&query=&selected_locations=&sort_type=relevance"
    "&submit=Search"
)


def glasgow(html_fixture: Any) -> RailsJobsBoardAdapter:
    """An adapter wired to all three of Glasgow's real (redacted, CSS-trimmed) result pages."""
    return RailsJobsBoardAdapter(
        http=FixtureHttpClient(
            responses={
                _GLASGOW_URL: response(
                    html_fixture("rails_jobs_board/glasgow-page1-2026-09-04.html"), _GLASGOW_URL
                ),
                _GLASGOW_PAGE2_URL: response(
                    html_fixture("rails_jobs_board/glasgow-page2-2026-09-04.html"),
                    _GLASGOW_PAGE2_URL,
                ),
                _GLASGOW_PAGE3_URL: response(
                    html_fixture("rails_jobs_board/glasgow-page3-2026-09-04.html"),
                    _GLASGOW_PAGE3_URL,
                ),
            }
        )
    )


def test_rails_jobs_board_follows_pagination_to_find_every_vacancy(html_fixture: Any) -> None:
    """20 + 20 + 10 across 3 pages - the site's own 'next' link is what gets pages 2 and 3."""
    adapter = glasgow(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GLASGOW_URL))

    assert len(vacancies) == 50


def test_rails_jobs_board_stops_when_a_page_has_no_next_link(html_fixture: Any) -> None:
    """Page 3 has no fixture registered for a page 4 - proves the loop actually stops there."""
    adapter = glasgow(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GLASGOW_URL))

    assert len({v.source_url for v in vacancies}) == 50


def test_rails_jobs_board_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = glasgow(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GLASGOW_URL))

    fellow = next(v for v in vacancies if v.title == "Clinical Fellow")
    assert fellow.location_raw == "Glasgow"
    assert fellow.salary_raw == "Clinical Academic: £51,348 - £77,389 per annum"
    assert fellow.reference == "6008305"
    assert fellow.source_url == "https://www.jobs.gla.ac.uk/job/clinical-fellow-6008305"
    assert "Stereotactic Ablative Radiotherapy" in fellow.description_text


def test_rails_jobs_board_tags_every_vacancy_with_the_institution(html_fixture: Any) -> None:
    adapter = glasgow(html_fixture)

    vacancies = adapter.list_vacancies(ref(_GLASGOW_URL))

    assert all(v.institution_slug == "university-of-test" for v in vacancies)


def test_rails_jobs_board_is_detected_from_its_results_page_markup(html_fixture: Any) -> None:
    html = html_fixture("rails_jobs_board/glasgow-page1-2026-09-04.html")
    probe_result = ProbeResult(url=_GLASGOW_URL, status_code=200, html=html, final_url=_GLASGOW_URL)

    adapter_class = detect_adapter(ref(_GLASGOW_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.RAILS_JOBS_BOARD


def test_a_page_with_no_rails_jobs_board_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert RailsJobsBoardAdapter.detect(ref(), probe_result) is False
