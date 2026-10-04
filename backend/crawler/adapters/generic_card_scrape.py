"""A shared "read the plain HTML" adapter for institutions with no recognisable ATS at all.

Recognise it by the institution's own host - deliberately, not by page content, since there is no
platform here to have a signature.
Quirk: four confirmed institutions (Queen Mary, RGU, St Mary's Belfast, RAU) are four genuinely
different templates, not one platform wearing different skin. Tries four read strategies in
order - card grid, labelled result cards, a plain table, free-text prose - and uses whichever
one the fetched page actually matches.
Browser: no. If a site blocks our honest User-Agent, the result is BLOCKED.
Example: https://www.qmul.ac.uk/jobs/vacancies/ - Queen Mary, University of London.
"""

from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from crawler.adapters.base import BaseAdapter
from crawler.extraction import absolutise, cell_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_CONFIRMED_HOSTS = ("qmul.ac.uk", "rgu.ac.uk", "smucb.ac.uk", "rau.ac.uk")

_QMUL_LABEL_RE = re.compile(r"(salary|ref|closing date)\s*:\s*(.*)", re.IGNORECASE)

_RGU_REF_FROM_URL_RE = re.compile(r"-(\d+)/?$")

_SMUCB_REF_RE = re.compile(r"\s*Ref:\s*(\S+)\s*$", re.IGNORECASE)


def _is_heading_style(style: str | None) -> bool:
    """Whether an inline ``style`` attribute is this template's 18px vacancy-heading style."""
    return style is not None and "18px" in style


