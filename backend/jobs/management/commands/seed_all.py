"""``manage.py seed_all`` - load everything a fresh database needs, idempotently."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from institutions.seeds.loader import seed_institutions
from screening.seeds.loader import seed_ruleset, seed_skill_terms, seed_sponsor_matches


class Command(BaseCommand):
    """Seed institutions, the current ruleset and known sponsor matches."""

    help = "Load institutions, the current ruleset and known sponsor matches. Safe to re-run."

    def handle(self, *args: Any, **options: Any) -> None:
        """Run every seeder in dependency order."""
        result = seed_institutions()
        self.stdout.write(
            f"institutions: {result.created} created, {result.updated} updated, "
            f"{result.unchanged} unchanged ({result.total} total)"
        )

        ruleset, created = seed_ruleset()
        verb = "created" if created else "already present"
        self.stdout.write(f"ruleset: v{ruleset.version} {verb} — {ruleset.name}")

        counts = seed_sponsor_matches()
        self.stdout.write(
            f"sponsor matches: {counts['seeded']} seeded, "
            f"{counts['needs_review']} queued for review, {counts['skipped']} skipped"
        )
        terms = seed_skill_terms()
        self.stdout.write(
            f"cv vocabulary: {terms['created']} created, {terms['updated']} updated "
            f"({terms['total']} total)"
        )
        self.stdout.write(self.style.SUCCESS("seed complete"))
