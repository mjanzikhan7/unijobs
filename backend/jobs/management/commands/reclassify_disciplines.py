"""``manage.py reclassify_disciplines``: work out every job's discipline again.

No network calls. A crawl does this for new jobs. This covers older rows, and rows that are out
of date after the keyword rules change.
"""

from __future__ import annotations

import time
from typing import Any

from django.core.management.base import BaseCommand

from jobs.services import reclassify_disciplines


class Command(BaseCommand):
    """Reclassify the whole corpus onto the current discipline taxonomy."""

    help = "Recompute every job's discipline from its title, category and department."

    def handle(self, *args: Any, **options: Any) -> None:
        """Reclassify and report how many changed."""
        started = time.monotonic()
        counts = reclassify_disciplines()
        elapsed = time.monotonic() - started

        self.stdout.write(
            self.style.SUCCESS(
                f"reclassified {counts['classified']} jobs in {elapsed:.1f}s; "
                f"{counts['changed']} disciplines changed"
            )
        )
