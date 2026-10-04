"""The events table and its daily totals.

A star schema: one row per event, with foreign keys to the things worth grouping by and a
JSON column for the rest. Two rules keep the history trustworthy:

* **Events are never changed or deleted one by one.** A correction is a new row.
* **Links use `SET_NULL`, never `CASCADE`.** Deleting a job must not delete the record that four
  people looked at it, or every trend line would change after a tidy-up.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.enums import Role
from analytics.enums import EventKind
from institutions.models import Institution
from jobs.models import Job


class AnalyticsEventQuerySet(models.QuerySet["AnalyticsEvent"]):
    """Query helpers the dashboards share."""

    def since(self, when: object) -> AnalyticsEventQuerySet:
        """Events from ``when`` onwards."""
        return self.filter(occurred_at__gte=when)

    def of_kind(self, *kinds: EventKind) -> AnalyticsEventQuerySet:
        """Events of one or more kinds."""
        return self.filter(kind__in=[str(kind) for kind in kinds])

    def by_candidates(self) -> AnalyticsEventQuerySet:
        """Only what candidates did.

        Staff browse institutions all the time as part of their work. Counting that as demand would
        give misleading totals.
        """
        return self.filter(actor_role=str(Role.CANDIDATE))


class AnalyticsEvent(models.Model):
    """One thing somebody did, recorded once and never revised."""

    kind = models.CharField(max_length=24, choices=EventKind.choices())
    occurred_at = models.DateTimeField(default=timezone.now)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
    )
    actor_role = models.CharField(max_length=16, blank=True)

    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="analytics_events"
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_events",
    )

    nation = models.CharField(max_length=32, blank=True)
    category = models.CharField(max_length=200, blank=True)

    query = models.CharField(max_length=200, blank=True)
    result_count = models.PositiveIntegerField(null=True, blank=True)

    payload = models.JSONField(default=dict, blank=True)

    objects = AnalyticsEventQuerySet.as_manager()

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["kind", "-occurred_at"], name="analytics_kind_time_idx"),
            models.Index(fields=["-occurred_at"], name="analytics_time_idx"),
            models.Index(fields=["institution", "-occurred_at"], name="analytics_inst_time_idx"),
            models.Index(fields=["actor", "-occurred_at"], name="analytics_actor_time_idx"),
            models.Index(fields=["actor_role", "kind"], name="analytics_role_kind_idx"),
        ]

    def __str__(self) -> str:
        """Return what happened and when."""
        return f"{self.kind} at {self.occurred_at:%Y-%m-%d %H:%M}"


class SearchTermDaily(models.Model):
    """How often one term was searched on one day.

    A total, not the source of truth. It can be rebuilt from the events table at any time. It
    exists so the word cloud does not read a year of raw events on every page load.
    """

    day = models.DateField()
    term = models.CharField(max_length=64)
    occurrences = models.PositiveIntegerField(default=0)
    searchers = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-day", "-occurrences"]
        constraints = [models.UniqueConstraint(fields=["day", "term"], name="unique_term_per_day")]
        indexes = [
            models.Index(fields=["-day", "-occurrences"], name="analytics_term_day_idx"),
            models.Index(fields=["term"], name="analytics_term_idx"),
        ]

    def __str__(self) -> str:
        """Return the term and its count."""
        return f"{self.term} x{self.occurrences} on {self.day}"
