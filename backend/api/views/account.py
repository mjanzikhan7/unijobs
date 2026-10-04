"""Your own account: change your details and preferences, download your data, or close it.

Different from ``api/views/users.py``, where an admin acts on *other* people. Here a person
acts on their own account. They must never be able to change their own role.
"""

from __future__ import annotations

import json
from typing import Any

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.emails import send_email_change_email
from accounts.services import ensure_account, role_of
from accounts.tokens import InvalidToken, read_email_change_token
from api.permissions import EVERY_ROLE
from api.personal_data import export_personal_data


class AccountSerializer(serializers.ModelSerializer[User]):
    """Everything the account screen shows."""

    role = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    digest_enabled = serializers.SerializerMethodField()
    pending_email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "pending_email",
            "first_name",
            "last_name",
            "role",
            "email_verified",
            "digest_enabled",
            "date_joined",
        ]
        read_only_fields = fields

    def get_role(self, obj: User) -> str:
        """The account's role. Read-only here - changing it is an administrator's action."""
        return str(role_of(obj) or "")

    def get_email_verified(self, obj: User) -> bool:
        """Whether the address has been proven."""
        account = getattr(obj, "account", None)
        return bool(account and account.email_verified)

    def get_pending_email(self, obj: User) -> str:
        """An address awaiting confirmation, so the screen can say the change is in flight."""
        account = getattr(obj, "account", None)
        return account.pending_email if account else ""

    def get_digest_enabled(self, obj: User) -> bool:
        """Whether any saved search is feeding this person's digest."""
        return obj.saved_searches.filter(digest_enabled=True).exists()


class UpdateAccountSerializer(serializers.Serializer[dict[str, Any]]):
    """The fields a person may change about themselves.

    Listed one by one. `role`, `is_staff`, `is_superuser` and `is_active` are real fields on
    `User`, and accepting any field would let anyone promote themselves.
    """

    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        """Refuse an address another account already holds."""
        holder = User.objects.filter(email__iexact=value).exclude(pk=self.context["user"].pk)
        if holder.exists():
            raise serializers.ValidationError("That address is already in use.")
        return value


class ChangePasswordSerializer(serializers.Serializer[dict[str, str]]):
    """A password change made by the account holder."""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value: str) -> str:
        """Require the current password.

        Without it, anyone at an unlocked computer could change the password and lock the owner out.
        """
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("That is not your current password.")
        return value

    def validate_new_password(self, value: str) -> str:
        """Hold it to the configured policy."""
        validate_password(value, user=self.context["user"])
        return value


class DigestPreferenceSerializer(serializers.Serializer[dict[str, bool]]):
    """Whether to receive the overnight digest."""

    digest_enabled = serializers.BooleanField()


class DeleteAccountSerializer(serializers.Serializer[dict[str, str]]):
    """Confirmation for closing an account."""

    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        """Require the password. Deleting is irreversible and cascades."""
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("That is not your password.")
        return value


