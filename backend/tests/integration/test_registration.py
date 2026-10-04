"""Self-registration, verification, password reset and sign-out.

Two properties carry the risk, and both are asserted directly rather than inferred: a stranger
cannot register themselves into a privileged role, and none of these endpoints reveals whether
an address already has an account.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.enums import Role
from accounts.models import UserAccount
from accounts.tasks import prune_unverified_accounts
from accounts.tokens import make_email_token

pytestmark = pytest.mark.django_db

_PASSWORD = "a-perfectly-fine-passphrase"


def _register(client: APIClient, **overrides: Any) -> Any:
    payload = {"username": "newcomer", "email": "newcomer@example.test", "password": _PASSWORD}
    return client.post("/api/auth/register/", {**payload, **overrides}, format="json")


def _verify_link_token() -> str:
    """Pull the token out of the email that was just sent."""
    body = mail.outbox[-1].body
    return body.split("/verify-email/")[1].split()[0]


def test_registering_creates_a_candidate(api_client: APIClient) -> None:
    assert _register(api_client).status_code == 202

    user = User.objects.get(username="newcomer")
    assert user.account.role == Role.CANDIDATE


def test_a_new_account_cannot_sign_in_until_verified(api_client: APIClient) -> None:
    """`is_active=False` is the gate, and it is Django's own - no parallel flag to forget."""
    _register(api_client)

    response = api_client.post(
        "/api/auth/login/", {"username": "newcomer", "password": _PASSWORD}, format="json"
    )

    assert response.status_code == 401


def test_registering_asks_for_a_role_and_does_not_get_one(api_client: APIClient) -> None:
    """The payload names every privilege field it can. None of them is a serializer field."""
    _register(
        api_client,
        role="ADMIN",
        is_staff=True,
        is_superuser=True,
    )

    user = User.objects.get(username="newcomer")
    assert (user.account.role, user.is_staff, user.is_superuser) == (Role.CANDIDATE, False, False)


def test_a_weak_password_is_refused(api_client: APIClient) -> None:
    response = _register(api_client, password="password")

    assert response.status_code == 400
    assert User.objects.filter(username="newcomer").count() == 0


def test_a_taken_username_answers_the_same_as_a_free_one(api_client: APIClient) -> None:
    """Otherwise the endpoint is a membership oracle for every username worth guessing."""
    User.objects.create_user(username="newcomer", password="x")

    first = _register(api_client, username="somebody-else", email="a@example.test")
    second = _register(api_client)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


def test_registering_sends_exactly_one_email(api_client: APIClient) -> None:
    _register(api_client)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["newcomer@example.test"]


def test_verifying_lets_the_account_sign_in(api_client: APIClient) -> None:
    _register(api_client)

    verified = api_client.post(
        "/api/auth/verify-email/", {"token": _verify_link_token()}, format="json"
    )
    signed_in = api_client.post(
        "/api/auth/login/", {"username": "newcomer", "password": _PASSWORD}, format="json"
    )

    assert verified.status_code == 200
    assert "token" in signed_in.json()


def test_verifying_records_when(api_client: APIClient) -> None:
    _register(api_client)

    api_client.post("/api/auth/verify-email/", {"token": _verify_link_token()}, format="json")

    assert UserAccount.objects.get(user__username="newcomer").email_verified_at is not None


def test_a_forged_token_is_refused(api_client: APIClient) -> None:
    response = api_client.post(
        "/api/auth/verify-email/", {"token": "not-a-real-token"}, format="json"
    )

    assert response.status_code == 400


def test_a_token_for_a_deleted_account_is_refused(api_client: APIClient) -> None:
    _register(api_client)
    token = _verify_link_token()
    User.objects.filter(username="newcomer").delete()

    assert (
        api_client.post("/api/auth/verify-email/", {"token": token}, format="json").status_code
        == 400
    )


def test_an_expired_token_is_refused(api_client: APIClient, settings: Any) -> None:
    _register(api_client)
    token = _verify_link_token()
    settings.EMAIL_VERIFICATION_MAX_AGE_SECONDS = -1

    assert (
        api_client.post("/api/auth/verify-email/", {"token": token}, format="json").status_code
        == 400
    )


def test_verifying_twice_is_harmless(api_client: APIClient) -> None:
    _register(api_client)
    token = _verify_link_token()

    first = api_client.post("/api/auth/verify-email/", {"token": token}, format="json")
    second = api_client.post("/api/auth/verify-email/", {"token": token}, format="json")

    assert (first.status_code, second.status_code) == (200, 200)


def test_a_reset_link_is_sent_to_a_real_address(api_client: APIClient, candidate_user: Any) -> None:
    response = api_client.post(
        "/api/auth/password-reset/", {"email": candidate_user.email}, format="json"
    )

    assert response.status_code == 202
    assert len(mail.outbox) == 1


def test_an_unknown_address_answers_identically(api_client: APIClient, candidate_user: Any) -> None:
    known = api_client.post(
        "/api/auth/password-reset/", {"email": candidate_user.email}, format="json"
    )
    unknown = api_client.post(
        "/api/auth/password-reset/", {"email": "nobody@example.test"}, format="json"
    )

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1


