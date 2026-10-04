"""``manage.py seed_demo_jobs``: load a small fixed set of vacancies for demos and browser tests.

The browser tests need vacancies on screen, and crawling forty universities for them would be
slow, unreliable and impolite.

The adverts are awkward on purpose: one rules sponsorship out in the text, one has no figures,
one gives only a top figure, one is part-time. They go through the real screening code, so the
badges are real.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from institutions.models import Institution
from jobs.models import Job
from screening.services import NoActiveRuleset, screen_jobs

FIXTURE = Path(__file__).resolve().parents[2] / "seeds" / "demo_jobs.json"


class Command(BaseCommand):
    """Load demo vacancies and screen them."""

    help = "Load a small fixed set of vacancies for demos and end-to-end tests. Safe to re-run."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Accept an alternative fixture path."""
        parser.add_argument(
            "--fixture",
            type=Path,
            default=FIXTURE,
            help=f"JSON file to load. Defaults to {FIXTURE.name}.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Upsert every row in the fixture, then screen the lot."""
        path: Path = options["fixture"]
        if not path.exists():
            raise CommandError(f"No such fixture: {path}")

        rows: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        today = timezone.localdate()

        created = 0
        updated = 0
        jobs: list[Job] = []

        for row in rows:
            slug = row["institution_slug"]
            try:
                institution = Institution.objects.get(slug=slug)
            except Institution.DoesNotExist:
                raise CommandError(f"Unknown institution {slug!r}. Run seed_all first.") from None

            posted = today - timedelta(days=int(row["posted_days_ago"]))
            closing = today + timedelta(days=int(row["closes_in_days"]))

            job, was_created = Job.objects.update_or_create(
                institution=institution,
                source_url=row["source_url"],
                defaults={
                    "title": row["title"],
                    "department": row.get("department", ""),
                    "reference": row.get("reference", ""),
                    "description_text": row.get("description_text", ""),
                    "location_raw": row.get("location_raw", ""),
                    "city": row.get("city", ""),
                    "salary_raw": row.get("salary_raw", ""),
                    "grade_raw": row.get("grade_raw", ""),
                    "contract_type": row.get("contract_type", "UNKNOWN"),
                    "hours": row.get("hours", "UNKNOWN"),
                    "workplace": row.get("workplace", "UNKNOWN"),
                    "posted_date": posted,
                    "closing_date": closing,
                    "status": "OPEN",
                    "last_seen_at": timezone.now(),
                },
            )
            jobs.append(job)
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(f"jobs: {created} created, {updated} updated")

        try:
            counts = screen_jobs(jobs)
        except NoActiveRuleset:
            raise CommandError(
                "No active ruleset, so these jobs would carry no verdicts. Run seed_all first."
            ) from None

        self.stdout.write(
            f"screening: {counts['screened']} screened, {counts['changed']} verdicts changed"
        )
        self.stdout.write(self.style.SUCCESS("demo jobs loaded"))
