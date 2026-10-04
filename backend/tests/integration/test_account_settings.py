"""Your own account: details, password, digest preference, and closing it.

Separate from user administration, and deliberately narrower. An administrator can change
somebody's role; the account holder cannot change their own by any route offered here.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core import mail
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.enums import Role
from accounts.services import role_of
from screening.models import CV
from tests.factories import SavedSearchFactory

pytestmark = pytest.mark.django_db

_PASSWORD = "not-a-real-password"
_NEW = "a-perfectly-fine-passphrase"


def test_the_account_screen_reports_who_you_are(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    body = candidate_client.get("/api/account/").json()

    assert body["username"] == candidate_user.username
    assert body["role"] == "CANDIDATE"
    assert body["email_verified"] is True


def test_a_name_can_be_set(candidate_client: APIClient, candidate_user: Any) -> None:
    response = candidate_client.patch(
        "/api/account/", {"first_name": "Jahanzaib", "last_name": "Khan"}, format="json"
    )

    assert response.status_code == 200
    candidate_user.refresh_from_db()
    assert (candidate_user.first_name, candidate_user.last_name) == ("Jahanzaib", "Khan")


def test_asking_to_change_an_email_does_not_change_it_yet(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """The old address keeps working until the new one answers.

    Writing it immediately means a typo - or somebody on a hijacked session - takes away the
    address every recovery path depends on.
    """
    original = candidate_user.email

    response = candidate_client.patch("/api/account/", {"email": "new@example.test"}, format="json")

    assert response.status_code == 200
    assert response.json()["email_change_pending"] is True
    candidate_user.refresh_from_db()
    assert candidate_user.email == original
    assert candidate_user.account.pending_email == "new@example.test"


def test_an_email_another_account_holds_is_refused(
    candidate_client: APIClient, second_candidate_user: Any
) -> None:
    response = candidate_client.patch(
        "/api/account/", {"email": second_candidate_user.email}, format="json"
    )

    assert response.status_code == 400


def test_you_cannot_promote_yourself(candidate_client: APIClient, candidate_user: Any) -> None:
    """The payload names every privilege field it can. None is a serializer field here."""
    candidate_client.patch(
        "/api/account/",
        {"role": "ADMIN", "is_staff": True, "is_superuser": True, "is_active": True},
        format="json",
    )

    candidate_user.refresh_from_db()
    assert role_of(candidate_user) is Role.CANDIDATE
    assert (candidate_user.is_staff, candidate_user.is_superuser) == (False, False)


def test_asking_to_change_an_email_writes_to_the_new_address(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """Sent to the new address, not the old: the point is proving it can receive mail."""
    candidate_client.patch("/api/account/", {"email": "new@example.test"}, format="json")

    assert [message.to[0] for message in mail.outbox] == ["new@example.test"]


def test_confirming_completes_the_change(
    api_client: APIClient, candidate_client: APIClient, candidate_user: Any
) -> None:
    candidate_client.patch("/api/account/", {"email": "new@example.test"}, format="json")
    token = mail.outbox[-1].body.split("/verify-email-change/")[1].split()[0]

    response = api_client.post("/api/account/confirm-email/", {"token": token}, format="json")

    assert response.status_code == 200
    candidate_user.refresh_from_db()
    assert candidate_user.email == "new@example.test"
    assert candidate_user.account.pending_email == ""


def test_a_forged_change_token_is_refused(api_client: APIClient) -> None:
    response = api_client.post("/api/account/confirm-email/", {"token": "nope"}, format="json")

    assert response.status_code == 400


def test_a_signup_token_cannot_confirm_an_address_change(
    api_client: APIClient, candidate_client: APIClient, candidate_user: Any
) -> None:
    """Different salts, so a link minted for one purpose cannot be replayed at another."""
    from accounts.tokens import make_email_token

    candidate_client.patch("/api/account/", {"email": "new@example.test"}, format="json")

    response = api_client.post(
        "/api/account/confirm-email/",
        {"token": make_email_token(candidate_user.pk)},
        format="json",
    )

    assert response.status_code == 400


def test_a_superseded_link_no_longer_works(
    api_client: APIClient, candidate_client: APIClient
) -> None:
    """The token names an address; asking for a different one retires the earlier link."""
    candidate_client.patch("/api/account/", {"email": "first@example.test"}, format="json")
    stale = mail.outbox[-1].body.split("/verify-email-change/")[1].split()[0]
    candidate_client.patch("/api/account/", {"email": "second@example.test"}, format="json")

    assert (
        api_client.post("/api/account/confirm-email/", {"token": stale}, format="json").status_code
        == 400
    )


def test_an_address_taken_since_the_request_is_refused(
    api_client: APIClient, candidate_client: APIClient, second_candidate_user: Any
) -> None:
    """Re-checked at confirmation: somebody may have taken it in the meantime."""
    candidate_client.patch("/api/account/", {"email": "contested@example.test"}, format="json")
    token = mail.outbox[-1].body.split("/verify-email-change/")[1].split()[0]
    second_candidate_user.email = "contested@example.test"
    second_candidate_user.save(update_fields=["email"])

    response = api_client.post("/api/account/confirm-email/", {"token": token}, format="json")

    assert response.status_code == 400


def test_changing_only_a_name_sends_nothing(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    candidate_client.patch("/api/account/", {"first_name": "Jahanzaib"}, format="json")

    assert mail.outbox == []


def test_a_password_can_be_changed(candidate_client: APIClient, candidate_user: Any) -> None:
    response = candidate_client.post(
        "/api/account/password/",
        {"current_password": _PASSWORD, "new_password": _NEW},
        format="json",
    )

    assert response.status_code == 200
    candidate_user.refresh_from_db()
    assert candidate_user.check_password(_NEW)


def test_the_current_password_is_required(candidate_client: APIClient, candidate_user: Any) -> None:
    """Otherwise an unlocked browser is enough to lock the owner out of their own account."""
    response = candidate_client.post(
        "/api/account/password/",
        {"current_password": "wrong", "new_password": _NEW},
        format="json",
    )

    assert response.status_code == 400
    candidate_user.refresh_from_db()
    assert candidate_user.check_password(_PASSWORD)


def test_a_weak_new_password_is_refused(candidate_client: APIClient) -> None:
    response = candidate_client.post(
        "/api/account/password/",
        {"current_password": _PASSWORD, "new_password": "password"},
        format="json",
    )

    assert response.status_code == 400


def test_changing_a_password_hands_back_a_working_token(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """Other sessions are revoked; the one you are sitting in front of is not."""
    body = candidate_client.post(
        "/api/account/password/",
        {"current_password": _PASSWORD, "new_password": _NEW},
        format="json",
    ).json()

    fresh = APIClient()
    fresh.credentials(HTTP_AUTHORIZATION=f"Token {body['token']}")
    assert fresh.get("/api/account/").status_code == 200


def test_changing_a_password_revokes_the_old_token(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    old = Token.objects.get(user=candidate_user).key

    candidate_client.post(
        "/api/account/password/",
        {"current_password": _PASSWORD, "new_password": _NEW},
        format="json",
    )

    stale = APIClient()
    stale.credentials(HTTP_AUTHORIZATION=f"Token {old}")
    assert stale.get("/api/account/").status_code == 401


def test_the_digest_can_be_turned_off(candidate_client: APIClient, candidate_user: Any) -> None:
    SavedSearchFactory(owner=candidate_user, digest_enabled=True)

    response = candidate_client.post(
        "/api/account/digest/", {"digest_enabled": False}, format="json"
    )

    assert response.status_code == 200
    assert not candidate_user.saved_searches.filter(digest_enabled=True).exists()


def test_turning_the_digest_off_leaves_other_people_alone(
    candidate_client: APIClient, candidate_user: Any, second_candidate_user: Any
) -> None:
    SavedSearchFactory(owner=candidate_user, digest_enabled=True, name="mine")
    SavedSearchFactory(owner=second_candidate_user, digest_enabled=True, name="theirs")

    candidate_client.post("/api/account/digest/", {"digest_enabled": False}, format="json")

    assert second_candidate_user.saved_searches.filter(digest_enabled=True).exists()


def test_the_account_reports_the_digest_state(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    SavedSearchFactory(owner=candidate_user, digest_enabled=True)

    assert candidate_client.get("/api/account/").json()["digest_enabled"] is True


def test_an_account_can_be_closed(candidate_client: APIClient, candidate_user: Any) -> None:
    response = candidate_client.delete("/api/account/", {"password": _PASSWORD}, format="json")

    assert response.status_code == 204
    assert not User.objects.filter(pk=candidate_user.pk).exists()


def test_closing_requires_the_password(candidate_client: APIClient, candidate_user: Any) -> None:
    """Irreversible and cascading, so a misclick must not be enough."""
    response = candidate_client.delete("/api/account/", {"password": "wrong"}, format="json")

    assert response.status_code == 400
    assert User.objects.filter(pk=candidate_user.pk).exists()


def test_closing_removes_the_uploaded_cv_files(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """A closed account leaving CVs on disk is the worst version of this bug."""
    from django.core.files.base import ContentFile

    cv = CV.objects.create(owner=candidate_user, original_filename="cv.pdf")
    cv.file.save("cv.pdf", ContentFile(b"%PDF-1.7 x"), save=True)
    storage, name = cv.file.storage, cv.file.name

    candidate_client.delete("/api/account/", {"password": _PASSWORD}, format="json")

    assert not storage.exists(name)


def test_an_anonymous_caller_reaches_none_of_it(api_client: APIClient) -> None:
    assert api_client.get("/api/account/").status_code == 401
    assert api_client.post("/api/account/password/", {}, format="json").status_code == 401
