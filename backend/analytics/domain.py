"""Turning what someone typed into something we can count. Pure Python, on purpose.

No Django, no I/O, no clock. Deciding what counts as a "term" (case, punctuation, words that
mean nothing) should be tested on plain strings, without a database.
"""

from __future__ import annotations

import re
from collections import Counter

STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "job",
        "jobs",
        "role",
        "roles",
        "vacancy",
        "vacancies",
        "position",
        "positions",
        "uk",
    }
)

MAX_QUERY_CHARS = 200

MIN_TERM_CHARS = 2

_WORD = re.compile(r"[a-z0-9][a-z0-9+#.\-]*", re.IGNORECASE)


def normalise_query(raw: str) -> str:
    """Return a search string in a form we can compare.

    Lowercased with single spaces, so "Research Software Engineer" and "research software
    engineer" count as one search.
    """
    return re.sub(r"\s+", " ", (raw or "").strip()).casefold()[:MAX_QUERY_CHARS]


def terms_in(raw: str) -> tuple[str, ...]:
    """Return the terms in a search string, in order, without repeats.

    "python python python" is one interest in Python. Counting it three times would let one search
    change a whole day's word cloud.
    """
    seen: list[str] = []
    for match in _WORD.finditer(normalise_query(raw)):
        term = match.group(0).strip(".-")
        if len(term) < MIN_TERM_CHARS or term in STOPWORDS or term in seen:
            continue
        seen.append(term)
    return tuple(seen)


def count_terms(queries: list[str]) -> Counter[str]:
    """Count terms across many searches, one vote per search."""
    counter: Counter[str] = Counter()
    for query in queries:
        counter.update(terms_in(query))
    return counter
