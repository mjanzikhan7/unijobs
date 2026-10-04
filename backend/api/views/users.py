"""Account administration.

Two rules, both so nobody gets extra rights by accident:

* **Only an admin may change a role, and never their own.** An admin who demotes themselves
  by mistake could lock every operator out.
* **Passwords are never sent back.** Setting one is a separate action.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Prefetch, QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.enums import Role
from accounts.services import ensure_account, role_of
from api.exceptions import ConflictError
from api.permissions import ADMIN_ONLY, STAFF
from institutions.models import Institution


class UserSerializer(serializers.ModelSerializer[User]):
    """An account as the admin screen shows it."""

    role = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    assigned_institutions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "role",
            "email_verified",
            "is_active",
            "date_joined",
            "last_login",
            "assigned_institutions",
        ]
        read_only_fields = ["id", "username", "date_joined", "last_login"]

    def get_role(self, obj: User) -> str:
        """Return the account's role."""
        return str(role_of(obj) or Role.CANDIDATE)

    def get_email_verified(self, obj: User) -> bool:
        """Whether the address has been proven."""
        account = getattr(obj, "account", None)
        return bool(account and account.email_verified)

    def get_assigned_institutions(self, obj: User) -> list[dict[str, str]]:
        """The institutions this account recruits for. Empty for every other role.

        Uses ``.all()``, not ``.order_by()``. ``.order_by()`` would run a new query for each row and
        undo the view's ``Prefetch``.
        """
        return [
            {"slug": institution.slug, "name": institution.name}
            for institution in obj.assigned_institutions.all()
        ]


class CreateUserSerializer(serializers.Serializer[dict[str, Any]]):
    """An account created by an admin.

    Unlike self-registration, this *can* set a role, because the caller was already checked as
    an admin. The field is declared here, so `is_superuser` still cannot come from the body.
    """

    username = serializers.RegexField(r"^[\w.@+-]+$", max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    role = serializers.ChoiceField(choices=Role.values(), default=Role.CANDIDATE.value)

    def validate_password(self, value: str) -> str:
        """Hold an admin-created account to the same policy as a registration."""
        validate_password(value)
        return value

    def validate_username(self, value: str) -> str:
        """Reject a duplicate here rather than letting the database raise."""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("That username is taken.")
        return value


class SetRoleSerializer(serializers.Serializer[dict[str, str]]):
    """A role change."""

    role = serializers.ChoiceField(choices=Role.values())


class SetInstitutionsSerializer(serializers.Serializer[dict[str, list[str]]]):
    """Which institutions a recruiter is assigned to - the complete set, not a delta."""

    institutions = serializers.ListField(child=serializers.SlugField(), allow_empty=True)


class SetPasswordSerializer(serializers.Serializer[dict[str, str]]):
    """A password an administrator is setting on someone's behalf."""

    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        """Hold it to the configured policy."""
        validate_password(value)
        return value


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Read accounts. Create and change them as an admin.

    Managers can see the list, because running the service means knowing who uses it. Only an
    admin can change anything.
    """

    required_roles = STAFF
    required_roles_write = ADMIN_ONLY

    serializer_class = UserSerializer
    filterset_fields = ["is_active"]

    def get_queryset(self) -> QuerySet[User]:
        """Load each account with its role and assigned institutions in one query."""
        return (
            User.objects.select_related("account")
            .prefetch_related(
                Prefetch("assigned_institutions", queryset=Institution.objects.order_by("name"))
            )
            .order_by("username")
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create an account that is already verified.

        An admin who hands out a login has checked the address another way, so no email link is
        needed.
        """
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.create_user(
            username=data["username"], email=data["email"], password=data["password"]
        )
        account = ensure_account(user, role=Role(data["role"]))
        from django.utils import timezone

        account.role = Role(data["role"])
        account.email_verified_at = timezone.now()
        account.save(update_fields=["role", "email_verified_at"])

        return Response(
            UserSerializer(self.get_queryset().get(pk=user.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=SetRoleSerializer, responses={200: UserSerializer})
    @action(detail=True, methods=["post"], url_path="set-role")
    def set_role(self, request: Request, pk: str | None = None) -> Response:
        """Change an account's role.

        Refused for your own account. If you are the only admin and demote yourself by mistake,
        nobody can reach the operator screens any more.
        """
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ConflictError(
                "You cannot change your own role. Ask another administrator.",
                extra={"reason": "self"},
            )

        serializer = SetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = ensure_account(user)
        account.role = Role(serializer.validated_data["role"])
        account.save(update_fields=["role"])

        return Response(UserSerializer(self.get_queryset().get(pk=user.pk)).data)

    @extend_schema(request=SetInstitutionsSerializer, responses={200: UserSerializer})
    @action(detail=True, methods=["post"], url_path="set-institutions")
    def set_institutions(self, request: Request, pk: str | None = None) -> Response:
        """Set the institutions this account recruits for. Replaces the old list.

        Only for a `RECRUITER`. Other roles already see all institutions or none, so this would be a
        row nothing reads.
        """
        user = self.get_object()
        if role_of(user) is not Role.RECRUITER:
            raise ConflictError(
                "Only a recruiter can be assigned institutions.", extra={"reason": "not_recruiter"}
            )

        serializer = SetInstitutionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slugs = serializer.validated_data["institutions"]

        institutions = list(Institution.objects.filter(slug__in=slugs))
        found = {institution.slug for institution in institutions}
        missing = set(slugs) - found
        if missing:
            raise serializers.ValidationError(
                {
                    "institutions": [
                        f"No institution with slug '{slug}'." for slug in sorted(missing)
                    ]
                }
            )

        user.assigned_institutions.set(institutions)
        return Response(UserSerializer(self.get_queryset().get(pk=user.pk)).data)

    @extend_schema(request=None, responses={200: UserSerializer})
    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        """Suspend an account and delete its tokens.

        Suspending, not deleting. Deleting would also delete the person's applications and saved
        jobs, and suspending is almost always what "remove this person" means.
        """
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ConflictError("You cannot deactivate your own account.", extra={"reason": "self"})

        user.is_active = False
        user.save(update_fields=["is_active"])
        Token.objects.filter(user=user).delete()

        return Response(UserSerializer(self.get_queryset().get(pk=user.pk)).data)

    @extend_schema(request=None, responses={200: UserSerializer})
    @action(detail=True, methods=["post"])
    def reactivate(self, request: Request, pk: str | None = None) -> Response:
        """Let a suspended account sign in again."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(UserSerializer(self.get_queryset().get(pk=user.pk)).data)

    @extend_schema(request=SetPasswordSerializer, responses={204: None})
    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request: Request, pk: str | None = None) -> Response:
        """Set a password on someone's behalf, revoking their existing tokens."""
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        Token.objects.filter(user=user).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
