"""The raw response cache.

Every fetch is saved to disk, keyed by ``(url, sha256(body))``, because:

* adapters are rewritten often, and replaying saved HTML takes seconds instead of a two-hour
  crawl;
* when a parse looks wrong, the exact bytes show why;
* it keeps the tests offline.

Bodies are on a Docker volume, not in PostgreSQL. They are large, they change often, and they
do not need a database.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol


def cache_key(url: str, body: str) -> str:
    """Key a body by its URL and its content.

    An unchanged page fetched every day uses one file, not ninety. A changed page never
    overwrites the version behind yesterday's parse.
    """
    url_digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    body_digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"{url_digest}-{body_digest}"


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """A stored body and everything needed to find it again."""

    key: str
    url: str
    sha256: str
    path: Path
    byte_size: int
    stored_at: datetime


class RawCacheStore(Protocol):
    """Where raw bodies go. Implemented on disk in production, in memory in tests."""

    def store(self, url: str, body: str) -> CacheEntry:
        """Persist ``body`` and return its entry."""
        ...

    def load(self, key: str) -> str | None:
        """Return a previously stored body, or ``None``."""
        ...


@dataclass
class DiskRawCache:
    """Disk-backed body store, sharded two levels deep to keep directories small."""

    root: Path

    def _path_for(self, key: str) -> Path:
        return self.root / key[:2] / key[2:4] / f"{key}.html"

    def store(self, url: str, body: str) -> CacheEntry:
        """Write ``body`` under its content-addressed key."""
        key = cache_key(url, body)
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = body.encode("utf-8")
        if not path.exists():
            path.write_bytes(encoded)
        return CacheEntry(
            key=key,
            url=url,
            sha256=hashlib.sha256(encoded).hexdigest(),
            path=path,
            byte_size=len(encoded),
            stored_at=datetime.now(tz=UTC),
        )

    def load(self, key: str) -> str | None:
        """Read a stored body, or return ``None`` when it has been pruned."""
        path = self._path_for(key)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8", errors="replace")

    def prune(self, *, older_than_days: int, now: float | None = None) -> int:
        """Delete bodies last changed more than ``older_than_days`` ago.

        Returns how many files were removed. Ninety days is long enough to debug a problem noticed a
        month late, and short enough that the volume does not grow forever.
        """
        cutoff = (now if now is not None else time.time()) - timedelta(
            days=older_than_days
        ).total_seconds()
        removed = 0
        if not self.root.exists():
            return 0
        for path in self.root.rglob("*.html"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        return removed


@dataclass
class InMemoryRawCache:
    """Body store for tests. Nothing touches the filesystem."""

    bodies: dict[str, str]

    def __init__(self) -> None:
        """Start empty."""
        self.bodies = {}

    def store(self, url: str, body: str) -> CacheEntry:
        """Keep ``body`` in a dict under its content-addressed key."""
        key = cache_key(url, body)
        self.bodies[key] = body
        return CacheEntry(
            key=key,
            url=url,
            sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
            path=Path("/dev/null"),
            byte_size=len(body.encode("utf-8")),
            stored_at=datetime.now(tz=UTC),
        )

    def load(self, key: str) -> str | None:
        """Return a stored body, or ``None``."""
        return self.bodies.get(key)
