"""Matching an institution to its legal entity on the register.

The register holds legal entity names, which are usually not the name anybody uses. "Exact
match then give up" would delete good employers from the search; "fuzzy match and accept" would
tell someone an employer sponsors when it does not. The cascade threads between those, and
these tests pin down exactly where the line sits.
"""

from __future__ import annotations

import pytest

from screening.domain import (
    RegisterCandidate,
    acronym_of,
    core_tokens,
    decide_sponsor_match,
    name_similarity,
    normalise_organisation_name,
    verdict_for_entry,
)
from screening.enums import MatchMethod, SponsorVerdict

KNOWN_VARIANTS: list[tuple[str, str]] = [
    ("Cambridge University", "The University of Cambridge"),
    ("Imperial College London", "Imperial College London (HR)"),
    ("Birkbeck, University of London", "Birkbeck College"),
    ("University of Hertfordshire", "University of Hertfordshire Higher Education Corporation"),
    ("LSE", "The London School of Economics and Political Science"),
    ("University of Edinburgh", "University of Edinburgh"),
]

REGISTER_NAMES: list[str] = [
    "The University of Cambridge",
    "Imperial College London (HR)",
    "Birkbeck College",
    "University of Hertfordshire Higher Education Corporation",
    "The London School of Economics and Political Science",
    "University of Edinburgh",
    "UK Research and Innovation",
    "University of Oxford",
    "Cardiff University",
    "The University of Manchester",
    "University of London",
    "London South Bank University",
    "Edinburgh Napier University",
]


def register(names: list[str] | None = None, **overrides: str) -> list[RegisterCandidate]:
    """Build register candidates, A-rated Skilled Worker sponsors unless told otherwise."""
    return [
        RegisterCandidate(
            organisation_name=name,
            town_city=overrides.get("town_city", ""),
            type_rating=overrides.get("type_rating", "Worker (A rating)"),
            routes=tuple(overrides.get("routes", "Skilled Worker").split(";")),
        )
        for name in (names or REGISTER_NAMES)
    ]


@pytest.mark.parametrize(("everyday", "registered"), KNOWN_VARIANTS)
def test_known_name_variants_rank_the_correct_entity_first(everyday: str, registered: str) -> None:
    """Whether decided automatically or sent for review, the right entity leads."""
    decision = decide_sponsor_match(everyday, register())

    assert decision.candidates[0].organisation_name == registered


@pytest.mark.parametrize(
    ("everyday", "registered"),
    [
        ("Cambridge University", "The University of Cambridge"),
        ("Imperial College London", "Imperial College London (HR)"),
        ("University of Hertfordshire", "University of Hertfordshire Higher Education Corporation"),
        ("University of Edinburgh", "University of Edinburgh"),
    ],
)
def test_variants_that_reduce_to_the_same_core_are_matched_automatically(
    everyday: str, registered: str
) -> None:
    """Identical identifying words is proof, not a guess, so no human is troubled by these."""
    decision = decide_sponsor_match(everyday, register())

    assert (decision.verdict, decision.matched_name) == (SponsorVerdict.CONFIRMED, registered)


@pytest.mark.parametrize("everyday", ["Birkbeck, University of London", "LSE"])
def test_variants_that_only_resemble_are_sent_for_review(everyday: str) -> None:
    """A containment or acronym match is a strong suggestion, and suggestions get confirmed."""
    decision = decide_sponsor_match(everyday, register())

    assert (decision.verdict, decision.needs_review) == (SponsorVerdict.NOT_FOUND, True)


def test_an_institution_whose_sponsor_is_a_parent_body_finds_nothing_itself() -> None:
    """MRC LMB has no entry of its own - its sponsor is UK Research and Innovation.

    No amount of string similarity finds that, which is precisely why the review queue exists
    and why the answer a human gives is persisted as ``CONFIRMED_VIA_PARENT``.
    """
    decision = decide_sponsor_match("MRC Laboratory of Molecular Biology", register())

    assert decision.verdict is SponsorVerdict.NOT_FOUND


def test_similarity_below_the_threshold_returns_not_found() -> None:
    """Asymmetric risk: a false positive costs weeks, a false negative costs a minute."""
    decision = decide_sponsor_match("Institute of Something Entirely Different", register())

    assert decision.verdict is SponsorVerdict.NOT_FOUND


