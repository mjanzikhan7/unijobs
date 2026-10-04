"""``manage.py export_static_site``: write the open vacancies as a static website.

Plain HTML, CSV and JSON with no JavaScript. Publish the folder on any static host.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from jobs.static_site import export_static_site


class Command(BaseCommand):
    """Export the static site."""

    help = "Write open vacancies as a static HTML, CSV and JSON site."

    def add_arguments(self, parser: Any) -> None:
        """Take the output folder."""
        parser.add_argument("--out", default="static-site", help="Folder to write to.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Write the site and report what was written."""
        result = export_static_site(Path(options["out"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {result.files} files: {result.jobs} jobs at "
                f"{result.institutions} institutions, in {options['out']}"
            )
        )
