"""Job and application enumerations."""

from __future__ import annotations

from shared.enums import LabelledEnum


class JobStatus(LabelledEnum):
    """The states of a vacancy.

    ``DISAPPEARED``: the advert was missing from a crawl whose outcome was ``OK``. It is only set
    by such a crawl. ``WITHDRAWN``: a person took the job down, with a reason. Two words, so the
    crawler's rule always means one thing.
    """

    OPEN = "OPEN", "Open"
    DISAPPEARED = "DISAPPEARED", "No longer listed"
    CLOSED = "CLOSED", "Closed"
    WITHDRAWN = "WITHDRAWN", "Withdrawn by an administrator"


class JobSource(LabelledEnum):
    """Where the record came from.

    When removing duplicates, the employer's own site wins over an aggregator.
    """

    PORTAL = "PORTAL", "Employer portal"
    AGGREGATOR = "AGGREGATOR", "Aggregator"
    MANUAL = "MANUAL", "Added by hand"


class ContractType(LabelledEnum):
    """Contract shape as advertised."""

    PERMANENT = "PERMANENT", "Permanent"
    FIXED_TERM = "FIXED_TERM", "Fixed term"
    CASUAL = "CASUAL", "Casual"
    SECONDMENT = "SECONDMENT", "Secondment"
    UNKNOWN = "UNKNOWN", "Unstated"


class Hours(LabelledEnum):
    """Full time, part time, or the advert did not say."""

    FULL_TIME = "FULL_TIME", "Full time"
    PART_TIME = "PART_TIME", "Part time"
    UNKNOWN = "UNKNOWN", "Unstated"


class Workplace(LabelledEnum):
    """On-site, hybrid or remote."""

    ON_SITE = "ON_SITE", "On site"
    HYBRID = "HYBRID", "Hybrid"
    REMOTE = "REMOTE", "Remote"
    UNKNOWN = "UNKNOWN", "Unstated"


class ApplicationStatus(LabelledEnum):
    """Columns of the pipeline board, in order."""

    FOUND = "FOUND", "Found"
    READY = "READY", "Ready"
    APPLIED = "APPLIED", "Applied"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
    INTERVIEW = "INTERVIEW", "Interview"
    OFFER = "OFFER", "Offer"
    REJECTED = "REJECTED", "Rejected"
    GHOSTED = "GHOSTED", "Ghosted"


APPLICATION_PIPELINE: tuple[ApplicationStatus, ...] = (
    ApplicationStatus.FOUND,
    ApplicationStatus.READY,
    ApplicationStatus.APPLIED,
    ApplicationStatus.ACKNOWLEDGED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.GHOSTED,
)

GHOSTED_AFTER_DAYS = 21


