"""Talentlink (MrTed syndication), a UK-university ATS embedded as a JS widget.

Recognise it by an embedded ``laydisplayrapido.cfm`` script (legacy widget), or a
``data-talentlink-fo-host``/``data-lumesse-fo-host`` attribute (newer widget generation).
Quirk: the legacy listing carries no salary, so every row needs its own detail-page fetch, and
pagination follows the page's own ``Lst-NavPage`` links. The newer widget's JSON API is
robots-disallowed on every confirmed tenant - checked live via a plain ``get`` rather than
hardcoded.
Example: https://jobs.bangor.ac.uk/list.php.en?ID=QLYFK026203F3VBQB7V68LOTX - Bangor University.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import ClassVar, NoReturn
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from crawler.adapters.base import BaseAdapter
from crawler.exceptions import ParseError
from crawler.extraction import absolutise, cell_text, html_to_text, parse_uk_date, soup_of
from crawler.registry import register_adapter
from crawler.types import InstitutionRef, ProbeResult, RawVacancy
from institutions.enums import Platform

_LISTING_COMPONENT = "lay9999_lst400a"
_PAGENUM_RE = re.compile(r"[?&]pagenum=(\d+)", re.IGNORECASE)

_MAX_PAGES = 100


def _widget_script_src(html: str) -> str | None:
    """The embedded MrTed widget's own ``src``, or ``None`` if this page has none."""
    for script in soup_of(html).find_all("script", src=True):
        if not isinstance(script, Tag):
            continue
        src = str(script["src"])
        lowered = src.casefold()
        if "recruitmentplatform.com" in lowered and "laydisplayrapido.cfm" in lowered:
            return src
    return None


_FO_HOST_ATTRS: tuple[str, ...] = ("data-talentlink-fo-host", "data-lumesse-fo-host")


def _has_newer_widget(html: str) -> bool:
    """Whether the page uses Talentlink's newer widget instead of the legacy one.

    The newer widget is named by one of two attributes, from before and after the rebrand.
    """
    lowered = html.casefold()
    return any(attr in lowered for attr in _FO_HOST_ATTRS)


def _fo_host(html: str) -> str | None:
    """The newer widget's API host, from its ``*-fo-host`` attribute.

    Read from the page, not assumed. Today's sites share one host, but a new one might not.
    """
    soup = soup_of(html)
    for attr in _FO_HOST_ATTRS:
        tag = soup.find(attrs={attr: True})
        if isinstance(tag, Tag):
            host = str(tag[attr]).strip()
            if host:
                return host
    return None


def _has_class_prefix(tag: Tag, prefix: str) -> bool:
    """Whether any of ``tag``'s (possibly multi-valued) classes starts with ``prefix``."""
    classes = tag.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    return any(str(css_class).startswith(prefix) for css_class in classes)


