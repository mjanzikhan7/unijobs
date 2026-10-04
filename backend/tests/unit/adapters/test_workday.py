"""Workday adapter tests, against cached fixtures."""

from __future__ import annotations

from typing import Any

import pytest

from crawler.adapters.workday import WorkdayAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import ref, response


@pytest.mark.parametrize(
    ("careers_url", "expected"),
    [
        (
            "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs",
            "https://lse.wd3.myworkdayjobs.com/wday/cxs/lse/LSEJobs/jobs",
        ),
        (
            "https://kcl.wd3.myworkdayjobs.com/KCLJobs",
            "https://kcl.wd3.myworkdayjobs.com/wday/cxs/kcl/KCLJobs/jobs",
        ),
    ],
)
def test_workday_derives_its_json_endpoint_from_the_ui_url(careers_url: str, expected: str) -> None:
    assert WorkdayAdapter.api_url(careers_url) == expected


def test_workday_reads_the_json_api(html_fixture: Any) -> None:
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("workday/lse-jobs.json"), content_type="application/json"
            ),
        )
    )

    vacancies = adapter.list_vacancies(ref(url))

    assert len(vacancies) >= 20


def test_workday_records_the_json_api_strategy(html_fixture: Any) -> None:
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("workday/lse-jobs.json"), content_type="application/json"
            ),
        )
    )

    adapter.list_vacancies(ref(url))

    assert adapter.strategy is ExtractionStrategy.JSON_API


def test_workday_builds_absolute_vacancy_urls(html_fixture: Any) -> None:
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("workday/lse-jobs.json"), content_type="application/json"
            ),
        )
    )

    vacancies = adapter.list_vacancies(ref(url))

    assert all(
        item.source_url.startswith("https://lse.wd3.myworkdayjobs.com/") for item in vacancies
    )


def test_workday_keeps_a_relative_posted_phrase_out_of_the_date_field(
    html_fixture: Any,
) -> None:
    """A phrase like "Posted 3 Days Ago" is not a date; inventing one would mislead a human."""
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("workday/lse-jobs.json"), content_type="application/json"
            ),
        )
    )

    vacancies = adapter.list_vacancies(ref(url))

    assert vacancies[0].posted_date is None


def test_workday_preserves_the_relative_phrase_as_context(html_fixture: Any) -> None:
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(
                html_fixture("workday/lse-jobs.json"), content_type="application/json"
            ),
        )
    )

    vacancies = adapter.list_vacancies(ref(url))

    assert vacancies[0].extra["posted_raw"] == "Posted 3 Days Ago"


def test_workday_raises_when_the_endpoint_stops_returning_json() -> None:
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    adapter = WorkdayAdapter(
        http=FixtureHttpClient(responses={}, default=response("<html>Signed out</html>"))
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(url))


def test_workday_rejects_a_url_it_cannot_turn_into_an_endpoint() -> None:
    with pytest.raises(ParseError):
        WorkdayAdapter.api_url("https://myworkdayjobs.com/")
