"""PostingPanda adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.postingpanda import PostingPandaAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_SOAS_URL = "https://vacancies.soas.ac.uk/"


def soas(html_fixture: Any) -> PostingPandaAdapter:
    """An adapter wired to SOAS's real (redacted) rendered page."""
    html = html_fixture("postingpanda/soas-2026-09-04.html")
    return PostingPandaAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(responses={_SOAS_URL: response(html, _SOAS_URL)}),
    )


def test_postingpanda_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 8 cards, one page, no pagination."""
    adapter = soas(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SOAS_URL))

    assert len(vacancies) == 8


def test_postingpanda_reads_the_icon_labelled_fields(html_fixture: Any) -> None:
    adapter = soas(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SOAS_URL))

    officer = next(v for v in vacancies if v.title == "Research Impact Officer")
    assert officer.location_raw == "Bloomsbury, Camden, Greater London, United Kingdom"
    assert officer.contract_raw == "Permanent"
    assert officer.salary_raw == "£43,297.57 - £50,562.57 per annum inc LA"
    assert officer.source_url == "https://vacancies.soas.ac.uk/job/934414"


def test_postingpanda_is_detected_from_its_asset_cdn(html_fixture: Any) -> None:
    html = html_fixture("postingpanda/soas-2026-09-04.html")
    probe_result = ProbeResult(url=_SOAS_URL, status_code=200, html=html, final_url=_SOAS_URL)

    adapter_class = detect_adapter(ref(_SOAS_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.POSTINGPANDA


def test_a_page_with_no_postingpanda_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert PostingPandaAdapter.detect(ref(), probe_result) is False
