"""``robots.txt`` parsing and caching, following RFC 9309.

A disallowed page is skipped and recorded as ``ROBOTS_DISALLOWED``. There is no setting to get
around it, on purpose. This project is not worth ignoring a university's stated wishes.

How the fetch result is read (RFC 9309, section 2.3.1):

* 200: the rules in the file apply.
* 4xx (for example 404): there are no rules, so crawling is allowed.
* 5xx, 429 or no answer: the site may have rules we cannot read, so everything is disallowed
  until a later run can read the file.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser


class RobotsUnreachable(Exception):
    """``robots.txt`` gave a server error or no answer. RFC 9309 says: disallow everything."""


@dataclass(frozen=True, slots=True)
class RobotsRules:
    """A parsed ``robots.txt`` for one host."""

    host: str
    parser: RobotFileParser | None
    crawl_delay: float | None = None
    unavailable: bool = False
    unreachable: bool = False

    def allows(self, url: str, user_agent: str) -> bool:
        """Whether ``user_agent`` may fetch ``url``."""
        if self.unreachable:
            return False
        if self.parser is None:
            return True
        return self.parser.can_fetch(user_agent, url)


@dataclass
class RobotsCache:
    """Fetches and caches ``robots.txt`` per host, once per run.

    ``fetch_text`` returns the file, returns ``None`` when there is no file, or raises
    :class:`RobotsUnreachable` when it cannot be read.
    """

    fetch_text: Callable[[str], str | None]
    user_agent: str
    _rules: dict[str, RobotsRules] = field(default_factory=dict, repr=False)

    def rules_for(self, url: str) -> RobotsRules:
        """Return the rules for the host of ``url``, fetching once per host."""
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        cached = self._rules.get(host)
        if cached is not None:
            return cached

        robots_url = urljoin(f"{parsed.scheme or 'https'}://{host}", "/robots.txt")
        try:
            body = self.fetch_text(robots_url)
        except RobotsUnreachable:
            rules = RobotsRules(host=host, parser=None, unreachable=True)
            self._rules[host] = rules
            return rules
        if body is None:
            rules = RobotsRules(host=host, parser=None, unavailable=True)
        else:
            parser = RobotFileParser()
            parser.parse(body.splitlines())
            delay = parser.crawl_delay(self.user_agent)
            rules = RobotsRules(
                host=host,
                parser=parser,
                crawl_delay=float(delay) if delay is not None else None,
            )
        self._rules[host] = rules
        return rules

    def allows(self, url: str) -> bool:
        """Whether this crawler may fetch ``url``."""
        return self.rules_for(url).allows(url, self.user_agent)
