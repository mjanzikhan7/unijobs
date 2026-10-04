"""Rulesets, re-screening and the candidate profile."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from api.permissions import ADMIN_ONLY, EVERY_ROLE, STAFF, OwnedQuerysetMixin
from api.serializers import (
    CandidateProfileSerializer,
    CreateRulesetSerializer,
    RulesetSerializer,
)
from screening.models import CandidateProfile, Ruleset
from screening.services import create_ruleset_version, rescreen_all
from screening.tasks import rescore_for_user


class RulesetViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Versioned threshold figures.

    No update or delete, on purpose. Editing a ruleset would make its old verdicts impossible to
    explain, so a change creates a new version.
    """

    required_roles = STAFF
    required_roles_write = ADMIN_ONLY

    queryset = Ruleset.objects.prefetch_related("figures").order_by("-version")
    serializer_class = RulesetSerializer

    def get_serializer_class(self):  # noqa: ANN201 - DRF signature
        """Use the creation serializer for POST."""
        return CreateRulesetSerializer if self.action == "create" else RulesetSerializer

    @extend_schema(
        summary="Create a new ruleset version",
        request=CreateRulesetSerializer,
        responses={201: RulesetSerializer},
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create the next version. Never mutates an existing one."""
        serializer = CreateRulesetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ruleset = create_ruleset_version(
            name=data["name"],
            effective_from=data["effective_from"],
            verified_at=data["verified_at"],
            source_url=data["source_url"],
            figures={key: str(value) for key, value in data["figures"].items()},
            notes=data.get("notes", ""),
            activate=data.get("activate", True),
        )
        ruleset = Ruleset.objects.prefetch_related("figures").get(pk=ruleset.pk)
        return Response(RulesetSerializer(ruleset).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Re-screen every job against this ruleset", responses={200: dict})
    @action(detail=True, methods=["post"])
    def rescreen(self, request: Request, pk: str | None = None) -> Response:
        """Recalculate every verdict against this ruleset.

        No network calls. It only uses stored data, so a rule change does not need a new crawl of
        167
        universities.
        """
        ruleset = self.get_object()
        counts = rescreen_all(ruleset)
        return Response({"ruleset_version": ruleset.version, **counts})

    @extend_schema(summary="The ruleset currently in force", responses={200: RulesetSerializer})
    @action(detail=False, methods=["get"])
    def active(self, request: Request) -> Response:
        """Return the active ruleset."""
        ruleset = self.get_queryset().filter(is_active=True).first()
        return Response(RulesetSerializer(ruleset).data if ruleset else None)


class CandidateProfileViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """The profile fitness is scored against, one set per candidate."""

    required_roles = EVERY_ROLE

    queryset = CandidateProfile.objects.all()
    serializer_class = CandidateProfileSerializer

    @extend_schema(summary="Re-score fitness after a profile change", responses={202: dict})
    @action(detail=True, methods=["post"])
    def rescore(self, request: Request, pk: str | None = None) -> Response:
        """Queue a new fitness score for this candidate across all jobs.

        Fitness only changes how jobs are ranked. It never changes whether a job can be sponsored.

        Queued, not done in the request, because the work grows with the number of jobs.
        """
        self.get_object()

        rescore_for_user.delay(request.user.pk)
        return Response(
            {"queued": True, "detail": "Scoring in the background; results appear shortly."},
            status=status.HTTP_202_ACCEPTED,
        )
