"""Throttles keyed on something other than the caller's IP address.

An IP limit stops one machine. It does not stop many machines trying passwords against one
account, where no single address is noisy.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class LoginUsernameThrottle(SimpleRateThrottle):
    """Limit sign-in attempts per *username*, wherever they come from.

    Used together with the IP limit. One limits an attacker's total rate. The other limits how
    fast one account can be attacked.
    """

    scope = "login_username"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        """Use the submitted username as the key, or skip when there is none.

        Lowercased, so "Alice" and "alice" share one limit.
        """
        username = ""
        if isinstance(request.data, dict):
            username = str(request.data.get("username") or "").strip().casefold()

        if not username:
            return None

        return self.cache_format % {"scope": self.scope, "ident": username[:150]}
