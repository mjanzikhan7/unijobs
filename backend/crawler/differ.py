"""Working out what changed between two crawls.

This module holds the most important rule in the project. It is a pure function, so every
outcome can be tested in a table in a millisecond:

    A job seen in run N-1 and missing in run N is marked DISAPPEARED **only** when that
    institution's outcome was OK.

The reason is real. A university site went down for maintenance over a weekend. If we had
trusted the empty page, every one of its vacancies would have been closed, and a whole
university would have vanished from search.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from crawler.enums import CLOSURE_SAFE_OUTCOMES, CrawlOutcome
from crawler.types import RawVacancy


def vacancy_content_hash(vacancy: RawVacancy) -> str:
    """Hash the fields whose change means the advert was edited.

    The description is left out on purpose. Universities often change their advert HTML without
    changing any important words, and counting that as an update would fill the Changed tab with
    noise.
    """
    digest = hashlib.sha256()
    for part in (
        vacancy.title,
        vacancy.salary_raw,
        vacancy.grade_raw,
        vacancy.location_raw,
        vacancy.department,
        vacancy.category,
        vacancy.reference,
        vacancy.contract_raw,
        vacancy.closing_date.isoformat() if vacancy.closing_date else "",
    ):
        digest.update((part or "").strip().encode("utf-8"))
        digest.update(b"\x1f")
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ExistingJob:
    """The stored state of a job, as far as the differ needs to know it."""

    job_id: int
    source_url: str
    content_hash: str
    status: str
    title: str = ""
    salary_raw: str = ""
    closing_date: date | None = None
    location_raw: str = ""
    is_manual: bool = False
    is_withdrawn: bool = False


@dataclass(frozen=True, slots=True)
class DiffResult:
    """What one institution's crawl changed."""

    new: tuple[RawVacancy, ...] = ()
    updated: tuple[tuple[RawVacancy, ExistingJob], ...] = ()
    unchanged: tuple[tuple[RawVacancy, ExistingJob], ...] = ()
    disappeared: tuple[ExistingJob, ...] = ()
    closure_skipped_reason: str = ""

    @property
    def counts(self) -> dict[str, int]:
        """Totals for the run summary."""
        return {
            "new": len(self.new),
            "updated": len(self.updated),
            "unchanged": len(self.unchanged),
            "disappeared": len(self.disappeared),
        }


def diff_vacancies(
    *,
    fetched: Sequence[RawVacancy],
    existing: Sequence[ExistingJob],
    outcome: CrawlOutcome,
) -> DiffResult:
    """Split a crawl's results into new, updated, unchanged and disappeared.

    ``disappeared`` is empty for every outcome except ``OK``. Always. A blocked, offline, timed
    out, robots-disallowed or empty run leaves existing jobs exactly as they were.
    """
    by_url = {job.source_url: job for job in existing}

    new: list[RawVacancy] = []
    updated: list[tuple[RawVacancy, ExistingJob]] = []
    unchanged: list[tuple[RawVacancy, ExistingJob]] = []
    seen_urls: set[str] = set()

    for vacancy in fetched:
        seen_urls.add(vacancy.source_url)
        stored = by_url.get(vacancy.source_url)
        if stored is None:
            new.append(vacancy)
        elif stored.is_withdrawn:
            unchanged.append((vacancy, stored))
        elif stored.status != "OPEN" or stored.content_hash != vacancy_content_hash(vacancy):
            updated.append((vacancy, stored))
        else:
            unchanged.append((vacancy, stored))

    if outcome not in CLOSURE_SAFE_OUTCOMES:
        return DiffResult(
            new=tuple(new),
            updated=tuple(updated),
            unchanged=tuple(unchanged),
            disappeared=(),
            closure_skipped_reason=(
                f"Outcome was {outcome.value}, not OK. Existing jobs were left untouched."
            ),
        )

    disappeared = tuple(
        job
        for job in existing
        if job.source_url not in seen_urls and not job.is_manual and job.status == "OPEN"
    )

    return DiffResult(
        new=tuple(new),
        updated=tuple(updated),
        unchanged=tuple(unchanged),
        disappeared=disappeared,
    )


@dataclass(frozen=True, slots=True)
class FieldChange:
    """One field of one job changing, for the Changed tab of a run diff."""

    field: str
    before: str
    after: str


TRACKED_FIELDS: tuple[str, ...] = ("title", "salary_raw", "closing_date", "location_raw")


def field_changes(vacancy: RawVacancy, stored: ExistingJob) -> list[FieldChange]:
    """List the tracked fields that differ between a fetched vacancy and the stored job."""
    fetched_values = {
        "title": vacancy.title,
        "salary_raw": vacancy.salary_raw,
        "closing_date": vacancy.closing_date.isoformat() if vacancy.closing_date else "",
        "location_raw": vacancy.location_raw,
    }
    stored_values = {
        "title": stored.title,
        "salary_raw": stored.salary_raw,
        "closing_date": stored.closing_date.isoformat() if stored.closing_date else "",
        "location_raw": stored.location_raw,
    }
    return [
        FieldChange(field=name, before=stored_values[name], after=fetched_values[name])
        for name in TRACKED_FIELDS
        if (stored_values[name] or "").strip() != (fetched_values[name] or "").strip()
    ]


def deduplicate(vacancies: Sequence[RawVacancy]) -> list[RawVacancy]:
    """Remove repeated ``source_url`` entries, keeping the first.

    Stonefish lists a vacancy once for each department, so a shared post can appear twice.
    """
    seen: set[str] = set()
    unique: list[RawVacancy] = []
    for vacancy in vacancies:
        if vacancy.source_url in seen:
            continue
        seen.add(vacancy.source_url)
        unique.append(vacancy)
    return unique
