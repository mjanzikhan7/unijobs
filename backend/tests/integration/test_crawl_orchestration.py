"""Orchestration against a real database.

The unit tests show the differ closes nothing after a bad outcome. These show the orchestrator
really passes that through to the database, where the damage would happen.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from django.conf import settings as django_settings
from django.test import override_settings

from crawler.browser import FixtureBrowserSession
from crawler.enums import CrawlOutcome, CrawlRunStatus
from crawler.exceptions import Blocked, ParseError, RobotsDisallowed, SiteOffline, Timeout
from crawler.http import FixtureHttpClient
from crawler.models import CrawlRun, CrawlRunInstitution
from crawler.services import (
    RunAlreadyActive,
    crawl_institution,
    crawl_one,
    finalise_run,
    record_skipped_institution,
    start_run,
)
from crawler.types import FetchResponse, InstitutionRef, RawVacancy
from institutions.enums import Platform
from institutions.models import Institution
from jobs.enums import Discipline, JobSource, JobStatus
from jobs.models import Job, JobRevision
from tests.factories import CrawlRunFactory, InstitutionFactory, JobFactory

pytestmark = pytest.mark.django_db

CAREERS_URL = "https://jobs.test.ac.uk/jobs"


class StubAdapter:
    """An adapter that returns what a test tells it to, or raises.

    Not registered. It is passed in directly, so orchestration can be tested without a parser.
    """

    platform = Platform.STONEFISH
    strategy = Platform.STONEFISH
    fallback_fired = False

    def __init__(
        self, vacancies: list[RawVacancy] | None = None, error: Exception | None = None
    ) -> None:
        """Record what this adapter should return, or raise."""
        from crawler.enums import ExtractionStrategy

        self.vacancies = vacancies or []
        self.error = error
        self.strategy = ExtractionStrategy.HTML

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: object) -> bool:
        return True

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        if self.error is not None:
            raise self.error
        return list(self.vacancies)

    def fetch_detail(self, url: str) -> RawVacancy:  # pragma: no cover - not used here
        raise NotImplementedError


@pytest.fixture
def institution(db: None) -> Institution:
    """A crawlable institution pointing at the fixture URL."""
    return InstitutionFactory(slug="university-of-test", careers_url=CAREERS_URL)


@pytest.fixture
def run(db: None) -> CrawlRun:
    """A running crawl."""
    return CrawlRunFactory()


def vacancy(index: int, **overrides: Any) -> RawVacancy:
    """A vacancy with a stable URL per index."""
    defaults: dict[str, Any] = {
        "source_url": f"{CAREERS_URL}/vacancy/{index}",
        "title": f"Research Software Engineer {index}",
        "institution_slug": "university-of-test",
        "salary_raw": "£38,784 to £46,049 per annum",
        "closing_date": date(2026, 9, 30),
    }
    defaults.update(overrides)
    return RawVacancy(**defaults)


def crawl_with(
    run: CrawlRun,
    institution: Institution,
    monkeypatch: pytest.MonkeyPatch,
    *,
    vacancies: list[RawVacancy] | None = None,
    error: Exception | None = None,
) -> CrawlRunInstitution:
    """Crawl one institution with a stubbed adapter and a fixture HTTP client."""
    adapter = StubAdapter(vacancies=vacancies, error=error)
    monkeypatch.setattr("crawler.crawl.resolve_adapter", lambda *args, **kwargs: adapter)
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(
            url=CAREERS_URL,
            status_code=200,
            text="<html><body>Vacancies</body></html>",
            headers={"content-type": "text/html"},
        ),
    )
    return crawl_institution(run, institution, http=client)


@pytest.mark.parametrize(
    ("error", "expected_outcome"),
    [
        (RobotsDisallowed("disallowed"), CrawlOutcome.ROBOTS_DISALLOWED),
        (SiteOffline("offline"), CrawlOutcome.OFFLINE),
        (Blocked("blocked"), CrawlOutcome.BLOCKED),
        (Timeout("timed out"), CrawlOutcome.TIMEOUT),
        (ParseError("bad markup"), CrawlOutcome.PARSE_ERROR),
    ],
)
def test_a_typed_adapter_error_maps_to_its_outcome(
    error: Exception,
    expected_outcome: CrawlOutcome,
    run: CrawlRun,
    institution: Institution,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = crawl_with(run, institution, monkeypatch, error=error)

    assert result.outcome == expected_outcome


def test_a_maintenance_banner_does_not_block_a_page_with_real_content(
    run: CrawlRun, html_fixture: Any
) -> None:
    """Real Huddersfield case, at the orchestration level.

    The probe used to run its own maintenance check before any adapter was chosen, so this false
    alarm could not be fixed inside an adapter. Every adapter already runs the same check after it
    knows whether real content came back, so the probe's check was removed.
    """
    open_url = (
        "https://vacancies.hud.ac.uk/tlive_webrecruitment/wrd/run/etrec179gf.open?WVID=2486049XkB"
    )
    json_url = (
        "https://vacancies.hud.ac.uk/tlive_webrecruitment/wrd/run/ETREC106GF.json"
        "?WVID=2486049XkB&USESSION=D8D05292B462E63CE2DD2238EC47F03A&LANG=USA&RESULTS_PP=200"
    )
    institution = InstitutionFactory(slug="huddersfield", careers_url=open_url)
    client = FixtureHttpClient(
        responses={
            open_url: FetchResponse(
                url=open_url,
                status_code=200,
                text=html_fixture(
                    "itrent/huddersfield-search-with-maintenance-banner-2026-08-25.html"
                ),
                headers={"content-type": "text/html"},
            ),
            json_url: FetchResponse(
                url=json_url,
                status_code=200,
                text=html_fixture("itrent/napier-results-2026-08-24.json"),
                headers={"content-type": "application/json"},
            ),
        }
    )

    result = crawl_institution(run, institution, http=client)

    assert result.outcome == CrawlOutcome.OK
    assert result.vacancies_found == 6


@pytest.mark.parametrize(
    "error",
    [
        RobotsDisallowed("disallowed"),
        SiteOffline("offline"),
        Blocked("blocked"),
        Timeout("timed out"),
        ParseError("bad markup"),
    ],
)
def test_no_job_is_closed_when_a_crawl_fails(
    error: Exception,
    run: CrawlRun,
    institution: Institution,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If one integration test survives in this project, it is this one."""
    JobFactory.create_batch(3, institution=institution)

    crawl_with(run, institution, monkeypatch, error=error)

    assert Job.objects.filter(status=JobStatus.OPEN).count() == 3


