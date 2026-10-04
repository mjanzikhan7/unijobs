"""Screening use cases: saving verdicts, matching sponsors to the register, re-screening.

The decisions are made in :mod:`screening.domain`. This module loads the right rows, passes
them to a pure function, and saves the answer with the ruleset version that produced it. That
way a verdict can still be explained after the rules change.

Re-screening never uses the network. It only recalculates from stored data.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from datetime import UTC, date, datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone as django_timezone

from institutions.models import Institution
from jobs.models import Job
from screening.cv_domain import ExtractedCriteria, VocabularyTerm, extract_terms
from screening.cv_text import extract_text as extract_cv_text
from screening.domain import (
    CandidateCriteria,
    RegisterCandidate,
    SponsorDecision,
    apply_advert_exclusion,
    core_tokens,
    decide_sponsor_match,
    evaluate_threshold,
    find_sponsorship_exclusion,
    normalise_organisation_name,
    parse_salary,
    score_fitness,
)
from screening.enums import MatchMethod, RulesetFigureKey, SponsorVerdict
from screening.models import (
    CV,
    CandidateProfile,
    InstitutionSponsorMatch,
    JobFitness,
    JobScreening,
    Ruleset,
    SkillTerm,
    SponsorRegisterEntry,
    SponsorRegisterSnapshot,
)

logger = logging.getLogger(__name__)

CANDIDATE_LIMIT = 8


class NoActiveRuleset(RuntimeError):
    """Nothing can be screened without a ruleset. Run ``make seed``."""


def active_ruleset() -> Ruleset:
    """Return the ruleset in force now.

    Raises an error instead of using the newest row. A verdict from a random ruleset could not
    be explained.
    """
    ruleset = Ruleset.objects.filter(is_active=True).prefetch_related("figures").first()
    if ruleset is None:
        raise NoActiveRuleset("No active ruleset. Run `make seed` to load the current figures.")
    return ruleset


def active_profile(owner: User | None = None) -> CandidateProfile | None:
    """Return the profile used to score fitness for one candidate, if there is one.

    ``owner`` is optional for callers with no user, such as the crawl. They get no profile, never
    someone else's: scoring one person against another person's profile is worse than no score.
    """
    if owner is None:
        return None
    return CandidateProfile.objects.filter(is_active=True, owner=owner).first()


def criteria_from(profile: CandidateProfile | None) -> CandidateCriteria:
    """Flatten a stored profile into the pure-domain criteria object."""
    if profile is None:
        return CandidateCriteria()
    return CandidateCriteria(
        skills=tuple(profile.skills or ()),
        domains=tuple(profile.domains or ()),
        seniority=tuple(profile.seniority or ()),
        projects=tuple(profile.projects or ()),
        education=tuple(profile.education or ()),
        years_experience=profile.years_experience,
    )


def latest_snapshot() -> SponsorRegisterSnapshot | None:
    """Return the most recent register download."""
    return SponsorRegisterSnapshot.objects.order_by("-downloaded_at").first()


def register_candidates(
    name: str, snapshot: SponsorRegisterSnapshot, *, limit: int = CANDIDATE_LIMIT
) -> list[RegisterCandidate]:
    """Return the register entries most likely to be ``name``.

    Two filters joined with OR: trigram similarity finds spelling differences, and a shared
    identifying word finds a short legal name inside a long one ("Birkbeck College" and
    "Birkbeck, University of London"). Both run in PostgreSQL, because the register has about
    142,000 rows.
    """
    threshold = float(getattr(settings, "SPONSOR_TRIGRAM_THRESHOLD", 0.62))
    tokens = sorted(core_tokens(name), key=len, reverse=True)[:2]

    token_match = Q()
    for token in tokens:
        if len(token) >= 4:
            token_match |= Q(organisation_name__icontains=token)

    rows = (
        SponsorRegisterEntry.objects.filter(snapshot=snapshot)
        .annotate(similarity=TrigramSimilarity("organisation_name", name))
        .filter(Q(similarity__gte=threshold * 0.5) | token_match)
        .order_by("-similarity")[:limit]
    )
    return [
        RegisterCandidate(
            organisation_name=row.organisation_name,
            town_city=row.town_city,
            type_rating=row.type_rating,
            routes=tuple(part.strip() for part in row.route.split(";") if part.strip()),
            similarity=float(row.similarity),
        )
        for row in rows
    ]


def search_register(
    query: str, snapshot: SponsorRegisterSnapshot | None = None, *, limit: int = 25
) -> list[RegisterCandidate]:
    """Free-text search of the register, for a person resolving a match by hand.

    Some institutions are sponsored by a parent body with a different name. For example, UK
    Research and Innovation sponsors the MRC Laboratory of Molecular Biology. No matcher finds
    that, but a person searching can.
    """
    snapshot = snapshot or latest_snapshot()
    if snapshot is None or not query.strip():
        return []

    rows = (
        SponsorRegisterEntry.objects.filter(snapshot=snapshot)
        .annotate(similarity=TrigramSimilarity("organisation_name", query))
        .filter(Q(organisation_name__icontains=query.strip()) | Q(similarity__gte=0.3))
        .order_by("-similarity", "organisation_name")[:limit]
    )
    return [
        RegisterCandidate(
            organisation_name=row.organisation_name,
            town_city=row.town_city,
            type_rating=row.type_rating,
            routes=tuple(part.strip() for part in row.route.split(";") if part.strip()),
            similarity=float(row.similarity),
        )
        for row in rows
    ]


def match_institution(
    institution: Institution, snapshot: SponsorRegisterSnapshot | None = None
) -> InstitutionSponsorMatch:
    """Run the matching steps for one institution and save the answer.

    A match that a person already resolved is left alone, so the question is asked only once.
    """
    match, _ = InstitutionSponsorMatch.objects.get_or_create(institution=institution)
    if match.resolved_by_human:
        return match

    snapshot = snapshot or latest_snapshot()
    if snapshot is None:
        return match

    candidates = register_candidates(institution.name, snapshot)
    decision = decide_sponsor_match(
        institution.name,
        candidates,
        similarity_threshold=float(getattr(settings, "SPONSOR_TRIGRAM_THRESHOLD", 0.62)),
    )
    _apply_decision(match, decision, snapshot)
    return match


def _apply_decision(
    match: InstitutionSponsorMatch,
    decision: SponsorDecision,
    snapshot: SponsorRegisterSnapshot,
) -> None:
    """Write a matcher decision onto the stored match row."""
    match.snapshot = snapshot
    match.verdict = decision.verdict
    match.registered_legal_name = decision.matched_name or ""
    match.method = decision.method
    match.confidence = decision.confidence
    match.candidates = [asdict(candidate) for candidate in decision.candidates]
    match.needs_review = decision.needs_review
    match.save()


def resolve_sponsor_match(
    institution: Institution,
    *,
    registered_legal_name: str,
    verdict: SponsorVerdict,
    notes: str = "",
) -> InstitutionSponsorMatch:
    """Save a person's decision about which legal entity an institution is.

    Saved with ``resolved_by_human``, so the matcher never overwrites it, even after a register
    refresh changes the scores.
    """
    match, _ = InstitutionSponsorMatch.objects.get_or_create(institution=institution)
    match.registered_legal_name = registered_legal_name
    match.verdict = verdict
    match.method = MatchMethod.HUMAN
    match.confidence = 1.0
    match.needs_review = False
    match.resolved_by_human = True
    match.resolved_at = django_timezone.now()
    if notes:
        match.notes = notes
    match.save()
    return match


def seed_sponsor_match(
    institution: Institution,
    *,
    registered_legal_name: str,
    verdict: SponsorVerdict,
    needs_review: bool,
) -> InstitutionSponsorMatch:
    """Save a match that came from the institutions spreadsheet.

    These are not marked as resolved by a person, so a register refresh still checks them again.
    They keep the review queue short: about a dozen institutions instead of all 167.
    """
    match, _ = InstitutionSponsorMatch.objects.get_or_create(institution=institution)
    if match.resolved_by_human:
        return match
    match.registered_legal_name = registered_legal_name
    match.verdict = verdict
    match.method = MatchMethod.SEED
    match.confidence = 1.0 if registered_legal_name else 0.0
    match.needs_review = needs_review
    match.save()
    return match


@transaction.atomic
def load_register_snapshot(
    rows: Iterable[dict[str, str]], *, source_url: str, notes: str = ""
) -> SponsorRegisterSnapshot:
    """Load a GOV.UK register CSV as a **new** snapshot, and keep the old ones.

    Never update in place. An employer on the register in August may be gone in November, and we
    can only show that if we still have August.
    """
    snapshot = SponsorRegisterSnapshot.objects.create(source_url=source_url, notes=notes)
    digest = hashlib.sha256()
    entries: list[SponsorRegisterEntry] = []

    for row in rows:
        name = (row.get("Organisation Name") or row.get("organisation_name") or "").strip()
        if not name:
            continue
        digest.update(name.encode("utf-8"))
        entries.append(
            SponsorRegisterEntry(
                snapshot=snapshot,
                organisation_name=name,
                normalised_name=normalise_organisation_name(name),
                town_city=(row.get("Town/City") or row.get("town_city") or "").strip(),
                county=(row.get("County") or row.get("county") or "").strip(),
                type_rating=(row.get("Type & Rating") or row.get("type_rating") or "").strip(),
                route=(row.get("Route") or row.get("route") or "").strip(),
            )
        )

    SponsorRegisterEntry.objects.bulk_create(entries, batch_size=2000)
    snapshot.row_count = len(entries)
    snapshot.sha256 = digest.hexdigest()
    snapshot.save(update_fields=["row_count", "sha256"])
    return snapshot


def compare_snapshots(
    previous: SponsorRegisterSnapshot, current: SponsorRegisterSnapshot
) -> dict[str, list[str]]:
    """Report which matched employers are in one snapshot but not the other.

    It is better to know an employer left the register before a job offer, not after.
    """
    matched_names = set(
        InstitutionSponsorMatch.objects.exclude(registered_legal_name="").values_list(
            "registered_legal_name", flat=True
        )
    )
    previous_names = set(
        SponsorRegisterEntry.objects.filter(
            snapshot=previous, organisation_name__in=matched_names
        ).values_list("organisation_name", flat=True)
    )
    current_names = set(
        SponsorRegisterEntry.objects.filter(
            snapshot=current, organisation_name__in=matched_names
        ).values_list("organisation_name", flat=True)
    )
    return {
        "dropped_off": sorted(previous_names - current_names),
        "newly_listed": sorted(current_names - previous_names),
    }


def screen_job(
    job: Job,
    *,
    ruleset: Ruleset,
    criteria: CandidateCriteria | None = None,
    sponsor_match: InstitutionSponsorMatch | None = None,
    now: datetime | None = None,
) -> JobScreening:
    """Calculate and save the objective verdicts for one job.

    The register decides the sponsor verdict, then the advert may overrule it. Never the other way.
    ``criteria`` is no longer used (fitness is per candidate, see :func:`score_fitness_for`). It
    stays so existing callers do not need to change.
    """
    match = sponsor_match or getattr(job.institution, "sponsor_match", None)
    register_verdict = SponsorVerdict(match.verdict) if match else SponsorVerdict.NOT_FOUND

    advert_text = ". ".join(filter(None, [job.title, job.description_text]))
    exclusion_phrase = find_sponsorship_exclusion(advert_text)
    sponsor_verdict = apply_advert_exclusion(register_verdict, exclusion_phrase is not None)

    salary = parse_salary(job.salary_raw)
    assessment = evaluate_threshold(salary, ruleset.thresholds())

    screening, _ = JobScreening.objects.update_or_create(
        job=job,
        defaults={
            "ruleset": ruleset,
            "sponsor_verdict": sponsor_verdict,
            "sponsor_matched_name": match.registered_legal_name if match else "",
            "sponsor_confidence": match.confidence if match else 0.0,
            "advert_excludes_sponsorship": exclusion_phrase is not None,
            "advert_exclusion_phrase": exclusion_phrase or "",
            "salary_min": salary.minimum,
            "salary_max": salary.maximum,
            "salary_currency": salary.currency,
            "salary_period": salary.period,
            "salary_confidence": salary.confidence,
            "threshold_verdict": assessment.verdict,
            "threshold_explanation": assessment.explanation,
            "screened_on": assessment.screened_on,
            "general_threshold_met": assessment.general_threshold_met,
            "going_rate_met": assessment.going_rate_met,
            "going_rate_key": assessment.going_rate_key,
            "screened_at": now or django_timezone.now(),
        },
    )

    if salary.grade and job.grade_raw != salary.grade:
        job.grade_raw = salary.grade
        job.save(update_fields=["grade_raw"])

    return screening


def screen_jobs(
    jobs: QuerySet[Job] | Sequence[Job], *, ruleset: Ruleset | None = None
) -> dict[str, int]:
    """Screen a set of jobs and return how many verdicts changed.

    No network calls: every input is already stored.
    """
    ruleset = ruleset or active_ruleset()

    if isinstance(jobs, QuerySet):
        jobs = jobs.select_related("institution", "institution__sponsor_match")

    changed = 0
    total = 0
    for job in jobs:
        total += 1
        previous = getattr(job, "screening", None)
        before = (
            (previous.sponsor_verdict, previous.threshold_verdict) if previous else (None, None)
        )
        screening = screen_job(job, ruleset=ruleset)
        if before != (screening.sponsor_verdict, screening.threshold_verdict):
            changed += 1

    return {"screened": total, "changed": changed}


def rescreen_all(ruleset: Ruleset | None = None) -> dict[str, int]:
    """Recalculate every verdict against ``ruleset``.

    Used after a threshold change. Old rows keep their own ``ruleset_version`` until they are
    recalculated, so each one can still be explained.
    """
    return screen_jobs(Job.objects.all(), ruleset=ruleset)


def criteria_fingerprint(criteria: CandidateCriteria) -> str:
    """Hash the criteria a score was calculated from.

    A re-score can then skip jobs whose score cannot have changed, instead of rewriting a row
    for every job.
    """
    payload = json.dumps(asdict(criteria), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score_fitness_for(
    owner: User,
    jobs: QuerySet[Job] | Sequence[Job] | None = None,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Score jobs against one candidate's active profile.

    Returns how many jobs were checked and how many changed. With no profile, all scores are
    removed, so no old score is left behind.
    """
    profile = active_profile(owner)
    if profile is None:
        removed, _ = JobFitness.objects.filter(owner=owner).delete()
        return {"scored": 0, "changed": removed}

    criteria = criteria_from(profile)
    fingerprint = criteria_fingerprint(criteria)

    queryset = Job.objects.all() if jobs is None else jobs
    if isinstance(queryset, QuerySet):
        queryset = queryset.only("id", "title", "description_text")

    existing = {
        row.job_id: row
        for row in JobFitness.objects.filter(owner=owner, job__in=[job.pk for job in queryset])
    }

    scored = 0
    changed = 0
    now = django_timezone.now()

    for job in queryset:
        scored += 1
        current = existing.get(job.pk)
        if not force and current is not None and current.criteria_hash == fingerprint:
            continue

        result = score_fitness(". ".join(filter(None, [job.title, job.description_text])), criteria)
        JobFitness.objects.update_or_create(
            owner=owner,
            job=job,
            defaults={
                "score": result.score,
                "reasons": [asdict(reason) for reason in result.reasons],
                "criteria_hash": fingerprint,
                "scored_at": now,
            },
        )
        changed += 1

    return {"scored": scored, "changed": changed}


