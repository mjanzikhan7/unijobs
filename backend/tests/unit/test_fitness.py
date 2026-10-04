"""Fitness scoring and the wall between it and sponsorship.

Fitness is a triage aid. It ranks what is already legally takeable; it never makes something
takeable. A 95% fit at an unlicensed employer is not a result.
"""

from __future__ import annotations

import pytest

from screening.domain import (
    CRITERION_WEIGHTS,
    CandidateCriteria,
    apply_advert_exclusion,
    required_years,
    score_fitness,
)
from screening.enums import SponsorVerdict

PROFILE = CandidateCriteria(
    skills=("python", "django", "postgres", "kubernetes"),
    domains=("higher education", "research software"),
    seniority=("senior",),
    projects=("data pipeline",),
    education=("msc",),
    years_experience=8,
)


def test_a_perfect_advert_scores_full_marks() -> None:
    advert = (
        "Senior engineer with python, django, postgres and kubernetes. Higher education and "
        "research software background. You will build a data pipeline. MSc required."
    )

    result = score_fitness(advert, PROFILE)

    assert result.score == 100


def test_an_advert_matching_nothing_scores_only_the_years_criterion() -> None:
    """An advert that states no minimum experience cannot fail the years criterion."""
    advert = "We are seeking a gardener for the botanical collection."

    result = score_fitness(advert, PROFILE)

    expected = round(100 * CRITERION_WEIGHTS["years"] / sum(CRITERION_WEIGHTS.values()))
    assert result.score == expected


def test_a_partial_skills_match_scores_between() -> None:
    advert = "Senior engineer with python and django experience in higher education."

    result = score_fitness(advert, PROFILE)

    assert 40 < result.score < 100


def test_a_partial_match_names_the_missing_skills() -> None:
    """The gaps are the point - they are what goes into a covering letter."""
    advert = "Senior engineer with python and django experience in higher education."

    result = score_fitness(advert, PROFILE)
    skills = next(reason for reason in result.reasons if reason.criterion == "skills")

    assert set(skills.missing) == {"postgres", "kubernetes"}


def test_a_partial_match_names_what_did_match() -> None:
    advert = "Senior engineer with python and django experience in higher education."

    result = score_fitness(advert, PROFILE)
    skills = next(reason for reason in result.reasons if reason.criterion == "skills")

    assert set(skills.matched) == {"python", "django"}


def test_every_criterion_is_reported_even_when_it_scored_nothing() -> None:
    """A silent zero is indistinguishable from a criterion nobody configured."""
    result = score_fitness("Gardener wanted.", PROFILE)

    assert {reason.criterion for reason in result.reasons} == set(CRITERION_WEIGHTS)


def test_skills_are_weighted_above_education() -> None:
    """Weights come from the rules: skills x3, education x1."""
    skills_only = score_fitness("python django postgres kubernetes", PROFILE)
    education_only = score_fitness("msc", PROFILE)

    assert skills_only.score > education_only.score


@pytest.mark.parametrize(
    ("advert", "expected"),
    [
        ("At least 5 years experience required", 5),
        ("3+ years of relevant experience", 3),
        ("You will have 10 years experience in research computing", 10),
        ("A PhD and a track record of publication", None),
        ("", None),
    ],
)
def test_reads_the_years_requirement_from_the_advert(advert: str, expected: int | None) -> None:
    assert required_years(advert) == expected


def test_an_advert_demanding_more_years_than_the_profile_has_fails_that_criterion() -> None:
    advert = "Senior engineer, at least 15 years experience with python and django."

    result = score_fitness(advert, PROFILE)
    years = next(reason for reason in result.reasons if reason.criterion == "years")

    assert years.fraction == 0.0


def test_an_advert_within_the_profile_experience_passes_that_criterion() -> None:
    advert = "Engineer with at least 5 years experience."

    result = score_fitness(advert, PROFILE)
    years = next(reason for reason in result.reasons if reason.criterion == "years")

    assert years.fraction == 1.0


def test_a_met_years_requirement_still_explains_itself() -> None:
    """The reasons list is the output; a silent pass is as unhelpful as a silent fail."""
    advert = "Engineer with at least 5 years experience."

    result = score_fitness(advert, PROFILE)
    years = next(reason for reason in result.reasons if reason.criterion == "years")

    assert years.note == "Advert asks for 5 years; profile has 8."


def test_the_years_criterion_explains_the_shortfall() -> None:
    advert = "Senior engineer, at least 15 years experience."

    result = score_fitness(advert, PROFILE)
    years = next(reason for reason in result.reasons if reason.criterion == "years")

    assert "15 years" in years.note


def test_an_empty_profile_scores_only_the_years_criterion() -> None:
    """No configured terms is a configuration problem, reported rather than scored around."""
    result = score_fitness("Anything at all", CandidateCriteria())
    skills = next(reason for reason in result.reasons if reason.criterion == "skills")

    assert "No terms configured" in skills.note


def test_terms_match_as_whole_words() -> None:
    """A term like "python" must not match "pythonesque" - substring matching inflates scores."""
    result = score_fitness("A pythonesque approach to djangoism", PROFILE)
    skills = next(reason for reason in result.reasons if reason.criterion == "skills")

    assert skills.matched == ()


def test_fitness_never_raises_a_sponsor_verdict() -> None:
    """The two are computed independently and neither may move the other."""
    advert = (
        "Senior python django postgres kubernetes engineer, higher education, research "
        "software, data pipeline, MSc. This post is not eligible for sponsorship."
    )
    fitness = score_fitness(advert, PROFILE)

    verdict = apply_advert_exclusion(SponsorVerdict.CONFIRMED, exclusion_found=True)

    assert (fitness.score, verdict) == (100, SponsorVerdict.NOT_FOUND)


def test_scoring_is_deterministic() -> None:
    advert = "Senior engineer with python and django in higher education."

    assert score_fitness(advert, PROFILE) == score_fitness(advert, PROFILE)
