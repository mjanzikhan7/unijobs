"""Writing a crawl's changes to the database: new jobs, changed fields, closed jobs.

See ``crawler.services`` for the full crawl of one institution. ``persistence.py`` is a
different thing: it records HTTP responses.
"""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from crawler.differ import DiffResult, ExistingJob, field_changes, vacancy_content_hash
from crawler.models import CrawlRun
from crawler.types import RawVacancy
from institutions.models import Institution
from jobs.domain import (
    classify_contract_type,
    classify_discipline,
    classify_hours,
    classify_workplace,
)
from jobs.enums import ChangeField, JobSource, JobStatus
from jobs.models import Job, JobRevision


def existing_jobs_for(institution: Institution) -> list[ExistingJob]:
    """Load the stored jobs the differ compares against."""
    return [
        ExistingJob(
            job_id=job.pk,
            source_url=job.source_url,
            content_hash=job.content_hash,
            status=job.status,
            title=job.title,
            salary_raw=job.salary_raw,
            closing_date=job.closing_date,
            location_raw=job.location_raw,
            is_manual=job.source == JobSource.MANUAL,
            is_withdrawn=job.status == JobStatus.WITHDRAWN,
        )
        for job in institution.jobs.all().only(
            "id",
            "source_url",
            "content_hash",
            "status",
            "title",
            "salary_raw",
            "closing_date",
            "location_raw",
            "source",
        )
    ]


@transaction.atomic
def apply_diff(run: CrawlRun, institution: Institution, diff: DiffResult) -> tuple[int, int, int]:
    """Write a diff to the database. Returns ``(new, updated, closed)``."""
    now = timezone.now()

    created = 0
    for vacancy in diff.new:
        _upsert_job(institution, vacancy, now=now)
        created += 1

    updated = 0
    for vacancy, stored in diff.updated:
        job = _upsert_job(institution, vacancy, now=now)
        for change in field_changes(vacancy, stored):
            JobRevision.objects.create(
                job=job,
                crawl_run=run,
                field=ChangeField(change.field),
                value_before=change.before,
                value_after=change.after,
                changed_at=now,
            )
        updated += 1

    for vacancy, _stored in diff.unchanged:
        _upsert_job(institution, vacancy, now=now)

    closed = 0
    if diff.disappeared:
        closed = Job.objects.filter(pk__in=[job.job_id for job in diff.disappeared]).update(
            status=JobStatus.DISAPPEARED, disappeared_at=now
        )

    return created, updated, closed


def _upsert_job(institution: Institution, vacancy: RawVacancy, *, now: datetime) -> Job:
    """Create or update one job, keyed by ``(institution, source_url)``.

    Safe to repeat: crawling the same unchanged content twice gives the same row and the same
    ``content_hash``, so nothing is updated.
    """
    description_text = vacancy.description_text or ""
    combined = " ".join(filter(None, [vacancy.contract_raw, vacancy.hours_raw, description_text]))

    job, _ = Job.objects.update_or_create(
        institution=institution,
        source_url=vacancy.source_url,
        defaults={
            "source": JobSource.PORTAL,
            "title": vacancy.title[:500],
            "department": vacancy.department[:300],
            "category": vacancy.category[:200],
            "reference": vacancy.reference[:120],
            "description_html": vacancy.description_html,
            "description_text": description_text,
            "location_raw": vacancy.location_raw[:300],
            "salary_raw": vacancy.salary_raw[:500],
            "grade_raw": vacancy.grade_raw[:120],
            "contract_raw": vacancy.contract_raw[:200],
            "hours_raw": vacancy.hours_raw[:200],
            "contract_type": classify_contract_type(vacancy.contract_raw or combined),
            "hours": classify_hours(vacancy.hours_raw or combined),
            "workplace": classify_workplace(combined),
            "discipline": classify_discipline(vacancy.title, vacancy.category, vacancy.department),
            "posted_date": vacancy.posted_date,
            "closing_date": vacancy.closing_date,
            "status": JobStatus.OPEN,
            "disappeared_at": None,
            "last_seen_at": now,
            "content_hash": vacancy_content_hash(vacancy),
        },
    )
    return job