class Discipline(LabelledEnum):
    """The jobs.ac.uk subject list: what field a vacancy is *in*.

    Not the same as ``category``, the platform's own free-text label. This is worked out from
    that label, the title and the department (see :func:`jobs.domain.classify_discipline`).
    ``OTHER`` is a real answer. Forty terms will never fit every vacancy.
    """

    AGRICULTURE_FOOD_VETERINARY = "AGRICULTURE_FOOD_VETERINARY", "Agriculture, Food & Veterinary"
    ARCHITECTURE_BUILDING_PLANNING = (
        "ARCHITECTURE_BUILDING_PLANNING",
        "Architecture, Building & Planning",
    )
    BIOLOGICAL_SCIENCES = "BIOLOGICAL_SCIENCES", "Biological Sciences"
    BUSINESS_MANAGEMENT_STUDIES = "BUSINESS_MANAGEMENT_STUDIES", "Business & Management Studies"
    COMPUTER_SCIENCES = "COMPUTER_SCIENCES", "Computer Sciences"
    CREATIVE_ARTS_DESIGN = "CREATIVE_ARTS_DESIGN", "Creative Arts & Design"
    ECONOMICS = "ECONOMICS", "Economics"
    EDUCATION_STUDIES = "EDUCATION_STUDIES", "Education Studies"
    ENGINEERING_TECHNOLOGY = "ENGINEERING_TECHNOLOGY", "Engineering & Technology"
    HEALTH_MEDICAL = "HEALTH_MEDICAL", "Health & Medical"
    HISTORICAL_PHILOSOPHICAL_STUDIES = (
        "HISTORICAL_PHILOSOPHICAL_STUDIES",
        "Historical & Philosophical Studies",
    )
    INFORMATION_MANAGEMENT_LIBRARIANSHIP = (
        "INFORMATION_MANAGEMENT_LIBRARIANSHIP",
        "Information Management & Librarianship",
    )
    LANGUAGES_LITERATURE_CULTURE = (
        "LANGUAGES_LITERATURE_CULTURE",
        "Languages, Literature & Culture",
    )
    LAW = "LAW", "Law"
    MATHEMATICS_STATISTICS = "MATHEMATICS_STATISTICS", "Mathematics & Statistics"
    MEDIA_COMMUNICATIONS = "MEDIA_COMMUNICATIONS", "Media & Communications"
    PHYSICAL_ENVIRONMENTAL_SCIENCES = (
        "PHYSICAL_ENVIRONMENTAL_SCIENCES",
        "Physical & Environmental Sciences",
    )
    POLITICS_GOVERNMENT = "POLITICS_GOVERNMENT", "Politics & Government"
    PSYCHOLOGY = "PSYCHOLOGY", "Psychology"
    SOCIAL_SCIENCES_SOCIAL_CARE = "SOCIAL_SCIENCES_SOCIAL_CARE", "Social Sciences & Social Care"

    ADMINISTRATIVE = "ADMINISTRATIVE", "Administrative"
    ESTATES_FACILITIES_MANAGEMENT = (
        "ESTATES_FACILITIES_MANAGEMENT",
        "Estates & Facilities Management",
    )
    FINANCE_PROCUREMENT = "FINANCE_PROCUREMENT", "Finance & Procurement"
    FUNDRAISING_ALUMNI_BIDS_GRANTS = (
        "FUNDRAISING_ALUMNI_BIDS_GRANTS",
        "Fundraising, Alumni, Bids & Grants",
    )
    HEALTH_WELLBEING_CARE = "HEALTH_WELLBEING_CARE", "Health, Wellbeing & Care"
    HOSPITALITY_RETAIL_EVENTS = (
        "HOSPITALITY_RETAIL_EVENTS",
        "Hospitality, Retail, Conferences & Events",
    )
    HUMAN_RESOURCES = "HUMAN_RESOURCES", "Human Resources"
    INTERNATIONAL_ACTIVITIES = "INTERNATIONAL_ACTIVITIES", "International Activities"
    IT_SERVICES = "IT_SERVICES", "IT Services"
    LABORATORY_CLINICAL_TECHNICIAN = (
        "LABORATORY_CLINICAL_TECHNICIAN",
        "Laboratory, Clinical & Technician",
    )
    LEGAL_COMPLIANCE_POLICY = "LEGAL_COMPLIANCE_POLICY", "Legal, Compliance & Policy"
    LIBRARY_SERVICES_DATA_INFORMATION = (
        "LIBRARY_SERVICES_DATA_INFORMATION",
        "Library Services, Data & Information Management",
    )
    PR_MARKETING_SALES_COMMUNICATION = (
        "PR_MARKETING_SALES_COMMUNICATION",
        "PR, Marketing, Sales & Communication",
    )
    PROJECT_MANAGEMENT_CONSULTING = (
        "PROJECT_MANAGEMENT_CONSULTING",
        "Project Management & Consulting",
    )
    SENIOR_MANAGEMENT = "SENIOR_MANAGEMENT", "Senior Management"
    STUDENT_SERVICES = "STUDENT_SERVICES", "Student Services"
    SUSTAINABILITY = "SUSTAINABILITY", "Sustainability"
    WEB_DESIGN_DEVELOPMENT = "WEB_DESIGN_DEVELOPMENT", "Web Design & Development"

    SPORT_LEISURE = "SPORT_LEISURE", "Sport & Leisure"
    STUDENTSHIPS_PHDS = "STUDENTSHIPS_PHDS", "Studentships & PhDs"

    OTHER = "OTHER", "Other"


class ChangeField(LabelledEnum):
    """Fields whose change between runs is worth recording on a revision."""

    TITLE = "title", "Title"
    SALARY_RAW = "salary_raw", "Salary"
    CLOSING_DATE = "closing_date", "Closing date"
    DESCRIPTION = "description_text", "Description"
    LOCATION_RAW = "location_raw", "Location"
    STATUS = "status", "Status"


JOB_STATUS_CHOICES = JobStatus.choices()
JOB_SOURCE_CHOICES = JobSource.choices()
CONTRACT_TYPE_CHOICES = ContractType.choices()
HOURS_CHOICES = Hours.choices()
WORKPLACE_CHOICES = Workplace.choices()
APPLICATION_STATUS_CHOICES = ApplicationStatus.choices()
CHANGE_FIELD_CHOICES = ChangeField.choices()
DISCIPLINE_CHOICES = Discipline.choices()
