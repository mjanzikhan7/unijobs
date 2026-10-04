"""Typed adapter failures.

An adapter raises one of these or returns a list. It never returns ``None``, never returns an
empty list to hide a failure, and never raises a bare ``Exception``. The type of the failure
becomes a :class:`~crawler.enums.CrawlOutcome`, and only one outcome allows jobs to be closed.
"""

from __future__ import annotations

from crawler.enums import CrawlOutcome


class AdapterError(Exception):
    """Base class for every failure an adapter is allowed to raise."""

    outcome: CrawlOutcome = CrawlOutcome.PARSE_ERROR

    def __init__(self, message: str = "", *, url: str = "") -> None:
        """Record the URL alongside the message; it is the first thing anyone asks for."""
        super().__init__(message or self.__class__.__name__)
        self.url = url


class RobotsDisallowed(AdapterError):
    """``robots.txt`` forbids the target path. Never retried, never routed around."""

    outcome = CrawlOutcome.ROBOTS_DISALLOWED


class SiteOffline(AdapterError):
    """The host is unreachable, or served a maintenance page instead of a listing."""

    outcome = CrawlOutcome.OFFLINE


class Blocked(AdapterError):
    """The host answered, but with a challenge, a 403, or a rate limit."""

    outcome = CrawlOutcome.BLOCKED


class Timeout(AdapterError):
    """The request did not complete inside the configured budget."""

    outcome = CrawlOutcome.TIMEOUT


class ParseError(AdapterError):
    """The page was fetched but could not be understood.

    Raised, never hidden, so an empty list always means there really are no vacancies.
    """

    outcome = CrawlOutcome.PARSE_ERROR


class NoAdapterFound(AdapterError):
    """No registered adapter recognised this institution's portal."""

    outcome = CrawlOutcome.NO_ADAPTER


def outcome_for(error: BaseException) -> CrawlOutcome:
    """Map an exception to a crawl outcome.

    An unexpected exception becomes ``PARSE_ERROR``, which never closes jobs. The default must
    fail in the direction that leaves existing jobs alone.
    """
    if isinstance(error, AdapterError):
        return error.outcome
    return CrawlOutcome.PARSE_ERROR


RETRYABLE_ERRORS: tuple[type[AdapterError], ...] = (Timeout, SiteOffline)
