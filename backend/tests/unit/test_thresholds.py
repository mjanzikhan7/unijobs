"""Banding the advertised floor against the ruleset.

Boundaries get a test on each side because an off-by-one here is invisible: £54,699 and £54,700
look the same in a list, and only one of them clears the going rate.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from screening.domain import Thresholds, evaluate_threshold, parse_salary
from screening.enums import ThresholdVerdict


@pytest.mark.parametrize(
    ("floor", "expected"),
    [
        ("36999", ThresholdVerdict.EXCLUDED_BELOW_FLOOR),
        ("37000", ThresholdVerdict.PAY_CUT),
        ("37001", ThresholdVerdict.PAY_CUT),
        ("50274", ThresholdVerdict.PAY_CUT),
        ("50275", ThresholdVerdict.LATERAL_CONTINGENT),
        ("50276", ThresholdVerdict.LATERAL_CONTINGENT),
        ("54699", ThresholdVerdict.LATERAL_CONTINGENT),
        ("54700", ThresholdVerdict.TARGET_BAND),
        ("54701", ThresholdVerdict.TARGET_BAND),
    ],
)
def test_bands_each_side_of_every_boundary(
    floor: str, expected: ThresholdVerdict, thresholds: Thresholds
) -> None:
    """Bands are inclusive at the bottom: exactly the going rate is TARGET_BAND."""
    salary = parse_salary(f"£{int(floor):,} per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.verdict is expected


def test_screens_on_the_bottom_of_the_range_not_the_top(thresholds: Thresholds) -> None:
    """The floor is what goes on a Certificate of Sponsorship and what they appoint at."""
    salary = parse_salary("£38,784 to £86,049 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.screened_on == Decimal("38784")


def test_a_wide_range_is_banded_on_its_floor(thresholds: Thresholds) -> None:
    salary = parse_salary("£38,784 to £86,049 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.verdict is ThresholdVerdict.PAY_CUT


def test_a_ceiling_with_no_floor_is_unclear_not_optimistic(thresholds: Thresholds) -> None:
    """£86,500 would land in TARGET_BAND; screening it there would be a lie."""
    salary = parse_salary("Up to £86,500 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.verdict is ThresholdVerdict.SALARY_UNCLEAR


def test_an_unclear_salary_is_never_screened_against_anything(thresholds: Thresholds) -> None:
    salary = parse_salary("Up to £86,500 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.screened_on is None


def test_an_unparseable_salary_is_unclear(thresholds: Thresholds) -> None:
    salary = parse_salary("Competitive")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.verdict is ThresholdVerdict.SALARY_UNCLEAR


def test_a_non_annual_figure_is_unclear(thresholds: Thresholds) -> None:
    """Annualising a monthly figure means guessing at the contract."""
    salary = parse_salary("£4,200 per month")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.verdict is ThresholdVerdict.SALARY_UNCLEAR


@pytest.mark.parametrize(
    ("floor", "expected"),
    [("41699", False), ("41700", True), ("54700", True)],
)
def test_records_whether_the_general_threshold_is_met(
    floor: str, expected: bool, thresholds: Thresholds
) -> None:
    """The statutory figure is tracked separately from the candidate's own economics."""
    salary = parse_salary(f"£{int(floor):,} per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.general_threshold_met is expected


@pytest.mark.parametrize(("floor", "expected"), [("54699", False), ("54700", True)])
def test_records_whether_the_going_rate_is_met(
    floor: str, expected: bool, thresholds: Thresholds
) -> None:
    salary = parse_salary(f"£{int(floor):,} per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert assessment.going_rate_met is expected


def test_an_unclear_salary_reports_neither_statutory_test_as_met(
    thresholds: Thresholds,
) -> None:
    """``None`` rather than ``False``: "we do not know" is not "it fails"."""
    salary = parse_salary("Competitive")

    assessment = evaluate_threshold(salary, thresholds)

    assert (assessment.general_threshold_met, assessment.going_rate_met) == (None, None)


def test_the_explanation_names_the_figure_that_produced_the_verdict(
    thresholds: Thresholds,
) -> None:
    """A badge without a reason is unarguable; the reason is what lets a human overrule it."""
    salary = parse_salary("£38,784 to £46,049 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert "£50,275" in assessment.explanation


def test_the_explanation_says_which_end_of_the_range_was_used(
    thresholds: Thresholds,
) -> None:
    salary = parse_salary("£38,784 to £46,049 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert "bottom of the range" in assessment.explanation


def test_an_unclear_verdict_explains_why_it_could_not_be_banded(
    thresholds: Thresholds,
) -> None:
    salary = parse_salary("Up to £86,500 per annum")

    assessment = evaluate_threshold(salary, thresholds)

    assert "ceiling" in assessment.explanation


def test_a_different_going_rate_moves_the_target_band() -> None:
    """The going rate depends on the occupation code, so it is a parameter, not a constant."""
    researcher_rates = Thresholds(
        personal_floor=Decimal("37000"),
        current_package=Decimal("50275"),
        going_rate=Decimal("43600"),
        standard_general=Decimal("41700"),
        transitional_general=Decimal("31300"),
        going_rate_key="soc_2162_going_rate",
    )
    salary = parse_salary("£52,000 per annum")

    assessment = evaluate_threshold(salary, researcher_rates)

    assert assessment.verdict is ThresholdVerdict.TARGET_BAND
