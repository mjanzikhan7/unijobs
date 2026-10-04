"""Getting vacancies out of a page, most reliable method first.

The order is fixed: ``schema.org/JobPosting`` JSON-LD, then an RSS feed, then a JSON endpoint
the page calls, and only then HTML selectors. Structured data is much more stable than the
HTML around it. A theme update breaks a CSS selector but leaves JSON-LD alone.

Pure functions. No network, no Django.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from crawler.enums import ExtractionStrategy
from crawler.types import RawVacancy

_WHITESPACE = re.compile(r"[ \t\r\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")

_MAINTENANCE_MARKERS: tuple[str, ...] = (
    "scheduled maintenance",
    "under maintenance",
    "site maintenance",
    "temporarily unavailable",
    "service unavailable",
    "we'll be back",
    "we will be back shortly",
    "currently undergoing maintenance",
    "system upgrade in progress",
)

_BLOCK_MARKERS: tuple[str, ...] = (
    "access denied",
    "request blocked",
    "are you a robot",
    "verify you are human",
    "checking your browser before accessing",
    "just a moment...",
    "attention required! | cloudflare",
    "ddos protection by cloudflare",
    "unusual traffic",
)


def soup_of(html: str) -> BeautifulSoup:
    """Parse ``html`` with lxml, which is both faster and more forgiving than html.parser."""
    return BeautifulSoup(html or "", "lxml")


def html_to_text(html: str) -> str:
    """Turn an advert body into readable text.

    Scripts and styles are removed. Block elements become line breaks. The exclusion matcher and
    the fitness scorer read this text, so paragraphs matter more than markup.
    """
    if not html:
        return ""
    soup = soup_of(html)
    for element in soup(["script", "style", "noscript"]):
        element.decompose()
    text = soup.get_text("\n")
    text = _WHITESPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _BLANK_LINES.sub("\n\n", text).strip()


def absolutise(base_url: str, href: str) -> str:
    """Resolve ``href`` against ``base_url``, leaving absolute URLs alone."""
    return urljoin(base_url, (href or "").strip())


_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def parse_uk_date(value: str | None) -> date | None:
    """Parse a date as a UK advert writes it, or as a recruitment system's API writes it.

    An ISO date such as 2026-05-04 is parsed strictly, never with ``dayfirst`` or ``fuzzy``, so it
    is always 4 May and never 5 April.
    """
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if _ISO_DATE_RE.match(text):
            parsed = date_parser.isoparse(text)
        else:
            parsed = date_parser.parse(text, dayfirst=True, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None
    return parsed.date() if isinstance(parsed, datetime) else parsed


def looks_like_maintenance(html: str) -> bool:
    """Whether a page is a maintenance page.

    Checked before we believe "zero vacancies". One university site was down for a weekend, and
    trusting the empty list would have closed all its jobs.
    """
    lowered = (html or "").casefold()
    return any(marker in lowered for marker in _MAINTENANCE_MARKERS)


def looks_blocked(html: str) -> bool:
    """Whether a response is a bot challenge rather than content."""
    lowered = (html or "").casefold()
    return any(marker in lowered for marker in _BLOCK_MARKERS)


def _iter_jsonld_nodes(payload: Any) -> list[dict[str, Any]]:
    """Flatten the shapes JSON-LD arrives in: object, list, or ``@graph``."""
    nodes: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        graph = payload.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                nodes.extend(_iter_jsonld_nodes(item))
        else:
            nodes.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            nodes.extend(_iter_jsonld_nodes(item))
    return nodes


def extract_jsonld_jobpostings(html: str) -> list[dict[str, Any]]:
    """Return every ``schema.org/JobPosting`` object in ``html``.

    Broken blocks are skipped, not raised. One bad advert in a list of forty should cost one
    advert, not the whole institution.
    """
    postings: list[dict[str, Any]] = []
    for script in soup_of(html).find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for node in _iter_jsonld_nodes(payload):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if any(str(item).casefold() == "jobposting" for item in types if item):
                postings.append(node)
    return postings


_ORGANISATION_TYPES = frozenset({"organization", "collegeoruniversity", "educationalorganization"})


def extract_organisation_description(html: str) -> str:
    """The ``description`` of a schema.org ``Organization`` on a homepage.

    Narrower than :func:`extract_jsonld_jobpostings` on purpose. Here an ``Organization`` means the
    institution itself, not one of its vacancies.
    """
    for script in soup_of(html).find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for node in _iter_jsonld_nodes(payload):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if any(str(item).casefold() in _ORGANISATION_TYPES for item in types if item):
                description = _jsonld_text(node.get("description"))
                if description:
                    return description
    return ""


def extract_meta_description(html: str) -> str:
    """The page's own ``<meta name="description">``.

    The fallback for :func:`extract_organisation_description`. Most homepages have it, even
    without structured data.
    """
    tag = soup_of(html).find("meta", attrs={"name": "description"})
    if not isinstance(tag, Tag):
        return ""
    content = tag.get("content")
    return content.strip() if isinstance(content, str) else ""


def _jsonld_text(value: Any) -> str:
    """Coerce a JSON-LD value that may be a string, a list or a nested object."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(filter(None, (_jsonld_text(item) for item in value)))
    if isinstance(value, dict):
        for key in ("name", "value", "@value", "text"):
            if key in value:
                return _jsonld_text(value[key])
    return str(value)


