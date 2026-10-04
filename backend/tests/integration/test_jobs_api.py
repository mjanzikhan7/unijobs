"""The job list, facets, detail and export.

Two checks here matter most. One fixes the query count, because one query per row on
``job -> institution -> screening`` is the slowdown that will really happen. The other checks
that both badges are always there, because a row with no badge in a badged list looks safe.
"""

from __future__ import annotations

import csv
import io
import time
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from api.serializers import JobListSerializer, UnscreenedJob
from jobs.enums import Discipline, JobStatus
from jobs.models import Job
from jobs.services import refresh_search_vectors
from screening.enums import SponsorVerdict, ThresholdVerdict
from screening.models import Ruleset
from tests.factories import (
    ApplicationFactory,
    InstitutionFactory,
    JobFactory,
    JobFitnessFactory,
    SavedJobFactory,
    ScreeningFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def corpus(ruleset: Ruleset) -> list[Job]:
    """A small, varied corpus with every job screened."""
    bath = InstitutionFactory(slug="university-of-bath", name="University of Bath", city="Bath")
    edinburgh = InstitutionFactory(
        slug="university-of-edinburgh",
        name="University of Edinburgh",
        city="Edinburgh",
        nation="SCOTLAND",
    )

    jobs = [
        JobFactory(
            institution=bath,
            title="Research Software Engineer",
            salary_raw="£55,755 to £64,914 per annum",
            description_text="python django postgres research software",
        ),
        JobFactory(
            institution=bath,
            title="Laboratory Technician",
            salary_raw="£30,505 per annum",
            description_text="laboratory work",
        ),
        JobFactory(
            institution=edinburgh,
            title="Lecturer in Data Science",
            salary_raw="£47,389 rising to £51,753",
            description_text="teaching data science",
        ),
    ]
    verdicts = [
        (SponsorVerdict.CONFIRMED, ThresholdVerdict.TARGET_BAND, 90, 55755),
        (SponsorVerdict.CONFIRMED, ThresholdVerdict.EXCLUDED_BELOW_FLOOR, 20, 30505),
        (SponsorVerdict.NOT_FOUND, ThresholdVerdict.PAY_CUT, 60, 47389),
    ]
    for job, (sponsor, threshold, fitness, floor) in zip(jobs, verdicts, strict=True):
        ScreeningFactory(
            job=job,
            ruleset=ruleset,
            sponsor_verdict=sponsor,
            threshold_verdict=threshold,
            salary_min=floor,
        )
        JobFitnessFactory(job=job, score=fitness)
    refresh_search_vectors()
    return jobs


def test_every_result_carries_a_sponsor_verdict(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/")

    assert all(row["screening"]["sponsor_verdict"] for row in response.json()["results"])


def test_every_result_carries_a_threshold_verdict(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/")

    assert all(row["screening"]["threshold_verdict"] for row in response.json()["results"])


def test_a_job_with_no_screening_row_is_left_out_and_search_keeps_working(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """One unscreened job must never take the whole list down, and must never be shown."""
    screened = JobFactory(title="Screened job")
    ScreeningFactory(job=screened, ruleset=ruleset)
    unscreened = JobFactory(title="Unscreened job")

    response = auth_client.get("/api/jobs/")
    ids = [row["id"] for row in response.json()["results"]]

    assert response.status_code == 200
    assert screened.pk in ids
    assert unscreened.pk not in ids
    assert auth_client.get(f"/api/jobs/{unscreened.pk}/").status_code == 404


def test_the_serializer_still_refuses_a_job_with_no_screening_row(
    candidate_user: Any, ruleset: Ruleset
) -> None:
    """The last line of defence: a missing badge must never read as "confirmed"."""
    job = JobFactory()
    row = Job.objects.with_related(for_user=candidate_user).get(pk=job.pk)

    with pytest.raises(UnscreenedJob):
        _ = JobListSerializer(row).data


def test_the_default_view_shows_open_vacancies(auth_client: APIClient, corpus: list[Job]) -> None:
    corpus[0].status = JobStatus.DISAPPEARED
    corpus[0].save()

    response = auth_client.get("/api/jobs/")

    assert response.json()["count"] == 2


def test_filtering_by_institution_narrows_the_set(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?institution=university-of-bath")

    assert response.json()["count"] == 2


def test_filtering_by_category_narrows_the_set(auth_client: APIClient, ruleset: Ruleset) -> None:
    bristol = InstitutionFactory(name="University of Bristol")
    academic = JobFactory(institution=bristol, category="Academic")
    research = JobFactory(institution=bristol, category="Research")
    for job in (academic, research):
        ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get("/api/jobs/?category=Research")

    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == research.pk


def test_the_category_facet_counts_what_is_actually_there(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    bristol = InstitutionFactory(name="University of Bristol")
    for job in (
        JobFactory(institution=bristol, category="Academic"),
        JobFactory(institution=bristol, category="Academic"),
        JobFactory(institution=bristol, category=""),
    ):
        ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get("/api/jobs/facets/")
    categories = {row["value"]: row["count"] for row in response.json()["facets"]["category"]}

    assert categories == {"Academic": 2}


def test_filtering_by_discipline_narrows_the_set(auth_client: APIClient, ruleset: Ruleset) -> None:
    bristol = InstitutionFactory(name="University of Bristol")
    psychology = JobFactory(institution=bristol, discipline=Discipline.PSYCHOLOGY)
    economics = JobFactory(institution=bristol, discipline=Discipline.ECONOMICS)
    for job in (psychology, economics):
        ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get(f"/api/jobs/?discipline={Discipline.PSYCHOLOGY.value}")

    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == psychology.pk


def test_the_discipline_facet_counts_what_is_actually_there(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    bristol = InstitutionFactory(name="University of Bristol")
    for job in (
        JobFactory(institution=bristol, discipline=Discipline.PSYCHOLOGY),
        JobFactory(institution=bristol, discipline=Discipline.PSYCHOLOGY),
        JobFactory(institution=bristol, discipline=Discipline.OTHER),
    ):
        ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get("/api/jobs/facets/")
    disciplines = {row["value"]: row["count"] for row in response.json()["facets"]["discipline"]}

    assert disciplines == {Discipline.PSYCHOLOGY.value: 2, Discipline.OTHER.value: 1}


def test_filtering_by_nation_narrows_the_set(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/?nation=SCOTLAND")

    assert response.json()["count"] == 1


def test_filtering_by_threshold_verdict_narrows_the_set(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?threshold_verdict=TARGET_BAND")

    assert response.json()["count"] == 1


def test_filtering_by_minimum_fitness_narrows_the_set(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?min_fitness=70")

    assert response.json()["count"] == 1


def test_filtering_by_salary_floor_narrows_the_set(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?salary_min=50000")

    assert response.json()["count"] == 1


def test_the_sponsorable_filter_excludes_unlicensed_employers(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?sponsorable=true")

    assert response.json()["count"] == 2


def test_the_sponsorable_filter_honours_an_advert_exclusion(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """A confirmed sponsor whose advert rules sponsorship out is not sponsorable for this job."""
    screening = corpus[0].screening
    screening.advert_excludes_sponsorship = True
    screening.save()

    response = auth_client.get("/api/jobs/?sponsorable=true")

    assert response.json()["count"] == 1


def test_combined_filters_intersect(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get(
        "/api/jobs/?institution=university-of-bath&threshold_verdict=TARGET_BAND"
    )

    assert response.json()["count"] == 1


def test_full_text_search_finds_by_title(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/?q=laboratory")

    assert response.json()["count"] == 1


def test_full_text_search_finds_by_institution_name(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/?q=Edinburgh")

    assert response.json()["count"] == 1


def test_search_falls_back_to_a_substring_match_full_text_would_miss(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """A partial word that full-text search cannot find.

    "chem" shares no word stem with "Biochemistry", but a person typing "chem" expects this job.
    """
    bristol = InstitutionFactory(name="University of Bristol")
    job = JobFactory(institution=bristol, title="PhD Studentship in Biochemistry")
    ScreeningFactory(job=job, ruleset=ruleset)
    refresh_search_vectors()

    response = auth_client.get("/api/jobs/?q=chem")

    assert response.json()["count"] == 1


def test_a_full_text_match_ranks_ahead_of_a_substring_only_match(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """A plain substring hit is a weaker signal than a real full-text match, not a better one."""
    bristol = InstitutionFactory(name="University of Bristol")
    exact = JobFactory(institution=bristol, title="Software Engineer")
    substring_only = JobFactory(institution=bristol, title="Softwarehouse Coordinator")
    for job in (exact, substring_only):
        ScreeningFactory(job=job, ruleset=ruleset)
    refresh_search_vectors()

    response = auth_client.get("/api/jobs/?q=software")
    results = response.json()["results"]

    assert [row["id"] for row in results] == [exact.pk, substring_only.pk]


def test_a_title_match_ranks_first_even_with_no_search_index_built_yet(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """Real case: search results were not sorted by relevance.

    When ``search_vector`` was empty, ``ts_rank`` returned ``NULL`` for every row, so results were
    sorted by date only. ``refresh_search_vectors()`` is not called here on purpose: a title match
    must still come first.
    """
    bristol = InstitutionFactory(name="University of Bristol")
    mention_only = JobFactory(
        institution=bristol,
        title="Finance Coordinator",
        description_text="Experience with financial software is desirable.",
        posted_date="2026-08-20",
    )
    title_match = JobFactory(
        institution=bristol, title="Software Engineer", posted_date="2026-08-01"
    )
    for job in (mention_only, title_match):
        ScreeningFactory(job=job, ruleset=ruleset)

    response = auth_client.get("/api/jobs/?q=software")
    results = response.json()["results"]

    assert [row["id"] for row in results] == [title_match.pk, mention_only.pk]


def test_the_list_endpoint_does_not_issue_a_query_per_row(
    auth_client: APIClient, ruleset: Ruleset, django_assert_max_num_queries: object
) -> None:
    """One query per row on job -> institution -> screening is the slowdown that really happens.

    A ceiling, not an exact count: the number must not grow with the results, and an exact count
    would break whenever middleware is added.
    """
    for _ in range(25):
        ScreeningFactory(job=JobFactory(), ruleset=ruleset)

    with django_assert_max_num_queries(6):  # type: ignore[operator]
        auth_client.get("/api/jobs/?page_size=25")


def test_the_list_query_count_does_not_grow_with_the_result_set(
    auth_client: APIClient, ruleset: Ruleset, django_assert_max_num_queries: object
) -> None:
    """Same ceiling at four times the page size."""
    for _ in range(100):
        ScreeningFactory(job=JobFactory(), ruleset=ruleset)

    with django_assert_max_num_queries(6):  # type: ignore[operator]
        auth_client.get("/api/jobs/?page_size=100")


def test_sorting_by_salary_works(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/?order=-salary")

    assert response.json()["results"][0]["title"] == "Research Software Engineer"


def test_sorting_by_fitness_works(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/?order=-fitness")

    assert response.json()["results"][0]["fitness_score"] == 90


def test_facet_counts_reflect_the_current_query(auth_client: APIClient, corpus: list[Job]) -> None:
    """A count that ignores the filters promises results clicking will not produce."""
    response = auth_client.get("/api/jobs/facets/?institution=university-of-bath")
    nations = {row["value"]: row["count"] for row in response.json()["facets"]["nation"]}

    assert nations == {"ENGLAND": 2}


def test_facet_counts_over_the_whole_corpus_when_unfiltered(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/facets/")
    nations = {row["value"]: row["count"] for row in response.json()["facets"]["nation"]}

    assert nations == {"ENGLAND": 2, "SCOTLAND": 1}


def test_facets_report_the_filtered_total(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/facets/?nation=SCOTLAND")

    assert response.json()["total"] == 1


def test_facets_cover_every_declared_dimension(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/facets/")

    assert "sponsor_verdict" in response.json()["facets"]


def test_selecting_one_facet_value_does_not_zero_out_its_siblings(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """A facet must not be counted with its own filter applied.

    Otherwise every other checkbox in the same group shows zero and looks unavailable.
    """
    response = auth_client.get("/api/jobs/facets/?sponsor_verdict=CONFIRMED")
    verdicts = {row["value"]: row["count"] for row in response.json()["facets"]["sponsor_verdict"]}

    assert verdicts == {"CONFIRMED": 2, "NOT_FOUND": 1}


def test_a_facet_still_honours_every_other_active_filter(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """Excluding a facet's own filter must not also drop the filters on other facets."""
    response = auth_client.get(
        "/api/jobs/facets/?sponsor_verdict=CONFIRMED&institution=university-of-bath"
    )
    verdicts = {row["value"]: row["count"] for row in response.json()["facets"]["sponsor_verdict"]}

    assert verdicts == {"CONFIRMED": 2}


@pytest.mark.slow
def test_the_list_endpoint_stays_fast_on_a_large_corpus(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """The real target is 5,000 jobs under 300ms; 800 keeps CI under eight minutes."""
    institution = InstitutionFactory()
    jobs = JobFactory.create_batch(800, institution=institution)
    for job in jobs:
        ScreeningFactory(job=job, ruleset=ruleset)
    refresh_search_vectors()

    started = time.monotonic()
    auth_client.get("/api/jobs/?page_size=25")
    elapsed = time.monotonic() - started

    assert elapsed < 0.3


def test_the_apply_url_is_the_employers_own_posting(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """Never a cached or internal copy. This project never stands in the middle."""
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")
    payload = response.json()

    assert payload["apply_url"] == payload["source_url"]


def test_the_apply_url_matches_what_was_crawled(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")

    assert response.json()["apply_url"] == corpus[0].source_url


def test_a_job_with_no_pipeline_entry_reports_no_application(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """The Apply button needs to tell "never tracked" apart from "already Found/Applied"."""
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")
    payload = response.json()

    assert payload["application_id"] is None
    assert payload["application_status"] is None


def test_a_job_already_in_the_pipeline_reports_its_application(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    application = ApplicationFactory(job=corpus[0], status="APPLIED")

    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")
    payload = response.json()

    assert payload["application_id"] == application.pk
    assert payload["application_status"] == "APPLIED"


def test_the_detail_view_includes_the_advert_body(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")

    assert "description_html" in response.json()


def test_the_detail_view_explains_the_threshold_verdict(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    """A badge without a reason is unarguable, and unarguable badges get ignored."""
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")

    assert response.json()["screening"]["threshold_explanation"]


def test_the_detail_view_names_the_ruleset_that_produced_the_verdict(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get(f"/api/jobs/{corpus[0].pk}/")

    assert response.json()["screening"]["ruleset_version"] == 1


def test_export_respects_the_active_filters(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/export/?institution=university-of-bath")
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))

    assert len(rows) == 2


def test_export_covers_the_whole_corpus_when_unfiltered(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/export/")
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))

    assert len(rows) == 3


def test_export_includes_the_badges_as_columns(auth_client: APIClient, corpus: list[Job]) -> None:
    """A spreadsheet without the verdicts loses the only thing that made the list useful."""
    response = auth_client.get("/api/jobs/export/")
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))

    assert rows[0]["Sponsor verdict"] and rows[0]["Threshold verdict"]


def test_export_keeps_the_salary_exactly_as_advertised(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/export/")
    rows = list(csv.DictReader(io.StringIO(response.content.decode())))

    assert any(row["Salary (as advertised)"] == "£30,505 per annum" for row in rows)


def test_export_offers_xlsx(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/export/?file_format=xlsx")

    assert response["Content-Type"].startswith("application/vnd.openxmlformats-officedocument")


def test_export_is_downloaded_not_rendered(auth_client: APIClient, corpus: list[Job]) -> None:
    response = auth_client.get("/api/jobs/export/")

    assert "attachment" in response["Content-Disposition"]


def test_a_manually_added_job_is_screened_immediately(
    auth_client: APIClient, ruleset: Ruleset
) -> None:
    """UC-12. Indistinguishable downstream: same badges, same search, same export."""
    InstitutionFactory(slug="nhs-trust")

    response = auth_client.post(
        "/api/jobs/manual/",
        {
            "institution": "nhs-trust",
            "source_url": "https://www.jobs.nhs.uk/candidate/jobadvert/C9999",
            "title": "Clinical Research Fellow",
            "salary_raw": "£55,000 per annum",
        },
        format="json",
    )

    assert response.json()["screening"]["threshold_verdict"] == ThresholdVerdict.TARGET_BAND


def test_a_manually_added_job_appears_in_search(auth_client: APIClient, ruleset: Ruleset) -> None:
    InstitutionFactory(slug="nhs-trust", name="NHS Trust")

    auth_client.post(
        "/api/jobs/manual/",
        {
            "institution": "nhs-trust",
            "source_url": "https://www.jobs.nhs.uk/candidate/jobadvert/C9999",
            "title": "Clinical Research Fellow",
            "salary_raw": "£55,000 per annum",
        },
        format="json",
    )

    response = auth_client.get("/api/jobs/?q=clinical")

    assert response.json()["count"] == 1


def test_saving_a_job_is_reflected_in_the_list(auth_client: APIClient, corpus: list[Job]) -> None:
    SavedJobFactory(job=corpus[0])

    response = auth_client.get("/api/jobs/?saved=true")

    assert response.json()["count"] == 1


def test_an_unsaved_job_reports_itself_as_unsaved(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    response = auth_client.get("/api/jobs/")

    assert all(row["is_saved"] is False for row in response.json()["results"])


def test_closing_before_filters_on_the_closing_date(
    auth_client: APIClient, corpus: list[Job]
) -> None:
    corpus[0].closing_date = timezone.localdate() + timedelta(days=3)
    corpus[0].save()

    response = auth_client.get(
        f"/api/jobs/?closing_before={(timezone.localdate() + timedelta(days=5)).isoformat()}"
    )

    assert response.json()["count"] == 1
