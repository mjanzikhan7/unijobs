"""Stonefish adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from crawler.adapters.stonefish import StonefishAdapter
from crawler.exceptions import SiteOffline
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import ref, response


def stonefish(html: str) -> StonefishAdapter:
    """A Stonefish adapter serving one fixture."""
    return StonefishAdapter(http=FixtureHttpClient(responses={}, default=response(html)))


def test_stonefish_extracts_every_vacancy(html_fixture: Any) -> None:
    """Bath advertises 40 posts across all departments."""
    adapter = stonefish(html_fixture("stonefish/bath-2026-08-23.html"))

    vacancies = adapter.list_vacancies(ref())

    assert len(vacancies) == 40


def test_stonefish_extracts_references(html_fixture: Any) -> None:
    adapter = stonefish(html_fixture("stonefish/bath-2026-08-23.html"))

    vacancies = adapter.list_vacancies(ref())

    assert all(item.reference.startswith("CC") for item in vacancies)


def test_stonefish_extracts_closing_dates(html_fixture: Any) -> None:
    adapter = stonefish(html_fixture("stonefish/bath-2026-08-23.html"))

    vacancies = adapter.list_vacancies(ref())

    assert all(item.closing_date is not None for item in vacancies)


def test_stonefish_keeps_the_salary_string_exactly_as_advertised(html_fixture: Any) -> None:
    """The raw string is what tells you where a wrong verdict came from."""
    adapter = stonefish(html_fixture("stonefish/bath-2026-08-23.html"))

    vacancies = adapter.list_vacancies(ref())

    assert "£38,784 to £46,049 per annum (pro-rata for part-time)" in {
        item.salary_raw for item in vacancies
    }


def test_stonefish_records_the_department_each_vacancy_sits_under(html_fixture: Any) -> None:
    adapter = stonefish(html_fixture("stonefish/bath-2026-08-23.html"))

    vacancies = adapter.list_vacancies(ref())

    assert all(item.department for item in vacancies)


@pytest.mark.parametrize(
    ("careers_url", "expected"),
    [
        (
            "https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx?cat=7",
            "https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx?cat=-1",
        ),
        (
            "https://www.bath.ac.uk/jobs/Vacancies/",
            "https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx?cat=-1",
        ),
        (
            "https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx",
            "https://www.bath.ac.uk/jobs/Vacancies/vacancies.aspx?cat=-1",
        ),
    ],
)
def test_stonefish_always_targets_the_all_categories_listing(
    careers_url: str, expected: str
) -> None:
    """A narrower category silently drops departments; the search form returns nothing at all."""
    assert StonefishAdapter.listing_url(careers_url) == expected


def test_stonefish_never_fetches_the_search_form(html_fixture: Any) -> None:
    """The search page's results come back through an ASP.NET postback we cannot trigger."""
    client = FixtureHttpClient(
        responses={}, default=response(html_fixture("stonefish/bath-2026-08-23.html"))
    )
    adapter = StonefishAdapter(http=client)

    adapter.list_vacancies(ref("https://www.bath.ac.uk/jobs/Vacancies/search.aspx"))

    assert all("search.aspx" not in url for url in client.requested)


def test_a_maintenance_page_is_reported_as_offline(html_fixture: Any) -> None:
    """Reading this as ZERO_RESULTS is how a weekend of downtime closes a university."""
    adapter = stonefish(html_fixture("stonefish/surrey-maintenance-2026-08-23.html"))

    with pytest.raises(SiteOffline):
        adapter.list_vacancies(ref())
