"""The polite HTTP client's own behaviour, independent of any adapter.

Every adapter test in ``test_adapters.py`` runs against :class:`FixtureHttpClient`, which never
exercises :class:`PoliteHttpClient` at all - so a bug in the real client's retry, robots or
caching logic has no test surface anywhere else. This file is that surface.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from crawler.cache import CacheEntry, InMemoryRawCache
from crawler.exceptions import RobotsDisallowed
from crawler.http import PoliteHttpClient, trusted_ssl_context
from crawler.rate_limit import HostDelayPolicy
from crawler.types import FetchResponse

_URL = "https://jobs.test.ac.uk/vacancies"
_ROBOTS_URL = "https://jobs.test.ac.uk/robots.txt"


class _FakeRecorder:
    """A recorder whose validators and cache key are set up by the test, not by a database."""

    def __init__(self, *, etag: str = "", cache_key: str | None = None) -> None:
        self.etag = etag
        self.cache_key = cache_key
        self.recorded: list[FetchResponse] = []

    def record(self, entry: CacheEntry, response: FetchResponse) -> None:
        self.recorded.append(response)

    def validators_for(self, url: str) -> tuple[str, str]:
        return self.etag, ""

    def cache_key_for(self, url: str) -> str | None:
        return self.cache_key


def _client(recorder: _FakeRecorder, cache: InMemoryRawCache) -> PoliteHttpClient:
    return PoliteHttpClient(
        user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)",
        cache=cache,
        recorder=recorder,
        max_retries=1,
        delay_policy=HostDelayPolicy(min_delay_seconds=0, jitter_seconds=0),
    )


@respx.mock
def test_a_304_returns_the_previously_cached_body_not_an_empty_one() -> None:
    """The regression.

    Two fetches of the same URL a few seconds apart within one crawl - a probe, then an
    adapter's own fetch - send the same conditional headers the second time, and a server that
    has not changed answers with 304. Every caller in this codebase reads ``.text`` as the
    page's content; handing back an empty string there reads as "this page is blank" instead of
    "nothing changed", which is what turned into every structured-data institution's
    ``PARSE_ERROR`` the same day this was written.
    """
    respx.get(_ROBOTS_URL).mock(return_value=httpx.Response(404))
    respx.get(_URL).mock(return_value=httpx.Response(304))

    cache = InMemoryRawCache()
    entry = cache.store(_URL, "<html>cached vacancy list</html>")
    recorder = _FakeRecorder(etag='"abc123"', cache_key=entry.key)
    client = _client(recorder, cache)

    response = client.get(_URL)

    assert response.status_code == 304
    assert response.not_modified is True
    assert response.text == "<html>cached vacancy list</html>"


@respx.mock
def test_a_304_with_nothing_cached_degrades_to_empty_rather_than_crashing() -> None:
    """No cache entry survives forever (pruning, a cold recorder) - this must not raise."""
    respx.get(_ROBOTS_URL).mock(return_value=httpx.Response(404))
    respx.get(_URL).mock(return_value=httpx.Response(304))

    recorder = _FakeRecorder(etag='"abc123"', cache_key=None)
    client = _client(recorder, InMemoryRawCache())

    response = client.get(_URL)

    assert response.status_code == 304
    assert response.text == ""


@respx.mock
def test_a_normal_200_is_cached_and_recorded_for_next_times_304() -> None:
    respx.get(_ROBOTS_URL).mock(return_value=httpx.Response(404))
    respx.get(_URL).mock(return_value=httpx.Response(200, text="<html>fresh</html>"))

    cache = InMemoryRawCache()
    recorder = _FakeRecorder()
    client = _client(recorder, cache)

    response = client.get(_URL)

    assert response.text == "<html>fresh</html>"
    assert response.not_modified is False
    assert len(recorder.recorded) == 1


def test_the_trusted_context_loads_without_error() -> None:
    """Regression: a target that fails to send its own intermediate certificate.

    `jobs.bcu.ac.uk` chains through a Sectigo intermediate it never sends in the handshake -
    a real, common server misconfiguration a browser papers over and Python's ``ssl`` module
    does not. This only proves the supplemental bundle in `crawler/certs/` parses and loads
    cleanly into the default trust store; it deliberately does not touch the real internet to
    prove the fix, since asserting a specific site's chain now verifies would be exactly the
    kind of test this project's `no test touches the real internet` rule rules out.
    """
    context = trusted_ssl_context()

    assert context.cert_store_stats()["x509"] > 0


def test_the_polite_client_is_built_with_the_trusted_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The client must actually use the supplemental trust store, not just have it lying around."""
    captured: dict[str, object] = {}
    real_client = httpx.Client

    def _spy(*args: object, **kwargs: object) -> httpx.Client:
        captured.update(kwargs)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("crawler.http.httpx.Client", _spy)

    _client(_FakeRecorder(), InMemoryRawCache())

    assert captured.get("verify") is trusted_ssl_context()


@respx.mock
def test_a_robots_server_error_disallows_every_request() -> None:
    """RFC 9309: if robots.txt gives a 5xx, assume the whole site is disallowed for now."""
    respx.get(_ROBOTS_URL).mock(return_value=httpx.Response(503))
    page = respx.get(_URL).mock(return_value=httpx.Response(200, text="<html>jobs</html>"))

    with pytest.raises(RobotsDisallowed):
        _client(_FakeRecorder(), InMemoryRawCache()).get(_URL)
    assert page.called is False


@respx.mock
def test_the_browser_guard_refuses_a_page_robots_disallows() -> None:
    """The browser asks the same robots check before it opens a page."""
    respx.get(_ROBOTS_URL).mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /vacancies")
    )

    with pytest.raises(RobotsDisallowed):
        _client(_FakeRecorder(), InMemoryRawCache()).prepare_navigation(_URL)


@respx.mock
def test_the_browser_guard_allows_a_site_with_no_robots_file() -> None:
    respx.get(_ROBOTS_URL).mock(return_value=httpx.Response(404))

    _client(_FakeRecorder(), InMemoryRawCache()).prepare_navigation(_URL)
