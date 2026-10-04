"""Fitness is a comparison against one person's profile, so it is stored per person.

It used to live on `JobScreening`, which is one row per job. With two candidates that meant the
second one's profile save silently overwrote the first one's scores across the whole estate -
and the first candidate's ranking quietly became a stranger's.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from screening.models import JobFitness, Ruleset
from screening.services import criteria_fingerprint, criteria_from, score_fitness_for
from tests.factories import CandidateProfileFactory, JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def job(ruleset: Ruleset) -> Any:
    """A python-flavoured advert, so a python profile scores and a chemistry one does not."""
    vacancy = JobFactory(
        title="Research Software Engineer",
        description_text="Senior python django postgres engineer, higher education.",
    )
    ScreeningFactory(job=vacancy, ruleset=ruleset)
    return vacancy


def test_two_candidates_score_the_same_job_differently(
    candidate_user: Any, second_candidate_user: Any, job: Any
) -> None:
    CandidateProfileFactory(owner=candidate_user, skills=["python", "django", "postgres"])
    CandidateProfileFactory(owner=second_candidate_user, skills=["welding", "metallurgy"])

    score_fitness_for(candidate_user, [job])
    score_fitness_for(second_candidate_user, [job])

    mine = JobFitness.objects.get(owner=candidate_user, job=job).score
    theirs = JobFitness.objects.get(owner=second_candidate_user, job=job).score
    assert mine > theirs


def test_scoring_one_candidate_leaves_the_other_untouched(
    candidate_user: Any, second_candidate_user: Any, job: Any
) -> None:
    """The exact regression: a profile save used to rewrite everyone's scores."""
    CandidateProfileFactory(owner=candidate_user, skills=["python"])
    CandidateProfileFactory(owner=second_candidate_user, skills=["python"])
    score_fitness_for(candidate_user, [job])
    score_fitness_for(second_candidate_user, [job])
    before = JobFitness.objects.get(owner=second_candidate_user, job=job).scored_at

    score_fitness_for(candidate_user, [job], force=True)

    assert JobFitness.objects.get(owner=second_candidate_user, job=job).scored_at == before


def test_the_job_list_shows_the_asking_candidates_score(
    candidate_client: APIClient, candidate_user: Any, second_candidate_user: Any, job: Any
) -> None:
    CandidateProfileFactory(owner=candidate_user, skills=["python", "django", "postgres"])
    CandidateProfileFactory(owner=second_candidate_user, skills=["welding"])
    score_fitness_for(candidate_user, [job])
    score_fitness_for(second_candidate_user, [job])

    row = candidate_client.get("/api/jobs/").json()["results"][0]

    assert row["fitness_score"] == JobFitness.objects.get(owner=candidate_user, job=job).score


def test_a_candidate_with_no_profile_sees_zero_not_someone_elses_score(
    candidate_client: APIClient, second_candidate_user: Any, job: Any
) -> None:
    CandidateProfileFactory(owner=second_candidate_user, skills=["python", "django"])
    score_fitness_for(second_candidate_user, [job])

    row = candidate_client.get("/api/jobs/").json()["results"][0]

    assert row["fitness_score"] == 0


def test_min_fitness_filters_on_your_own_score(
    candidate_client: APIClient, candidate_user: Any, second_candidate_user: Any, job: Any
) -> None:
    """A filter reading a shared column would hand back jobs that fit somebody else."""
    CandidateProfileFactory(owner=second_candidate_user, skills=["python", "django", "postgres"])
    score_fitness_for(second_candidate_user, [job])

    assert candidate_client.get("/api/jobs/?min_fitness=1").json()["results"] == []


def test_removing_a_profile_removes_the_scores(candidate_user: Any, job: Any) -> None:
    """Stale scores from a deleted profile would rank against criteria nobody holds."""
    profile = CandidateProfileFactory(owner=candidate_user, skills=["python"])
    score_fitness_for(candidate_user, [job])
    profile.delete()

    score_fitness_for(candidate_user, [job])

    assert not JobFitness.objects.filter(owner=candidate_user).exists()


def test_rescoring_an_unchanged_profile_does_no_work(candidate_user: Any, job: Any) -> None:
    """This is what stops a profile save from rewriting a row for every job in the estate."""
    CandidateProfileFactory(owner=candidate_user, skills=["python"])
    score_fitness_for(candidate_user, [job])

    counts = score_fitness_for(candidate_user, [job])

    assert counts == {"scored": 1, "changed": 0}


def test_changing_the_profile_rescores(candidate_user: Any, job: Any) -> None:
    profile = CandidateProfileFactory(owner=candidate_user, skills=["welding"])
    score_fitness_for(candidate_user, [job])
    low = JobFitness.objects.get(owner=candidate_user, job=job).score

    profile.skills = ["python", "django", "postgres"]
    profile.save(update_fields=["skills"])
    score_fitness_for(candidate_user, [job])

    assert JobFitness.objects.get(owner=candidate_user, job=job).score > low


def test_the_fingerprint_changes_with_the_criteria(candidate_user: Any) -> None:
    one = criteria_from(CandidateProfileFactory.build(skills=["python"]))
    two = criteria_from(CandidateProfileFactory.build(skills=["welding"]))

    assert criteria_fingerprint(one) != criteria_fingerprint(two)


def test_the_fingerprint_is_stable_for_equal_criteria(candidate_user: Any) -> None:
    one = criteria_from(CandidateProfileFactory.build(skills=["python", "django"]))
    two = criteria_from(CandidateProfileFactory.build(skills=["python", "django"]))

    assert criteria_fingerprint(one) == criteria_fingerprint(two)


def test_rescore_is_queued_not_run_inline(
    candidate_client: APIClient, candidate_user: Any, job: Any
) -> None:
    """O(jobs) work in the request thread was a self-inflicted outage waiting to happen."""
    profile = CandidateProfileFactory(owner=candidate_user, skills=["python"])

    response = candidate_client.post(f"/api/profiles/{profile.pk}/rescore/")

    assert response.status_code == 202
    assert response.json()["queued"] is True


def test_rescore_on_someone_elses_profile_is_not_found(
    candidate_client: APIClient, second_candidate_user: Any
) -> None:
    theirs = CandidateProfileFactory(owner=second_candidate_user)

    assert candidate_client.post(f"/api/profiles/{theirs.pk}/rescore/").status_code == 404
