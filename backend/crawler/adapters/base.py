"""Shared adapter code.

Each adapter gets an :class:`~crawler.types.HttpClient` and, if needed, a
:class:`~crawler.types.BrowserSession`. Both are passed in, never built here, which keeps the
adapter tests offline and fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from crawler.enums import ExtractionStrategy
from crawler.exceptions import Blocked, ParseError, SiteOffline
from crawler.extraction import (
    apply_labelled_fields,
    extract_jsonld_jobpostings,
    find_rss_link,
    html_to_text,
    jobposting_to_vacancy,
    labelled_fields,
    looks_blocked,
    looks_like_a_jobs_feed,
    looks_like_maintenance,
    parse_rss_vacancies,
    soup_of,
)
from crawler.types import (
    BrowserSession,
    FetchResponse,
    HttpClient,
    InstitutionRef,
    ProbeResult,
    RawVacancy,
)
from institutions.enums import Platform


@dataclass
class BaseAdapter:
    """Shared behaviour for every adapter.

    Subclasses write :meth:`detect` and :meth:`list_vacancies`. Everything else is inherited.
    """

    http: HttpClient
    browser: BrowserSession | None = None
    strategy: ExtractionStrategy = field(default=ExtractionStrategy.HTML, init=False)
    fallback_fired: bool = field(default=False, init=False)

    platform: ClassVar[Platform] = Platform.UNKNOWN

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:  # pragma: no cover
        """Whether this adapter recognises the portal. Overridden by every subclass."""
        raise NotImplementedError

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:  # pragma: no cover
        """Return every live vacancy. Overridden by every subclass."""
        raise NotImplementedError

    def fetch_detail(self, url: str) -> RawVacancy:
        """Fetch and parse one vacancy page.

        Only used when the listing had no salary or closing date. Most sites show both in the list.
        """
        response = self.http.get(url)
        self.guard(response.text, url)

        postings = extract_jsonld_jobpostings(response.text)
        if postings:
            vacancy = jobposting_to_vacancy(
                postings[0], institution_slug="pending", base_url=url, fallback_url=url
            )
            if vacancy is not None:
                return apply_labelled_fields(vacancy, labelled_fields(response.text))

        soup = soup_of(response.text)
        heading = soup.find(["h1", "h2"])
        title = heading.get_text(" ", strip=True) if heading else ""
        if not title:
            raise ParseError(f"No title found on {url}", url=url)

        body = soup.find(["main", "article"]) or soup.body or soup
        description_html = str(body)
        vacancy = RawVacancy(
            source_url=url,
            title=title,
            institution_slug="pending",
            description_html=description_html,
            description_text=html_to_text(description_html),
        )
        return apply_labelled_fields(vacancy, labelled_fields(response.text))

    def guard(self, html: str, url: str) -> None:
        """Reject a response that is not a listing, before anything trusts it.

        A maintenance page is ``OFFLINE``, not ``ZERO_RESULTS``. Mixing them up could close a whole
        university's vacancies during planned downtime.
        """
        if looks_like_maintenance(html):
            raise SiteOffline(f"{url} served a maintenance page", url=url)
        if looks_blocked(html):
            raise Blocked(f"{url} served a challenge page", url=url)

    def structured_vacancies(
        self, response: FetchResponse, institution: InstitutionRef
    ) -> list[RawVacancy] | None:
        """Try JSON-LD, then RSS, before any CSS selector.

        Returns ``None`` when neither exists, so the caller falls back to HTML. A site that adds
        JSON-LD later is upgraded automatically, and the saved strategy shows it.
        """
        postings = extract_jsonld_jobpostings(response.text)
        if postings:
            vacancies = [
                vacancy
                for posting in postings
                if (
                    vacancy := jobposting_to_vacancy(
                        posting,
                        institution_slug=institution.slug,
                        base_url=response.url,
                    )
                )
                is not None
            ]
            if vacancies:
                self.strategy = ExtractionStrategy.JSON_LD
                return vacancies

        feed_url = find_rss_link(response.text, response.url)
        if feed_url:
            feed = self.http.get(feed_url)
            if looks_like_a_jobs_feed(feed.text):
                vacancies = parse_rss_vacancies(
                    feed.text, institution_slug=institution.slug, base_url=feed.url
                )
                if vacancies:
                    self.strategy = ExtractionStrategy.RSS
                    return vacancies

        return None

    def render(self, url: str, *, wait_for_selector: str | None = None) -> FetchResponse:
        """Render ``url`` in the injected browser, or fail loudly if there isn't one."""
        if self.browser is None:
            raise SiteOffline(f"{url} needs a browser to render and none was provided", url=url)
        response = self.browser.render(url, wait_for_selector=wait_for_selector)
        self.strategy = ExtractionStrategy.BROWSER_HTML
        return response

    def render_after_click(
        self, url: str, *, click_selector: str, wait_for_selector: str | None = None
    ) -> FetchResponse:
        """Render ``url``, click once, then return the DOM - or fail loudly without a browser."""
        if self.browser is None:
            raise SiteOffline(f"{url} needs a browser to render and none was provided", url=url)
        response = self.browser.render_after_click(
            url, click_selector=click_selector, wait_for_selector=wait_for_selector
        )
        self.strategy = ExtractionStrategy.BROWSER_HTML
        return response