@register_adapter
class TalentlinkAdapter(BaseAdapter):
    """Reads a Talentlink/MrTed tenant's paginated results list, then every detail page."""

    platform: ClassVar[Platform] = Platform.TALENTLINK

    @classmethod
    def detect(cls, institution: InstitutionRef, probe: ProbeResult) -> bool:
        """Recognise either generation of the embedded Talentlink widget."""
        return _widget_script_src(probe.html) is not None or _has_newer_widget(probe.html)

    def list_vacancies(self, institution: InstitutionRef) -> list[RawVacancy]:
        """Collect every detail-page URL across every page, then fetch each in turn."""
        url = institution.careers_url
        page = self.http.get(url)
        self.guard(page.text, url)

        listing_url = self._listing_url(page.text, base_url=page.url or url)
        if listing_url is None:
            if _has_newer_widget(page.text):
                self._reject_newer_widget(page.text, source_url=url)
            raise ParseError(f"{url} has no Talentlink syndication widget", url=url)

        detail_urls = self._collect_detail_urls(listing_url)
        return [
            replace(self.fetch_detail(detail_url), institution_slug=institution.slug)
            for detail_url in detail_urls
        ]

    def fetch_detail(self, url: str) -> RawVacancy:
        """Parse one Talentlink job-description page's labelled field pairs."""
        response = self.http.get(url)
        self.guard(response.text, url)
        soup = soup_of(response.text)

        title_tag = soup.find(class_="JD-Title")
        title = cell_text(title_tag if isinstance(title_tag, Tag) else None)
        if not title:
            raise ParseError(f"No title found on {url}", url=url)

        fields = self._labelled_fields(soup)
        description_html = "".join(
            str(block)
            for block in soup.find_all(id=re.compile(r"^JD-Field\d+$"))
            if isinstance(block, Tag)
        )

        return RawVacancy(
            institution_slug="pending",
            source_url=url,
            title=title,
            department=_field(fields, "department", "school"),
            reference=_field(fields, "job number"),
            salary_raw=_field(fields, "salary"),
            grade_raw=_field(fields, "grade"),
            closing_date=parse_uk_date(_field(fields, "closing date")),
            description_html=description_html,
            description_text=html_to_text(description_html),
            extra=fields,
        )

    def _reject_newer_widget(self, html: str, *, source_url: str) -> NoReturn:
        """Check, live, why the newer widget cannot be read, then say so.

        Reads the real robots.txt rule instead of hard-coding it, because it could change.
        """
        fo_host = _fo_host(html)
        if fo_host is not None:
            self.http.get(f"https://{fo_host}/fo/rest/")
        raise ParseError(
            f"{source_url} uses Talentlink's newer front-office widget, which this adapter "
            "does not yet read",
            url=source_url,
        )

    def _listing_url(self, html: str, *, base_url: str) -> str | None:
        """The results list request, built from the widget's own query string.

        All the widget's parameters (``ID``, ``LG``, ``mask``, ``browserchk``, ``JobAdlg``) are
        kept.
        Only the file name and ``component`` change, to get the plain results page.
        """
        src = _widget_script_src(html)
        if src is None:
            return None
        resolved = absolutise(base_url, src)
        split = urlsplit(resolved)
        params = {key: values[0] for key, values in parse_qs(split.query).items()}
        params["component"] = _LISTING_COMPONENT
        params.setdefault("Resultsperpage", "50")
        path = split.path.replace("laydisplayrapido.cfm", "jsoutputinitrapido.cfm")
        return urlunsplit((split.scheme, split.netloc, path, urlencode(params), ""))

    def _collect_detail_urls(self, listing_url: str) -> list[str]:
        """Every vacancy's detail-page URL, across every page the site itself links to."""
        detail_urls: list[str] = []
        seen_details: set[str] = set()
        seen_pagenums: set[str] = {"1"}
        frontier: list[str] = [listing_url]
        pages_fetched = 0

        while frontier:
            pages_fetched += 1
            if pages_fetched > _MAX_PAGES:
                raise ParseError(
                    f"{listing_url} paginates past {_MAX_PAGES} pages", url=listing_url
                )
            current = frontier.pop(0)
            response = self.http.get(current)
            self.guard(response.text, current)
            soup = soup_of(response.text)
            base = response.url or current

            for anchor in soup.find_all("a", href=True):
                if not isinstance(anchor, Tag) or not _has_class_prefix(anchor, "lstA-desc"):
                    continue
                resolved = absolutise(base, str(anchor["href"]))
                if resolved not in seen_details:
                    seen_details.add(resolved)
                    detail_urls.append(resolved)

            for nav in soup.find_all("a", class_="Lst-NavPage", href=True):
                if not isinstance(nav, Tag):
                    continue
                href = str(nav["href"])
                pagenum_match = _PAGENUM_RE.search(href)
                if pagenum_match is None or pagenum_match.group(1) in seen_pagenums:
                    continue
                seen_pagenums.add(pagenum_match.group(1))
                frontier.append(absolutise(base, href))

        return detail_urls

    @staticmethod
    def _labelled_fields(soup: BeautifulSoup) -> dict[str, str]:
        """Every ``<h4 class="JD-HDLabel">Label</h4><span class="JD-HDText">Value</span>`` pair."""
        fields: dict[str, str] = {}
        for label_tag in soup.find_all(class_="JD-HDLabel"):
            if not isinstance(label_tag, Tag):
                continue
            value_tag = label_tag.find_next_sibling(class_="JD-HDText")
            label = cell_text(label_tag)
            if label and isinstance(value_tag, Tag):
                fields[label.casefold()] = cell_text(value_tag)
        return fields


def _field(fields: dict[str, str], *label_fragments: str) -> str:
    """The value of the first field whose label contains any of ``label_fragments``."""
    for label, value in fields.items():
        if any(fragment in label for fragment in label_fragments):
            return value
    return ""
