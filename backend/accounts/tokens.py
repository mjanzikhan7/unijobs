"""Signed links for email confirmation.

A signed token carries its own expiry, so it needs no table and no clean-up job. Changing
``SECRET_KEY`` makes every open link invalid, which is correct.

Password reset does **not** use this. It uses Django's ``PasswordResetTokenGenerator``, which
also stops working after a password change or a new login.
"""

from __future__ import annotations

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

_VERIFY_SALT = "accounts.verify-email"
_CHANGE_SALT = "accounts.change-email"


class InvalidToken(ValueError):
    """The token was forged, corrupted, or has expired."""


def make_email_token(user_id: int) -> str:
    """Return a signed, expiring token proving control of this account's address."""
    return TimestampSigner(salt=_VERIFY_SALT).sign(str(user_id))


def make_email_change_token(user_id: int, new_email: str) -> str:
    """Return a token for one specific address change.

    The address is signed into the token, not only the user id. Otherwise an old link could
    confirm a newer, different address request.
    """
    return TimestampSigner(salt=_CHANGE_SALT).sign(f"{user_id}:{new_email}")


def read_email_change_token(token: str) -> tuple[int, str]:
    """Return the ``(user_id, new_email)`` a change token authorises."""
    signer = TimestampSigner(salt=_CHANGE_SALT)
    try:
        raw = signer.unsign(token, max_age=settings.EMAIL_VERIFICATION_MAX_AGE_SECONDS)
        user_id, _, new_email = raw.partition(":")
        return int(user_id), new_email
    except (BadSignature, SignatureExpired, ValueError) as error:
        raise InvalidToken("That link is invalid or has expired.") from error


def read_email_token(token: str) -> int:
    """Return the user id a token was made for, or raise :class:`InvalidToken`.

    An expired token and a changed token give the same error. Telling them apart would tell a
    stranger whether the id exists.
    """
    signer = TimestampSigner(salt=_VERIFY_SALT)
    try:
        raw = signer.unsign(token, max_age=settings.EMAIL_VERIFICATION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired) as error:
        raise InvalidToken("That link is invalid or has expired.") from error

    try:
        return int(raw)
    except ValueError as error:  # pragma: no cover - only reachable with a forged payload
        raise InvalidToken("That link is invalid or has expired.") from error
