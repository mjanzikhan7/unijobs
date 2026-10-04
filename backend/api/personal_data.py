"""Everything this service holds about one person, as plain data.

Used by the export endpoint, so a person can see and keep a copy of their data
(UK GDPR, articles 15 and 20). When a new model gets an `owner`, add it here too.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone

from accounts.services import ensure_account
from analytics.models import AnalyticsEvent
from jobs.models import Application, SavedJob, SavedSearch
from screening.models import CV, CandidateProfile

EXPORT_FORMAT_VERSION = 1


def _job_summary(job: Any) -> dict[str, Any]:
    return {
        "id": job.pk,
        "title": job.title,
        "institution": job.institution.name,
        "url": job.source_url,
    }


def export_personal_data(user: User) -> dict[str, Any]:
    """Return one person's data as a dictionary that can be written as JSON."""
    account = ensure_account(user)

    saved_jobs = SavedJob.objects.filter(owner=user).select_related("job__institution")
    applications = (
        Application.objects.filter(owner=user)
        .select_related("job__institution")
        .prefetch_related("status_events")
    )

    return {
        "format_version": EXPORT_FORMAT_VERSION,
        "exported_at": timezone.now().isoformat(),
        "account": {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": account.role,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "email_verified_at": (
                account.email_verified_at.isoformat() if account.email_verified_at else None
            ),
            "pending_email": account.pending_email,
        },
        "saved_jobs": [
            {
                "job": _job_summary(saved.job),
                "tags": saved.tags,
                "note": saved.note,
                "saved_at": saved.saved_at.isoformat(),
            }
            for saved in saved_jobs
        ],
        "applications": [
            {
                "job": _job_summary(application.job),
                "status": application.status,
                "applied_at": _iso(application.applied_at),
                "response_at": _iso(application.response_at),
                "next_action": application.next_action,
                "next_action_due": _iso(application.next_action_due),
                "notes": application.notes,
                "history": [
                    {
                        "from_status": event.from_status,
                        "to_status": event.to_status,
                        "occurred_at": event.occurred_at.isoformat(),
                        "note": event.note,
                    }
                    for event in application.status_events.all()
                ],
            }
            for application in applications
        ],
        "saved_searches": list(
            SavedSearch.objects.filter(owner=user).values(
                "name", "query", "digest_enabled", "created_at", "last_run_at"
            )
        ),
        "candidate_profiles": list(
            CandidateProfile.objects.filter(owner=user).values(
                "name",
                "skills",
                "domains",
                "seniority",
                "projects",
                "education",
                "years_experience",
                "is_active",
                "updated_at",
            )
        ),
        "cvs": list(
            CV.objects.filter(owner=user).values(
                "original_filename",
                "content_type",
                "byte_size",
                "uploaded_at",
                "applied_at",
                "suggestions",
                "extracted_text",
            )
        ),
        "activity": list(
            AnalyticsEvent.objects.filter(actor=user).values(
                "kind", "occurred_at", "query", "category", "nation", "result_count"
            )
        ),
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None
