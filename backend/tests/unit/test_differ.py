"""The differ, and the closure safety rule.

If only one test in this project were kept, it would be
:func:`test_no_job_is_closed_on_a_non_ok_outcome`. A university portal went down for scheduled
maintenance across a weekend; a differ that trusted the empty response would have closed every
one of its vacancies.
"""

from __future__ import annotations

from datetime import date

import pytest

from crawler.differ import (
    ExistingJob,
    deduplicate,
    diff_vacancies,
    field_changes,
    vacancy_content_hash,
)
from crawler.enums import CrawlOutcome
from crawler.types import RawVacancy

NON_OK_OUTCOMES = [
    CrawlOutcome.ZERO_RESULTS,
    CrawlOutcome.BLOCKED,
    CrawlOutcome.OFFLINE,
    CrawlOutcome.TIMEOUT,
    CrawlOutcome.ROBOTS_DISALLOWED,
    CrawlOutcome.PARSE_ERROR,
    CrawlOutcome.NO_ADAPTER,
    CrawlOutcome.SKIPPED,
]


def vacancy(url: str = "https://jobs.test.ac.uk/1", **overrides: object) -> RawVacancy:
    """Build a vacancy with sensible defaults."""
    defaults: dict[str, object] = {
        "source_url": url,
        "title": "Research Software Engineer",
        "institution_slug": "university-of-test",
        "salary_raw": "£38,784 to £46,049 per annum",
        "closing_date": date(2026, 9, 30),
    }
    defaults.update(overrides)
    return RawVacancy(**defaults)  # type: ignore[arg-type]


def stored(url: str, **overrides: object) -> ExistingJob:
    """Build a stored job whose hash matches :func:`vacancy` unless told otherwise."""
    matching = vacancy(url, **{k: v for k, v in overrides.items() if k in {"salary_raw", "title"}})
    defaults: dict[str, object] = {
        "job_id": abs(hash(url)) % 100000,
        "source_url": url,
        "content_hash": vacancy_content_hash(matching),
        "status": "OPEN",
        "title": matching.title,
        "salary_raw": matching.salary_raw,
        "closing_date": matching.closing_date,
        "location_raw": "",
        "is_manual": False,
    }
    defaults.update({k: v for k, v in overrides.items() if k in ExistingJob.__slots__})
    return ExistingJob(**defaults)  # type: ignore[arg-type]


@pytest.mark.parametrize("outcome", NON_OK_OUTCOMES)
def test_no_job_is_closed_on_a_non_ok_outcome(outcome: CrawlOutcome) -> None:
    """The most consequential assertion in the suite."""
    existing = [stored("https://jobs.test.ac.uk/1"), stored("https://jobs.test.ac.uk/2")]

    result = diff_vacancies(fetched=[], existing=existing, outcome=outcome)

    assert result.disappeared == ()


@pytest.mark.parametrize("outcome", NON_OK_OUTCOMES)
def test_a_non_ok_outcome_records_why_nothing_was_closed(outcome: CrawlOutcome) -> None:
    """Silence about a decision this important is its own failure mode."""
    existing = [stored("https://jobs.test.ac.uk/1")]

    result = diff_vacancies(fetched=[], existing=existing, outcome=outcome)

    assert outcome.value in result.closure_skipped_reason


def test_zero_results_is_not_treated_as_an_empty_estate() -> None:
    """40 vacancies yesterday and none today is breakage, not news."""
    existing = [stored(f"https://jobs.test.ac.uk/{index}") for index in range(40)]

    result = diff_vacancies(fetched=[], existing=existing, outcome=CrawlOutcome.ZERO_RESULTS)

    assert len(result.disappeared) == 0


def test_a_successful_crawl_does_close_what_is_genuinely_gone() -> None:
    """The rule protects against false closure, not against closure."""
    existing = [stored("https://jobs.test.ac.uk/1"), stored("https://jobs.test.ac.uk/2")]

    result = diff_vacancies(
        fetched=[vacancy("https://jobs.test.ac.uk/1")],
        existing=existing,
        outcome=CrawlOutcome.OK,
    )

    assert [job.source_url for job in result.disappeared] == ["https://jobs.test.ac.uk/2"]


def test_a_job_already_marked_disappeared_is_not_closed_again() -> None:
    existing = [stored("https://jobs.test.ac.uk/2", status="DISAPPEARED")]

    result = diff_vacancies(fetched=[], existing=existing, outcome=CrawlOutcome.OK)

    assert result.disappeared == ()