def test_similarity_below_the_threshold_still_attaches_candidates() -> None:
    """A "not found" with no candidates to look at is a dead end, not an answer."""
    decision = decide_sponsor_match("Birkbeck, University of London", register())

    assert len(decision.candidates) > 0


def test_a_high_similarity_match_is_never_auto_confirmed() -> None:
    """Trigram similarity ranks candidates; it never decides."""
    decision = decide_sponsor_match("Universty of Oxfrd", register())

    assert decision.method is not MatchMethod.EXACT


def test_an_exact_name_match_is_decided_without_a_human() -> None:
    decision = decide_sponsor_match("University of Oxford", register())

    assert (decision.method, decision.confidence) == (MatchMethod.EXACT, 1.0)


def test_an_employer_appearing_under_several_related_entities_returns_all_of_them() -> None:
    """None is silently picked; the human sees every candidate."""
    candidates = register(
        [
            "University of Wales Trinity Saint David",
            "University of Wales",
            "University of Wales Press",
        ]
    )

    decision = decide_sponsor_match("University of Wales", candidates)

    assert len(decision.candidates) == 3


def test_the_exact_entity_wins_over_its_relatives() -> None:
    candidates = register(
        [
            "University of Wales Trinity Saint David",
            "University of Wales",
            "University of Wales Press",
        ]
    )

    decision = decide_sponsor_match("University of Wales", candidates)

    assert decision.matched_name == "University of Wales"


@pytest.mark.parametrize(
    ("type_rating", "routes", "expected"),
    [
        ("Worker (A rating)", ("Skilled Worker",), SponsorVerdict.CONFIRMED),
        (
            "Temporary Worker (A rating); Worker (A rating)",
            ("Government Authorised Exchange", "Skilled Worker"),
            SponsorVerdict.CONFIRMED,
        ),
        ("Worker (B rating)", ("Skilled Worker",), SponsorVerdict.B_RATED),
        ("Worker (Provisional rating)", ("Skilled Worker",), SponsorVerdict.PROVISIONAL),
        (
            "Temporary Worker (A rating)",
            ("Government Authorised Exchange",),
            SponsorVerdict.OTHER_ROUTE_ONLY,
        ),
    ],
)
def test_register_rating_translates_to_a_verdict(
    type_rating: str, routes: tuple[str, ...], expected: SponsorVerdict
) -> None:
    candidate = RegisterCandidate(
        organisation_name="Somewhere", type_rating=type_rating, routes=routes
    )

    assert verdict_for_entry(candidate) is expected


def test_a_licence_for_another_route_is_not_a_skilled_worker_licence() -> None:
    """Being on the register is not the same as being able to sponsor *this* visa."""
    candidate = RegisterCandidate(
        organisation_name="Somewhere",
        type_rating="Temporary Worker (A rating)",
        routes=("Creative Worker", "Government Authorised Exchange"),
    )

    assert verdict_for_entry(candidate) is SponsorVerdict.OTHER_ROUTE_ONLY


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("The University of Cambridge", "university of cambridge"),
        ("Imperial College London (HR)", "imperial college london"),
        ("University of Hertfordshire Higher Education Corporation", "university of hertfordshire"),
        ("Acme Education Ltd", "acme education"),
        ("Something & Co Limited", "something and"),
        ("Université de Test", "universite de test"),
    ],
)
def test_normalisation_strips_what_carries_no_information(raw: str, expected: str) -> None:
    assert normalise_organisation_name(raw) == expected


def test_word_order_does_not_change_the_identifying_core() -> None:
    """Both "Cambridge University" and "University of Cambridge" name the same place."""
    assert core_tokens("Cambridge University") == core_tokens("The University of Cambridge")


def test_an_acronym_expands_to_the_initials_of_the_significant_words() -> None:
    assert acronym_of("The London School of Economics and Political Science") == "lseps"


def test_identical_cores_score_a_perfect_similarity() -> None:
    assert name_similarity("Cambridge University", "The University of Cambridge") == 1.0


def test_unrelated_names_score_nothing() -> None:
    assert name_similarity("University of Bath", "Cardiff University") == 0.0


def test_a_name_made_only_of_generic_words_scores_nothing() -> None:
    """A name like "The University" identifies nobody; matching on it would match everybody."""
    assert name_similarity("The University", "The College") == 0.0
