"""Pure screening logic: name matching, salary parsing, threshold bands, fitness scores.

This module does not import Django, use the network, read the clock or use randomness. Each
function takes inputs and returns a value, so the riskiest logic is also the quickest to test.

Two rules apply everywhere:

* **Check the bottom of the salary range.** The lowest figure is what universities usually
  appoint at, and what goes on a Certificate of Sponsorship.
* **When unsure, say so.** A wrong "yes, they sponsor" costs a person weeks. "Please check"
  costs a minute.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Final, NamedTuple

from screening.enums import (
    MatchMethod,
    SalaryConfidence,
    SalaryPeriod,
    SponsorVerdict,
    ThresholdVerdict,
)

_STOPWORDS: Final[frozenset[str]] = frozenset({"the", "of", "and", "for", "at", "in", "a", "an"})

_GENERIC_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "university",
        "universities",
        "college",
        "school",
        "institute",
        "institution",
        "academy",
        "conservatoire",
        "higher",
        "education",
        "corporation",
        "limited",
        "ltd",
        "plc",
        "llp",
        "cic",
        "cio",
        "trust",
        "group",
        "hr",
        "uk",
        "united",
        "kingdom",
    }
)

_SUFFIX_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bhigher education corporation\b",
        r"\bhigher education institution\b",
        r"\b(?:co(?:mpany)?\s*)?limited\b",
        r"\bltd\b",
        r"\bplc\b",
        r"\bllp\b",
        r"\bcic\b",
        r"\bcio\b",
        r"\bincorporated\b",
    )
)

_PARENTHETICAL = re.compile(r"\([^)]*\)")
_NON_WORD = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")
_LEADING_THE = re.compile(r"^the\s+")


def _strip_accents(value: str) -> str:
    """Return ``value`` with combining marks removed, so Ecole matches École."""
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalise_organisation_name(name: str) -> str:
    """Reduce an organisation name to a form we can compare.

    Lowercases, removes accents, punctuation, text in brackets (like the ``(HR)`` in Imperial's
    entry), legal suffixes and a leading ``The``. The register says "The University of Cambridge"
    where people say "Cambridge".
    """
    value = _strip_accents(name).casefold()
    value = _PARENTHETICAL.sub(" ", value)
    value = value.replace("&", " and ")
    value = _NON_WORD.sub(" ", value)
    value = _WHITESPACE.sub(" ", value).strip()
    for pattern in _SUFFIX_PATTERNS:
        value = pattern.sub(" ", value)
    value = _WHITESPACE.sub(" ", value).strip()
    value = _LEADING_THE.sub("", value)
    return value


def name_tokens(name: str) -> tuple[str, ...]:
    """Return the normalised words of ``name``, stopwords included."""
    normalised = normalise_organisation_name(name)
    return tuple(token for token in normalised.split() if token)


def core_tokens(name: str) -> frozenset[str]:
    """Return the identifying words of ``name``.

    ``University of Cambridge`` and ``Cambridge University`` both give ``{cambridge}``. This
    catches everyday name variants without fuzzy matching.
    """
    return frozenset(
        token
        for token in name_tokens(name)
        if token not in _STOPWORDS and token not in _GENERIC_TOKENS
    )


def acronym_of(name: str) -> str:
    """Return the initials of the identifying words of ``name``.

    ``The London School of Economics and Political Science`` gives ``lseps``, and ``LSE`` is a
    prefix of it. We compare prefixes because short names are often shorter than the legal name.
    """
    return "".join(token[0] for token in name_tokens(name) if token and token not in _STOPWORDS)


def looks_like_acronym(name: str) -> bool:
    """Whether ``name`` is a short all-capitals token such as ``LSE`` or ``UCL``."""
    stripped = name.strip()
    return 2 <= len(stripped) <= 6 and stripped.isalpha() and stripped.isupper()


def name_similarity(left: str, right: str) -> float:
    """Score how alike two organisation names are, from 0.0 to 1.0.

    1.0 means the identifying words are the same. Anything lower is only a suggestion for a
    person to confirm. See :func:`decide_sponsor_match`.
    """
    left_core, right_core = core_tokens(left), core_tokens(right)
    if not left_core or not right_core:
        return 0.0
    if left_core == right_core:
        return 1.0

    shared = left_core & right_core
    containment = len(shared) / min(len(left_core), len(right_core))
    jaccard = len(shared) / len(left_core | right_core)

    acronym_score = 0.0
    for short, long in ((left, right), (right, left)):
        if looks_like_acronym(short):
            expansion = acronym_of(long)
            candidate = normalise_organisation_name(short).replace(" ", "")
            if expansion.startswith(candidate) and len(candidate) >= 2:
                acronym_score = 0.9

    return max(acronym_score, (containment * 0.75) + (jaccard * 0.25))


@dataclass(frozen=True, slots=True)
class RegisterCandidate:
    """One row of the sponsor register, as a candidate for an institution."""

    organisation_name: str
    town_city: str = ""
    type_rating: str = ""
    routes: tuple[str, ...] = ()
    similarity: float = 0.0

    def sponsors_skilled_worker(self) -> bool:
        """Whether this entry is licensed for the Skilled Worker route specifically."""
        return any("skilled worker" in route.casefold() for route in self.routes)


@dataclass(frozen=True, slots=True)
class SponsorDecision:
    """The outcome of matching an institution against the register."""

    verdict: SponsorVerdict
    matched_name: str | None
    method: MatchMethod
    confidence: float
    candidates: tuple[RegisterCandidate, ...] = ()
    needs_review: bool = False


def verdict_for_entry(candidate: RegisterCandidate) -> SponsorVerdict:
    """Turn a register entry's rating and routes into a verdict.

    A B-rated licence still allows sponsorship, but it means the employer has a compliance
    problem. So it gets its own verdict instead of ``CONFIRMED``.
    """
    rating = candidate.type_rating.casefold()
    if not candidate.sponsors_skilled_worker():
        return SponsorVerdict.OTHER_ROUTE_ONLY
    if "provisional" in rating:
        return SponsorVerdict.PROVISIONAL
    if "worker (b rating)" in rating or "b rating" in rating:
        return SponsorVerdict.B_RATED
    return SponsorVerdict.CONFIRMED


def decide_sponsor_match(
    institution_name: str,
    candidates: Sequence[RegisterCandidate],
    *,
    similarity_threshold: float = 0.62,
) -> SponsorDecision:
    """Run the matching steps for one institution.

    Exact and normalised matches are decided automatically. Anything weaker returns ``NOT_FOUND``
    with ranked candidates and ``needs_review`` set. A fuzzy match must never guess "yes". A person
    picks from the candidates in :mod:`screening.services`, and the answer is saved.
    """
    ranked = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                max(
                    candidate.similarity,
                    name_similarity(institution_name, candidate.organisation_name),
                ),
                -len(candidate.organisation_name),
            ),
            reverse=True,
        )
    )

    for candidate in ranked:
        if candidate.organisation_name.strip() == institution_name.strip():
            return SponsorDecision(
                verdict=verdict_for_entry(candidate),
                matched_name=candidate.organisation_name,
                method=MatchMethod.EXACT,
                confidence=1.0,
                candidates=ranked,
            )

    normalised_target = normalise_organisation_name(institution_name)
    for candidate in ranked:
        candidate_normalised = normalise_organisation_name(candidate.organisation_name)
        same_string = candidate_normalised == normalised_target
        same_core = core_tokens(candidate.organisation_name) == core_tokens(institution_name)
        if same_string or same_core:
            return SponsorDecision(
                verdict=verdict_for_entry(candidate),
                matched_name=candidate.organisation_name,
                method=MatchMethod.NORMALISED,
                confidence=0.95,
                candidates=ranked,
            )

    best = max(
        (
            max(
                candidate.similarity,
                name_similarity(institution_name, candidate.organisation_name),
            )
            for candidate in ranked
        ),
        default=0.0,
    )
    return SponsorDecision(
        verdict=SponsorVerdict.NOT_FOUND,
        matched_name=None,
        method=MatchMethod.TRIGRAM if best >= similarity_threshold else MatchMethod.NONE,
        confidence=best,
        candidates=ranked,
        needs_review=True,
    )


SPONSORSHIP_EXCLUSION_PHRASES: Final[tuple[str, ...]] = (
    "does not meet the minimum requirements for visa sponsorship",
    "does not meet the requirements for visa sponsorship",
    "not eligible for visa sponsorship",
    "not eligible for sponsorship under the skilled worker",
    "this role is not eligible for sponsorship",
    "this post is not eligible for sponsorship",
    "we are unable to offer visa sponsorship",
    "we are unable to sponsor",
    "unable to offer sponsorship",
    "cannot offer visa sponsorship",
    "cannot offer sponsorship",
    "no sponsorship is available",
    "sponsorship is not available",
    "visa sponsorship is not available",
    "does not attract visa sponsorship",
    "does not attract sponsorship",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

MAX_QUOTE_LENGTH: Final[int] = 300
QUOTE_CONTEXT: Final[int] = 110


def _excerpt(sentence: str, index: int, length: int) -> str:
    """Return the matched phrase with enough context to be judged, and no more."""
    if len(sentence) <= MAX_QUOTE_LENGTH:
        return sentence
    start = max(0, index - QUOTE_CONTEXT)
    end = min(len(sentence), index + length + QUOTE_CONTEXT)
    prefix = "… " if start > 0 else ""
    suffix = " …" if end < len(sentence) else ""
    return f"{prefix}{sentence[start:end].strip()}{suffix}"


def find_sponsorship_exclusion(text: str) -> str | None:
    """Return the sentence that rules sponsorship out, or ``None``.

    We return the whole sentence because the UI shows it, and a person needs the context to judge
    it. Whitespace is normalised first, so a phrase split over two lines is still found.

    Silence is not evidence. Most licensed sponsors never mention sponsorship, so there is no
    opposite of this function.
    """
    if not text:
        return None
    for sentence in _SENTENCE_SPLIT.split(text):
        cleaned = _WHITESPACE.sub(" ", sentence.replace("\n", " ")).strip()
        lowered = cleaned.casefold()
        for phrase in SPONSORSHIP_EXCLUSION_PHRASES:
            index = lowered.find(phrase)
            if index != -1:
                return _excerpt(cleaned, index, len(phrase))
    return None


def apply_advert_exclusion(verdict: SponsorVerdict, exclusion_found: bool) -> SponsorVerdict:
    """Let an advert overrule the register, but never the other way round.

    An advert that says "no sponsorship" is evidence about this job. The register is about the
    employer. An advert that says nothing tells us nothing.
    """
    if exclusion_found:
        return SponsorVerdict.NOT_FOUND
    return verdict


MIN_PLAUSIBLE_SALARY: Final[Decimal] = Decimal("1000")
MAX_PLAUSIBLE_SALARY: Final[Decimal] = Decimal("500000")


def _any_phrase(*phrases: str) -> str:
    """Return a pattern that matches any of the phrases as whole words, however spaced."""
    alternatives = "|".join(phrase.replace(" ", r"\s+") for phrase in phrases)
    return rf"\b(?:{alternatives})\b"


_THOUSANDS = r"\d{1,3}(?:,\d{3})+"
_PENCE = r"(?:\.\d{1,2})?"
_AMOUNT = re.compile(rf"(?:£|GBP\s?)\s*((?:{_THOUSANDS}|\d+){_PENCE})", re.IGNORECASE)

_CEILING_BEFORE_FIGURE = re.compile(_any_phrase("up to", "maximum of") + r"\s*$", re.IGNORECASE)
_UNFINISHED_RANGE = re.compile(r"\s*(?:[-\u2013\u2014]|(?:up\s+)?to\b)", re.IGNORECASE)

_PERIOD_PHRASES: Final[dict[SalaryPeriod, tuple[str, ...]]] = {
    SalaryPeriod.HOURLY: ("per hour", "an hour", "hourly", "p/?h"),
    SalaryPeriod.DAILY: ("per day", "a day", "daily", "per diem"),
    SalaryPeriod.WEEKLY: ("per week", "weekly", "p/?w"),
    SalaryPeriod.MONTHLY: ("per month", "per calendar month", "monthly", "pcm"),
    SalaryPeriod.ANNUAL: ("per annum", "per year", "annually", "annum", r"p\.?\s?a\.?", "p/?a"),
}
_PERIOD_PATTERNS: Final[dict[SalaryPeriod, re.Pattern[str]]] = {
    period: re.compile(_any_phrase(*phrases)) for period, phrases in _PERIOD_PHRASES.items()
}

_GRADE_LABEL = r"(?:grade|band|scale|level|spine\s*point|pay\s*band)"
_GRADE_VALUE = r"(?:[A-Za-z]{0,2}\d{1,3}[A-Za-z]?|[A-Za-z]{1,3})"
_GRADE_CODE = r"(?:UE\d{2}|AC\d{1,2})"
_GRADE = re.compile(
    rf"\b(?:{_GRADE_LABEL}\s*[:\-]?\s*{_GRADE_VALUE}|{_GRADE_CODE})\b", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class ParsedSalary:
    """A salary string, taken apart.

    ``minimum`` is what we check. ``maximum`` is for context. ``raw`` helps trace a wrong verdict.
    """

    raw: str
    minimum: Decimal | None
    maximum: Decimal | None
    currency: str
    period: SalaryPeriod
    confidence: SalaryConfidence
    grade: str | None = None

    @property
    def is_screenable(self) -> bool:
        """Whether there is a floor solid enough to band against a threshold."""
        if self.confidence is SalaryConfidence.UNPARSEABLE or self.minimum is None:
            return False
        return self.period in (SalaryPeriod.ANNUAL, SalaryPeriod.UNKNOWN)


class _Figures(NamedTuple):
    """The figures read from a salary string, and how far they can be trusted."""

    minimum: Decimal | None
    maximum: Decimal | None
    confidence: SalaryConfidence


_NO_FIGURES: Final = _Figures(None, None, SalaryConfidence.UNPARSEABLE)


def parse_salary(raw: str) -> ParsedSalary:
    """Parse an advertised salary string.

    Returns the bottom of the range as ``minimum``. Phrases about a future top figure ("rising
    to", "progression to") can set ``maximum`` but never ``minimum``.

    ``"Up to £86,500"`` gives ``minimum=None``. Treating a top figure as the starting salary
    could send someone to a job that cannot be sponsored.
    """
    text = (raw or "").strip()
    figures = _read_figures(text)
    return ParsedSalary(
        raw=raw,
        minimum=figures.minimum,
        maximum=figures.maximum,
        currency="GBP",
        period=detect_period(text),
        confidence=figures.confidence,
        grade=extract_grade(text),
    )


def _read_figures(text: str) -> _Figures:
    """Read the bottom and top figures from the text, without guessing.

    A ceiling ("Up to £86,500") has no bottom figure. A range that is cut short ("£9,883 -
    please see advert") has no top figure. One implausible figure rejects the whole string.
    """
    matches = list(_AMOUNT.finditer(text))
    amounts = [Decimal(match.group(1).replace(",", "")) for match in matches]
    if not amounts or not all(_is_plausible(amount) for amount in amounts):
        return _NO_FIGURES

    first, highest = amounts[0], max(amounts)
    before_first = text[: matches[0].start()].rstrip()
    after_first = text[matches[0].end() :]

    if _CEILING_BEFORE_FIGURE.search(before_first):
        return _Figures(minimum=None, maximum=highest, confidence=SalaryConfidence.PARSED)
    if len(amounts) > 1:
        return _Figures(minimum=first, maximum=highest, confidence=SalaryConfidence.PARSED)
    if _UNFINISHED_RANGE.match(after_first):
        return _Figures(minimum=first, maximum=None, confidence=SalaryConfidence.LOW)
    return _Figures(minimum=first, maximum=first, confidence=SalaryConfidence.EXACT)


def _is_plausible(amount: Decimal) -> bool:
    """Whether a figure could be a salary. A typo such as ``£47.39`` could not."""
    return MIN_PLAUSIBLE_SALARY <= amount <= MAX_PLAUSIBLE_SALARY


def detect_period(text: str) -> SalaryPeriod:
    """Return the period the figures cover, or ``UNKNOWN`` when the advert does not say."""
    lowered = text.casefold()
    for period, pattern in _PERIOD_PATTERNS.items():
        if pattern.search(lowered):
            return period
    return SalaryPeriod.UNKNOWN


def extract_grade(text: str) -> str | None:
    """Return the grade or band as written, for example ``Grade 7``, ``Band 6`` or ``UE07``.

    Kept exactly as written, so a person can compare it with the advert.
    """
    match = _GRADE.search(text or "")
    return _WHITESPACE.sub(" ", match.group(0)).strip() if match else None


@dataclass(frozen=True, slots=True)
class Thresholds:
    """The figures a verdict is calculated against.

    Built from a :class:`screening.models.Ruleset` row. Never from fixed numbers outside tests.
    """

    personal_floor: Decimal
    current_package: Decimal
    going_rate: Decimal
    standard_general: Decimal
    transitional_general: Decimal
    going_rate_key: str = "soc_2134_going_rate"


@dataclass(frozen=True, slots=True)
class ThresholdAssessment:
    """A threshold verdict plus the reasoning that produced it."""

    verdict: ThresholdVerdict
    screened_on: Decimal | None
    general_threshold_met: bool | None
    going_rate_met: bool | None
    going_rate_key: str
    explanation: str


def evaluate_threshold(salary: ParsedSalary, thresholds: Thresholds) -> ThresholdAssessment:
    """Place the bottom of the advertised range in a band of the ruleset.

    Each band includes its lower edge: exactly ``personal_floor`` is ``PAY_CUT``, and exactly
    ``going_rate`` is ``TARGET_BAND``.
    """
    floor = salary.minimum
    if not salary.is_screenable or floor is None:
        return ThresholdAssessment(
            verdict=ThresholdVerdict.SALARY_UNCLEAR,
            screened_on=None,
            general_threshold_met=None,
            going_rate_met=None,
            going_rate_key=thresholds.going_rate_key,
            explanation=_unclear_reason(salary),
        )

    verdict, reason = _band_for(floor, thresholds)
    return ThresholdAssessment(
        verdict=verdict,
        screened_on=floor,
        general_threshold_met=floor >= thresholds.standard_general,
        going_rate_met=floor >= thresholds.going_rate,
        going_rate_key=thresholds.going_rate_key,
        explanation=f"Screened on the bottom of the range. {reason}",
    )


def _band_for(floor: Decimal, thresholds: Thresholds) -> tuple[ThresholdVerdict, str]:
    """Return the band the floor falls in, and a sentence naming the figure that decided it."""
    offered = _money(floor)
    going_rate = f"{thresholds.going_rate_key} going rate of {_money(thresholds.going_rate)}"

    if floor < thresholds.personal_floor:
        return (
            ThresholdVerdict.EXCLUDED_BELOW_FLOOR,
            f"{offered} is below the personal floor of {_money(thresholds.personal_floor)}.",
        )
    if floor < thresholds.current_package:
        return (
            ThresholdVerdict.PAY_CUT,
            f"{offered} is below the current package of {_money(thresholds.current_package)}.",
        )
    if floor < thresholds.going_rate:
        return (
            ThresholdVerdict.LATERAL_CONTINGENT,
            f"{offered} matches or beats the current package but is below the {going_rate}.",
        )
    return ThresholdVerdict.TARGET_BAND, f"{offered} meets the {going_rate}."


def _unclear_reason(salary: ParsedSalary) -> str:
    """Explain, in the advert's own terms, why no band could be assigned."""
    if salary.confidence is SalaryConfidence.UNPARSEABLE:
        return f"Salary could not be parsed from {salary.raw!r}."
    if salary.minimum is None:
        return (
            f"{salary.raw!r} states a ceiling but no floor. A ceiling is not screened: the "
            "advertised start salary is what matters."
        )
    return (
        f"{salary.raw!r} is quoted {salary.period.label.lower()}, not per annum. Annualising it "
        "would mean guessing at contracted hours."
    )


def _money(amount: Decimal) -> str:
    """Format a figure the way the adverts do: ``£54,700``."""
    return f"£{amount:,.0f}"


CRITERION_WEIGHTS: Final[dict[str, int]] = {
    "skills": 3,
    "domains": 2,
    "seniority": 2,
    "years": 2,
    "projects": 1,
    "education": 1,
}

_YEARS_REQUIRED = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:or\s+more\s+)?year[s]?(?:\s+of)?(?:\s+\w+){0,3}\s*"
    r"(?:experience|track record)?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CandidateCriteria:
    """The candidate profile, flattened into the terms fitness is scored on."""

    skills: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    seniority: tuple[str, ...] = ()
    projects: tuple[str, ...] = ()
    education: tuple[str, ...] = ()
    years_experience: int = 0


@dataclass(frozen=True, slots=True)
class CriterionResult:
    """How one weighted criterion scored, and what was missing."""

    criterion: str
    weight: int
    fraction: float
    matched: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True, slots=True)
