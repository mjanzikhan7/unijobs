"""``manage.py refresh_fixtures``: capture the test pages again from the live sites.

The only command in the project that uses the real internet on purpose. No test runs it.
Adapters change, and their test pages must be able to follow a site that changed.

Two rules, printed at the end because they are easy to forget:

* **Read the diff before committing.** A test page that changed without anyone noticing can
  hide a real bug.
* **Remove anything personal.** Adverts can contain names, phone numbers and email addresses.
  They do not belong in git.
"""

from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from crawler.config import crawler_config
from crawler.exceptions import AdapterError
from crawler.services import build_http_client, institution_ref, probe_portal
from institutions.models import Institution

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "captured_pages"

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "redacted@example.ac.uk"),
    (re.compile(r"\+44\s?\(?0?\)?[\d\s-]{9,13}"), "+44 000 000 0000"),
    (re.compile(r"\b0\d{3}\s?\d{3}\s?\d{4}\b"), "0000 000 0000"),
    # API keys that a site embeds in its own pages, such as Google Maps.
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "REDACTED-API-KEY"),
)


def redact(html: str) -> str:
    """Remove the personal data a careers page routinely carries."""
    for pattern, replacement in _REDACTIONS:
        html = pattern.sub(replacement, html)
    return html


class Command(BaseCommand):
    """Re-capture HTML fixtures from live careers pages."""

    help = (
        "Capture careers pages from live sites into tests/fixtures/captured_pages/. "
        "Hits the real internet — run it deliberately, and review the diff."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Accept the institutions to capture."""
        parser.add_argument(
            "--slug",
            action="append",
            default=[],
            required=True,
            help="Institution to capture (repeatable). Required: this command is not a crawl.",
        )
        parser.add_argument(
            "--out",
            type=Path,
            default=FIXTURE_ROOT,
            help=f"Where to write. Defaults to {FIXTURE_ROOT}.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Capture each named institution's careers page."""
        slugs: list[str] = options["slug"]
        out_root: Path = options["out"]

        institutions = list(Institution.objects.filter(slug__in=slugs))
        missing = set(slugs) - {institution.slug for institution in institutions}
        if missing:
            raise CommandError(f"Unknown institutions: {sorted(missing)}")

        config = crawler_config()
        self.stdout.write(
            self.style.WARNING(
                f"Capturing {len(institutions)} live page(s) as {config.user_agent}."
            )
        )

        http = build_http_client()
        captured: list[Path] = []
        try:
            for institution in institutions:
                path = self._capture(institution, http, out_root)
                if path is not None:
                    captured.append(path)
        finally:
            http.close()

        if not captured:
            self.stdout.write(self.style.ERROR("Nothing was captured."))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(captured)} fixture(s):"))
        for path in captured:
            self.stdout.write(f"  {path}")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Before committing: read the diff. A silently changed fixture turns a real "
                "regression green. Check for contact names the redactions missed."
            )
        )

    def _capture(self, institution: Institution, http: Any, out_root: Path) -> Path | None:
        """Fetch and write one institution's careers page."""
        ref = institution_ref(institution)
        if not ref.careers_url:
            self.stdout.write(self.style.WARNING(f"{institution.slug}: no careers URL, skipped"))
            return None

        try:
            probe = probe_portal(ref, http)
        except AdapterError as error:
            self.stdout.write(self.style.ERROR(f"{institution.slug}: {error}"))
            return None

        platform = (institution.effective_platform or "unknown").lower()
        today = timezone.localdate().isoformat()
        path = out_root / platform / f"{institution.slug}-{today}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(redact(probe.html), encoding="utf-8")

        self.stdout.write(
            f"{institution.slug}: {len(probe.html):,} bytes from {probe.final_url or probe.url}"
        )
        return path
