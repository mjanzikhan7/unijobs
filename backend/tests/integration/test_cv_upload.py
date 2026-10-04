"""Uploading a CV, and refusing everything that is not one.

The refusals carry more weight than the happy path here. This endpoint takes a file from anyone
who can register, so the interesting tests are the ones that hand it something hostile.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from screening.cv_text import MAX_UNCOMPRESSED_BYTES, UnreadableCV, sniff_format
from screening.models import CV, CandidateProfile, SkillTerm

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def vocabulary() -> None:
    """A handful of real terms, so extraction has something to find."""
    SkillTerm.objects.bulk_create(
        [
            SkillTerm(canonical="python", kind="skill", aliases=["python3"]),
            SkillTerm(canonical="django", kind="skill"),
            SkillTerm(canonical="kubernetes", kind="skill", aliases=["k8s"]),
            SkillTerm(canonical="higher education", kind="domain"),
            SkillTerm(canonical="senior", kind="seniority"),
            SkillTerm(canonical="phd", kind="education"),
        ]
    )


def _docx(text: str, *, padding: int = 0) -> bytes:
    """Build a real .docx, using the same library that will read it back.

    Hand-assembling the zip is possible but easy to get subtly wrong - a missing content-type
    override produces a file Word accepts and `python-docx` rejects, which would make this
    fixture test the fixture rather than the code.
    """
    import docx

    document = docx.Document()
    for line in text.splitlines():
        if line:
            document.add_paragraph(line)

    buffer = io.BytesIO()
    document.save(buffer)
    if not padding:
        return buffer.getvalue()

    bomb = io.BytesIO()
    with (
        zipfile.ZipFile(buffer, "r") as source,
        zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for item in source.infolist():
            target.writestr(item, source.read(item.filename))
        target.writestr("word/padding.xml", "0" * padding)
    return bomb.getvalue()


def _upload(client: APIClient, data: bytes, name: str = "cv.docx") -> Any:
    return client.post(
        "/api/cvs/upload/", {"file": SimpleUploadedFile(name, data)}, format="multipart"
    )


def test_a_docx_cv_is_accepted_and_parsed(candidate_client: APIClient) -> None:
    response = _upload(
        candidate_client, _docx("Senior Python and Django engineer in higher education.\nPhD.")
    )

    assert response.status_code == 201
    suggestions = response.json()["suggestions"]
    assert "python" in suggestions["skills"]
    assert "higher education" in suggestions["domains"]


def test_years_of_experience_are_read(candidate_client: APIClient) -> None:
    response = _upload(candidate_client, _docx("Python engineer with 9 years of experience."))

    assert response.json()["suggestions"]["years_experience"] == 9


def test_the_extracted_text_is_never_returned(candidate_client: APIClient) -> None:
    """The most personal thing in the database. The UI needs the suggestions, not the CV."""
    response = _upload(candidate_client, _docx("Python. Home address, phone number."))

    assert "extracted_text" not in response.json()


def test_the_stored_filename_is_not_the_uploaded_one(candidate_client: APIClient) -> None:
    """The supplied name can traverse, collide, or be PII in itself."""
    _upload(candidate_client, _docx("Python."), name="../../Jane Smith CV.docx")

    cv = CV.objects.get()
    assert "Jane Smith" not in cv.file.name
    assert ".." not in cv.file.name
    assert cv.file.name.startswith(f"cv/{cv.owner_id}/")


def test_a_file_that_is_not_a_pdf_or_docx_is_refused(candidate_client: APIClient) -> None:
    response = _upload(candidate_client, b"just some text", name="cv.txt")

    assert response.status_code == 400
    assert not CV.objects.exists()


def test_a_renamed_executable_is_refused(candidate_client: APIClient) -> None:
    """The extension says PDF. The bytes do not, and the bytes are what count."""
    response = _upload(candidate_client, b"MZ\x90\x00 this is a PE binary", name="cv.pdf")

    assert response.status_code == 400
    assert not CV.objects.exists()


def test_an_oversized_file_is_refused(candidate_client: APIClient, settings: Any) -> None:
    settings.CV_MAX_BYTES = 1024

    response = _upload(candidate_client, _docx("Python.") + b"\x00" * 4096)

    assert response.status_code == 400
    assert not CV.objects.exists()


def test_a_zip_that_is_not_a_docx_is_refused(candidate_client: APIClient) -> None:
    """A .docx is a zip, but not every zip is a .docx."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("something.txt", "not a word document")

    response = _upload(candidate_client, buffer.getvalue())

    assert response.status_code == 400


def test_a_zip_bomb_is_refused(candidate_client: APIClient) -> None:
    """Highly compressible padding: a few KB on the wire, far too much unpacked."""
    response = _upload(candidate_client, _docx("Python.", padding=MAX_UNCOMPRESSED_BYTES + 1))

    assert response.status_code == 400
    assert not CV.objects.exists()


