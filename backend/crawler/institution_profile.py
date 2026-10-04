"""Filling an institution's About text from its homepage, when it is still empty.

Only the description. Contact details (email, phone, address) are always typed in by an
operator, like a logo. A meta description is written to describe the page. A contact detail
guessed from a homepage is often wrong, and a wrong one is worse than none.
"""

from __future__ import annotations

from urllib.parse import urlparse

from crawler.extraction import extract_meta_description, extract_organisation_description
from crawler.types import HttpClient
from institutions.models import Institution

MIN_DESCRIPTION_CHARS = 40

MAX_DESCRIPTION_CHARS = 600


def discover_description(html: str) -> str:
    """The best About text in ``html``, or an empty string.

    Structured data first. A schema.org ``Organization`` is written for software to read, so we
    trust it more than a meta tag.
    """
    for candidate in (extract_organisation_description(html), extract_meta_description(html)):
        text = candidate.strip()
        if len(text) >= MIN_DESCRIPTION_CHARS:
            return text[:MAX_DESCRIPTION_CHARS]
    return ""


def _homepage_url(institution: Institution) -> str:
    """The URL to read an About paragraph from.

    The seed data has a careers URL for every institution but no homepage. ``website`` is only set
    if an operator typed it. Otherwise we use the careers URL's domain, which is almost always the
    institution's own.
    """
    if institution.website:
        return institution.website
    parsed = urlparse(institution.careers_url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}/"


def enrich_institution_description(institution: Institution, *, http: HttpClient) -> bool:
    """Fill ``institution.description`` from its homepage, if it is still empty.

    Never overwrites. An operator's own words always win. Returns whether the field changed. It
    does not save, so the caller decides, and it can be tested on a plain object.
    """
    homepage = _homepage_url(institution)
    if institution.description or not homepage:
        return False

    try:
        response = http.get(homepage)
    except Exception:
        return False

    if not response.ok:
        return False

    description = discover_description(response.text)
    if not description:
        return False

    institution.description = description
    return True
