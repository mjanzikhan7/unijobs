"""Turning a search box's contents into countable terms. Pure functions, literal strings.

The word cloud is read as a statement about what people want, so the tokeniser's judgements are
worth pinning down: what counts as one vote, what is noise, and what must never be allowed to
dominate.
"""

from __future__ import annotations

import pytest

from analytics.domain import (
    MAX_QUERY_CHARS,
    count_terms,
    normalise_query,
    terms_in,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Research Software Engineer", "research software engineer"),
        ("  padded  ", "padded"),
        ("Collapsed\n\twhitespace", "collapsed whitespace"),
        ("", ""),
    ],
)
def test_normalise_query(raw: str, expected: str) -> None:
    assert normalise_query(raw) == expected


def test_a_very_long_query_is_truncated() -> None:
    """A paste is not a search, and letting one event carry unlimited terms lets it dominate."""
    assert len(normalise_query("x" * (MAX_QUERY_CHARS * 3))) == MAX_QUERY_CHARS


def test_terms_are_extracted_in_order() -> None:
    assert terms_in("Research Software Engineer") == ("research", "software", "engineer")


def test_stopwords_are_dropped() -> None:
    assert terms_in("lecturer in the department of physics") == (
        "lecturer",
        "department",
        "physics",
    )


def test_the_word_job_is_a_stopword_here() -> None:
    """Every search is for a job; counting the word tells you nothing about which."""
    assert "job" not in terms_in("python job")


def test_single_letters_are_dropped() -> None:
    assert terms_in("a c x python") == ("python",)


def test_technology_names_with_punctuation_survive() -> None:
    """`c++`, `c#` and `.net` are real skills, and a naive word split destroys all three."""
    assert terms_in("c++ and c# and node.js") == ("c++", "c#", "node.js")


def test_a_term_repeated_in_one_search_counts_once() -> None:
    """Otherwise one person typing "python python python" outweighs three people."""
    assert terms_in("python python python") == ("python",)


def test_case_is_ignored() -> None:
    assert terms_in("PYTHON Django") == ("python", "django")


def test_an_empty_search_yields_nothing() -> None:
    assert terms_in("") == ()


def test_punctuation_only_yields_nothing() -> None:
    assert terms_in("!!! ... ???") == ()


def test_counting_is_one_vote_per_search() -> None:
    counts = count_terms(["python django", "python", "python python python"])

    assert counts["python"] == 3
    assert counts["django"] == 1


def test_counting_an_empty_list() -> None:
    assert count_terms([]) == {}
