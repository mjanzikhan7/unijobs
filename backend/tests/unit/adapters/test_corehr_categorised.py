"""CoreHR, categorised adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

from crawler.adapters.corehr_categorised import CoreHRCategorisedAdapter
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_OXFORD_URL = "https://www.ox.ac.uk/about/jobs"
_OXFORD_AC_URL = (
    "https://my.corehr.com/pls/uoxrecruit/erq_search_version_4.start_search_with_params"
    "?p_company=10&p_internal_external=E&p_display_in_irish=N&p_competition_type=AC&p_force_type=E"
)
_OXFORD_RE_URL = (
    "https://my.corehr.com/pls/uoxrecruit/erq_search_version_4.start_search_with_params"
    "?p_company=10&p_internal_external=E&p_display_in_irish=N&p_competition_type=RE&p_force_type=E"
)
_OXFORD_PS_URL = (
    "https://my.corehr.com/pls/uoxrecruit/erq_search_version_4.start_search_with_params"
    "?p_company=10&p_internal_external=E&p_display_in_irish=N&p_competition_type=PM"
    "&p_competition_type=ST&p_force_type=E"
)


def oxford(html_fixture: Any) -> CoreHRCategorisedAdapter:
    """An adapter wired to the marketing page and all three category result pages."""
    return CoreHRCategorisedAdapter(
        http=FixtureHttpClient(
            responses={
                _OXFORD_URL: response(
                    html_fixture("corehr_categorised/oxford-marketing-page-2026-08-24.html"),
                    _OXFORD_URL,
                ),
                _OXFORD_AC_URL: response(
                    html_fixture("corehr_categorised/oxford-academic-2026-08-24.html"),
                    _OXFORD_AC_URL,
                ),
                _OXFORD_RE_URL: response(
                    html_fixture("corehr_categorised/oxford-research-2026-08-24.html"),
                    _OXFORD_RE_URL,
                ),
                _OXFORD_PS_URL: response(
                    html_fixture("corehr_categorised/oxford-professional-services-2026-08-24.html"),
                    _OXFORD_PS_URL,
                ),
            }
        )
    )


def test_corehr_categorised_merges_every_category(html_fixture: Any) -> None:
    """2 Academic + 1 Research + 1 Professional Services, from three separate requests."""
    adapter = oxford(html_fixture)

    vacancies = adapter.list_vacancies(ref(_OXFORD_URL))

    assert len(vacancies) == 4


def test_corehr_categorised_tags_each_vacancy_with_its_search_category(html_fixture: Any) -> None:
    adapter = oxford(html_fixture)

    vacancies = adapter.list_vacancies(ref(_OXFORD_URL))

    by_title = {v.title: v.category for v in vacancies}
    assert (
        by_title[
            "Astrophoria Foundation Year Preparation for Undergraduate Studies Teaching Associate"
        ]
        == "Academic"
    )
    assert by_title["Postdoctoral Research Assistant in Islamic Art"] == "Research"
    assert by_title["Finance Coordinator"] == "Professional Services"


def test_corehr_categorised_reads_the_real_row_shape(html_fixture: Any) -> None:
    """A nested table with a ``javascript:`` link, not a plain ``<a href>``.

    :class:`CoreHRAdapter`'s generic row scan cannot read it at all, which is the whole reason
    this adapter has its own ``_parse``.
    """
    adapter = oxford(html_fixture)

    vacancies = adapter.list_vacancies(ref(_OXFORD_URL))

    finance = next(v for v in vacancies if v.title == "Finance Coordinator")
    assert finance.salary_raw == "£31,459 - £36,616"
    assert finance.grade_raw == "STANDARD GRADE 5"
    assert finance.closing_date == date(2026, 10, 18)
    assert finance.source_url.startswith("https://my.corehr.com/pls/uoxrecruit/")
    assert "190500" in finance.source_url


_OXFORD_RE_NEXT_PAGE_URL = (
    "https://my.corehr.com/pls/uoxrecruit/erq_search_version_4.start_search_with_params"
)


def test_corehr_categorised_follows_a_search_past_its_first_page(html_fixture: Any) -> None:
    """Real Oxford Research page 1: "Displaying 1 to 100 of 102" - page 2 holds the other two.

    The 100-row cap is not a fixed vacancy count, it is CoreHR's own page size, and its
    ordering is not stable between crawls - leaving page 2 unfetched does not just under-count
    once, it makes a different couple of still-open vacancies fall out of ``seen_urls`` on
    every run, closing real jobs. See the module docstring.
    """
    adapter = CoreHRCategorisedAdapter(
        http=FixtureHttpClient(
            responses={
                _OXFORD_RE_URL: response(
                    html_fixture("corehr_categorised/oxford-research-page1-2026-08-25.html"),
                    _OXFORD_RE_URL,
                ),
                _OXFORD_RE_NEXT_PAGE_URL: response(
                    html_fixture("corehr_categorised/oxford-research-page2-2026-08-25.html"),
                    _OXFORD_RE_NEXT_PAGE_URL,
                ),
            }
        )
    )

    first = adapter.http.get(_OXFORD_RE_URL)

    pages = adapter._paginate(first.text, first.url or _OXFORD_RE_URL)
    all_vacancies = [
        v for html, base_url in pages for v in adapter._parse(html, ref(), base_url=base_url)
    ]

    assert len(pages) == 2
    assert len(all_vacancies) == 102


def test_corehr_categorised_stops_paging_when_a_page_carries_no_summary(
    html_fixture: Any,
) -> None:
    """A fixture trimmed down to its rows, with no "Displaying" line, is treated as complete."""
    adapter = oxford(html_fixture)
    first = adapter.http.get(_OXFORD_AC_URL)

    pages = adapter._paginate(first.text, first.url or _OXFORD_AC_URL)

    assert len(pages) == 1


def test_corehr_categorised_is_detected_from_two_or_more_category_links(
    html_fixture: Any,
) -> None:
    html = html_fixture("corehr_categorised/oxford-marketing-page-2026-08-24.html")
    probe_result = ProbeResult(url=_OXFORD_URL, status_code=200, html=html, final_url=_OXFORD_URL)
    ref_ = InstitutionRef(slug="oxford", name="Oxford", careers_url=_OXFORD_URL)

    adapter_class = detect_adapter(ref_, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.COREHR_CATEGORISED


def test_a_single_categorised_link_is_not_enough_to_claim_the_tenant() -> None:
    """One categorised link is ambiguous with an ordinary single-search CoreHR tenant."""
    html = (
        '<a href="https://my.corehr.com/pls/x/erq_search_version_4.start_search_with_params'
        '?p_competition_type=AC">Academic jobs</a>'
    )
    probe_result = ProbeResult(url=_OXFORD_URL, status_code=200, html=html, final_url=_OXFORD_URL)
    ref_ = InstitutionRef(slug="test", name="Test", careers_url=_OXFORD_URL)

    adapter_class = detect_adapter(ref_, probe_result)

    assert adapter_class is None or adapter_class.platform is not Platform.COREHR_CATEGORISED
