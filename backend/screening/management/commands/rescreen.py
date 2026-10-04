"""``manage.py rescreen``: recalculate every verdict against the active ruleset.

No network calls. It only uses stored data, so a rule change does not need a new crawl.
"""

from __future__ import annotations

import time
from typing import Any

from django.core.management.base import BaseCommand

from screening.services import active_ruleset, rescreen_all


class Command(BaseCommand):
    """Re-screen the whole corpus."""

    help = "Recompute every job's verdicts against the active ruleset. No network calls."

    def handle(self, *args: Any, **options: Any) -> None:
        """Re-screen and report how many verdicts moved."""
        ruleset = active_ruleset()
        started = time.monotonic()
        counts = rescreen_all(ruleset)
        elapsed = time.monotonic() - started

        self.stdout.write(
            self.style.SUCCESS(
                f"re-screened {counts['screened']} jobs against ruleset v{ruleset.version} "
                f"in {elapsed:.1f}s; {counts['changed']} verdicts changed"
            )
        )
