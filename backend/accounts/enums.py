"""Enumerations of the accounts app.

They reach TypeScript through the generated OpenAPI schema. Add a value here and regenerate.
Never copy the list by hand in the frontend.
"""

from __future__ import annotations

from shared.enums import LabelledEnum


class Role(LabelledEnum):
    """What a user is allowed to do.

    Exactly one role per user. With several roles, the code would need a rule for which one
    wins, and that is where privilege bugs hide.
    """

    ADMIN = "ADMIN", "Administrator"
    MANAGER = "MANAGER", "Manager"
    RECRUITER = "RECRUITER", "Recruiter"
    CANDIDATE = "CANDIDATE", "Candidate"


STAFF_ROLES = frozenset({Role.ADMIN, Role.MANAGER})

RECRUITER_ROLES = frozenset({Role.RECRUITER})

ROLE_CHOICES = Role.choices()
