"""Loading screening seed data: the ruleset and the sponsor matches from the institutions sheet.

The sponsor seed is a shortcut, not a replacement for the matcher. It holds the legal names a
person already found for 156 of the 167 institutions, so only eleven need review.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from institutions.models import Institution
from screening.enums import SponsorVerdict
from screening.models import Ruleset, SkillTerm
from screening.services import create_ruleset_version, seed_sponsor_match

SEED_DIR = Path(__file__).resolve().parent
RULESET_FILE = SEED_DIR / "ruleset_v1.json"
SPONSORS_FILE = SEED_DIR / "institution_sponsors.json"


def seed_ruleset(path: Path | None = None) -> tuple[Ruleset, bool]:
    """Load the committed ruleset if there is no ruleset yet.

    Returns ``(ruleset, created)``. Never overwrites: replacing a ruleset in use would make stored
    verdicts impossible to explain. A change means a new version, created through the API.
    """
    existing = Ruleset.objects.order_by("-version").first()
    if existing is not None:
        return existing, False

    payload = json.loads((path or RULESET_FILE).read_text(encoding="utf-8"))
    ruleset = create_ruleset_version(
        name=payload["name"],
        effective_from=date.fromisoformat(payload["effective_from"]),
        verified_at=date.fromisoformat(payload["verified_at"]),
        source_url=payload["source_url"],
        figures=payload["figures"],
        notes=payload.get("notes", ""),
        activate=True,
    )
    return ruleset, True


_STATUS_VERDICTS: dict[str, SponsorVerdict] = {
    "ON REGISTER": SponsorVerdict.CONFIRMED,
    "NOT FOUND": SponsorVerdict.NOT_FOUND,
    "UNCONFIRMED": SponsorVerdict.NOT_FOUND,
    "VIA PARENT": SponsorVerdict.NOT_FOUND,
}


def verdict_for(record: dict[str, str]) -> tuple[SponsorVerdict, bool]:
    """Translate one seed row into ``(verdict, needs_review)``."""
    status = (record.get("register_status") or "").strip().upper()
    rating = (record.get("type_rating") or "").casefold()
    licensed_for_skilled_worker = "skilled worker" in (record.get("routes") or "").casefold()

    verdict = _STATUS_VERDICTS.get(status, SponsorVerdict.NOT_FOUND)

    if verdict == SponsorVerdict.CONFIRMED:
        if not licensed_for_skilled_worker:
            return SponsorVerdict.OTHER_ROUTE_ONLY, False
        if "worker (b rating)" in rating:
            return SponsorVerdict.B_RATED, False
        if "provisional" in rating:
            return SponsorVerdict.PROVISIONAL, False
        return SponsorVerdict.CONFIRMED, False

    return verdict, True


def seed_sponsor_matches(path: Path | None = None) -> dict[str, int]:
    """Record the legal-entity names already established in the estate spreadsheet."""
    records = json.loads((path or SPONSORS_FILE).read_text(encoding="utf-8"))
    by_slug = {institution.slug: institution for institution in Institution.objects.all()}

    counts = {"seeded": 0, "needs_review": 0, "skipped": 0}
    for record in records:
        institution = by_slug.get(record["slug"])
        if institution is None:
            counts["skipped"] += 1
            continue
        verdict, needs_review = verdict_for(record)
        seed_sponsor_match(
            institution,
            registered_legal_name=record.get("registered_legal_name") or "",
            verdict=verdict,
            needs_review=needs_review,
        )
        counts["seeded"] += 1
        counts["needs_review"] += int(needs_review)
    return counts


def seed_skill_terms(path: Path | None = None) -> dict[str, int]:
    """Load the CV parser's word list, matching on ``canonical``.

    Safe to repeat. Running it again updates aliases in place, so an admin's additions and a seed
    refresh can live together.
    """
    source = path or SEED_DIR / "skill_terms.json"
    records = json.loads(source.read_text(encoding="utf-8"))

    created = 0
    updated = 0
    for record in records:
        _, was_created = SkillTerm.objects.update_or_create(
            canonical=record["canonical"],
            defaults={"kind": record["kind"], "aliases": record.get("aliases", [])},
        )
        created += was_created
        updated += not was_created

    return {"created": created, "updated": updated, "total": len(records)}
