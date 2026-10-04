"""The adapter registry.

Supporting a new recruitment system means adding one decorated adapter class. Nothing in the
orchestrator should need to change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from crawler.types import InstitutionRef, ProbeResult
from institutions.enums import Platform

if TYPE_CHECKING:  # pragma: no cover - import cycle: base imports this module at runtime
    from crawler.adapters.base import BaseAdapter

_REGISTRY: dict[Platform, type[BaseAdapter]] = {}

_DETECTION_ORDER: tuple[Platform, ...] = (
    Platform.WORKDAY,
    Platform.STONEFISH,
    Platform.JOBTRAIN,
    Platform.COREHR_CATEGORISED,
    Platform.COREHR,
    Platform.EPLOY,
    Platform.ITRENT,
    Platform.HIRESERVE,
    Platform.SUCCESSFACTORS,
    Platform.CAMBRIDGE_VIEWS_TABLE,
    Platform.RAILS_JOBS_BOARD,
    Platform.CONTENSIS_JOBS,
    Platform.TALENTLINK,
    Platform.AUB_VACANCY_CARDS,
    Platform.ORACLE_FUSION,
    Platform.ENGAGE_ATS,
    Platform.GENERIC_CARD_SCRAPE,
    Platform.CHANGEWORKNOW,
    Platform.LUMINATE,
    Platform.LIPA_VACANCY_CARDS,
    Platform.NORWICH_VACANCY_CARDS,
    Platform.LEEDS_ARTS_VACANCY_CARDS,
    Platform.TALEO,
    Platform.POSTINGPANDA,
    Platform.MHR_PEOPLE_FIRST,
    Platform.DUNDEE_VACANCY_CARDS,
    Platform.TRIBEPAD,
    Platform.GUILDHALL_VACANCY_CARDS,
    Platform.RCM_VACANCY_CARDS,
    Platform.RNCM_VACANCY_CARDS,
    Platform.LIVERPOOL_HOPE_VACANCY_TABLES,
    Platform.FUNNELBACK,
    Platform.HIREFUL_CMS,
    Platform.WEBRECRUIT,
    Platform.STRUCTURED,
)


class DuplicateAdapter(RuntimeError):
    """Two adapters claim the same platform."""


def register_adapter[AdapterT: type[BaseAdapter]](adapter_class: AdapterT) -> AdapterT:
    """Register ``adapter_class`` against its declared platform."""
    platform = adapter_class.platform
    existing = _REGISTRY.get(platform)
    if existing is not None and existing is not adapter_class:
        raise DuplicateAdapter(
            f"{adapter_class.__name__} and {existing.__name__} both claim {platform}"
        )
    _REGISTRY[platform] = adapter_class
    return adapter_class


def registered_adapters() -> dict[Platform, type[BaseAdapter]]:
    """Return a copy of the registry. The contract suite parameterises over this."""
    return dict(_REGISTRY)


def adapter_for_platform(platform: Platform | str) -> type[BaseAdapter] | None:
    """Return the adapter registered for ``platform``, or ``None``."""
    try:
        return _REGISTRY.get(Platform(platform))
    except ValueError:
        return None


def detect_adapter(institution: InstitutionRef, probe: ProbeResult) -> type[BaseAdapter] | None:
    """Pick the adapter for a portal, most specific signature first."""
    for platform in _DETECTION_ORDER:
        adapter_class = _REGISTRY.get(platform)
        if adapter_class is not None and adapter_class.detect(institution, probe):
            return adapter_class
    return None
