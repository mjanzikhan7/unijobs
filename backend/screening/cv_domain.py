"""Reading a CV into the criteria used for fitness scoring. Pure Python, on purpose.

No Django, no I/O, no clock. The text comes in as a string and the word list as an argument,
so every rule can be tested with a plain function call.

This is not :func:`screening.domain.required_years`. That reads how many years an advert asks
for. This reads how many years a candidate claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VocabularyTerm:
    """One thing worth spotting in a CV, and the ways it might be written."""

    canonical: str
    kind: str
    aliases: tuple[str, ...] = ()

    def spellings(self) -> tuple[str, ...]:
        """Every string that counts as this term."""
        return (self.canonical, *self.aliases)


@dataclass(frozen=True, slots=True)
class ExtractedCriteria:
    """What a CV appears to claim. Every field is a suggestion, not a fact."""

    skills: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    seniority: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    education: tuple[str, ...] = ()
    years_experience: int = 0
    missing: tuple[str, ...] = field(default=())


_YEARS_CLAIMED = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)(?:['’]?s?)?"  # noqa: RUF001
    r"\s+(?:of\s+)?(?:[a-z]+\s+){0,3}?(?:experience|exp\b)",
    re.IGNORECASE,
)

MAX_TEXT_CHARS = 400_000

_SKILLS_HEADING = re.compile(
    r"^\s*(technical\s+skills|core\s+skills|key\s+skills|skills(?:\s*(?:&|and)\s*"
    r"(?:tools|expertise))?)\s*:?\s*$",
    re.IGNORECASE,
)

_LABELLED_LIST_LINE = re.compile(r"^[ \t]*[A-Za-z][A-Za-z /&\-]{1,40}:[ \t]*(?P<items>.+\S)\s*$")

_ITEM_SPLIT = re.compile(r"[,;•|]")

_BLANK_LINES_CLOSE_SECTION = 2

MAX_DECLARED_SKILLS = 150


def _normalise(text: str) -> str:
    """Flatten whitespace so a term split across a line break still matches."""
    return re.sub(r"\s+", " ", text).casefold()


def _term_present(spelling: str, haystack: str) -> bool:
    """Whether a term appears as a whole word or phrase.

    Whole words only, so "r" does not match every word with an r in it, and "go" does not match
    "going". ``screening.domain`` uses the same rule for adverts, and the two must agree.
    """
    pattern = r"(?<!\w)" + re.escape(spelling.casefold()) + r"(?!\w)"
    return re.search(pattern, haystack) is not None


def _declared_skill_lines(text: str) -> list[str]:
    """The comma-separated lines inside the CV's own Skills section.

    A line with "Label: items" adds its items. A line with commas but no label continues the line
    before, because PDF and Word text often splits lines. A line with no colon and no list is the
    next heading, such as "Experience", and ends the section. So do two blank lines in a row.
    """
    lines: list[str] = []
    in_section = False
    blank_run = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if _SKILLS_HEADING.match(line):
            in_section = True
            blank_run = 0
            continue
        if not in_section:
            continue
        if not line:
            blank_run += 1
            if blank_run >= _BLANK_LINES_CLOSE_SECTION:
                break
            continue
        blank_run = 0
        match = _LABELLED_LIST_LINE.match(line)
        if match:
            lines.append(match.group("items"))
        elif any(delimiter in line for delimiter in ",;•|"):
            lines.append(line)
        else:
            break

    return lines


def extract_declared_skills(text: str) -> tuple[str, ...]:
    """What the CV lists under its own Skills heading, exactly as written.

    A word list can never be complete. A real skill the candidate wrote should not disappear just
    because nobody has added it as a ``SkillTerm`` yet.
    """
    seen: dict[str, str] = {}
    for line in _declared_skill_lines(text):
        opened_out = line.replace("(", ",").replace(")", ",")
        for raw_item in _ITEM_SPLIT.split(opened_out):
            item = raw_item.strip(" \t.")
            if not item or len(item) > 40:
                continue
            key = item.casefold()
            if key in seen:
                continue
            seen[key] = item
            if len(seen) >= MAX_DECLARED_SKILLS:
                return tuple(seen.values())
    return tuple(seen.values())


def claimed_years(text: str) -> int:
    """Return the largest number of years of experience the text claims.

    The largest, not the first. "5 years of Python and 12 years of research" claims twelve.
    """
    matches = _YEARS_CLAIMED.findall(text)
    return max((int(value) for value in matches), default=0)


def extract_terms(text: str, vocabulary: tuple[VocabularyTerm, ...]) -> ExtractedCriteria:
    """Read a CV's text into criteria, using the given word list.

    It finds what the word list contains. Skills also include what the CV's own Skills section
    lists (see :func:`extract_declared_skills`). The result is shown to the candidate to confirm,
    not written straight to their profile.
    """
    truncated = text[:MAX_TEXT_CHARS]
    haystack = _normalise(truncated)

    found: dict[str, list[str]] = {}
    missing: list[str] = []

    for term in vocabulary:
        if any(_term_present(spelling, haystack) for spelling in term.spellings()):
            bucket = found.setdefault(term.kind, [])
            if term.canonical not in bucket:
                bucket.append(term.canonical)
        else:
            missing.append(term.canonical)

    skills = list(found.get("skill", ()))
    already_named = {skill.casefold() for skill in skills}
    for declared in extract_declared_skills(truncated):
        if declared.casefold() not in already_named:
            skills.append(declared)
            already_named.add(declared.casefold())

    return ExtractedCriteria(
        skills=tuple(skills),
        domains=tuple(found.get("domain", ())),
        seniority=tuple(found.get("seniority", ())),
        projects=tuple(found.get("project", ())),
        education=tuple(found.get("education", ())),
        years_experience=claimed_years(haystack),
        missing=tuple(missing),
    )
