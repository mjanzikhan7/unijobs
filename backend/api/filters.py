"""Query filters for the job list.

One filter set is used by the list, the facet counts, the export and the digest. So the export
always matches the active filters, and a saved search matches what the URL showed.
"""

from __future__ import annotations

from typing import Any

import django_filters
from django.contrib.postgres.search import SearchQuery
from django.db.models import Case, Count, IntegerField, Q, QuerySet, Value, When
from django.http import QueryDict

from institutions.enums import Nation
from jobs.enums import ContractType, Discipline, Hours, JobSource, JobStatus, Workplace
from jobs.models import Job
from screening.enums import SPONSORING_VERDICTS, SponsorVerdict, ThresholdVerdict


class JobFilter(django_filters.FilterSet):
    """Every facet on the job list.

    Only listed sort orders are allowed. Letting a client sort by any field could mean a slow
    scan of a column with no index.
    """

    q = django_filters.CharFilter(method="filter_search", label="Search")

    institution = django_filters.BaseInFilter(field_name="institution__slug", lookup_expr="in")
    nation = django_filters.MultipleChoiceFilter(
        field_name="institution__nation", choices=Nation.choices()
    )
    city = django_filters.CharFilter(field_name="city", lookup_expr="icontains")
    category = django_filters.BaseInFilter(field_name="category", lookup_expr="in")
    discipline = django_filters.MultipleChoiceFilter(choices=Discipline.choices())

    status = django_filters.MultipleChoiceFilter(choices=JobStatus.choices())
    source = django_filters.MultipleChoiceFilter(choices=JobSource.choices())
    contract_type = django_filters.MultipleChoiceFilter(choices=ContractType.choices())
    hours = django_filters.MultipleChoiceFilter(choices=Hours.choices())
    workplace = django_filters.MultipleChoiceFilter(choices=Workplace.choices())

    sponsor_verdict = django_filters.MultipleChoiceFilter(
        field_name="screening__sponsor_verdict", choices=SponsorVerdict.choices()
    )
    threshold_verdict = django_filters.MultipleChoiceFilter(
        field_name="screening__threshold_verdict", choices=ThresholdVerdict.choices()
    )
    sponsorable = django_filters.BooleanFilter(
        method="filter_sponsorable",
        label="Only employers that can sponsor, advert exclusions honoured",
    )

    salary_min = django_filters.NumberFilter(field_name="screening__salary_min", lookup_expr="gte")
    salary_max = django_filters.NumberFilter(field_name="screening__salary_min", lookup_expr="lte")
    min_fitness = django_filters.NumberFilter(field_name="fitness_score", lookup_expr="gte")

    posted_after = django_filters.DateFilter(field_name="posted_date", lookup_expr="gte")
    closing_before = django_filters.DateFilter(field_name="closing_date", lookup_expr="lte")
    closing_after = django_filters.DateFilter(field_name="closing_date", lookup_expr="gte")

    saved = django_filters.BooleanFilter(method="filter_saved", label="Saved jobs only")

    order = django_filters.OrderingFilter(
        fields=(
            ("posted_date", "posted"),
            ("closing_date", "closing"),
            ("fitness_score", "fitness"),
            ("screening__salary_min", "salary"),
            ("first_seen_at", "seen"),
            ("title", "title"),
        ),
        label="Sort by",
    )

    class Meta:
        model = Job
        fields: list[str] = []

    def filter_search(self, queryset: QuerySet[Job], name: str, value: str) -> QuerySet[Job]:
        """Search, with a wider match and a clear ranking.

        Full-text search finds "lecturer" from "lecturing", but "chem" finds nothing in
        "chemistry", so a substring match is added. Results are sorted by a fixed ladder, not
        ``ts_rank``, which returns ``NULL`` for an empty ``search_vector``. A whole-word title match
        ("Software Engineer") comes before a title that only contains the letters ("Softwarehouse").
        """
        term = (value or "").strip()
        if not term:
            return queryset
        query = SearchQuery(term, config="english", search_type="websearch")
        title_tokenised = Q(title__search=query)
        title_contains = Q(title__icontains=term)
        field_contains = Q(department__icontains=term) | Q(institution__name__icontains=term)
        fulltext_match = Q(search_vector=query)
        description_contains = Q(description_text__icontains=term)

        relevance = Case(
            When(title_tokenised, then=Value(5)),
            When(title_contains, then=Value(4)),
            When(field_contains, then=Value(3)),
            When(fulltext_match, then=Value(2)),
            When(description_contains, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
        return (
            queryset.filter(
                title_tokenised
                | title_contains
                | field_contains
                | fulltext_match
                | description_contains
            )
            .annotate(relevance=relevance)
            .order_by("-relevance", "-posted_date")
        )

    def filter_sponsorable(
        self, queryset: QuerySet[Job], name: str, value: bool | None
    ) -> QuerySet[Job]:
        """Keep only jobs where sponsorship is really possible.

        An advert that rules sponsorship out removes the job even at a confirmed sponsor. The advert
        is about this post. The register is about the employer.
        """
        if value is None:
            return queryset
        condition = Q(
            screening__sponsor_verdict__in=[verdict.value for verdict in SPONSORING_VERDICTS]
        ) & Q(screening__advert_excludes_sponsorship=False)
        return queryset.filter(condition) if value else queryset.exclude(condition)

    def filter_saved(self, queryset: QuerySet[Job], name: str, value: bool | None) -> QuerySet[Job]:
        """Keep only jobs *this user* saved, or leave them out.

        Always filtered by the requester. ``saved__isnull`` alone would answer "did anyone save
        this", which is wrong and would also reveal another person's shortlist.
        """
        if value is None:
            return queryset

        user = getattr(self.request, "user", None)
        if user is None or not user.is_authenticated:
            return queryset.none() if value else queryset

        saved = Q(saved_by__owner=user)
        return queryset.filter(saved) if value else queryset.exclude(saved)


FACET_FIELDS: dict[str, str] = {
    "institution": "institution__slug",
    "nation": "institution__nation",
    "category": "category",
    "discipline": "discipline",
    "status": "status",
    "source": "source",
    "contract_type": "contract_type",
    "hours": "hours",
    "workplace": "workplace",
    "sponsor_verdict": "screening__sponsor_verdict",
    "threshold_verdict": "screening__threshold_verdict",
}


def facet_counts(
    base_queryset: QuerySet[Job], query_params: QueryDict
) -> dict[str, list[dict[str, Any]]]:
    """Count each facet value **in the current query, without that facet's own filter**.

    Counts follow every *other* filter. With its own filter applied, every other value in the
    group would show zero and look unavailable. We copy the real ``QueryDict`` so values with
    several entries still arrive as lists.
    """
    facets: dict[str, list[dict[str, Any]]] = {}
    for name, field in FACET_FIELDS.items():
        params = query_params.copy()
        params.pop(name, None)
        sibling_queryset = JobFilter(params, queryset=base_queryset).qs
        rows = sibling_queryset.values(field).order_by(field).annotate(count=Count("id"))
        facets[name] = [
            {"value": row[field], "count": row["count"]}
            for row in rows
            if row[field] not in (None, "")
        ]
    return facets
