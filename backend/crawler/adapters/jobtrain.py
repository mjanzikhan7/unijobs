"""Jobtrain portals.

Recognise it by ``jobseekersupport.jobtrain.co.uk`` in the footer, or ``/Home/Job`` and
``/Job/JobDetail?JobId=`` in the URL.
Quirk: a plain fetch returns HTTP 200 with "There are 0 jobs matching" - the list is injected by
JavaScript after load, and nothing about that response looks like a failure. Waits for a
selector, not for ``networkidle``, since the page polls and never goes idle.
Browser: yes - listing shows 0 jobs matching until its JS has run.
Example: https://www.jobs.manchester.ac.uk/Home/Job - University of Manchester.
"""

from __future__ import annotations

from typing import ClassVar

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.extraction import absolutise, cell_text, looks_like_vacancy_link, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

RESULTS_SELECTOR = "#jobResults, .job-results, .vacancy-list, [data-job-list], .jobResultsList"

EMPTY_MARKER = "there are 0 jobs matching"


@register_adapter
class JobtrainAdapter(BaseAdapter):
    """Renders the listing in a browser, because plain HTTP lies about it."""

    platform: ClassVar[Platform] = Platform.JOBTRAIN

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise Jobtrain from its support-site link or its URL shape."""
        html = probe.lowered_html
        if "jobtrain" in html:
            return True
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "/home/job" in url or "/job/jobdetail" in url or "jobtrain" in url

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Render the listing and parse it.

        Falls back to the raw HTTP response only when no browser was injected. That path
        genuinely does return zero rows, and returning them honestly - as an empty list the
        orchestrator will record as ``ZERO_RESULTS`` - is the whole point.
        """
        url = institution.careers_url
        if self.browser is not None:
            response = self.render(url, wait_for_selector=RESULTS_SELECTOR)
        else:
            response = self.http.get(url)
            self.strategy = ExtractionStrategy.HTML

        self.guard(response.text, url)
        return self._parse(response.text, institution, base_url=response.url or url)

    def _parse(self, html: str, institution: InstitutionRef, *, base_url: str) -> list[RawVacancy]:
        """Extract vacancies from a rendered Jobtrain listing."""
        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if "jobdetail" not in href.casefold() and "jobid=" not in href.casefold():
                continue
            title = cell_text(link)
            if not looks_like_vacancy_link(title, href):
                continue
            url = absolutise(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            card = link.find_parent(["li", "article", "tr", "div"])
            vacancies.append(
                RawVacancy(
                    source_url=url,
                    title=title,
                    institution_slug=institution.slug,
                    department=self._field(card, ("department", "business-unit", "category")),
                    reference=self._field(card, ("reference", "job-ref", "vacancy-ref")),
                    salary_raw=self._field(card, ("salary", "pay")),
                    location_raw=self._field(card, ("location", "site", "region")),
                    contract_raw=self._field(card, ("contract", "job-type", "type")),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _field(card: object, needles: tuple[str, ...]) -> str:
        """Read a labelled value out of a result card.

        Jobtrain tenants theme their markup heavily, so this matches on any class or data
        attribute containing the label rather than on an exact selector.
        """
        if card is None:
            return ""
        for element in card.find_all(True):  # type: ignore[attr-defined]
            attributes = " ".join(
                [
                    " ".join(element.get("class") or []),
                    str(element.get("data-field") or ""),
                    str(element.get("data-label") or ""),
                ]
            ).casefold()
            if any(needle in attributes for needle in needles):
                text = cell_text(element)
                if text:
                    return text
        return ""
