"""A CoreHR tenant reached only through several category-scoped searches, not one.

Recognise it by a marketing page linking to more than one ``corehr.com`` search, each naming a
different ``p_competition_type``, with no "everything" search that actually works.
Quirk: the category links are only ever published on that marketing page, not derivable from the
tenant's URL shape. Pagination is not optional - CoreHR's own ordering is unstable run to run, so
a single page per category mis-closes real jobs.
Browser: yes - the marketing-page discovery step still benefits from one.
Example: https://www.ox.ac.uk/about/jobs - University of Oxford, three categories merged.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.corehr import CoreHRAdapter
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CATEGORY_PARAM = "p_competition_type"

_OPENS_IN_NEW_WINDOW_RE = re.compile(r"\s*\(opens in new window\)\s*$", re.IGNORECASE)
_TRAILING_JOBS_RE = re.compile(r"\s*jobs\s*$", re.IGNORECASE)


@register_adapter
class CoreHRCategorisedAdapter(CoreHRAdapter):
    """Reads a marketing page's own category links rather than one fixed search URL."""

    platform: ClassVar[Platform] = Platform.COREHR_CATEGORISED

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise the marketing page by more than one categorised CoreHR link on it.

        More than one, not "at least one": a single categorised link is ambiguous with a
        tenant that merely happens to default its main search to one category, which
        :class:`CoreHRAdapter` already handles as an ordinary single-URL fetch.
        """
        return len(cls._category_links(probe.html, base_url=probe.final_url or probe.url)) >= 2

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the marketing page's own category links, then read and merge each of them."""
        url = institution.careers_url
        page = self.render(url) if self.browser is not None else self.http.get(url)

        links = self._category_links(page.text, base_url=page.url or url)

        vacancies: list[RawVacancy] = []
        seen_source_urls: set[str] = set()
        for category_url, category in links:
            response = self.http.get(category_url)
            for html, base_url in self._paginate(response.text, response.url or category_url):
                for vacancy in self._parse(html, institution, base_url=base_url):
                    if vacancy.source_url in seen_source_urls:
                        continue
                    seen_source_urls.add(vacancy.source_url)
                    vacancies.append(replace(vacancy, category=category))

        if not vacancies:
            self.guard(page.text, url)
        return vacancies

    @staticmethod
    def _category_links(html: str, *, base_url: str) -> list[tuple[str, str]]:
        """Every categorised search link on the page, paired with its human label.

        The label comes from ``aria-label`` where the page provides one - set here
        specifically so an icon or a screen-reader-only suffix inside the link's own visible
        text does not leak into the category string - falling back to the link's plain text.
        """
        soup = soup_of(html)
        links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            if not isinstance(anchor, Tag):
                continue
            href = str(anchor["href"])
            if "corehr.com" not in href.casefold() or _CATEGORY_PARAM not in href:
                continue
            resolved = absolutise(base_url, href)
            if resolved in seen_urls:
                continue
            seen_urls.add(resolved)

            label = str(anchor.get("aria-label") or "").strip() or cell_text(anchor)
            label = _OPENS_IN_NEW_WINDOW_RE.sub("", label).strip()
            category = _TRAILING_JOBS_RE.sub("", label).strip()
            links.append((resolved, category or label))
        return links
