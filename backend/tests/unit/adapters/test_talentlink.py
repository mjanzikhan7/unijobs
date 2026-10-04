"""Talentlink adapter tests, against cached fixtures."""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import pytest
import respx

from crawler.adapters.talentlink import TalentlinkAdapter, _fo_host
from crawler.cache import InMemoryRawCache
from crawler.exceptions import ParseError, RobotsDisallowed
from crawler.extraction import absolutise
from crawler.http import FixtureHttpClient, PoliteHttpClient
from crawler.rate_limit import HostDelayPolicy
from crawler.registry import detect_adapter
from crawler.types import ProbeResult
from institutions.enums import Platform
from tests.unit.adapters.conftest import CAREERS_URL, ref, response

_BANGOR_URL = (
    "https://jobs.bangor.ac.uk/list.php.en?LOV13=All&ContractType=All&LOV25=All&keywords="
    "&Resultsperpage=10&srcsubmit=Search&statlog=1&ID=QLYFK026203F3VBQB7V68LOTX&mask=stdext"
    "&LG=UK"
)


def bangor(html_fixture: Any) -> TalentlinkAdapter:
    """An adapter wired to the marketing page and both pages of the real listing."""
    marketing_html = html_fixture("talentlink/bangor-marketing-page-2026-08-25.html")
    adapter = TalentlinkAdapter(http=FixtureHttpClient(responses={}))
    listing_url = adapter._listing_url(marketing_html, base_url=_BANGOR_URL)
    assert listing_url is not None
    page2_href = (
        "jsoutputinitrapido.cfm?component=lay9999_lst400a&page=jsoutputinitrapido.cfm"
        "&ID=QLYFK026203F3VBQB7V68LOTX&JOBADLG=UK&Resultsperpage=10&lg=UK&mask=stdext"
        "&pagenum=2&option=48&sort=ASC"
    )
    page2_url = absolutise(listing_url, page2_href)

    return TalentlinkAdapter(
        http=FixtureHttpClient(
            responses={
                _BANGOR_URL: response(marketing_html, _BANGOR_URL),
                listing_url: response(
                    html_fixture("talentlink/bangor-listing-page1-2026-08-25.html"), listing_url
                ),
                page2_url: response(
                    html_fixture("talentlink/bangor-listing-page2-2026-08-25.html"), page2_url
                ),
            },
            default=response(html_fixture("talentlink/bangor-detail-2026-08-25.html")),
        )
    )


def test_talentlink_follows_pagination_to_find_every_vacancy(html_fixture: Any) -> None:
    """10 on page 1, 2 on page 2 - the site's own generated page link is what gets page 2."""
    adapter = bangor(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BANGOR_URL))

    assert len(vacancies) == 12


def test_talentlink_never_requests_the_same_detail_page_twice(html_fixture: Any) -> None:
    adapter = bangor(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BANGOR_URL))

    assert len({v.source_url for v in vacancies}) == 12


def test_talentlink_tags_every_vacancy_with_the_institution(html_fixture: Any) -> None:
    adapter = bangor(html_fixture)

    vacancies = adapter.list_vacancies(ref(_BANGOR_URL))

    assert all(v.institution_slug == "university-of-test" for v in vacancies)


def test_talentlink_reads_the_real_detail_page(html_fixture: Any) -> None:
    """The listing carries no salary at all - every field worth screening comes from here."""
    adapter = TalentlinkAdapter(http=FixtureHttpClient(responses={}))
    detail_html = html_fixture("talentlink/bangor-detail-2026-08-25.html")
    detail_url = "https://emea3.recruitmentplatform.com/syndicated/lay/jsoutputinitrapido.cfm?id=1"
    adapter.http = FixtureHttpClient(responses={detail_url: response(detail_html, detail_url)})

    vacancy = adapter.fetch_detail(detail_url)

    assert vacancy.title == "Adjunct Lecturer in Finance (China) – 6 week teaching roles"  # noqa: RUF001
    assert vacancy.department == "The Albert Gubay Business School"
    assert vacancy.reference == "BU04089"
    assert "£18,750" in vacancy.salary_raw
    assert vacancy.grade_raw == "Other"
    assert vacancy.closing_date == date(2026, 8, 26)


