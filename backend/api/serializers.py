"""Serializers.

The main rule: **a job with no screening row must not be shown.** A missing badge in a list
looks like "confirmed", which is the dangerous direction to be wrong in. So
:class:`JobListSerializer` raises an error instead of sending empty verdicts.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from crawler.models import CrawlLogEntry, CrawlRun, CrawlRunInstitution
from crawler.services import retriable_institution_ids
from institutions.models import Institution
from jobs.enums import ApplicationStatus, ContractType, Discipline, Hours, Workplace
from jobs.models import Application, ApplicationStatusEvent, Job, JobRevision, SavedJob, SavedSearch
from screening.models import (
    CandidateProfile,
    InstitutionSponsorMatch,
    JobScreening,
    Ruleset,
    RulesetFigure,
)


class UnscreenedJob(RuntimeError):
    """A job reached serialization without a screening row."""


class SponsorMatchSerializer(serializers.ModelSerializer[InstitutionSponsorMatch]):
    """The sponsor verdict for an institution, plus the candidates behind it."""

    class Meta:
        model = InstitutionSponsorMatch
        fields = [
            "registered_legal_name",
            "verdict",
            "method",
            "confidence",
            "candidates",
            "needs_review",
            "resolved_by_human",
            "resolved_at",
            "notes",
        ]
        read_only_fields = ["method", "confidence", "candidates", "resolved_at"]


class InstitutionSerializer(serializers.ModelSerializer[Institution]):
    """An institution as the crawl console shows it."""

    sponsor_match = SponsorMatchSerializer(read_only=True)
    effective_platform = serializers.CharField(read_only=True)
    last_crawl = serializers.SerializerMethodField()
    open_jobs = serializers.IntegerField(read_only=True, required=False)
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id",
            "slug",
            "name",
            "nation",
            "city",
            "institution_type",
            "ranking",
            "website",
            "careers_url",
            "platform",
            "adapter_override",
            "effective_platform",
            "crawl_enabled",
            "notes",
            "description",
            "contact_email",
            "contact_phone",
            "address",
            "logo_url",
            "banner_url",
            "sponsor_match",
            "last_crawl",
            "open_jobs",
        ]
        read_only_fields = ["id", "slug", "platform", "logo_url", "banner_url"]

    def get_logo_url(self, obj: Institution) -> str | None:
        """Where to fetch the logo, or ``None`` when there is not one."""
        return f"/api/institutions/{obj.pk}/logo/" if obj.logo else None

    def get_banner_url(self, obj: Institution) -> str | None:
        """Where to fetch the banner, or ``None`` when there is not one."""
        return f"/api/institutions/{obj.pk}/banner/" if obj.banner else None

    def get_last_crawl(self, obj: Institution) -> dict[str, Any] | None:
        """Summarise the latest crawl of this institution.

        Includes the previous vacancy count. "0 vacancies" means something very different if
        yesterday's number was 0 or 40.
        """
        results = getattr(obj, "recent_results", None)
        result = results[0] if results else obj.crawl_results.order_by("-started_at").first()
        if result is None:
            return None
        return {
            "run_id": result.run_id,
            "outcome": result.outcome,
            "adapter": result.adapter,
            "strategy": result.strategy,
            "vacancies_found": result.vacancies_found,
            "previous_vacancies_found": result.previous_vacancies_found,
            "dropped_to_zero": result.dropped_to_zero,
            "fallback_fired": result.fallback_fired,
            "error_class": result.error_class,
            "error_detail": result.error_detail,
            "started_at": result.started_at,
            "duration_ms": result.duration_ms,
        }


class InstitutionMediaSerializer(serializers.Serializer[dict[str, Any]]):
    """A logo, a banner, or both.

    `ImageField` opens the file to check it is a real image. It does not trust the file name.
    """

    logo = serializers.ImageField(required=False)
    banner = serializers.ImageField(required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Require at least one file, so an empty POST is a clear 400 rather than a silent no-op."""
        if not attrs.get("logo") and not attrs.get("banner"):
            raise serializers.ValidationError("Provide a logo, a banner, or both.")
        return attrs


