"""The per-user record that carries a role and verification state.

Django's ``auth.User`` is left alone: swapping ``AUTH_USER_MODEL`` is a project-start decision and
this project is well past that. A one-to-one row alongside it makes "exactly one role per user" a
database invariant rather than an application convention.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from accounts.enums import Role


class UserAccount(models.Model):
    """Role and verification state for one ``auth.User``.

    Created by a signal for every user, so application code may assume it exists.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account"
    )
    role = models.CharField(max_length=16, choices=Role.choices(), default=Role.CANDIDATE)

    email_verified_at = models.DateTimeField(null=True, blank=True)

    pending_email = models.EmailField(blank=True)
    pending_email_requested_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["role"])]

    def __str__(self) -> str:
        """Return the username and role, for the shell and error messages."""
        return f"{self.user.get_username()} ({self.role})"

    @property
    def email_verified(self) -> bool:
        """Whether the address has been proven."""
        return self.email_verified_at is not None
