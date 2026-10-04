"""A labelled string enum that Django, DRF and pure domain code can all use.

``django.db.models.TextChoices`` would need Django inside ``screening/domain.py`` and the
adapters, which stay Django-free so they are easy to test. ``.choices()`` gives Django what it
needs at the model boundary.
"""

from __future__ import annotations

from enum import StrEnum


class LabelledEnum(StrEnum):
    """String enum whose members carry a human-readable label.

    Members are declared as ``NAME = "VALUE", "Label"``.
    """

    label: str

    def __new__(cls, value: str, label: str = "") -> LabelledEnum:
        """Attach the label to the member without making it part of the value."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label or value.replace("_", " ").capitalize()
        return member

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return Django-style ``(value, label)`` pairs."""
        return [(member.value, member.label) for member in cls]

    @classmethod
    def values(cls) -> list[str]:
        """Return every value, in declaration order."""
        return [member.value for member in cls]

    def __str__(self) -> str:
        """Return the raw value so f-strings and ORM lookups behave."""
        return self.value