class ResolveSponsorSerializer(serializers.Serializer[dict[str, Any]]):
    """A human's answer to "which legal entity is this?"."""

    registered_legal_name = serializers.CharField(max_length=500, allow_blank=True)
    verdict = serializers.ChoiceField(
        choices=[choice[0] for choice in InstitutionSponsorMatch._meta.get_field("verdict").choices]
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ScreeningSerializer(serializers.ModelSerializer[JobScreening]):
    """The two verdicts and everything needed to explain them."""

    ruleset_version = serializers.IntegerField(source="ruleset.version", read_only=True)

    class Meta:
        model = JobScreening
        fields = [
            "sponsor_verdict",
            "sponsor_matched_name",
            "sponsor_confidence",
            "advert_excludes_sponsorship",
            "advert_exclusion_phrase",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_period",
            "salary_confidence",
            "threshold_verdict",
            "threshold_explanation",
            "screened_on",
            "general_threshold_met",
            "going_rate_met",
            "going_rate_key",
            "ruleset_version",
            "screened_at",
        ]


class JobListSerializer(serializers.ModelSerializer[Job]):
    """A row in the job list. Always carries both badges."""

    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_slug = serializers.CharField(source="institution.slug", read_only=True)
    nation = serializers.CharField(source="institution.nation", read_only=True)
    screening = ScreeningSerializer(read_only=True)
    is_saved = serializers.BooleanField(read_only=True, default=False)
    fitness_score = serializers.IntegerField(read_only=True, default=0)
    fitness_reasons = serializers.JSONField(read_only=True, default=list)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "institution_name",
            "institution_slug",
            "nation",
            "department",
            "category",
            "discipline",
            "city",
            "location_raw",
            "salary_raw",
            "grade_raw",
            "contract_raw",
            "hours_raw",
            "contract_type",
            "hours",
            "workplace",
            "posted_date",
            "closing_date",
            "status",
            "source",
            "source_url",
            "first_seen_at",
            "last_seen_at",
            "screening",
            "is_saved",
            "fitness_score",
            "fitness_reasons",
        ]

    def to_representation(self, instance: Job) -> dict[str, Any]:
        """Refuse to show a job with no screening row.

        Failing loudly is on purpose. A job with an empty verdict among badged jobs would look safe.
        """
        screening = getattr(instance, "screening", None)
        if screening is None:
            raise UnscreenedJob(
                f"Job {instance.pk} has no screening row and must not be rendered. "
                "Run `manage.py rescreen`."
            )
        return super().to_representation(instance)


class JobDetailSerializer(JobListSerializer):
    """The detail view: everything in the list row, plus the advert itself."""

    apply_url = serializers.SerializerMethodField()
    revisions = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(read_only=True, default=None, allow_null=True)
    application_status = serializers.ChoiceField(
        choices=ApplicationStatus.choices(), read_only=True, default=None, allow_null=True
    )

    class Meta(JobListSerializer.Meta):
        fields = [
            *JobListSerializer.Meta.fields,
            "description_html",
            "description_text",
            "reference",
            "apply_url",
            "revisions",
            "disappeared_at",
            "application_id",
            "application_status",
        ]

    def get_apply_url(self, obj: Job) -> str:
        """The employer's own advert, exactly as crawled.

        Never a cached or proxied copy. This project never stands between a candidate and the
        employer's application form, so ``apply_url`` is always ``source_url``.
        """
        return obj.source_url

    def get_revisions(self, obj: Job) -> list[dict[str, Any]]:
        """The advert's change history, newest first."""
        return [
            {
                "field": revision.field,
                "before": revision.value_before,
                "after": revision.value_after,
                "changed_at": revision.changed_at,
            }
            for revision in obj.revisions.all()[:20]
        ]


class ManualJobSerializer(serializers.Serializer[dict[str, Any]]):
    """Adding a job by hand, for sites the crawler cannot reach.

    The same fields as :class:`EditManualJobSerializer`, so one form works for both. The four
    classified fields are optional. If left empty, the view works them out from the raw text, as
    it does for a crawled job.
    """

    institution = serializers.SlugRelatedField(
        slug_field="slug", queryset=Institution.objects.all()
    )
    source_url = serializers.URLField(max_length=1000)
    title = serializers.CharField(max_length=500)
    department = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    category = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    location_raw = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    salary_raw = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    grade_raw = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    contract_raw = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    hours_raw = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    contract_type = serializers.ChoiceField(
        choices=ContractType.values(), required=False, allow_blank=True, default=""
    )
    hours = serializers.ChoiceField(
        choices=Hours.values(), required=False, allow_blank=True, default=""
    )
    workplace = serializers.ChoiceField(
        choices=Workplace.values(), required=False, allow_blank=True, default=""
    )
    discipline = serializers.ChoiceField(
        choices=Discipline.values(), required=False, allow_blank=True, default=""
    )
    description_html = serializers.CharField(required=False, allow_blank=True, default="")
    closing_date = serializers.DateField(required=False, allow_null=True)
    posted_date = serializers.DateField(required=False, allow_null=True)


