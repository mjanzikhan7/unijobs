"""Enumerations of the institutions app.

They reach TypeScript through the generated OpenAPI schema. Add a value here and regenerate.
Never copy the list by hand in the frontend.
"""

from __future__ import annotations

from shared.enums import LabelledEnum


class Platform(LabelledEnum):
    """The recruitment system behind an institution's careers site.

    How each one is detected and handled is written on its adapter class.
    """

    STONEFISH = "STONEFISH", "Stonefish"
    JOBTRAIN = "JOBTRAIN", "Jobtrain"
    COREHR = "COREHR", "CoreHR"
    EPLOY = "EPLOY", "eploy"
    WORKDAY = "WORKDAY", "Workday"
    ITRENT = "ITRENT", "MHR iTrent (WebRecruitment)"
    HIRESERVE = "HIRESERVE", "Hireserve"
    SUCCESSFACTORS = "SUCCESSFACTORS", "SAP SuccessFactors"
    CAMBRIDGE_VIEWS_TABLE = "CAMBRIDGE_VIEWS_TABLE", "Cambridge careers table"
    COREHR_CATEGORISED = "COREHR_CATEGORISED", "CoreHR (categorised searches)"
    TALENTLINK = "TALENTLINK", "Talentlink (MrTed syndication)"
    AUB_VACANCY_CARDS = "AUB_VACANCY_CARDS", "AUB careers CMS cards"
    ORACLE_FUSION = "ORACLE_FUSION", "Oracle Fusion Cloud Recruiting"
    ENGAGE_ATS = "ENGAGE_ATS", "engage|ats (Havas People)"
    GENERIC_CARD_SCRAPE = "GENERIC_CARD_SCRAPE", "Generic plain-HTML card scrape"
    CHANGEWORKNOW = "CHANGEWORKNOW", "ChangeWorkNow / ISW"
    LUMINATE = "LUMINATE", "Luminate (Sitebuilder job widget)"
    RAILS_JOBS_BOARD = "RAILS_JOBS_BOARD", "Rails-based jobs board (results-list/job-result-item)"
    CONTENSIS_JOBS = "CONTENSIS_JOBS", "Contensis CMS jobs (window.REDUX_DATA)"
    LIPA_VACANCY_CARDS = "LIPA_VACANCY_CARDS", "LIPA careers CMS cards"
    NORWICH_VACANCY_CARDS = "NORWICH_VACANCY_CARDS", "Norwich UA careers CMS cards"
    TALEO = "TALEO", "Oracle Taleo"
    POSTINGPANDA = "POSTINGPANDA", "PostingPanda"
    LEEDS_ARTS_VACANCY_CARDS = "LEEDS_ARTS_VACANCY_CARDS", "Leeds Arts careers CMS cards"
    MHR_PEOPLE_FIRST = "MHR_PEOPLE_FIRST", "MHR People First HR"
    DUNDEE_VACANCY_CARDS = "DUNDEE_VACANCY_CARDS", "Dundee careers CMS cards (Drupal Views)"
    TRIBEPAD = "TRIBEPAD", "Tribepad Talent Acquisition Software"
    GUILDHALL_VACANCY_CARDS = "GUILDHALL_VACANCY_CARDS", "Guildhall careers CMS cards"
    RCM_VACANCY_CARDS = "RCM_VACANCY_CARDS", "Royal College of Music careers CMS cards"
    RNCM_VACANCY_CARDS = "RNCM_VACANCY_CARDS", "Royal Northern College of Music careers page"
    LIVERPOOL_HOPE_VACANCY_TABLES = (
        "LIVERPOOL_HOPE_VACANCY_TABLES",
        "Liverpool Hope careers category tables",
    )
    FUNNELBACK = "FUNNELBACK", "Funnelback (Squiz Cloud) search"
    HIREFUL_CMS = "HIREFUL_CMS", "Hireful CMS"
    WEBRECRUIT = "WEBRECRUIT", "Webrecruit"
    STRUCTURED = "STRUCTURED", "Structured data (JSON-LD or RSS)"
    UNKNOWN = "UNKNOWN", "Unknown"


class Nation(LabelledEnum):
    """UK nation. A search facet, and context when reading a salary."""

    ENGLAND = "ENGLAND", "England"
    SCOTLAND = "SCOTLAND", "Scotland"
    WALES = "WALES", "Wales"
    NORTHERN_IRELAND = "NORTHERN_IRELAND", "Northern Ireland"


class InstitutionType(LabelledEnum):
    """Broad category of institution, as recorded in the estate spreadsheet."""

    UNIVERSITY = "UNIVERSITY", "University"
    COLLEGE = "COLLEGE", "College"
    CONSERVATOIRE = "CONSERVATOIRE", "Conservatoire"
    RESEARCH_INSTITUTE = "RESEARCH_INSTITUTE", "Research institute"
    BUSINESS_SCHOOL = "BUSINESS_SCHOOL", "Business school"
    OTHER = "OTHER", "Other"


PLATFORM_CHOICES = Platform.choices()
NATION_CHOICES = Nation.choices()
INSTITUTION_TYPE_CHOICES = InstitutionType.choices()
