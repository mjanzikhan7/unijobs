"""Filling an institution's About text from its own homepage.

Pure with respect to persistence: `enrich_institution_description` never saves, so these run
against a plain, unsaved `Institution` instance rather than the database.
"""

from __future__ import annotations

from crawler.http import FixtureHttpClient
from crawler.institution_profile import discover_description, enrich_institution_description
from crawler.types import FetchResponse
from institutions.models import Institution

HOMEPAGE_URL = "https://example.ac.uk/"

ORGANISATION_DESCRIPTION = "A research-led university in the north of England."
META_DESCRIPTION = "A civic university, founded in 1900, in the heart of the city."

ORGANISATION_HTML = f"""<script type="application/ld+json">
    {{"@type": "CollegeOrUniversity", "description": "{ORGANISATION_DESCRIPTION}"}}
</script>"""

META_ONLY_HTML = f'<meta name="description" content="{META_DESCRIPTION}">'


def _institution(**overrides: object) -> Institution:
    fields: dict[str, object] = {
        "slug": "example",
        "name": "Example University",
        "website": HOMEPAGE_URL,
        "description": "",
    }
    fields.update(overrides)
    return Institution(**fields)  # type: ignore[arg-type]


def _client(text: str = ORGANISATION_HTML, *, status_code: int = 200) -> FixtureHttpClient:
    return FixtureHttpClient(
        responses={
            HOMEPAGE_URL: FetchResponse(
                url=HOMEPAGE_URL, status_code=status_code, text=text, headers={}
            )
        }
    )


def test_the_organisation_nodes_description_wins_over_the_meta_tag() -> None:
    html = ORGANISATION_HTML + META_ONLY_HTML
    assert discover_description(html) == ORGANISATION_DESCRIPTION


def test_the_meta_tag_is_used_when_there_is_no_organisation_node() -> None:
    assert discover_description(META_ONLY_HTML) == META_DESCRIPTION


def test_nothing_found_is_an_empty_string() -> None:
    assert discover_description("<html><body>Welcome</body></html>") == ""


def test_a_description_shorter_than_the_floor_is_rejected() -> None:
    """A nav label or a stray fragment is not a summary."""
    html = '<meta name="description" content="Home">'
    assert discover_description(html) == ""


def test_a_long_description_is_truncated() -> None:
    long_text = "A" * 1000
    html = f'<meta name="description" content="{long_text}">'
    assert len(discover_description(html)) == 600


def test_a_blank_description_is_filled_from_the_homepage() -> None:
    institution = _institution()

    changed = enrich_institution_description(institution, http=_client())

    assert changed is True
    assert institution.description == ORGANISATION_DESCRIPTION


def test_an_existing_description_is_never_overwritten() -> None:
    institution = _institution(description="Written by an operator.")

    changed = enrich_institution_description(institution, http=_client())

    assert changed is False
    assert institution.description == "Written by an operator."


def test_no_website_and_no_careers_url_means_nothing_to_fetch() -> None:
    institution = _institution(website="")

    changed = enrich_institution_description(institution, http=_client())

    assert changed is False
    assert institution.description == ""


def test_falls_back_to_the_careers_urls_own_origin_when_no_website_is_set() -> None:
    """The only guess available without a website, and what every real institution hits.

    The seed estate carries a careers URL for every institution but a homepage for none.
    """
    institution = _institution(website="", careers_url="https://example.ac.uk/jobs/search?q=")
    client = FixtureHttpClient(
        responses={
            HOMEPAGE_URL: FetchResponse(
                url=HOMEPAGE_URL, status_code=200, text=ORGANISATION_HTML, headers={}
            )
        }
    )

    changed = enrich_institution_description(institution, http=client)

    assert changed is True
    assert institution.description == ORGANISATION_DESCRIPTION


def test_a_failed_fetch_leaves_the_description_blank_not_broken() -> None:
    institution = _institution()
    client = FixtureHttpClient(responses={})

    changed = enrich_institution_description(institution, http=client)

    assert changed is False
    assert institution.description == ""


def test_a_non_ok_response_is_not_trusted() -> None:
    institution = _institution()

    changed = enrich_institution_description(institution, http=_client(status_code=404))

    assert changed is False


def test_a_homepage_with_nothing_worth_reading_leaves_the_description_blank() -> None:
    institution = _institution()

    changed = enrich_institution_description(
        institution, http=_client("<html><body>Welcome</body></html>")
    )

    assert changed is False
