"""The shared adapter contract suite.

Every registered adapter is parameterised through this file. Adding an adapter without it
appearing here is not possible: the suite reads the registry, so a new adapter is covered the
moment it is imported.

The contract every adapter owes its caller:

* returns ``list[RawVacancy]`` or raises a typed ``AdapterError`` - never ``None``, never a bare
  ``Exception``, never a silently-empty list on failure;
* populates ``title``, ``source_url`` and ``institution`` on every item;
* is idempotent - the same fixture twice gives identical output;
* reports which extraction strategy it used.
"""

from __future__ import annotations

from typing import Any

import pytest

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import AdapterError
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter, registered_adapters
from crawler.types import FetchResponse, InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

ADAPTERS = sorted(registered_adapters().items(), key=lambda item: item[0].value)
ADAPTER_IDS = [platform.value for platform, _ in ADAPTERS]


def response(text: str, url: str = "https://jobs.test.ac.uk/jobs", **kwargs: Any) -> FetchResponse:
    """Build a fixture response."""
    return FetchResponse(
        url=url,
        status_code=kwargs.pop("status_code", 200),
        text=text,
        headers={"content-type": kwargs.pop("content_type", "text/html")},
    )


def institution(slug: str = "university-of-test") -> InstitutionRef:
    """An institution reference pointing at the fixture URL."""
    return InstitutionRef(
        slug=slug, name="University of Test", careers_url="https://jobs.test.ac.uk/jobs"
    )


def probe(html: str, url: str = "https://jobs.test.ac.uk/jobs") -> ProbeResult:
    """A probe of the careers page."""
    return ProbeResult(url=url, status_code=200, html=html, final_url=url)


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_declares_its_platform(platform: Platform, adapter_class: type) -> None:
    assert adapter_class.platform is platform


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_subclasses_the_shared_base(platform: Platform, adapter_class: type) -> None:
    """Inheriting the base is what guarantees the maintenance and block guards run."""
    assert issubclass(adapter_class, BaseAdapter)


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_raises_a_typed_error_when_the_site_is_unreachable(
    platform: Platform, adapter_class: type
) -> None:
    """Never ``None``, never a bare ``Exception``, never a silent empty list."""
    adapter = adapter_class(http=FixtureHttpClient(responses={}))

    with pytest.raises(AdapterError):
        adapter.list_vacancies(institution())


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_raises_rather_than_returning_none_on_a_maintenance_page(
    platform: Platform, adapter_class: type, html_fixture: Any
) -> None:
    """A holding page is OFFLINE. Returning an empty list would let the differ act on it."""
    maintenance = html_fixture("stonefish/surrey-maintenance-2026-08-23.html")
    adapter = adapter_class(http=FixtureHttpClient(responses={}, default=response(maintenance)))

    with pytest.raises(AdapterError):
        adapter.list_vacancies(institution())


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_starts_with_a_strategy_it_can_report(
    platform: Platform, adapter_class: type
) -> None:
    """The strategy lands on the crawl result, so a site that gains JSON-LD is visible."""
    adapter = adapter_class(http=FixtureHttpClient(responses={}))

    assert isinstance(adapter.strategy, ExtractionStrategy)


@pytest.mark.parametrize(("platform", "adapter_class"), ADAPTERS, ids=ADAPTER_IDS)
def test_every_adapter_reports_no_fallback_until_one_fires(
    platform: Platform, adapter_class: type
) -> None:
    adapter = adapter_class(http=FixtureHttpClient(responses={}))

    assert adapter.fallback_fired is False


PRODUCING_CASES: list[tuple[str, str, str]] = [
    ("STONEFISH", "stonefish/bath-2026-08-23.html", "https://jobs.test.ac.uk/jobs"),
    ("STRUCTURED", "jsonld/example-jobposting-2026-08-23.html", "https://jobs.test.ac.uk/jobs"),
    (
        "JOBTRAIN",
        "jobtrain/manchester-rendered-2026-08-23.html",
        "https://jobs.test.ac.uk/jobs",
    ),
    ("COREHR", "corehr/sheffield-hallam-results-2026-08-25.html", "https://jobs.test.ac.uk/jobs"),
    ("EPLOY", "eploy/cardiff-page1-2026-08-25.html", "https://jobs.test.ac.uk/jobs"),
]


