"""University of Dundee adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.dundee_vacancy_cards import DundeeVacancyCardsAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_DUNDEE_URL = "https://www.dundee.ac.uk/work-for-us/jobs?search_api_fulltext="


def dundee(html_fixture: Any) -> DundeeVacancyCardsAdapter:
    """An adapter wired to Dundee's real (redacted), plain-HTTP-fetched listing page."""
    return DundeeVacancyCardsAdapter(
        http=FixtureHttpClient(
            responses={
                _DUNDEE_URL: response(
                    html_fixture("dundee_vacancy_cards/dundee-2026-09-04.html"), _DUNDEE_URL
                )
            }
        )
    )


def test_dundee_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Real case: 12 cards, one page, no pagination control observed anywhere."""
    adapter = dundee(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DUNDEE_URL))

    assert len(vacancies) == 12


def test_dundee_reads_the_real_fields(html_fixture: Any) -> None:
    adapter = dundee(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DUNDEE_URL))

    postdoc = next(v for v in vacancies if v.reference == "UOD2357")
    assert postdoc.title == "Postdoctoral Researcher - UOD2357"
    assert postdoc.salary_raw == "£37,694 - £46,049 per annum"
    assert "Faculty of Life Sciences" in postdoc.location_raw
    assert "MRC PPU" in postdoc.location_raw
    assert postdoc.closing_date == date(2026, 9, 11)
    assert postdoc.source_url == "https://www.dundee.ac.uk/work-for-us/jobs/uod2357"


def test_dundee_reads_a_negotiable_salary_as_published(html_fixture: Any) -> None:
    """One real card publishes "Negotiable" instead of a figure - read as-is, not blanked."""
    adapter = dundee(html_fixture)

    vacancies = adapter.list_vacancies(ref(_DUNDEE_URL))

    negotiable = next(v for v in vacancies if v.salary_raw == "Negotiable")
    assert "Cell Signalling and Immunology" in negotiable.location_raw


def test_dundee_is_detected_from_the_drupal_card_class(html_fixture: Any) -> None:
    html = html_fixture("dundee_vacancy_cards/dundee-2026-09-04.html")
    probe_result = ProbeResult(url=_DUNDEE_URL, status_code=200, html=html, final_url=_DUNDEE_URL)

    adapter_class = detect_adapter(ref(_DUNDEE_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.DUNDEE_VACANCY_CARDS


def test_a_page_with_no_dundee_card_signature_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert DundeeVacancyCardsAdapter.detect(ref(), probe_result) is False
