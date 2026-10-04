"""An institution's logo, banner and description.

Branding is editorial: entered by an operator, never crawled or inferred. The interesting part
is that images go through the API rather than a media URL - the same rule that keeps uploaded
CVs unreachable, applied rather than carved an exception into.
"""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from institutions.models import Institution
from tests.factories import InstitutionFactory

pytestmark = pytest.mark.django_db


def _png(colour: str = "red") -> bytes:
    """A real, tiny PNG. ImageField decodes it, so bytes with the right name are not enough."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(client: APIClient, institution: Institution, **files: bytes) -> Any:
    payload = {
        name: SimpleUploadedFile(f"{name}.png", data, content_type="image/png")
        for name, data in files.items()
    }
    return client.post(f"/api/institutions/{institution.pk}/media/", payload, format="multipart")


def test_an_admin_can_write_a_description(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    response = auth_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"description": "A research-intensive university in the south west."},
        format="json",
    )

    assert response.status_code == 200
    institution.refresh_from_db()
    assert institution.description.startswith("A research-intensive")


def test_a_manager_cannot_write_a_description(manager_client: APIClient) -> None:
    """Editorial copy is an admin's, like the name and ranking."""
    institution = InstitutionFactory()

    manager_client.patch(
        f"/api/institutions/{institution.pk}/", {"description": "Mine now"}, format="json"
    )

    institution.refresh_from_db()
    assert institution.description == ""


def test_the_description_reaches_the_candidate_page(candidate_client: APIClient) -> None:
    institution = InstitutionFactory(description="Founded 1966.")

    rows = candidate_client.get(f"/api/institutions/?slug={institution.slug}").json()["results"]

    assert rows[0]["description"] == "Founded 1966."


def test_an_admin_can_write_contact_details(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    response = auth_client.patch(
        f"/api/institutions/{institution.pk}/",
        {
            "contact_email": "careers@example.ac.uk",
            "contact_phone": "01223 000000",
            "address": "Trumpington Street, Cambridge, CB2 1QA",
        },
        format="json",
    )

    assert response.status_code == 200
    institution.refresh_from_db()
    assert institution.contact_email == "careers@example.ac.uk"
    assert institution.contact_phone == "01223 000000"
    assert institution.address == "Trumpington Street, Cambridge, CB2 1QA"


def test_a_manager_cannot_write_contact_details(manager_client: APIClient) -> None:
    """Contact details are editorial, like the description - an admin's, not an operator's."""
    institution = InstitutionFactory()

    manager_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"contact_email": "mine@example.ac.uk"},
        format="json",
    )

    institution.refresh_from_db()
    assert institution.contact_email == ""


def test_contact_details_reach_the_candidate_page(candidate_client: APIClient) -> None:
    institution = InstitutionFactory(
        contact_email="careers@example.ac.uk",
        contact_phone="01223 000000",
        address="Trumpington Street, Cambridge",
    )

    rows = candidate_client.get(f"/api/institutions/?slug={institution.slug}").json()["results"]

    assert rows[0]["contact_email"] == "careers@example.ac.uk"
    assert rows[0]["contact_phone"] == "01223 000000"
    assert rows[0]["address"] == "Trumpington Street, Cambridge"


def test_a_recruiter_can_write_the_profile_of_their_own_institution(
    recruiter_client: APIClient, recruiter_user: User
) -> None:
    institution = InstitutionFactory()
    institution.recruiters.add(recruiter_user)

    response = recruiter_client.patch(
        f"/api/institutions/{institution.pk}/",
        {
            "description": "A research-intensive university.",
            "contact_email": "careers@example.ac.uk",
        },
        format="json",
    )

    assert response.status_code == 200
    institution.refresh_from_db()
    assert institution.description == "A research-intensive university."
    assert institution.contact_email == "careers@example.ac.uk"


def test_a_recruiter_cannot_write_another_institutions_profile(
    recruiter_client: APIClient,
) -> None:
    """Assigned to nothing here - every recruiter starts scoped to zero institutions."""
    institution = InstitutionFactory()

    response = recruiter_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"description": "Not theirs to write."},
        format="json",
    )

    assert response.status_code == 403
    institution.refresh_from_db()
    assert institution.description == ""


