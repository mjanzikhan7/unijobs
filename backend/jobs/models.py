"""Vacancies, and what candidates attach to them.

A ``Job`` is identified by ``(institution, source_url)``. Crawling the same institution twice
must give the same rows, so the upsert uses that pair as its key and ``content_hash`` to see
whether anything changed.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models.functions import Coalesce
from django.utils import timezone

from institutions.models import Institution
from jobs.domain import looks_ghosted
from jobs.enums import (
    ApplicationStatus,
    ChangeField,
    ContractType,
    Discipline,
    Hours,
    JobSource,
    JobStatus,
    Workplace,
)


class JobQuerySet(models.QuerySet["Job"]):
    """Query helpers. The list endpoint must never issue a query per row."""

    def with_related(self, *, for_user: User) -> JobQuerySet:
        """Load everything one user's job row needs, in one query.

        ``for_user`` is keyword-only with no default, on purpose. Without it, the list could show
        whether *someone* saved a job, or return *someone else's* ``application_id``. A missing
        argument fails loudly instead.
        """
        return (
            self.select_related("institution", "screening", "screening__ruleset")
            .annotate(
                is_saved=models.Exists(
                    SavedJob.objects.filter(job=models.OuterRef("pk"), owner=for_user)
                ),
                application_id=models.Subquery(
                    Application.objects.filter(job=models.OuterRef("pk"), owner=for_user).values(
                        "pk"
                    )[:1]
                ),
                application_status=models.Subquery(
                    Application.objects.filter(job=models.OuterRef("pk"), owner=for_user).values(
                        "status"
                    )[:1]
                ),
            )
            .with_fitness_for(for_user)
        )

    def with_fitness_for(self, user: User) -> JobQuerySet:
        """Add this user's fitness score and reasons to each row.

        Uses a ``FilteredRelation`` (one LEFT JOIN) instead of importing ``screening.JobFitness``,
        which would create an import cycle. A job with no score shows 0, meaning "no profile yet".
        """
        return self.annotate(
            _owner_fitness=models.FilteredRelation(
                "fitness", condition=models.Q(fitness__owner=user)
            ),
            fitness_score=Coalesce(models.F("_owner_fitness__score"), models.Value(0)),
            fitness_reasons=models.F("_owner_fitness__reasons"),
        )

    def open(self) -> JobQuerySet:
        """Only vacancies still listed."""
        return self.filter(status=JobStatus.OPEN)

    def crawled(self) -> JobQuerySet:
        """Exclude manually added jobs - the differ must never close those."""
        return self.exclude(source=JobSource.MANUAL)

    def withdrawn(self) -> JobQuerySet:
        """Jobs an administrator took down."""
        return self.filter(status=JobStatus.WITHDRAWN)


class Job(models.Model):
    """One advertised vacancy."""

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="jobs")
    source = models.CharField(max_length=16, choices=JobSource.choices(), default=JobSource.PORTAL)
    source_url = models.URLField(max_length=1000)

    title = models.CharField(max_length=500)
    department = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=120, blank=True)

    description_html = models.TextField(blank=True)
    description_text = models.TextField(blank=True)

    location_raw = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    salary_raw = models.CharField(max_length=500, blank=True)
    grade_raw = models.CharField(max_length=120, blank=True)

    contract_raw = models.CharField(max_length=200, blank=True)
    hours_raw = models.CharField(max_length=200, blank=True)

    contract_type = models.CharField(
        max_length=16, choices=ContractType.choices(), default=ContractType.UNKNOWN
    )
    hours = models.CharField(max_length=16, choices=Hours.choices(), default=Hours.UNKNOWN)
    workplace = models.CharField(
        max_length=16, choices=Workplace.choices(), default=Workplace.UNKNOWN
    )
    discipline = models.CharField(
        max_length=48, choices=Discipline.choices(), default=Discipline.OTHER
    )

    posted_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=16, choices=JobStatus.choices(), default=JobStatus.OPEN)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    disappeared_at = models.DateTimeField(null=True, blank=True)

    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdrawn_jobs",
    )
    withdrawn_reason = models.CharField(max_length=300, blank=True)

    content_hash = models.CharField(max_length=64, blank=True)
    search_vector = SearchVectorField(null=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ["-posted_date", "-first_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "source_url"], name="unique_job_per_institution_url"
            )
        ]
        indexes = [
            models.Index(fields=["institution", "status"]),
            models.Index(fields=["closing_date"]),
            models.Index(fields=["posted_date"]),
            models.Index(fields=["status", "-posted_date"]),
            GinIndex(fields=["search_vector"], name="job_search_vector_gin"),
        ]

    def __str__(self) -> str:
        """Return a human-readable identifier."""
        return f"{self.title} — {self.institution_id}"

    @staticmethod
    def compute_content_hash(*parts: str | None) -> str:
        """Hash the fields whose change means the advert was edited.

        This tells new, updated and unchanged apart without comparing whole rows, so a re-crawl of
        unchanged adverts writes nothing.
        """
        digest = hashlib.sha256()
        for part in parts:
            digest.update((part or "").strip().encode("utf-8"))
            digest.update(b"\x1f")
        return digest.hexdigest()

    @property
    def closes_within_days(self) -> int | None:
        """Days until the advert closes, or ``None`` when no closing date was advertised."""
        if self.closing_date is None:
            return None
        return (self.closing_date - timezone.localdate()).days


class JobRevision(models.Model):
    """One field of one job changing between two crawls.

    It powers the Changed tab of a run, and it is the record of "the salary was different last
    week".
    """

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="revisions")
    crawl_run = models.ForeignKey(
        "crawler.CrawlRun", on_delete=models.SET_NULL, null=True, related_name="revisions"
    )
    field = models.CharField(max_length=32, choices=ChangeField.choices())
    value_before = models.TextField(blank=True)
    value_after = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [models.Index(fields=["job", "-changed_at"])]

    def __str__(self) -> str:
        """Return a short description of the change."""
        return f"{self.field} changed on job {self.job_id}"


class SavedJob(models.Model):
    """A job one candidate wants to come back to.

    ``job`` is a normal foreign key, because many candidates can save the same job.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by")
    tags = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True)
    saved_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-saved_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "job"], name="unique_saved_job_per_owner")
        ]
        indexes = [models.Index(fields=["owner"], name="jobs_savedjob_owner_idx")]

    def __str__(self) -> str:
        """Return a short description."""
        return f"Saved job {self.job_id} for user {self.owner_id}"


