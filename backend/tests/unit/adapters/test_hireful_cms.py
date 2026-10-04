"""Hireful CMS adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.hireful_cms import HirefulCmsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_SUSSEX_URL = "https://jobs.sussex.ac.uk/"


def sussex(html_fixture: Any) -> HirefulCmsAdapter:
    """An adapter wired to Sussex's real (redacted), rendered listing page."""
    html = html_fixture("hireful_cms/sussex-listing-2026-09-04.html")
    return HirefulCmsAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(responses={_SUSSEX_URL: response(html, _SUSSEX_URL)}),
    )


def test_hireful_cms_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 5 cards, one page, no pagination control observed."""
    adapter = sussex(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SUSSEX_URL))

    assert len(vacancies) == 5


def test_hireful_cms_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = sussex(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SUSSEX_URL))

    coordinator = next(v for v in vacancies if v.reference == "43863")
    assert coordinator.title == (
        "Student Placement Coordinator (Primary Care) Ref: 43863 (Internal Only)"
    )
    assert coordinator.department == "Brighton and Sussex Medical School"
    assert "£26,093" in coordinator.salary_raw
    assert coordinator.closing_date == date(2026, 9, 20)
    assert (
        coordinator.source_url
        == "https://jobs.sussex.ac.uk/job/030abd36-8d7d-46f6-a75d-75b7459193cc"
    )


def test_hireful_cms_is_detected_from_its_own_cms_api_reference(html_fixture: Any) -> None:
    html = html_fixture("hireful_cms/sussex-listing-2026-09-04.html")
    probe_result = ProbeResult(url=_SUSSEX_URL, status_code=200, html=html, final_url=_SUSSEX_URL)

    adapter_class = detect_adapter(ref(_SUSSEX_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.HIREFUL_CMS


def test_a_page_with_no_hireful_cms_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert HirefulCmsAdapter.detect(ref(), probe_result) is False
