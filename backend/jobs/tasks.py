"""Scheduled work on the job and application side."""

from __future__ import annotations

from typing import Any

from celery import shared_task


@shared_task(name="jobs.tasks.flag_ghosted_applications")
def flag_ghosted_applications() -> int:
    """Flag applications that have sat unanswered past the ghosting window."""
    from jobs.services import flag_ghosted

    return flag_ghosted()


@shared_task(name="jobs.tasks.refresh_search_vectors")
def refresh_search_vectors_task() -> int:
    """Rebuild the full-text index across the corpus."""
    from jobs.services import refresh_search_vectors

    return refresh_search_vectors()


@shared_task(name="jobs.tasks.send_digest")
def send_digest() -> dict[str, Any]:
    """Assemble and send the overnight digest."""
    from jobs.digest import send_digest_email

    return send_digest_email()
