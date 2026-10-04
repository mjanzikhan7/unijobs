"""The structured data adapter: JSON-LD and RSS, for sites with no known platform.

**Recognise it by** ``schema.org/JobPosting`` JSON-LD or an RSS feed. It is checked last, so a
site on a known platform still uses that platform's adapter, which knows more about it.

The best case. Structured data survives theme changes that break CSS selectors.
"""

from __future__ import annotations

from typing import ClassVar

from crawler.adapters.base import BaseAdapter
from crawler.exceptions import ParseError
from crawler.extraction import extract_jsonld_jobpostings, find_rss_link
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform


@register_adapter
class StructuredDataAdapter(BaseAdapter):
    """Extracts vacancies from JSON-LD, falling back to an advertised RSS feed."""

    platform: ClassVar[Platform] = Platform.STRUCTURED

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise a page carrying JSON-LD job postings or an RSS feed link."""
        if extract_jsonld_jobpostings(probe.html):
            return True
        return find_rss_link(probe.html, probe.final_url or probe.url) is not None

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Return the structured vacancies, or fail loudly if there are none to find."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)

        vacancies = self.structured_vacancies(response, institution)
        if vacancies is None:
            raise ParseError(
                f"{url} advertised structured data but none could be extracted", url=url
            )
        return vacancies