def _jsonld_salary(node: dict[str, Any]) -> str:
    """Turn ``baseSalary`` back into the kind of text a person would write.

    We rebuild a string instead of parsing here, so :func:`screening.domain.parse_salary` stays
    the only place that reads salary text.
    """
    salary = node.get("baseSalary")
    if not isinstance(salary, dict):
        return _jsonld_text(salary)
    value = salary.get("value")
    currency = salary.get("currency") or salary.get("currencyCode") or "GBP"
    symbol = "£" if str(currency).upper() == "GBP" else ""
    if isinstance(value, dict):
        minimum = _format_amount(value.get("minValue"), symbol)
        maximum = _format_amount(value.get("maxValue"), symbol)
        single = _format_amount(value.get("value"), symbol)
        unit = str(value.get("unitText") or "").lower()
        suffix = f" per {unit}" if unit else ""
        if minimum and maximum:
            return f"{minimum} to {maximum}{suffix}"
        if single:
            return f"{single}{suffix}"
        if maximum:
            return f"Up to {maximum}{suffix}"
        if minimum:
            return f"From {minimum}{suffix}"
    return _jsonld_text(salary)


def _format_amount(value: Any, symbol: str) -> str:
    """Render a JSON-LD money value as ``£38,784``, or an empty string if it is not a number."""
    if value in (None, ""):
        return ""
    try:
        return f"{symbol}{float(value):,.0f}"
    except (TypeError, ValueError):
        return ""


def _jsonld_location(node: dict[str, Any]) -> str:
    """Flatten ``jobLocation`` into the address line an advert would print."""
    location = node.get("jobLocation")
    if isinstance(location, list):
        location = location[0] if location else None
    if not isinstance(location, dict):
        return _jsonld_text(location)
    address = location.get("address")
    if isinstance(address, dict):
        parts = [
            _jsonld_text(address.get(key))
            for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode")
        ]
        return ", ".join(part for part in parts if part)
    return _jsonld_text(address or location.get("name"))


def jobposting_to_vacancy(
    node: dict[str, Any], *, institution_slug: str, base_url: str, fallback_url: str = ""
) -> RawVacancy | None:
    """Convert one JSON-LD ``JobPosting`` into a :class:`RawVacancy`.

    Returns ``None`` when the posting has no title or no usable URL. A vacancy with no link cannot
    be applied for, and inventing a link would be worse than dropping it.
    """
    title = _jsonld_text(node.get("title")) or _jsonld_text(node.get("name"))
    url = _jsonld_text(node.get("url")) or _jsonld_text(node.get("sameAs")) or fallback_url
    if not title or not url:
        return None

    description_html = _jsonld_text(node.get("description"))
    organisation = node.get("hiringOrganization")
    department = (
        _jsonld_text(organisation.get("department")) if isinstance(organisation, dict) else ""
    )

    return RawVacancy(
        source_url=absolutise(base_url, url),
        title=title,
        institution_slug=institution_slug,
        department=department,
        reference=_jsonld_text(node.get("identifier")),
        location_raw=_jsonld_location(node),
        salary_raw=_jsonld_salary(node),
        description_html=description_html,
        description_text=html_to_text(description_html),
        posted_date=parse_uk_date(_jsonld_text(node.get("datePosted"))),
        closing_date=parse_uk_date(_jsonld_text(node.get("validThrough"))),
        contract_raw=_jsonld_text(node.get("employmentType")),
        strategy=ExtractionStrategy.JSON_LD,
    )


