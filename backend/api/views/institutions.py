"""The crawl-health console and the sponsor review queue."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.enums import Role
from accounts.services import role_of
from analytics.enums import EventKind
from analytics.services import record
from api.exceptions import ConflictError
from api.permissions import ADMIN_ONLY, EVERY_ROLE, STAFF, STAFF_OR_RECRUITER, is_assigned
from api.serializers import (
    CrawlRunSerializer,
    InstitutionMediaSerializer,
    InstitutionSerializer,
    ResolveSponsorSerializer,
)
from crawler.models import CrawlRunInstitution
from crawler.services import RunAlreadyActive, start_run
from institutions.enums import Platform
from institutions.models import Institution
from jobs.enums import JobStatus
from screening.enums import SponsorVerdict
from screening.models import InstitutionSponsorMatch
from screening.services import resolve_sponsor_match


class InstitutionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Read and manage institutions.

    Which fields can change depends on the role. A manager changes how an institution is
    crawled. Changing what it *is* (name, ranking, nation) is for an admin, because a crawl cannot
    restore those values.
    """

    required_roles = EVERY_ROLE
    required_roles_write = STAFF_OR_RECRUITER
    required_roles_by_action = {
        "create": ADMIN_ONLY,
        "destroy": ADMIN_ONLY,
        "crawl": STAFF,
        "review_queue": STAFF,
        "resolve_sponsor": STAFF,
        "register_search": STAFF,
        "rematch_sponsor": STAFF,
    }

    serializer_class = InstitutionSerializer
    filterset_fields = ["slug", "nation", "platform", "crawl_enabled", "institution_type"]
    search_fields = ["name", "city"]

    MANAGER_FIELDS = frozenset({"adapter_override", "crawl_enabled", "notes", "careers_url"})
    ADMIN_FIELDS = MANAGER_FIELDS | {
        "name",
        "city",
        "nation",
        "institution_type",
        "ranking",
        "website",
        "description",
        "contact_email",
        "contact_phone",
        "address",
    }
    RECRUITER_FIELDS = frozenset({"description", "contact_email", "contact_phone", "address"})

    def get_queryset(self):  # noqa: ANN201 - DRF signature
        """Load each institution with its sponsor match and its latest crawl result."""
        return (
            Institution.objects.select_related("sponsor_match")
            .annotate(open_jobs=Count("jobs", filter=Q(jobs__status=JobStatus.OPEN), distinct=True))
            .prefetch_related(
                Prefetch(
                    "crawl_results",
                    queryset=CrawlRunInstitution.objects.order_by("-started_at")[:1],
                    to_attr="recent_results",
                )
            )
            .order_by("name")
        )

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return one institution, and record the visit."""
        response = super().retrieve(request, *args, **kwargs)
        record(EventKind.INSTITUTION_VIEW, actor=request.user, institution=self.get_object())
        return response

    @extend_schema(summary="Crawl one institution", responses={202: CrawlRunSerializer, 409: dict})
    @action(detail=True, methods=["post"])
    def crawl(self, request: Request, pk: str | None = None) -> Response:
        """Start a run covering only this institution."""
        institution = self.get_object()
        try:
            run = start_run(institution_ids=[institution.pk])
        except RunAlreadyActive as exc:
            raise ConflictError(
                "A crawl is already running.", extra={"active_run_id": exc.run.pk}
            ) from exc

        from crawler.tasks import dispatch_run_task

        dispatch_run_task.delay(run.pk, [institution.pk])
        return Response(CrawlRunSerializer(run).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Institutions needing a sponsor decision",
        responses={200: InstitutionSerializer},
    )
    @action(detail=False, methods=["get"], url_path="review-queue")
    def review_queue(self, request: Request) -> Response:
        """List institutions whose legal entity a person still has to confirm.

        These are the cases where a guess would hurt most. Legal names on the register are often
        different from everyday names, so a fuzzy match is often wrong.
        """
        queryset = self.get_queryset().filter(
            Q(sponsor_match__needs_review=True) | Q(sponsor_match__isnull=True)
        )
        return Response(InstitutionSerializer(queryset, many=True).data)

    @extend_schema(
        summary="Record which legal entity this institution is",
        request=ResolveSponsorSerializer,
        responses={200: InstitutionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="resolve-sponsor")
    def resolve_sponsor(self, request: Request, pk: str | None = None) -> Response:
        """Save a person's decision, so the question is never asked again.

        This covers the parent body case. The MRC Laboratory of Molecular Biology has no entry of
        its
        own, because UK Research and Innovation is its sponsor. No string matching can find that.
        """
        institution = self.get_object()
        serializer = ResolveSponsorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolve_sponsor_match(
            institution,
            registered_legal_name=serializer.validated_data["registered_legal_name"],
            verdict=SponsorVerdict(serializer.validated_data["verdict"]),
            notes=serializer.validated_data.get("notes", ""),
        )

        institution = self.get_queryset().get(pk=institution.pk)
        return Response(InstitutionSerializer(institution).data)

    @extend_schema(
        summary="Search the sponsor register by hand",
        parameters=[OpenApiParameter("q", description="Free-text organisation name")],
        responses={200: dict},
    )
    @action(detail=False, methods=["get"], url_path="register-search")
    def register_search(self, request: Request) -> Response:
        """Search the register directly.

        Some institutions are sponsored by a parent body with a different name. For example, UK
        Research and Innovation sponsors the MRC Laboratory of Molecular Biology. A person searching
        the register can find that. A matcher cannot.
        """
        from dataclasses import asdict

        from screening.services import search_register

        results = search_register(request.query_params.get("q", ""))
        return Response([asdict(candidate) for candidate in results])

    @extend_schema(
        summary="Re-run sponsor matching for this institution",
        responses={200: InstitutionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="rematch-sponsor")
    def rematch_sponsor(self, request: Request, pk: str | None = None) -> Response:
        """Run the matching cascade again against the newest register snapshot."""
        from screening.services import match_institution

        institution = self.get_object()
        match_institution(institution)
        institution = self.get_queryset().get(pk=institution.pk)
        return Response(InstitutionSerializer(institution).data)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Allow only the fields this role is meant to change."""
        instance = self.get_object()
        role = role_of(request.user)
        if role is Role.ADMIN:
            allowed = self.ADMIN_FIELDS
        elif role is Role.RECRUITER:
            if not is_assigned(request.user, instance):
                raise PermissionDenied("You are not assigned to this institution.")
            allowed = self.RECRUITER_FIELDS
        else:
            allowed = self.MANAGER_FIELDS
        payload = {key: value for key, value in request.data.items() if key in allowed}

        moved = "careers_url" in payload and payload["careers_url"] != instance.careers_url

        serializer = self.get_serializer(instance, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if moved:
            instance.refresh_from_db()
            instance.platform = Platform.UNKNOWN
            instance.save(update_fields=["platform"])
            serializer = self.get_serializer(self.get_queryset().get(pk=instance.pk))

        return Response(serializer.data)

    @extend_schema(
        summary="Upload a logo, a banner, or both",
        request=InstitutionMediaSerializer,
        responses={200: InstitutionSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def media(self, request: Request, pk: str | None = None) -> Response:
        """Add a logo or banner to an institution.

        `ImageField` opens each upload to check it is a real image before it is saved.
        """
        institution = self.get_object()
        if role_of(request.user) is Role.RECRUITER and not is_assigned(request.user, institution):
            raise PermissionDenied("You are not assigned to this institution.")
        serializer = InstitutionMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        changed: list[str] = []
        for field in ("logo", "banner"):
            upload = serializer.validated_data.get(field)
            if upload is None:
                continue
            existing = getattr(institution, field)
            if existing:
                existing.delete(save=False)
            setattr(institution, field, upload)
            changed.append(field)

        if changed:
            institution.save(update_fields=changed)

        return Response(InstitutionSerializer(self.get_queryset().get(pk=institution.pk)).data)

    @extend_schema(summary="Fetch an institution's logo", responses={200: bytes})
    @action(detail=True, methods=["get"])
    def logo(self, request: Request, pk: str | None = None) -> FileResponse:
        """Return the stored logo."""
        return self._media_response(self.get_object().logo)

    @extend_schema(summary="Fetch an institution's banner", responses={200: bytes})
    @action(detail=True, methods=["get"])
    def banner(self, request: Request, pk: str | None = None) -> FileResponse:
        """Return the stored banner."""
        return self._media_response(self.get_object().banner)

    @staticmethod
    def _media_response(stored: Any) -> FileResponse:
        """Serve one stored image, or 404.

        Through the API, not a media URL. Nothing in `MEDIA_ROOT` is served directly, because that
        is what keeps CVs private. Logos follow the same rule.
        """
        if not stored:
            raise Http404("No image for that institution.")
        response = FileResponse(stored.open("rb"))
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, max-age=86400"
        return response

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Delete an institution, unless it has jobs.

        Deleting an institution deletes its jobs, and with them every candidate's saved copies and
        application history. That cannot be undone. Usually turning off the crawl is what is wanted.
        """
        institution = self.get_object()
        job_count = institution.jobs.count()
        if job_count:
            raise ConflictError(
                f"{institution.name} has {job_count} job(s). Deleting it would remove them and "
                f"every saved job and application against them. Disable crawling instead.",
                extra={"jobs": job_count, "use": "crawl_enabled=false"},
            )

        institution.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SponsorMatchViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Read-only view of every sponsor verdict, for auditing."""

    required_roles = STAFF

    queryset = InstitutionSponsorMatch.objects.select_related("institution").order_by(
        "institution__name"
    )
    serializer_class = InstitutionSerializer
    filterset_fields = ["verdict", "needs_review", "resolved_by_human"]

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return a flat verdict list rather than nested institutions."""
        rows = self.filter_queryset(self.get_queryset())
        return Response(
            [
                {
                    "institution": row.institution.name,
                    "slug": row.institution.slug,
                    "registered_legal_name": row.registered_legal_name,
                    "verdict": row.verdict,
                    "method": row.method,
                    "confidence": row.confidence,
                    "needs_review": row.needs_review,
                    "resolved_by_human": row.resolved_by_human,
                }
                for row in rows
            ]
        )
