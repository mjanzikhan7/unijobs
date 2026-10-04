"""Institution records: who we crawl, where, and with which adapter.

Reference data. Loaded once from the institutions spreadsheet, then edited by hand when a site
moves or needs a different adapter.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from institutions.enums import InstitutionType, Nation, Platform


def institution_media_path(instance: Institution, filename: str) -> str:
    """Return where an institution's logo or banner is stored.

    Uses the slug as the folder, so each institution's files are together. The uploaded file name
    is never used, only its extension in lowercase.
    """
    import uuid

    suffix = Path(filename).suffix.lower().lstrip(".") or "png"
    return f"institutions/{instance.slug or 'unfiled'}/{uuid.uuid4().hex}.{suffix}"


class InstitutionQuerySet(models.QuerySet["Institution"]):
    """Query helpers used by the crawl orchestrator and the API."""

    def crawlable(self) -> InstitutionQuerySet:
        """Institutions the orchestrator is allowed to fan out to."""
        return self.filter(crawl_enabled=True).exclude(careers_url="")


class Institution(models.Model):
    """A UK higher education institution with a careers site.

    ``slug`` is the natural key. Seeding matches on it, so running ``make seed`` again updates rows
    instead of creating duplicates.
    """

    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=255, unique=True)
    nation = models.CharField(max_length=32, choices=Nation.choices(), default=Nation.ENGLAND)
    city = models.CharField(max_length=120, blank=True)
    institution_type = models.CharField(
        max_length=32, choices=InstitutionType.choices(), default=InstitutionType.UNIVERSITY
    )
    ranking = models.PositiveIntegerField(
        null=True, blank=True, help_text="Complete University Guide position, where ranked."
    )

    website = models.URLField(max_length=500, blank=True)
    careers_url = models.URLField(max_length=500, blank=True)

    logo = models.ImageField(upload_to=institution_media_path, blank=True)
    banner = models.ImageField(upload_to=institution_media_path, blank=True)
    description = models.TextField(
        blank=True,
        help_text="Plain text shown on the institution's page. Rendered as text, never as HTML.",
    )

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(
        blank=True, help_text="Postal address, as it should be shown to a candidate."
    )

    platform = models.CharField(
        max_length=32,
        choices=Platform.choices(),
        default=Platform.UNKNOWN,
        help_text="Detected on the last successful crawl.",
    )
    adapter_override = models.CharField(
        max_length=32,
        choices=Platform.choices(),
        blank=True,
        help_text="Set from the crawl console when detection picks the wrong adapter.",
    )
    crawl_enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    recruiters = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="assigned_institutions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InstitutionQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["crawl_enabled"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self) -> str:
        """Return the everyday name."""
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        """Derive the slug from the name on first save."""
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @property
    def effective_platform(self) -> str:
        """The adapter to actually use - a human override always wins over detection."""
        return self.adapter_override or self.platform

    @property
    def careers_host(self) -> str:
        """Host of the careers URL, used as the politeness and robots.txt key."""
        if not self.careers_url:
            return ""
        return urlparse(self.careers_url).netloc.lower()
