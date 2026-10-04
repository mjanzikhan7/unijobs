"""A withdrawn job stays withdrawn, whatever the crawl finds.

Written before the code, per the working agreement for ``crawler/``.

The rule this protects is narrow and easy to break by accident. ``_upsert_job`` sets
``status = OPEN`` unconditionally, and the differ routes any stored job whose status is not
``OPEN`` into ``updated`` - so before this change, an administrator closing a still-listed job
would have had it silently reopened by the next successful crawl.

``WITHDRAWN`` is deliberately a different word from ``DISAPPEARED``. ``DISAPPEARED`` means, and
only means, "absent from a crawl whose outcome was OK" - domain rule 1. An administrator
withdrawing a job is a different event, so the closure gate is not weakened; it is not consulted.
"""

from __future__ import annotations

import pytest

from crawler.differ import ExistingJob, diff_vacancies, vacancy_content_hash
from crawler.enums import CrawlOutcome
from crawler.types import RawVacancy


def _vacancy(url: str = "https://jobs.test.ac.uk/1", title: str = "Lecturer") -> RawVacancy:
    return RawVacancy(institution_slug="university-of-test", source_url=url, title=title)


def _stored(vacancy: RawVacancy, *, status: str, is_withdrawn: bool = False) -> ExistingJob:
    return ExistingJob(
        job_id=1,
        source_url=vacancy.source_url,
        content_hash=vacancy_content_hash(vacancy),
        status=status,
        is_withdrawn=is_withdrawn,
    )


def test_a_withdrawn_job_still_listed_is_not_reopened() -> None:
    """The regression this exists for: an admin decision undone by the next crawl."""
    vacancy = _vacancy()
    stored = _stored(vacancy, status="WITHDRAWN", is_withdrawn=True)

    result = diff_vacancies(fetched=[vacancy], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.updated == ()
    assert result.unchanged == ((vacancy, stored),)


def test_a_withdrawn_job_whose_advert_changed_is_still_not_reopened() -> None:
    """A changed content hash is the tempting case - it looks like a real update."""
    vacancy = _vacancy()
    stored = ExistingJob(
        job_id=1,
        source_url=vacancy.source_url,
        content_hash="something-else-entirely",
        status="WITHDRAWN",
        is_withdrawn=True,
    )

    result = diff_vacancies(fetched=[vacancy], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.updated == ()


def test_a_disappeared_job_that_comes_back_is_reopened() -> None:
    """The behaviour that must *not* change: reappearing is a real update."""
    vacancy = _vacancy()
    stored = _stored(vacancy, status="DISAPPEARED")

    result = diff_vacancies(fetched=[vacancy], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.updated == ((vacancy, stored),)


def test_an_open_job_with_a_changed_advert_is_updated() -> None:
    vacancy = _vacancy()
    stored = ExistingJob(
        job_id=1, source_url=vacancy.source_url, content_hash="stale", status="OPEN"
    )

    result = diff_vacancies(fetched=[vacancy], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.updated == ((vacancy, stored),)


def test_a_withdrawn_job_absent_from_the_crawl_is_not_closed_again() -> None:
    """Already closed by a person; closing it again would rewrite who did it and when."""
    stored = ExistingJob(
        job_id=1,
        source_url="https://jobs.test.ac.uk/1",
        content_hash="x",
        status="WITHDRAWN",
        is_withdrawn=True,
    )

    result = diff_vacancies(fetched=[], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.disappeared == ()


def test_an_open_job_absent_from_an_ok_crawl_still_disappears() -> None:
    """Domain rule 1 in its ordinary form - this must keep working."""
    stored = ExistingJob(
        job_id=1, source_url="https://jobs.test.ac.uk/1", content_hash="x", status="OPEN"
    )

    result = diff_vacancies(fetched=[], existing=[stored], outcome=CrawlOutcome.OK)

    assert result.disappeared == (stored,)


@pytest.mark.parametrize("outcome", list(CrawlOutcome))
@pytest.mark.parametrize("present", [True, False], ids=["listed", "absent"])
@pytest.mark.parametrize("status", ["OPEN", "WITHDRAWN", "DISAPPEARED"])
def test_a_withdrawn_job_is_never_reopened_or_reclosed(
    outcome: CrawlOutcome, present: bool, status: str
) -> None:
    """Whatever the outcome, and whether or not it is still listed.

    Table-driven because the interesting failures are at combinations nobody thinks to write out
    by hand - a withdrawn job on a ZERO_RESULTS crawl, say.
    """
    vacancy = _vacancy()
    stored = _stored(vacancy, status=status, is_withdrawn=status == "WITHDRAWN")

    result = diff_vacancies(
        fetched=[vacancy] if present else [], existing=[stored], outcome=outcome
    )

    if status != "WITHDRAWN":
        return

    assert stored not in [existing for _, existing in result.updated]
    assert stored not in result.disappeared