def test_no_job_is_closed_on_zero_results(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forty vacancies yesterday and none today is breakage, not an empty estate."""
    JobFactory.create_batch(3, institution=institution)

    crawl_with(run, institution, monkeypatch, vacancies=[])

    assert Job.objects.filter(status=JobStatus.OPEN).count() == 3


def test_an_empty_result_is_recorded_as_zero_results_not_ok(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty list is a fact that needs its own name."""
    result = crawl_with(run, institution, monkeypatch, vacancies=[])

    assert result.outcome == CrawlOutcome.ZERO_RESULTS


def test_a_failed_crawl_records_why_nothing_was_closed(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    JobFactory(institution=institution)

    result = crawl_with(run, institution, monkeypatch, error=Timeout("timed out"))

    assert "TIMEOUT" in result.error_detail or "timed out" in result.error_detail


def test_a_drop_from_many_to_none_is_flagged(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Visually distinct from an institution that has genuinely had none for weeks."""
    first_run = CrawlRunFactory()
    crawl_with(first_run, institution, monkeypatch, vacancies=[vacancy(i) for i in range(40)])

    result = crawl_with(run, institution, monkeypatch, vacancies=[])

    assert result.dropped_to_zero is True


def test_an_institution_that_has_always_had_none_is_not_flagged(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_run = CrawlRunFactory()
    crawl_with(first_run, institution, monkeypatch, vacancies=[])

    result = crawl_with(run, institution, monkeypatch, vacancies=[])

    assert result.dropped_to_zero is False


def test_a_successful_crawl_closes_what_is_genuinely_gone(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule protects against false closure, not against closure."""
    JobFactory(institution=institution, source_url=f"{CAREERS_URL}/vacancy/0")
    JobFactory(institution=institution, source_url=f"{CAREERS_URL}/vacancy/99")

    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(0)])

    assert Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/99").status == JobStatus.DISAPPEARED


def test_a_closed_job_records_when_it_disappeared(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    JobFactory(institution=institution, source_url=f"{CAREERS_URL}/vacancy/99")

    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(0)])

    assert Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/99").disappeared_at is not None


