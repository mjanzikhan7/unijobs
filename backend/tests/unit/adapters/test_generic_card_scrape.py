"""Generic card scrape adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from crawler.adapters.generic_card_scrape import GenericCardScrapeAdapter
from crawler.browser import FixtureBrowserSession
from crawler.exceptions import Blocked
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import FetchResponse, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_QMUL_URL = "https://www.qmul.ac.uk/jobs/vacancies/"
_RGU_URL = "https://www.rgu.ac.uk/jobs/current-vacancies"
_SMUCB_URL = "https://webapps.smucb.ac.uk/employment/default.asp"


def qmul(html_fixture: Any) -> GenericCardScrapeAdapter:
    return GenericCardScrapeAdapter(
        http=FixtureHttpClient(
            responses={
                _QMUL_URL: response(
                    html_fixture("generic_card_scrape/qmul-vacancies-2026-08-26.html"), _QMUL_URL
                )
            }
        )
    )


def test_generic_card_scrape_reads_every_qmul_card(html_fixture: Any) -> None:
    """Real QMUL case: ~50 cards in one plain grid, no pagination control at all."""
    adapter = qmul(html_fixture)

    vacancies = adapter.list_vacancies(ref(_QMUL_URL))

    assert len(vacancies) == 50


def test_generic_card_scrape_reads_qmuls_data_attributes_and_labelled_paragraph(
    html_fixture: Any,
) -> None:
    adapter = qmul(html_fixture)

    vacancies = adapter.list_vacancies(ref(_QMUL_URL))

    reader = next(v for v in vacancies if v.reference == "10750")
    assert reader.title == "Reader in Law (Teaching & Research)"
    assert reader.department == "School of Law"
    assert reader.category == "Academic"
    assert reader.contract_raw == "Permanent"
    assert reader.salary_raw == "£64,331 - £71,834 per annum"
    assert reader.closing_date == date(2026, 8, 26)
    assert reader.source_url == (
        "https://qmul-jobs.tal.net/vx/mobile-0/appcentre-ext/brand-4/candidate/so/pm/1/pl/3/"
        "opp/10750-Reader-in-Law-Teaching-Research/en-GB"
    )


def test_generic_card_scrape_reports_a_block_even_when_a_browser_is_available() -> None:
    """A site that blocks our honest User-Agent is reported as blocked, never worked around."""

    class _BlockedHttpClient:
        def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
            raise Blocked(f"{url} returned 403", url=url)

    browser = FixtureBrowserSession(responses={})
    adapter = GenericCardScrapeAdapter(http=_BlockedHttpClient(), browser=browser)

    with pytest.raises(Blocked):
        adapter.list_vacancies(ref(_QMUL_URL))
    assert browser.rendered == []


def test_generic_card_scrape_raises_when_qmul_blocks_with_no_browser_configured() -> None:
    class _BlockedHttpClient:
        def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
            raise Blocked(f"{url} returned 403", url=url)

    adapter = GenericCardScrapeAdapter(http=_BlockedHttpClient())

    with pytest.raises(Blocked):
        adapter.list_vacancies(ref(_QMUL_URL))


def test_generic_card_scrape_is_detected_from_the_qmul_host() -> None:
    probe_result = ProbeResult(
        url=_QMUL_URL, status_code=200, html="<p>Working here</p>", final_url=_QMUL_URL
    )

    adapter_class = detect_adapter(ref(_QMUL_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.GENERIC_CARD_SCRAPE


def rgu(html_fixture: Any) -> GenericCardScrapeAdapter:
    return GenericCardScrapeAdapter(
        http=FixtureHttpClient(
            responses={
                _RGU_URL: response(
                    html_fixture("generic_card_scrape/rgu-vacancies-2026-08-26.html"), _RGU_URL
                )
            }
        )
    )


def test_generic_card_scrape_reads_every_rgu_card(html_fixture: Any) -> None:
    """Real RGU case: 4 cards, confirmed live."""
    adapter = rgu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RGU_URL))

    assert len(vacancies) == 4


def test_generic_card_scrape_reads_rgus_labelled_fields_and_derives_a_reference_from_the_url(
    html_fixture: Any,
) -> None:
    """RGU publishes no department, category or reference on the card at all."""
    adapter = rgu(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RGU_URL))

    dean = next(v for v in vacancies if "Associate Dean" in v.title)
    assert dean.salary_raw == "£69,488- £71,566"
    assert dean.closing_date == date(2026, 8, 30)
    assert dean.reference == "484416"
    assert dean.department == ""
    assert dean.category == ""
    assert dean.source_url == (
        "https://myjobscotland.gov.uk/education/rgu/jobs/associate-dean-research-484416"
    )


def test_generic_card_scrape_is_detected_from_the_rgu_host() -> None:
    probe_result = ProbeResult(
        url=_RGU_URL, status_code=200, html="<p>Working here</p>", final_url=_RGU_URL
    )

    adapter_class = detect_adapter(ref(_RGU_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.GENERIC_CARD_SCRAPE


def smucb(html_fixture: Any) -> GenericCardScrapeAdapter:
    return GenericCardScrapeAdapter(
        http=FixtureHttpClient(
            responses={
                _SMUCB_URL: response(
                    html_fixture("generic_card_scrape/st-marys-belfast-vacancies-2026-08-26.html"),
                    _SMUCB_URL,
                )
            }
        )
    )


def test_generic_card_scrape_reads_the_one_free_text_vacancy_at_st_marys_belfast(
    html_fixture: Any,
) -> None:
    """Real case: no card markup at all - a bold heading line, then plain prose."""
    adapter = smucb(html_fixture)

    vacancies = adapter.list_vacancies(ref(_SMUCB_URL))

    assert len(vacancies) == 1
    vacancy = vacancies[0]
    assert vacancy.title == "Technology and Design (Control Systems) Technician"
    assert vacancy.reference == "T-26-1"
    assert vacancy.closing_date == date(2026, 8, 27)
    assert vacancy.source_url == _SMUCB_URL


def test_generic_card_scrape_is_detected_from_the_st_marys_belfast_host() -> None:
    probe_result = ProbeResult(
        url=_SMUCB_URL, status_code=200, html="<p>Working here</p>", final_url=_SMUCB_URL
    )

    adapter_class = detect_adapter(ref(_SMUCB_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.GENERIC_CARD_SCRAPE


_RAU_URL = "https://www.rau.ac.uk/about-rau/work-for-us"


def rau(html_fixture: Any) -> GenericCardScrapeAdapter:
    return GenericCardScrapeAdapter(
        http=FixtureHttpClient(
            responses={
                _RAU_URL: response(
                    html_fixture("generic_card_scrape/rau-vacancies-2026-09-04.html"), _RAU_URL
                )
            }
        )
    )


def test_generic_card_scrape_reads_every_rau_table_row(html_fixture: Any) -> None:
    """Real case: 6 rows, no ``headers`` attribute to key cells by - read by position."""
    adapter = rau(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RAU_URL))

    assert len(vacancies) == 6


def test_generic_card_scrape_reads_rau_title_department_and_closing_date(
    html_fixture: Any,
) -> None:
    adapter = rau(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RAU_URL))

    chef = next(v for v in vacancies if v.title == "Commis Chef")
    assert chef.department == "Commercial Experience"
    assert chef.closing_date == date(2026, 9, 7)
    assert chef.source_url.endswith(".pdf")


def test_generic_card_scrape_rau_title_ignores_text_outside_the_link(html_fixture: Any) -> None:
    """One row's cell carries trailing prose after the link - the title is the link text only."""
    adapter = rau(html_fixture)

    vacancies = adapter.list_vacancies(ref(_RAU_URL))

    ambassador = next(v for v in vacancies if v.title.startswith("Student Ambassador"))
    assert ambassador.title == "Student Ambassador"


def test_generic_card_scrape_is_detected_from_the_rau_host() -> None:
    probe_result = ProbeResult(
        url=_RAU_URL, status_code=200, html="<p>Work for us</p>", final_url=_RAU_URL
    )

    adapter_class = detect_adapter(ref(_RAU_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.GENERIC_CARD_SCRAPE


def test_a_host_with_no_generic_card_scrape_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Working here</p>", final_url=CAREERS_URL
    )

    assert GenericCardScrapeAdapter.detect(ref(), probe_result) is False