def find_rss_link(html: str, base_url: str) -> str | None:
    """Return the page's advertised RSS or Atom feed, if it has one."""
    links = soup_of(html).find_all("link", rel=lambda value: value and "alternate" in value)
    for link in links:
        if not isinstance(link, Tag):
            continue
        link_type = str(link.get("type", "")).lower()
        if "rss" in link_type or "atom" in link_type:
            href = str(link.get("href") or "")
            if href:
                return absolutise(base_url, href)
    return None


_JOBS_FEED_KEYWORDS = ("job", "vacan", "career", "recruit")


def looks_like_a_jobs_feed(xml: str) -> bool:
    """Whether an RSS or Atom feed is really about jobs, not just mentioning them.

    Accepts a clear channel title, or a feed where most items link to a job-like path. Never the
    channel description alone.
    """
    soup = BeautifulSoup(xml or "", "xml")
    channel = soup.find(["channel", "feed"])
    if not isinstance(channel, Tag):
        return False

    title_tag = channel.find("title")
    title = cell_text(title_tag if isinstance(title_tag, Tag) else None)
    if any(keyword in title.casefold() for keyword in _JOBS_FEED_KEYWORDS):
        return True

    items = soup.find_all(["item", "entry"])
    if not items:
        return False
    job_like = 0
    for item in items:
        if not isinstance(item, Tag):
            continue
        link_tag = item.find("link")
        href = ""
        if isinstance(link_tag, Tag):
            href = str(link_tag.get("href") or link_tag.get_text(strip=True) or "")
        path = urlsplit(href).path.casefold()
        if any(keyword in path for keyword in _JOBS_FEED_KEYWORDS):
            job_like += 1
    return job_like >= len(items) / 2


def parse_rss_vacancies(xml: str, *, institution_slug: str, base_url: str) -> list[RawVacancy]:
    """Turn an RSS or Atom feed into vacancies."""
    soup = BeautifulSoup(xml or "", "xml")
    vacancies: list[RawVacancy] = []
    for item in soup.find_all(["item", "entry"]):
        title = (item.find("title").get_text(strip=True) if item.find("title") else "").strip()
        link_tag = item.find("link")
        if link_tag is None:
            continue
        href = (link_tag.get("href") or link_tag.get_text(strip=True) or "").strip()
        if not title or not href:
            continue
        description = item.find(["description", "summary", "content"])
        description_html = description.get_text() if description else ""
        published = item.find(["pubDate", "published", "updated"])
        vacancies.append(
            RawVacancy(
                source_url=absolutise(base_url, href),
                title=title,
                institution_slug=institution_slug,
                description_html=description_html,
                description_text=html_to_text(description_html),
                posted_date=parse_uk_date(published.get_text(strip=True) if published else None),
                strategy=ExtractionStrategy.RSS,
            )
        )
    return vacancies


_NON_VACANCY_LINK_TEXT: frozenset[str] = frozenset(
    {
        "apply",
        "apply now",
        "back",
        "back to search",
        "next",
        "previous",
        "home",
        "search",
        "view all",
        "more",
        "read more",
        "details",
        "view details",
        "sign in",
        "login",
        "register",
    }
)


def looks_like_vacancy_link(text: str, href: str) -> bool:
    """Whether a link is plausibly a vacancy rather than site furniture."""
    cleaned = _WHITESPACE.sub(" ", (text or "")).strip()
    if len(cleaned) < 6 or cleaned.casefold() in _NON_VACANCY_LINK_TEXT:
        return False
    return bool(href) and not href.startswith(("#", "javascript:", "mailto:"))


