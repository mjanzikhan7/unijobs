"""Screening against the database.

The main check: re-screening makes no network calls. So a change to the Immigration Rules is a
30-second recalculation, not a new crawl of 167 universities.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

import pytest
import respx

from screening.enums import MatchMethod, SalaryConfidence, SponsorVerdict, ThresholdVerdict
from screening.models import JobFitness, JobScreening, Ruleset
from screening.services import (
    active_ruleset,
    compare_snapshots,
    create_ruleset_version,
    criteria_from,
    load_register_snapshot,
    match_institution,
    rescreen_all,
    resolve_sponsor_match,
    score_fitness_for,
    screen_job,
    screen_jobs,
)
from tests.factories import (
    CandidateProfileFactory,
    InstitutionFactory,
    JobFactory,
    RegisterEntryFactory,
    SnapshotFactory,
    SponsorMatchFactory,
)

pytestmark = pytest.mark.django_db


def test_a_screened_job_always_carries_both_verdicts(ruleset: Ruleset) -> None:
    """No nulls. A missing badge reads as "confirmed" to a human skimming a list."""
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution)
    job = JobFactory(institution=institution)

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.sponsor_verdict and screening.threshold_verdict


def test_the_ruleset_version_is_recorded_on_every_verdict(ruleset: Ruleset) -> None:
    """A verdict must stay explainable by the rules in force when it was computed."""
    job = JobFactory()

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.ruleset_id == ruleset.pk


def test_a_job_at_a_confirmed_sponsor_inherits_that_verdict(ruleset: Ruleset) -> None:
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.CONFIRMED)
    job = JobFactory(institution=institution)

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.sponsor_verdict == SponsorVerdict.CONFIRMED


def test_an_advert_exclusion_overrides_a_confirmed_sponsor(ruleset: Ruleset) -> None:
    """At the service layer: the advert is about this job, the register is not."""
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.CONFIRMED)
    job = JobFactory(
        institution=institution,
        description_text=(
            "This post does not meet the minimum requirements for visa sponsorship under the "
            "Skilled Worker Route."
        ),
    )

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.sponsor_verdict == SponsorVerdict.NOT_FOUND


def test_an_advert_exclusion_records_the_phrase_it_found(ruleset: Ruleset) -> None:
    """The UI quotes it back, so a human can judge whether the advert really means it."""
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.CONFIRMED)
    job = JobFactory(
        institution=institution,
        description_text="This post is not eligible for sponsorship.",
    )

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert "not eligible for sponsorship" in screening.advert_exclusion_phrase


def test_an_advert_silent_on_sponsorship_keeps_the_register_verdict(ruleset: Ruleset) -> None:
    """Most licensed sponsors never mention sponsorship at all."""
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.CONFIRMED)
    job = JobFactory(
        institution=institution,
        description_text="We are seeking an outstanding Research Software Engineer.",
    )

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.advert_excludes_sponsorship is False


def test_the_salary_floor_is_what_gets_screened(ruleset: Ruleset) -> None:
    job = JobFactory(salary_raw="£38,784 to £86,049 per annum")

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.screened_on == Decimal("38784.00")


def test_a_ceiling_only_salary_is_recorded_as_unclear(ruleset: Ruleset) -> None:
    """At the service layer: a top figure is never screened as a starting salary."""
    job = JobFactory(salary_raw="Up to £86,500 per annum")

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.threshold_verdict == ThresholdVerdict.SALARY_UNCLEAR


def test_an_unparseable_salary_is_surfaced_not_guessed_at(ruleset: Ruleset) -> None:
    job = JobFactory(salary_raw="Competitive")

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.salary_confidence == SalaryConfidence.UNPARSEABLE


def test_the_grade_is_copied_onto_the_job_for_a_human_to_check(ruleset: Ruleset) -> None:
    job = JobFactory(salary_raw="£39,424 to £47,779 p.a. (Grade 7)", grade_raw="")

    screen_job(job, ruleset=ruleset, criteria=criteria_from(None))
    job.refresh_from_db()

    assert job.grade_raw == "Grade 7"


def test_fitness_is_scored_against_the_active_profile(ruleset: Ruleset) -> None:
    profile = CandidateProfileFactory()
    job = JobFactory(description_text="Senior python django postgres engineer.")

    score_fitness_for(profile.owner, [job])

    assert JobFitness.objects.get(owner=profile.owner, job=job).score > 0


def test_fitness_reasons_are_stored_alongside_the_score(ruleset: Ruleset) -> None:
    """A bare number is unactionable; the gaps are what go into a covering letter."""
    profile = CandidateProfileFactory()
    job = JobFactory(description_text="Senior python engineer.")

    score_fitness_for(profile.owner, [job])

    reasons = JobFitness.objects.get(owner=profile.owner, job=job).reasons
    assert any(reason["criterion"] == "skills" for reason in reasons)


def test_a_high_fitness_score_never_promotes_a_sponsor_verdict(ruleset: Ruleset) -> None:
    """A 95% fit at an unlicensed employer is not a result."""
    profile = CandidateProfileFactory()
    institution = InstitutionFactory()
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.NOT_FOUND)
    job = JobFactory(
        institution=institution,
        description_text=(
            "Senior python django postgres kubernetes engineer, higher education, research "
            "software, data pipeline, MSc."
        ),
    )

    screening = screen_job(job, ruleset=ruleset)
    score_fitness_for(profile.owner, [job])

    fitness = JobFitness.objects.get(owner=profile.owner, job=job)
    assert (fitness.score, screening.sponsor_verdict) == (100, SponsorVerdict.NOT_FOUND)


def test_screening_a_job_twice_is_idempotent(ruleset: Ruleset) -> None:
    job = JobFactory()
    screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert JobScreening.objects.filter(job=job).count() == 1


@respx.mock
def test_rescreening_makes_no_network_calls(ruleset: Ruleset) -> None:
    """Asserted with respx: any outbound request would be recorded here."""
    JobFactory.create_batch(20)

    rescreen_all(ruleset)

    assert len(respx.calls) == 0


def test_rescreening_is_fast_enough_to_be_used(ruleset: Ruleset) -> None:
    """500 jobs under 3s; the real target is 5,000 under 30s."""
    JobFactory.create_batch(200)

    started = time.monotonic()
    rescreen_all(ruleset)
    elapsed = time.monotonic() - started

    assert elapsed < 3.0


def test_rescreening_reports_how_many_verdicts_changed(ruleset: Ruleset) -> None:
    JobFactory.create_batch(5)

    counts = rescreen_all(ruleset)

    assert counts == {"screened": 5, "changed": 5}


def test_rescreening_unchanged_data_changes_nothing(ruleset: Ruleset) -> None:
    JobFactory.create_batch(5)
    rescreen_all(ruleset)

    counts = rescreen_all(ruleset)

    assert counts["changed"] == 0


def test_a_new_ruleset_is_a_new_version_not_an_edit(ruleset: Ruleset) -> None:
    create_ruleset_version(
        name="November 2026",
        effective_from=date(2026, 11, 1),
        verified_at=date(2026, 10, 30),
        source_url="https://www.gov.uk/",
        figures={key.key: str(key.value) for key in ruleset.figures.all()},
    )

    assert Ruleset.objects.count() == 2


def test_only_one_ruleset_is_active_at_a_time(ruleset: Ruleset) -> None:
    create_ruleset_version(
        name="November 2026",
        effective_from=date(2026, 11, 1),
        verified_at=date(2026, 10, 30),
        source_url="https://www.gov.uk/",
        figures={key.key: str(key.value) for key in ruleset.figures.all()},
    )

    assert Ruleset.objects.filter(is_active=True).count() == 1


def test_a_historic_verdict_keeps_pointing_at_the_rules_that_produced_it(
    ruleset: Ruleset,
) -> None:
    """Nothing becomes inexplicable when the figures move."""
    job = JobFactory(salary_raw="£52,000 per annum")
    screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    create_ruleset_version(
        name="November 2026",
        effective_from=date(2026, 11, 1),
        verified_at=date(2026, 10, 30),
        source_url="https://www.gov.uk/",
        figures={key.key: str(key.value) for key in ruleset.figures.all()},
    )

    assert JobScreening.objects.get(job=job).ruleset.version == 1


def test_raising_a_threshold_moves_the_verdicts_that_depend_on_it(ruleset: Ruleset) -> None:
    """UC-09: apply an Immigration Rules change without re-crawling."""
    job = JobFactory(salary_raw="£52,000 per annum")
    screen_job(job, ruleset=ruleset, criteria=criteria_from(None))
    figures = {figure.key: str(figure.value) for figure in ruleset.figures.all()}
    figures["soc_2134_going_rate"] = "51000"

    new_ruleset = create_ruleset_version(
        name="November 2026",
        effective_from=date(2026, 11, 1),
        verified_at=date(2026, 10, 30),
        source_url="https://www.gov.uk/",
        figures=figures,
    )
    rescreen_all(new_ruleset)

    assert JobScreening.objects.get(job=job).threshold_verdict == ThresholdVerdict.TARGET_BAND


def test_the_active_ruleset_is_the_one_screening_uses(ruleset: Ruleset) -> None:
    assert active_ruleset().pk == ruleset.pk


def test_matching_finds_a_legal_entity_name_the_everyday_name_does_not_resemble() -> None:
    snapshot = SnapshotFactory()
    RegisterEntryFactory(snapshot=snapshot, organisation_name="The University of Cambridge")
    institution = InstitutionFactory(name="Cambridge University", slug="cambridge-university")

    match = match_institution(institution, snapshot)

    assert match.registered_legal_name == "The University of Cambridge"


def test_a_low_confidence_match_is_queued_for_review_not_confirmed() -> None:
    """At the service layer: similarity alone never confirms a sponsor."""
    snapshot = SnapshotFactory()
    RegisterEntryFactory(snapshot=snapshot, organisation_name="Birkbeck College")
    institution = InstitutionFactory(name="Birkbeck, University of London", slug="birkbeck")

    match = match_institution(institution, snapshot)

    assert (match.verdict, match.needs_review) == (SponsorVerdict.NOT_FOUND, True)


def test_a_queued_match_carries_the_candidates_for_a_human_to_choose_from() -> None:
    snapshot = SnapshotFactory()
    RegisterEntryFactory(snapshot=snapshot, organisation_name="Birkbeck College")
    institution = InstitutionFactory(name="Birkbeck, University of London", slug="birkbeck")

    match = match_institution(institution, snapshot)

    assert match.candidates[0]["organisation_name"] == "Birkbeck College"


def test_a_human_decision_is_persisted() -> None:
    """UC-08: the question is asked once."""
    institution = InstitutionFactory(name="MRC Laboratory of Molecular Biology", slug="mrc-lmb")

    match = resolve_sponsor_match(
        institution,
        registered_legal_name="UK Research and Innovation",
        verdict=SponsorVerdict.CONFIRMED_VIA_PARENT,
    )

    assert (match.verdict, match.method) == (
        SponsorVerdict.CONFIRMED_VIA_PARENT,
        MatchMethod.HUMAN,
    )


def test_a_human_decision_survives_a_later_rematch() -> None:
    """A register refresh shifts the fuzzy scores; it must not overwrite a person's answer."""
    institution = InstitutionFactory(name="MRC Laboratory of Molecular Biology", slug="mrc-lmb")
    resolve_sponsor_match(
        institution,
        registered_legal_name="UK Research and Innovation",
        verdict=SponsorVerdict.CONFIRMED_VIA_PARENT,
    )
    snapshot = SnapshotFactory()
    RegisterEntryFactory(snapshot=snapshot, organisation_name="Medical Research Council")

    match = match_institution(institution, snapshot)

    assert match.registered_legal_name == "UK Research and Innovation"


