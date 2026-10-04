"""Pure job-side rules: reading contract shape, hours and workplace off an advert."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from jobs.domain import (
    classify_contract_type,
    classify_discipline,
    classify_hours,
    classify_workplace,
    closes_within,
    looks_ghosted,
)
from jobs.enums import ApplicationStatus, ContractType, Discipline, Hours, Workplace

NOW = datetime(2026, 8, 23, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Permanent, full time", ContractType.PERMANENT),
        ("Fixed term until 31 August 2028", ContractType.FIXED_TERM),
        ("Fixed-term contract", ContractType.FIXED_TERM),
        ("12 month FTC", ContractType.FIXED_TERM),
        ("Maternity cover", ContractType.FIXED_TERM),
        ("Secondment opportunity", ContractType.SECONDMENT),
        ("Casual, zero-hours", ContractType.CASUAL),
        ("Open-ended contract", ContractType.PERMANENT),
        ("", ContractType.UNKNOWN),
        ("Research post", ContractType.UNKNOWN),
    ],
)
def test_reads_the_contract_shape(text: str, expected: ContractType) -> None:
    assert classify_contract_type(text) is expected


def test_a_fixed_term_beats_the_word_permanent() -> None:
    """A fixed term beats the word permanent.

    Adverts say "permanent contract, fixed term until 2028", and the fixed term is what a visa
    actually depends on.
    """
    assert classify_contract_type("Permanent contract, fixed term until 2028") is (
        ContractType.FIXED_TERM
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Full time, 36.5 hours", Hours.FULL_TIME),
        ("Part time, 0.6 FTE", Hours.PART_TIME),
        ("Salary pro-rata for part-time", Hours.PART_TIME),
        ("1.0 FTE", Hours.FULL_TIME),
        ("", Hours.UNKNOWN),
    ],
)
def test_reads_the_hours(text: str, expected: Hours) -> None:
    assert classify_hours(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hybrid working available", Workplace.HYBRID),
        ("This role is fully remote", Workplace.REMOTE),
        ("Campus-based", Workplace.ON_SITE),
        ("On-site working", Workplace.ON_SITE),
        ("", Workplace.UNKNOWN),
    ],
)
def test_reads_the_workplace(text: str, expected: Workplace) -> None:
    assert classify_workplace(text) is expected


@pytest.mark.parametrize(
    ("closing", "expected"),
    [
        (date(2026, 8, 23), True),
        (date(2026, 8, 30), True),
        (date(2026, 8, 31), False),
        (date(2026, 8, 22), False),
        (None, False),
    ],
)
def test_closing_soon_covers_today_through_the_horizon(
    closing: date | None, expected: bool
) -> None:
    assert closes_within(closing, today=date(2026, 8, 23), days=7) is expected


def test_an_application_that_never_got_a_reply_is_ghosted() -> None:
    assert (
        looks_ghosted(
            status=ApplicationStatus.APPLIED,
            applied_at=NOW - timedelta(days=22),
            response_at=None,
            now=NOW,
        )
        is True
    )


def test_an_application_that_got_a_reply_is_never_ghosted() -> None:
    assert (
        looks_ghosted(
            status=ApplicationStatus.APPLIED,
            applied_at=NOW - timedelta(days=90),
            response_at=NOW - timedelta(days=60),
            now=NOW,
        )
        is False
    )


@pytest.mark.parametrize(
    "status",
    [
        ApplicationStatus.FOUND,
        ApplicationStatus.READY,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED,
    ],
)
def test_only_an_applied_application_can_be_ghosted(status: ApplicationStatus) -> None:
    assert (
        looks_ghosted(status=status, applied_at=NOW - timedelta(days=90), response_at=None, now=NOW)
        is False
    )


def test_an_application_never_submitted_is_not_ghosted() -> None:
    assert (
        looks_ghosted(status=ApplicationStatus.APPLIED, applied_at=None, response_at=None, now=NOW)
        is False
    )


@pytest.mark.parametrize(("days", "expected"), [(20, False), (21, True), (22, True)])
def test_the_ghosting_window_boundary(days: int, expected: bool) -> None:
    assert (
        looks_ghosted(
            status=ApplicationStatus.APPLIED,
            applied_at=NOW - timedelta(days=days),
            response_at=None,
            now=NOW,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Vice-Chancellor", Discipline.SENIOR_MANAGEMENT),
        ("Director of Estates", Discipline.SENIOR_MANAGEMENT),
        ("HR Business Partner", Discipline.HUMAN_RESOURCES),
        ("Management Accountant", Discipline.FINANCE_PROCUREMENT),
        ("Compliance Officer", Discipline.LEGAL_COMPLIANCE_POLICY),
        ("Estates Maintenance Technician", Discipline.ESTATES_FACILITIES_MANAGEMENT),
        ("IT Support Technician", Discipline.IT_SERVICES),
        ("Full-Stack Developer", Discipline.WEB_DESIGN_DEVELOPMENT),
        ("Subject Librarian", Discipline.LIBRARY_SERVICES_DATA_INFORMATION),
        ("Marketing Officer", Discipline.PR_MARKETING_SALES_COMMUNICATION),
        ("Alumni Relations Officer", Discipline.FUNDRAISING_ALUMNI_BIDS_GRANTS),
        ("Project Manager", Discipline.PROJECT_MANAGEMENT_CONSULTING),
        ("Student Support Officer", Discipline.STUDENT_SERVICES),
        ("Study Abroad Coordinator", Discipline.INTERNATIONAL_ACTIVITIES),
        ("Wellbeing Adviser", Discipline.HEALTH_WELLBEING_CARE),
        ("Conference and Events Coordinator", Discipline.HOSPITALITY_RETAIL_EVENTS),
        ("Laboratory Technician", Discipline.LABORATORY_CLINICAL_TECHNICIAN),
        ("Sustainability Officer", Discipline.SUSTAINABILITY),
        ("Administrative Assistant", Discipline.ADMINISTRATIVE),
        ("Lecturer in Agriculture", Discipline.AGRICULTURE_FOOD_VETERINARY),
        ("Research Fellow in Architecture", Discipline.ARCHITECTURE_BUILDING_PLANNING),
        ("Postdoctoral Researcher in Molecular Biology", Discipline.BIOLOGICAL_SCIENCES),
        ("Lecturer in the Business School", Discipline.BUSINESS_MANAGEMENT_STUDIES),
        ("Lecturer in Computer Science", Discipline.COMPUTER_SCIENCES),
        ("Lecturer in Fine Art", Discipline.CREATIVE_ARTS_DESIGN),
        ("Lecturer in Economics", Discipline.ECONOMICS),
        ("Lecturer in Education Studies", Discipline.EDUCATION_STUDIES),
        ("Research Associate in Mechanical Engineering", Discipline.ENGINEERING_TECHNOLOGY),
        ("Clinical Lecturer in Medicine", Discipline.HEALTH_MEDICAL),
        ("Lecturer in History", Discipline.HISTORICAL_PHILOSOPHICAL_STUDIES),
        ("Lecturer in Information Science", Discipline.INFORMATION_MANAGEMENT_LIBRARIANSHIP),
        ("Lecturer in Modern Languages", Discipline.LANGUAGES_LITERATURE_CULTURE),
        ("Lecturer in the Law School", Discipline.LAW),
        ("Lecturer in Applied Mathematics", Discipline.MATHEMATICS_STATISTICS),
        ("Lecturer in Journalism", Discipline.MEDIA_COMMUNICATIONS),
        ("Postdoctoral Researcher in Physics", Discipline.PHYSICAL_ENVIRONMENTAL_SCIENCES),
        ("Lecturer in Politics", Discipline.POLITICS_GOVERNMENT),
        ("Lecturer in Psychology", Discipline.PSYCHOLOGY),
        ("Lecturer in Sociology", Discipline.SOCIAL_SCIENCES_SOCIAL_CARE),
        ("Lecturer in Sport Science", Discipline.SPORT_LEISURE),
        ("PhD Studentship in Genetics", Discipline.STUDENTSHIPS_PHDS),
        ("Front of House Assistant", Discipline.OTHER),
    ],
)
def test_classify_discipline_from_the_title(title: str, expected: Discipline) -> None:
    assert classify_discipline(title, "", "") == expected


def test_a_studentship_is_recognised_ahead_of_its_own_subject() -> None:
    """A studentship title beats its own subject - the subject here is secondary."""
    result = classify_discipline("PhD Studentship in Genetics", "", "")
    assert result == Discipline.STUDENTSHIPS_PHDS


def test_senior_management_is_settled_before_business_studies() -> None:
    """The word "director" must not fall through to Business & Management Studies."""
    result = classify_discipline("Director of Business Engagement", "", "")
    assert result == Discipline.SENIOR_MANAGEMENT


def test_the_platforms_own_category_is_read_when_the_title_says_nothing() -> None:
    result = classify_discipline("Post 4938", "Biological Sciences", "")
    assert result == Discipline.BIOLOGICAL_SCIENCES


def test_the_department_is_read_when_neither_title_nor_category_says_anything() -> None:
    assert classify_discipline("Post 4938", "", "School of Psychology") == Discipline.PSYCHOLOGY


def test_nothing_recognisable_is_other_not_a_guess() -> None:
    assert classify_discipline("Post 4938", "", "") == Discipline.OTHER


def test_matching_is_case_insensitive() -> None:
    result = classify_discipline("LECTURER IN PHYSICS", "", "")
    assert result == Discipline.PHYSICAL_ENVIRONMENTAL_SCIENCES


def test_every_discipline_value_is_reachable_by_at_least_one_keyword() -> None:
    """A member with no keyword that ever fires would be dead code nobody would notice."""
    from jobs.domain import _DISCIPLINE_KEYWORDS

    covered = {discipline for discipline, _ in _DISCIPLINE_KEYWORDS}
    everything_but_other = {member for member in Discipline if member is not Discipline.OTHER}
    assert covered == everything_but_other
