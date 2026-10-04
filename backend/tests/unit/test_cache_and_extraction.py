"""The raw response cache and the extraction helpers.

The cache lets us replay an adapter against the exact bytes behind a bad parse, so its keys are
tested closely.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from crawler.cache import DiskRawCache, InMemoryRawCache, cache_key
from crawler.extraction import (
    absolutise,
    extract_jsonld_jobpostings,
    extract_meta_description,
    extract_organisation_description,
    find_rss_link,
    html_to_text,
    looks_blocked,
    looks_like_a_jobs_feed,
    looks_like_maintenance,
    looks_like_vacancy_link,
    parse_uk_date,
)


def test_the_same_url_and_body_produce_the_same_key() -> None:
    """Content-addressed: an unchanged page fetched nightly occupies one file, not ninety."""
    assert cache_key("https://a.ac.uk/jobs", "<html>x</html>") == cache_key(
        "https://a.ac.uk/jobs", "<html>x</html>"
    )


def test_a_changed_body_produces_a_different_key() -> None:
    """So a changed page never overwrites the version that produced yesterday's parse."""
    assert cache_key("https://a.ac.uk/jobs", "<html>x</html>") != cache_key(
        "https://a.ac.uk/jobs", "<html>y</html>"
    )


def test_the_same_body_from_different_urls_produces_different_keys() -> None:
    assert cache_key("https://a.ac.uk/jobs", "x") != cache_key("https://b.ac.uk/jobs", "x")


def test_a_stored_body_can_be_read_back(tmp_path: Path) -> None:
    cache = DiskRawCache(root=tmp_path)

    entry = cache.store("https://a.ac.uk/jobs", "<html>hello</html>")

    assert cache.load(entry.key) == "<html>hello</html>"


def test_a_missing_key_reads_back_as_nothing(tmp_path: Path) -> None:
    """A pruned body is absent, not an exception."""
    assert DiskRawCache(root=tmp_path).load("does-not-exist") is None


def test_storing_records_the_body_size(tmp_path: Path) -> None:
    cache = DiskRawCache(root=tmp_path)

    entry = cache.store("https://a.ac.uk/jobs", "hello")

    assert entry.byte_size == 5


def test_pruning_removes_bodies_past_the_ttl(tmp_path: Path) -> None:
    cache = DiskRawCache(root=tmp_path)
    entry = cache.store("https://a.ac.uk/jobs", "old")
    ancient = time.time() - (100 * 86400)
    import os

    os.utime(entry.path, (ancient, ancient))

    removed = cache.prune(older_than_days=90)

    assert removed == 1


def test_pruning_keeps_recent_bodies(tmp_path: Path) -> None:
    cache = DiskRawCache(root=tmp_path)
    cache.store("https://a.ac.uk/jobs", "fresh")

    assert DiskRawCache(root=tmp_path).prune(older_than_days=90) == 0


def test_pruning_an_empty_cache_is_harmless(tmp_path: Path) -> None:
    assert DiskRawCache(root=tmp_path / "nothing-here").prune(older_than_days=90) == 0


def test_the_in_memory_cache_round_trips() -> None:
    cache = InMemoryRawCache()

    entry = cache.store("https://a.ac.uk/jobs", "body")

    assert cache.load(entry.key) == "body"


def test_the_in_memory_cache_reports_a_missing_key() -> None:
    assert InMemoryRawCache().load("nope") is None


def test_scripts_and_styles_are_stripped_from_advert_text() -> None:
    """The exclusion matcher reads this text; a stray script would poison it."""
    html = "<div><script>var x=1</script><style>p{}</style><p>Hello</p></div>"

    assert html_to_text(html) == "Hello"


def test_block_structure_becomes_line_breaks() -> None:
    assert html_to_text("<p>One</p><p>Two</p>") == "One\nTwo"


def test_empty_html_is_empty_text() -> None:
    assert html_to_text("") == ""


@pytest.mark.parametrize(
    ("base", "href", "expected"),
    [
        ("https://a.ac.uk/jobs/", "vacancy/1", "https://a.ac.uk/jobs/vacancy/1"),
        ("https://a.ac.uk/jobs/", "/vacancy/1", "https://a.ac.uk/vacancy/1"),
        ("https://a.ac.uk/jobs/", "https://b.ac.uk/x", "https://b.ac.uk/x"),
    ],
)
def test_relative_links_are_resolved(base: str, href: str, expected: str) -> None:
    assert absolutise(base, href) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("23 September 2026", "2026-09-23"),
        ("2026-09-23", "2026-09-23"),
        ("05/06/2026", "2026-06-05"),
        ("Closing date: 30 September 2026", "2026-09-30"),
    ],
)
def test_uk_dates_are_parsed_day_first(raw: str, expected: str) -> None:
    """``05/06/2026`` on a UK careers page is June. Reading it as May moves a deadline."""
    parsed = parse_uk_date(raw)

    assert parsed is not None and parsed.isoformat() == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-09-01T22:59:00+00:00", "2026-09-01"),
        ("2026-09-01", "2026-09-01"),
        ("2026-01-09", "2026-01-09"),
        ("2026-12-05T00:00:00Z", "2026-12-05"),
    ],
)
def test_an_iso_date_is_never_reinterpreted_as_day_first(raw: str, expected: str) -> None:
    """An ISO 8601 date always has the same field order, whatever the UK style is.

    Real case: ``dayfirst=True`` with ``fuzzy=True`` turned Oracle Fusion's ``2026-09-01``
    (1 September) into 9 January, and the job looked closed months early.
    """
    parsed = parse_uk_date(raw)

    assert parsed is not None and parsed.isoformat() == expected