def test_talentlink_is_detected_from_the_embedded_widget_script(html_fixture: Any) -> None:
    html = html_fixture("talentlink/bangor-marketing-page-2026-08-25.html")
    probe_result = ProbeResult(url=_BANGOR_URL, status_code=200, html=html, final_url=_BANGOR_URL)

    adapter_class = detect_adapter(ref(_BANGOR_URL), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.TALENTLINK


def test_talentlink_is_detected_from_the_newer_front_office_widget(html_fixture: Any) -> None:
    """Real Imperial College case: a newer, differently-shaped Talentlink widget.

    ``talentlink-fo-host``, not the legacy ``laydisplayrapido.cfm`` syndication script Bangor
    uses. Same vendor (also seen this way at Bristol and UCL), a different embed generation with
    no ``ID=`` query string to read - ``detect()`` must still recognise it as Talentlink rather
    than reporting ``NO_ADAPTER`` for a platform this project already knows.
    """
    html = html_fixture("talentlink/imperial-new-widget-2026-08-25.html")
    imperial_url = "https://www.imperial.ac.uk/jobs/search-jobs/"
    probe_result = ProbeResult(url=imperial_url, status_code=200, html=html, final_url=imperial_url)

    adapter_class = detect_adapter(ref(imperial_url), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.TALENTLINK


def test_talentlink_is_detected_from_the_older_lumesse_fo_host_attribute(html_fixture: Any) -> None:
    """Real Stirling case: the same newer widget, under its pre-rebrand attribute name.

    ``data-lumesse-fo-host`` rather than ``data-talentlink-fo-host`` - Lumesse TalentLink was the
    vendor's name before the rebrand this embed generation is otherwise named for. Confirmed
    NO_ADAPTER in production before this attribute name was recognised, on the same
    ``emea3.recruitmentplatform.com`` host Imperial uses.
    """
    html = html_fixture("talentlink/university-of-stirling-2026-09-04.html")
    stirling_url = "https://www.stir.ac.uk/about/work-at-stirling/list/index.html"
    probe_result = ProbeResult(url=stirling_url, status_code=200, html=html, final_url=stirling_url)

    adapter_class = detect_adapter(ref(stirling_url), probe_result)

    assert adapter_class is not None and adapter_class.platform is Platform.TALENTLINK


def test_talentlink_names_the_newer_widget_it_cannot_yet_read(html_fixture: Any) -> None:
    """Confirmed but unsupported reads honestly, not as "no widget found".

    That would be a stale claim once ``detect()`` recognises the page at all. This exercises the
    fallback path specifically: ``FixtureHttpClient`` has no robots.txt enforcement of its own
    (that lives in ``PoliteHttpClient``, see ``test_http_client.py``), so the live check the
    adapter makes against the widget's own host is not blocked here - proving that even when it
    isn't, the adapter still doesn't understand the JSON API and says so honestly, rather than
    silently returning nothing.
    """
    imperial_url = "https://www.imperial.ac.uk/jobs/search-jobs/"
    fo_rest_url = "https://emea3.recruitmentplatform.com/fo/rest/"
    adapter = TalentlinkAdapter(
        http=FixtureHttpClient(
            responses={
                imperial_url: response(
                    html_fixture("talentlink/imperial-new-widget-2026-08-25.html"), imperial_url
                ),
                fo_rest_url: response("{}", fo_rest_url, content_type="application/json"),
            }
        )
    )

    with pytest.raises(ParseError, match="newer front-office widget"):
        adapter.list_vacancies(ref(imperial_url))


@respx.mock
def test_talentlink_reports_robots_disallowed_for_the_newer_widget(html_fixture: Any) -> None:
    """The real, live case: every confirmed tenant's ``robots.txt`` forbids ``/fo/rest``.

    Unlike every other test in this file, this runs against ``PoliteHttpClient`` rather than
    ``FixtureHttpClient`` - deliberately, because the property under test *is* the robots check,
    which the fixture client does not implement (see ``test_http_client.py``). Proves the crawl
    outcome ends up ``ROBOTS_DISALLOWED``, not ``PARSE_ERROR`` - the distinction between "the
    estate said no" and "this adapter is broken" that the crawl console relies on.
    """
    imperial_url = "https://www.imperial.ac.uk/jobs/search-jobs/"
    imperial_html = html_fixture("talentlink/imperial-new-widget-2026-08-25.html")
    respx.get("https://www.imperial.ac.uk/robots.txt").mock(return_value=httpx.Response(404))
    respx.get(imperial_url).mock(return_value=httpx.Response(200, text=imperial_html))
    respx.get("https://emea3.recruitmentplatform.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /fo/rest\n")
    )

    client = PoliteHttpClient(
        user_agent="HEJobsBot/1.0 (+mailto:test@example.ac.uk)",
        cache=InMemoryRawCache(),
        max_retries=1,
        delay_policy=HostDelayPolicy(min_delay_seconds=0, jitter_seconds=0),
    )
    adapter = TalentlinkAdapter(http=client)

    with pytest.raises(RobotsDisallowed):
        adapter.list_vacancies(ref(imperial_url))


def test_talentlink_reads_the_fo_host_from_the_older_lumesse_attribute(html_fixture: Any) -> None:
    """``_fo_host`` must find Stirling's host under its pre-rebrand attribute name too.

    Without this, ``_reject_newer_widget`` would skip the live robots check entirely (treating
    the host as unrecognised) and fall straight to ``ParseError`` - losing the same
    ``ROBOTS_DISALLOWED`` distinction just proven for Imperial's attribute name.
    """
    html = html_fixture("talentlink/university-of-stirling-2026-09-04.html")

    assert _fo_host(html) == "emea3.recruitmentplatform.com"


def test_a_page_with_no_talentlink_widget_is_not_detected() -> None:
    probe_result = ProbeResult(
        url=CAREERS_URL, status_code=200, html="<p>Vacancies</p>", final_url=CAREERS_URL
    )

    assert TalentlinkAdapter.detect(ref(), probe_result) is False


def test_talentlink_gives_up_loudly_rather_than_paginate_forever(html_fixture: Any) -> None:
    """A malformed site whose ``pagenum`` keeps climbing must not hang the crawl."""
    marketing_html = html_fixture("talentlink/bangor-marketing-page-2026-08-25.html")
    adapter = TalentlinkAdapter(http=FixtureHttpClient(responses={}))
    listing_url = adapter._listing_url(marketing_html, base_url=_BANGOR_URL)
    assert listing_url is not None

    def looping_page(pagenum: int) -> str:
        next_num = pagenum + 1
        return (
            '<a class="lstA-desc1" href="jsoutputinitrapido.cfm?component=lay9999_jdesc100a'
            f'&id=x&nPostingID={pagenum}&nPostingTargetID={pagenum}">Job {pagenum}</a>'
            f'<a class="Lst-NavPage" href="jsoutputinitrapido.cfm?pagenum={next_num}">Next</a>'
        )

    responses = {
        _BANGOR_URL: response(marketing_html, _BANGOR_URL),
        listing_url: response(looping_page(1), listing_url),
    }
    for pagenum in range(2, 300):
        url = absolutise(listing_url, f"jsoutputinitrapido.cfm?pagenum={pagenum}")
        responses[url] = response(looping_page(pagenum), url)

    adapter = TalentlinkAdapter(http=FixtureHttpClient(responses=responses))

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref(_BANGOR_URL))