def test_a_disappeared_job_that_reappears_is_reopened_even_with_unchanged_content() -> None:
    """A closure can be wrong - a transient adapter miss, a paging bug - not just right.

    Routing a reappearance through ``unchanged`` would leave ``status`` frozen at
    ``DISAPPEARED`` forever: :func:`crawler.sync.apply_diff` only ever resets ``status``
    on the ``new``/``updated`` paths. The advert's own content has not changed, but the job
    coming back at all is itself the change that matters here.
    """
    url = "https://jobs.test.ac.uk/2"
    existing = [stored(url, status="DISAPPEARED")]

    result = diff_vacancies(fetched=[vacancy(url)], existing=existing, outcome=CrawlOutcome.OK)

    assert result.counts == {"new": 0, "updated": 1, "unchanged": 0, "disappeared": 0}


def test_a_manually_added_job_is_never_closed_by_diffing() -> None:
    """It was never in the crawl's universe, so its absence says nothing."""
    existing = [
        stored("https://nhs.jobs/1", is_manual=True),
        stored("https://jobs.test.ac.uk/2"),
    ]

    result = diff_vacancies(fetched=[], existing=existing, outcome=CrawlOutcome.OK)

    assert [job.source_url for job in result.disappeared] == ["https://jobs.test.ac.uk/2"]


def test_unchanged_content_produces_no_updates() -> None:
    """Crawling twice must be free of writes the second time."""
    fetched = [vacancy("https://jobs.test.ac.uk/1")]
    existing = [stored("https://jobs.test.ac.uk/1")]

    result = diff_vacancies(fetched=fetched, existing=existing, outcome=CrawlOutcome.OK)

    assert result.counts == {"new": 0, "updated": 0, "unchanged": 1, "disappeared": 0}


def test_a_changed_salary_is_an_update() -> None:
    fetched = [vacancy("https://jobs.test.ac.uk/1", salary_raw="£40,000 to £48,000 per annum")]
    existing = [stored("https://jobs.test.ac.uk/1")]

    result = diff_vacancies(fetched=fetched, existing=existing, outcome=CrawlOutcome.OK)

    assert result.counts["updated"] == 1


def test_an_unseen_url_is_new() -> None:
    result = diff_vacancies(
        fetched=[vacancy("https://jobs.test.ac.uk/9")], existing=[], outcome=CrawlOutcome.OK
    )

    assert result.counts["new"] == 1


def test_the_content_hash_ignores_description_reflow() -> None:
    """Universities re-flow advert HTML constantly without changing a word that matters."""
    first = vacancy(description_html="<p>Hello</p>", description_text="Hello")
    second = vacancy(description_html="<div><p>Hello</p></div>", description_text="Hello ")

    assert vacancy_content_hash(first) == vacancy_content_hash(second)


def test_the_content_hash_notices_a_closing_date_change() -> None:
    first = vacancy(closing_date=date(2026, 9, 30))
    second = vacancy(closing_date=date(2026, 10, 14))

    assert vacancy_content_hash(first) != vacancy_content_hash(second)


def test_the_content_hash_notices_a_category_change() -> None:
    first = vacancy(category="Academic")
    second = vacancy(category="Research")

    assert vacancy_content_hash(first) != vacancy_content_hash(second)


def test_a_salary_change_produces_a_revision_with_both_values() -> None:
    """Before and after side by side is what the Changed tab shows."""
    changes = field_changes(
        vacancy("https://jobs.test.ac.uk/1", salary_raw="£40,000 per annum"),
        stored("https://jobs.test.ac.uk/1"),
    )
    salary_change = next(change for change in changes if change.field == "salary_raw")

    assert (salary_change.before, salary_change.after) == (
        "£38,784 to £46,049 per annum",
        "£40,000 per annum",
    )


def test_no_change_produces_no_revisions() -> None:
    changes = field_changes(
        vacancy("https://jobs.test.ac.uk/1"), stored("https://jobs.test.ac.uk/1")
    )

    assert changes == []


def test_whitespace_only_differences_are_not_changes() -> None:
    changes = field_changes(
        vacancy("https://jobs.test.ac.uk/1", salary_raw=" £38,784 to £46,049 per annum "),
        stored("https://jobs.test.ac.uk/1"),
    )

    assert changes == []


def test_a_vacancy_listed_under_two_departments_is_counted_once() -> None:
    """Stonefish lists a cross-faculty post once per department it appears under."""
    duplicates = [
        vacancy("https://jobs.test.ac.uk/1", department="Computer Science"),
        vacancy("https://jobs.test.ac.uk/1", department="Mathematics"),
        vacancy("https://jobs.test.ac.uk/2"),
    ]

    assert len(deduplicate(duplicates)) == 2


def test_deduplication_keeps_the_first_occurrence() -> None:
    duplicates = [
        vacancy("https://jobs.test.ac.uk/1", department="Computer Science"),
        vacancy("https://jobs.test.ac.uk/1", department="Mathematics"),
    ]

    assert deduplicate(duplicates)[0].department == "Computer Science"
