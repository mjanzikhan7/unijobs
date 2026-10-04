"""Structured data (JSON-LD/RSS) adapter tests, against cached fixtures."""

from __future__ import annotations

import json
from typing import Any

import pytest

from crawler.adapters.structured import StructuredDataAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import ParseError
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import CAREERS_URL, ref, response


def test_json_ld_is_used_when_present(html_fixture: Any) -> None:
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("jsonld/example-jobposting-2026-08-23.html")),
        )
    )

    assert len(adapter.list_vacancies(ref())) == 3


def test_the_json_ld_strategy_is_recorded(html_fixture: Any) -> None:
    """Recording it is how a site that gains JSON-LD later gets noticed and upgraded."""
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("jsonld/example-jobposting-2026-08-23.html")),
        )
    )

    adapter.list_vacancies(ref())

    assert adapter.strategy is ExtractionStrategy.JSON_LD


def test_json_ld_salary_is_rendered_back_into_an_advert_style_string(
    html_fixture: Any,
) -> None:
    """One input format for the salary parser, whatever the source."""
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("jsonld/example-jobposting-2026-08-23.html")),
        )
    )

    vacancies = adapter.list_vacancies(ref())

    assert vacancies[0].salary_raw == "£38,784 to £46,049 per year"


def test_json_ld_carries_the_closing_date(html_fixture: Any) -> None:
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={},
            default=response(html_fixture("jsonld/example-jobposting-2026-08-23.html")),
        )
    )

    vacancies = adapter.list_vacancies(ref())

    assert all(item.closing_date is not None for item in vacancies)


def test_an_rss_feed_is_used_when_there_is_no_json_ld(html_fixture: Any) -> None:
    """RSS is dramatically more stable than the markup around it."""
    feed_url = "https://jobs.test.ac.uk/jobs/feed.xml"
    page = (
        '<html><head><link rel="alternate" type="application/rss+xml" href="/jobs/feed.xml">'
        "</head><body><h1>Vacancies</h1></body></html>"
    )
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={
                CAREERS_URL: response(page),
                feed_url: response(
                    html_fixture("rss/example-feed-2026-08-23.xml"),
                    feed_url,
                    content_type="application/rss+xml",
                ),
            }
        )
    )

    assert len(adapter.list_vacancies(ref())) == 4


def test_the_rss_strategy_is_recorded(html_fixture: Any) -> None:
    feed_url = "https://jobs.test.ac.uk/jobs/feed.xml"
    page = (
        '<html><head><link rel="alternate" type="application/rss+xml" href="/jobs/feed.xml">'
        "</head><body><h1>Vacancies</h1></body></html>"
    )
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={
                CAREERS_URL: response(page),
                feed_url: response(
                    html_fixture("rss/example-feed-2026-08-23.xml"),
                    feed_url,
                    content_type="application/rss+xml",
                ),
            }
        )
    )

    adapter.list_vacancies(ref())

    assert adapter.strategy is ExtractionStrategy.RSS


def test_a_site_wide_feed_is_not_mistaken_for_a_jobs_feed() -> None:
    """A site-wide feed parses through the same code path as a jobs feed.

    Same ``<item>``/``<title>``/``<link>`` shape - but carries news and events, not vacancies.
    Real case: a conservatoire's careers page advertised only its site-wide feed, whose items
    included "Acid Casuals celebrate 20 years of Omni" - which this adapter, before this test
    was written, would have listed as a job opening.
    """
    feed_url = "https://jobs.test.ac.uk/feed.xml"
    page = (
        '<html><head><link rel="alternate" type="application/rss+xml" href="/feed.xml">'
        "</head><body><h1>Careers</h1></body></html>"
    )
    site_wide_feed = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <title>University of Test</title>
      <description>The main RSS feed for University of Test</description>
      <item>
        <title>Acid Casuals celebrate 20 years of Omni</title>
        <link>https://jobs.test.ac.uk/events/acid-casuals</link>
        <pubDate>Fri, 14 Aug 2026 09:55:00 +0100</pubDate>
      </item>
    </channel></rss>"""
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={
                CAREERS_URL: response(page),
                feed_url: response(site_wide_feed, feed_url, content_type="application/rss+xml"),
            }
        )
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref())


def test_a_page_that_lost_its_structured_data_raises_rather_than_reporting_zero() -> None:
    """Detection said there was JSON-LD. Its disappearance is a change, not an empty estate."""
    adapter = StructuredDataAdapter(
        http=FixtureHttpClient(
            responses={}, default=response("<html><body><h1>Vacancies</h1></body></html>")
        )
    )

    with pytest.raises(ParseError):
        adapter.list_vacancies(ref())


def test_a_malformed_json_ld_block_costs_one_advert_not_the_institution() -> None:
    """One broken advert in a listing of forty should cost one advert."""
    good = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Research Fellow",
            "url": "https://jobs.test.ac.uk/vacancy/1",
        }
    )
    page = (
        "<html><head>"
        '<script type="application/ld+json">{not valid json</script>'
        f'<script type="application/ld+json">{good}</script>'
        "</head><body>Vacancies</body></html>"
    )
    adapter = StructuredDataAdapter(http=FixtureHttpClient(responses={}, default=response(page)))

    assert len(adapter.list_vacancies(ref())) == 1
