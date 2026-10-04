"""Housekeeping on accounts."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="accounts.tasks.prune_unverified_accounts")
def prune_unverified_accounts() -> int:
    """Delete accounts that never confirmed their address, and return how many.

    Otherwise anyone could hold every good username by signing up and never confirming. Deleting
    is safe: the account was never usable, and signing up again is easy.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.contrib.auth.models import User
    from django.utils import timezone

    cutoff = timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS)
    stale = User.objects.filter(
        is_active=False,
        account__email_verified_at__isnull=True,
        date_joined__lt=cutoff,
    )
    count = stale.count()
    if count:
        stale.delete()
        logger.info("pruned %s unverified account(s)", count)
    return count