class FitnessResult:
    """A 0-100 score and the reasons for it.

    The reasons matter most. The gaps they show are what a cover letter should address.
    """

    score: int
    reasons: tuple[CriterionResult, ...] = field(default_factory=tuple)


def _term_present(term: str, haystack: str) -> bool:
    """Whether ``term`` appears in ``haystack`` as a whole word or phrase."""
    pattern = r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)"
    return re.search(pattern, haystack) is not None


def _score_terms(criterion: str, terms: tuple[str, ...], haystack: str) -> CriterionResult:
    """Score one term-list criterion as the fraction of its terms present in the advert."""
    weight = CRITERION_WEIGHTS[criterion]
    if not terms:
        return CriterionResult(
            criterion=criterion,
            weight=weight,
            fraction=0.0,
            note="No terms configured on the candidate profile.",
        )
    matched = tuple(term for term in terms if _term_present(term, haystack))
    missing = tuple(term for term in terms if term not in matched)
    return CriterionResult(
        criterion=criterion,
        weight=weight,
        fraction=len(matched) / len(terms),
        matched=matched,
        missing=missing,
    )


def required_years(text: str) -> int | None:
    """Return the largest "N years experience" figure in ``text``, or ``None``."""
    figures = [int(match.group(1)) for match in _YEARS_REQUIRED.finditer(text)]
    plausible = [figure for figure in figures if 1 <= figure <= 30]
    return max(plausible) if plausible else None


