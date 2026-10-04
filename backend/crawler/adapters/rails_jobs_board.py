"""A Rails-based jobs board (Ruby on Rails ``/rails/active_storage/`` asset URLs).

Recognise it by the specific combination of CSS classes its results page renders together -
``results-list``, ``job-result-item`` and ``results-job-location`` - a content signature, not
the host, so another tenant of the same product would still match.
Quirk: pagination is a plain ``?page=N``, no session needed. Neither closing date nor reference
is published; the job URL's own numeric id is read as the reference. No separate detail fetch -
salary and location are already on the listing.
Example: https://www.jobs.gla.ac.uk/jobs - University of Glasgow.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import BeautifulSoup, Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_REQUIRED_SIGNATURES = ("results-list", "job-result-item", "results-job-location")

_REFERENCE_FROM_URL_RE = re.compile(r"-(\d+)/?$")

_MAX_PAGES = 50


@register_adapter
class RailsJobsBoardAdapter(BaseAdapter):
    """Reads every page of the results list, following its own ``?page=N`` links."""

    platform: ClassVar[Platform] = Platform.RAILS_JOBS_BOARD

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the platform by its results-page markup, not by host."""
        html = probe.lowered_html
        return all(signature in html for signature in _REQUIRED_SIGNATURES)

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch every page the listing itself links to, reading each one's cards."""
        vacancies: list[RawVacancy] = []
        next_url: str | None = institution.careers_url
        seen_urls: set[str] = set()
        pages_fetched = 0

        while next_url and next_url not in seen_urls:
            pages_fetched += 1
            if pages_fetched > _MAX_PAGES:
                break
            seen_urls.add(next_url)
            response = self.http.get(next_url)
            self.guard(response.text, next_url)
            base_url = response.url or next_url

            soup = soup_of(response.text)
            for card in soup.find_all("li", class_="job-result-item"):
                if not isinstance(card, Tag):
                    continue
                vacancy = self._read_card(card, institution, base_url=base_url)
                if vacancy is not None:
                    vacancies.append(vacancy)

            next_url = self._next_page_url(soup, base_url=base_url)

        return vacancies

    def _read_card(
        self, card: Tag, institution: InstitutionRef, *, base_url: str
    ) -> RawVacancy | None:
        """One ``job-result-item``'s title, location, salary and truncated description."""
        title_div = card.find("div", class_="job-title")
        link = title_div.find("a", href=True) if isinstance(title_div, Tag) else None
        if not isinstance(link, Tag):
            return None
        title = cell_text(link)
        if not title:
            return None

        source_url = absolutise(base_url, str(link["href"]))
        ref_match = _REFERENCE_FROM_URL_RE.search(source_url)
        location = card.find("li", class_="results-job-location")
        salary = card.find("li", class_="results-salary")
        description = card.find("p", class_="job-description")

        return RawVacancy(
            source_url=source_url,
            title=title,
            institution_slug=institution.slug,
            reference=ref_match.group(1) if ref_match else "",
            location_raw=cell_text(location) if isinstance(location, Tag) else "",
            salary_raw=cell_text(salary) if isinstance(salary, Tag) else "",
            description_text=cell_text(description) if isinstance(description, Tag) else "",
            strategy=self.strategy,
        )

    @staticmethod
    def _next_page_url(soup: BeautifulSoup, *, base_url: str) -> str | None:
        """The pager's own ``next`` link, or ``None`` on the last page.

        Trusting the page's own link over reconstructing a ``?page=`` URL is the same reasoning
        the Talentlink adapter's ``Lst-NavPage`` handling already established.
        """
        nav = soup.find("nav", class_="pagination")
        if not isinstance(nav, Tag):
            return None
        next_span = nav.find("span", class_="next")
        if not isinstance(next_span, Tag):
            return None
        link = next_span.find("a", href=True)
        if not isinstance(link, Tag):
            return None
        return absolutise(base_url, str(link["href"]))
