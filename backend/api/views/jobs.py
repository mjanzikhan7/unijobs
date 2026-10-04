"""Job search, detail, facets, export and manual entry."""

from __future__ import annotations

import csv
import io
from typing import Any

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.enums import Role
from accounts.services import role_of
from analytics.enums import EventKind
from analytics.services import record
from api.exceptions import ConflictError
from api.filters import JobFilter, facet_counts
from api.permissions import EVERY_ROLE, STAFF_OR_RECRUITER, is_assigned
from api.serializers import (
    EditManualJobSerializer,
    ExtractJobSerializer,
    JobDetailSerializer,
    JobListSerializer,
    ManualJobSerializer,
    WithdrawJobSerializer,
)
from institutions.models import Institution
from jobs.domain import (
    classify_contract_type,
    classify_discipline,
    classify_hours,
    classify_workplace,
)
from jobs.enums import JobSource, JobStatus
from jobs.models import Job
from jobs.services import (
    CannotDeleteCrawledJob,
    add_manual_job,
    delete_job,
    refresh_search_vectors,
    reinstate_job,
    withdraw_job,
)


def _require_assigned(user: Any, institution: Institution) -> None:
    """Refuse a recruiter who acts on an institution they are not assigned to.

    Does nothing for other roles. The role check (`STAFF_OR_RECRUITER`) already ran in the
    permission layer. This adds the per-institution check.
    """
    if role_of(user) is Role.RECRUITER and not is_assigned(user, institution):
        raise PermissionDenied("You are not assigned to this institution.")


EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("title", "Title"),
    ("institution", "Institution"),
    ("nation", "Nation"),
    ("department", "Department"),
    ("location", "Location"),
    ("salary_raw", "Salary (as advertised)"),
    ("salary_min", "Salary floor"),
    ("salary_max", "Salary ceiling"),
    ("grade", "Grade"),
    ("contract_raw", "Contract (as advertised)"),
    ("hours_raw", "Hours (as advertised)"),
    ("sponsor_verdict", "Sponsor verdict"),
    ("sponsor_matched_name", "Registered legal name"),
    ("advert_excludes_sponsorship", "Advert excludes sponsorship"),
    ("threshold_verdict", "Threshold verdict"),
    ("fitness_score", "Fitness"),
    ("contract_type", "Contract"),
    ("hours", "Hours"),
    ("workplace", "Workplace"),
    ("posted_date", "Posted"),
    ("closing_date", "Closing"),
    ("status", "Status"),
    ("source_url", "URL"),
)


class JobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Search, read, export and manage vacancies.

    **Crawled adverts cannot be edited**: the next crawl would overwrite the edit. Only manual jobs
    accept PATCH and DELETE. An admin can take a crawled job down with ``POST /withdraw/``, and
    later crawls respect that.
    """

    required_roles = EVERY_ROLE
    required_roles_write = STAFF_OR_RECRUITER

    filterset_class = JobFilter
    serializer_class = JobListSerializer

    def get_queryset(self):  # noqa: ANN201 - DRF signature
        """Load jobs with their institution and screening in one query.

        ``with_related`` avoids one query per row for ``job -> institution -> screening``, and a
        test
        checks the query count. It is filtered by the caller, so the saved star and pipeline status
        on each row belong to this user.
        """
        queryset = Job.objects.with_related(for_user=self.request.user).filter(
            screening__isnull=False
        )
        if self.action == "list" and not self.request.query_params:
            queryset = queryset.filter(status=JobStatus.OPEN)
        return queryset

    @extend_schema(
        summary="Facet counts for the current query",
        parameters=[
            OpenApiParameter(
                "any job filter",
                description="Accepts every parameter GET /jobs/ accepts.",
                required=False,
            )
        ],
        responses={200: dict},
    )
    @action(detail=False, methods=["get"])
    def facets(self, request: Request) -> Response:
        """Return counts for each facet value, over the *filtered* set.

        Counts that ignore the filters are worse than no counts. They promise results that are not
        there.
        """
        base_queryset = self.get_queryset()
        queryset = self.filter_queryset(base_queryset)
        return Response(
            {
                "total": queryset.count(),
                "facets": facet_counts(base_queryset, request.query_params),
            }
        )

    @extend_schema(
        summary="Export the current view",
        parameters=[
            OpenApiParameter("file_format", description="csv (default) or xlsx", required=False)
        ],
        responses={200: bytes},
    )
    @action(detail=False, methods=["get"])
    def export(self, request: Request) -> HttpResponse:
        """Export exactly the filtered result set, badges included."""
        queryset = self.filter_queryset(self.get_queryset())
        rows = [_export_row(job) for job in queryset]
        export_format = (request.query_params.get("file_format") or "csv").lower()
        record(EventKind.EXPORT, actor=request.user, rows=len(rows), file_format=export_format)

        if export_format == "xlsx":
            return _xlsx_response(rows)
        return _csv_response(rows)

    @extend_schema(
        summary="Add a job by hand",
        request=ManualJobSerializer,
        responses={201: JobDetailSerializer},
    )
    @action(detail=False, methods=["post"])
    def manual(self, request: Request) -> Response:
        """Create a job that the crawler cannot reach.

        Screened the same way as a crawled job and marked ``source = MANUAL``. It gets the same
        badges,
        and a crawl never closes it.
        """
        serializer = ManualJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        institution = data.pop("institution")
        _require_assigned(request.user, institution)

        from crawler.extraction import html_to_text
        from screening.services import active_profile, active_ruleset, criteria_from, screen_job

        description_html = data.pop("description_html", "")
        description_text = html_to_text(description_html)
        raw_fields = [data.get("contract_raw", ""), data.get("hours_raw", ""), description_text]
        combined = " ".join(filter(None, raw_fields))
        if not data.get("contract_type"):
            data["contract_type"] = classify_contract_type(data.get("contract_raw") or combined)
        if not data.get("hours"):
            data["hours"] = classify_hours(data.get("hours_raw") or combined)
        if not data.get("workplace"):
            data["workplace"] = classify_workplace(combined)
        if not data.get("discipline"):
            data["discipline"] = classify_discipline(
                data.get("title", ""), data.get("category", ""), data.get("department", "")
            )

        job = add_manual_job(
            institution_id=institution.pk,
            source_url=data.pop("source_url"),
            title=data.pop("title"),
            description_html=description_html,
            description_text=description_text,
            **data,
        )
        screen_job(
            job,
            ruleset=active_ruleset(),
            criteria=criteria_from(active_profile(request.user)),
        )

        job = Job.objects.with_related(for_user=request.user).get(pk=job.pk)
        return Response(JobDetailSerializer(job).data, status=status.HTTP_201_CREATED)

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return the filtered page, and record the search.

        Recorded after the page is built, using its real count, so the event shows how many results
        the person really saw.
        """
        response = super().list(request, *args, **kwargs)

        data = response.data if isinstance(response.data, dict) else {}
        record(
            EventKind.SEARCH,
            actor=request.user,
            query=request.query_params.get("q", ""),
            result_count=data.get("count"),
            filters=sorted(key for key in request.query_params if key not in {"q", "page"}),
        )
        return response

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return one vacancy, and record that it was looked at."""
        response = super().retrieve(request, *args, **kwargs)
        record(EventKind.JOB_VIEW, actor=request.user, job=self.get_object())
        return response

    def get_serializer_class(self):  # noqa: ANN201 - DRF signature
        """Use the editable serializer for a manual-job PATCH."""
        if self.action in {"update", "partial_update"}:
            return EditManualJobSerializer
        return JobDetailSerializer if self.action == "retrieve" else JobListSerializer

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Edit a manually added job. Refuses on a crawled one."""
        job = self.get_object()
        _require_assigned(request.user, job.institution)
        if job.source != JobSource.MANUAL:
            raise ConflictError(
                "This advert came from a crawl and is the employer's text. The next crawl would "
                "overwrite any edit made here.",
                extra={"use": "withdraw", "source": job.source},
            )

        serializer = EditManualJobSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        from screening.services import active_ruleset, screen_job

        job.refresh_from_db()
        screen_job(job, ruleset=active_ruleset())
        refresh_search_vectors(Job.objects.filter(pk=job.pk))

        job = Job.objects.with_related(for_user=request.user).get(pk=job.pk)
        return Response(JobDetailSerializer(job).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Delete a manually added job. Refuses on a crawled one."""
        job = self.get_object()
        _require_assigned(request.user, job.institution)
        try:
            delete_job(job)
        except CannotDeleteCrawledJob as error:
            raise ConflictError(str(error), extra={"use": "withdraw"}) from error
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Take a job down",
        request=WithdrawJobSerializer,
        responses={200: JobDetailSerializer},
    )
    @action(detail=True, methods=["post"])
    def withdraw(self, request: Request, pk: str | None = None) -> Response:
        """Withdraw a job, and record who did it and why.

        Later crawls keep it withdrawn, even if the advert is still listed.
        """
        serializer = WithdrawJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = self.get_object()
        _require_assigned(request.user, job.institution)
        withdraw_job(
            job,
            by=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        job = Job.objects.with_related(for_user=request.user).get(pk=pk)
        return Response(JobDetailSerializer(job).data)

    @extend_schema(summary="Undo a withdrawal", request=None, responses={200: JobDetailSerializer})
    @action(detail=True, methods=["post"])
    def reinstate(self, request: Request, pk: str | None = None) -> Response:
        """Put a withdrawn job back. A later crawl may still close it the ordinary way."""
        job = self.get_object()
        _require_assigned(request.user, job.institution)
        reinstate_job(job)
        job = Job.objects.with_related(for_user=request.user).get(pk=pk)
        return Response(JobDetailSerializer(job).data)

    @extend_schema(
        summary="Pre-fill a manual job from a URL",
        request=ExtractJobSerializer,
        responses={200: dict},
    )
    @action(detail=False, methods=["post"], url_path="extract")
    def extract(self, request: Request) -> Response:
        """Try to read a vacancy from a URL, to fill in the manual form.

        It may fail. Then it returns an empty draft and the reason, and the person can type the job
        in themselves.
        """
        serializer = ExtractJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        url = serializer.validated_data["url"]

        from crawler.adapters.base import BaseAdapter
        from crawler.exceptions import AdapterError
        from crawler.services import build_http_client

        http = build_http_client()
        try:
            vacancy = BaseAdapter(http=http).fetch_detail(url)
        except AdapterError as error:
            return Response(
                {
                    "extracted": False,
                    "reason": str(error),
                    "draft": {"source_url": url},
                }
            )
        finally:
            http.close()

        return Response(
            {
                "extracted": True,
                "draft": {
                    "source_url": vacancy.source_url,
                    "title": vacancy.title,
                    "department": vacancy.department,
                    "location_raw": vacancy.location_raw,
                    "salary_raw": vacancy.salary_raw,
                    "description_html": vacancy.description_html,
                    "closing_date": vacancy.closing_date,
                    "posted_date": vacancy.posted_date,
                    "reference": vacancy.reference,
                },
            }
        )


def _export_row(job: Job) -> dict[str, Any]:
    """Flatten one job for export, badges included as columns."""
    screening = getattr(job, "screening", None)
    return {
        "title": job.title,
        "institution": job.institution.name,
        "nation": job.institution.nation,
        "department": job.department,
        "location": job.location_raw or job.city,
        "salary_raw": job.salary_raw,
        "salary_min": screening.salary_min if screening else "",
        "salary_max": screening.salary_max if screening else "",
        "grade": job.grade_raw,
        "contract_raw": job.contract_raw,
        "hours_raw": job.hours_raw,
        "sponsor_verdict": screening.sponsor_verdict if screening else "",
        "sponsor_matched_name": screening.sponsor_matched_name if screening else "",
        "advert_excludes_sponsorship": (
            "yes" if screening and screening.advert_excludes_sponsorship else "no"
        ),
        "threshold_verdict": screening.threshold_verdict if screening else "",
        "fitness_score": getattr(job, "fitness_score", "") or "",
        "contract_type": job.contract_type,
        "hours": job.hours,
        "workplace": job.workplace,
        "posted_date": job.posted_date.isoformat() if job.posted_date else "",
        "closing_date": job.closing_date.isoformat() if job.closing_date else "",
        "status": job.status,
        "source_url": job.source_url,
    }


def _csv_response(rows: list[dict[str, Any]]) -> HttpResponse:
    """Render export rows as CSV."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _, label in EXPORT_COLUMNS])
    for row in rows:
        writer.writerow([row[key] for key, _ in EXPORT_COLUMNS])

    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="he-jobs.csv"'
    return response


def _xlsx_response(rows: list[dict[str, Any]]) -> HttpResponse:
    """Render export rows as XLSX."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Jobs"
    sheet.append([label for _, label in EXPORT_COLUMNS])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append([row[key] for key, _ in EXPORT_COLUMNS])
    sheet.freeze_panes = "A2"

    buffer = io.BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="he-jobs.xlsx"'
    return response
