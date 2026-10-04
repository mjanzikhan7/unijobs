"""Tribepad adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.tribepad import TribepadAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_BPP_PAGE1_URL = "https://vacancies.bpp.com/jobs/search"
_BPP_PAGE2_URL = "https://vacancies.bpp.com/jobs/search/-1/2"


def bpp(html_fixture: Any) -> TribepadAdapter:
    """An adapter wired to BPP's real (redacted), plain-HTTP-fetched, two-page listing."""
    return TribepadAdapter(
        http=FixtureHttpClient(
            responses={
                _BPP_PAGE1_URL: response(
                    html_fixture("tribepad/bpp-page1-2026-09-04.html"), _BPP_PAGE1_URL
                ),
                _BPP_PAGE2_URL: response(
                    html_fixture("tribepad/bpp-page2-2026-09-04.html"), _BPP_PAGE2_URL
                ),
            }
        )
    )


def test_tribepad_reads_every_real_vacancy_across_both_pages(html_fixture: Any) -> None:
    """Real case: 10 cards on page 1, 6 on page 2, no "Next" link once page 2 is the last."""
    adapter = bpp(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BPP_PAGE1_URL))

    assert len(vacancies) == 16


def test_tribepad_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = bpp(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BPP_PAGE1_URL))

    admin = next(v for v in vacancies if v.title == "Customer Services Administrator")
    assert admin.reference == "1507"
    assert admin.salary_raw == "£26,000 - £28,000"
    assert "Abingdon" in admin.location_raw
    assert admin.contract_raw == "Permanent"
    assert admin.closing_date == date(2026, 9, 25)
    assert admin.posted_date == date(2026, 8, 28)
    assert admin.source_url == (
        "https://vacancies.bpp.com/jobs/job/Customer-Services-Administrator/1507"
    )


def test_tribepad_is_detected_from_its_footer_credit(html_fixture: Any) -> None:
    html = html_fixture("tribepad/bpp-page1-2026-09-04.html")
    probe_result = ProbeResult(
        url=_BPP_PAGE1_URL, status_code=200, html=html, final_url=_BPP_PAGE1_URL
    )

    adapter_class = detect_adapter(ref(_BPP_PAGE1_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.TRIBEPAD


def test_a_page_with_no_tribepad_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert TribepadAdapter.detect(ref(), probe_result) is False
