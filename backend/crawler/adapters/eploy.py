"""eploy portals.

Recognise it by an ``*.eploy.net`` host.
Quirk: tenants are mixed - some server-render, some inject - so HTTP is tried first, falling
back to a browser when it comes back empty, recording ``fallback_fired`` so a silent estate-wide
slowdown stays visible. Detail links are ``<id>/<slug>.html``, not any other guessed shape.
Pagination is an ASP.NET ``__doPostBack`` full-page postback, walked via
:meth:`~crawler.types.BrowserSession.render_each_page` when a browser is available.
Browser: yes - as the HTTP-empty fallback.
Example: https://cardiffuniweb.eploy.net/vacancies/vacancy-search-results.aspx - Cardiff.
"""

from __future__ import annotations

import re
from typing import ClassVar

from bs4 import Tag

from crawler.adapters.base import BaseAdapter
from crawler.enums import ExtractionStrategy
from crawler.extraction import absolutise, cell_text, looks_like_vacancy_link, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

RESULTS_SELECTOR = ".vacancies, .vacancy-list, #vacancies, [class*='vacancy']"

_NEXT_PAGE_SELECTOR = 'a:has-text("Next")'

_MULTIPLE_PAGES_RE = re.compile(r'title="Go to page \d+"')

_VACANCY_MARKERS = (
    "/vacancy/",
    "vacancydetails",
    "vacancy.aspx",
    "jobdetails",
    "/job/",
)

_ID_SLUG_HTML_RE = re.compile(r"(^|/)\d+/[\w-]+\.html(?:[?#]|$)", re.IGNORECASE)


def _looks_like_a_detail_link(href: str) -> bool:
    lowered = href.casefold()
    if any(marker in lowered for marker in _VACANCY_MARKERS):
        return True
    return bool(_ID_SLUG_HTML_RE.search(href))


@register_adapter
class EployAdapter(BaseAdapter):
    """HTTP first, browser second, and always honest about which one worked."""

    platform: ClassVar[Platform] = Platform.EPLOY

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise eploy from its host."""
        url = (probe.final_url or probe.url or institution.careers_url).casefold()
        return "eploy.net" in url or "eploy" in probe.lowered_html

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Try plain HTTP; render only if that returns nothing, or to reach later pages."""
        url = institution.careers_url
        response = self.http.get(url)
        self.guard(response.text, url)

        structured = self.structured_vacancies(response, institution)
        if structured:
            return structured

        self.strategy = ExtractionStrategy.HTML
        vacancies = self._parse(response.text, institution, base_url=response.url or url)

        if not vacancies:
            if self.browser is None:
                return vacancies
            rendered = self.render(url, wait_for_selector=RESULTS_SELECTOR)
            self.fallback_fired = True
            self.guard(rendered.text, url)
            return self._parse(rendered.text, institution, base_url=rendered.url or url)

        if self.browser is not None and _MULTIPLE_PAGES_RE.search(response.text):
            self.fallback_fired = True
            pages = self.browser.render_each_page(
                url, wait_for_selector=RESULTS_SELECTOR, next_selector=_NEXT_PAGE_SELECTOR
            )
            merged: list[RawVacancy] = []
            seen: set[str] = set()
            for page in pages:
                self.guard(page.text, url)
                for vacancy in self._parse(page.text, institution, base_url=page.url or url):
                    if vacancy.source_url not in seen:
                        seen.add(vacancy.source_url)
                        merged.append(vacancy)
            return merged

        return vacancies

    def _parse(self, html: str, institution: InstitutionRef, *, base_url: str) -> list[RawVacancy]:
        """Extract vacancies from an eploy listing."""
        soup = soup_of(html)
        vacancies: list[RawVacancy] = []
        seen: set[str] = set()

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            if not _looks_like_a_detail_link(href):
                continue
            title = cell_text(link)
            if not looks_like_vacancy_link(title, href):
                continue
            url = absolutise(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            card = self._card_for(link)
            vacancies.append(
                RawVacancy(
                    source_url=url,
                    title=title,
                    institution_slug=institution.slug,
                    salary_raw=self._labelled(card, ("salary", "pay")),
                    location_raw=self._labelled(card, ("location", "site")),
                    department=self._labelled(card, ("department", "team", "directorate")),
                    reference=self._labelled(card, ("reference", "ref")),
                    contract_raw=self._labelled(card, ("contract",)),
                    strategy=self.strategy,
                )
            )
        return vacancies

    @staticmethod
    def _card_for(link: Tag) -> Tag | None:
        """The nearest ancestor containing a ``.label`` field - the card's true boundary.

        Not the title's own wrapper: the salary and contract fields sit several levels higher.
        """
        node = link.parent
        while isinstance(node, Tag):
            if node.find(class_="label") is not None:
                return node
            node = node.parent
        return None

    @staticmethod
    def _labelled(card: Tag | None, needles: tuple[str, ...]) -> str:
        """Read a value from a card's own ``.label`` / ``.content`` field pairs, by label text.

        The label is visible text, not a ``data-label`` attribute.
        """
        if card is None:
            return ""
        for label in card.find_all(class_="label"):
            if not isinstance(label, Tag):
                continue
            if not any(needle in cell_text(label).casefold() for needle in needles):
                continue
            content = label.find_next_sibling(class_="content")
            if not isinstance(content, Tag):
                continue
            text = cell_text(content)
            if text:
                return text
        return ""
