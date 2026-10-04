"""Give candidate profiles an owner, and make "one active profile" mean one per person.

The old constraint was global — the clearest single expression of the single-user assumption
this phase removes. A second candidate saving a profile would have hit a database error.
"""

from __future__ import annotations

from typing import Any

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from jobs.migrations._0004_helpers import sole_owner


def assign_owner(apps: Any, schema_editor: Any) -> None:
    """Point existing profiles at the sole account. Refuses to guess between several."""
    CandidateProfile = apps.get_model("screening", "CandidateProfile")
    if not CandidateProfile.objects.exists():
        return

    CandidateProfile.objects.filter(owner__isnull=True).update(owner=sole_owner(apps))


def clear_owner(apps: Any, schema_editor: Any) -> None:
    """Drop the owner again, so the migration reverses cleanly."""
    apps.get_model("screening", "CandidateProfile").objects.update(owner=None)


def _owner_field(*, null: bool) -> models.ForeignKey:
    return models.ForeignKey(
        null=null,
        on_delete=django.db.models.deletion.CASCADE,
        related_name="candidate_profiles",
        to=settings.AUTH_USER_MODEL,
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("screening", "0002_order_candidate_profiles"),
    ]

    operations = [
        # Drop the global constraint first: with two owners each holding an active profile, it
        # would reject the very state this migration is creating.
        migrations.RemoveConstraint("candidateprofile", "only_one_active_profile"),
        migrations.AddField("candidateprofile", "owner", _owner_field(null=True)),
        migrations.RunPython(assign_owner, clear_owner),
        migrations.AlterField("candidateprofile", "owner", _owner_field(null=False)),
        migrations.AddConstraint(
            "candidateprofile",
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(is_active=True),
                name="one_active_profile_per_owner",
            ),
        ),
    ]
