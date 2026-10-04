"""Jobtrain adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

from crawler.adapters.jobtrain import JobtrainAdapter
from crawler.browser import FixtureBrowserSession
from crawler.enums import ExtractionStrategy
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import CAREERS_URL, ref, response


def test_jobtrain_over_plain_http_finds_nothing(html_fixture: Any) -> None:
    """HTTP 200, full filter panel, "There are 0 jobs matching" - and no jobs.

    Returning an empty list here is correct and honest: the orchestrator turns it into
    ``ZERO_RESULTS``, which is not closure-safe, so nothing gets closed off it.
    """
    adapter = JobtrainAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("jobtrain/manchester-2026-08-23.html"))
        )
    )

    assert adapter.list_vacancies(ref()) == []


def test_jobtrain_finds_the_vacancies_once_rendered(html_fixture: Any) -> None:
    """The same portal, after the JavaScript that plain HTTP never runs."""
    adapter = JobtrainAdapter(
        http=FixtureHttpClient(
            responses={}, default=response(html_fixture("jobtrain/manchester-2026-08-23.html"))
        ),
        browser=FixtureBrowserSession(
            responses={
                CAREERS_URL: response(html_fixture("jobtrain/manchester-rendered-2026-08-23.html"))
            }
        ),
    )

    assert len(adapter.list_vacancies(ref())) == 12


def test_jobtrain_waits_for_the_results_container_not_for_quiet(html_fixture: Any) -> None:
    """The page polls, so it never goes idle; waiting for quiet either hangs or returns early."""
    browser = FixtureBrowserSession(
        responses={
            CAREERS_URL: response(html_fixture("jobtrain/manchester-rendered-2026-08-23.html"))
        }
    )
    adapter = JobtrainAdapter(http=FixtureHttpClient(responses={}), browser=browser)

    adapter.list_vacancies(ref())

    assert browser.rendered == [CAREERS_URL]


def test_jobtrain_records_that_it_used_a_browser(html_fixture: Any) -> None:
    adapter = JobtrainAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(
            responses={
                CAREERS_URL: response(html_fixture("jobtrain/manchester-rendered-2026-08-23.html"))
            }
        ),
    )

    adapter.list_vacancies(ref())

    assert adapter.strategy is ExtractionStrategy.BROWSER_HTML


def test_jobtrain_reads_the_salary_off_a_result_card(html_fixture: Any) -> None:
    adapter = JobtrainAdapter(
        http=FixtureHttpClient(responses={}),
        browser=FixtureBrowserSession(
            responses={
                CAREERS_URL: response(html_fixture("jobtrain/manchester-rendered-2026-08-23.html"))
            }
        ),
    )

    vacancies = adapter.list_vacancies(ref())

    assert all(item.salary_raw for item in vacancies)
