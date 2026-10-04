"""Filling in a thin listing from its own detail page.

Written before the code, per the working agreement for ``crawler/``.

Fitness scoring and the category facets both need real text a listing page frequently does not
carry. This is the layer that goes back for it - carefully: never overwriting what the listing
already had, never spending more than it was told to, and never letting one bad detail page take
the rest of the run down with it.
"""

from __future__ import annotations

from crawler.enrichment import MIN_DESCRIPTION_CHARS, enrich_missing_details, needs_detail_fetch
from crawler.exceptions import Blocked
from crawler.types import RawVacancy

LONG_DESCRIPTION = "We are seeking a candidate. " * 20


def _vacancy(**overrides: object) -> RawVacancy:
    fields: dict[str, object] = {
        "source_url": "https://example.ac.uk/jobs/1",
        "title": "Research Assistant",
        "institution_slug": "example",
    }
    fields.update(overrides)
    return RawVacancy(**fields)  # type: ignore[arg-type]


class _FakeAdapter:
    """A `PlatformAdapter` stand-in exposing only what enrichment calls."""

    def __init__(self, details: dict[str, RawVacancy | Exception]) -> None:
        self._details = details
        self.calls: list[str] = []

    def fetch_detail(self, url: str) -> RawVacancy:
        self.calls.append(url)
        outcome = self._details[url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_a_vacancy_with_no_description_and_no_category_needs_fetching() -> None:
    assert needs_detail_fetch(_vacancy()) is True


def test_a_vacancy_with_a_real_description_and_a_category_does_not() -> None:
    vacancy = _vacancy(description_text=LONG_DESCRIPTION, category="Research")
    assert needs_detail_fetch(vacancy) is False


def test_a_stub_description_under_the_threshold_still_needs_fetching() -> None:
    vacancy = _vacancy(description_text="Apply now.", category="Research")
    assert needs_detail_fetch(vacancy) is True


def test_a_long_description_with_no_category_still_needs_fetching() -> None:
    """Fitness has what it needs; the category facets on job search do not."""
    vacancy = _vacancy(description_text=LONG_DESCRIPTION, category="")
    assert needs_detail_fetch(vacancy) is True


def test_the_threshold_boundary_is_exclusive() -> None:
    exactly_at_threshold = "x" * MIN_DESCRIPTION_CHARS
    vacancy = _vacancy(description_text=exactly_at_threshold, category="Research")
    assert needs_detail_fetch(vacancy) is False


def test_a_thin_vacancy_is_topped_up_from_its_detail_page() -> None:
    thin = _vacancy()
    detail = _vacancy(description_text=LONG_DESCRIPTION, category="Research")
    adapter = _FakeAdapter({thin.source_url: detail})

    [result] = enrich_missing_details([thin], adapter=adapter, max_fetches=10)

    assert result.description_text == LONG_DESCRIPTION
    assert result.category == "Research"


def test_a_detail_pages_placeholder_institution_never_leaks_into_the_result() -> None:
    """A detail page's own placeholder institution must never survive into the merged result.

    A listing from institution "example" merged with a detail page claiming to be institution
    "pending" must still come out as "example".
    """
    listing = _vacancy(institution_slug="example")
    detail = _vacancy(
        institution_slug="pending", description_text=LONG_DESCRIPTION, category="Research"
    )
    adapter = _FakeAdapter({listing.source_url: detail})

    [result] = enrich_missing_details([listing], adapter=adapter, max_fetches=10)

    assert result.institution_slug == "example"


def test_a_field_the_listing_already_had_is_never_overwritten() -> None:
    """The listing page is trusted first - it is what the adapter was built and tested against."""
    listing = _vacancy(category="Academic")
    detail = _vacancy(category="Research", description_text=LONG_DESCRIPTION)
    adapter = _FakeAdapter({listing.source_url: detail})

    [result] = enrich_missing_details([listing], adapter=adapter, max_fetches=10)

    assert result.category == "Academic"
    assert result.description_text == LONG_DESCRIPTION


def test_a_vacancy_that_already_has_everything_is_never_fetched() -> None:
    complete = _vacancy(description_text=LONG_DESCRIPTION, category="Research")
    adapter = _FakeAdapter({})

    enrich_missing_details([complete], adapter=adapter, max_fetches=10)

    assert adapter.calls == []


def test_zero_max_fetches_disables_enrichment_entirely() -> None:
    thin = _vacancy()
    adapter = _FakeAdapter({thin.source_url: _vacancy(category="Research")})

    [result] = enrich_missing_details([thin], adapter=adapter, max_fetches=0)

    assert adapter.calls == []
    assert result.category == ""


def test_the_fetch_count_is_capped_regardless_of_how_many_vacancies_need_it() -> None:
    thin = [_vacancy(source_url=f"https://example.ac.uk/jobs/{i}") for i in range(5)]
    adapter = _FakeAdapter({vacancy.source_url: _vacancy(category="Research") for vacancy in thin})

    enrich_missing_details(thin, adapter=adapter, max_fetches=2)

    assert len(adapter.calls) == 2


def test_the_thinnest_vacancies_are_prioritised_within_the_cap() -> None:
    """A vacancy with nothing at all has more to gain than one that's merely missing a category."""
    bare = _vacancy(source_url="https://example.ac.uk/jobs/bare")
    almost_there = _vacancy(
        source_url="https://example.ac.uk/jobs/almost", description_text=LONG_DESCRIPTION
    )
    adapter = _FakeAdapter(
        {
            bare.source_url: _vacancy(category="Research"),
            almost_there.source_url: _vacancy(category="Research"),
        }
    )

    enrich_missing_details([almost_there, bare], adapter=adapter, max_fetches=1)

    assert adapter.calls == [bare.source_url]


def test_a_typed_adapter_error_on_one_detail_page_does_not_stop_the_others() -> None:
    ok = _vacancy(source_url="https://example.ac.uk/jobs/ok")
    blocked = _vacancy(source_url="https://example.ac.uk/jobs/blocked")
    adapter = _FakeAdapter(
        {
            ok.source_url: _vacancy(category="Research"),
            blocked.source_url: Blocked("challenge page", url=blocked.source_url),
        }
    )

    results = enrich_missing_details([ok, blocked], adapter=adapter, max_fetches=10)
    by_url = {vacancy.source_url: vacancy for vacancy in results}

    assert by_url[ok.source_url].category == "Research"
    assert by_url[blocked.source_url].category == ""


def test_an_unexpected_exception_on_one_detail_page_does_not_stop_the_others() -> None:
    """A parser bug on one page's markup is not evidence anything is wrong with the rest."""
    ok = _vacancy(source_url="https://example.ac.uk/jobs/ok")
    broken = _vacancy(source_url="https://example.ac.uk/jobs/broken")
    adapter = _FakeAdapter(
        {
            ok.source_url: _vacancy(category="Research"),
            broken.source_url: ValueError("malformed markup"),
        }
    )

    results = enrich_missing_details([ok, broken], adapter=adapter, max_fetches=10)
    by_url = {vacancy.source_url: vacancy for vacancy in results}

    assert by_url[ok.source_url].category == "Research"
    assert by_url[broken.source_url].category == ""


def test_vacancies_that_needed_no_fetch_pass_through_unchanged() -> None:
    thin = _vacancy(source_url="https://example.ac.uk/jobs/thin")
    complete = _vacancy(
        source_url="https://example.ac.uk/jobs/complete",
        description_text=LONG_DESCRIPTION,
        category="Research",
    )
    adapter = _FakeAdapter({thin.source_url: _vacancy(category="Research")})

    results = enrich_missing_details([complete, thin], adapter=adapter, max_fetches=10)

    assert results[0] == complete


def test_a_detail_page_with_nothing_new_leaves_the_listing_untouched() -> None:
    """The detail page can be thin too - an empty top-up changes nothing."""
    thin = _vacancy()
    empty_detail = _vacancy()
    adapter = _FakeAdapter({thin.source_url: empty_detail})

    [result] = enrich_missing_details([thin], adapter=adapter, max_fetches=10)

    assert result == thin


def test_every_detail_fetch_failing_still_returns_the_original_listings() -> None:
    thin = _vacancy()
    adapter = _FakeAdapter({thin.source_url: Blocked("challenge page", url=thin.source_url)})

    results = enrich_missing_details([thin], adapter=adapter, max_fetches=10)

    assert results == [thin]


def test_original_order_is_preserved() -> None:
    first = _vacancy(source_url="https://example.ac.uk/jobs/1")
    second = _vacancy(source_url="https://example.ac.uk/jobs/2")
    adapter = _FakeAdapter(
        {
            first.source_url: _vacancy(category="A"),
            second.source_url: _vacancy(category="B"),
        }
    )

    results = enrich_missing_details([first, second], adapter=adapter, max_fetches=10)

    assert [result.source_url for result in results] == [first.source_url, second.source_url]
