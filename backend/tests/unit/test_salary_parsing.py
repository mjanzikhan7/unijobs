"""The salary parser, against real advert strings.

Every string in the main table came off a live university advert. They are here rather than in
a docstring because this is the part of the system where being subtly wrong is invisible: a
parser that reads "£47.39" as £47,390 produces a plausible number and a wrong decision.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from screening.domain import parse_salary
from screening.enums import SalaryConfidence, SalaryPeriod

CORPUS: list[tuple[str, str | None, str | None, SalaryConfidence]] = [
    (
        "£38,784 to £46,049 per annum (pro-rata for part-time)",
        "38784",
        "46049",
        SalaryConfidence.PARSED,
    ),
    ("£47,389 rising to £51,753", "47389", "51753", SalaryConfidence.PARSED),
    (
        "Starting from £47,389, rising to £56,535 (Grade 6)",
        "47389",
        "56535",
        SalaryConfidence.PARSED,
    ),
    (
        "£32,080 to £33,002 with progression to £34,610 per annum.",
        "32080",
        "34610",
        SalaryConfidence.PARSED,
    ),
    (
        "£39,424 to £47,779 with a discretionary range to £51,983 p.a. (gRADE 7)",
        "39424",
        "51983",
        SalaryConfidence.PARSED,
    ),
    (
        "£43,277 to £51,714 per annum inclusive with potential to progress to £55,497 pa "
        "inclusive of London allowance",
        "43277",
        "55497",
        SalaryConfidence.PARSED,
    ),
    ("Up to £86,500 per annum", None, "86500", SalaryConfidence.PARSED),
    ("£47.39 to £56,535", None, None, SalaryConfidence.UNPARSEABLE),
    ("£9,883 - please see advert", "9883", None, SalaryConfidence.LOW),
    ("Band 7: £49,387 - £56,515 per annum pro rata", "49387", "56515", SalaryConfidence.PARSED),
    ("£36,636 per annum (Grade 3)", "36636", "36636", SalaryConfidence.EXACT),
    ("Competitive", None, None, SalaryConfidence.UNPARSEABLE),
    ("Not specified", None, None, SalaryConfidence.UNPARSEABLE),
    ("", None, None, SalaryConfidence.UNPARSEABLE),
]


@pytest.mark.parametrize(("raw", "expected_min", "expected_max", "confidence"), CORPUS)
def test_parses_the_advert_corpus(
    raw: str, expected_min: str | None, expected_max: str | None, confidence: SalaryConfidence
) -> None:
    result = parse_salary(raw)

    assert (result.minimum, result.maximum, result.confidence) == (
        Decimal(expected_min) if expected_min else None,
        Decimal(expected_max) if expected_max else None,
        confidence,
    )


def test_keeps_the_raw_string_even_when_it_cannot_be_parsed() -> None:
    result = parse_salary("Competitive salary, depending on experience")

    assert result.raw == "Competitive salary, depending on experience"


def test_typo_below_the_plausible_floor_poisons_the_whole_string() -> None:
    """£47.39 is a typo for £47,389; picking the "good" figure would be guessing."""
    result = parse_salary("£47.39 to £56,535")

    assert result.confidence is SalaryConfidence.UNPARSEABLE


def test_ceiling_without_a_floor_leaves_the_minimum_unset() -> None:
    """Screening a ceiling as a starting salary is the expensive mistake."""
    result = parse_salary("Up to £86,500 per annum")

    assert result.minimum is None


@pytest.mark.parametrize(
    "raw",
    [
        "£36,636 to £38,784 with progression to £46,049",
        "£36,636 - £38,784, rising to £46,049",
        "£36,636 to £38,784 with a discretionary range to £46,049",
    ],
)
def test_progression_language_sets_the_ceiling_never_the_floor(raw: str) -> None:
    """Words like "progression to" describe a future top figure, not the advertised band."""
    result = parse_salary(raw)

    assert result.minimum == Decimal("36636")


def test_progression_language_still_records_the_ceiling() -> None:
    result = parse_salary("£36,636 to £38,784 with progression to £46,049")

    assert result.maximum == Decimal("46049")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("£38,784 per annum", SalaryPeriod.ANNUAL),
        ("£38,784 p.a.", SalaryPeriod.ANNUAL),
        ("£12,500 per month", SalaryPeriod.MONTHLY),
        ("£1,200 per week", SalaryPeriod.WEEKLY),
        ("£38,784 to £46,049", SalaryPeriod.UNKNOWN),
    ],
)
def test_detects_the_period(raw: str, expected: SalaryPeriod) -> None:
    assert parse_salary(raw).period is expected


def test_a_monthly_figure_is_not_screenable() -> None:
    """Annualising a monthly figure means guessing at the contract, so it is refused."""
    result = parse_salary("£4,200 per month")

    assert result.is_screenable is False


def test_an_unstated_period_is_treated_as_annual() -> None:
    """University adverts that omit "per annum" are quoting annual salaries."""
    result = parse_salary("£47,389 rising to £51,753")

    assert result.is_screenable is True


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("£39,424 to £47,779 p.a. (gRADE 7)", "gRADE 7"),
        ("Band 7: £49,387 - £56,515", "Band 7"),
        ("UE07 £40,497 to £48,149", "UE07"),
        ("£36,636 per annum (Grade 3)", "Grade 3"),
        ("Grade Ha, £30,000", "Grade Ha"),
        ("£36,636 per annum", None),
    ],
)
def test_extracts_the_grade_as_written(raw: str, expected: str | None) -> None:
    """The grade is kept verbatim: it is what a human uses to check a parse against the advert."""
    assert parse_salary(raw).grade == expected


@pytest.mark.parametrize("raw", ["£500 per annum", "£750,000 per annum", "£0"])
def test_implausible_figures_are_parse_failures_not_salaries(raw: str) -> None:
    assert parse_salary(raw).confidence is SalaryConfidence.UNPARSEABLE


def test_the_same_string_parses_identically_twice() -> None:
    """The parser is pure; re-screening must be reproducible."""
    first = parse_salary("£38,784 to £46,049 per annum")
    second = parse_salary("£38,784 to £46,049 per annum")

    assert first == second
