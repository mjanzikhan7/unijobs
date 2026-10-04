"""The overnight digest email.

The main rule: **no empty digests**. An email that says "nothing today" teaches people to
ignore us, and then they ignore the one that matters. If every section is empty, nothing is
sent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from urllib.parse import parse_qs

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q, QuerySet
from django.utils import timezone

from jobs.enums import ApplicationStatus, JobStatus
from jobs.models import Application, Job, SavedSearch

logger = logging.getLogger(__name__)


@dataclass
class DigestContent:
    """What the digest has to say today."""

    new_matches: list[tuple[str, list[Job]]] = field(default_factory=list)
    closing_soon: list[Job] = field(default_factory=list)
    actions_due: list[Application] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        """Whether there is nothing worth an email."""
        return not (self.new_matches or self.closing_soon or self.actions_due)


def build_digest(*, owner: object, today: date | None = None) -> DigestContent:
    """Build one candidate's digest sections.

    ``owner`` is required. A digest built across everybody would send one person another
    person's shortlist.
    """
    today = today or timezone.localdate()
    horizon = today + timedelta(days=settings.DIGEST_CLOSING_SOON_DAYS)

    content = DigestContent()

    for search in SavedSearch.objects.filter(digest_enabled=True, owner=owner):
        matches = list(_jobs_for_saved_search(search)[:20])
        if matches:
            content.new_matches.append((search.name, matches))

    content.closing_soon = list(
        Job.objects.filter(
            saved_by__owner=owner,
            status=JobStatus.OPEN,
            closing_date__gte=today,
            closing_date__lte=horizon,
        )
        .select_related("institution")
        .order_by("closing_date")
    )

    content.actions_due = list(
        Application.objects.filter(owner=owner, next_action_due__lte=today)
        .exclude(status__in=[ApplicationStatus.REJECTED, ApplicationStatus.OFFER])
        .select_related("job", "job__institution")
        .order_by("next_action_due")
    )

    return content


def _jobs_for_saved_search(search: SavedSearch) -> QuerySet[Job]:
    """Return new jobs that match a saved search since it last ran.

    The saved query is the job list's URL query string, run through the API's own filter set, so a
    saved search and a bookmarked URL always agree.
    """
    from api.filters import JobFilter

    since = search.last_run_at or timezone.now() - timedelta(days=1)
    params = {key: values[0] for key, values in parse_qs(search.query).items() if values}
    queryset = Job.objects.filter(first_seen_at__gte=since).with_related(for_user=search.owner)
    return JobFilter(params, queryset=queryset).qs


def render_digest(content: DigestContent) -> tuple[str, str]:
    """Render the digest to ``(subject, body)`` as plain text."""
    lines: list[str] = []

    for name, jobs in content.new_matches:
        lines.append(f"New for “{name}” ({len(jobs)})")
        for job in jobs:
            screening = getattr(job, "screening", None)
            badges = (
                f"[{screening.sponsor_verdict} · {screening.threshold_verdict}]"
                if screening
                else "[unscreened]"
            )
            lines.append(f"  · {job.title} — {job.institution.name} {badges}")
            lines.append(f"    {job.source_url}")
        lines.append("")

    if content.closing_soon:
        lines.append(f"Saved jobs closing soon ({len(content.closing_soon)})")
        for job in content.closing_soon:
            lines.append(f"  · {job.closing_date:%d %b} — {job.title}, {job.institution.name}")
        lines.append("")

    if content.actions_due:
        lines.append(f"Actions due ({len(content.actions_due)})")
        for application in content.actions_due:
            lines.append(
                f"  · {application.next_action_due:%d %b} — "
                f"{application.next_action or 'Follow up'}"
                f" ({application.job.title}, {application.job.institution.name})"
            )
        lines.append("")

    total = sum(len(jobs) for _, jobs in content.new_matches)
    subject = f"HE jobs: {total} new, {len(content.closing_soon)} closing soon"
    return subject, "\n".join(lines).strip()


def send_digest_email(*, today: date | None = None) -> dict[str, object]:
    """Send each candidate their own digest, and skip anyone with nothing new.

    One email per person, sent to their own account address.
    """
    if not settings.DIGEST_ENABLED:
        return {"sent": False, "reason": "digest disabled"}

    User = get_user_model()
    recipients = (
        User.objects.filter(is_active=True)
        .filter(
            Q(saved_searches__digest_enabled=True)
            | Q(saved_jobs__isnull=False)
            | Q(applications__isnull=False)
        )
        .distinct()
    )

    sent = 0
    totals = {"new_matches": 0, "closing_soon": 0, "actions_due": 0}

    for user in recipients:
        if not user.email:
            logger.info("digest skipped for %s: no email address", user.pk)
            continue

        content = build_digest(owner=user, today=today)
        if content.is_empty:
            continue

        subject, body = render_digest(content)
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        SavedSearch.objects.filter(digest_enabled=True, owner=user).update(
            last_run_at=timezone.now()
        )

        sent += 1
        totals["new_matches"] += sum(len(jobs) for _, jobs in content.new_matches)
        totals["closing_soon"] += len(content.closing_soon)
        totals["actions_due"] += len(content.actions_due)

    if not sent:
        logger.info("digest skipped: nothing to report for anyone")
        return {"sent": False, "reason": "nothing to report"}

    return {"sent": True, "recipients": sent, **totals}