def score_fitness(job_text: str, criteria: CandidateCriteria) -> FitnessResult:
    """Score an advert against the candidate profile, from 0 to 100.

    This is separate from the sponsorship check on purpose. A good fit at an employer that cannot
    sponsor is still not a result, and fitness never changes a sponsor verdict.
    """
    haystack = (job_text or "").casefold()

    results = [
        _score_terms("skills", criteria.skills, haystack),
        _score_terms("domains", criteria.domains, haystack),
        _score_terms("seniority", criteria.seniority, haystack),
    ]

    demanded = required_years(job_text or "")
    if demanded is None:
        years = CriterionResult(
            criterion="years",
            weight=CRITERION_WEIGHTS["years"],
            fraction=1.0,
            note="Advert states no minimum years of experience.",
        )
    elif criteria.years_experience >= demanded:
        years = CriterionResult(
            criterion="years",
            weight=CRITERION_WEIGHTS["years"],
            fraction=1.0,
            note=f"Advert asks for {demanded} years; profile has {criteria.years_experience}.",
        )
    else:
        years = CriterionResult(
            criterion="years",
            weight=CRITERION_WEIGHTS["years"],
            fraction=0.0,
            missing=(f"{demanded} years experience",),
            note=f"Advert asks for {demanded} years; profile has {criteria.years_experience}.",
        )
    results.append(years)

    results.append(_score_terms("projects", criteria.projects, haystack))
    results.append(_score_terms("education", criteria.education, haystack))

    total_weight = sum(result.weight for result in results)
    earned = sum(result.weight * result.fraction for result in results)
    score = round(100 * earned / total_weight) if total_weight else 0

    return FitnessResult(score=score, reasons=tuple(results))
