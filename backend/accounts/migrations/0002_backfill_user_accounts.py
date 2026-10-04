"""Give every pre-existing user an account row.

The signal only fires for users created after it was installed, so the accounts that already
exist — the operator's own superuser among them — would otherwise resolve to CANDIDATE and lose
access to the console.
"""

from __future__ import annotations

from typing import Any

from django.db import migrations

# Literals rather than `accounts.enums.Role`, so renaming a member later cannot rewrite what this
# migration did when it ran.
_ADMIN = "ADMIN"
_CANDIDATE = "CANDIDATE"


def create_accounts(apps: Any, schema_editor: Any) -> None:
    """Create one account per user, admins for superusers."""
    User = apps.get_model("auth", "User")
    UserAccount = apps.get_model("accounts", "UserAccount")

    UserAccount.objects.bulk_create(
        [
            UserAccount(user=user, role=_ADMIN if user.is_superuser else _CANDIDATE)
            for user in User.objects.filter(account__isnull=True)
        ]
    )


def drop_accounts(apps: Any, schema_editor: Any) -> None:
    """Remove every account row, so the migration is reversible."""
    apps.get_model("accounts", "UserAccount").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [migrations.RunPython(create_accounts, drop_accounts)]
