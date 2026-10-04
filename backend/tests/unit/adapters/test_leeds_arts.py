"""Leeds Arts adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.leeds_arts import LeedsArtsAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_LEEDS_ARTS_URL = "https://www.leeds-art.ac.uk/about-us/jobs"
_LEEDS_ARTS_DETAIL_URL = (
    "https://www.leeds-art.ac.uk/about-us/jobs/lecturer-ba-hons-fashion-photography"
)


def leeds_arts(html_fixture: Any) -> LeedsArtsAdapter:
    """An adapter wired to Leeds Arts's real (redacted) listing and its one fixtured detail page.

    The listing carries 5 real links, including a "skip to main content" accessibility link and
    a self-link back to the listing itself - both real cases, confirmed live - so the detail
    fixture is only registered for the one vacancy the field-reading tests check; the other four
    resolve to whatever ``FixtureHttpClient``'s ``default`` provides.
    """
    listing_html = html_fixture("leeds_arts/list-2026-09-04.html")
    detail_html = html_fixture("leeds_arts/detail-fashion-photography-2026-09-04.html")
    return LeedsArtsAdapter(
        http=FixtureHttpClient(
            responses={_LEEDS_ARTS_DETAIL_URL: response(detail_html, _LEEDS_ARTS_DETAIL_URL)},
            default=response(detail_html, _LEEDS_ARTS_DETAIL_URL),
        ),
        browser=FixtureBrowserSession(
            responses={_LEEDS_ARTS_URL: response(listing_html, _LEEDS_ARTS_URL)}
        ),
    )


def test_leeds_arts_reads_every_real_vacancy_link_only(html_fixture: Any) -> None:
    """5 real vacancies - neither the skip link nor the listing's own self-link counted."""
    adapter = leeds_arts(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LEEDS_ARTS_URL))

    assert len(vacancies) == 5
    assert all(v.source_url != _LEEDS_ARTS_URL for v in vacancies)


def test_leeds_arts_reads_the_real_detail_fields(html_fixture: Any) -> None:
    adapter = leeds_arts(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LEEDS_ARTS_URL))

    photography = next(v for v in vacancies if v.source_url == _LEEDS_ARTS_DETAIL_URL)
    assert photography.title == "Lecturer - BA (Hons) Fashion Photography"
    assert photography.salary_raw == "c £39,000 per annum, pro rata"
    assert photography.hours_raw == "Part time - 0.4 FTE"
    assert photography.contract_raw == "Permanent"
    assert photography.closing_date == date(2026, 9, 6)


def test_leeds_arts_is_detected_from_its_host_and_path() -> None:
    probe_result = ProbeResult(
        url=_LEEDS_ARTS_URL, status_code=200, html="<p>Loading…</p>", final_url=_LEEDS_ARTS_URL
    )

    adapter_class = detect_adapter(ref(_LEEDS_ARTS_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.LEEDS_ARTS_VACANCY_CARDS


def test_a_leeds_arts_host_with_no_careers_path_is_not_detected() -> None:
    url = "https://www.leeds-art.ac.uk/some/other/page"
    probe_result = ProbeResult(url=url, status_code=200, html="<p>Nothing</p>", final_url=url)

    assert LeedsArtsAdapter.detect(ref(url), probe_result) is False
