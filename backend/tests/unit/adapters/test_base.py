"""`BaseAdapter.fetch_detail` - the shared implementation every adapter inherits by default.

Its own detail vacancy never knows which institution it belongs to; the caller always
overwrites that afterwards, so this only has to prove the placeholder is non-empty, not that
it is meaningful.
"""

from __future__ import annotations

from crawler.adapters.base import BaseAdapter
from crawler.http import FixtureHttpClient
from tests.unit.adapters.conftest import response

_JSONLD_URL = "https://jobs.test.ac.uk/vacancy/1"
_JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Research Fellow",
  "description": "<p>We are seeking a Research Fellow.</p>",
  "datePosted": "2026-08-01"
}
</script>
</head><body></body></html>
"""

_PLAIN_URL = "https://jobs.test.ac.uk/vacancy/2"
_PLAIN_HTML = (
    "<html><body><main><h1>Research Assistant</h1>"
    "<p>An excellent opportunity.</p></main></body></html>"
)


def test_fetch_detail_reads_jsonld_without_a_blank_institution_slug() -> None:
    adapter = BaseAdapter(
        http=FixtureHttpClient(responses={_JSONLD_URL: response(_JSONLD_HTML, _JSONLD_URL)})
    )

    vacancy = adapter.fetch_detail(_JSONLD_URL)

    assert vacancy.title == "Research Fellow"
    assert vacancy.institution_slug


def test_fetch_detail_falls_back_to_the_page_body_without_a_blank_institution_slug() -> None:
    adapter = BaseAdapter(
        http=FixtureHttpClient(responses={_PLAIN_URL: response(_PLAIN_HTML, _PLAIN_URL)})
    )

    vacancy = adapter.fetch_detail(_PLAIN_URL)

    assert vacancy.title == "Research Assistant"
    assert vacancy.institution_slug
