"""Loading the institutions from committed seed data.

Safe to repeat: the second ``make seed`` changes nothing. Institutions match on ``slug``, so a
moved careers URL is updated in place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from institutions.enums import InstitutionType, Nation
from institutions.models import Institution

SEED_DIR = Path(__file__).resolve().parent
INSTITUTIONS_FILE = SEED_DIR / "institutions.json"


@dataclass(frozen=True, slots=True)
class SeedResult:
    """What a seeding run did."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0

    @property
    def total(self) -> int:
        """How many rows were considered."""
        return self.created + self.updated + self.unchanged


def load_institution_records(path: Path | None = None) -> list[dict[str, object]]:
    """Read the committed institution seed file."""
    return json.loads((path or INSTITUTIONS_FILE).read_text(encoding="utf-8"))


def seed_institutions(path: Path | None = None) -> SeedResult:
    """Create or update every institution in the seed file.

    Fields a person edits (``platform``, ``adapter_override``, ``crawl_enabled``) are not touched.
    Seeding again must never undo someone's decision to turn off a site that keeps timing out.
    """
    created = updated = unchanged = 0

    for record in load_institution_records(path):
        slug = str(record["slug"])
        defaults = {
            "name": str(record["name"]),
            "nation": Nation(str(record.get("nation") or Nation.ENGLAND)).value,
            "city": str(record.get("city") or ""),
            "institution_type": InstitutionType(
                str(record.get("institution_type") or InstitutionType.UNIVERSITY)
            ).value,
            "ranking": record.get("ranking") or None,
            "careers_url": str(record.get("careers_url") or ""),
            "notes": str(record.get("notes") or ""),
        }

        institution = Institution.objects.filter(slug=slug).first()
        if institution is None:
            Institution.objects.create(slug=slug, **defaults)
            created += 1
            continue

        changes = {
            field: value
            for field, value in defaults.items()
            if getattr(institution, field) != value
        }
        if changes:
            for field, value in changes.items():
                setattr(institution, field, value)
            institution.save(update_fields=list(changes))
            updated += 1
        else:
            unchanged += 1

    return SeedResult(created=created, updated=updated, unchanged=unchanged)