def test_an_unreadable_upload_leaves_no_row_behind(candidate_client: APIClient) -> None:
    """A file nothing can read must not sit in storage holding personal data."""
    corrupt = _docx("Python.")[:40]

    _upload(candidate_client, corrupt)

    assert not CV.objects.exists()


def test_sniffing_rejects_empty_input() -> None:
    with pytest.raises(UnreadableCV):
        sniff_format(b"")


def test_sniffing_recognises_a_pdf() -> None:
    assert sniff_format(b"%PDF-1.7 ...") == "pdf"


def test_a_candidate_sees_only_their_own_cvs(
    candidate_client: APIClient, second_candidate_user: Any
) -> None:
    _upload(candidate_client, _docx("Python."))
    CV.objects.create(owner=second_candidate_user, original_filename="theirs.docx")

    rows = candidate_client.get("/api/cvs/").json()["results"]

    assert len(rows) == 1


def test_another_users_cv_cannot_be_downloaded(
    candidate_client: APIClient, second_candidate_client: APIClient
) -> None:
    """The only route to the bytes, so this is the whole access control for the file."""
    _upload(second_candidate_client, _docx("Python."))
    theirs = CV.objects.get()

    assert candidate_client.get(f"/api/cvs/{theirs.pk}/download/").status_code == 404


def test_the_owner_can_download_their_own(candidate_client: APIClient) -> None:
    _upload(candidate_client, _docx("Python."))
    cv = CV.objects.get()

    response = candidate_client.get(f"/api/cvs/{cv.pk}/download/")

    assert response.status_code == 200
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in response["Content-Disposition"]


def test_deleting_a_cv_removes_the_file(candidate_client: APIClient) -> None:
    """Django has not deleted files on model delete since 1.3."""
    _upload(candidate_client, _docx("Python."))
    cv = CV.objects.get()
    storage, name = cv.file.storage, cv.file.name

    candidate_client.delete(f"/api/cvs/{cv.pk}/")

    assert not storage.exists(name)


def test_suggestions_are_not_written_to_the_profile_automatically(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """Extraction is approximate; silently overwriting a curated profile is the wrong default."""
    _upload(candidate_client, _docx("Senior Python engineer."))

    assert not CandidateProfile.objects.filter(owner=candidate_user).exists()


def test_confirming_writes_the_terms_to_the_profile(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    _upload(candidate_client, _docx("Senior Python engineer, PhD."))
    cv = CV.objects.get()

    response = candidate_client.post(f"/api/cvs/{cv.pk}/apply_to_profile/", {}, format="json")

    assert response.status_code == 202
    profile = CandidateProfile.objects.get(owner=candidate_user)
    assert "python" in profile.skills


def test_the_candidate_can_edit_before_confirming(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """The parser suggests; the person decides."""
    _upload(candidate_client, _docx("Senior Python engineer."))
    cv = CV.objects.get()

    candidate_client.post(
        f"/api/cvs/{cv.pk}/apply_to_profile/",
        {"skills": ["python", "rust"], "years_experience": 12},
        format="json",
    )

    profile = CandidateProfile.objects.get(owner=candidate_user)
    assert set(profile.skills) == {"python", "rust"}
    assert profile.years_experience == 12


def test_applying_merges_rather_than_replaces(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    """A CV omitting a skill is not evidence the candidate lost it."""
    CandidateProfile.objects.create(
        owner=candidate_user, skills=["fortran"], is_active=True, years_experience=20
    )
    _upload(candidate_client, _docx("Python engineer."))
    cv = CV.objects.get()

    candidate_client.post(f"/api/cvs/{cv.pk}/apply_to_profile/", {}, format="json")

    profile = CandidateProfile.objects.get(owner=candidate_user)
    assert set(profile.skills) == {"fortran", "python"}
    assert profile.years_experience == 20


def test_replace_is_available_when_asked_for(
    candidate_client: APIClient, candidate_user: Any
) -> None:
    CandidateProfile.objects.create(owner=candidate_user, skills=["fortran"], is_active=True)
    _upload(candidate_client, _docx("Python engineer."))
    cv = CV.objects.get()

    candidate_client.post(f"/api/cvs/{cv.pk}/apply_to_profile/", {"replace": True}, format="json")

    profile = CandidateProfile.objects.get(owner=candidate_user)
    assert set(profile.skills) == {"python"}


def test_applying_someone_elses_cv_is_not_found(
    candidate_client: APIClient, second_candidate_client: APIClient
) -> None:
    _upload(second_candidate_client, _docx("Python."))
    theirs = CV.objects.get()

    response = candidate_client.post(f"/api/cvs/{theirs.pk}/apply_to_profile/", {}, format="json")

    assert response.status_code == 404
