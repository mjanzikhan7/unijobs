"""Service metrics in the Prometheus text format.

Lets Prometheus, Grafana or a university's own monitoring watch the things that really go wrong
here: crawls that stop, institutions that stop answering, and jobs left without a verdict.

Protected by a bearer token (``METRICS_TOKEN``). With no token set, the endpoint returns 404,
so it is never open by accident. Only totals are exposed, never personal data.
"""

from __future__ import annotations

import hmac

from django.conf import settings
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from crawler.models import CrawlRun, CrawlRunInstitution
from institutions.models import Institution
from jobs.models import Job

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def _authorised(request: Request) -> bool:
    expected = settings.METRICS_TOKEN
    supplied = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def _line(name: str, value: float, labels: dict[str, str] | None = None) -> str:
    if labels:
        inner = ",".join(f'{key}="{val}"' for key, val in sorted(labels.items()))
        return f"{name}{{{inner}}} {value}"
    return f"{name} {value}"


def render_metrics() -> str:
    """Build the metrics text from the database."""
    lines: list[str] = []

    def metric(name: str, kind: str, help_text: str, rows: list[str]) -> None:
        lines.extend([f"# HELP {name} {help_text}", f"# TYPE {name} {kind}", *rows])

    jobs_by_status = Job.objects.values("status").annotate(n=Count("id")).order_by("status")
    metric(
        "unijobs_jobs",
        "gauge",
        "Jobs by status.",
        [_line("unijobs_jobs", row["n"], {"status": row["status"]}) for row in jobs_by_status],
    )
    metric(
        "unijobs_jobs_unscreened",
        "gauge",
        "Jobs with no screening verdict. Should always be 0.",
        [_line("unijobs_jobs_unscreened", Job.objects.filter(screening__isnull=True).count())],
    )
    metric(
        "unijobs_institutions_crawl_enabled",
        "gauge",
        "Institutions that are crawled.",
        [
            _line(
                "unijobs_institutions_crawl_enabled",
                Institution.objects.filter(crawl_enabled=True).count(),
            )
        ],
    )

    last_run = CrawlRun.objects.order_by("-started_at").first()
    if last_run is not None:
        age = (timezone.now() - last_run.started_at).total_seconds()
        metric(
            "unijobs_crawl_last_run_age_seconds",
            "gauge",
            "Seconds since the latest crawl started.",
            [_line("unijobs_crawl_last_run_age_seconds", round(age))],
        )
        metric(
            "unijobs_crawl_last_run_info",
            "gauge",
            "The latest crawl run and its status.",
            [
                _line(
                    "unijobs_crawl_last_run_info",
                    1,
                    {"run": str(last_run.pk), "status": str(last_run.status)},
                )
            ],
        )
        outcomes = (
            CrawlRunInstitution.objects.filter(run=last_run)
            .values("outcome")
            .annotate(n=Count("id"))
            .order_by("outcome")
        )
        metric(
            "unijobs_crawl_last_run_outcomes",
            "gauge",
            "Institutions in the latest crawl, by outcome.",
            [
                _line("unijobs_crawl_last_run_outcomes", row["n"], {"outcome": row["outcome"]})
                for row in outcomes
            ],
        )

    return "\n".join(lines) + "\n"


class MetricsView(APIView):
    """Expose service metrics to a monitoring system."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(exclude=True)
    def get(self, request: Request) -> HttpResponse:
        """Return metrics, or 404 when metrics are off or the token is wrong."""
        if not settings.METRICS_TOKEN or not _authorised(request):
            raise Http404
        return HttpResponse(render_metrics(), content_type=CONTENT_TYPE)
