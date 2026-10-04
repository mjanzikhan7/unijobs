"""eploy adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.eploy import EployAdapter
from crawler.browser import FixtureBrowserSession
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import CAREERS_URL, ref, response


def test_eploy_falls_back_to_a_browser_when_http_returns_nothing(html_fixture: Any) -> None:
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cranfield-empty-2026-08-23.html"))
        ),
        browser=FixtureBrowserSession(
            responses={CAREERS_URL: response(html_fixture("eploy/cardiff-page2-2026-08-25.html"))}
        ),
    )

    assert len(adapter.list_vacancies(ref())) == 3


def test_eploy_records_that_the_fallback_fired(html_fixture: Any) -> None:
    """A silent fallback lets a two-second fetch become a thirty-second render unnoticed."""
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cranfield-empty-2026-08-23.html"))
        ),
        browser=FixtureBrowserSession(
            responses={CAREERS_URL: response(html_fixture("eploy/cardiff-page2-2026-08-25.html"))}
        ),
    )

    adapter.list_vacancies(ref())

    assert adapter.fallback_fired is True


def test_eploy_does_not_render_when_http_already_worked_and_there_is_one_page(
    html_fixture: Any,
) -> None:
    """Launching a browser costs seconds per institution; it is not done speculatively."""
    browser = FixtureBrowserSession(responses={})
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("eploy/cardiff-page2-2026-08-25.html")),
        ),
        browser=browser,
    )

    adapter.list_vacancies(ref())

    assert browser.rendered == []


def test_eploy_reports_no_fallback_when_http_worked_and_there_is_one_page(
    html_fixture: Any,
) -> None:
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("eploy/cardiff-page2-2026-08-25.html")),
        )
    )

    adapter.list_vacancies(ref())

    assert adapter.fallback_fired is False


def test_eploy_recognises_a_real_tenants_detail_link_shape(html_fixture: Any) -> None:
    """The regression: `436/some-slug.html` matched none of the originally-guessed markers.

    All five eploy institutions crawled through this adapter came back ``ZERO_RESULTS`` for
    exactly this reason - the listing page fetched fine and every row on it went unmatched.
    """
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cardiff-page2-2026-08-25.html"))
        )
    )

    vacancies = adapter.list_vacancies(ref())

    assert {v.source_url for v in vacancies} == {
        "https://jobs.test.ac.uk/609/research-assistant.html",
        "https://jobs.test.ac.uk/442/research-assistant.html",
        "https://jobs.test.ac.uk/436/deputy-law-clinic-manager-commercial-law-clinic-practitioner.html",
    }


def test_eploy_reads_the_real_labelled_fields(html_fixture: Any) -> None:
    """Salary and contract status come from a card's own label/content pairs, not a class name.

    The original `_labelled` looked for the needle in a CSS class or a `data-label` attribute.
    A real tenant's label is plain visible text next to its value - `_labelled` never matched
    anything on a live tenant until this was fixed either.
    """
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cardiff-page1-2026-08-25.html"))
        )
    )

    vacancies = adapter.list_vacancies(ref())

    lecturer = next(v for v in vacancies if v.title.startswith("Lecturer - Occupational"))
    assert "£41,064" in lecturer.salary_raw
    assert lecturer.contract_raw == "Full Time"


def test_eploy_pages_through_every_page_the_pager_has(html_fixture: Any) -> None:
    """The regression: a plain HTTP GET only ever sees page one of an ASP.NET postback pager.

    Cardiff's real listing advertises 30 vacancies across 3 pages; a fetch of page one alone
    found 12 of them. `render_each_page` is what a real "click Next" looks like when there is
    no URL a plain HTTP client could ask for instead.
    """
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cardiff-page1-2026-08-25.html"))
        ),
        browser=FixtureBrowserSession(
            responses={},
            paginated_responses={
                CAREERS_URL: [
                    response(html_fixture("eploy/cardiff-page1-2026-08-25.html")),
                    response(html_fixture("eploy/cardiff-page2-2026-08-25.html")),
                    response(html_fixture("eploy/cardiff-page3-2026-08-25.html")),
                ]
            },
        ),
    )

    vacancies = adapter.list_vacancies(ref())

    assert len(vacancies) == 9


def test_eploy_records_the_fallback_when_pagination_was_needed(html_fixture: Any) -> None:
    """HTTP alone found real vacancies here - but not all of them, which is still incomplete."""
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cardiff-page1-2026-08-25.html"))
        ),
        browser=FixtureBrowserSession(
            responses={},
            paginated_responses={
                CAREERS_URL: [
                    response(html_fixture("eploy/cardiff-page1-2026-08-25.html")),
                    response(html_fixture("eploy/cardiff-page2-2026-08-25.html")),
                ]
            },
        ),
    )

    adapter.list_vacancies(ref())

    assert adapter.fallback_fired is True


def test_eploy_does_not_paginate_without_a_browser(html_fixture: Any) -> None:
    """No browser configured at all - page one is still a genuine, honest answer, not a crash."""
    adapter = EployAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("eploy/cardiff-page1-2026-08-25.html"))
        )
    )

    vacancies = adapter.list_vacancies(ref())

    assert len(vacancies) == 3
    assert adapter.fallback_fired is False