def build(platform_value: str, fixture_html: str, url: str) -> tuple[BaseAdapter, InstitutionRef]:
    """Build an adapter wired to a single fixture response.

    Served as the client's default rather than keyed on the URL, because some adapters rewrite
    the careers URL before fetching - Stonefish goes to ``vacancies.aspx?cat=-1`` - and the
    contract suite is about output shape, not about URL construction.
    """
    adapter_class = registered_adapters()[Platform(platform_value)]
    client = FixtureHttpClient(responses={}, default=response(fixture_html, url))
    return adapter_class(http=client), institution()


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_every_item_carries_a_title(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    adapter, ref = build(platform_value, html_fixture(fixture_path), url)

    vacancies = adapter.list_vacancies(ref)

    assert all(item.title.strip() for item in vacancies)


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_every_item_carries_an_absolute_source_url(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    """A vacancy that cannot be opened is not a vacancy."""
    adapter, ref = build(platform_value, html_fixture(fixture_path), url)

    vacancies = adapter.list_vacancies(ref)

    assert all(item.source_url.startswith("http") for item in vacancies)


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_every_item_carries_its_institution(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    adapter, ref = build(platform_value, html_fixture(fixture_path), url)

    vacancies = adapter.list_vacancies(ref)

    assert all(item.institution_slug == ref.slug for item in vacancies)


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_parsing_the_same_fixture_twice_gives_identical_output(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    """Idempotence: crawling the same institution twice produces the same rows."""
    html = html_fixture(fixture_path)
    first_adapter, ref = build(platform_value, html, url)
    second_adapter, _ = build(platform_value, html, url)

    assert first_adapter.list_vacancies(ref) == second_adapter.list_vacancies(ref)


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_every_adapter_returns_a_plain_list(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    adapter, ref = build(platform_value, html_fixture(fixture_path), url)

    result = adapter.list_vacancies(ref)

    assert isinstance(result, list)


@pytest.mark.parametrize(
    ("platform_value", "fixture_path", "url"),
    PRODUCING_CASES,
    ids=[case[0] for case in PRODUCING_CASES],
)
def test_every_item_is_a_raw_vacancy(
    platform_value: str, fixture_path: str, url: str, html_fixture: Any
) -> None:
    adapter, ref = build(platform_value, html_fixture(fixture_path), url)

    result = adapter.list_vacancies(ref)

    assert all(isinstance(item, RawVacancy) for item in result)


DETECTION_CASES: list[tuple[str, str, Platform]] = [
    ("stonefish/bath-2026-08-23.html", "https://www.bath.ac.uk/jobs/", Platform.STONEFISH),
    (
        "jobtrain/manchester-2026-08-23.html",
        "https://www.jobs.manchester.ac.uk/Home/Job",
        Platform.JOBTRAIN,
    ),
    (
        "corehr/oxford-2026-08-23.html",
        "https://my.corehr.com/pls/uoxrecruit/erq_search_version_4.start_search",
        Platform.COREHR,
    ),
    (
        "eploy/cranfield-empty-2026-08-23.html",
        "https://cranfield.eploy.net/vacancies/",
        Platform.EPLOY,
    ),
    (
        "jsonld/example-jobposting-2026-08-23.html",
        "https://jobs.example.ac.uk/vacancies",
        Platform.STRUCTURED,
    ),
]


@pytest.mark.parametrize(
    ("fixture_path", "url", "expected"),
    DETECTION_CASES,
    ids=[case[2].value for case in DETECTION_CASES],
)
def test_detection_picks_the_right_adapter(
    fixture_path: str, url: str, expected: Platform, html_fixture: Any
) -> None:
    ref = InstitutionRef(slug="test", name="Test", careers_url=url)

    adapter_class = detect_adapter(ref, probe(html_fixture(fixture_path), url))

    assert adapter_class is not None and adapter_class.platform is expected


def test_a_workday_host_is_detected_from_the_url_alone() -> None:
    """Workday's UI is a JavaScript shell; the host is the only reliable signal."""
    url = "https://lse.wd3.myworkdayjobs.com/en-US/LSEJobs"
    ref = InstitutionRef(slug="lse", name="LSE", careers_url=url)

    adapter_class = detect_adapter(ref, probe("<html><body>Loading…</body></html>", url))

    assert adapter_class is not None and adapter_class.platform is Platform.WORKDAY


def test_an_unrecognisable_portal_returns_no_adapter() -> None:
    """Guessing an adapter would produce a confident, wrong, empty result."""
    ref = InstitutionRef(slug="test", name="Test", careers_url="https://example.com/about/contact")

    assert detect_adapter(ref, probe("<html><body>Contact us</body></html>")) is None


def test_the_generic_adapter_never_outranks_a_specific_one(html_fixture: Any) -> None:
    """A Stonefish tenant that also publishes JSON-LD is still crawled as Stonefish.

    The specific adapter knows about department grouping and the ``cat=-1`` listing URL, which
    generic extraction does not.
    """
    stonefish = html_fixture("stonefish/bath-2026-08-23.html")
    jsonld = html_fixture("jsonld/example-jobposting-2026-08-23.html")
    injected = jsonld.split("<head>")[1].split("</head>")[0]
    combined = stonefish.replace("</head>", injected + "</head>")
    ref = InstitutionRef(slug="bath", name="Bath", careers_url="https://www.bath.ac.uk/jobs/")

    adapter_class = detect_adapter(ref, probe(combined, ref.careers_url))

    assert adapter_class is not None and adapter_class.platform is Platform.STONEFISH
