"""Robots.txt and per-host pacing.

These are asserted against the *policy*, not by making the suite wait. Proving a two-second gap
by sleeping for two seconds would add a minute to every CI run to test one number.
"""

from __future__ import annotations

import pytest

from crawler.rate_limit import HostDelayPolicy, backoff_seconds, parse_retry_after
from crawler.robots import RobotsCache, RobotsUnreachable

ALLOW_ALL = "User-agent: *\nAllow: /\n"
DISALLOW_JOBS = "User-agent: *\nDisallow: /jobs/\nDisallow: /vacancies/\n"
CRAWL_DELAY = "User-agent: *\nAllow: /\nCrawl-delay: 7\n"


def robots(body: str | None) -> RobotsCache:
    """Build a robots cache serving one body for every host."""
    return RobotsCache(fetch_text=lambda url: body, user_agent="HEJobPortal/1.0")


def test_a_disallowed_path_is_refused() -> None:
    cache = robots(DISALLOW_JOBS)

    assert cache.allows("https://jobs.test.ac.uk/jobs/vacancy/1") is False


def test_an_allowed_path_on_the_same_host_is_permitted() -> None:
    cache = robots(DISALLOW_JOBS)

    assert cache.allows("https://jobs.test.ac.uk/about/") is True


def test_robots_is_fetched_once_per_host() -> None:
    """Cached for the run: 40 vacancy fetches must not mean 40 robots.txt fetches."""
    fetches: list[str] = []

    def record(url: str) -> str:
        fetches.append(url)
        return ALLOW_ALL

    cache = RobotsCache(fetch_text=record, user_agent="HEJobPortal/1.0")
    for index in range(5):
        cache.allows(f"https://jobs.test.ac.uk/vacancy/{index}")

    assert fetches == ["https://jobs.test.ac.uk/robots.txt"]


def test_two_hosts_are_fetched_separately() -> None:
    fetches: list[str] = []

    def record(url: str) -> str:
        fetches.append(url)
        return ALLOW_ALL

    cache = RobotsCache(fetch_text=record, user_agent="HEJobPortal/1.0")
    cache.allows("https://a.ac.uk/jobs")
    cache.allows("https://b.ac.uk/jobs")

    assert len(fetches) == 2


def test_a_missing_robots_file_permits_crawling() -> None:
    """RFC 9309: a 4xx answer means there are no rules."""
    cache = robots(None)

    assert cache.allows("https://jobs.test.ac.uk/jobs/") is True
    assert cache.rules_for("https://jobs.test.ac.uk/jobs/").unavailable is True


def test_an_unreachable_robots_file_disallows_everything() -> None:
    """RFC 9309: a server error or no answer means we must assume we are not allowed."""

    def unreachable(url: str) -> str | None:
        raise RobotsUnreachable(url)

    cache = RobotsCache(fetch_text=unreachable, user_agent="HEJobPortal/1.0")

    assert cache.allows("https://jobs.test.ac.uk/jobs/") is False
    assert cache.rules_for("https://jobs.test.ac.uk/jobs/").unreachable is True


def test_a_crawl_delay_directive_is_read() -> None:
    cache = robots(CRAWL_DELAY)

    assert cache.rules_for("https://jobs.test.ac.uk/jobs/").crawl_delay == 7.0


def test_the_first_request_to_a_host_waits_for_nothing() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)

    assert policy.wait_seconds("jobs.test.ac.uk", now=100.0) == 0.0


def test_a_second_request_to_the_same_host_waits_the_minimum() -> None:
    """Two requests to one host land at least two seconds apart."""
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.record_request("jobs.test.ac.uk", now=100.0)

    assert policy.wait_seconds("jobs.test.ac.uk", now=100.0) == 2.0


def test_a_request_after_the_gap_has_already_passed_waits_for_nothing() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.record_request("jobs.test.ac.uk", now=100.0)

    assert policy.wait_seconds("jobs.test.ac.uk", now=103.0) == 0.0


def test_two_different_hosts_do_not_block_each_other() -> None:
    """Global concurrency is across hosts; the one-at-a-time rule is per host."""
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.record_request("a.ac.uk", now=100.0)

    assert policy.wait_seconds("b.ac.uk", now=100.0) == 0.0


def test_jitter_never_shortens_the_gap() -> None:
    """Jitter exists to avoid a machine-gun-regular pattern, not to speed anything up."""
    import random

    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.5)
    policy.record_request("jobs.test.ac.uk", now=100.0)

    waits = [
        policy.wait_seconds("jobs.test.ac.uk", now=100.0, rng=random.Random(seed))
        for seed in range(20)
    ]

    assert min(waits) >= 2.0


def test_jitter_stays_inside_its_bound() -> None:
    import random

    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.5)
    policy.record_request("jobs.test.ac.uk", now=100.0)

    waits = [
        policy.wait_seconds("jobs.test.ac.uk", now=100.0, rng=random.Random(seed))
        for seed in range(20)
    ]

    assert max(waits) <= 2.5


def test_a_crawl_delay_raises_the_minimum_for_that_host() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.set_host_minimum("slow.ac.uk", 7.0)

    assert policy.minimum_for("slow.ac.uk") == 7.0


def test_a_crawl_delay_shorter_than_our_floor_does_not_make_us_less_polite() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.set_host_minimum("fast.ac.uk", 0.1)

    assert policy.minimum_for("fast.ac.uk") == 2.0


def test_retry_after_seconds_defers_the_host() -> None:
    """A host that says "come back in two minutes" is not argued with."""
    assert parse_retry_after("120", now=1000.0) == 1120.0


@pytest.mark.parametrize("value", ["", "   ", "Wed, 21 Oct 2026 07:28:00 GMT", "soon"])
def test_an_unusable_retry_after_leaves_the_standard_backoff_in_charge(value: str) -> None:
    """Guessing at an HTTP-date is worse than falling back to exponential backoff."""
    assert parse_retry_after(value, now=1000.0) is None


def test_a_deferral_is_honoured_by_the_delay_policy() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.defer("jobs.test.ac.uk", until=1120.0)

    assert policy.wait_seconds("jobs.test.ac.uk", now=1000.0) == pytest.approx(120.0)


def test_a_deferral_is_never_shortened_by_a_later_request() -> None:
    policy = HostDelayPolicy(min_delay_seconds=2.0, jitter_seconds=0.0)
    policy.defer("jobs.test.ac.uk", until=1120.0)
    policy.defer("jobs.test.ac.uk", until=1010.0)

    assert policy.wait_seconds("jobs.test.ac.uk", now=1000.0) == pytest.approx(120.0)


@pytest.mark.parametrize(("attempt", "expected"), [(1, 1.0), (2, 2.0), (3, 4.0), (10, 60.0)])
def test_backoff_grows_exponentially_and_is_capped(attempt: int, expected: float) -> None:
    assert backoff_seconds(attempt) == expected
