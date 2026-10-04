"""Move fitness off the screening row and onto a per-candidate one.

The existing scores are worth carrying over rather than recomputing: they belong to the operator
whose profile produced them, and re-scoring an estate of thousands of jobs at migration time
would make this migration arbitrarily slow.
"""

from __future__ import annotations

from typing import Any

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

from jobs.migrations._0004_helpers import AmbiguousOwner, sole_owner


def copy_existing_scores(apps: Any, schema_editor: Any) -> None:
    """Carry each screening row's score over to its owner's fitness row."""
    JobScreening = apps.get_model("screening", "JobScreening")
    JobFitness = apps.get_model("screening", "JobFitness")

    scored = JobScreening.objects.exclude(fitness_score=0)
    if not scored.exists():
        return

    try:
        owner = sole_owner(apps)
    except AmbiguousOwner:
        # Several accounts and no way to say whose profile produced these. Dropping them is
        # safe: a score is derived data, and `rescreen` recomputes it per candidate on demand.
        return

    JobFitness.objects.bulk_create(
        [
            JobFitness(
                job_id=row.job_id,
                owner=owner,
                score=row.fitness_score,
                reasons=row.fitness_reasons,
                scored_at=row.screened_at,
            )
            for row in scored.iterator()
        ],
        batch_size=500,
    )


def restore_scores(apps: Any, schema_editor: Any) -> None:
    """Put the scores back on the screening rows, so the migration reverses."""
    JobScreening = apps.get_model("screening", "JobScreening")
    for fitness in apps.get_model("screening", "JobFitness").objects.iterator():
        JobScreening.objects.filter(job_id=fitness.job_id).update(
            fitness_score=fitness.score, fitness_reasons=fitness.reasons
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("screening", "0003_profile_ownership"),
        ("jobs", "0004_multi_tenant_ownership"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobFitness",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("reasons", models.JSONField(blank=True, default=list)),
                ("criteria_hash", models.CharField(blank=True, max_length=64)),
                ("scored_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fitness",
                        to="jobs.job",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="job_fitness",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name_plural": "job fitness"},
        ),
        migrations.AddConstraint(
            "jobfitness",
            models.UniqueConstraint(fields=["owner", "job"], name="unique_fitness_per_owner_job"),
        ),
        migrations.AddIndex(
            "jobfitness",
            models.Index(fields=["owner", "-score"], name="screening_fit_owner_score_idx"),
        ),
        # Copy before dropping, so nothing is lost between the two.
        migrations.RunPython(copy_existing_scores, restore_scores),
        migrations.RemoveIndex("jobscreening", "screening_j_fitness_aa4c9c_idx"),
        migrations.RemoveField("jobscreening", "fitness_score"),
        migrations.RemoveField("jobscreening", "fitness_reasons"),
    ]
