"""Uploading a CV, reading back what was found, and applying it to a profile.

The file comes from an untrusted client, so the checks run in this order: size, real format,
unpacked size, and only then parsing.

The file never has a public URL. Downloads go through :meth:`CVViewSet.download`, which checks
the owner like every other row.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from analytics.enums import EventKind
from analytics.services import record
from api.permissions import EVERY_ROLE, OwnedQuerysetMixin
from screening.cv_domain import ExtractedCriteria
from screening.cv_text import UnreadableCV, sniff_format
from screening.models import CV
from screening.services import apply_cv_to_profile, parse_cv
from screening.tasks import rescore_for_user

ALLOWED_SUFFIXES = (".pdf", ".docx")


class CVSerializer(serializers.ModelSerializer[CV]):
    """An uploaded CV and what was read from it.

    ``extracted_text`` is never sent to the client. It is the most personal data we hold, and the
    UI only needs the suggestions.
    """

    class Meta:
        model = CV
        fields = [
            "id",
            "original_filename",
            "content_type",
            "byte_size",
            "suggestions",
            "applied_at",
            "uploaded_at",
        ]
        read_only_fields = fields


class CVUploadSerializer(serializers.Serializer[dict[str, Any]]):
    """One uploaded file, validated before anything opens it."""

    file = serializers.FileField()

    def validate_file(self, value: Any) -> Any:
        """Reject anything too large, wrongly named, or not actually the format it claims."""
        if value.size > settings.CV_MAX_BYTES:
            limit = settings.CV_MAX_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"That file is larger than {limit}MB.")

        if not value.name.lower().endswith(ALLOWED_SUFFIXES):
            raise serializers.ValidationError("Upload a PDF or a Word (.docx) document.")

        head = value.read(8)
        value.seek(0)
        try:
            sniff_format(head)
        except UnreadableCV as error:
            raise serializers.ValidationError(str(error)) from error

        return value


class ApplyCVSerializer(serializers.Serializer[dict[str, Any]]):
    """The candidate's confirmed edit of what the parser suggested."""

    skills = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    domains = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    seniority = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    projects = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    education = serializers.ListField(child=serializers.CharField(max_length=120), required=False)
    years_experience = serializers.IntegerField(min_value=0, max_value=70, required=False)
    replace = serializers.BooleanField(required=False, default=False)


class CVViewSet(
    OwnedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """A candidate's own CVs."""

    required_roles = EVERY_ROLE

    queryset = CV.objects.all()
    serializer_class = CVSerializer

    throttle_scope = "cv_upload"

    @extend_schema(request=CVUploadSerializer, responses={201: CVSerializer})
    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        throttle_classes=[ScopedRateThrottle],
    )
    def upload(self, request: Request) -> Response:
        """Accept a CV, read its text, and return what it suggests.

        Done in the request, not in a queue. The candidate is waiting for the result, and the size
        and format checks keep the work small.
        """
        serializer = CVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]

        cv = CV.objects.create(
            owner=request.user,
            file=upload,
            original_filename=upload.name[:255],
            content_type="pdf" if upload.name.lower().endswith(".pdf") else "docx",
            byte_size=upload.size,
        )

        try:
            parse_cv(cv)
        except UnreadableCV as error:
            cv.delete()
            return Response(
                {"detail": str(error), "code": "unreadable_cv"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record(
            EventKind.CV_UPLOAD,
            actor=request.user,
            skills_found=len((cv.suggestions or {}).get("skills", [])),
            content_type=cv.content_type,
        )
        return Response(CVSerializer(cv).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ApplyCVSerializer, responses={202: dict})
    @action(detail=True, methods=["post"])
    def apply_to_profile(self, request: Request, pk: str | None = None) -> Response:
        """Write the candidate's confirmed terms to their profile, and score jobs again.

        The candidate decides, not the parser, because the parser is not exact.
        """
        cv = self.get_object()
        serializer = ApplyCVSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        stored = cv.suggestions or {}
        extracted = ExtractedCriteria(
            skills=tuple(data.get("skills", stored.get("skills", ()))),
            domains=tuple(data.get("domains", stored.get("domains", ()))),
            seniority=tuple(data.get("seniority", stored.get("seniority", ()))),
            projects=tuple(data.get("projects", stored.get("projects", ()))),
            education=tuple(data.get("education", stored.get("education", ()))),
            years_experience=data.get("years_experience", stored.get("years_experience", 0)),
        )
        apply_cv_to_profile(cv, extracted, replace=data["replace"])

        rescore_for_user.delay(request.user.pk)
        return Response(
            {"queued": True, "detail": "Profile updated. Re-scoring in the background."},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: bytes})
    @action(detail=True, methods=["get"])
    def download(self, request: Request, pk: str | None = None) -> FileResponse:
        """Return the stored file to its owner.

        The only way to read a CV. Sent as an attachment with `nosniff`, so a crafted file cannot
        open as a web page on our site.
        """
        cv = self.get_object()
        response = FileResponse(
            cv.file.open("rb"),
            as_attachment=True,
            filename=cv.original_filename or f"cv.{cv.content_type}",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
