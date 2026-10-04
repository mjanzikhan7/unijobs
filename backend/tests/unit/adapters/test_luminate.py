"""Luminate adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.luminate import LuminateAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_LEEDS_CONSERVATOIRE_URL = "https://jobs.luminate.ac.uk/v2/leedsconservatoirejobs"


def leeds_conservatoire(html_fixture: Any) -> LuminateAdapter:
    """An adapter wired to Leeds Conservatoire's real (redacted) listing page."""
    html = html_fixture("luminate/leeds-conservatoire-2026-09-04.html")
    return LuminateAdapter(
        http=FixtureHttpClient(
            responses={_LEEDS_CONSERVATOIRE_URL: response(html, _LEEDS_CONSERVATOIRE_URL)}
        )
    )


def test_luminate_reads_every_real_vacancy(html_fixture: Any) -> None:
    """Leeds Conservatoire, live: 3 cards, no pagination control, one plain fetch."""
    adapter = leeds_conservatoire(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LEEDS_CONSERVATOIRE_URL))

    assert len(vacancies) == 3


def test_luminate_reads_the_icon_labelled_fields(html_fixture: Any) -> None:
    """Fields are matched by their Font Awesome icon, not by position in the card."""
    adapter = leeds_conservatoire(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LEEDS_CONSERVATOIRE_URL))

    vocal = next(v for v in vacancies if "Classical Vocal Lecturer" in v.title)
    assert vocal.location_raw == "Leeds"
    assert vocal.salary_raw == (
        "Commencing at £35,694 with progression to £40,149 pro rata per annum"
    )
    assert vocal.category == "Teachers/Lecturers"
    assert vocal.contract_raw == "LC - Fractional - Permanent"
    assert vocal.closing_date == date(2026, 9, 10)
    assert vocal.reference == "LUM40582/2857"
    assert vocal.source_url == (
        "https://jobs.luminate.ac.uk/members/modules/job/detail.php?record=2857"
    )


def test_luminate_tags_every_vacancy_with_the_institution(html_fixture: Any) -> None:
    adapter = leeds_conservatoire(html_fixture)

    vacancies = adapter.list_vacancies(ref(_LEEDS_CONSERVATOIRE_URL))

    assert all(v.institution_slug == "university-of-test" for v in vacancies)


def test_luminate_is_detected_from_its_own_host(html_fixture: Any) -> None:
    html = html_fixture("luminate/leeds-conservatoire-2026-09-04.html")
    probe_result = ProbeResult(
        url=_LEEDS_CONSERVATOIRE_URL, status_code=200, html=html, final_url=_LEEDS_CONSERVATOIRE_URL
    )

    adapter_class = detect_adapter(ref(_LEEDS_CONSERVATOIRE_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.LUMINATE


def test_a_page_with_no_luminate_widget_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert LuminateAdapter.detect(ref(), probe_result) is False