class Application(models.Model):
    """One candidate's progress on one vacancy.

    The pipeline board is built from these. Each person tracks their own status, even for the
    same job.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(
        max_length=20, choices=ApplicationStatus.choices(), default=ApplicationStatus.FOUND
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    response_at = models.DateTimeField(null=True, blank=True)
    next_action = models.CharField(max_length=300, blank=True)
    next_action_due = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    ghosted_flagged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "job"], name="unique_application_per_owner")
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["next_action_due"]),
            models.Index(fields=["owner", "status"], name="jobs_app_owner_status_idx"),
        ]

    def __str__(self) -> str:
        """Return a short description."""
        return f"Application for job {self.job_id} by user {self.owner_id} ({self.status})"

    def is_ghosted(self, *, now: datetime) -> bool:
        """Whether this has stayed at ``APPLIED`` past the ghosting window with no reply.

        The current time is passed in, so the rule can be tested at the exact boundary.
        """
        return looks_ghosted(
            status=self.status,
            applied_at=self.applied_at,
            response_at=self.response_at,
            now=now,
        )


class ApplicationStatusEvent(models.Model):
    """Every transition, timestamped, so response rates can be analysed later."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="status_events"
    )
    from_status = models.CharField(max_length=20, choices=ApplicationStatus.choices(), blank=True)
    to_status = models.CharField(max_length=20, choices=ApplicationStatus.choices())
    occurred_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["occurred_at"]

    def __str__(self) -> str:
        """Return a short description."""
        return f"{self.from_status or '—'} → {self.to_status}"


class SavedSearch(models.Model):
    """A named filter set, optionally feeding the overnight digest."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=120)
    query = models.CharField(
        max_length=2000,
        blank=True,
        help_text="The URL query string from the job list, stored verbatim so a saved search "
        "and a bookmarked URL can never drift apart. Blank means "
        "'everything new', which is a legitimate thing to want in a digest.",
    )
    digest_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "saved searches"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"], name="unique_saved_search_name_per_owner"
            )
        ]

    def __str__(self) -> str:
        """Return the search name."""
        return self.name
