"""When an advert overrules the register, and when silence means nothing.

The asymmetry here is the whole point. An advert saying "this post is not eligible for
sponsorship" is direct evidence about *this job* and beats a register entry about the
*employer*. An advert that says nothing about sponsorship tells you nothing at all, because
most licensed sponsors never mention it.
"""

from __future__ import annotations

import pytest

from screening.domain import (
    SPONSORSHIP_EXCLUSION_PHRASES,
    apply_advert_exclusion,
    find_sponsorship_exclusion,
)
from screening.enums import SponsorVerdict

EXCLUDING_ADVERTS: list[str] = [
    "This post does not meet the minimum requirements for visa sponsorship under the Skilled "
    "Worker Route.",
    "Please note this role is not eligible for sponsorship under the Skilled Worker route.",
    "Unfortunately we are unable to offer visa sponsorship for this position.",
    "Sponsorship is not available for this vacancy.",
    "This post is not eligible for sponsorship.",
    "We regret that this post does not attract sponsorship under the Skilled Worker route.",
]

SILENT_ADVERTS: list[str] = [
    "We are seeking an outstanding Research Software Engineer to join the group.",
    "Applicants must have the right to work in the UK.",
    "The University is committed to equality of opportunity.",
    "You will need a PhD in a relevant discipline and experience of scientific computing.",
    "We welcome applications from all sections of the community.",
    "",
]


@pytest.mark.parametrize("advert", EXCLUDING_ADVERTS)
def test_finds_an_explicit_exclusion(advert: str) -> None:
    assert find_sponsorship_exclusion(advert) is not None


@pytest.mark.parametrize("advert", SILENT_ADVERTS)
def test_silence_is_not_an_exclusion(advert: str) -> None:
    """Inferring "no sponsorship" from absence would delete most of the corpus."""
    assert find_sponsorship_exclusion(advert) is None


def test_right_to_work_boilerplate_is_not_an_exclusion() -> None:
    """This phrase appears on adverts from employers who sponsor happily."""
    advert = (
        "Applicants must have the right to work in the UK. The University is a licensed sponsor."
    )

    assert find_sponsorship_exclusion(advert) is None


def test_returns_the_whole_sentence_so_the_ui_can_quote_it() -> None:
    """The surrounding words are what let a human judge whether the advert means it."""
    advert = (
        "We are seeking a Lecturer. This post does not meet the minimum requirements for visa "
        "sponsorship under the Skilled Worker Route. Interviews will be held in October."
    )

    found = find_sponsorship_exclusion(advert)

    assert found == (
        "This post does not meet the minimum requirements for visa sponsorship under the "
        "Skilled Worker Route."
    )


def test_a_phrase_broken_across_a_line_wrap_is_still_found() -> None:
    """Advert HTML wraps mid-sentence; the phrase is the same phrase either way."""
    advert = "This post is not eligible\nfor sponsorship under the Skilled Worker route."

    assert find_sponsorship_exclusion(advert) is not None


def test_a_phrase_split_by_extra_whitespace_is_still_found() -> None:
    advert = "This  post   is not  eligible for sponsorship."

    assert find_sponsorship_exclusion(advert) is not None


def test_a_paragraph_length_sentence_is_trimmed_to_a_quotable_excerpt() -> None:
    """A 2,000-character "sentence" is not a quote a human can read at a glance."""
    filler = "The University is committed to equality and diversity in all its activities "
    advert = filler * 10 + "sponsorship is not available for this post " + filler * 10

    found = find_sponsorship_exclusion(advert)

    assert found is not None and len(found) < 400


def test_a_trimmed_excerpt_still_contains_the_phrase() -> None:
    filler = "The University is committed to equality and diversity in all its activities "
    advert = filler * 10 + "sponsorship is not available for this post " + filler * 10

    found = find_sponsorship_exclusion(advert)

    assert found is not None and "sponsorship is not available" in found


def test_a_trimmed_excerpt_is_marked_as_trimmed() -> None:
    filler = "The University is committed to equality and diversity in all its activities "
    advert = filler * 10 + "sponsorship is not available for this post " + filler * 10

    found = find_sponsorship_exclusion(advert)

    assert found is not None and found.startswith("… ")


def test_a_short_sentence_is_returned_whole() -> None:
    advert = "Sponsorship is not available for this post."

    assert find_sponsorship_exclusion(advert) == advert


def test_matching_is_case_insensitive() -> None:
    advert = "THIS POST IS NOT ELIGIBLE FOR SPONSORSHIP."

    assert find_sponsorship_exclusion(advert) is not None


@pytest.mark.parametrize(
    "verdict",
    [
        SponsorVerdict.CONFIRMED,
        SponsorVerdict.B_RATED,
        SponsorVerdict.PROVISIONAL,
        SponsorVerdict.CONFIRMED_VIA_PARENT,
    ],
)
def test_an_exclusion_overrides_any_sponsoring_verdict(verdict: SponsorVerdict) -> None:
    """The advert is about this job; the register is about the employer."""
    assert apply_advert_exclusion(verdict, exclusion_found=True) is SponsorVerdict.NOT_FOUND


@pytest.mark.parametrize(
    "verdict", [SponsorVerdict.CONFIRMED, SponsorVerdict.NOT_FOUND, SponsorVerdict.B_RATED]
)
def test_no_exclusion_leaves_the_register_verdict_alone(verdict: SponsorVerdict) -> None:
    """The override only ever moves a verdict down."""
    assert apply_advert_exclusion(verdict, exclusion_found=False) is verdict


def test_the_phrase_list_is_kept_small_and_specific() -> None:
    """Every phrase here can override a CONFIRMED match, so a loose one would hide real jobs."""
    assert all(len(phrase) > 15 for phrase in SPONSORSHIP_EXCLUSION_PHRASES)


def test_the_phrase_list_never_contains_right_to_work_boilerplate() -> None:
    assert not any("right to work" in phrase for phrase in SPONSORSHIP_EXCLUSION_PHRASES)
