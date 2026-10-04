"""What kind of browser :class:`PlaywrightSession` presents as.

Not "does Chromium launch" - that is covered in ``tests/integration/test_crawl_tasks.py``, which
uses the same fake-driver pattern for the failure paths. This is specifically the fingerprint:
the user agent, viewport and init script that decide whether a WAF's simplest heuristics see an
ordinary browser or an automated one.
"""

from __future__ import annotations

from typing import Any

import pytest

from crawler.browser import _CONSENT_REJECT_SELECTORS, PlaywrightSession

HONEST_UA = "HEJobsBot/1.0 (+mailto:test@example.ac.uk)"


class _FakeContext:
    """Records what it was asked to do, in place of a real Playwright ``BrowserContext``."""

    def __init__(self) -> None:
        self.init_scripts: list[str] = []

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)


class _FakeBrowser:
    """Stands in for `playwright.chromium.launch()`'s return value."""

    def __init__(self) -> None:
        self.context_kwargs: dict[str, Any] | None = None
        self.context = _FakeContext()

    def new_context(self, **kwargs: Any) -> _FakeContext:
        self.context_kwargs = kwargs
        return self.context


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser) -> None:
        self._browser = browser

    def launch(self, headless: bool) -> _FakeBrowser:
        return self._browser


class _FakeDriver:
    def __init__(self, browser: _FakeBrowser) -> None:
        self.chromium = _FakeChromium(browser)

    def stop(self) -> None:
        """Nothing to release for a fake driver."""


class _FakeContextManager:
    def __init__(self, driver: _FakeDriver) -> None:
        self._driver = driver

    def start(self) -> _FakeDriver:
        return self._driver


def _patch_playwright(monkeypatch: pytest.MonkeyPatch, browser: _FakeBrowser) -> None:
    """Patched at the source, the same way ``test_crawl_tasks.py`` does it.

    ``PlaywrightSession.start()`` imports ``sync_playwright`` locally on every call, so the
    module attribute is what has to change, not anything on ``crawler.browser``.
    """
    import playwright.sync_api

    driver = _FakeDriver(browser)
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: _FakeContextManager(driver))


def test_the_browser_sends_the_honest_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The browser says who we are, exactly like the plain HTTP client."""
    browser = _FakeBrowser()
    _patch_playwright(monkeypatch, browser)

    session = PlaywrightSession(user_agent=HONEST_UA)
    session.start()

    assert browser.context_kwargs is not None
    assert browser.context_kwargs["user_agent"] == HONEST_UA


def test_the_browser_does_not_hide_that_it_is_automated(monkeypatch: pytest.MonkeyPatch) -> None:
    """No script that hides ``navigator.webdriver`` or pretends to be a person."""
    browser = _FakeBrowser()
    _patch_playwright(monkeypatch, browser)

    session = PlaywrightSession(user_agent=HONEST_UA)
    session.start()

    assert browser.context.init_scripts == []


def test_cookie_banners_are_only_ever_rejected() -> None:
    """We read public pages, so we never accept tracking or advertising cookies."""
    assert _CONSENT_REJECT_SELECTORS
    assert not any("accept" in selector.lower() for selector in _CONSENT_REJECT_SELECTORS)
    assert not any("allowall" in selector.lower() for selector in _CONSENT_REJECT_SELECTORS)


def test_every_navigation_runs_the_robots_and_delay_check_first() -> None:
    """The browser asks the same guard as the HTTP client before it contacts a site."""
    seen: list[str] = []
    session = PlaywrightSession(user_agent=HONEST_UA, before_navigation=seen.append)

    session._before("https://jobs.test.ac.uk/vacancies")

    assert seen == ["https://jobs.test.ac.uk/vacancies"]