def test_a_reset_sets_the_new_password(api_client: APIClient, candidate_user: Any) -> None:
    response = api_client.post(
        "/api/auth/password-reset/confirm/",
        {
            "uid": urlsafe_base64_encode(force_bytes(candidate_user.pk)),
            "token": default_token_generator.make_token(candidate_user),
            "password": _PASSWORD,
        },
        format="json",
    )

    assert response.status_code == 200
    candidate_user.refresh_from_db()
    assert candidate_user.check_password(_PASSWORD)


def test_a_reset_revokes_existing_tokens(api_client: APIClient, candidate_user: Any) -> None:
    """Resetting is what you do when you think you are compromised."""
    Token.objects.get_or_create(user=candidate_user)

    api_client.post(
        "/api/auth/password-reset/confirm/",
        {
            "uid": urlsafe_base64_encode(force_bytes(candidate_user.pk)),
            "token": default_token_generator.make_token(candidate_user),
            "password": _PASSWORD,
        },
        format="json",
    )

    assert not Token.objects.filter(user=candidate_user).exists()


def test_a_reset_token_cannot_be_reused(api_client: APIClient, candidate_user: Any) -> None:
    payload = {
        "uid": urlsafe_base64_encode(force_bytes(candidate_user.pk)),
        "token": default_token_generator.make_token(candidate_user),
        "password": _PASSWORD,
    }
    api_client.post("/api/auth/password-reset/confirm/", payload, format="json")

    again = api_client.post("/api/auth/password-reset/confirm/", payload, format="json")

    assert again.status_code == 400


def test_a_reset_for_another_account_is_refused(
    api_client: APIClient, candidate_user: Any, second_candidate_user: Any
) -> None:
    """A token is bound to one user; pointing it at another must not work."""
    response = api_client.post(
        "/api/auth/password-reset/confirm/",
        {
            "uid": urlsafe_base64_encode(force_bytes(second_candidate_user.pk)),
            "token": default_token_generator.make_token(candidate_user),
            "password": _PASSWORD,
        },
        format="json",
    )

    assert response.status_code == 400


def test_logging_out_revokes_the_token(candidate_client: APIClient, candidate_user: Any) -> None:
    """DRF tokens never expire, so clearing only the client leaves a working credential."""
    assert candidate_client.post("/api/auth/logout/").status_code == 204

    assert not Token.objects.filter(user=candidate_user).exists()
    assert candidate_client.get("/api/jobs/").status_code == 401


def test_unverified_accounts_are_pruned(api_client: APIClient, settings: Any) -> None:
    """An unverified registration would otherwise squat a username indefinitely."""
    _register(api_client)
    User.objects.filter(username="newcomer").update(
        date_joined=timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS + 1)
    )

    assert prune_unverified_accounts() == 1
    assert not User.objects.filter(username="newcomer").exists()


def test_a_recent_unverified_account_is_left_alone(api_client: APIClient) -> None:
    _register(api_client)

    assert prune_unverified_accounts() == 0
    assert User.objects.filter(username="newcomer").exists()


def test_a_verified_account_is_never_pruned(api_client: APIClient, settings: Any) -> None:
    _register(api_client)
    api_client.post("/api/auth/verify-email/", {"token": _verify_link_token()}, format="json")
    User.objects.filter(username="newcomer").update(
        date_joined=timezone.now() - timedelta(days=settings.UNVERIFIED_ACCOUNT_TTL_DAYS + 1)
    )

    assert prune_unverified_accounts() == 0
    assert User.objects.filter(username="newcomer").exists()


def test_registration_is_throttled(api_client: APIClient) -> None:
    """Exercises the configured rate rather than an override.

    DRF caches `api_settings` at import, so reassigning `settings.REST_FRAMEWORK` in a test does
    not reach the throttle - asserting against the real 5/hour is both simpler and a truer test
    of what actually ships. Without a shared cache this limit would be per worker process and
    effectively fake, which is why `CACHES` had to be configured alongside it.
    """
    codes = [
        _register(
            api_client, username=f"person-{index}", email=f"p{index}@example.test"
        ).status_code
        for index in range(6)
    ]

    assert codes[:5] == [202] * 5
    assert codes[5] == 429


def test_login_is_throttled(api_client: APIClient, candidate_user: Any) -> None:
    """The brute-force target. 10/min, so the eleventh attempt is refused."""
    attempts = [
        api_client.post(
            "/api/auth/login/",
            {"username": candidate_user.username, "password": "wrong"},
            format="json",
        ).status_code
        for _ in range(11)
    ]

    assert attempts[:10] == [401] * 10
    assert attempts[10] == 429


def test_a_token_from_verification_is_the_signed_user(candidate_user: Any) -> None:
    """Guards the token helper itself, independently of the view that uses it."""
    from accounts.tokens import read_email_token

    assert read_email_token(make_email_token(candidate_user.pk)) == candidate_user.pk
