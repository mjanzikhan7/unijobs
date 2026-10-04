"""Which platforms need Chromium to render their listing.

A plain, unsaved ``Institution`` is enough: ``needs_browser`` only reads ``effective_platform``,
which never touches the database, so this stays a unit test rather than an integration one.
"""

from __future__ import annotations

from crawler.transport import _BROWSER_PLATFORMS, needs_browser
from institutions.enums import Platform
from institutions.models import Institution


def institution(platform: str = "", adapter_override: str = "") -> Institution:
    return Institution(platform=platform, adapter_override=adapter_override)


def test_a_platform_with_a_plain_http_path_needs_no_browser() -> None:
    assert needs_browser(institution(Platform.STONEFISH.value)) is False


def test_a_platform_in_the_dict_needs_a_browser() -> None:
    assert needs_browser(institution(Platform.JOBTRAIN.value)) is True


def test_an_unset_platform_needs_a_browser() -> None:
    """Never yet crawled. Detection may land on a platform that needs one."""
    assert needs_browser(institution("")) is True


def test_an_explicitly_unknown_platform_needs_a_browser() -> None:
    assert needs_browser(institution(Platform.UNKNOWN.value)) is True


def test_a_human_adapter_override_wins_over_the_detected_platform() -> None:
    overridden = institution(
        platform=Platform.STONEFISH.value, adapter_override=Platform.JOBTRAIN.value
    )
    assert needs_browser(overridden) is True


def test_corehr_plain_http_needs_no_browser() -> None:
    """Confirmed by hand against two live tenants.

    CoreHR's "everything" search is a plain HTTP form submission, no session cookie or JS
    required. ``COREHR_CATEGORISED`` is a different platform and does still need
    one, for its own marketing-page discovery step.
    """
    assert Platform.COREHR not in _BROWSER_PLATFORMS


def test_generic_card_scrape_does_not_use_a_browser() -> None:
    """The browser was only there to get past a site that blocks our User-Agent. Not any more."""
    assert Platform.GENERIC_CARD_SCRAPE not in _BROWSER_PLATFORMS
