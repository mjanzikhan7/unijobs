"""Keeping worker processes healthy around browser crawls.

Playwright's sync API runs an asyncio event loop. Under Celery's prefork pool, if that loop
outlives its crawl, every later database call in that process fails with
``SynchronousOnlyOperation``, including the task that recovers stuck runs.

These tests make that failure survivable: it is visible when it happens, and it cannot break a
worker for ever.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from django.conf import settings
from django.test import override_settings

from crawler.browser import BrowserUnavailable, PlaywrightSession
from crawler.services import build_browser_session


class _ExplodingOnStop:
    """A Playwright handle whose teardown fails, the way a wedged browser's does."""

    def stop(self) -> None:
        """Fail, loudly enough that the caller has to decide what to do about it."""
        raise RuntimeError("playwright refused to stop")


class _Capture(logging.Handler):
    """Collect records straight from the logger.

    The ``crawler`` logger does not propagate, so ``caplog`` on the root logger would not see them.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Keep the record."""
        self.records.append(record)


def test_browser_teardown_failure_is_logged_loudly() -> None:
    """A teardown failure must not be hidden at DEBUG.

    This log line is how a broken worker is found. At DEBUG it would be invisible in production.
    """
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session._playwright = _ExplodingOnStop()
    handler = _Capture()
    logger = logging.getLogger("crawler.browser")
    logger.addHandler(handler)

    try:
        session.stop()
    finally:
        logger.removeHandler(handler)

    assert [record for record in handler.records if record.levelno >= logging.WARNING]


def test_teardown_failure_still_clears_the_handles() -> None:
    """A failed stop must not leave the session looking usable."""
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    session._playwright = _ExplodingOnStop()

    session.stop()

    assert session._playwright is None


def test_worker_processes_are_recycled() -> None:
    """Limits the damage of a broken worker process.

    Without a limit, one browser crawl that leaks its event loop would break every later task in
    that process until someone restarts the worker.
    """
    assert settings.CELERY_WORKER_MAX_TASKS_PER_CHILD > 0


class _FakeChromium:
    """Stands in for `playwright.chromium`, whose `launch()` fails."""

    def launch(self, headless: bool) -> None:
        """Fail the way a missing browser executable does."""
        raise RuntimeError(
            "BrowserType.launch: Executable doesn't exist at "
            "/root/.cache/ms-playwright/chromium_headless_shell-1148/chrome-linux/headless_shell"
        )


class _FakeDriver:
    """Stands in for the object `sync_playwright().start()` returns."""

    def __init__(self) -> None:
        self.chromium = _FakeChromium()
        self.stopped = False

    def stop(self) -> None:
        """Record that cleanup ran, so a test can prove it was not skipped."""
        self.stopped = True


class _FakeContextManager:
    """Stands in for what `sync_playwright()` itself returns."""

    def __init__(self, driver: _FakeDriver) -> None:
        self._driver = driver

    def start(self) -> _FakeDriver:
        """Return the fake driver, as the real context manager returns the real one."""
        return self._driver


def _patch_launch_failure(monkeypatch: pytest.MonkeyPatch, driver: _FakeDriver) -> None:
    """Make `sync_playwright()` return a driver whose Chromium launch fails.

    Patched in `playwright.sync_api`, because `PlaywrightSession.start()` imports it inside the
    function on every call.
    """
    import playwright.sync_api

    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: _FakeContextManager(driver))


def test_a_launch_failure_is_reported_as_browser_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The crawler only knows how to handle `BrowserUnavailable`.

    This really happened: Chromium was missing from the worker image, `chromium.launch()` raised a
    plain `Error`, and it crashed the Celery task and broke the worker for later tasks.
    """
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    _patch_launch_failure(monkeypatch, _FakeDriver())

    with pytest.raises(BrowserUnavailable):
        session.start()


def test_a_launch_failure_still_stops_the_driver_that_did_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`sync_playwright().start()` works, then `chromium.launch()` fails.

    The half-started driver must be closed, or it outlives the task and breaks the next one.
    """
    session = PlaywrightSession(user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)")
    driver = _FakeDriver()
    _patch_launch_failure(monkeypatch, driver)

    with pytest.raises(BrowserUnavailable):
        session.start()

    assert driver.stopped is True


@override_settings(CRAWLER={**settings.CRAWLER, "PLAYWRIGHT_ENABLED": True})
def test_build_browser_session_degrades_to_none_rather_than_crashing_the_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The path a Celery task really calls.

    Playwright is turned on here, because test settings turn it off, and then
    ``build_browser_session()`` would return ``None`` before reaching the code under test.
    """
    _patch_launch_failure(monkeypatch, _FakeDriver())

    result = build_browser_session()

    assert result is None


@pytest.mark.django_db
def test_jobs_left_unscreened_by_a_stopped_run_are_screened_later(ruleset: Any) -> None:
    """A run that stops early must not leave jobs hidden from search for ever."""
    from crawler.tasks import screen_unscreened_jobs
    from jobs.models import Job
    from tests.factories import JobFactory

    JobFactory()
    JobFactory()

    result = screen_unscreened_jobs()

    assert result["screened"] == 2
    assert not Job.objects.filter(screening__isnull=True).exists()


@pytest.mark.django_db
def test_screening_unscreened_jobs_does_nothing_when_all_are_screened() -> None:
    from crawler.tasks import screen_unscreened_jobs

    assert screen_unscreened_jobs() == {"screened": 0, "changed": 0}
