"""Cambridge adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.cambridge_views_table import CambridgeViewsTableAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_CAMBRIDGE_URL = "https://www.cam.ac.uk/jobs/search?search_api_views_fulltext="


def cambridge(html_fixture: Any) -> CambridgeViewsTableAdapter:
    """An adapter serving the (trimmed, 8-row) real listing fixture."""
    return CambridgeViewsTableAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("cambridge_views_table/cambridge-listing-2026-08-24.html"),
                _CAMBRIDGE_URL,
            ),
        )
    )


def test_cambridge_reads_every_row_in_one_plain_request(html_fixture: Any) -> None:
    """No pagination, no browser: the whole listing renders in one server response."""
    adapter = cambridge(html_fixture)

    vacancies = adapter.list_vacancies(ref(_CAMBRIDGE_URL))

    assert len(vacancies) == 8
    assert vacancies[0].title == "Research Assistant (Fixed Term)"


def test_cambridge_captures_the_category_column(html_fixture: Any) -> None:
    """The one platform in this codebase that hands back a real job category."""
    adapter = cambridge(html_fixture)

    vacancies = adapter.list_vacancies(ref(_CAMBRIDGE_URL))

    assert [v.category for v in vacancies[:3]] == ["Research", "Research", "Academic"]


def test_cambridge_builds_absolute_vacancy_urls(html_fixture: Any) -> None:
    adapter = cambridge(html_fixture)

    vacancies = adapter.list_vacancies(ref(_CAMBRIDGE_URL))

    assert all(v.source_url.startswith("https://www.cam.ac.uk/jobs/") for v in vacancies)


def test_cambridge_reads_the_reference_and_salary(html_fixture: Any) -> None:
    adapter = cambridge(html_fixture)

    vacancies = adapter.list_vacancies(ref(_CAMBRIDGE_URL))

    first = vacancies[0]
    assert first.reference == "RD50817"
    assert first.salary_raw == "£33,002-£35,608"


def test_cambridge_is_detected_by_its_column_shape() -> None:
    """Detected by a distinctive combination of header ids.

    Not the ``cam.ac.uk`` host - so another institution built on the same Drupal Views shape
    would still match.
    """
    html = (
        "<table><thead><tr>"
        '<th id="view-title-table-column">Title</th>'
        '<th id="view-field-category-table-column">Category</th>'
        '<th id="view-field-closing-date-table-column">Closes</th>'
        "</tr></thead></table>"
    )
    ref_ = InstitutionRef(slug="test", name="Test", careers_url="https://jobs.example.ac.uk/")
    probe_result = ProbeResult(
        url=ref_.careers_url, status_code=200, html=html, final_url=ref_.careers_url
    )

    adapter_class = detect_adapter(ref_, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.CAMBRIDGE_VIEWS_TABLE
