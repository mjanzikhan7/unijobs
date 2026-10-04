"""Browser rendering, for sites that load their vacancy list with JavaScript.

Jobtrain is the main reason. A plain fetch returns HTTP 200 with "There are 0 jobs matching",
which looks like a successful crawl of an empty list but is not.

The browser lifecycle lives here, not on the adapter interface, so HTTP-only adapters do not
need browser methods they never use.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from crawler.exceptions import Blocked, SiteOffline, Timeout
from crawler.types import FetchResponse

logger = logging.getLogger(__name__)

_CONSENT_REJECT_SELECTORS: tuple[str, ...] = (
    "#onetrust-reject-all-handler",
    "#CybotCookiebotDialogBodyButtonDecline",
    "#ccc-reject-settings",
    "#ccc-notify-reject",
)
_CONSENT_DISMISS_TIMEOUT_MS = 2_000

_PAGINATION_SETTLE_MS = 1_200


class BrowserUnavailable(RuntimeError):
    """Playwright is not installed or is disabled by configuration."""


@dataclass
class PlaywrightSession:
    """One Chromium context, reused for all pages of one institution.

    It sends the same honest User-Agent as the HTTP client and does not hide that it is automated.
    ``before_navigation`` runs before every page load and every pager click. The crawler passes
    the HTTP client's robots and delay check here.
    """

    user_agent: str
    timeout_ms: int = 30_000
    headless: bool = True
    before_navigation: Callable[[str], None] | None = None
    _playwright: Any = field(default=None, repr=False)
    _browser: Any = field(default=None, repr=False)
    _context: Any = field(default=None, repr=False)

    def start(self) -> None:
        """Start Chromium. Raises :class:`BrowserUnavailable` when it cannot.

        Covers a missing Playwright and a missing browser binary, so a failure does not crash the
        worker.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - exercised only without playwright
            raise BrowserUnavailable("playwright is not installed") from exc

        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._context = self._browser.new_context(
                user_agent=self.user_agent,
                locale="en-GB",
                viewport={"width": 1280, "height": 800},
            )
        except Exception as exc:
            self.stop()
            raise BrowserUnavailable(f"could not launch chromium: {exc}") from exc

    def stop(self) -> None:
        """Close everything, even if the session only half started.

        Failures are logged as WARNING, so a browser that did not close is easy to spot. The handles
        are cleared anyway, so a half-closed session never looks usable.
        """
        try:
            for closer in (self._context, self._browser):
                try:
                    if closer is not None:
                        closer.close()
                except Exception:
                    logger.warning("browser teardown error", exc_info=True)
            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:
                    logger.warning("playwright stop error", exc_info=True)
        finally:
            self._playwright = self._browser = self._context = None

    def __enter__(self) -> PlaywrightSession:
        """Start the browser on the way in."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the browser on the way out, even if the body raised."""
        self.stop()

    def _before(self, url: str) -> None:
        """Run the robots and delay check before the browser contacts ``url``."""
        if self.before_navigation is not None:
            self.before_navigation(url)

    def _dismiss_consent_banner(self, page: Any) -> None:
        """Reject cookies on a consent banner if one covers the page. Otherwise do nothing.

        A banner can block clicks on the element we need. We always choose "reject", never
        "accept". The timeout is short, so sites without a banner lose almost no time.
        """
        for selector in _CONSENT_REJECT_SELECTORS:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.click(timeout=_CONSENT_DISMISS_TIMEOUT_MS)
                    return
            except Exception:
                continue

    def render(self, url: str, *, wait_for_selector: str | None = None) -> FetchResponse:
        """Load ``url`` and return the page once the results are really there.

        Waits for a selector, not for ``networkidle``. Jobtrain's page keeps polling and never goes
        quiet.
        """
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        if self._context is None:
            raise BrowserUnavailable("PlaywrightSession.start() was not called")

        page = self._context.new_page()
        try:
            self._before(url)
            response = page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            if response is not None and response.status in (401, 403):
                raise Blocked(f"{url} returned {response.status}", url=url)
            self._dismiss_consent_banner(page)
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=self.timeout_ms)
            html = page.content()
            status = response.status if response is not None else 200
            return FetchResponse(
                url=page.url,
                status_code=status,
                text=html,
                headers={"content-type": "text/html"},
            )
        except PlaywrightTimeout as exc:
            raise Timeout(f"{url} did not render in time", url=url) from exc
        except PlaywrightError as exc:
            raise SiteOffline(f"{url} failed to render: {exc}", url=url) from exc
        finally:
            page.close()

    def render_after_click(
        self, url: str, *, click_selector: str, wait_for_selector: str | None = None
    ) -> FetchResponse:
        """Load ``url``, click ``click_selector`` when it appears, and return the page.

        For SuccessFactors: its result list only appears after the search is submitted.
        """
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        if self._context is None:
            raise BrowserUnavailable("PlaywrightSession.start() was not called")

        page = self._context.new_page()
        try:
            self._before(url)
            response = page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            if response is not None and response.status in (401, 403):
                raise Blocked(f"{url} returned {response.status}", url=url)
            self._dismiss_consent_banner(page)
            self._before(page.url)
            page.click(click_selector, timeout=self.timeout_ms)
            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=self.timeout_ms)
            html = page.content()
            status = response.status if response is not None else 200
            return FetchResponse(
                url=page.url,
                status_code=status,
                text=html,
                headers={"content-type": "text/html"},
            )
        except PlaywrightTimeout as exc:
            raise Timeout(f"{url} did not render in time", url=url) from exc
        except PlaywrightError as exc:
            raise SiteOffline(f"{url} failed to render: {exc}", url=url) from exc
        finally:
            page.close()

    def render_each_page(
        self,
        url: str,
        *,
        wait_for_selector: str,
        next_selector: str,
        max_pages: int = 20,
    ) -> list[FetchResponse]:
        """Load ``url`` and click ``next_selector`` until there is no next page, keeping every page.

        Built for eploy's pager. The scroll and pause before each click are for engage|ats, whose
        pager needs a moment between pages.
        """
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeout

        if self._context is None:
            raise BrowserUnavailable("PlaywrightSession.start() was not called")

        page = self._context.new_page()
        try:
            self._before(url)
            response = page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            if response is not None and response.status in (401, 403):
                raise Blocked(f"{url} returned {response.status}", url=url)
            self._dismiss_consent_banner(page)
            page.wait_for_selector(wait_for_selector, timeout=self.timeout_ms)

            pages = [
                FetchResponse(
                    url=page.url,
                    status_code=response.status if response is not None else 200,
                    text=page.content(),
                    headers={"content-type": "text/html"},
                )
            ]

            for _ in range(max_pages - 1):
                next_link = page.locator(next_selector).first
                if next_link.count() == 0:
                    break
                next_link.scroll_into_view_if_needed(timeout=self.timeout_ms)
                self._before(page.url)
                next_link.click(timeout=self.timeout_ms)
                page.wait_for_load_state("domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_timeout(_PAGINATION_SETTLE_MS)
                page.wait_for_selector(wait_for_selector, timeout=self.timeout_ms)
                pages.append(
                    FetchResponse(
                        url=page.url,
                        status_code=200,
                        text=page.content(),
                        headers={"content-type": "text/html"},
                    )
                )
            return pages
        except PlaywrightTimeout as exc:
            raise Timeout(f"{url} did not render in time", url=url) from exc
        except PlaywrightError as exc:
            raise SiteOffline(f"{url} failed to render: {exc}", url=url) from exc
        finally:
            page.close()


@dataclass
class FixtureBrowserSession:
    """Browser stand-in for tests: returns registered HTML, never launches Chromium."""

    responses: dict[str, FetchResponse]
    paginated_responses: dict[str, list[FetchResponse]] = field(default_factory=dict)
    rendered: list[str] = field(default_factory=list)
    clicked: list[tuple[str, str]] = field(default_factory=list)

    def render(self, url: str, *, wait_for_selector: str | None = None) -> FetchResponse:
        """Return the fixture registered for ``url``."""
        self.rendered.append(url)
        response = self.responses.get(url)
        if response is None:
            raise SiteOffline(f"No rendered fixture registered for {url}", url=url)
        return response

    def render_after_click(
        self, url: str, *, click_selector: str, wait_for_selector: str | None = None
    ) -> FetchResponse:
        """Return the fixture registered for ``url``, recording the click that was requested."""
        self.clicked.append((url, click_selector))
        return self.render(url, wait_for_selector=wait_for_selector)

    def render_each_page(
        self,
        url: str,
        *,
        wait_for_selector: str,
        next_selector: str,
        max_pages: int = 20,
    ) -> list[FetchResponse]:
        """Return every fixture registered for ``url`` in `paginated_responses`, in order."""
        self.rendered.append(url)
        pages = self.paginated_responses.get(url)
        if pages is None:
            raise SiteOffline(f"No paginated fixtures registered for {url}", url=url)
        return pages[:max_pages]
