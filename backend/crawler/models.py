"""Crawl records: runs, the result for each institution, and raw response details.

The per-institution row matters most. It makes silent breakage visible. An institution with 40
vacancies last night and 0 this morning is different from one that has had none for two weeks.
Only the saved outcome and the previous count can tell them apart.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from crawler.enums import (
    ACTIVE_RUN_STATUSES,
    CLOSURE_SAFE_OUTCOMES,
    CrawlLogLevel,
    CrawlOutcome,
    CrawlRunStatus,
    CrawlTrigger,
    ExtractionStrategy,
)
from institutions.models import Institution


class CrawlRun(models.Model):
    """One crawl of the estate, or of a single institution."""

    trigger = models.CharField(
        max_length=16, choices=CrawlTrigger.choices(), default=CrawlTrigger.MANUAL
    )
    status = models.CharField(
        max_length=16, choices=CrawlRunStatus.choices(), default=CrawlRunStatus.RUNNING
    )
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(default=timezone.now)

    institutions_total = models.PositiveIntegerField(default=0)
    institutions_done = models.PositiveIntegerField(default=0)
    jobs_new = models.PositiveIntegerField(default=0)
    jobs_updated = models.PositiveIntegerField(default=0)
    jobs_closed = models.PositiveIntegerField(default=0)

    institution_ids = models.JSONField(default=list, blank=True)

    error_detail = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["status", "-started_at"])]

    def __str__(self) -> str:
        """Return the run id and status."""
        return f"Run {self.pk} ({self.status})"

    @property
    def is_active(self) -> bool:
        """Whether this run still holds the single active run slot.

        A paused run is not finished. Starting a second run, or pausing twice, must still be
        refused.
        """
        return CrawlRunStatus(self.status) in ACTIVE_RUN_STATUSES

    @property
    def duration_seconds(self) -> float | None:
        """Wall-clock duration, or ``None`` while still running."""
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()


class CrawlRunInstitution(models.Model):
    """The outcome of crawling one institution within one run."""

    run = models.ForeignKey(CrawlRun, on_delete=models.CASCADE, related_name="institution_results")
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="crawl_results"
    )

    adapter = models.CharField(max_length=64, blank=True)
    outcome = models.CharField(max_length=32, choices=CrawlOutcome.choices())
    strategy = models.CharField(
        max_length=32, choices=ExtractionStrategy.choices(), default=ExtractionStrategy.NONE
    )
    fallback_fired = models.BooleanField(default=False)

    vacancies_found = models.PositiveIntegerField(default=0)
    previous_vacancies_found = models.PositiveIntegerField(null=True, blank=True)
    jobs_new = models.PositiveIntegerField(default=0)
    jobs_updated = models.PositiveIntegerField(default=0)
    jobs_closed = models.PositiveIntegerField(default=0)

    duration_ms = models.PositiveIntegerField(default=0)
    error_class = models.CharField(max_length=120, blank=True)
    error_detail = models.TextField(blank=True)
    raw_cache_keys = models.JSONField(default=list, blank=True)

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["institution__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "institution"], name="unique_institution_per_run"
            )
        ]
        indexes = [
            models.Index(fields=["run", "outcome"]),
            models.Index(fields=["institution", "-started_at"]),
        ]

    def __str__(self) -> str:
        """Return the institution and outcome."""
        return f"{self.institution_id}: {self.outcome}"

    @property
    def permits_closure(self) -> bool:
        """Whether the differ may close jobs based on this result.

        The most important property in the project. A university site was once down for maintenance
        over a weekend. Trusting a non-``OK`` outcome would have closed all its vacancies.
        """
        return CrawlOutcome(self.outcome) in CLOSURE_SAFE_OUTCOMES

    @property
    def dropped_to_zero(self) -> bool:
        """Whether this institution went from some vacancies to none.

        Shown at the top of the crawl console, because it is the sign of an adapter that stopped
        working without an error.
        """
        return self.vacancies_found == 0 and bool(self.previous_vacancies_found)


class RawResponse(models.Model):
    """Details of one cached fetch.

    The body is on disk, found by ``cache_key``. It is too big and changes too often for the
    database.
    """

    cache_key = models.CharField(max_length=128, unique=True)
    url = models.URLField(max_length=1000)
    sha256 = models.CharField(max_length=64)
    status_code = models.PositiveSmallIntegerField(default=0)
    content_type = models.CharField(max_length=200, blank=True)
    etag = models.CharField(max_length=300, blank=True)
    last_modified = models.CharField(max_length=200, blank=True)
    byte_size = models.PositiveIntegerField(default=0)
    fetched_at = models.DateTimeField(default=timezone.now)
    storage_path = models.CharField(max_length=500)

    class Meta:
        ordering = ["-fetched_at"]
        indexes = [
            models.Index(fields=["url", "-fetched_at"]),
            models.Index(fields=["fetched_at"]),
        ]

    def __str__(self) -> str:
        """Return the URL and fetch time."""
        return f"{self.url} @ {self.fetched_at:%Y-%m-%d %H:%M}"


class CrawlLogEntry(models.Model):
    """One line in a run's log, written at every important step.

    The crawl console reads these through the ``/logs/`` endpoint.
    """

    run = models.ForeignKey(CrawlRun, on_delete=models.CASCADE, related_name="log_entries")
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    level = models.CharField(
        max_length=8, choices=CrawlLogLevel.choices(), default=CrawlLogLevel.INFO
    )
    message = models.TextField()
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["run", "created_at"])]

    def __str__(self) -> str:
        """Return the level and the message, truncated."""
        return f"[{self.level}] {self.message[:80]}"
