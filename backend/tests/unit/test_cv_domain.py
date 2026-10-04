"""Reading a CV into criteria. Pure functions, literal strings, no files.

Held to the same 100% line-and-branch standard as `screening/domain.py`: this decides what a
candidate's whole ranking is computed from, and it is cheap to test exhaustively.
"""

from __future__ import annotations

import pytest

from screening.cv_domain import (
    MAX_DECLARED_SKILLS,
    MAX_TEXT_CHARS,
    VocabularyTerm,
    claimed_years,
    extract_declared_skills,
    extract_terms,
)

VOCABULARY = (
    VocabularyTerm(canonical="python", kind="skill", aliases=("python3",)),
    VocabularyTerm(canonical="django", kind="skill"),
    VocabularyTerm(canonical="kubernetes", kind="skill", aliases=("k8s",)),
    VocabularyTerm(canonical="higher education", kind="domain", aliases=("universities",)),
    VocabularyTerm(canonical="senior", kind="seniority"),
    VocabularyTerm(canonical="data pipeline", kind="project"),
    VocabularyTerm(canonical="msc", kind="education", aliases=("master of science",)),
)


def test_a_skill_is_found() -> None:
    result = extract_terms("Experienced Python developer.", VOCABULARY)

    assert "python" in result.skills


def test_matching_ignores_case() -> None:
    assert "python" in extract_terms("PYTHON", VOCABULARY).skills


def test_an_alias_maps_to_its_canonical_name() -> None:
    """A profile holding both "k8s" and "kubernetes" would score the same skill twice."""
    result = extract_terms("Ran k8s clusters.", VOCABULARY)

    assert result.skills == ("kubernetes",)


def test_a_multi_word_phrase_is_found() -> None:
    assert "higher education" in extract_terms("Worked in higher education.", VOCABULARY).domains


def test_a_term_split_across_a_line_break_is_still_found() -> None:
    """PDF extraction wraps lines wherever the column ended, not where the phrase did."""
    result = extract_terms("Worked in higher\neducation for years.", VOCABULARY)

    assert "higher education" in result.domains


def test_a_substring_of_a_longer_word_is_not_a_match() -> None:
    """A term inside a longer word is not that term: "djangoesque" is not Django."""
    assert extract_terms("djangoesque architecture", VOCABULARY).skills == ()


def test_a_term_touching_punctuation_is_found() -> None:
    assert "python" in extract_terms("Skills: Python, Django.", VOCABULARY).skills


def test_a_repeated_term_is_reported_once() -> None:
    result = extract_terms("Python. Python. Python everywhere.", VOCABULARY)

    assert result.skills == ("python",)


def test_terms_land_in_the_bucket_their_kind_names() -> None:
    result = extract_terms(
        "Senior Python engineer in higher education, built a data pipeline, MSc.", VOCABULARY
    )

    assert result.skills == ("python",)
    assert result.domains == ("higher education",)
    assert result.seniority == ("senior",)
    assert result.projects == ("data pipeline",)
    assert result.education == ("msc",)


def test_what_was_looked_for_and_not_found_is_reported() -> None:
    """So a candidate can see the parser's vocabulary rather than guess at its silence."""
    result = extract_terms("Python only.", VOCABULARY)

    assert "kubernetes" in result.missing
    assert "python" not in result.missing


def test_an_empty_cv_yields_nothing() -> None:
    result = extract_terms("", VOCABULARY)

    assert result.skills == ()
    assert result.years_experience == 0
    assert len(result.missing) == len(VOCABULARY)


def test_an_empty_vocabulary_finds_nothing_and_claims_nothing_missing() -> None:
    result = extract_terms("Python, Django, everything.", ())

    assert (result.skills, result.missing) == ((), ())


def test_text_beyond_the_ceiling_is_ignored() -> None:
    """A ceiling on regex work, so a pathological upload cannot burn CPU indefinitely."""
    padding = "a " * MAX_TEXT_CHARS
    result = extract_terms(padding + "python", VOCABULARY)

    assert result.skills == ()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("8 years of experience", 8),
        ("8 years experience", 8),
        ("10+ years of experience", 10),
        ("3 yrs experience", 3),
        ("12 years' experience", 12),
        ("12 years’ experience", 12),  # noqa: RUF001
        ("5 years of exp", 5),
        ("no numbers here", 0),
        ("", 0),
        ("years of experience", 0),
    ],
)
def test_claimed_years(text: str, expected: int) -> None:
    assert claimed_years(text) == expected


def test_the_largest_claim_wins() -> None:
    """Taking the first would undersell a candidate against a threshold they clear."""
    assert claimed_years("5 years of Python and 12 years of research experience") == 12


