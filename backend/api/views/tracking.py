"""Saved jobs, the application pipeline and saved searches."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from analytics.enums import EventKind
from analytics.services import record
from api.permissions import EVERY_ROLE, OwnedQuerysetMixin
from api.serializers import (
    ApplicationSerializer,
    SavedJobSerializer,
    SavedSearchSerializer,
)
from jobs.enums import APPLICATION_PIPELINE, ApplicationStatus
from jobs.models import Application, SavedJob, SavedSearch
from jobs.services import transition_application


class SavedJobViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Save and organise jobs. Scoped to the signed-in candidate."""

    required_roles = EVERY_ROLE

    def perform_create(self, serializer: Any) -> None:
        """Save the job, and record the save."""
        super().perform_create(serializer)
        record(EventKind.JOB_SAVE, actor=self.request.user, job=serializer.instance.job)

    def perform_destroy(self, instance: Any) -> None:
        """Unsave, and record it - a save that does not stick is a signal too."""
        job = instance.job
        super().perform_destroy(instance)
        record(EventKind.JOB_UNSAVE, actor=self.request.user, job=job)

    queryset = SavedJob.objects.select_related(
        "job", "job__institution", "job__screening"
    ).order_by("job__closing_date")
    serializer_class = SavedJobSerializer
    filterset_fields = ["job__status"]


class ApplicationViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """The pipeline board, showing this candidate's own progress against each job."""

    required_roles = EVERY_ROLE

    queryset = Application.objects.select_related(
        "job", "job__institution", "job__screening"
    ).prefetch_related("status_events")
    serializer_class = ApplicationSerializer
    filterset_fields = ["status", "ghosted_flagged"]

    def perform_create(self, serializer: Any) -> None:
        """Create the application, and record it."""
        super().perform_create(serializer)
        record(
            EventKind.APPLY,
            actor=self.request.user,
            job=serializer.instance.job,
            status=serializer.instance.status,
        )

    def perform_update(self, serializer: Any) -> None:
        """Send a status change through the service, so the change is recorded.

        Writing ``status`` straight onto the row would lose the timestamp, and the timestamps are
        what make reply-time analysis possible.
        """
        instance = serializer.instance
        new_status = serializer.validated_data.get("status")

        if new_status and new_status != instance.status:
            serializer.validated_data.pop("status")
            serializer.save()
            transition_application(instance, to_status=ApplicationStatus(new_status))
        else:
            serializer.save()

    @extend_schema(summary="The pipeline board, grouped by column", responses={200: dict})
    @action(detail=False, methods=["get"])
    def board(self, request: Request) -> Response:
        """Return applications grouped into the board's columns, in board order."""
        applications = list(self.filter_queryset(self.get_queryset()))
        by_status: dict[str, list[dict[str, Any]]] = {
            status_value.value: [] for status_value in APPLICATION_PIPELINE
        }
        for application in applications:
            by_status.setdefault(application.status, []).append(
                ApplicationSerializer(application).data
            )
        return Response(
            {
                "columns": [
                    {
                        "status": status_value.value,
                        "label": status_value.label,
                        "applications": by_status.get(status_value.value, []),
                    }
                    for status_value in APPLICATION_PIPELINE
                ]
            }
        )

    @extend_schema(
        summary="Move an application", request=dict, responses={200: ApplicationSerializer}
    )
    @action(detail=True, methods=["post"])
    def move(self, request: Request, pk: str | None = None) -> Response:
        """Move a card between columns, recording the transition."""
        application = self.get_object()
        raw_status = request.data.get("status")
        try:
            to_status = ApplicationStatus(raw_status)
        except ValueError:
            return Response(
                {"detail": f"Unknown status {raw_status!r}.", "code": "invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        transition_application(application, to_status=to_status, note=request.data.get("note", ""))
        record(
            EventKind.APPLICATION_MOVE,
            actor=request.user,
            job=application.job,
            to_status=str(to_status),
        )
        application.refresh_from_db()
        return Response(ApplicationSerializer(application).data)


class SavedSearchViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Named filter sets, optionally feeding the digest. Scoped to their owner."""

    required_roles = EVERY_ROLE

    queryset = SavedSearch.objects.all()
    serializer_class = SavedSearchSerializer
