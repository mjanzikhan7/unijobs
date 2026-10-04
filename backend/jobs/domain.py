"""Pure job rules: ghosting, closing soon, and tidying advert details.

No Django, no I/O, no clock. The current time is always an argument.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Final

from jobs.enums import (
    GHOSTED_AFTER_DAYS,
    ApplicationStatus,
    ContractType,
    Discipline,
    Hours,
    Workplace,
)


def looks_ghosted(
    *,
    status: str,
    applied_at: datetime | None,
    response_at: datetime | None,
    now: datetime,
    window_days: int = GHOSTED_AFTER_DAYS,
) -> bool:
    """Whether an application has been quiet for longer than the ghosting window.

    Only a flag. Moving the card to ``GHOSTED`` automatically would overrule the candidate, and
    some employers do reply after five weeks.
    """
    if status != ApplicationStatus.APPLIED or applied_at is None or response_at is not None:
        return False
    return applied_at <= now - timedelta(days=window_days)


def closes_within(closing_date: date | None, *, today: date, days: int) -> bool:
    """Whether ``closing_date`` falls inside the next ``days`` days, today included."""
    if closing_date is None:
        return False
    return today <= closing_date <= today + timedelta(days=days)


_CONTRACT_PATTERNS: Final[tuple[tuple[re.Pattern[str], ContractType], ...]] = (
    (
        re.compile(r"\bfixed[\s-]?term\b|\bftc\b|\btemporary\b|\bmaternity cover\b"),
        ContractType.FIXED_TERM,
    ),
    (re.compile(r"\bsecondment\b"), ContractType.SECONDMENT),
    (re.compile(r"\bcasual\b|\bzero[\s-]?hours\b|\bbank\b"), ContractType.CASUAL),
    (re.compile(r"\bpermanent\b|\bopen[\s-]?ended\b|\bindefinite\b"), ContractType.PERMANENT),
)

_HOURS_PATTERNS: Final[tuple[tuple[re.Pattern[str], Hours], ...]] = (
    (re.compile(r"\bpart[\s-]?time\b|\bpro[\s-]?rata\b|\b0\.\d\s*fte\b"), Hours.PART_TIME),
    (re.compile(r"\bfull[\s-]?time\b|\b1\.0\s*fte\b"), Hours.FULL_TIME),
)

_WORKPLACE_PATTERNS: Final[tuple[tuple[re.Pattern[str], Workplace], ...]] = (
    (re.compile(r"\bfully remote\b|\bremote[\s-]?first\b|\b100% remote\b"), Workplace.REMOTE),
    (re.compile(r"\bhybrid\b|\bblended working\b"), Workplace.HYBRID),
    (re.compile(r"\bon[\s-]?site\b|\bcampus[\s-]?based\b"), Workplace.ON_SITE),
)


def classify_contract_type(text: str) -> ContractType:
    """Read the contract type from an advert, or return ``UNKNOWN``.

    Fixed term is checked before permanent. Adverts often say "permanent contract, fixed term until
    2028", and for a visa the fixed term is what matters.
    """
    return _first_match(text, _CONTRACT_PATTERNS, ContractType.UNKNOWN)


def classify_hours(text: str) -> Hours:
    """Read full/part time out of an advert, defaulting to ``UNKNOWN``."""
    return _first_match(text, _HOURS_PATTERNS, Hours.UNKNOWN)


def classify_workplace(text: str) -> Workplace:
    """Read on-site/hybrid/remote out of an advert, defaulting to ``UNKNOWN``."""
    return _first_match(text, _WORKPLACE_PATTERNS, Workplace.UNKNOWN)


def _first_match[T](text: str, patterns: tuple[tuple[re.Pattern[str], T], ...], default: T) -> T:
    """Return the value of the first pattern that matches ``text``."""
    lowered = (text or "").casefold()
    for pattern, value in patterns:
        if pattern.search(lowered):
            return value
    return default


_DISCIPLINE_KEYWORDS: Final[tuple[tuple[Discipline, tuple[str, ...]], ...]] = (
    (
        Discipline.STUDENTSHIPS_PHDS,
        (r"\bphd\b", r"\bstudentship\b", r"\bdoctoral\b", r"\bdphil\b"),
    ),
    (
        Discipline.SENIOR_MANAGEMENT,
        (
            r"\bvice[\s-]?chancellor\b",
            r"\bpro[\s-]?vice[\s-]?chancellor\b",
            r"\bdean\b",
            r"\bdirector\b",
            r"\bhead of\b",
            r"\bchief (executive|operating|financial) officer\b",
            r"\bregistrar\b",
        ),
    ),
    (
        Discipline.HUMAN_RESOURCES,
        (
            r"\bhuman resources\b",
            r"\bhr (advisor|adviser|officer|manager|business partner)\b",
            r"\brecruitment (advisor|adviser|officer|manager)\b",
            r"\bpeople (and culture|partner)\b",
        ),
    ),
    (
        Discipline.FINANCE_PROCUREMENT,
        (
            r"\bfinance (officer|manager|assistant|analyst|business partner)\b",
            r"\baccountant\b",
            r"\bprocurement\b",
            r"\bpayroll\b",
            r"\btreasury\b",
            r"\bmanagement accountant\b",
        ),
    ),
    (
        Discipline.LEGAL_COMPLIANCE_POLICY,
        (
            r"\blegal counsel\b",
            r"\bsolicitor\b",
            r"\bcompliance officer\b",
            r"\bpolicy (officer|adviser|advisor)\b",
            r"\bdata protection officer\b",
            r"\bgovernance officer\b",
        ),
    ),
    (
        Discipline.ESTATES_FACILITIES_MANAGEMENT,
        (
            r"\bestates\b",
            r"\bfacilities\b",
            r"\bmaintenance (technician|engineer|officer)\b",
            r"\bgrounds\w* (person|staff|team)\b",
            r"\bcaretaker\b",
            r"\bcleaning\b",
            r"\bsecurity officer\b",
            r"\bporter\b",
        ),
    ),
    (
        Discipline.IT_SERVICES,
        (
            r"\bit (support|services|technician|manager)\b",
            r"\bnetwork engineer\b",
            r"\bsystems administrator\b",
            r"\bdesktop support\b",
            r"\bcyber ?security\b",
            r"\binfrastructure engineer\b",
            r"\bservice desk\b",
        ),
    ),
    (
        Discipline.WEB_DESIGN_DEVELOPMENT,
        (
            r"\bweb developer\b",
            r"\bfront[\s-]?end developer\b",
            r"\bback[\s-]?end developer\b",
            r"\bfull[\s-]?stack developer\b",
            r"\bux designer\b",
            r"\bui designer\b",
            r"\bsoftware engineer\b",
            r"\bwebmaster\b",
        ),
    ),
    (
        Discipline.LIBRARY_SERVICES_DATA_INFORMATION,
        (
            r"\blibrarian\b",
            r"\blibrary\b",
            r"\barchivist\b",
            r"\brecords manager\b",
            r"\bdata (analyst|steward|manager)\b",
            r"\binformation (governance|management) officer\b",
        ),
    ),
    (
        Discipline.PR_MARKETING_SALES_COMMUNICATION,
        (
            r"\bmarketing\b",
            r"\bcommunications officer\b",
            r"\bpublic relations\b",
            r"\bpress officer\b",
            r"\bsocial media\b",
            r"\bbrand manager\b",
            r"\bsales (executive|manager)\b",
        ),
    ),
    (
        Discipline.FUNDRAISING_ALUMNI_BIDS_GRANTS,
        (
            r"\bfundraising\b",
            r"\balumni relations\b",
            r"\bdevelopment officer\b",
            r"\bbid writer\b",
            r"\bgrants (officer|manager)\b",
            r"\bphilanthropy\b",
        ),
    ),
    (
        Discipline.PROJECT_MANAGEMENT_CONSULTING,
        (
            r"\bproject manager\b",
            r"\bprogramme manager\b",
            r"\bproject (officer|coordinator)\b",
            r"\bbusiness analyst\b",
            r"\bconsultant\b",
            r"\bscrum master\b",
        ),
    ),
    (
        Discipline.STUDENT_SERVICES,
        (
            r"\bstudent (services|support|experience|welfare|recruitment|advisor|adviser)\b",
            r"\badmissions (officer|tutor)\b",
            r"\bwidening participation\b",
            r"\bcareers adviser\b",
        ),
    ),
    (
        Discipline.INTERNATIONAL_ACTIVITIES,
        (
            r"\binternational (office|officer|recruitment|partnerships)\b",
            r"\bstudy abroad\b",
            r"\bglobal engagement\b",
            r"\berasmus\b",
        ),
    ),
    (
        Discipline.HEALTH_WELLBEING_CARE,
        (
            r"\bcounsellor\b",
            r"\bwellbeing (adviser|advisor|officer)\b",
            r"\boccupational health\b",
            r"\bmental health (adviser|advisor|practitioner)\b",
            r"\bdisability adviser\b",
        ),
    ),
    (
        Discipline.HOSPITALITY_RETAIL_EVENTS,
        (
            r"\bcatering\b",
            r"\bhospitality\b",
            r"\bconferences? (and events|manager|coordinator)\b",
            r"\bretail (assistant|manager)\b",
            r"\bevents (officer|manager|coordinator)\b",
            r"\bchef\b",
            r"\bbar (staff|supervisor)\b",
        ),
    ),
    (
        Discipline.LABORATORY_CLINICAL_TECHNICIAN,
        (
            r"\blaboratory technician\b",
            r"\blab technician\b",
            r"\bclinical (technician|scientist)\b",
            r"\btechnician\b",
        ),
    ),
    (
        Discipline.SUSTAINABILITY,
        (r"\bsustainability\b", r"\bcarbon (reduction|management)\b", r"\bnet zero\b"),
    ),
    (
        Discipline.ADMINISTRATIVE,
        (
            r"\badministrator\b",
            r"\badministrative (assistant|officer|support)\b",
            r"\boffice manager\b",
            r"\bpersonal assistant\b",
            r"\bexecutive assistant\b",
            r"\breceptionist\b",
            r"\bsecretary\b",
        ),
    ),
    (
        Discipline.AGRICULTURE_FOOD_VETERINARY,
        (
            r"\bagricultur\w*\b",
            r"\bveterinary\b",
            r"\bfood science\b",
            r"\banimal science\b",
            r"\bforestry\b",
            r"\bequine\b",
        ),
    ),
    (
        Discipline.ARCHITECTURE_BUILDING_PLANNING,
        (
            r"\barchitectur\w*\b",
            r"\burban planning\b",
            r"\bbuilt environment\b",
            r"\bsurveying\b",
            r"\bconstruction management\b",
            r"\btown planning\b",
        ),
    ),
    (
        Discipline.BIOLOGICAL_SCIENCES,
        (
            r"\bbiolog\w*\b",
            r"\bbiomedical\b",
            r"\bgenetics\b",
            r"\bmicrobiology\b",
            r"\bzoology\b",
            r"\bbotany\b",
            r"\becology\b",
            r"\bbiochemistry\b",
            r"\bimmunology\b",
            r"\bneuroscience\b",
            r"\bmolecular biology\b",
        ),
    ),
    (
        Discipline.BUSINESS_MANAGEMENT_STUDIES,
        (
            r"\bbusiness school\b",
            r"\bmanagement studies\b",
            r"\bmba\b",
            r"\baccounting and finance\b",
            r"\bhuman resource management\b",
            r"\bbusiness (lecturer|professor)\b",
            r"\bmarketing lecturer\b",
        ),
    ),
    (
        Discipline.COMPUTER_SCIENCES,
        (
            r"\bcomputer science\w*\b",
            r"\bcomputing\b",
            r"\bsoftware engineering\b",
            r"\bartificial intelligence\b",
            r"\bmachine learning\b",
            r"\bdata science\b",
            r"\binformatics\b",
        ),
    ),
    (
        Discipline.CREATIVE_ARTS_DESIGN,
        (
            r"\bfine art\b",
            r"\bcreative arts\b",
            r"\bgraphic design\b",
            r"\bfashion design\b",
            r"\bperforming arts\b",
            r"\bfilm and television\b",
            r"\bmusic (lecturer|professor)\b",
            r"\bdrama\b",
            r"\bphotography\b",
        ),
    ),
    (Discipline.ECONOMICS, (r"\beconomics\b", r"\beconometrics\b", r"\bfinancial economics\b")),
    (
        Discipline.EDUCATION_STUDIES,
        (
            r"\beducation studies\b",
            r"\bteacher training\b",
            r"\btefl\b",
            r"\bpgce\b",
            r"\beducational research\b",
            r"\bpedagogy\b",
        ),
    ),
    (
        Discipline.ENGINEERING_TECHNOLOGY,
        (
            r"\bengineering\b",
            r"\bmechanical engineer\w*\b",
            r"\belectrical engineer\w*\b",
            r"\bcivil engineer\w*\b",
            r"\baerospace\b",
            r"\brobotics\b",
            r"\bmechatronics\b",
        ),
    ),
    (
        Discipline.HEALTH_MEDICAL,
        (
            r"\bmedicine\b",
            r"\bmedical school\b",
            r"\bnursing\b",
            r"\bpharmacy\b",
            r"\bdentistry\b",
            r"\bphysiotherapy\b",
            r"\bpublic health\b",
            r"\bepidemiology\b",
            r"\bclinical (lecturer|professor|research fellow)\b",
            r"\bhealthcare\b",
        ),
    ),
    (
        Discipline.HISTORICAL_PHILOSOPHICAL_STUDIES,
        (
            r"\bhistory\b",
            r"\bphilosophy\b",
            r"\barchaeology\b",
            r"\btheology\b",
            r"\bclassics\b",
            r"\breligious studies\b",
        ),
    ),
    (
        Discipline.INFORMATION_MANAGEMENT_LIBRARIANSHIP,
        (r"\blibrary and information\b", r"\binformation science\b", r"\barchive studies\b"),
    ),
    (
        Discipline.LANGUAGES_LITERATURE_CULTURE,
        (
            r"\bmodern languages\b",
            r"\benglish literature\b",
            r"\blinguistics\b",
            r"\btranslation studies\b",
            r"\bcultural studies\b",
            r"\bcreative writing\b",
        ),
    ),
    (
        Discipline.LAW,
        (
            r"\blaw school\b",
            r"\bllb\b",
            r"\bllm\b",
            r"\blegal studies\b",
            r"\bjurisprudence\b",
            r"\blaw (lecturer|professor)\b",
        ),
    ),
    (
        Discipline.MATHEMATICS_STATISTICS,
        (
            r"\bmathematics\b",
            r"\bstatistics\b",
            r"\bapplied mathematics\b",
            r"\bpure mathematics\b",
            r"\bbiostatistics\b",
            r"\boperational research\b",
        ),
    ),
    (
        Discipline.MEDIA_COMMUNICATIONS,
        (
            r"\bmedia studies\b",
            r"\bjournalism\b",
            r"\bcommunication studies\b",
            r"\bbroadcasting\b",
        ),
    ),
    (
        Discipline.PHYSICAL_ENVIRONMENTAL_SCIENCES,
        (
            r"\bphysics\b",
            r"\bchemistry\b",
            r"\bastronomy\b",
            r"\bastrophysics\b",
            r"\bgeology\b",
            r"\bgeography\b",
            r"\benvironmental science\w*\b",
            r"\bearth science\w*\b",
            r"\bclimate science\b",
            r"\boceanography\b",
            r"\bmaterials science\b",
        ),
    ),
    (
        Discipline.POLITICS_GOVERNMENT,
        (
            r"\bpolitics\b",
            r"\bpolitical science\b",
            r"\binternational relations\b",
            r"\bpublic policy\b",
            r"\bpublic administration\b",
        ),
    ),
    (
        Discipline.PSYCHOLOGY,
        (r"\bpsycholog\w*\b", r"\bcognitive science\b", r"\bbehavioural science\b"),
    ),
    (
        Discipline.SOCIAL_SCIENCES_SOCIAL_CARE,
        (
            r"\bsociology\b",
            r"\bsocial work\b",
            r"\bsocial policy\b",
            r"\bsocial science\w*\b",
            r"\banthropology\b",
            r"\bcriminology\b",
            r"\bsocial care\b",
        ),
    ),
    (
        Discipline.SPORT_LEISURE,
        (
            r"\bsport\w* science\b",
            r"\bsport\w* (studies|management|coaching)\b",
            r"\bexercise science\b",
            r"\bleisure management\b",
        ),
    ),
)

_DISCIPLINE_PATTERNS: Final[tuple[tuple[re.Pattern[str], Discipline], ...]] = tuple(
    (re.compile("|".join(fragments)), discipline) for discipline, fragments in _DISCIPLINE_KEYWORDS
)


def classify_discipline(title: str, category: str, department: str) -> Discipline:
    """Place a vacancy in the jobs.ac.uk subject list, or return ``OTHER``.

    The title is the strongest signal. The platform's category and the department help. The order
    of ``_DISCIPLINE_KEYWORDS`` is part of the rule (see the comment above it).
    """
    combined = " ".join(filter(None, [title, category, department]))
    return _first_match(combined, _DISCIPLINE_PATTERNS, Discipline.OTHER)