def test_years_are_read_through_extract_terms_too() -> None:
    result = extract_terms("Senior engineer with 9 years of experience.", VOCABULARY)

    assert result.years_experience == 9


def test_a_labelled_list_line_under_the_heading_is_read() -> None:
    text = "Technical Skills\nProgramming: Python, Terraform, Datadog"
    assert extract_declared_skills(text) == ("Python", "Terraform", "Datadog")


def test_several_sub_category_lines_are_all_read() -> None:
    """Every CV template names its sub-categories differently; the label itself is never matched."""
    text = "Skills\nFrameworks: Django, Flask\nDatabases: Postgres, Redis"
    assert extract_declared_skills(text) == ("Django", "Flask", "Postgres", "Redis")


def test_a_heading_with_no_colon_and_trailing_whitespace_still_opens_the_section() -> None:
    assert extract_declared_skills("Skills  \nTools: Git") == ("Git",)


def test_text_before_the_heading_is_never_read_as_a_skills_line() -> None:
    text = "Employer: Cambridge University\nTechnical Skills\nProgramming: Python"
    assert extract_declared_skills(text) == ("Python",)


def test_a_wrapped_continuation_line_is_still_read() -> None:
    """PDF extraction loses the original layout: one logical line arrives as two or three."""
    text = "Technical Skills\nCloud Platforms: AWS (ECS, Lambda), Monitoring\n(CloudWatch), Vault"
    skills = extract_declared_skills(text)
    assert "CloudWatch" in skills
    assert "Vault" in skills


def test_a_parenthesised_aside_becomes_its_own_items_not_one_fused_token() -> None:
    text = "Skills\nCloud: AWS (ECS, RDS, Lambda)"
    skills = extract_declared_skills(text)
    assert "ECS" in skills
    assert "RDS" in skills
    assert "Lambda" in skills
    assert "AWS (ECS, RDS, Lambda)" not in skills


def test_a_bare_heading_line_with_no_colon_or_list_closes_the_section() -> None:
    """The next section's own heading - "Experience", "Education" - looks exactly like this."""
    text = "Technical Skills\nProgramming: Python, Django\nExperience\nEmployer: Java, Spring"
    skills = extract_declared_skills(text)
    assert skills == ("Python", "Django")


def test_two_blank_lines_close_the_section() -> None:
    text = "Technical Skills\nProgramming: Python\n\n\nOther: Java"
    assert extract_declared_skills(text) == ("Python",)


def test_a_single_blank_line_does_not_close_the_section() -> None:
    text = "Technical Skills\nProgramming: Python\n\nDatabases: Postgres"
    assert extract_declared_skills(text) == ("Python", "Postgres")


def test_a_repeated_item_across_lines_is_reported_once_in_its_first_casing() -> None:
    text = "Skills\nLang: Python, PYTHON\nOther: python"
    assert extract_declared_skills(text) == ("Python",)


def test_an_item_over_the_length_ceiling_is_dropped() -> None:
    """A sentence that happens to contain a comma is not a skill just because it is short-ish."""
    long_phrase = "a" * 41
    text = f"Skills\nList: Python, {long_phrase}"
    assert extract_declared_skills(text) == ("Python",)


def test_nothing_before_a_skills_heading_yields_nothing() -> None:
    assert extract_declared_skills("Just a CV with no skills heading anywhere.") == ()


def test_an_empty_labelled_line_contributes_nothing() -> None:
    assert extract_declared_skills("Skills\nTools: , ,") == ()


def test_the_declared_skill_ceiling_stops_collection() -> None:
    items = ", ".join(f"skill{i}" for i in range(MAX_DECLARED_SKILLS + 20))
    text = f"Skills\nA: {items}"
    assert len(extract_declared_skills(text)) == MAX_DECLARED_SKILLS


def test_declared_skills_flow_through_extract_terms() -> None:
    """A term the vocabulary has not caught up to yet is not silently dropped."""
    text = "Technical Skills\nTools: Terraform, Datadog\n\nExperience\nBuilt things."
    result = extract_terms(text, VOCABULARY)

    assert "Terraform" in result.skills
    assert "Datadog" in result.skills


def test_a_declared_skill_already_matched_by_the_vocabulary_is_not_duplicated() -> None:
    text = "Technical Skills\nLanguages: Python, Django\n\nExperience\nBuilt things."
    result = extract_terms(text, VOCABULARY)

    assert result.skills.count("python") == 1
    assert "Python" not in result.skills


def test_a_term_lists_its_canonical_spelling_first() -> None:
    term = VocabularyTerm(canonical="kubernetes", kind="skill", aliases=("k8s",))

    assert term.spellings() == ("kubernetes", "k8s")


def test_a_term_without_aliases_has_one_spelling() -> None:
    assert VocabularyTerm(canonical="django", kind="skill").spellings() == ("django",)
