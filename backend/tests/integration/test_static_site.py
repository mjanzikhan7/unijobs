"""The static export: plain HTML, CSV and JSON for open, screened jobs only."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command

from jobs.enums import JobStatus
from jobs.static_site import export_static_site
from tests.factories import JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


def _screened(ruleset: Any, **fields: Any) -> Any:
    job = JobFactory(**fields)
    ScreeningFactory(job=job, ruleset=ruleset)
    return job


def test_only_open_screened_jobs_are_exported(tmp_path: Path, ruleset: Any) -> None:
    open_job = _screened(ruleset, title="Lecturer in History")
    _screened(ruleset, title="Closed post", status=JobStatus.DISAPPEARED)
    JobFactory(title="Not screened yet")

    result = export_static_site(tmp_path)
    data = json.loads((tmp_path / "jobs.json").read_text())

    assert result.jobs == 1
    assert [job["title"] for job in data["jobs"]] == ["Lecturer in History"]
    assert (tmp_path / "institutions" / f"{open_job.institution.slug}.html").exists()


def test_pages_have_no_javascript_and_escape_text(tmp_path: Path, ruleset: Any) -> None:
    job = _screened(ruleset, title="<script>alert(1)</script> Research Fellow")

    export_static_site(tmp_path)
    page = (tmp_path / "institutions" / f"{job.institution.slug}.html").read_text()
    index = (tmp_path / "index.html").read_text()

    assert "<script" not in page.lower()
    assert "<script" not in index.lower()
    assert "&lt;script&gt;" in page
    assert '<html lang="en-GB">' in index
    assert 'href="#main"' in index


def test_csv_matches_the_json(tmp_path: Path, ruleset: Any) -> None:
    _screened(ruleset, title="Data Scientist")
    _screened(ruleset, title="Research Software Engineer")

    export_static_site(tmp_path)
    rows = list(csv.DictReader((tmp_path / "jobs.csv").open()))
    data = json.loads((tmp_path / "jobs.json").read_text())

    assert sorted(row["title"] for row in rows) == sorted(job["title"] for job in data["jobs"])


def test_the_command_writes_the_site(tmp_path: Path, ruleset: Any) -> None:
    _screened(ruleset)

    call_command("export_static_site", "--out", str(tmp_path))

    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "styles.css").exists()