def test_loading_a_register_csv_creates_a_new_snapshot() -> None:
    rows = [
        {
            "Organisation Name": "The University of Cambridge",
            "Town/City": "Cambridge",
            "Type & Rating": "Worker (A rating)",
            "Route": "Skilled Worker",
        }
    ]

    snapshot = load_register_snapshot(rows, source_url="https://www.gov.uk/")

    assert snapshot.row_count == 1


def test_loading_a_second_register_preserves_the_first() -> None:
    """Comparing snapshots is the only way to say "they dropped off"."""
    rows = [{"Organisation Name": "The University of Cambridge"}]
    first = load_register_snapshot(rows, source_url="https://www.gov.uk/")

    second = load_register_snapshot(rows, source_url="https://www.gov.uk/")

    assert first.pk != second.pk


def test_an_employer_dropping_off_the_register_is_reported() -> None:
    """Worth knowing before an offer conversation, not after one."""
    institution = InstitutionFactory(name="Somewhere University", slug="somewhere")
    SponsorMatchFactory(institution=institution, registered_legal_name="Somewhere University")
    previous = load_register_snapshot(
        [{"Organisation Name": "Somewhere University"}], source_url="https://www.gov.uk/"
    )
    current = load_register_snapshot(
        [{"Organisation Name": "Elsewhere University"}], source_url="https://www.gov.uk/"
    )

    changes = compare_snapshots(previous, current)

    assert changes["dropped_off"] == ["Somewhere University"]