@register_adapter
class GenericCardScrapeAdapter(BaseAdapter):
    """Reads whichever of three known plain-HTML shapes the fetched page actually has."""

    platform: ClassVar[Platform] = Platform.GENERIC_CARD_SCRAPE

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise one of the three confirmed institutions by host, not by content."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        host = urlparse(url).netloc
        return any(known in host for known in _CONFIRMED_HOSTS)

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Fetch the one page and read it with whichever strategy its markup matches.

        If the site blocks us, ``Blocked`` is raised and the crawl records BLOCKED. We do not
        retry in a browser to get around it.
        """
        response = self.http.get(institution.careers_url)
        self.guard(response.text, institution.careers_url)
        base_url = response.url or institution.careers_url

        soup = soup_of(response.text)
        if soup.find("div", class_="job-card") is not None:
            return self._parse_qmul(soup, institution, base_url=base_url)
        if soup.find("h3", class_="job-title") is not None:
            return self._parse_rgu(soup, institution, base_url=base_url)
        if soup.find("table", class_="table") is not None:
            return self._parse_rau(soup, institution, base_url=base_url)
        return self._parse_free_text(soup, institution, base_url=base_url)

    def _parse_qmul(
        self, soup: BeautifulSoup, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """QMUL's card grid - its own ``data-*`` attributes, and one labelled paragraph."""
        vacancies: list[RawVacancy] = []
        for card in soup.find_all("div", class_="job-card"):
            if not isinstance(card, Tag):
                continue
            link = card.find("a", href=True)
            if not isinstance(link, Tag):
                continue
            title = cell_text(link)
            if not title:
                continue

            fields = self._qmul_contact_fields(card)
            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link.get("href") or "")),
                    title=title,
                    institution_slug=institution.slug,
                    department=str(card.get("data-org") or ""),
                    category=str(card.get("data-family") or ""),
                    reference=fields.get("ref", ""),
                    salary_raw=fields.get("salary", ""),
                    contract_raw=str(card.get("data-contract") or ""),
                    closing_date=parse_uk_date(fields.get("closing date")),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _qmul_contact_fields(card: Tag) -> dict[str, str]:
        """The ``profile-card__contact`` paragraph's ``Label: value`` lines, split on ``<br>``."""
        contact = card.find("p", class_="profile-card__contact")
        if not isinstance(contact, Tag):
            return {}
        fields: dict[str, str] = {}
        for line in contact.get_text("\n").split("\n"):
            match = _QMUL_LABEL_RE.match(line.strip())
            if match:
                fields[match.group(1).casefold()] = match.group(2).strip()
        return fields

    def _parse_rgu(
        self, soup: BeautifulSoup, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """RGU's result cards - labelled salary/closing date, no department, category or ref."""
        vacancies: list[RawVacancy] = []
        for heading in soup.find_all("h3", class_="job-title"):
            if not isinstance(heading, Tag):
                continue
            title = cell_text(heading)
            if not title:
                continue
            card = heading.find_parent("div", class_="result")
            if not isinstance(card, Tag):
                continue
            link = card.find("a", class_="link-block", href=True)
            if not isinstance(link, Tag):
                continue
            source_url = absolutise(base_url, str(link.get("href") or ""))

            fields = self._rgu_labelled_fields(card)
            ref_match = _RGU_REF_FROM_URL_RE.search(source_url)

            vacancies.append(
                RawVacancy(
                    source_url=source_url,
                    title=title,
                    institution_slug=institution.slug,
                    reference=ref_match.group(1) if ref_match else "",
                    salary_raw=fields.get("salary", ""),
                    closing_date=parse_uk_date(fields.get("closing date")),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _rgu_labelled_fields(card: Tag) -> dict[str, str]:
        """Each ``<p><span class="bold">Label:</span> value</p>`` pair inside one result card."""
        fields: dict[str, str] = {}
        for paragraph in card.find_all("p"):
            if not isinstance(paragraph, Tag):
                continue
            label = paragraph.find("span", class_="bold")
            if not isinstance(label, Tag):
                continue
            label_text = cell_text(label).rstrip(":").casefold()
            full_text = cell_text(paragraph)
            fields[label_text] = full_text[len(cell_text(label)) :].strip()
        return fields

    def _parse_rau(
        self, soup: BeautifulSoup, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """RAU's plain three-column table - title, department, closing date, by position.

        No ``headers`` attribute to key cells by; the header row is skipped by requiring a title
        cell that actually links somewhere.
        """
        vacancies: list[RawVacancy] = []
        table = soup.find("table", class_="table")
        if not isinstance(table, Tag):
            return vacancies
        for row in table.find_all("tr"):
            if not isinstance(row, Tag):
                continue
            cells = [cell for cell in row.find_all("td") if isinstance(cell, Tag)]
            if len(cells) < 3:
                continue
            link = cells[0].find("a", href=True)
            if not isinstance(link, Tag):
                continue
            title = cell_text(link)
            if not title:
                continue

            vacancies.append(
                RawVacancy(
                    source_url=absolutise(base_url, str(link["href"])),
                    title=title,
                    institution_slug=institution.slug,
                    department=cell_text(cells[1]),
                    closing_date=parse_uk_date(cell_text(cells[2])),
                    strategy=self.strategy,
                )
            )
        return vacancies

    def _parse_free_text(
        self, soup: BeautifulSoup, institution: InstitutionRef, *, base_url: str
    ) -> list[RawVacancy]:
        """St Mary's Belfast - no card markup; a bold, 18px heading line per vacancy, then prose.

        Confirmed live with exactly one open vacancy; the template's own trailing ``<hr/>``
        after the closing-date paragraph is read as the boundary between vacancies in case more
        than one is ever posted at once, though that has not been observed live.
        """
        vacancies: list[RawVacancy] = []
        for heading_span in soup.find_all("span", style=_is_heading_style):
            strong = heading_span.find("strong")
            if not isinstance(strong, Tag):
                continue
            raw_title = cell_text(strong)
            if not raw_title:
                continue

            ref_match = _SMUCB_REF_RE.search(raw_title)
            title = _SMUCB_REF_RE.sub("", raw_title).strip()
            reference = ref_match.group(1) if ref_match else ""

            closing_date = None
            heading_block = heading_span.find_parent("p") or heading_span
            for sibling in heading_block.find_next_siblings():
                if not isinstance(sibling, Tag):
                    continue
                if sibling.name == "hr":
                    break
                if sibling.name != "p":
                    continue
                text = cell_text(sibling)
                if "closing date" in text.casefold():
                    closing_date = parse_uk_date(text)
                    break

            vacancies.append(
                RawVacancy(
                    source_url=base_url,
                    title=title,
                    institution_slug=institution.slug,
                    reference=reference,
                    closing_date=closing_date,
                    strategy=self.strategy,
                )
            )
        return vacancies
