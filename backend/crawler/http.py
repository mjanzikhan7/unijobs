"""The polite HTTP client that every adapter uses.

The tool visits about 170 universities several times a day from one IP address, so politeness
matters. This file follows robots.txt, makes one request per host at a time with at least two
seconds between them, respects ``Retry-After``, uses conditional requests so an unchanged page
costs a 304, and sends a User-Agent with a real contact address.

Adapters use the :class:`~crawler.types.HttpClient` protocol, not this class. Tests use
:class:`FixtureHttpClient`, which reads saved pages and cannot reach the network.
"""

from __future__ import annotations

import logging
import random
import ssl
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import certifi
import httpx

from crawler.cache import CacheEntry, RawCacheStore
from crawler.exceptions import Blocked, RobotsDisallowed, SiteOffline, Timeout
from crawler.extraction import looks_blocked
from crawler.rate_limit import HostDelayPolicy, backoff_seconds, parse_retry_after
from crawler.robots import RobotsCache, RobotsUnreachable
from crawler.types import FetchResponse

logger = logging.getLogger(__name__)


class ResponseRecorder(Protocol):
    """Where the metadata of a fetch is written, and where validators come from."""

    def record(self, entry: CacheEntry, response: FetchResponse) -> None:
        """Persist metadata for a fetched body."""
        ...

    def validators_for(self, url: str) -> tuple[str, str]:
        """Return ``(etag, last_modified)`` from the newest stored fetch of ``url``."""
        ...

    def cache_key_for(self, url: str) -> str | None:
        """Return the raw-cache key of the newest stored fetch of ``url``, or ``None``."""
        ...


class NullRecorder:
    """Recorder that keeps nothing. Used in unit tests and one-off scripts."""

    def record(self, entry: CacheEntry, response: FetchResponse) -> None:
        """Do nothing."""

    def validators_for(self, url: str) -> tuple[str, str]:
        """Report no validators, so every request is unconditional."""
        return "", ""

    def cache_key_for(self, url: str) -> str | None:
        """Report nothing cached - paired with no validators, a 304 never happens."""
        return None


_CERTS_DIR = Path(__file__).resolve().parent / "certs"


@lru_cache(maxsize=1)
def trusted_ssl_context() -> ssl.SSLContext:
    """The default trust store, plus every supplemental intermediate in :data:`_CERTS_DIR`."""
    context = ssl.create_default_context(cafile=certifi.where())
    for cert_path in sorted(_CERTS_DIR.glob("*.pem")):
        context.load_verify_locations(cafile=str(cert_path))
    return context


def build_user_agent(name: str, contact_email: str) -> str:
    """Build a User-Agent that says who we are and how to contact us.

    A university's IT staff should be able to see who is crawling them and ask us to stop.
    """
    return f"{name}/1.0 (+mailto:{contact_email})"