def cell_text(cell: Tag | None) -> str:
    """Return the trimmed text of a table cell, or an empty string."""
    if cell is None:
        return ""
    return _WHITESPACE.sub(" ", cell.get_text(" ", strip=True)).strip()


MAX_FIELD_VALUE_CHARS = 300

FIELD_LABELS: dict[str, str] = {
    "location": "location_raw",
    "locations": "location_raw",
    "based at": "location_raw",
    "salary": "salary_raw",
    "salary range": "salary_raw",
    "remuneration": "salary_raw",
    "hours": "hours_raw",
    "working hours": "hours_raw",
    "contract type": "contract_raw",
    "contract": "contract_raw",
    "contract duration": "contract_raw",
    "type of contract": "contract_raw",
    "job ref": "reference",
    "job reference": "reference",
    "vacancy reference": "reference",
    "vacancy ref": "reference",
    "reference": "reference",
    "ref": "reference",
    "department": "department",
    "faculty": "department",
    "school": "department",
    "division": "department",
    "grade": "grade_raw",
    "salary grade": "grade_raw",
    "job type": "category",
    "category": "category",
    "job category": "category",
}

DATE_LABELS: dict[str, str] = {
    "placed on": "posted_date",
    "posted": "posted_date",
    "date posted": "posted_date",
    "published": "posted_date",
    "closes": "closing_date",
    "closing date": "closing_date",
    "closing": "closing_date",
    "deadline": "closing_date",
    "application deadline": "closing_date",
}


def _normalise_label(text: str) -> str:
    """Reduce a label to something comparable: lowercase, no colon, no stray whitespace."""
    return re.sub(r"\s+", " ", text).strip().rstrip(":").strip().casefold()


def _record(fields: dict[str, str], label: str, value: str) -> None:
    """Save one pair, keeping the first time a label appears.

    Sites often repeat a label in a summary box and again in the text. The summary comes first,
    and it is the one stated on purpose.
    """
    key = _normalise_label(label)
    value = re.sub(r"\s+", " ", value).strip()
    if not key or not value or len(value) > MAX_FIELD_VALUE_CHARS:
        return
    fields.setdefault(key, value)


def labelled_fields(html: str) -> dict[str, str]:
    """Return every ``label: value`` pair a detail page states, normalised.

    Handles the three layouts we see: definition lists, table rows (including two pairs per row),
    and a label element followed by a value element.
    """
    if not html or not html.strip():
        return {}

    soup = soup_of(html)
    fields: dict[str, str] = {}

    for term in soup.find_all("dt"):
        value = term.find_next_sibling("dd")
        if value is not None:
            _record(fields, term.get_text(" ", strip=True), value.get_text(" ", strip=True))

    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        for index in range(0, len(cells) - 1, 2):
            _record(
                fields,
                cells[index].get_text(" ", strip=True),
                cells[index + 1].get_text(" ", strip=True),
            )

    for node in soup.find_all(["span", "strong", "b", "label", "div"]):
        text = node.get_text(" ", strip=True)
        looks_like_label = text.endswith(":") or "label" in " ".join(node.get("class") or [])
        if not looks_like_label or len(text) > 60:
            continue
        sibling = node.find_next_sibling()
        if sibling is not None:
            _record(fields, text, sibling.get_text(" ", strip=True))

    return fields


def apply_labelled_fields(vacancy: RawVacancy, fields: dict[str, str]) -> RawVacancy:
    """Fill a vacancy's *empty* fields from label and value pairs.

    Never overwrites. A field from the listing page wins over one found on the detail page.
    """
    if not fields:
        return vacancy

    changes: dict[str, object] = {}
    extra = dict(vacancy.extra)

    for label, value in fields.items():
        if attribute := FIELD_LABELS.get(label):
            if not getattr(vacancy, attribute, ""):
                changes[attribute] = value
        elif attribute := DATE_LABELS.get(label):
            if getattr(vacancy, attribute, None) is None and (parsed := parse_uk_date(value)):
                changes[attribute] = parsed
        else:
            extra.setdefault(label, value)

    if not changes and extra == vacancy.extra:
        return vacancy

    return replace(vacancy, **changes, extra=extra)  # type: ignore[arg-type]