@pytest.mark.parametrize("raw", ["", None, "Ongoing", "see advert"])
def test_an_unparseable_date_is_nothing_rather_than_a_guess(raw: str | None) -> None:
    assert parse_uk_date(raw) is None


@pytest.mark.parametrize(
    "html",
    [
        "<h1>Scheduled maintenance</h1>",
        "<p>Our system is currently undergoing maintenance</p>",
        "<p>We'll be back shortly</p>",
        "<p>Service unavailable</p>",
    ],
)
def test_a_maintenance_page_is_recognised(html: str) -> None:
    """This is what stops a weekend of downtime closing a university's vacancies."""
    assert looks_like_maintenance(html) is True


def test_a_listing_page_is_not_a_maintenance_page() -> None:
    assert looks_like_maintenance("<h1>Current vacancies</h1>") is False


@pytest.mark.parametrize(
    "html",
    [
        "<p>Access denied</p>",
        "<p>Please verify you are human</p>",
        "<title>Just a moment...</title>",
        "<title>Attention Required! | Cloudflare</title>",
    ],
)
def test_a_challenge_page_is_recognised(html: str) -> None:
    assert looks_blocked(html) is True


def test_a_normal_page_is_not_a_challenge() -> None:
    assert looks_blocked("<h1>Current vacancies</h1>") is False


def test_a_page_merely_hosted_behind_cloudflare_is_not_a_challenge() -> None:
    """Real case: Oxford's normal careers page was reported ``BLOCKED``.

    It loads Cloudflare's analytics script, and a plain "cloudflare" check could not tell that
    apart from a real challenge page.
    """
    html = (
        "<h1>Current vacancies</h1>"
        '<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js">'
        "</script>"
    )

    assert looks_blocked(html) is False


def test_a_captcha_feature_flag_in_page_config_is_not_a_challenge() -> None:
    """Real case: Bath Spa's normal careers page was reported ``BLOCKED``.

    Every page holds a setting called `careers_site_form_captchas` (set to `false`), and a plain
    "captcha" check could not tell that apart from a real challenge.
    """
    html = (
        "<h1>Current vacancies</h1>"
        '<script>window.CONFIG = {"careers_site_form_captchas":false}</script>'
    )

    assert looks_blocked(html) is False


@pytest.mark.parametrize(
    ("text", "href", "expected"),
    [
        ("Research Software Engineer", "/vacancy/1", True),
        ("Apply", "/vacancy/1", False),
        ("View details", "/vacancy/1", False),
        ("Next", "/page/2", False),
        ("Short", "/vacancy/1", False),
        ("Research Software Engineer", "#", False),
        ("Research Software Engineer", "javascript:void(0)", False),
        ("Research Software Engineer", "mailto:hr@a.ac.uk", False),
    ],
)
def test_navigation_links_are_not_mistaken_for_vacancies(
    text: str, href: str, expected: bool
) -> None:
    assert looks_like_vacancy_link(text, href) is expected


def test_a_page_without_json_ld_yields_nothing() -> None:
    assert extract_jsonld_jobpostings("<html><body>Vacancies</body></html>") == []


def test_json_ld_that_is_not_a_job_posting_is_ignored() -> None:
    html = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Organization","name":"A University"}'
        "</script>"
    )

    assert extract_jsonld_jobpostings(html) == []


def test_job_postings_inside_a_graph_are_found() -> None:
    """JSON-LD arrives as an object, a list or an ``@graph``; all three are the same data."""
    html = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"JobPosting","title":"Engineer","url":"https://a.ac.uk/1"}]}'
        "</script>"
    )

    assert len(extract_jsonld_jobpostings(html)) == 1


def test_an_rss_link_is_found(html_fixture: Any) -> None:
    html = '<link rel="alternate" type="application/rss+xml" href="/jobs/feed.xml">'

    assert find_rss_link(html, "https://a.ac.uk/jobs") == "https://a.ac.uk/jobs/feed.xml"


def test_a_page_with_no_feed_reports_none() -> None:
    assert find_rss_link("<html><head></head></html>", "https://a.ac.uk/jobs") is None


