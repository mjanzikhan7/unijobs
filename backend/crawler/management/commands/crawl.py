"""``manage.py crawl``: start a crawl from the command line.

Runs in the terminal by default, so you see the output. ``--async`` sends it to Celery.
"""

from __future__ import annotations

from argparse import ArgumentParser
from functools import partial
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from crawler.enums import CrawlTrigger
from crawler.services import (
    RunAlreadyActive,
    build_browser_session,
    build_http_client,
    crawl_institution,
    finalise_run,
    needs_browser,
    start_run,
)
from institutions.models import Institution


class Command(BaseCommand):
    """Crawl the estate, or one institution."""

    help = "Run a crawl. Defaults to every enabled institution, synchronously."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Accept an institution filter and an async switch."""
        parser.add_argument(
            "--slug",
            action="append",
            default=[],
            help="Crawl only these institutions (repeatable).",
        )
        parser.add_argument(
            "--async",
            dest="run_async",
            action="store_true",
            help="Hand the run to Celery instead of running it here.",
        )
        parser.add_argument(
            "--no-browser",
            action="store_true",
            help="Skip Playwright. JS-rendered portals will report ZERO_RESULTS.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Start a run and report each institution as it completes."""
        slugs: list[str] = options["slug"]
        queryset = Institution.objects.crawlable()
        if slugs:
            queryset = queryset.filter(slug__in=slugs)
            missing = set(slugs) - set(queryset.values_list("slug", flat=True))
            if missing:
                raise CommandError(f"Unknown or non-crawlable institutions: {sorted(missing)}")

        institution_ids = list(queryset.values_list("pk", flat=True))
        if not institution_ids:
            raise CommandError("No crawlable institutions. Run `make seed` first.")

        try:
            run = start_run(trigger=CrawlTrigger.MANUAL, institution_ids=institution_ids)
        except RunAlreadyActive as exc:
            raise CommandError(
                f"Crawl run {exc.run.pk} is already in progress. Concurrent runs are not allowed."
            ) from exc

        if options["run_async"]:
            from crawler.tasks import dispatch_run_task

            dispatch_run_task.delay(run.pk, institution_ids)
            self.stdout.write(self.style.SUCCESS(f"run {run.pk} dispatched to Celery"))
            return

        http = build_http_client()
        try:
            for institution in queryset:
                browser_factory = (
                    None
                    if options["no_browser"] or not needs_browser(institution)
                    else partial(build_browser_session, before_navigation=http.prepare_navigation)
                )
                result = crawl_institution(
                    run, institution, http=http, browser_factory=browser_factory
                )
                style = self.style.SUCCESS if result.outcome == "OK" else self.style.WARNING
                self.stdout.write(
                    style(
                        f"{institution.name:<45} {result.outcome:<18} "
                        f"{result.vacancies_found:>4} found  "
                        f"+{result.jobs_new} new  ~{result.jobs_updated} updated  "
                        f"-{result.jobs_closed} closed"
                    )
                )
        finally:
            http.close()

        run = finalise_run(run)
        self.stdout.write(
            self.style.SUCCESS(
                f"run {run.pk} complete: {run.jobs_new} new, {run.jobs_updated} updated, "
                f"{run.jobs_closed} closed"
            )
        )

        from crawler.tasks import screen_run_changes

        counts = screen_run_changes(run.pk)
        self.stdout.write(
            f"screened {counts['screened']} jobs, {counts['changed']} verdicts changed"
        )
