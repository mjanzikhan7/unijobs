"""Reading and setting a user's role.

Every read goes through :func:`role_of`, so "no account row" has one answer in one place.
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from accounts.enums import Role
from accounts.models import UserAccount

logger = logging.getLogger(__name__)


def role_of(user: AbstractBaseUser | AnonymousUser | None) -> Role | None:
    """Return the user's role, or ``None`` if there is no user.

    A missing account row gives ``CANDIDATE``, the role with the fewest rights. ``accounts.checks``
    warns about missing rows at startup.
    """
    if user is None or not user.is_authenticated:
        return None

    account: UserAccount | None = getattr(user, "account", None)
    if account is None:
        logger.error("user %s has no UserAccount; treating as CANDIDATE", user.pk)
        return Role.CANDIDATE

    return Role(account.role)


def ensure_account(user: AbstractBaseUser, *, role: Role | None = None) -> UserAccount:
    """Return the user's account row, and create it if the signal did not.

    The role is ``ADMIN`` for superusers and ``CANDIDATE`` for everyone else. It is never read from
    a request, so sign-up cannot give itself more rights.
    """
    resolved = role or (Role.ADMIN if getattr(user, "is_superuser", False) else Role.CANDIDATE)
    account, _ = UserAccount.objects.get_or_create(user=user, defaults={"role": resolved})
    return account


def backfill_missing_accounts() -> int:
    """Create account rows for users that have none, and return how many were made."""
    from django.contrib.auth import get_user_model

    missing = get_user_model().objects.filter(account__isnull=True)
    created = [ensure_account(user) for user in missing]
    return len(created)
