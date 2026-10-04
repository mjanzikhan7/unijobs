"""Politeness per host, as a policy instead of sleeps.

The decision ("how long until this host may be contacted again?") is separate from the
waiting, so tests can check a 2-second gap in microseconds.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class HostDelayPolicy:
    """Decides when a host may be contacted next.

    One request per host at a time, a minimum gap, and some random jitter.
    """

    min_delay_seconds: float = 2.0
    jitter_seconds: float = 0.5
    _next_allowed: dict[str, float] = field(default_factory=dict, repr=False)
    _per_host_minimum: dict[str, float] = field(default_factory=dict, repr=False)

    def set_host_minimum(self, host: str, delay_seconds: float) -> None:
        """Raise the minimum gap for one host, from its ``robots.txt`` ``Crawl-delay``.

        Only ever raises it. A site that asks for a longer gap gets it. A site cannot make us less
        polite than our own minimum.
        """
        self._per_host_minimum[host] = max(delay_seconds, self.min_delay_seconds)

    def minimum_for(self, host: str) -> float:
        """The gap this host requires, taking its ``Crawl-delay`` into account."""
        return self._per_host_minimum.get(host, self.min_delay_seconds)

    def wait_seconds(self, host: str, *, now: float, rng: random.Random | None = None) -> float:
        """How long to wait before contacting ``host``. Zero on first contact."""
        allowed_at = self._next_allowed.get(host)
        if allowed_at is None:
            return 0.0
        base = max(0.0, allowed_at - now)
        if base == 0.0:
            return 0.0
        if not self.jitter_seconds:
            return base
        generator = rng if rng is not None else random.Random()
        return base + generator.uniform(0.0, self.jitter_seconds)

    def record_request(self, host: str, *, now: float) -> None:
        """Note that ``host`` was just contacted."""
        self._next_allowed[host] = now + self.minimum_for(host)

    def defer(self, host: str, *, until: float) -> None:
        """Hold off on ``host`` until a specific time, honouring a ``Retry-After``."""
        self._next_allowed[host] = max(self._next_allowed.get(host, 0.0), until)


def parse_retry_after(value: str, *, now: float) -> float | None:
    """Turn a ``Retry-After`` header into an absolute time.

    Handles the seconds form. The date form is rare on university sites, so it counts as "no
    value" and the normal backoff applies.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return now + float(int(raw))
    except ValueError:
        return None


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 60.0) -> float:
    """Exponential backoff for attempt ``attempt`` (1-indexed), capped."""
    return min(cap, base * float(2 ** max(0, attempt - 1)))
