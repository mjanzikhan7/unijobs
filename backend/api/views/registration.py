"""Public sign-up, address confirmation, password reset and sign-out.

Anyone can reach these endpoints, so two rules apply to all of them:

* **Sign-up cannot choose a role.** The serializer lists its fields, and ``role``,
  ``is_staff`` and ``is_superuser`` are not among them. The server sets the role.
* **Nothing here shows whether an address has an account.** Sign-up and reset give the same
  answer either way, like the login view.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import logout as end_session
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.emails import send_password_reset_email, send_verification_email
from accounts.enums import Role
from accounts.services import ensure_account
from accounts.tokens import InvalidToken, read_email_token
from api.permissions import EVERY_ROLE

_NEUTRAL_REGISTER = "Check your inbox — if that address can be registered, a link is on its way."
_NEUTRAL_RESET = "If that address has an account, a reset link is on its way."


class RegisterSerializer(serializers.Serializer[dict[str, Any]]):
    """What a stranger may send.

    A fixed list of fields, not a ModelSerializer. `is_staff` and `is_superuser` are real fields on
    `User`, and nothing here may set a role.
    """

    username = serializers.RegexField(
        r"^[\w.@+-]+$", max_length=150, help_text="Letters, digits and . @ + - _"
    )
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        """Hold registrations to Django's configured password policy."""
        validate_password(value)
        return value


class RegisterView(APIView):
    """Create a candidate account, pending address verification."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={202: dict}, auth=[])
    def post(self, request: Request) -> Response:
        """Create an account and send a confirmation link.

        The account starts with ``is_active=False``. Django's own ``ModelBackend`` refuses inactive
        users, so an unconfirmed account cannot get a token at all.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    is_active=False,
                )
                ensure_account(user, role=Role.CANDIDATE)
        except IntegrityError:
            return Response({"detail": _NEUTRAL_REGISTER}, status=status.HTTP_202_ACCEPTED)

        send_verification_email(user)
        return Response({"detail": _NEUTRAL_REGISTER}, status=status.HTTP_202_ACCEPTED)


class VerifyEmailSerializer(serializers.Serializer[dict[str, str]]):
    """The signed token from a verification link."""

    token = serializers.CharField()


class VerifyEmailView(APIView):
    """Turn a verification link into a usable account."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=VerifyEmailSerializer, responses={200: dict, 400: dict}, auth=[])
    def post(self, request: Request) -> Response:
        """Mark the address verified and let the account sign in."""
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_id = read_email_token(serializer.validated_data["token"])
        except InvalidToken as error:
            return Response(
                {"detail": str(error), "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response(
                {"detail": "That link is invalid or has expired.", "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = ensure_account(user)
        if account.email_verified_at is None:
            account.email_verified_at = timezone.now()
            account.save(update_fields=["email_verified_at"])
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        return Response({"detail": "Address confirmed. You can sign in now."})


class PasswordResetRequestSerializer(serializers.Serializer[dict[str, str]]):
    """An address to send a reset link to."""

    email = serializers.EmailField()


class PasswordResetRequestView(APIView):
    """Send a password reset link, without confirming whether the address exists."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(request=PasswordResetRequestSerializer, responses={202: dict}, auth=[])
    def post(self, request: Request) -> Response:
        """Send the link if there is somewhere to send it, and say so either way."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user is not None:
            send_password_reset_email(user)

        return Response({"detail": _NEUTRAL_RESET}, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmSerializer(serializers.Serializer[dict[str, str]]):
    """A reset link's two halves, plus the new password."""

    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        """Hold a reset to the same policy as a registration."""
        validate_password(value)
        return value


class PasswordResetConfirmView(APIView):
    """Set a new password from a reset link."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetConfirmSerializer, responses={200: dict, 400: dict}, auth=[]
    )
    def post(self, request: Request) -> Response:
        """Check the link and set the new password.

        All old tokens are deleted. People reset a password when they think the account is at risk,
        so the old tokens must stop working.
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invalid = Response(
            {"detail": "That link is invalid or has expired.", "code": "invalid_token"},
            status=status.HTTP_400_BAD_REQUEST,
        )

        try:
            user_id = force_str(urlsafe_base64_decode(data["uid"]))
        except (TypeError, ValueError, OverflowError):
            return invalid

        user = User.objects.filter(pk=user_id).first()
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return invalid

        user.set_password(data["password"])
        user.save(update_fields=["password"])
        Token.objects.filter(user=user).delete()

        return Response({"detail": "Password updated. You can sign in now."})


class LogoutView(APIView):
    """End the session and delete the caller's tokens."""

    required_roles = EVERY_ROLE

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        """End the session and delete the user's tokens.

        DRF tokens never expire. If sign-out only cleared the browser, a working credential would
        be left behind, for example on a shared computer.
        """
        Token.objects.filter(user=request.user).delete()
        end_session(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)
