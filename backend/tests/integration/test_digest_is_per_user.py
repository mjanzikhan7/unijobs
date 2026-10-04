"""The digest is one email per candidate, containing only their own rows.

The old digest read every saved search and every saved job in the database and sent the result to
a single configured address. With two candidates that is one person's shortlist mailed to
another.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.utils import timezone

from jobs.digest import build_digest, send_digest_email
from screening.models import Ruleset
from tests.factories import ApplicationFactory, JobFactory, SavedJobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


def _saved_job_closing_soon(owner: Any, ruleset: Ruleset, title: str) -> None:
    job = JobFactory(title=title, closing_date=timezone.localdate() + timedelta(days=3))
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(owner=owner, job=job)


def test_each_candidate_gets_their_own_email(
    candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    _saved_job_closing_soon(candidate_user, ruleset, "Lecturer in Physics")
    _saved_job_closing_soon(second_candidate_user, ruleset, "Research Software Engineer")

    send_digest_email()

    assert len(mail.outbox) == 2
    by_recipient = {message.to[0]: message.body for message in mail.outbox}
    assert "Lecturer in Physics" in by_recipient[candidate_user.email]
    assert "Research Software Engineer" not in by_recipient[candidate_user.email]


def test_a_candidate_with_nothing_to_report_gets_no_email(
    candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """The no-empty-digests rule, now applied per person rather than globally."""
    _saved_job_closing_soon(candidate_user, ruleset, "Lecturer in Physics")

    send_digest_email()

    assert [message.to[0] for message in mail.outbox] == [candidate_user.email]


def test_a_digest_never_contains_another_users_actions(
    candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    job = JobFactory(title="Chase this one")
    ScreeningFactory(job=job, ruleset=ruleset)
    ApplicationFactory(
        owner=second_candidate_user,
        job=job,
        status="APPLIED",
        next_action="Chase HR",
        next_action_due=timezone.localdate(),
    )

    content = build_digest(owner=candidate_user)

    assert content.actions_due == []


def test_sending_marks_only_that_users_searches_as_run(
    candidate_user: Any, second_candidate_user: Any, ruleset: Ruleset
) -> None:
    """A global `last_run_at` bump would make the other candidate silently miss a window."""
    from tests.factories import SavedSearchFactory

    mine = SavedSearchFactory(owner=candidate_user, name="Mine", query="")
    theirs = SavedSearchFactory(
        owner=second_candidate_user, name="Theirs", query="q=nothingmatchesthis"
    )
    job = JobFactory()
    ScreeningFactory(job=job, ruleset=ruleset)
    SavedJobFactory(owner=candidate_user, job=job)

    send_digest_email()

    mine.refresh_from_db()
    theirs.refresh_from_db()
    assert mine.last_run_at is not None
    assert theirs.last_run_at is None


def test_a_user_without_an_email_address_is_skipped(candidate_user: Any, ruleset: Ruleset) -> None:
    """No address is a reason to skip, not to crash the whole run."""
    candidate_user.email = ""
    candidate_user.save(update_fields=["email"])
    _saved_job_closing_soon(candidate_user, ruleset, "Lecturer in Physics")

    result = send_digest_email()

    assert mail.outbox == []
    assert result["sent"] is False
