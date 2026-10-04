"""Funnelback adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.funnelback import FunnelbackAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_DERBY_PAGE1_URL = (
    "https://www.derby.ac.uk/jobs/current-vacancies/"
    "?query=&collection=derbyu~sp-jobs-meta&profile=_default"
)
_DERBY_PAGE2_URL = (
    "https://www.derby.ac.uk/jobs/current-vacancies/"
    "?collection=derbyu~sp-jobs-meta&profile=_default&query=&start_rank=11"
)
_DERBY_PAGE3_URL = (
    "https://www.derby.ac.uk/jobs/current-vacancies/"
    "?collection=derbyu~sp-jobs-meta&profile=_default&query=&start_rank=21"
)


def derby(html_fixture: Any) -> FunnelbackAdapter:
    """An adapter wired to Derby's real (redacted), plain-HTTP-fetched, 3-page listing."""
    return FunnelbackAdapter(
        http=FixtureHttpClient(
            responses={
                _DERBY_PAGE1_URL: response(
                    html_fixture("funnelback/derby-page1-2026-09-04.html"), _DERBY_PAGE1_URL
                ),
                _DERBY_PAGE2_URL: response(
                    html_fixture("funnelback/derby-page2-2026-09-04.html"), _DERBY_PAGE2_URL
                ),
                _DERBY_PAGE3_URL: response(
                    html_fixture("funnelback/derby-page3-2026-09-04.html"), _DERBY_PAGE3_URL
                ),
            }
        )
    )


def test_funnelback_reads_every_real_vacancy_across_all_three_pages(html_fixture: Any) -> None:
    """Real case: 23 results, 10 per page, the third page carrying no "Next" link at all."""
    adapter = derby(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DERBY_PAGE1_URL))

    assert len(vacancies) == 23


def test_funnelback_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = derby(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DERBY_PAGE1_URL))

    researcher = next(
        v for v in vacancies if v.title == "Academic Researcher in Biomedical Science"
    )
    assert researcher.reference == "academic-researcher-biomedical-science"
    assert researcher.hours_raw == "Full-time"
    assert researcher.contract_raw == "Permanent"
    assert "£29,588" in researcher.salary_raw
    assert researcher.closing_date == date(2026, 9, 14)


def test_funnelback_reads_the_target_url_from_the_title_attribute_not_the_tracking_href(
    html_fixture: Any,
) -> None:
    """The link's own ``href`` is a Funnelback tracking redirect, never stored as source_url."""
    adapter = derby(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DERBY_PAGE1_URL))

    researcher = next(
        v for v in vacancies if v.reference == "academic-researcher-biomedical-science"
    )
    assert researcher.source_url == (
        "https://www.derby.ac.uk/jobs/current-vacancies/academic-researcher-biomedical-science/"
    )
    assert "funnelback" not in researcher.source_url


def test_funnelback_is_detected_from_its_own_search_backend(html_fixture: Any) -> None:
    html = html_fixture("funnelback/derby-page1-2026-09-04.html")
    probe_result = ProbeResult(
        url=_DERBY_PAGE1_URL, status_code=200, html=html, final_url=_DERBY_PAGE1_URL
    )

    adapter_class = detect_adapter(ref(_DERBY_PAGE1_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.FUNNELBACK


def test_a_page_with_no_funnelback_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert FunnelbackAdapter.detect(ref(), probe_result) is False
