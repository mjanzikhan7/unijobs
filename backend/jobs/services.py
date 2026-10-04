"""Job use cases: search indexing, manual entry, application status changes.

Search uses a PostgreSQL ``search_vector`` that is updated when a job is saved, not at search
time. Building it for 5,000 descriptions on every request would be about ten times slower.
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils import timezone

from institutions.models import Institution
from jobs.domain import classify_discipline, looks_ghosted
from jobs.enums import ApplicationStatus, JobSource, JobStatus
from jobs.models import Application, ApplicationStatusEvent, Job

logger = logging.getLogger(__name__)

_RECLASSIFY_BATCH_SIZE = 500

_INSTITUTION_NAME = Subquery(
    Institution.objects.filter(pk=OuterRef("institution_id")).values("name")[:1]
)

SEARCH_VECTOR = (
    SearchVector("title", weight="A", config="english")
    + SearchVector("department", weight="B", config="english")
    + SearchVector(_INSTITUTION_NAME, weight="B", config="english")
    + SearchVector("description_text", weight="D", config="english")
)


def refresh_search_vectors(jobs: QuerySet[Job] | None = None) -> int:
    """Recompute the full-text index for ``jobs``, or for everything."""
    queryset = jobs if jobs is not None else Job.objects.all()
    return queryset.update(search_vector=SEARCH_VECTOR)


def reclassify_disciplines(jobs: QuerySet[Job] | None = None) -> dict[str, int]:
    """Work out the discipline again for ``jobs``, or for every job.

    A crawl already does this for new jobs. This is for older rows, and for rows that are out of
    date after the keyword rules change. All the inputs are on the row, so there are no network
    calls.
    """
    queryset = jobs if jobs is not None else Job.objects.all()
    total = 0
    changed = 0
    batch: list[Job] = []
    for job in queryset.only("id", "title", "category", "department", "discipline").iterator():
        total += 1
        discipline = classify_discipline(job.title, job.category, job.department)
        if discipline != job.discipline:
            job.discipline = discipline
            batch.append(job)
            changed += 1
        if len(batch) >= _RECLASSIFY_BATCH_SIZE:
            Job.objects.bulk_update(batch, ["discipline"])
            batch.clear()
    if batch:
        Job.objects.bulk_update(batch, ["discipline"])
    return {"classified": total, "changed": changed}


@transaction.atomic
def add_manual_job(
    *,
    institution_id: int,
    source_url: str,
    title: str,
    **fields: object,
) -> Job:
    """Save a job that the crawler cannot reach.

    Marked ``source = MANUAL``. A crawl never closes a manual job, because it was never part of
    the crawl. Everywhere else it looks the same: same badges, same search, same export.
    """
    job, _ = Job.objects.update_or_create(
        institution_id=institution_id,
        source_url=source_url,
        defaults={
            "source": JobSource.MANUAL,
            "title": title,
            "status": JobStatus.OPEN,
            "last_seen_at": timezone.now(),
            **fields,
        },
    )
    refresh_search_vectors(Job.objects.filter(pk=job.pk))
    return job


class CannotDeleteCrawledJob(RuntimeError):
    """Hard-deleting a crawled job would only invite the next crawl to recreate it."""


@transaction.atomic
def withdraw_job(job: Job, *, by: User | None, reason: str = "") -> Job:
    """Take a job down, and record who did it and why.

    ``WITHDRAWN``, not ``DISAPPEARED``. ``DISAPPEARED`` only means "not found by a successful
    crawl". Keeping them apart stops an admin's decision looking like a crawl result.
    """
    job.status = JobStatus.WITHDRAWN
    job.withdrawn_at = timezone.now()
    job.withdrawn_by = by
    job.withdrawn_reason = reason[:300]
    job.save(update_fields=["status", "withdrawn_at", "withdrawn_by", "withdrawn_reason"])
    return job


@transaction.atomic
def reinstate_job(job: Job) -> Job:
    """Undo a withdrawal.

    The job goes back to ``OPEN``. If the advert is really gone, the next successful crawl will
    close it in the normal way.
    """
    job.status = JobStatus.OPEN
    job.withdrawn_at = None
    job.withdrawn_by = None
    job.withdrawn_reason = ""
    job.save(update_fields=["status", "withdrawn_at", "withdrawn_by", "withdrawn_reason"])
    return job


def delete_job(job: Job) -> None:
    """Delete a manually added job. Refuses for a crawled job.

    A crawled job is still on the employer's site, so the next crawl would add it again as new,
    and its history and every saved copy would be lost. Withdraw a crawled job instead.
    """
    if job.source != JobSource.MANUAL:
        raise CannotDeleteCrawledJob(
            "This job came from a crawl, so deleting it would only last until the next one. "
            "Withdraw it instead."
        )
    job.delete()


@transaction.atomic
def transition_application(
    application: Application,
    *,
    to_status: ApplicationStatus,
    note: str = "",
    now: datetime | None = None,
) -> Application:
    """Move an application and record the change.

    Each move has a timestamp, so we can later see how long employers take to reply.
    """
    moment = now or timezone.now()
    previous = application.status

    if previous == to_status:
        return application

    ApplicationStatusEvent.objects.create(
        application=application,
        from_status=previous,
        to_status=to_status,
        occurred_at=moment,
        note=note,
    )

    application.status = to_status
    if to_status == ApplicationStatus.APPLIED and application.applied_at is None:
        application.applied_at = moment
    if to_status in (
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
    ):
        application.response_at = application.response_at or moment
        application.ghosted_flagged = False
    application.save()
    return application


def flag_ghosted(*, now: datetime | None = None) -> int:
    """Flag applications that have been quiet past the ghosting window.

    Only a flag, never a move. The candidate decides, and some employers reply late.
    """
    moment = now or timezone.now()
    flagged = 0
    candidates = Application.objects.filter(
        status=ApplicationStatus.APPLIED, response_at__isnull=True, ghosted_flagged=False
    )
    for application in candidates:
        if looks_ghosted(
            status=application.status,
            applied_at=application.applied_at,
            response_at=application.response_at,
            now=moment,
        ):
            application.ghosted_flagged = True
            application.save(update_fields=["ghosted_flagged"])
            flagged += 1
    return flagged
