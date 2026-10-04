"""iTrent adapter tests, against cached fixtures."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from crawler.adapters.itrent import ITrentAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.http import FixtureHttpClient
from crawler.registry import detect_adapter
from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import ref, response

_ITRENT_BASE = "https://jobs.napier.ac.uk/mthrprod_webrecruitment"
_ITRENT_OPEN_URL = f"{_ITRENT_BASE}/wrd/run/ETREC179GF.open?WVID=150547JMmr"
_ITRENT_SESSION = "67B3DCE8F791E491801EFA63685AAA3F"
_ITRENT_JSON_URL = (
    f"{_ITRENT_BASE}/wrd/run/ETREC106GF.json?WVID=150547JMmr"
    f"&USESSION={_ITRENT_SESSION}&LANG=USA&RESULTS_PP=200"
)


def itrent_pinned(html_fixture: Any) -> ITrentAdapter:
    """An adapter whose careers URL already names a live web view."""
    return ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                _ITRENT_OPEN_URL: response(
                    html_fixture("itrent/napier-search-2026-08-24.html"), _ITRENT_OPEN_URL
                ),
                _ITRENT_JSON_URL: response(
                    html_fixture("itrent/napier-results-2026-08-24.json"),
                    _ITRENT_JSON_URL,
                    content_type="application/json",
                ),
            }
        )
    )


@pytest.mark.parametrize(
    ("careers_url", "expected"),
    [
        (
            "https://jobs.napier.ac.uk/mthrprod_webrecruitment/wrd/run/ETREC179GF.open?WVID=1",
            "https://jobs.napier.ac.uk/mthrprod_webrecruitment",
        ),
        (
            "https://ce0309li.webitrent.com/ce0309li_webrecruitment/",
            "https://ce0309li.webitrent.com/ce0309li_webrecruitment",
        ),
    ],
)
def test_itrent_finds_the_tenant_base_from_the_webrecruitment_segment(
    careers_url: str, expected: str
) -> None:
    assert ITrentAdapter._tenant_base(careers_url) == expected


def test_itrent_rejects_a_url_with_no_webrecruitment_segment() -> None:
    with pytest.raises(ParseError):
        ITrentAdapter._tenant_base("https://example.ac.uk/jobs")


def test_itrent_reads_every_vacancy_from_a_pinned_web_view(html_fixture: Any) -> None:
    adapter = itrent_pinned(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    assert len(vacancies) == 6
    assert vacancies[0].title == "Lecturer in Cyber Security and Systems Engineering"


def test_itrent_records_the_json_api_strategy(html_fixture: Any) -> None:
    adapter = itrent_pinned(html_fixture)

    adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    assert adapter.strategy is ExtractionStrategy.JSON_API


def test_itrent_builds_absolute_vacancy_urls(html_fixture: Any) -> None:
    adapter = itrent_pinned(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    assert all(item.source_url.startswith(_ITRENT_BASE) for item in vacancies)


def test_itrent_source_url_does_not_depend_on_this_crawls_own_session(html_fixture: Any) -> None:
    """The upsert key is ``(institution, source_url)``.

    ``USESSION`` is minted fresh on every visit to the search page. A ``source_url`` built from
    it would make every vacancy look like a different one on every crawl - closed and reopened
    every run - which is exactly the bug this pins down.
    """
    base_html = html_fixture("itrent/napier-search-2026-08-24.html")
    other_session = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    other_session_html = base_html.replace(_ITRENT_SESSION, other_session)
    other_json_url = (
        f"{_ITRENT_BASE}/wrd/run/ETREC106GF.json?WVID=150547JMmr"
        f"&USESSION={other_session}&LANG=USA&RESULTS_PP=200"
    )
    results_json = html_fixture("itrent/napier-results-2026-08-24.json")

    first = itrent_pinned(html_fixture)
    second = ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                _ITRENT_OPEN_URL: response(other_session_html, _ITRENT_OPEN_URL),
                other_json_url: response(
                    results_json, other_json_url, content_type="application/json"
                ),
            }
        )
    )

    first_urls = [v.source_url for v in first.list_vacancies(ref(_ITRENT_OPEN_URL))]
    second_urls = [v.source_url for v in second.list_vacancies(ref(_ITRENT_OPEN_URL))]

    assert first_urls == second_urls


def test_itrent_keeps_the_salary_string_exactly_as_advertised(html_fixture: Any) -> None:
    adapter = itrent_pinned(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    assert vacancies[0].salary_raw == "£46,049 p/a - £58,225 (depending on experience)"


def test_itrent_parses_the_yyyymmdd_closing_date(html_fixture: Any) -> None:
    adapter = itrent_pinned(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    assert vacancies[0].closing_date == date(2026, 9, 17)


def test_itrent_leaves_an_unset_closing_date_as_none_rather_than_guessing(
    html_fixture: Any,
) -> None:
    """The fourth Napier vacancy in the fixture has no ``app_close_d``."""
    adapter = itrent_pinned(html_fixture)

    vacancies = adapter.list_vacancies(ref(_ITRENT_OPEN_URL))

    coordinator = next(v for v in vacancies if "Programme Support Coordinator" in v.title)
    assert coordinator.closing_date is None


def test_itrent_discovers_a_live_web_view_when_the_careers_url_is_just_the_tenant_root(
    html_fixture: Any,
) -> None:
    """A marketing page's own link often has no ``WVID`` at all, just the tenant root.

    The adapter re-derives a live web view via the tenant's default redirect rather than
    guessing, which is what keeps it working after the institution's HR team rotates one.
    """
    base = "https://ce0309li.webitrent.com/ce0309li_webrecruitment"
    discovery_url = f"{base}/wrd/run/etrec002gf.open"
    open_url = f"{base}/wrd/run/etrec179gf.open?WVID=4121641WJu"
    json_url = (
        f"{base}/wrd/run/ETREC106GF.json?WVID=4121641WJu"
        f"&USESSION={_ITRENT_SESSION}&LANG=USA&RESULTS_PP=200"
    )
    adapter = ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                discovery_url: response(
                    html_fixture("itrent/leeds-trinity-landing-2026-08-24.html"), discovery_url
                ),
                open_url: response(html_fixture("itrent/napier-search-2026-08-24.html"), open_url),
                json_url: response(
                    html_fixture("itrent/napier-results-2026-08-24.json"),
                    json_url,
                    content_type="application/json",
                ),
            }
        )
    )

    vacancies = adapter.list_vacancies(ref(f"{base}/"))

    assert len(vacancies) == 6


def test_itrent_reads_a_search_page_that_also_carries_a_maintenance_notice(
    html_fixture: Any,
) -> None:
    """Real Huddersfield case: a maintenance page, but the other way round.

    The search page still minted a live session and full JSON results, but its own template
    permanently carries a banner about a scheduled future maintenance window ("will be
    unavailable from 15:45 - 18:45 on Wednesday..."). A page that hands out a real, fresh
    ``USESSION`` is not the "whole site is down" holding
    page the maintenance guard exists for - that page never gets that far. Treating the banner
    as fatal here would report a live, working tenant as ``OFFLINE`` on every single crawl.
    """
    base = "https://vacancies.hud.ac.uk/tlive_webrecruitment"
    open_url = f"{base}/wrd/run/etrec179gf.open?WVID=2486049XkB"
    json_url = (
        f"{base}/wrd/run/ETREC106GF.json?WVID=2486049XkB"
        f"&USESSION=D8D05292B462E63CE2DD2238EC47F03A&LANG=USA&RESULTS_PP=200"
    )
    adapter = ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                open_url: response(
                    html_fixture(
                        "itrent/huddersfield-search-with-maintenance-banner-2026-08-25.html"
                    ),
                    open_url,
                ),
                json_url: response(
                    html_fixture("itrent/napier-results-2026-08-24.json"),
                    json_url,
                    content_type="application/json",
                ),
            }
        )
    )

    vacancies = adapter.list_vacancies(ref(open_url))

    assert len(vacancies) == 6


def test_itrent_raises_rather_than_trusting_a_stale_pinned_web_view(html_fixture: Any) -> None:
    """A pasted ``WVID`` can be out of date.

    A copied-and-pasted ``WVID`` can be stale; iTrent answers with an in-page error, not a
    missing session, so the adapter must read the page rather than just checking for one.
    """
    stale = html_fixture("itrent/napier-search-2026-08-24.html").replace(
        "Working at Edinburgh Napier",
        "A possible security violation has been detected on displaying this page.",
    )
    adapter = ITrentAdapter(
        http=FixtureHttpClient(responses={_ITRENT_OPEN_URL: response(stale, _ITRENT_OPEN_URL)})
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_ITRENT_OPEN_URL))


def test_itrent_raises_when_the_json_endpoint_stops_returning_json(html_fixture: Any) -> None:
    adapter = ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                _ITRENT_OPEN_URL: response(
                    html_fixture("itrent/napier-search-2026-08-24.html"), _ITRENT_OPEN_URL
                ),
                _ITRENT_JSON_URL: response(
                    "<html><body>Page Not Found</body></html>", _ITRENT_JSON_URL
                ),
            }
        )
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_ITRENT_OPEN_URL))


def test_itrent_raises_rather_than_silently_truncating_a_list_page_size_did_not_cover(
    html_fixture: Any,
) -> None:
    truncated = json.dumps({"search": {"total_rec": 999}, "results": [{"job_title": "x"}]})
    adapter = ITrentAdapter(
        http=FixtureHttpClient(
            responses={
                _ITRENT_OPEN_URL: response(
                    html_fixture("itrent/napier-search-2026-08-24.html"), _ITRENT_OPEN_URL
                ),
                _ITRENT_JSON_URL: response(truncated, _ITRENT_JSON_URL),
            }
        )
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_ITRENT_OPEN_URL))


def test_itrent_is_detected_from_the_webrecruitment_path_alone() -> None:
    """The search page is a client-rendered shell; the path is the only reliable signal."""
    url = "https://jobs.napier.ac.uk/mthrprod_webrecruitment/wrd/run/ETREC179GF.open?WVID=1"
    institution_ref = InstitutionRef(slug="napier", name="Napier", careers_url=url)
    probe_result = ProbeResult(
        url=url, status_code=200, html="<html><body>Loading…</body></html>", final_url=url
    )

    adapter_class = detect_adapter(institution_ref, probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.ITRENT


def test_itrent_is_not_detected_from_an_unrelated_mention_of_the_product_name() -> None:
    """An unrelated internal link can mention the product name too.

    A university's own HR intranet can link to "iTrent" - their internal payroll system - from
    a page that has nothing to do with the public vacancy portal. Real case: Strathclyde's
    careers page has a nav-menu link to
    ``/professionalservices/hr/itrent-hrpayrollsystem/``, titled "itrent". A bare substring
    check matched it and sent the crawl down a path with no real tenant URL to resolve,
    reporting a confusing ``PARSE_ERROR`` for an institution that was never on this platform.
    """
    url = "https://www.strath.ac.uk/workwithus/vacancies/"
    institution_ref = InstitutionRef(slug="strathclyde", name="Strathclyde", careers_url=url)
    html = (
        '<html><body><nav><a href="/professionalservices/hr/itrent-hrpayrollsystem/">'
        "itrent</a></nav></body></html>"
    )
    probe_result = ProbeResult(url=url, status_code=200, html=html, final_url=url)

    adapter_class = detect_adapter(institution_ref, probe_result)

    assert adapter_class is None or adapter_class.platform is not Platform.ITRENT