@dataclass
class PoliteHttpClient:
    """HTTP client with robots, per-host pacing, retries and a raw-response cache."""

    user_agent: str
    cache: RawCacheStore
    recorder: ResponseRecorder = field(default_factory=NullRecorder)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    delay_policy: HostDelayPolicy = field(default_factory=HostDelayPolicy)
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    rng: random.Random = field(default_factory=random.Random)
    _client: httpx.Client | None = field(default=None, repr=False)
    _robots: RobotsCache | None = field(default=None, repr=False)
    cache_keys: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Create the underlying transport and the robots cache."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent, "Accept-Language": "en-GB,en;q=0.9"},
                verify=trusted_ssl_context(),
            )
        if self._robots is None:
            self._robots = RobotsCache(fetch_text=self._fetch_robots, user_agent=self.user_agent)

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
        """Fetch ``url`` politely, or raise a typed error."""
        return self._request("GET", url, headers=headers)

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResponse:
        """POST to ``url``. Used for form-backed listings and Workday's JSON API."""
        return self._request("POST", url, headers=headers, data=data, json=json)

    def close(self) -> None:
        """Release the connection pool."""
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> PoliteHttpClient:
        """Support ``with`` so connections are always released."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close the transport on the way out."""
        self.close()

    def _fetch_robots(self, robots_url: str) -> str | None:
        """Fetch ``robots.txt`` directly, without the robots check, to avoid recursion.

        Returns the file, or ``None`` for a 4xx (no rules). Raises :class:`RobotsUnreachable` for
        a server error, a 429 or no answer, as RFC 9309 asks.
        """
        try:
            response = self._transport().get(robots_url)
        except httpx.HTTPError as exc:
            raise RobotsUnreachable(robots_url) from exc
        if response.status_code == 200:
            return response.text
        if response.status_code == 429 or response.status_code >= 500:
            raise RobotsUnreachable(robots_url)
        return None

    def _transport(self) -> httpx.Client:
        """Return the httpx client, which ``__post_init__`` guarantees exists."""
        if self._client is None:  # pragma: no cover - defensive
            raise RuntimeError("PoliteHttpClient was not initialised")
        return self._client

    def _robots_cache(self) -> RobotsCache:
        """Return the robots cache, which ``__post_init__`` guarantees exists."""
        if self._robots is None:  # pragma: no cover - defensive
            raise RuntimeError("PoliteHttpClient was not initialised")
        return self._robots

    def prepare_navigation(self, url: str) -> None:
        """Apply the same rules as a normal request before the browser opens ``url``.

        Checks ``robots.txt``, applies its ``Crawl-delay``, and waits for this host's turn. The
        browser calls this before every page load and every "next page" click, so it is exactly
        as polite as the plain HTTP client.
        """
        host = urlparse(url).netloc.lower()
        self._check_robots(url, host)
        self._wait_turn(host)

    def _check_robots(self, url: str, host: str) -> None:
        """Raise if ``robots.txt`` disallows ``url``, and apply its ``Crawl-delay``."""
        rules = self._robots_cache().rules_for(url)
        if rules.unreachable:
            raise RobotsDisallowed(
                f"robots.txt for {host} could not be read, so everything is disallowed (RFC 9309)",
                url=url,
            )
        if not rules.allows(url, self.user_agent):
            raise RobotsDisallowed(f"robots.txt disallows {url}", url=url)
        if rules.crawl_delay:
            self.delay_policy.set_host_minimum(host, rules.crawl_delay)

    def _wait_turn(self, host: str) -> None:
        """Block until this host may be contacted again."""
        wait = self.delay_policy.wait_seconds(host, now=self.clock(), rng=self.rng)
        if wait > 0:
            self.sleep(wait)
        self.delay_policy.record_request(host, now=self.clock())

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        json: object | None = None,
    ) -> FetchResponse:
        """Perform one request with robots, pacing and bounded retries."""
        host = urlparse(url).netloc.lower()

        self._check_robots(url, host)

        request_headers = dict(headers or {})
        etag, last_modified = self.recorder.validators_for(url)
        if etag:
            request_headers.setdefault("If-None-Match", etag)
        if last_modified:
            request_headers.setdefault("If-Modified-Since", last_modified)

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._wait_turn(host)
            try:
                raw = self._transport().request(
                    method, url, headers=request_headers, data=data, json=json
                )
            except httpx.TimeoutException:
                last_error = Timeout(f"{url} timed out", url=url)
                logger.warning("timeout fetching %s (attempt %s)", url, attempt)
            except httpx.HTTPError as exc:
                last_error = SiteOffline(f"{url} unreachable: {exc}", url=url)
                logger.warning("transport error fetching %s: %s", url, exc)
            else:
                retry_after = raw.headers.get("retry-after", "")
                if raw.status_code in (429, 503):
                    until = parse_retry_after(retry_after, now=self.clock())
                    if until is not None:
                        self.delay_policy.defer(host, until=until)
                    last_error = (
                        Blocked(f"{url} returned 429", url=url)
                        if raw.status_code == 429
                        else SiteOffline(f"{url} returned 503", url=url)
                    )
                elif raw.status_code == 304:
                    cached_text = ""
                    key = self.recorder.cache_key_for(url)
                    if key is not None:
                        cached_text = self.cache.load(key) or ""
                    return FetchResponse(
                        url=str(raw.url),
                        status_code=304,
                        text=cached_text,
                        headers=dict(raw.headers),
                        not_modified=True,
                    )
                elif raw.status_code in (401, 403):
                    raise Blocked(f"{url} returned {raw.status_code}", url=url)
                elif raw.status_code >= 500:
                    last_error = SiteOffline(f"{url} returned {raw.status_code}", url=url)
                elif raw.status_code >= 400:
                    raise SiteOffline(f"{url} returned {raw.status_code}", url=url)
                else:
                    return self._finalise(url, raw)

            if attempt < self.max_retries:
                self.sleep(backoff_seconds(attempt))

        raise last_error or SiteOffline(f"{url} failed after {self.max_retries} attempts", url=url)

    def _finalise(self, url: str, raw: httpx.Response) -> FetchResponse:
        """Cache the body, record its metadata, and return the response."""
        text = raw.text
        if looks_blocked(text) and "text/html" in raw.headers.get("content-type", ""):
            raise Blocked(f"{url} served a challenge page", url=url)

        response = FetchResponse(
            url=str(raw.url),
            status_code=raw.status_code,
            text=text,
            headers=dict(raw.headers),
        )
        entry = self.cache.store(url, text)
        self.cache_keys.append(entry.key)
        self.recorder.record(entry, response)
        return response


@dataclass
class FixtureHttpClient:
    """A client that serves saved pages and refuses to use the network.

    Every adapter test uses it, so "no test visits a university" is enforced.
    """

    responses: dict[str, FetchResponse]
    requested: list[str] = field(default_factory=list)
    default: FetchResponse | None = None

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
        """Return the fixture registered for ``url``."""
        self.requested.append(url)
        response = self.responses.get(url, self.default)
        if response is None:
            raise SiteOffline(f"No fixture registered for {url}", url=url)
        return response

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResponse:
        """Return the fixture registered for ``url``, ignoring the body."""
        return self.get(url, headers=headers)