def create_ruleset_version(
    *,
    name: str,
    effective_from: date,
    verified_at: date,
    source_url: str,
    figures: dict[str, str],
    notes: str = "",
    activate: bool = True,
) -> Ruleset:
    """Create a new ruleset version instead of editing the current one.

    Threshold figures change. An old verdict must stay explainable, which is impossible if the
    row it points to has been changed.
    """
    from decimal import Decimal

    from screening.models import RulesetFigure

    with transaction.atomic():
        highest = Ruleset.objects.order_by("-version").values_list("version", flat=True).first()
        next_version = (highest or 0) + 1
        if activate:
            Ruleset.objects.filter(is_active=True).update(is_active=False)
        ruleset = Ruleset.objects.create(
            version=next_version,
            name=name,
            effective_from=effective_from,
            verified_at=verified_at,
            source_url=source_url,
            notes=notes,
            is_active=activate,
        )
        RulesetFigure.objects.bulk_create(
            [
                RulesetFigure(ruleset=ruleset, key=str(key), value=Decimal(str(value)))
                for key, value in figures.items()
            ]
        )
    return ruleset


def required_figure_keys() -> tuple[str, ...]:
    """The figures a ruleset must carry to be usable."""
    return tuple(key.value for key in RulesetFigureKey)


def utc_now() -> datetime:
    """Return an aware UTC timestamp. Exists so callers never build a naive one."""
    return datetime.now(tz=UTC)


