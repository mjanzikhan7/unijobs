"""Guards the one property nothing else checks: registration and detection order agree.

Adding a platform means editing three separate, hand-maintained lists - the import and
``__all__`` in ``crawler/adapters/__init__.py``, and ``_DETECTION_ORDER`` in
``crawler/registry.py``. Nothing about Python itself enforces that all three name the same
platforms. An adapter registered but missing from ``_DETECTION_ORDER`` is never a crash - it is
silently never selected by ``detect_adapter()``, and only the contract suite happening to run
detection against it would ever reveal the gap.
"""

from __future__ import annotations

from crawler.registry import _DETECTION_ORDER, registered_adapters
from institutions.enums import Platform


def test_every_registered_platform_is_in_the_detection_order() -> None:
    registered = set(registered_adapters())
    ordered = set(_DETECTION_ORDER)
    missing = registered - ordered
    assert not missing, f"registered but never detected: {sorted(p.value for p in missing)}"


def test_every_detection_order_entry_has_a_registered_adapter() -> None:
    registered = set(registered_adapters())
    ordered = set(_DETECTION_ORDER)
    orphaned = ordered - registered
    names = sorted(p.value for p in orphaned)
    assert not orphaned, f"in the detection order but not registered: {names}"


def test_the_detection_order_has_no_duplicates() -> None:
    assert len(_DETECTION_ORDER) == len(set(_DETECTION_ORDER))


def test_structured_is_checked_last() -> None:
    """STRUCTURED matches any page with JSON-LD or an RSS link - the one true fallback.

    Anything placed after it would never be reached. GENERIC_CARD_SCRAPE carries no equivalent
    constraint: its own ``detect()`` matches four specific hosts, not "any page shaped like X",
    so it is free to sit anywhere relative to the others.
    """
    assert _DETECTION_ORDER[-1] == Platform.STRUCTURED
