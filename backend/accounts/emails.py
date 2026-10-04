"""The account emails: confirm your address, change your address, reset your password.

Plain text, built here. Each one is a few lines, so template files would add more than they
save.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.tokens import make_email_change_token, make_email_token

logger = logging.getLogger(__name__)


def _link(path: str) -> str:
    """Build a link into the SPA, which is a different origin from the API."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}{path}"


def _send(*, subject: str, message: str, recipient: str) -> bool:
    """Send one message. If the mail server cannot be reached, report it instead of raising.

    Raising would turn "no mail server" into a 500 on sign-up, after the account was already
    created.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except OSError:
        logger.exception(
            "could not send %r to %s. Is a mail server listening on %s:%s? In development that "
            "is Mailpit, read at http://localhost:8025",
            subject,
            recipient,
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
        )
        return False
    return True


def send_verification_email(user: User) -> bool:
    """Ask a new account to confirm the address it signed up with.

    Returns whether the email was sent. A failure here must not fail the sign-up, because the
    account exists either way. An admin can confirm it with ``manage.py verify_user``.
    """
    if not user.email:
        logger.info("verification email skipped for %s: no address", user.pk)
        return False

    url = _link(f"/verify-email/{make_email_token(user.pk)}")
    hours = settings.EMAIL_VERIFICATION_MAX_AGE_SECONDS // 3600
    return _send(
        subject="Confirm your UniJobs address",
        message=(
            f"Hello {user.get_username()},\n\n"
            f"Confirm your address to finish setting up your account:\n\n"
            f"  {url}\n\n"
            f"The link works for {hours} hours. If you did not sign up, ignore this email — "
            f"the account cannot be used until the address is confirmed.\n"
        ),
        recipient=user.email,
    )


def send_password_reset_email(user: User) -> bool:
    """Send a reset link, using Django's own generator rather than a hand-rolled token."""
    if not user.email:
        logger.info("reset email skipped for %s: no address", user.pk)
        return False

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    url = _link(f"/reset-password/{uid}/{default_token_generator.make_token(user)}")
    return _send(
        subject="Reset your UniJobs password",
        message=(
            f"Hello {user.get_username()},\n\n"
            f"Set a new password here:\n\n"
            f"  {url}\n\n"
            f"The link stops working once it is used, or once you next sign in. If you did not "
            f"ask for this, nothing has changed and you can ignore this email.\n"
        ),
        recipient=user.email,
    )


def send_email_change_email(user: User, new_email: str) -> bool:
    """Ask the *new* address to confirm itself before the account moves to it.

    Sent to the new address, to prove the person can receive mail there. The account keeps its
    old address until the link is followed, so a typo does not lose the account.
    """
    url = _link(f"/verify-email-change/{make_email_change_token(user.pk, new_email)}")
    hours = settings.EMAIL_VERIFICATION_MAX_AGE_SECONDS // 3600
    return _send(
        subject="Confirm your new UniJobs address",
        message=(
            f"Hello {user.get_username()},\n\n"
            f"You asked to change your UniJobs address to this one. Confirm it here:\n\n"
            f"  {url}\n\n"
            f"The link works for {hours} hours. Until you follow it, your account keeps its "
            f"existing address. If you did not ask for this, ignore this email — nothing has "
            f"changed.\n"
        ),
        recipient=new_email,
    )