def active_vocabulary() -> tuple[VocabularyTerm, ...]:
    """Load the CV parser's word list from the database.

    A table, not a constant, so adding a term does not need a deployment.
    """
    return tuple(
        VocabularyTerm(
            canonical=term.canonical,
            kind=term.kind,
            aliases=tuple(str(alias) for alias in (term.aliases or ())),
        )
        for term in SkillTerm.objects.filter(is_active=True)
    )


def parse_cv(cv: CV) -> ExtractedCriteria:
    """Read an uploaded CV and save what it suggests.

    Only suggestions. The candidate confirms or edits them. Writing them straight to the profile
    could overwrite careful manual work.
    """
    text = extract_cv_text(cv.file.read())
    extracted = extract_terms(text, active_vocabulary())

    cv.extracted_text = text
    cv.suggestions = asdict(extracted)
    cv.save(update_fields=["extracted_text", "suggestions"])
    return extracted


@transaction.atomic
def apply_cv_to_profile(cv: CV, extracted: ExtractedCriteria, *, replace: bool = False) -> None:
    """Write confirmed suggestions to the candidate's active profile.

    ``replace=False`` merges, which is the safe default. A skill missing from a CV does not mean
    the person lost it.
    """
    profile = active_profile(cv.owner)
    if profile is None:
        profile = CandidateProfile.objects.create(owner=cv.owner, name="From CV", is_active=True)

    def merged(existing: list[str] | None, found: tuple[str, ...]) -> list[str]:
        if replace:
            return list(found)
        combined = list(existing or ())
        combined.extend(term for term in found if term not in combined)
        return combined

    profile.skills = merged(profile.skills, extracted.skills)
    profile.domains = merged(profile.domains, extracted.domains)
    profile.seniority = merged(profile.seniority, extracted.seniority)
    profile.projects = merged(profile.projects, extracted.projects)
    profile.education = merged(profile.education, extracted.education)
    profile.years_experience = max(profile.years_experience, extracted.years_experience)
    profile.save()

    cv.applied_at = django_timezone.now()
    cv.save(update_fields=["applied_at"])
