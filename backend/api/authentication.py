"""Token authentication that loads the role in the same query.

DRF's own ``TokenAuthentication`` loads the token and the user. ``RoleRequired`` also needs
``user.account`` on every request, which would cost a second query. This class does one join
instead, so ``GET /auth/me/`` needs one query, not two.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication


class RoleAwareTokenAuthentication(TokenAuthentication):
    """Authenticate by token, bringing the user's role along for the ride."""

    def authenticate_credentials(self, key: str) -> tuple[Any, Any]:
        """Resolve a token to ``(user, token)`` with the account already loaded."""
        model = self.get_model()
        try:
            token = model.objects.select_related("user", "user__account").get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token.")) from None

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)
