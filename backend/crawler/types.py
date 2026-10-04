"""The contracts between the crawler, the adapters and the HTTP layer.

No Django, on purpose. Adapters get plain values and a client protocol, so the whole adapter
test suite runs against saved pages in seconds, with no database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

from crawler.enums import ExtractionStrategy
from institutions.enums import Platform


@dataclass(frozen=True, slots=True)
class InstitutionRef:
    """Everything an adapter needs to know about an institution.

    A plain value object, not the Django model, so adapters cannot use the ORM.
    """

    slug: str
    name: str
    careers_url: str
    platform: Platform = Platform.UNKNOWN
    website: str = ""


@dataclass(frozen=True, slots=True)
class FetchResponse:
    """One HTTP response, already read."""

    url: str
    status_code: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)
    from_cache: bool = False
    not_modified: bool = False

    @property
    def content_type(self) -> str:
        """The bare content type, without parameters."""
        return self.headers.get("content-type", "").split(";")[0].strip().lower()

    @property
    def ok(self) -> bool:
        """Whether the status code is a success."""
        return 200 <= self.status_code < 300


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """A first, cheap fetch of the careers page, used to choose an adapter.

    Read once, so choosing an adapter costs one request, not one per adapter.
    """

    url: str
    status_code: int
    html: str
    headers: dict[str, str] = field(default_factory=dict)
    final_url: str = ""

    @property
    def lowered_html(self) -> str:
        """Casefolded body, since every detection heuristic is case-insensitive."""
        return self.html.casefold()


@dataclass(frozen=True, slots=True)
class RawVacancy:
    """One vacancy as the site published it.

    All raw text. Parsing happens in :mod:`screening`, and the raw text is kept next to it.
    """

    source_url: str
    title: str
    institution_slug: str
    department: str = ""
    category: str = ""
    reference: str = ""
    location_raw: str = ""
    salary_raw: str = ""
    grade_raw: str = ""
    description_html: str = ""
    description_text: str = ""
    posted_date: date | None = None
    closing_date: date | None = None
    contract_raw: str = ""
    hours_raw: str = ""
    strategy: ExtractionStrategy = ExtractionStrategy.HTML
    extra: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Reject items missing the fields every downstream consumer assumes."""
        if not self.title.strip():
            raise ValueError("RawVacancy.title is required")
        if not self.source_url.strip():
            raise ValueError("RawVacancy.source_url is required")
        if not self.institution_slug.strip():
            raise ValueError("RawVacancy.institution_slug is required")


@runtime_checkable
class HttpClient(Protocol):
    """What an adapter may do on the network.

    A protocol, not ``httpx`` itself, so tests can give it a client that reads saved pages.
    """

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> FetchResponse:
        """Fetch ``url``, honouring robots.txt and per-host politeness."""
        ...

    def post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResponse:
        """POST to ``url``. Used by portals whose listing is behind a form or a JSON API."""
        ...


@runtime_checkable
class BrowserSession(Protocol):
    """A rendered page, for sites that load their list with JavaScript.

    Kept out of :class:`PlatformAdapter`, so HTTP-only adapters have no unused browser methods.
    """

    def render(self, url: str, *, wait_for_selector: str | None = None) -> FetchResponse:
        """Load ``url`` in a browser and return the DOM once ``wait_for_selector`` appears."""
        ...

    def render_after_click(
        self, url: str, *, click_selector: str, wait_for_selector: str | None = None
    ) -> FetchResponse:
        """Load ``url``, click ``click_selector`` once, then return the page.

        For sites where the results only appear after a search is submitted.
        """
        ...

    def render_each_page(
        self,
        url: str,
        *,
        wait_for_selector: str,
        next_selector: str,
        max_pages: int = 20,
    ) -> list[FetchResponse]:
        """Load ``url``, then click ``next_selector`` again and again, keeping each page.

        For lists that change page with a button, not a URL. Stops when ``next_selector`` matches
        nothing. ``max_pages`` is only a safety limit.
        """
        ...


@runtime_checkable
class PlatformAdapter(Protocol):
    """The adapter contract. Every registered adapter satisfies exactly this."""

    platform: Platform

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Whether this adapter recognises the portal described by ``probe``."""
        ...

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Return every live vacancy, or raise a typed ``AdapterError``.

        Every one, not only the relevant ones. Filtering is the screening layer's job, and filtering
        too much here loses data for good.
        """
        ...

    def fetch_detail(self, url: str) -> RawVacancy:
        """Fetch one vacancy's detail page. Called only when the listing lacked fields."""
        ...


@dataclass(frozen=True, slots=True)
class ListingResult:
    """What an adapter produced, plus how it produced it."""

    vacancies: tuple[RawVacancy, ...]
    strategy: ExtractionStrategy
    fallback_fired: bool = False
    cache_keys: tuple[str, ...] = ()