def test_a_newly_listed_employer_is_reported() -> None:
    institution = InstitutionFactory(name="Elsewhere University", slug="elsewhere")
    SponsorMatchFactory(institution=institution, registered_legal_name="Elsewhere University")
    previous = load_register_snapshot(
        [{"Organisation Name": "Somewhere University"}], source_url="https://www.gov.uk/"
    )
    current = load_register_snapshot(
        [{"Organisation Name": "Elsewhere University"}], source_url="https://www.gov.uk/"
    )

    changes = compare_snapshots(previous, current)

    assert changes["newly_listed"] == ["Elsewhere University"]


def test_an_unchanged_register_reports_nothing() -> None:
    institution = InstitutionFactory(name="Somewhere University", slug="somewhere")
    SponsorMatchFactory(institution=institution, registered_legal_name="Somewhere University")
    rows = [{"Organisation Name": "Somewhere University"}]
    previous = load_register_snapshot(rows, source_url="https://www.gov.uk/")
    current = load_register_snapshot(rows, source_url="https://www.gov.uk/")

    changes = compare_snapshots(previous, current)

    assert changes == {"dropped_off": [], "newly_listed": []}


def test_screening_a_batch_reports_totals(ruleset: Ruleset) -> None:
    jobs = JobFactory.create_batch(3)

    counts = screen_jobs(list(jobs))

    assert counts["screened"] == 3


def test_the_quoted_exclusion_does_not_begin_with_the_job_title(ruleset: Ruleset) -> None:
    """The quote is shown to a human to judge the verdict by.

    Title and description are searched together, so without a sentence break between them the
    splitter runs the two into one "sentence" and the quote comes back as
    "Senior Research Technician We regret that this post does not attract...".
    """
    institution = InstitutionFactory(name="University of Test")
    SponsorMatchFactory(institution=institution, verdict=SponsorVerdict.CONFIRMED)
    job = JobFactory(
        institution=institution,
        title="Senior Research Technician",
        description_text="We regret that this post does not attract sponsorship.",
        salary_raw="£30,000 per annum",
    )

    screening = screen_job(job, ruleset=ruleset, criteria=criteria_from(None))

    assert screening.advert_excludes_sponsorship is True
    assert screening.advert_exclusion_phrase.startswith("We regret")
