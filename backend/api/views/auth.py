"""Sign-in.

Swap a username and password for a token, and say who a token belongs to. Every other
endpoint needs the token. A request without one gets a 401.
"""

from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth import login as start_session
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.enums import Role
from accounts.services import role_of
from api.permissions import EVERY_ROLE
from api.throttling import LoginUsernameThrottle


class LoginSerializer(serializers.Serializer[dict[str, str]]):
    """Credentials for exchanging for a token."""

    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)
    session = serializers.BooleanField(default=False)


class LoginView(APIView):
    """Sign in: a session cookie for the web app, or an API token for scripts."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    throttle_classes = [ScopedRateThrottle, LoginUsernameThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: dict, 401: dict}, auth=[])
    def post(self, request: Request) -> Response:
        """Start a session or return a token, or answer 401.

        The web app asks for a session, so no token ever reaches JavaScript. The error message is
        the same for "no such user" and "wrong password".
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Incorrect username or password.", "code": "authentication_failed"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if serializer.validated_data["session"]:
            start_session(request._request, user)
            return Response({"username": user.get_username()})

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.get_username()})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    """Report the authenticated user, and make sure the CSRF cookie is set."""

    required_roles = EVERY_ROLE

    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        """Return the current user, their role, and whether their address is confirmed.

        The frontend builds its menu from ``role``, so it calls this before showing the app.
        """
        account = getattr(request.user, "account", None)
        role = role_of(request.user)
        assigned = (
            list(request.user.assigned_institutions.order_by("name").values_list("slug", flat=True))
            if role is Role.RECRUITER
            else []
        )
        return Response(
            {
                "username": request.user.get_username(),
                "role": role,
                "email_verified": account.email_verified if account else False,
                "is_staff": request.user.is_staff,
                "assigned_institutions": assigned,
            }
        )
