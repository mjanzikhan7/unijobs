"""A static copy of the open vacancies: plain HTML, CSV and JSON, with no JavaScript.

Minimal computing: the pages work in any browser, with a screen reader, on a slow connection,
and from any static host. They need no server, no database and no sign-in. The React app adds
search and tracking on top, but these pages stand on their own.

Only open jobs with a verdict are exported. Nothing personal is included.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.template.loader import render_to_string
from django.utils import timezone

from jobs.enums import Discipline, JobStatus
from jobs.models import Job
from screening.enums import SponsorVerdict, ThresholdVerdict

STYLESHEET = """\
:root { color-scheme: light dark; --text: #1a1a1a; --muted: #505a5f; --link: #1d4ed8;
  --bg: #ffffff; --line: #b1b4b6; }
@media (prefers-color-scheme: dark) { :root { --text: #f3f2f1; --muted: #c8ccd0;
  --link: #8ab4ff; --bg: #0b0c0c; --line: #505a5f; } }
* { box-sizing: border-box; }
body { margin: 0; font: 1.1875rem/1.5 system-ui, sans-serif; color: var(--text);
  background: var(--bg); }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 1rem; top: 1rem; background: #ffdd00; color: #0b0c0c; padding: .5rem; }
main, header, footer { max-width: 60rem; margin: 0 auto; padding: 1rem; }
a { color: var(--link); text-decoration: underline; text-underline-offset: .15em; }
a:focus { outline: 3px solid #ffdd00; outline-offset: 0; background: #ffdd00; color: #0b0c0c; }
h1 { font-size: 2rem; line-height: 1.2; }
.meta, footer { color: var(--muted); }
ul.jobs { list-style: none; padding: 0; }
ul.jobs li { border-top: 1px solid var(--line); padding: .75rem 0; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1rem; margin: .5rem 0 0; }
dt { font-weight: 600; }
dd { margin: 0; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; border-bottom: 1px solid var(--line); padding: .5rem .25rem; }
"""


@dataclass(frozen=True)
class ExportResult:
    """What the export wrote."""

    jobs: int
    institutions: int
    files: int


def _label(enum: Any, value: str) -> str:
    try:
        return str(enum(value).label)
    except ValueError:
        return value


def _row(job: Job) -> dict[str, Any]:
    screening = job.screening
    return {
        "id": job.pk,
        "title": job.title,
        "institution": job.institution.name,
        "institution_slug": job.institution.slug,
        "city": job.city,
        "salary": job.salary_raw,
        "closing_date": job.closing_date.isoformat() if job.closing_date else "",
        "discipline": _label(Discipline, job.discipline),
        "sponsor_verdict": _label(SponsorVerdict, screening.sponsor_verdict),
        "threshold_verdict": _label(ThresholdVerdict, screening.threshold_verdict),
        "url": job.source_url,
    }


def export_static_site(out_dir: Path) -> ExportResult:
    """Write the static site to ``out_dir`` and return what was written."""
    jobs = (
        Job.objects.filter(status=JobStatus.OPEN, screening__isnull=False)
        .select_related("institution", "screening")
        .order_by("institution__name", "closing_date", "title")
    )
    rows = [_row(job) for job in jobs]

    by_institution: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}
    for row in rows:
        by_institution[row["institution_slug"]].append(row)
        names[row["institution_slug"]] = row["institution"]

    generated = timezone.localtime().strftime("%-d %B %Y, %H:%M")
    (out_dir / "institutions").mkdir(parents=True, exist_ok=True)
    files = 0

    def write(path: Path, text: str) -> None:
        nonlocal files
        path.write_text(text, encoding="utf-8")
        files += 1

    write(out_dir / "styles.css", STYLESHEET)
    institutions = sorted(
        (
            {"slug": slug, "name": names[slug], "count": len(items)}
            for slug, items in by_institution.items()
        ),
        key=lambda item: item["name"],
    )
    write(
        out_dir / "index.html",
        render_to_string(
            "static_site/index.html",
            {"institutions": institutions, "total": len(rows), "generated": generated},
        ),
    )
    for slug, items in by_institution.items():
        write(
            out_dir / "institutions" / f"{slug}.html",
            render_to_string(
                "static_site/institution.html",
                {"name": names[slug], "jobs": items, "generated": generated},
            ),
        )

    write(out_dir / "jobs.json", json.dumps({"generated": generated, "jobs": rows}, indent=2))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()) if rows else ["id"])
    writer.writeheader()
    writer.writerows(rows)
    write(out_dir / "jobs.csv", buffer.getvalue())

    return ExportResult(jobs=len(rows), institutions=len(by_institution), files=files)