def test_a_stylesheet_link_is_not_mistaken_for_a_feed() -> None:
    html = '<link rel="alternate stylesheet" type="text/css" href="/print.css">'

    assert find_rss_link(html, "https://a.ac.uk/jobs") is None


def test_a_feed_titled_as_jobs_is_recognised_on_title_alone() -> None:
    xml = """<rss><channel>
        <title>Jobs at Example University</title>
        <description>Updates from our website.</description>
    </channel></rss>"""

    assert looks_like_a_jobs_feed(xml) is True


def test_a_generic_title_is_still_a_jobs_feed_when_items_link_to_vacancies() -> None:
    xml = """<rss><channel>
        <title>Example University</title>
        <description>Current vacancies at Example University.</description>
        <item><title>Lecturer in Physics</title><link>https://a.ac.uk/jobs/lecturer-physics</link></item>
        <item><title>Research Fellow</title><link>https://a.ac.uk/jobs/research-fellow</link></item>
    </channel></rss>"""

    assert looks_like_a_jobs_feed(xml) is True


def test_a_marketing_tagline_mentioning_careers_is_not_a_jobs_feed() -> None:
    """Real case: Arts University Bournemouth's site-wide feed, shortened.

    Its description says "We turn creativity into careers", but every item is a news article. The
    word "careers" alone once made it look like a jobs feed, and blog posts became vacancies.
    """
    xml = """<rss><channel>
        <title>Arts University Bournemouth</title>
        <description>We turn creativity into careers. Book an Open Day today.</description>
        <item>
            <title>Rock, Paper, Scissors</title>
            <link>https://aub.ac.uk/latest/rock-paper-scissors</link>
        </item>
        <item>
            <title>Keliss Moutou - my honest accommodation experience at AUB</title>
            <link>https://aub.ac.uk/latest/keliss-moutou-my-honest-accommodation-experience-at-aub</link>
        </item>
    </channel></rss>"""

    assert looks_like_a_jobs_feed(xml) is False


def test_item_links_corroborate_even_when_the_description_says_nothing_about_jobs() -> None:
    """Real case: London Business School's feed (Teamtailor), shortened.

    The title and description never mention jobs, but every item links to `/jobs/<id>-<slug>`.
    The link shape is enough evidence on its own.
    """
    xml = """<rss><channel>
        <title>London Business School</title>
        <description>Work for us</description>
        <item>
            <title>Database Manager</title>
            <link>https://jobsearch.london.edu/jobs/8262304-database-manager</link>
        </item>
        <item>
            <title>Senior Finance Business Partner</title>
            <link>https://jobsearch.london.edu/jobs/8253427-senior-finance-business-partner</link>
        </item>
    </channel></rss>"""

    assert looks_like_a_jobs_feed(xml) is True


def test_a_feed_with_no_channel_is_not_a_jobs_feed() -> None:
    assert looks_like_a_jobs_feed("<rss></rss>") is False


def test_a_jobs_sounding_description_with_no_items_is_not_trusted_alone() -> None:
    xml = """<rss><channel>
        <title>Example University</title>
        <description>News, events and careers updates.</description>
    </channel></rss>"""

    assert looks_like_a_jobs_feed(xml) is False


def test_an_organisation_nodes_description_is_read() -> None:
    html = """<script type="application/ld+json">
        {"@type": "CollegeOrUniversity", "name": "Example",
         "description": "A research-led university in the north."}
    </script>"""

    assert extract_organisation_description(html) == "A research-led university in the north."


def test_a_jobposting_node_is_not_mistaken_for_the_organisation() -> None:
    """The same script tag shape carries adverts on most portals - not the institution itself."""
    html = """<script type="application/ld+json">
        {"@type": "JobPosting", "title": "Lecturer", "description": "Apply now."}
    </script>"""

    assert extract_organisation_description(html) == ""


def test_an_organisation_node_inside_at_graph_is_still_found() -> None:
    html = """<script type="application/ld+json">
        {"@graph": [
            {"@type": "WebSite", "name": "Example"},
            {"@type": "Organization", "description": "A civic university since 1900."}
        ]}
    </script>"""

    assert extract_organisation_description(html) == "A civic university since 1900."


def test_malformed_jsonld_is_skipped_not_raised_on() -> None:
    html = '<script type="application/ld+json">{not valid json</script>'
    assert extract_organisation_description(html) == ""


def test_an_organisation_node_with_no_description_yields_nothing() -> None:
    html = """<script type="application/ld+json">
        {"@type": "Organization", "name": "Example"}
    </script>"""

    assert extract_organisation_description(html) == ""


def test_the_meta_description_tag_is_read() -> None:
    html = '<meta name="description" content="A research-led university in the north.">'
    assert extract_meta_description(html) == "A research-led university in the north."


def test_a_page_with_no_meta_description_yields_nothing() -> None:
    assert extract_meta_description("<html><head></head></html>") == ""


def test_a_meta_description_with_no_content_attribute_yields_nothing() -> None:
    assert extract_meta_description('<meta name="description">') == ""
