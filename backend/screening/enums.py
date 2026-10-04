"""Screening enumerations.

Every verdict a job can have is one of these. :class:`SponsorVerdict` has no "unknown" value
apart from ``NOT_FOUND``. An empty verdict would look like "confirmed", which is the
dangerous direction to be wrong in.
"""

from __future__ import annotations

from shared.enums import LabelledEnum


class SponsorVerdict(LabelledEnum):
    """Whether the employer can sponsor a Skilled Worker visa."""

    CONFIRMED = "CONFIRMED", "Confirmed sponsor"
    B_RATED = "B_RATED", "B-rated sponsor"
    PROVISIONAL = "PROVISIONAL", "Provisional sponsor"
    CONFIRMED_VIA_PARENT = "CONFIRMED_VIA_PARENT", "Confirmed via parent entity"
    OTHER_ROUTE_ONLY = "OTHER_ROUTE_ONLY", "Licensed, but not for Skilled Worker"
    NOT_FOUND = "NOT_FOUND", "Not found on the register"


SPONSORING_VERDICTS: frozenset[SponsorVerdict] = frozenset(
    {
        SponsorVerdict.CONFIRMED,
        SponsorVerdict.B_RATED,
        SponsorVerdict.PROVISIONAL,
        SponsorVerdict.CONFIRMED_VIA_PARENT,
    }
)


class ThresholdVerdict(LabelledEnum):
    """Where the advertised floor sits against the candidate's own salary needs.

    This is separate from the legal thresholds, which are stored on the screening row as
    ``general_threshold_met`` and ``going_rate_met``.
    """

    EXCLUDED_BELOW_FLOOR = "EXCLUDED_BELOW_FLOOR", "Below personal floor"
    PAY_CUT = "PAY_CUT", "Pay cut"
    LATERAL_CONTINGENT = "LATERAL_CONTINGENT", "Lateral, contingent"
    TARGET_BAND = "TARGET_BAND", "Target band"
    SALARY_UNCLEAR = "SALARY_UNCLEAR", "Salary unclear"


class SalaryConfidence(LabelledEnum):
    """How much the parsed salary can be trusted."""

    EXACT = "EXACT", "Exact single figure"
    PARSED = "PARSED", "Range parsed cleanly"
    LOW = "LOW", "Parsed, but incomplete"
    UNPARSEABLE = "UNPARSEABLE", "Could not be parsed"


class SalaryPeriod(LabelledEnum):
    """The period the advertised figure covers.

    Anything except ``ANNUAL`` counts as unclear. Turning an hourly rate into a yearly one means
    guessing the hours, and a wrong guess could suggest a job that cannot be sponsored.
    """

    ANNUAL = "ANNUAL", "Per annum"
    MONTHLY = "MONTHLY", "Per month"
    WEEKLY = "WEEKLY", "Per week"
    DAILY = "DAILY", "Per day"
    HOURLY = "HOURLY", "Per hour"
    UNKNOWN = "UNKNOWN", "Unstated"


class RulesetFigureKey(LabelledEnum):
    """The figures a ruleset holds.

    The values are stored in the database with ``verified_at`` and a source URL, never in Python.
    """

    TRANSITIONAL_GENERAL_THRESHOLD = (
        "transitional_general_threshold",
        "Transitional general threshold",
    )
    STANDARD_GENERAL_THRESHOLD = "standard_general_threshold", "Standard general threshold"
    SOC_2134_GOING_RATE = "soc_2134_going_rate", "SOC 2134 - software developers"
    SOC_2139_GOING_RATE = "soc_2139_going_rate", "SOC 2139 - DevOps, IT consultants"
    SOC_2133_GOING_RATE = "soc_2133_going_rate", "SOC 2133 - BAs, architects, data engineers"
    SOC_2162_GOING_RATE = "soc_2162_going_rate", "SOC 2162 - researchers, RSE posts"
    SOC_3131_GOING_RATE = "soc_3131_going_rate", "SOC 3131 - RQF 3-5"
    SOC_3133_GOING_RATE = "soc_3133_going_rate", "SOC 3133 - RQF 3-5"
    CURRENT_PACKAGE = "current_package", "Current package"
    PERSONAL_FLOOR = "personal_floor", "Personal floor"


class MatchMethod(LabelledEnum):
    """How an institution was matched to a register entry. Drives the review queue."""

    EXACT = "EXACT", "Exact name match"
    NORMALISED = "NORMALISED", "Normalised name match"
    TRIGRAM = "TRIGRAM", "Trigram similarity"
    HUMAN = "HUMAN", "Chosen by a human"
    SEED = "SEED", "From the estate spreadsheet"
    NONE = "NONE", "No match"


class SkillTermKind(LabelledEnum):
    """Which criterion a vocabulary term feeds."""

    SKILL = "skill", "Skill"
    DOMAIN = "domain", "Domain"
    SENIORITY = "seniority", "Seniority"
    PROJECT = "project", "Project"
    EDUCATION = "education", "Education"


SPONSOR_VERDICT_CHOICES = SponsorVerdict.choices()
THRESHOLD_VERDICT_CHOICES = ThresholdVerdict.choices()
SALARY_CONFIDENCE_CHOICES = SalaryConfidence.choices()
SALARY_PERIOD_CHOICES = SalaryPeriod.choices()
RULESET_FIGURE_KEY_CHOICES = RulesetFigureKey.choices()
MATCH_METHOD_CHOICES = MatchMethod.choices()
SKILL_TERM_KIND_CHOICES = SkillTermKind.choices()
