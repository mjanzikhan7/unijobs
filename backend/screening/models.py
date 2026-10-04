"""Screening records: the sponsor register, the rulesets, and one verdict row per job.

Two things here never change once saved. A :class:`Ruleset` is never edited: a new figure
means a new version, so an August verdict can still be explained in November. A
:class:`SponsorRegisterSnapshot` is never overwritten, so we can see when an employer left the
register.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone

from institutions.models import Institution
from jobs.models import Job
from screening.domain import Thresholds
from screening.enums import (
    MatchMethod,
    RulesetFigureKey,
    SalaryConfidence,
    SalaryPeriod,
    SkillTermKind,
    SponsorVerdict,
    ThresholdVerdict,
)


class MissingRulesetFigure(LookupError):
    """A ruleset does not carry a figure the screener needs."""


class SponsorRegisterSnapshot(models.Model):
    """One download of the GOV.UK register of licensed sponsors.

    Snapshots are kept. Comparing the newest with the one before shows which employers left.
    """

    downloaded_at = models.DateTimeField(default=timezone.now)
    source_url = models.URLField(max_length=500)
    row_count = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-downloaded_at"]

    def __str__(self) -> str:
        """Return the snapshot date and size."""
        return f"Register snapshot {self.downloaded_at:%Y-%m-%d} ({self.row_count} rows)"


class SponsorRegisterEntry(models.Model):
    """One organisation on the register, as it appears in the CSV.

    ``organisation_name`` is the legal name, which is often not the everyday name. Birkbeck is
    "Birkbeck College", and Imperial is "Imperial College London (HR)".
    """

    snapshot = models.ForeignKey(
        SponsorRegisterSnapshot, on_delete=models.CASCADE, related_name="entries"
    )
    organisation_name = models.CharField(max_length=500)
    normalised_name = models.CharField(max_length=500, db_index=True)
    town_city = models.CharField(max_length=200, blank=True)
    county = models.CharField(max_length=200, blank=True)
    type_rating = models.CharField(max_length=300, blank=True)
    route = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name_plural = "sponsor register entries"
        indexes = [
            models.Index(fields=["snapshot", "organisation_name"]),
            GinIndex(
                name="sponsor_name_trgm",
                fields=["organisation_name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        """Return the registered name."""
        return self.organisation_name


class InstitutionSponsorMatch(models.Model):
    """The answer to "can this employer sponsor?", asked once and saved.

    It lives in :mod:`screening`, not on :class:`~institutions.models.Institution`, because
    ``institutions`` must not depend on ``screening``.
    """

    institution = models.OneToOneField(
        Institution, on_delete=models.CASCADE, related_name="sponsor_match"
    )
    snapshot = models.ForeignKey(
        SponsorRegisterSnapshot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches",
    )
    registered_legal_name = models.CharField(max_length=500, blank=True)
    verdict = models.CharField(
        max_length=32, choices=SponsorVerdict.choices(), default=SponsorVerdict.NOT_FOUND
    )
    method = models.CharField(
        max_length=16, choices=MatchMethod.choices(), default=MatchMethod.NONE
    )
    confidence = models.FloatField(default=0.0)
    candidates = models.JSONField(
        default=list,
        blank=True,
        help_text="Ranked register entries for a human to choose from, when nothing matched "
        "confidently enough to decide automatically.",
    )
    needs_review = models.BooleanField(default=False)
    resolved_by_human = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "institution sponsor matches"
        indexes = [
            models.Index(fields=["verdict"]),
            models.Index(fields=["needs_review"]),
        ]

    def __str__(self) -> str:
        """Return the institution and its verdict."""
        return f"{self.institution_id}: {self.verdict}"


class Ruleset(models.Model):
    """A versioned set of threshold figures.

    Never edited. ``POST /api/rulesets/`` creates a new version, so ``JobScreening.ruleset``
    always points to the rules that were in force when the verdict was made.
    """

    version = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200)
    effective_from = models.DateField()
    verified_at = models.DateField(
        help_text="When a human last checked these figures against the source."
    )
    source_url = models.URLField(max_length=500)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="only_one_active_ruleset",
            )
        ]

    def __str__(self) -> str:
        """Return the version and name."""
        return f"v{self.version} — {self.name}"

    def figure(self, key: RulesetFigureKey | str) -> Decimal:
        """Return one figure, and raise an error if the ruleset does not have it.

        A missing figure must fail loudly. Treating a missing floor as zero would mark every job as
        a
        pay cut, and hide the real problem.
        """
        try:
            return self.figures.get(key=str(key)).value
        except RulesetFigure.DoesNotExist as exc:
            raise MissingRulesetFigure(f"Ruleset v{self.version} has no figure {key!r}") from exc

    def thresholds(
        self, going_rate_key: RulesetFigureKey | str = RulesetFigureKey.SOC_2134_GOING_RATE
    ) -> Thresholds:
        """Build the pure domain version of this ruleset.

        After this point everything is a plain function over plain values.
        """
        return Thresholds(
            personal_floor=self.figure(RulesetFigureKey.PERSONAL_FLOOR),
            current_package=self.figure(RulesetFigureKey.CURRENT_PACKAGE),
            going_rate=self.figure(going_rate_key),
            standard_general=self.figure(RulesetFigureKey.STANDARD_GENERAL_THRESHOLD),
            transitional_general=self.figure(RulesetFigureKey.TRANSITIONAL_GENERAL_THRESHOLD),
            going_rate_key=str(going_rate_key),
        )


class RulesetFigure(models.Model):
    """One threshold figure, in pounds.

    Figures live only here. A threshold written in Python would be wrong the day the rules
    change, and nobody would remember to look for it.
    """

    ruleset = models.ForeignKey(Ruleset, on_delete=models.CASCADE, related_name="figures")
    key = models.CharField(max_length=64, choices=RulesetFigureKey.choices())
    value = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ruleset", "key"], name="unique_figure_per_ruleset")
        ]
        ordering = ["ruleset", "key"]

    def __str__(self) -> str:
        """Return the key and value."""
        return f"{self.key} = {self.value}"


class CandidateProfile(models.Model):
    """One candidate's profile, used for fitness scoring.

    ``is_active`` marks the profile in use, so an older one can be kept for comparison.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profiles"
    )
    name = models.CharField(max_length=200, default="Default profile")
    skills = models.JSONField(default=list, blank=True)
    domains = models.JSONField(default=list, blank=True)
    seniority = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(is_active=True),
                name="one_active_profile_per_owner",
            )
        ]

    def __str__(self) -> str:
        """Return the profile name."""
        return self.name


