"""The bug that made every browser crawl fail without a message.

While a Playwright session is open, the thread has a running asyncio event loop. Django then
refuses any database call with ``SynchronousOnlyOperation``. In production, the first query in
``crawl_institution`` failed before any vacancy was fetched, for every site that needed a
browser.

These tests use a real ``PlaywrightSession``, not a mock. A mock never leaks the event loop,
which is how the bug was missed before.
"""

from __future__ import annotations

import pytest

from crawler.browser import PlaywrightSession
from crawler.models import CrawlRunInstitution
from crawler.services import build_browser_session, crawl_institution, needs_browser
from institutions.enums import Platform
from institutions.models import Institution
from tests.factories import CrawlRunFactory, InstitutionFactory

pytestmark = pytest.mark.django_db


def test_a_running_playwright_session_blocks_synchronous_orm_calls() -> None:
    """The cause on its own, without the crawler.

    This is how Playwright's sync API works, not a bug in our code. The test shows the rule to the
    next person who changes the browser code.
    """
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session.start()
    try:
        with pytest.raises(Exception, match=r"SynchronousOnlyOperation|async context"):
            Institution.objects.count()
    finally:
        session.stop()


def test_closing_the_session_first_makes_orm_calls_safe_again() -> None:
    """The other half: once stopped, the thread is clean."""
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session.start()
    session.stop()

    Institution.objects.count()


def test_crawl_institution_writes_to_the_database_after_a_real_browser_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real case: an opened browser must not block the database write that follows.

    Runs a real Chromium session through ``crawl_institution``, the same path production uses,
    and checks that the result row is saved.
    """
    from tests.integration.test_crawl_orchestration import StubAdapter

    adapter = StubAdapter(vacancies=[])
    monkeypatch.setattr("crawler.crawl.resolve_adapter", lambda *args, **kwargs: adapter)

    from crawler.http import FixtureHttpClient
    from crawler.types import FetchResponse

    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(
            url="https://jobs.test.ac.uk/jobs",
            status_code=200,
            text="<html><body>Vacancies</body></html>",
            headers={"content-type": "text/html"},
        ),
    )

    run = CrawlRunFactory()
    institution = InstitutionFactory(careers_url="https://jobs.test.ac.uk/jobs")

    row = crawl_institution(run, institution, http=client, browser_factory=build_browser_session)

    assert CrawlRunInstitution.objects.filter(pk=row.pk).exists()


def test_needs_browser_is_shared_between_the_cli_and_the_celery_task() -> None:
    """One decision, in one place.

    The browser must be opened and closed per institution, because an open browser breaks the next
    database call. So the command line and the Celery task both use this one function.
    """
    jobtrain = InstitutionFactory(platform=Platform.JOBTRAIN.value)
    stonefish = InstitutionFactory(platform=Platform.STONEFISH.value)

    assert needs_browser(jobtrain) is True
    assert needs_browser(stonefish) is False
