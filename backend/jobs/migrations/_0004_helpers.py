"""Owner resolution for the multi-tenancy backfill.

Lives beside the migration rather than inside it so the rule can be tested directly. Named with a
leading underscore so Django's migration loader ignores it.

The rule exists because the alternative — ``User.objects.first()`` — hands one person's saved
jobs and application history to another, silently, with no way to tell afterwards.
"""

from __future__ import annotations

from typing import Any


class AmbiguousOwner(RuntimeError):
    """Raised when the existing rows cannot be attributed to exactly one account."""


def sole_owner(apps: Any) -> Any:
    """Return the one account existing rows must belong to, or refuse.

    A single superuser wins; failing that, a single user of any kind. Anything else is a guess.
    """
    User = apps.get_model("auth", "User")

    superusers = list(User.objects.filter(is_superuser=True).order_by("pk")[:2])
    if len(superusers) == 1:
        return superusers[0]

    users = list(User.objects.order_by("pk")[:2])
    if len(users) == 1:
        return users[0]

    raise AmbiguousOwner(
        f"Cannot decide who owns the existing rows: found {len(superusers)} superuser(s) and "
        f"{User.objects.count()} user(s). Set the owner by hand before migrating."
    )