class JobScreening(models.Model):
    """One verdict row per job. A job shown in the UI always has one.

    A missing badge would look like "confirmed" to someone reading a list quickly. That is the
    dangerous direction to be wrong in, so the serializer refuses a job with no screening row.
    """

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="screening")
    ruleset = models.ForeignKey(Ruleset, on_delete=models.PROTECT, related_name="screenings")

    sponsor_verdict = models.CharField(max_length=32, choices=SponsorVerdict.choices())
    sponsor_matched_name = models.CharField(max_length=500, blank=True)
    sponsor_confidence = models.FloatField(default=0.0)

    advert_excludes_sponsorship = models.BooleanField(default=False)
    advert_exclusion_phrase = models.TextField(blank=True)

    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="GBP")
    salary_period = models.CharField(
        max_length=16, choices=SalaryPeriod.choices(), default=SalaryPeriod.UNKNOWN
    )
    salary_confidence = models.CharField(
        max_length=16, choices=SalaryConfidence.choices(), default=SalaryConfidence.UNPARSEABLE
    )

    threshold_verdict = models.CharField(max_length=32, choices=ThresholdVerdict.choices())
    threshold_explanation = models.TextField(blank=True)
    screened_on = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    general_threshold_met = models.BooleanField(null=True)
    going_rate_met = models.BooleanField(null=True)
    going_rate_key = models.CharField(max_length=64, blank=True)

    screened_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["sponsor_verdict"]),
            models.Index(fields=["threshold_verdict"]),
            models.Index(fields=["salary_min"]),
        ]

    def __str__(self) -> str:
        """Return the two verdicts."""
        return f"job {self.job_id}: {self.sponsor_verdict} / {self.threshold_verdict}"


def cv_upload_path(instance: CV, filename: str) -> str:
    """Return where an uploaded CV is stored.

    The uploaded file name is never used for the path. It is chosen by the user, so it could try
    ``../../``, clash with another file, or contain a name ("Jane Smith CV.pdf"). The original
    name is kept in its own column, only for display.
    """
    import uuid

    suffix = "pdf" if filename.lower().endswith(".pdf") else "docx"
    return f"cv/{instance.owner_id}/{uuid.uuid4().hex}.{suffix}"


class CV(models.Model):
    """One candidate's uploaded CV, and the text read from it.

    The file never has a public URL. The only way to read it is a signed-in view that checks the
    owner.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cvs"
    )
    file = models.FileField(upload_to=cv_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=16, blank=True)
    byte_size = models.PositiveIntegerField(default=0)

    extracted_text = models.TextField(blank=True)
    suggestions = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["owner", "-uploaded_at"], name="screening_cv_owner_idx")]

    def __str__(self) -> str:
        """Return the display name and who it belongs to."""
        return f"{self.original_filename or 'CV'} (user {self.owner_id})"

    def delete(
        self, using: str | None = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        """Delete the row and its file.

        Django does not delete files when a row is deleted. Without this, the CV would stay on disk
        after the account is gone.
        """
        stored = self.file
        result = super().delete(using=using, keep_parents=keep_parents)
        if stored:
            stored.delete(save=False)
        return result


class SkillTerm(models.Model):
    """One term the CV parser looks for.

    Data, not code. Adding "kubernetes" is a new row, not a deployment.
    """

    canonical = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=16, choices=SkillTermKind.choices())
    aliases = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["kind", "canonical"]
        indexes = [models.Index(fields=["kind"])]

    def __str__(self) -> str:
        """Return the term and its kind."""
        return f"{self.canonical} ({self.kind})"


class JobFitness(models.Model):
    """How well one job matches one candidate's profile.

    Separate from :class:`JobScreening` on purpose. Sponsor and threshold verdicts are facts
    about the advert and are the same for everybody. Fitness depends on one person's profile.
    """

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="fitness")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_fitness"
    )

    score = models.PositiveSmallIntegerField(default=0)
    reasons = models.JSONField(default=list, blank=True)

    criteria_hash = models.CharField(max_length=64, blank=True)
    scored_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "job fitness"
        constraints = [
            models.UniqueConstraint(fields=["owner", "job"], name="unique_fitness_per_owner_job")
        ]
        indexes = [
            models.Index(fields=["owner", "-score"], name="screening_fit_owner_score_idx"),
        ]

    def __str__(self) -> str:
        """Return the score and who it is for."""
        return f"job {self.job_id} scores {self.score} for user {self.owner_id}"
