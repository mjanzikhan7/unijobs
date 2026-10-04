"""Crawl runs: starting them, watching them, and reading what they changed."""

from __future__ import annotations

from typing import Any

from django.db.models import Case, IntegerField, Prefetch, Value, When
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.exceptions import ConflictError
from api.permissions import STAFF
from api.serializers import (
    CrawlLogEntrySerializer,
    CrawlRunDetailSerializer,
    CrawlRunInstitutionSerializer,
    CrawlRunSerializer,
    JobListSerializer,
    JobRevisionSerializer,
    RestartCrawlSerializer,
    StartCrawlSerializer,
)
from crawler.enums import CrawlOutcome
from crawler.models import CrawlRun, CrawlRunInstitution
from crawler.services import (
    InvalidRunTransition,
    NothingToRetry,
    RunAlreadyActive,
    cancel_run,
    pause_run,
    restart_run,
    resume_run,
    start_run,
)
from institutions.models import Institution
from jobs.enums import JobStatus
from jobs.models import Job, JobRevision


class CrawlRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Start a crawl, list past runs, and inspect one."""

    required_roles = STAFF

    queryset = CrawlRun.objects.all()
    serializer_class = CrawlRunSerializer

    def get_queryset(self):  # noqa: ANN201 - DRF signature
        """Prefetch institution results for the detail view only."""
        queryset = CrawlRun.objects.all()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                Prefetch(
                    "institution_results",
                    queryset=CrawlRunInstitution.objects.select_related("institution"),
                )
            )
        return queryset

    def get_serializer_class(self):  # noqa: ANN201 - DRF signature
        """Return the detail serializer for a single run."""
        if self.action == "retrieve":
            return CrawlRunDetailSerializer
        if self.action == "create":
            return StartCrawlSerializer
        return CrawlRunSerializer

    @extend_schema(
        summary="Start a crawl",
        request=StartCrawlSerializer,
        responses={202: CrawlRunSerializer, 409: dict},
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create a run and start it in the background.

        Returns ``202`` with the run id straight away, because Celery does the work. If a run is
        already active, the answer is ``409`` with that run's id, so the UI can link to it.
        """
        serializer = StartCrawlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slugs = serializer.validated_data.get("institutions") or []

        institution_ids = (
            list(Institution.objects.filter(slug__in=slugs).values_list("pk", flat=True))
            if slugs
            else None
        )

        try:
            run = start_run(institution_ids=institution_ids)
        except RunAlreadyActive as exc:
            raise ConflictError(
                "A crawl is already running.",
                extra={"active_run_id": exc.run.pk},
            ) from exc

        from crawler.tasks import dispatch_run_task

        dispatch_run_task.delay(run.pk, institution_ids)
        return Response(CrawlRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(summary="What this run changed", responses={200: dict})
    @action(detail=True, methods=["get"])
    def diff(self, request: Request, pk: str | None = None) -> Response:
        """Split this run's effects into New, Changed and Disappeared.

        The three sets never overlap. A job is new if this run first saw it, changed if this run
        wrote a revision for it, and disappeared only if this run closed it.
        """
        run = self.get_object()

        new_jobs = (
            Job.objects.with_related(for_user=request.user)
            .filter(first_seen_at__gte=run.started_at)
            .filter(institution__crawl_results__run=run)
            .distinct()
        )
        new_ids = set(new_jobs.values_list("pk", flat=True))

        revisions = (
            JobRevision.objects.filter(crawl_run=run)
            .exclude(job_id__in=new_ids)
            .select_related("job", "job__institution")
        )

        disappeared = (
            Job.objects.with_related(for_user=request.user)
            .filter(status=JobStatus.DISAPPEARED, disappeared_at__gte=run.started_at)
            .filter(institution__crawl_results__run=run)
            .distinct()
        )

        return Response(
            {
                "run": CrawlRunSerializer(run).data,
                "new": JobListSerializer(new_jobs, many=True).data,
                "changed": JobRevisionSerializer(revisions, many=True).data,
                "disappeared": JobListSerializer(disappeared, many=True).data,
            }
        )

    @extend_schema(
        summary="Institution rows for a run",
        responses={200: CrawlRunInstitutionSerializer},
    )
    @action(detail=True, methods=["get"], url_path="institutions")
    def institution_results(self, request: Request, pk: str | None = None) -> Response:
        """List every institution's outcome in this run, problems first."""
        run = self.get_object()
        rows = (
            CrawlRunInstitution.objects.filter(run=run)
            .select_related("institution")
            .annotate(
                is_problem=Case(
                    When(outcome=CrawlOutcome.OK.value, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by("is_problem", "-vacancies_found", "institution__name")
        )
        return Response(CrawlRunInstitutionSerializer(rows, many=True).data)

    @extend_schema(summary="The run currently in progress", responses={200: dict})
    @action(detail=False, methods=["get"])
    def active(self, request: Request) -> Response:
        """Return the active run, or ``null``.

        Wrapped in an object, because DRF sends an empty body for a bare ``None``, and a client
        cannot tell that apart from a failed request.
        """
        from crawler.services import active_run

        run = active_run()
        return Response({"run": CrawlRunSerializer(run).data if run else None})

    @extend_schema(
        summary="Log lines for this run",
        parameters=[OpenApiParameter("after", int, description="Only entries with a higher id")],
        responses={200: CrawlLogEntrySerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="logs", pagination_class=None)
    def logs(self, request: Request, pk: str | None = None) -> Response:
        """Log lines after a given id, oldest first.

        ``?after=<id>`` returns only the lines that are new since the last poll. Fetching the whole
        log every few seconds would make a long run's log slow.
        """
        run = self.get_object()
        after = int(request.query_params.get("after", 0))
        entries = (
            run.log_entries.select_related("institution").filter(id__gt=after).order_by("id")[:500]
        )
        return Response(CrawlLogEntrySerializer(entries, many=True).data)

    @extend_schema(
        summary="Pause a running crawl", responses={200: CrawlRunSerializer}, request=None
    )
    @action(detail=True, methods=["post"])
    def pause(self, request: Request, pk: str | None = None) -> Response:
        """Pause a running crawl. Refused with 409 if it isn't running."""
        run = self.get_object()
        try:
            pause_run(run)
        except InvalidRunTransition as exc:
            raise ConflictError(str(exc)) from exc
        return Response(CrawlRunSerializer(run).data)

    @extend_schema(
        summary="Resume a paused crawl", responses={200: CrawlRunSerializer}, request=None
    )
    @action(detail=True, methods=["post"])
    def resume(self, request: Request, pk: str | None = None) -> Response:
        """Resume a paused crawl. Refused with 409 if it isn't paused."""
        run = self.get_object()
        try:
            resume_run(run)
        except InvalidRunTransition as exc:
            raise ConflictError(str(exc)) from exc
        return Response(CrawlRunSerializer(run).data)

    @extend_schema(
        summary="Cancel a running or paused crawl",
        responses={200: CrawlRunSerializer},
        request=None,
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel a running or paused crawl. Refused with 409 if it has already finished."""
        run = self.get_object()
        try:
            cancel_run(run)
        except InvalidRunTransition as exc:
            raise ConflictError(str(exc)) from exc
        return Response(CrawlRunSerializer(run).data)

    @extend_schema(
        summary="Start a fresh run from this one",
        request=RestartCrawlSerializer,
        responses={202: CrawlRunSerializer},
    )
    @action(detail=True, methods=["post"])
    def restart(self, request: Request, pk: str | None = None) -> Response:
        """Start a new run for ``"all"`` (this run's institutions) or ``"failures"``.

        If this run is still active, it is cancelled first. ``scope="failures"`` with no failures is
        refused with 409, instead of starting an empty run.
        """
        run = self.get_object()
        serializer = RestartCrawlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            new_run = restart_run(run, scope=serializer.validated_data["scope"])
        except NothingToRetry as exc:
            raise ConflictError(str(exc)) from exc
        return Response(CrawlRunSerializer(new_run).data, status=status.HTTP_202_ACCEPTED)