def test_a_recruiter_cannot_write_crawl_technical_fields(
    recruiter_client: APIClient, recruiter_user: User
) -> None:
    """A recruiter gets the public profile, not `MANAGER_FIELDS` or the rest of `ADMIN_FIELDS`."""
    institution = InstitutionFactory(crawl_enabled=True)
    institution.recruiters.add(recruiter_user)

    recruiter_client.patch(
        f"/api/institutions/{institution.pk}/",
        {"crawl_enabled": False, "name": "Renamed University"},
        format="json",
    )

    institution.refresh_from_db()
    assert institution.crawl_enabled is True
    assert institution.name != "Renamed University"


def test_a_recruiter_can_upload_branding_for_their_own_institution(
    recruiter_client: APIClient, recruiter_user: User
) -> None:
    institution = InstitutionFactory()
    institution.recruiters.add(recruiter_user)

    response = _upload(recruiter_client, institution, logo=_png())

    assert response.status_code == 200


def test_a_recruiter_cannot_upload_branding_for_another_institution(
    recruiter_client: APIClient,
) -> None:
    institution = InstitutionFactory()

    response = _upload(recruiter_client, institution, logo=_png())

    assert response.status_code == 403


def test_a_logo_can_be_uploaded(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    response = _upload(auth_client, institution, logo=_png())

    assert response.status_code == 200
    assert response.json()["logo_url"] == f"/api/institutions/{institution.pk}/logo/"


def test_both_images_can_go_up_at_once(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    body = _upload(auth_client, institution, logo=_png("red"), banner=_png("blue")).json()

    assert body["logo_url"] and body["banner_url"]


def test_an_institution_without_branding_reports_no_urls(candidate_client: APIClient) -> None:
    institution = InstitutionFactory()

    rows = candidate_client.get(f"/api/institutions/?slug={institution.slug}").json()["results"]

    assert (rows[0]["logo_url"], rows[0]["banner_url"]) == (None, None)


def test_a_file_that_is_not_an_image_is_refused(auth_client: APIClient) -> None:
    """The name says PNG. ImageField decodes it and finds otherwise."""
    institution = InstitutionFactory()

    response = _upload(auth_client, institution, logo=b"MZ\x90\x00 not an image at all")

    assert response.status_code == 400
    institution.refresh_from_db()
    assert not institution.logo


def test_an_empty_upload_is_refused(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    response = auth_client.post(
        f"/api/institutions/{institution.pk}/media/", {}, format="multipart"
    )

    assert response.status_code == 400


def test_replacing_a_logo_removes_the_old_file(auth_client: APIClient) -> None:
    """Otherwise every replacement orphans a file nothing will ever refer to again."""
    institution = InstitutionFactory()
    _upload(auth_client, institution, logo=_png("red"))
    institution.refresh_from_db()
    storage, old = institution.logo.storage, institution.logo.name

    _upload(auth_client, institution, logo=_png("blue"))

    institution.refresh_from_db()
    assert institution.logo.name != old
    assert not storage.exists(old)


def test_the_stored_path_ignores_the_supplied_filename(auth_client: APIClient) -> None:
    institution = InstitutionFactory()

    auth_client.post(
        f"/api/institutions/{institution.pk}/media/",
        {"logo": SimpleUploadedFile("../../escape.png", _png(), content_type="image/png")},
        format="multipart",
    )

    institution.refresh_from_db()
    assert ".." not in institution.logo.name
    assert institution.logo.name.startswith(f"institutions/{institution.slug}/")


def test_a_signed_in_candidate_can_fetch_a_logo(
    auth_client: APIClient, candidate_client: APIClient
) -> None:
    institution = InstitutionFactory()
    _upload(auth_client, institution, logo=_png())

    response = candidate_client.get(f"/api/institutions/{institution.pk}/logo/")

    assert response.status_code == 200
    assert response["X-Content-Type-Options"] == "nosniff"


def test_fetching_a_missing_logo_is_a_404(candidate_client: APIClient) -> None:
    institution = InstitutionFactory()

    assert candidate_client.get(f"/api/institutions/{institution.pk}/logo/").status_code == 404


def test_branding_needs_a_session(api_client: APIClient, auth_client: APIClient) -> None:
    """Served through the API, so it inherits the API's auth - there is no public media URL."""
    institution = InstitutionFactory()
    _upload(auth_client, institution, logo=_png())

    assert api_client.get(f"/api/institutions/{institution.pk}/logo/").status_code == 401


def test_a_candidate_cannot_upload_branding(candidate_client: APIClient) -> None:
    institution = InstitutionFactory()

    assert _upload(candidate_client, institution, logo=_png()).status_code == 403
