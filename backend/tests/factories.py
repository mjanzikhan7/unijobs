"""factory_boy factories.

``JobFactory(salary_raw="£38,784 to £46,049")`` reads better than three chained fixtures and
says exactly what the test is about.
"""

from __future__ import annotations

from datetime import timedelta

import factory
from django.contrib.auth.models import User
from django.utils import timezone

from crawler.enums import CrawlOutcome, CrawlRunStatus, CrawlTrigger, ExtractionStrategy
from crawler.models import CrawlRun, CrawlRunInstitution
from institutions.enums import InstitutionType, Nation, Platform
from institutions.models import Institution
from jobs.enums import ApplicationStatus, JobSource, JobStatus
from jobs.models import Application, Job, SavedJob, SavedSearch
from screening.enums import (
    MatchMethod,
    SalaryConfidence,
    SalaryPeriod,
    SponsorVerdict,
    ThresholdVerdict,
)
from screening.models import (
    CandidateProfile,
    InstitutionSponsorMatch,
    JobFitness,
    JobScreening,
    SponsorRegisterEntry,
    SponsorRegisterSnapshot,
)

DEFAULT_OWNER_USERNAME = "operator"


class UserFactory(factory.django.DjangoModelFactory):
    """A user to own the per-candidate rows."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.test")


class DefaultOwner(factory.SubFactory):
    """The shared default owner, reused rather than minted per row."""

    def __init__(self) -> None:
        """Point at the shared default account rather than minting a new one."""
        super().__init__(UserFactory, username=DEFAULT_OWNER_USERNAME)


class InstitutionFactory(factory.django.DjangoModelFactory):
    """A crawlable institution."""

    class Meta:
        model = Institution
        django_get_or_create = ("slug",)

    slug = factory.Sequence(lambda n: f"university-of-test-{n}")
    name = factory.Sequence(lambda n: f"University of Test {n}")
    nation = Nation.ENGLAND.value
    city = "Bath"
    institution_type = InstitutionType.UNIVERSITY.value
    careers_url = factory.LazyAttribute(lambda o: f"https://{o.slug}.ac.uk/jobs")
    platform = Platform.STONEFISH.value
    crawl_enabled = True


class SponsorMatchFactory(factory.django.DjangoModelFactory):
    """A resolved sponsor match."""

    class Meta:
        model = InstitutionSponsorMatch
        django_get_or_create = ("institution",)

    institution = factory.SubFactory(InstitutionFactory)
    registered_legal_name = factory.LazyAttribute(lambda o: f"The {o.institution.name}")
    verdict = SponsorVerdict.CONFIRMED.value
    method = MatchMethod.SEED.value
    confidence = 1.0
    needs_review = False


class SnapshotFactory(factory.django.DjangoModelFactory):
    """A sponsor-register download."""

    class Meta:
        model = SponsorRegisterSnapshot

    source_url = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
    row_count = 0


class RegisterEntryFactory(factory.django.DjangoModelFactory):
    """One row of the sponsor register."""

    class Meta:
        model = SponsorRegisterEntry

    snapshot = factory.SubFactory(SnapshotFactory)
    organisation_name = "The University of Cambridge"
    normalised_name = "university of cambridge"
    town_city = "Cambridge"
    type_rating = "Worker (A rating)"
    route = "Skilled Worker"


class JobFactory(factory.django.DjangoModelFactory):
    """A vacancy."""

    class Meta:
        model = Job

    institution = factory.SubFactory(InstitutionFactory)
    source = JobSource.PORTAL.value
    source_url = factory.Sequence(lambda n: f"https://jobs.example.ac.uk/vacancy/{n}")
    title = factory.Sequence(lambda n: f"Research Software Engineer {n}")
    department = "Department of Computer Science"
    description_html = "<p>An excellent opportunity.</p>"
    description_text = "An excellent opportunity."
    location_raw = "Bath, Somerset"
    city = "Bath"
    salary_raw = "£38,784 to £46,049 per annum"
    posted_date = factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=3))
    closing_date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=21))
    status = JobStatus.OPEN.value
    content_hash = factory.Sequence(lambda n: f"hash-{n}")


class ScreeningFactory(factory.django.DjangoModelFactory):
    """A verdict row. Every job needs one before it can be rendered."""

    class Meta:
        model = JobScreening
        django_get_or_create = ("job",)

    job = factory.SubFactory(JobFactory)
    sponsor_verdict = SponsorVerdict.CONFIRMED.value
    sponsor_matched_name = "The University of Test"
    sponsor_confidence = 1.0
    salary_min = 38784
    salary_max = 46049
    salary_period = SalaryPeriod.ANNUAL.value
    salary_confidence = SalaryConfidence.PARSED.value
    threshold_verdict = ThresholdVerdict.PAY_CUT.value
    threshold_explanation = "Screened on the bottom of the range."
    screened_on = 38784
    general_threshold_met = False
    going_rate_met = False
    going_rate_key = "soc_2134_going_rate"


class JobFitnessFactory(factory.django.DjangoModelFactory):
    """One candidate's score against one job."""

    class Meta:
        model = JobFitness
        django_get_or_create = ("owner", "job")

    owner = DefaultOwner()
    job = factory.SubFactory(JobFactory)
    score = 65
    reasons: list[dict[str, object]] = []


class SavedJobFactory(factory.django.DjangoModelFactory):
    """A saved job."""

    class Meta:
        model = SavedJob

    owner = DefaultOwner()
    job = factory.SubFactory(JobFactory)
    tags: list[str] = []


class ApplicationFactory(factory.django.DjangoModelFactory):
    """A tracked application."""

    class Meta:
        model = Application

    owner = DefaultOwner()
    job = factory.SubFactory(JobFactory)
    status = ApplicationStatus.FOUND.value


class SavedSearchFactory(factory.django.DjangoModelFactory):
    """A named filter set."""

    class Meta:
        model = SavedSearch

    owner = DefaultOwner()
    name = factory.Sequence(lambda n: f"Saved search {n}")
    query = "sponsorable=true&min_fitness=60"
    digest_enabled = True


class CandidateProfileFactory(factory.django.DjangoModelFactory):
    """The profile fitness is scored against."""

    class Meta:
        model = CandidateProfile

    owner = DefaultOwner()
    name = "Test profile"
    skills = ["python", "django", "postgres"]
    domains = ["higher education", "research software"]
    seniority = ["senior"]
    projects = ["data pipeline"]
    education = ["msc"]
    years_experience = 8
    is_active = True


class CrawlRunFactory(factory.django.DjangoModelFactory):
    """A crawl run."""

    class Meta:
        model = CrawlRun

    trigger = CrawlTrigger.MANUAL.value
    status = CrawlRunStatus.RUNNING.value
    started_at = factory.LazyFunction(timezone.now)


class CrawlRunInstitutionFactory(factory.django.DjangoModelFactory):
    """One institution's outcome within a run."""

    class Meta:
        model = CrawlRunInstitution

    run = factory.SubFactory(CrawlRunFactory)
    institution = factory.SubFactory(InstitutionFactory)
    adapter = "StonefishAdapter"
    outcome = CrawlOutcome.OK.value
    strategy = ExtractionStrategy.HTML.value
    vacancies_found = 40
