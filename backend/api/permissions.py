"""Role-based access. A view that names no roles refuses everyone.

This replaces DRF's global ``IsAuthenticated``. A view that forgets to say who it serves
returns 403. It never serves everyone by mistake.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from rest_framework.permissions import BasePermission

from accounts.enums import Role
from accounts.services import role_of

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

ADMIN_ONLY = frozenset({Role.ADMIN})
STAFF = frozenset({Role.ADMIN, Role.MANAGER})
STAFF_OR_RECRUITER = frozenset({Role.ADMIN, Role.MANAGER, Role.RECRUITER})
EVERY_ROLE = frozenset({Role.ADMIN, Role.MANAGER, Role.RECRUITER, Role.CANDIDATE})


def is_assigned(user: Any, institution: Any) -> bool:
    """Whether ``user`` is one of ``institution``'s recruiters.

    The second half of a recruiter's write access. `STAFF_OR_RECRUITER` only says a recruiter may
    try. This says for which institution.
    """
    return institution.recruiters.filter(pk=user.pk).exists()


class RoleRequired(BasePermission):
    """Allow the request only if the view names the caller's role.

    Three settings, most specific first: ``required_roles_by_action`` for one action,
    ``required_roles_write`` for any change, then ``required_roles`` for everything else.
    """

    message = "Your account does not have access to this."

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return whether this caller's role is one the view serves."""
        allowed: Collection[Role] | None = getattr(view, "required_roles", None)
        if allowed is None:
            logger.error(
                "%s declares no required_roles, so the request was denied", type(view).__name__
            )
            return False

        role = role_of(request.user)
        if role is None:
            return False

        by_action: dict[str, Collection[Role]] | None = getattr(
            view, "required_roles_by_action", None
        )
        action: str | None = getattr(view, "action", None)
        if by_action is not None and action is not None and action in by_action:
            return role in by_action[action]

        if request.method not in SAFE_METHODS:
            write_only: Collection[Role] | None = getattr(view, "required_roles_write", None)
            if write_only is not None:
                return role in write_only

        return role in allowed


class OwnedQuerysetMixin:
    """Limit a viewset to rows the caller owns, and set the owner on new rows.

    The filter is in ``get_queryset``, not an object permission. DRF only checks object
    permissions in ``get_object``, so they do nothing for a list, where a leak would be biggest.
    It also turns "someone else's row" into a 404, not a 403, so we do not confirm the row exists.
    """

    owner_field = "owner"

    def get_queryset(self):  # noqa: ANN201 - DRF signature
        """Return only the requesting user's rows."""
        queryset = super().get_queryset()  # type: ignore[misc]
        return queryset.filter(**{self.owner_field: self.request.user})  # type: ignore[attr-defined]

    def perform_create(self, serializer: Any) -> None:
        """Set the signed-in user as the owner.

        Always from the request, never from the body, so nobody can create a row for someone else.
        """
        serializer.save(**{self.owner_field: self.request.user})  # type: ignore[attr-defined]
