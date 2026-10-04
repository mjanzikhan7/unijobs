"""SAP SuccessFactors "Recruiting" portals.

Recognise it by a ``successfactors.eu``/``successfactors.com``/``sapsf.eu`` host, or either
theme's own structural markup on a custom domain fronting the same tenant.
Quirk: **every confirmed tenant's ``robots.txt`` disallows every institution-scoped search URL,
platform-wide** - real crawls report ``ROBOTS_DISALLOWED``, honoured rather than
routed around; the two themes below only matter if that policy ever changes. Classic theme needs
one click before its results table exists; Career Site Builder needs none but paginates via
``render_each_page`` on stable ``data-testid`` hooks.
Example: https://career2.successfactors.eu/careers?company=coventryun - Coventry University.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.exceptions import ParseError, SiteOffline
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

RESULTS_SELECTOR = "table#searchresults"
_SEARCH_BUTTON_SELECTOR = 'text="Search Jobs"'

_CSB_CARD_SELECTOR = '[data-testid="jobCard"]'
_CSB_NEXT_SELECTOR = '[data-testid="goToNextPageBtn"]'
_CSB_FOOTER_LABEL_RE = re.compile(r"jobcardfooterlabel", re.IGNORECASE)
_CSB_SALARY_SHAPE_RE = re.compile(r"^[£$€]?\d{1,3}(,\d{3})+|salary", re.IGNORECASE)

_CSB_LABEL_FIELDS = {
    "salary": "salary",
    "contract type": "contract",
    "closing date": "closing",
}


def _looks_like_classic_theme(lowered_html: str) -> bool:
    """The classic "Recruiting" theme's table skeleton - present before any click."""
    return 'id="searchresults"' in lowered_html and "jobtitle-link" in lowered_html


def _looks_like_career_site_builder(lowered_html: str) -> bool:
    """Career Site Builder's React root, only counted alongside a SuccessFactors reference.

    ``id="root"`` alone is far too generic - any React app uses it. Requiring a
    ``successfactors`` mention too (present in every confirmed tenant's bundled asset URLs, both
    themes) keeps this from ever matching an unrelated site.
    """
    return 'id="root"' in lowered_html and "successfactors" in lowered_html


@register_adapter
class SuccessFactorsAdapter(BaseAdapter):
    """Reads whichever of the two known SuccessFactors themes the fetched page actually is."""

    platform: ClassVar[Platform] = Platform.SUCCESSFACTORS

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise SuccessFactors from its host, or either theme's own static markup."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        if "successfactors" in url or "sapsf." in url:
            return True
        html = probe.lowered_html
        return _looks_like_classic_theme(html) or _looks_like_career_site_builder(html)

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch once, plainly, to tell the two themes apart before deciding how to render."""
        url = institution.careers_url
        probe = self.http.get(url)
        if _looks_like_career_site_builder(probe.text.casefold()):
            return self._list_career_site_builder(institution, url=url)
        return self._list_classic(institution, url=url)

    def _list_classic(self, institution: InstitutionRef, *, url: str) -> list[RawVacancy]:
        """Submit the (empty) search, then read the classic Recruiting theme's table."""
        response = self.render_after_click(
            url, click_selector=_SEARCH_BUTTON_SELECTOR, wait_for_selector=RESULTS_SELECTOR
        )
        self.guard(response.text, url)
        return self._parse_classic(response.text, institution, base_url=response.url or url)

    def _parse_classic(
        self, html: str, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """Read the classic Recruiting theme's results table."""
        soup = soup_of(html)
        table = soup.find("table", id="searchresults")
        if not isinstance(table, Tag):
            raise ParseError(f"{base_url} rendered no recognisable results table", url=base_url)

        vacancies: list[RawVacancy] = []
        for row in table.find_all("tr", class_="data-row"):
            link = row.find("a", class_="jobTitle-link")
            href = str(link.get("href") or "").strip() if link is not None else ""
            title = cell_text(link) if link is not None else ""
            if not href or not title:
                continue

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, href),
                    title=title,
                    institution_slug=institution.slug,
                    location_raw=cell_text(row.find("td", class_="colLocation")),
                    posted_date=parse_uk_date(cell_text(row.find("td", class_="colDate"))),
                    strategy=self.strategy,
                )
            )
        return vacancies

    def _list_career_site_builder(
        self, institution: InstitutionRef, *, url: str
    ) -> list[RawVacancy]:
        """Walk every page a real "Next" click reveals - results need no search submitted."""
        if self.browser is None:
            raise SiteOffline(f"{url} needs a browser to render and none was provided", url=url)

        pages = self.browser.render_each_page(
            url, wait_for_selector=_CSB_CARD_SELECTOR, next_selector=_CSB_NEXT_SELECTOR
        )
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        for page in pages:
            self.guard(page.text, url)
            base_url = page.url or url
            found = self._parse_career_site_builder(page.text, institution, base_url=base_url)
            for vacancy in found:
                if vacancy.source_url not in seen:
                    seen.add(vacancy.source_url)
                    vacancies.append(vacancy)
        return vacancies

    def _parse_career_site_builder(
        self, html: str, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """Read every ``jobCard``, by its own stable ``data-testid``s, not its hashed classes."""
        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        for card in soup.find_all(attrs={"data-testid": "jobCard"}):
            if not isinstance(card, Tag):
                continue
            link = card.find("a", class_="jobCardTitle")
            title = cell_text(link) if isinstance(link, Tag) else ""
            href = str(link.get("href") or "") if isinstance(link, Tag) else ""
            if not title or not href:
                continue

            location = card.find(attrs={"data-testid": "jobCardLocation"})
            fields = self._csb_footer_fields(card)

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, href),
                    title=title,
                    institution_slug=institution.slug,
                    location_raw=cell_text(location) if isinstance(location, Tag) else "",
                    salary_raw=fields.get("salary", ""),
                    contract_raw=fields.get("contract", ""),
                    closing_date=parse_uk_date(fields.get("closing")),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _csb_footer_fields(card: Tag) -> dict[str, str]:
        """Salary/contract/closing-date from a Career Site Builder card's footer.

        Read by label when the tenant configured one (``data-haslabel="true"``); an unlabelled
        salary is still read if its own value is unambiguous (a leading currency symbol) - an
        unlabelled contract type or closing date has no such shape and stays blank.
        """
        fields: dict[str, str] = {}
        footer = card.find(attrs={"data-testid": "jobCardFooter"})
        if not isinstance(footer, Tag):
            return fields

        for label_span in footer.find_all("span", attrs={"data-help-id": _CSB_FOOTER_LABEL_RE}):
            if not isinstance(label_span, Tag):
                continue
            value_span = label_span.find_next_sibling("span")
            if not isinstance(value_span, Tag):
                continue
            value = cell_text(value_span)
            if not value:
                continue
            if label_span.get("data-haslabel") == "true":
                label = cell_text(label_span).casefold()
                field = _CSB_LABEL_FIELDS.get(label)
                if field:
                    fields[field] = value
            elif "salary" not in fields and _CSB_SALARY_SHAPE_RE.search(value):
                fields["salary"] = value
        return fields
