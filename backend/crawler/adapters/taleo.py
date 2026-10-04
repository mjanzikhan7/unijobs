"""Oracle Taleo careers portals.

Recognise it by a ``taleo.net`` host.
Quirk: client-rendered, same "0 jobs matching until JS runs" shape as Jobtrain. Pagination is a
JS-click "Next" link that stays in the DOM disabled on the last page, so the stop selector must
exclude ``.navigation-link-disabled`` explicitly. Durham's site works with our honest bot
User-Agent. It used to hang when the browser pretended to be desktop Chrome.
Browser: yes - listing is client-rendered, same shape as Jobtrain.
Example: https://durham.taleo.net/careersection/du_ext/jobsearch.ftl - Durham University.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.exceptions import SiteOffline
from crawler.extraction import absolutise, cell_text, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_RESULTS_SELECTOR = "#jobList li"
_NEXT_SELECTOR = "a#next:not(.navigation-link-disabled)"
_JOB_NUMBER_RE = re.compile(r"[?&]job=(\d+)")


@register_adapter
class TaleoAdapter(BaseAdapter):
    """Walks every page a real "Next" click reveals, reading each ``jobList`` card directly."""

    platform: ClassVar[Platform] = Platform.TALEO

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Taleo from Oracle's own domain."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "taleo.net" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render every page the pager reveals, reading each card by its stable Taleo ids."""
        url = institution.careers_url
        if self.browser is None:
            raise SiteOffline(f"{url} needs a browser to render and none was provided", url=url)
        self.strategy = ExtractionStrategy.BROWSER_HTML

        pages = self.browser.render_each_page(
            url, wait_for_selector=_RESULTS_SELECTOR, next_selector=_NEXT_SELECTOR
        )
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()
        for page in pages:
            self.guard(page.text, url)
            base_url = page.url or url
            for vacancy in self._parse(page.text, institution, base_url=base_url):
                if vacancy.source_url not in seen:
                    seen.add(vacancy.source_url)
                    vacancies.append(vacancy)
        return vacancies

    def _parse(self, html: str, institution: InstitutionRef, *, base_url: str) -> list[RawVacancy]:
        """Read every ``<li id="jobNNNNNN">`` card's title, department and salary line."""
        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        for card in soup.select("#jobList > li"):
            if not isinstance(card, Tag):
                continue
            container = card.find("div", class_="multiline-data-container")
            if not isinstance(container, Tag):
                continue
            rows = container.find_all("div", recursive=False)
            if len(rows) < 2:
                continue
            title_row, detail_row = rows[0], rows[1]

            link = title_row.find("a", href=True)
            title = cell_text(link) if isinstance(link, Tag) else ""
            if not title:
                continue
            href = str(link["href"]) if isinstance(link, Tag) else ""

            spans = detail_row.find_all("span", recursive=False)
            department = cell_text(spans[0]) if spans else ""
            salary = cell_text(spans[-1]) if len(spans) > 1 else ""

            number_match = _JOB_NUMBER_RE.search(href)

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, href),
                    title=title,
                    institution_slug=institution.slug,
                    department=department,
                    salary_raw=salary,
                    reference=number_match.group(1) if number_match else "",
                    strategy=self.strategy,
                )
            )
        return vacancies