def test_a_manual_job_survives_a_crawl_that_never_saw_it(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    JobFactory(institution=institution, source="MANUAL", source_url="https://www.jobs.nhs.uk/916")

    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(0)])

    assert Job.objects.get(source=JobSource.MANUAL).status == JobStatus.OPEN


def test_crawling_the_same_content_twice_creates_nothing_the_second_time(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacancies = [vacancy(index) for index in range(5)]
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=vacancies)

    second = crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=vacancies)

    assert (second.jobs_new, second.jobs_updated) == (0, 0)


def test_crawling_the_same_content_twice_leaves_one_row_per_vacancy(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    vacancies = [vacancy(index) for index in range(5)]
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=vacancies)
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=vacancies)

    assert Job.objects.count() == 5


def test_a_first_crawl_creates_every_vacancy(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = crawl_with(run, institution, monkeypatch, vacancies=[vacancy(i) for i in range(5)])

    assert result.jobs_new == 5


def test_a_vacancys_category_lands_on_its_job_row(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A platform's own classification - "Academic", "Research" - is stored, not discarded."""
    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(1, category="Research")])

    assert Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/1").category == "Research"


def test_a_vacancy_with_no_category_leaves_it_blank_not_guessed(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Most platforms draw no such distinction at all - blank is the honest answer."""
    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(1)])

    assert Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/1").category == ""


def test_a_vacancys_discipline_is_classified_from_its_title(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fixed taxonomy, unlike `category`, is inferred - that is the whole point of it."""
    crawl_with(
        run, institution, monkeypatch, vacancies=[vacancy(1, title="Lecturer in Psychology")]
    )

    job = Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/1")
    assert job.discipline == Discipline.PSYCHOLOGY


def test_a_vacancy_matching_no_discipline_is_other_not_blank(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    crawl_with(
        run, institution, monkeypatch, vacancies=[vacancy(1, title="Front of House Assistant")]
    )

    job = Job.objects.get(source_url=f"{CAREERS_URL}/vacancy/1")
    assert job.discipline == Discipline.OTHER


class _EnrichingStubAdapter(StubAdapter):
    """A `StubAdapter` whose detail page actually answers, for the one test that opens it."""

    def __init__(self, vacancies: list[RawVacancy], detail: RawVacancy) -> None:
        super().__init__(vacancies=vacancies)
        self._detail = detail

    def fetch_detail(self, url: str) -> RawVacancy:
        return self._detail


def test_a_thin_listing_is_topped_up_from_its_own_detail_page(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    thin = vacancy(1)
    detail = RawVacancy(
        source_url=thin.source_url,
        title=thin.title,
        institution_slug=thin.institution_slug,
        description_text="We are seeking a candidate with strong Python experience. " * 5,
        category="Research",
    )
    adapter = _EnrichingStubAdapter([thin], detail)
    monkeypatch.setattr("crawler.crawl.resolve_adapter", lambda *args, **kwargs: adapter)
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(
            url=CAREERS_URL,
            status_code=200,
            text="<html><body>Vacancies</body></html>",
            headers={"content-type": "text/html"},
        ),
    )

    overridden = {**django_settings.CRAWLER, "MAX_DETAIL_FETCHES_PER_INSTITUTION": 5}
    with override_settings(CRAWLER=overridden):
        crawl_institution(run, institution, http=client)

    job = Job.objects.get(source_url=thin.source_url)
    assert job.category == "Research"
    assert "Python experience" in job.description_text


def test_an_enriched_description_survives_a_crawl_the_differ_calls_unchanged(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A change that only enrichment found must still be saved.

    The differ calls it unchanged: `vacancy_content_hash` leaves out the description, so a job that
    only gains a description
    counts as "unchanged". That must mean "no revision", not "throw the description away".
    """
    thin = vacancy(1)
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=[thin])
    assert Job.objects.get(source_url=thin.source_url).description_text == ""

    detail = RawVacancy(
        source_url=thin.source_url,
        title=thin.title,
        institution_slug=thin.institution_slug,
        description_text="We are seeking a candidate with strong Python experience. " * 5,
    )
    adapter = _EnrichingStubAdapter([thin], detail)
    monkeypatch.setattr("crawler.crawl.resolve_adapter", lambda *args, **kwargs: adapter)
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(
            url=CAREERS_URL,
            status_code=200,
            text="<html><body>Vacancies</body></html>",
            headers={"content-type": "text/html"},
        ),
    )

    overridden = {**django_settings.CRAWLER, "MAX_DETAIL_FETCHES_PER_INSTITUTION": 5}
    with override_settings(CRAWLER=overridden):
        crawl_institution(CrawlRunFactory(), institution, http=client)

    job = Job.objects.get(source_url=thin.source_url)
    assert "Python experience" in job.description_text
    assert not JobRevision.objects.filter(job=job).exists()


def test_a_changed_salary_writes_a_revision(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=[vacancy(1)])

    crawl_with(
        CrawlRunFactory(),
        institution,
        monkeypatch,
        vacancies=[vacancy(1, salary_raw="£42,000 to £50,000 per annum")],
    )

    assert JobRevision.objects.filter(field="salary_raw").count() == 1


def test_a_revision_records_both_values(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before and after side by side is what the Changed tab shows."""
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=[vacancy(1)])
    crawl_with(
        CrawlRunFactory(),
        institution,
        monkeypatch,
        vacancies=[vacancy(1, salary_raw="£42,000 to £50,000 per annum")],
    )

    revision = JobRevision.objects.get(field="salary_raw")

    assert (revision.value_before, revision.value_after) == (
        "£38,784 to £46,049 per annum",
        "£42,000 to £50,000 per annum",
    )


def test_a_revision_is_attributed_to_the_run_that_found_it(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    crawl_with(CrawlRunFactory(), institution, monkeypatch, vacancies=[vacancy(1)])
    second_run = CrawlRunFactory()
    crawl_with(
        second_run, institution, monkeypatch, vacancies=[vacancy(1, title="Senior Engineer")]
    )

    assert JobRevision.objects.get(field="title").crawl_run_id == second_run.pk


def test_one_institution_raising_does_not_stop_the_others(
    run: CrawlRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With 167 institutions, one bad certificate must not cost the whole run."""
    broken = InstitutionFactory(slug="broken", careers_url=CAREERS_URL)
    healthy = InstitutionFactory(slug="healthy", careers_url=CAREERS_URL)

    crawl_with(run, broken, monkeypatch, error=ParseError("bad markup"))
    result = crawl_with(run, healthy, monkeypatch, vacancies=[vacancy(1)])

    assert result.outcome == CrawlOutcome.OK


def test_an_unexpected_exception_becomes_a_parse_error_not_a_success(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bug in an adapter must fail in the direction that leaves jobs alone."""
    result = crawl_with(run, institution, monkeypatch, error=ZeroDivisionError("oops"))

    assert result.outcome == CrawlOutcome.PARSE_ERROR


def test_an_unexpected_exception_records_its_type(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = crawl_with(run, institution, monkeypatch, error=ZeroDivisionError("oops"))

    assert result.error_class == "ZeroDivisionError"


def test_an_unexpected_exception_still_leaves_existing_jobs_open(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    JobFactory.create_batch(2, institution=institution)

    crawl_with(run, institution, monkeypatch, error=ZeroDivisionError("oops"))

    assert Job.objects.filter(status=JobStatus.OPEN).count() == 2


def test_a_second_concurrent_run_is_refused(institution: Institution) -> None:
    """Concurrent runs would double every request to every university."""
    start_run()

    with pytest.raises(RunAlreadyActive):
        start_run()


def test_the_refusal_carries_the_active_run(institution: Institution) -> None:
    """So the UI can link to the run in progress rather than only refusing."""
    first = start_run()

    with pytest.raises(RunAlreadyActive) as caught:
        start_run()

    assert caught.value.run.pk == first.pk


def test_a_run_can_start_once_the_previous_one_finished(institution: Institution) -> None:
    finalise_run(start_run())

    assert start_run().pk is not None


def test_finalising_a_run_rolls_up_its_totals(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = start_run()
    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(i) for i in range(3)])

    finalised = finalise_run(run)

    assert finalised.jobs_new == 3


def test_finalising_a_run_marks_it_complete(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = start_run()

    assert finalise_run(run).status == CrawlRunStatus.COMPLETE


def test_a_crawl_records_the_strategy_that_worked(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """So a site that gains JSON-LD later can be noticed and upgraded."""
    result = crawl_with(run, institution, monkeypatch, vacancies=[vacancy(1)])

    assert result.strategy == "HTML"


def test_a_crawl_records_which_adapter_ran(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = crawl_with(run, institution, monkeypatch, vacancies=[vacancy(1)])

    assert result.adapter == "StubAdapter"


def test_institutions_done_advances_while_the_run_is_still_in_progress(
    run: CrawlRun, institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The console reads this field during a run, not only after ``finalise_run``.

    Otherwise a 167-institution run would show "0 of 167 done" until the very end.
    """
    crawl_with(run, institution, monkeypatch, vacancies=[vacancy(1)])

    run.refresh_from_db()

    assert run.institutions_done == 1


def test_institutions_done_counts_a_skipped_institution_too(
    run: CrawlRun, institution: Institution
) -> None:
    record_skipped_institution(run, institution, reason="Skipped: run was cancelled.")

    run.refresh_from_db()

    assert run.institutions_done == 1


def test_an_institution_with_no_careers_url_is_skipped_not_failed(
    run: CrawlRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing was attempted, so nothing failed - and nothing may be closed either."""
    institution = InstitutionFactory(slug="no-url", careers_url="")

    result = crawl_with(run, institution, monkeypatch, vacancies=[])

    assert result.outcome == CrawlOutcome.SKIPPED


class _BlockedHttp:
    """A client that raises ``Blocked`` for every request - the plain probe's whole estate."""

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
        raise Blocked(f"{url} returned 403", url=url)

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResponse:
        raise Blocked(f"{url} returned 403", url=url)


def test_a_blocked_probe_is_never_retried_through_the_browser(institution: Institution) -> None:
    """A site that refuses our honest crawler has said no. We record BLOCKED and stop."""
    browser = FixtureBrowserSession(
        responses={
            CAREERS_URL: FetchResponse(
                url=CAREERS_URL, status_code=200, text="<html><body>Vacancies</body></html>"
            )
        }
    )

    result = crawl_one(institution, http=_BlockedHttp(), browser=browser)

    assert result.outcome == CrawlOutcome.BLOCKED
    assert browser.rendered == []


def test_a_probe_blocked_with_no_browser_available_stays_blocked(
    institution: Institution,
) -> None:
    """No browser configured - the block is reported honestly, not retried into silence."""
    result = crawl_one(institution, http=_BlockedHttp(), browser=None)

    assert result.outcome == CrawlOutcome.BLOCKED


class _NoAdapterMatchAdapter:
    """What ``detect_adapter`` returns for the *rendered* page.

    A class, not an instance: ``resolve_adapter`` builds it, as it would a real adapter.
    """

    platform = Platform.STONEFISH

    def __init__(self, http: object, browser: object | None = None) -> None:
        """Accept the same constructor signature every real adapter does."""
        from crawler.enums import ExtractionStrategy

        self.http = http
        self.browser = browser
        self.strategy = ExtractionStrategy.HTML
        self.fallback_fired = False

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: object) -> bool:
        return True

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        return [vacancy(1)]

    def fetch_detail(self, url: str) -> RawVacancy:  # pragma: no cover - not used here
        raise NotImplementedError


def test_a_probe_matching_no_adapter_gets_one_retry_through_the_browser(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The plain HTTP probe finds nothing; the rendered page does.

    ``detect_adapter`` is replaced in two places, because ``crawler.crawl`` and
    ``crawler.adapter_resolution`` each import it. Both need the same fake, so one counter sees
    both calls.
    """
    calls: list[object] = []

    def fake_detect_adapter(ref: InstitutionRef, probe: object) -> type | None:
        calls.append(probe)
        return None if len(calls) == 1 else _NoAdapterMatchAdapter

    monkeypatch.setattr("crawler.crawl.detect_adapter", fake_detect_adapter)
    monkeypatch.setattr("crawler.adapter_resolution.detect_adapter", fake_detect_adapter)
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(
            url=CAREERS_URL,
            status_code=200,
            text="<html><body>Empty until a script runs</body></html>",
            headers={"content-type": "text/html"},
        ),
    )
    browser = FixtureBrowserSession(
        responses={
            CAREERS_URL: FetchResponse(
                url=CAREERS_URL,
                status_code=200,
                text="<html><body>Rendered vacancies</body></html>",
            )
        }
    )

    result = crawl_one(institution, http=client, browser=browser)

    assert result.outcome == CrawlOutcome.OK
    assert result.fallback_fired is True
    assert len(calls) == 2


def test_a_probe_matching_no_adapter_with_no_browser_stays_no_adapter(
    institution: Institution, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No browser configured - reported honestly as ``NoAdapterFound``, not retried into silence."""
    monkeypatch.setattr("crawler.crawl.detect_adapter", lambda ref, probe: None)
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(url=CAREERS_URL, status_code=200, text="<html></html>"),
    )

    result = crawl_one(institution, http=client, browser=None)

    assert result.outcome == CrawlOutcome.NO_ADAPTER


def test_a_human_adapter_override_skips_the_browser_retry(
    run: CrawlRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A platform set by a person is trusted, so there is never a second, browser-rendered fetch.

    ``adapter_for_platform`` is replaced in ``crawler.adapter_resolution``, where
    ``resolve_adapter`` calls it.
    """
    institution = InstitutionFactory(
        slug="university-with-override",
        careers_url=CAREERS_URL,
        adapter_override=Platform.STONEFISH,
    )
    detect_calls: list[object] = []
    monkeypatch.setattr(
        "crawler.crawl.detect_adapter",
        lambda ref, probe: detect_calls.append(probe),
    )
    monkeypatch.setattr(
        "crawler.adapter_resolution.adapter_for_platform", lambda platform: _NoAdapterMatchAdapter
    )
    client = FixtureHttpClient(
        responses={},
        default=FetchResponse(url=CAREERS_URL, status_code=200, text="<html></html>"),
    )

    result = crawl_one(institution, http=client, browser=None)

    assert result.outcome == CrawlOutcome.OK
    assert detect_calls == []
