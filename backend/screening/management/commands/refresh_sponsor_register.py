"""``manage.py refresh_sponsor_register``: download the GOV.UK register as a new snapshot.

The old snapshot is kept so the two can be compared. It is better to know an employer left the
register before a job offer, not after.
"""

from __future__ import annotations

import csv
import io
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import httpx
from django.core.management.base import BaseCommand, CommandError

from institutions.models import Institution
from screening.services import (
    compare_snapshots,
    latest_snapshot,
    load_register_snapshot,
    match_institution,
)

REGISTER_PAGE = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"


class Command(BaseCommand):
    """Load a new sponsor-register snapshot and report what changed."""

    help = "Download or load the GOV.UK sponsor register as a new snapshot and re-run matching."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Accept a local CSV or a URL."""
        parser.add_argument("--file", type=Path, help="Load a CSV already on disk.")
        parser.add_argument("--url", help="Download the CSV from this URL.")
        parser.add_argument(
            "--skip-rematch",
            action="store_true",
            help="Load the snapshot without re-running institution matching.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Load the register, then re-match every institution against it."""
        previous = latest_snapshot()

        if options["file"]:
            path: Path = options["file"]
            if not path.exists():
                raise CommandError(f"{path} does not exist")
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            source = str(path)
        elif options["url"]:
            source = options["url"]
            self.stdout.write(f"downloading {source} …")
            response = httpx.get(source, timeout=120.0, follow_redirects=True)
            response.raise_for_status()
            text = response.text
        else:
            raise CommandError(
                "Pass --file or --url. The current CSV is linked from " + REGISTER_PAGE
            )

        rows = list(csv.DictReader(io.StringIO(text)))
        snapshot = load_register_snapshot(rows, source_url=source)
        self.stdout.write(self.style.SUCCESS(f"loaded {snapshot.row_count} register rows"))

        if not options["skip_rematch"]:
            reviewed = 0
            for institution in Institution.objects.all():
                match = match_institution(institution, snapshot)
                reviewed += int(match.needs_review)
            self.stdout.write(f"re-matched every institution; {reviewed} need review")

        if previous is not None:
            changes = compare_snapshots(previous, snapshot)
            for name in changes["dropped_off"]:
                self.stdout.write(self.style.ERROR(f"DROPPED OFF THE REGISTER: {name}"))
            for name in changes["newly_listed"]:
                self.stdout.write(self.style.SUCCESS(f"newly listed: {name}"))
            if not changes["dropped_off"] and not changes["newly_listed"]:
                self.stdout.write("no matched employer changed status since the last snapshot")