class AccountView(APIView):
    """Read and change your own account."""

    required_roles = EVERY_ROLE

    @extend_schema(responses={200: AccountSerializer})
    def get(self, request: Request) -> Response:
        """Return the signed-in account."""
        return Response(AccountSerializer(request.user).data)

    @extend_schema(request=UpdateAccountSerializer, responses={200: AccountSerializer})
    def patch(self, request: Request) -> Response:
        """Change your name, or start an email change.

        A new address is **not** saved straight away. It is held as pending, and a confirmation link
        goes to the new address. Until then the account keeps the old address. Otherwise a typo, or
        someone on a stolen session, could take away the address used for account recovery.
        """
        serializer = UpdateAccountSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        user = request.user
        requested_email = data.pop("email", None)

        if data:
            for field, value in data.items():
                setattr(user, field, value)
            user.save(update_fields=list(data))

        pending = False
        if requested_email and requested_email.lower() != (user.email or "").lower():
            account = ensure_account(user)
            account.pending_email = requested_email
            account.pending_email_requested_at = timezone.now()
            account.save(update_fields=["pending_email", "pending_email_requested_at"])
            send_email_change_email(user, requested_email)
            pending = True

        body = AccountSerializer(user).data
        body["email_change_pending"] = pending
        return Response(body)

    @extend_schema(request=DeleteAccountSerializer, responses={204: None})
    def delete(self, request: Request) -> Response:
        """Close your account and everything linked to it.

        This cannot be undone. It deletes saved jobs, applications, saved searches, the profile and
        every CV. The password is required because there is no undo.
        """
        serializer = DeleteAccountSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)

        for cv in request.user.cvs.all():
            cv.delete()

        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExportPersonalDataView(APIView):
    """Download a copy of everything the service holds about you."""

    required_roles = EVERY_ROLE

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> HttpResponse:
        """Return your data as a JSON file.

        A download, not a page, so the person can keep it or give it to another service.
        """
        data = export_personal_data(request.user)
        response = HttpResponse(
            json.dumps(data, indent=2, default=str), content_type="application/json"
        )
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = f'attachment; filename="unijobs-my-data-{stamp}.json"'
        response["Cache-Control"] = "no-store"
        return response


class ConfirmEmailChangeSerializer(serializers.Serializer[dict[str, str]]):
    """The signed token from an address-change confirmation link."""

    token = serializers.CharField()


class ConfirmEmailChangeView(APIView):
    """Complete an address change from the link sent to the new address."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=ConfirmEmailChangeSerializer, responses={200: dict, 400: dict}, auth=[])
    def post(self, request: Request) -> Response:
        """Move the account to its pending address.

        No sign-in needed, on purpose. The link arrives by email, often on a device that is not
        signed
        in. The signed token names both the account and the exact address, which is enough.
        """
        serializer = ConfirmEmailChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invalid = Response(
            {"detail": "That link is invalid or has expired.", "code": "invalid_token"},
            status=status.HTTP_400_BAD_REQUEST,
        )
        try:
            user_id, new_email = read_email_change_token(serializer.validated_data["token"])
        except InvalidToken:
            return invalid

        user = User.objects.filter(pk=user_id).select_related("account").first()
        account = getattr(user, "account", None) if user else None
        if user is None or account is None:
            return invalid

        if (account.pending_email or "").lower() != new_email.lower():
            return invalid

        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response(
                {"detail": "That address is already in use.", "code": "invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.email = new_email
        user.save(update_fields=["email"])
        account.pending_email = ""
        account.pending_email_requested_at = None
        account.email_verified_at = timezone.now()
        account.save(
            update_fields=["pending_email", "pending_email_requested_at", "email_verified_at"]
        )

        return Response({"detail": "Address updated.", "email": new_email})


class ChangePasswordView(APIView):
    """Change your own password."""

    required_roles = EVERY_ROLE

    @extend_schema(request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        """Set a new password and keep this device signed in.

        Every token and every *other* session is ended, which is the point of changing a password
        you think is known. A session caller keeps its session. A token caller gets a new token.
        """
        serializer = ChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        Token.objects.filter(user=user).delete()
        if isinstance(request.auth, Token):
            token = Token.objects.create(user=user)
            return Response({"token": token.key, "detail": "Password updated."})

        update_session_auth_hash(request._request, user)
        return Response({"detail": "Password updated."})


class DigestPreferenceView(APIView):
    """Turn the overnight digest on or off."""

    required_roles = EVERY_ROLE

    @extend_schema(request=DigestPreferenceSerializer, responses={200: dict})
    def post(self, request: Request) -> Response:
        """Set the digest flag on all of this person's saved searches.

        The digest reads the flag from each saved search. One switch here is simpler, because "stop
        emailing me" is what people want.
        """
        serializer = DigestPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["digest_enabled"]

        updated = request.user.saved_searches.update(digest_enabled=enabled)
        return Response({"digest_enabled": enabled, "saved_searches_updated": updated})