class EditManualJobSerializer(serializers.ModelSerializer[Job]):
    """The fields an admin may correct on a *manually added* job.

    Kept small on purpose. `source`, `source_url` and `institution` identify the job. Changing
    them would create a duplicate on the next crawl instead of an edit.
    """

    class Meta:
        model = Job
        fields = [
            "title",
            "department",
            "category",
            "reference",
            "description_html",
            "description_text",
            "location_raw",
            "city",
            "salary_raw",
            "grade_raw",
            "contract_raw",
            "hours_raw",
            "contract_type",
            "hours",
            "workplace",
            "discipline",
            "posted_date",
            "closing_date",
        ]


class WithdrawJobSerializer(serializers.Serializer[dict[str, str]]):
    """Why a job is being taken down."""

    reason = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class ExtractJobSerializer(serializers.Serializer[dict[str, Any]]):
    """Ask the system to pre-fill a manual job from a URL."""

    url = serializers.URLField(max_length=1000)


class OwnerScopedUniqueMixin:
    """Check a per-owner unique rule that DRF cannot see.

    ``owner`` is not a serializer field, because it comes from the request, never from the body.
    So DRF cannot check ``(owner, ...)`` itself, and a duplicate would cause a 500 instead of a 400.
    """

    unique_with_owner: str = ""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Reject a duplicate for this owner before the database has to."""
        attrs = super().validate(attrs)  # type: ignore[misc]

        request = self.context.get("request")  # type: ignore[attr-defined]
        value = attrs.get(self.unique_with_owner)
        if request is None or value is None:
            return attrs

        model = self.Meta.model  # type: ignore[attr-defined]
        clash = model.objects.filter(owner=request.user, **{self.unique_with_owner: value})
        if self.instance is not None:  # type: ignore[attr-defined]
            clash = clash.exclude(pk=self.instance.pk)  # type: ignore[attr-defined]

        if clash.exists():
            raise serializers.ValidationError(
                {self.unique_with_owner: "You already have one of these."}
            )
        return attrs


class SavedJobSerializer(OwnerScopedUniqueMixin, serializers.ModelSerializer[SavedJob]):
    """A saved job, with enough of the job to render the saved view."""

    job_detail = JobListSerializer(source="job", read_only=True)
    unique_with_owner = "job"

    class Meta:
        model = SavedJob
        fields = ["id", "job", "job_detail", "tags", "note", "saved_at"]
        read_only_fields = ["id", "saved_at"]


class ApplicationStatusEventSerializer(serializers.ModelSerializer[ApplicationStatusEvent]):
    """One transition on the pipeline board."""

    class Meta:
        model = ApplicationStatusEvent
        fields = ["from_status", "to_status", "occurred_at", "note"]


class ApplicationSerializer(OwnerScopedUniqueMixin, serializers.ModelSerializer[Application]):
    """A tracked application."""

    job_detail = JobListSerializer(source="job", read_only=True)
    status_events = ApplicationStatusEventSerializer(many=True, read_only=True)
    unique_with_owner = "job"

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "job_detail",
            "status",
            "applied_at",
            "response_at",
            "next_action",
            "next_action_due",
            "notes",
            "ghosted_flagged",
            "status_events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "ghosted_flagged", "status_events"]


class SavedSearchSerializer(OwnerScopedUniqueMixin, serializers.ModelSerializer[SavedSearch]):
    """A named filter set."""

    unique_with_owner = "name"

    class Meta:
        model = SavedSearch
        fields = ["id", "name", "query", "digest_enabled", "created_at", "last_run_at"]
        read_only_fields = ["id", "created_at", "last_run_at"]


class CrawlRunInstitutionSerializer(serializers.ModelSerializer[CrawlRunInstitution]):
    """One institution's row in a run."""

    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_slug = serializers.CharField(source="institution.slug", read_only=True)
    dropped_to_zero = serializers.BooleanField(read_only=True)
    permits_closure = serializers.BooleanField(read_only=True)

    class Meta:
        model = CrawlRunInstitution
        fields = [
            "id",
            "institution",
            "institution_name",
            "institution_slug",
            "adapter",
            "outcome",
            "strategy",
            "fallback_fired",
            "vacancies_found",
            "previous_vacancies_found",
            "dropped_to_zero",
            "permits_closure",
            "jobs_new",
            "jobs_updated",
            "jobs_closed",
            "duration_ms",
            "error_class",
            "error_detail",
            "raw_cache_keys",
            "started_at",
            "finished_at",
        ]


class CrawlLogEntrySerializer(serializers.ModelSerializer[CrawlLogEntry]):
    """One line of a run's persisted log."""

    institution_name = serializers.CharField(
        source="institution.name", read_only=True, default=None, allow_null=True
    )

    class Meta:
        model = CrawlLogEntry
        fields = [
            "id",
            "level",
            "message",
            "extra",
            "institution",
            "institution_name",
            "created_at",
        ]


class CrawlRunSerializer(serializers.ModelSerializer[CrawlRun]):
    """A run summary.

    Kept cheap, because the run list and the polling check use it. No extra query per run.
    ``retriable_count`` needs its own query, so it is only on :class:`CrawlRunDetailSerializer`.
    """

    duration_seconds = serializers.FloatField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = CrawlRun
        fields = [
            "id",
            "trigger",
            "status",
            "is_active",
            "started_at",
            "finished_at",
            "duration_seconds",
            "institutions_total",
            "institutions_done",
            "jobs_new",
            "jobs_updated",
            "jobs_closed",
            "error_detail",
        ]


class CrawlRunDetailSerializer(CrawlRunSerializer):
    """A run with every institution result attached."""

    institution_results = CrawlRunInstitutionSerializer(many=True, read_only=True)
    retriable_count = serializers.SerializerMethodField()

    def get_retriable_count(self, run: CrawlRun) -> int:
        """How many institutions in this run did not come back OK.

        Used by the "Retry failures" button on the run page and its label.
        """
        return len(retriable_institution_ids(run))

    class Meta(CrawlRunSerializer.Meta):
        fields = [*CrawlRunSerializer.Meta.fields, "institution_results", "retriable_count"]


class StartCrawlSerializer(serializers.Serializer[dict[str, Any]]):
    """Request body for starting a run."""

    institutions = serializers.ListField(
        child=serializers.SlugField(), required=False, default=list
    )


class RestartCrawlSerializer(serializers.Serializer[dict[str, Any]]):
    """Request body for restarting a run.

    Required, with no default. "All" or "failures" is the choice the crawl console asks the user
    to make, and a default would make it for them.
    """

    scope = serializers.ChoiceField(choices=["all", "failures"])


class JobRevisionSerializer(serializers.ModelSerializer[JobRevision]):
    """A before/after pair for the Changed tab."""

    job_title = serializers.CharField(source="job.title", read_only=True)
    institution_name = serializers.CharField(source="job.institution.name", read_only=True)

    class Meta:
        model = JobRevision
        fields = [
            "id",
            "job",
            "job_title",
            "institution_name",
            "field",
            "value_before",
            "value_after",
            "changed_at",
        ]


class RulesetFigureSerializer(serializers.ModelSerializer[RulesetFigure]):
    """One threshold figure."""

    class Meta:
        model = RulesetFigure
        fields = ["key", "value", "note"]


class RulesetSerializer(serializers.ModelSerializer[Ruleset]):
    """A versioned ruleset with its figures."""

    figures = RulesetFigureSerializer(many=True, read_only=True)

    class Meta:
        model = Ruleset
        fields = [
            "id",
            "version",
            "name",
            "effective_from",
            "verified_at",
            "source_url",
            "notes",
            "is_active",
            "created_at",
            "figures",
        ]
        read_only_fields = ["id", "version", "created_at"]


class CreateRulesetSerializer(serializers.Serializer[dict[str, Any]]):
    """Creating a **new version**. Rulesets are never edited in place."""

    name = serializers.CharField(max_length=200)
    effective_from = serializers.DateField()
    verified_at = serializers.DateField()
    source_url = serializers.URLField(max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    activate = serializers.BooleanField(default=True)
    figures = serializers.DictField(child=serializers.DecimalField(max_digits=12, decimal_places=2))

    def validate_figures(self, value: dict[str, Any]) -> dict[str, Any]:
        """Reject a ruleset that cannot place a salary in a band.

        A missing ``personal_floor`` would mark every job as a pay cut, so it is caught here.
        """
        from screening.services import required_figure_keys

        missing = set(required_figure_keys()) - set(value)
        if missing:
            raise serializers.ValidationError(f"Missing figures: {sorted(missing)}")
        return value


class CandidateProfileSerializer(serializers.ModelSerializer[CandidateProfile]):
    """The profile fitness is scored against."""

    class Meta:
        model = CandidateProfile
        fields = [
            "id",
            "name",
            "skills",
            "domains",
            "seniority",
            "projects",
            "education",
            "years_experience",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
