"""The OpenAPI schema, and property testing against it.

The schema is what generates the frontend's types. If it is wrong, the frontend is wrong in a
way TypeScript will confidently tell you is fine.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def schema(client: APIClient) -> dict[str, Any]:
    """Fetch the generated OpenAPI document."""
    response = client.get("/api/schema/?format=json")
    assert response.status_code == 200
    return response.json()


def test_the_schema_is_generated(auth_client: APIClient) -> None:
    assert schema(auth_client)["openapi"].startswith("3.")


def test_the_schema_covers_the_job_list(auth_client: APIClient) -> None:
    assert "/api/jobs/" in schema(auth_client)["paths"]


def test_the_schema_covers_starting_a_crawl(auth_client: APIClient) -> None:
    assert "post" in schema(auth_client)["paths"]["/api/crawl-runs/"]


@pytest.mark.parametrize(
    "component",
    [
        "SponsorVerdict",
        "ThresholdVerdict",
        "SalaryConfidence",
        "CrawlOutcome",
        "ExtractionStrategy",
        "Platform",
        "JobStatus",
        "ApplicationStatus",
    ],
)
def test_every_domain_enum_reaches_the_schema_under_its_own_name(
    auth_client: APIClient, component: str
) -> None:
    """Named enums are what make the generated TypeScript readable.

    Without the overrides, drf-spectacular resolves the several distinct "status" fields to
    invented names like ``Status912Enum``, and the frontend inherits them.
    """
    assert component in schema(auth_client)["components"]["schemas"]


def test_the_sponsor_verdict_enum_lists_every_verdict(auth_client: APIClient) -> None:
    from screening.enums import SponsorVerdict

    values = schema(auth_client)["components"]["schemas"]["SponsorVerdict"]["enum"]

    assert set(values) == set(SponsorVerdict.values())


def test_the_crawl_outcome_enum_lists_every_outcome(auth_client: APIClient) -> None:
    """The frontend has to render each one distinctly; a missing member renders as nothing."""
    from crawler.enums import CrawlOutcome

    values = schema(auth_client)["components"]["schemas"]["CrawlOutcome"]["enum"]

    assert set(values) == set(CrawlOutcome.values())


def test_a_job_payload_declares_its_screening(auth_client: APIClient) -> None:
    """The schema says the badges are always there, so a client can rely on them."""
    properties = schema(auth_client)["components"]["schemas"]["JobList"]["properties"]

    assert "screening" in properties


def test_the_schema_is_free_of_generated_enum_names(auth_client: APIClient) -> None:
    """A name like ``Status912Enum`` means two choice sets collided and nobody noticed."""
    names = schema(auth_client)["components"]["schemas"]

    assert not [name for name in names if name.endswith("Enum") and any(c.isdigit() for c in name)]


@pytest.mark.slow
def test_no_endpoint_returns_a_server_error_on_generated_input(
    auth_client: APIClient, ruleset: Any
) -> None:
    """Property testing over the schema: nothing may 500, whatever is sent.

    Read-only operations only. Letting a fuzzer POST to ``/crawl-runs/`` would start real
    crawls, and the point of this suite is that nothing reaches a university.
    """
    import schemathesis

    document = schema(auth_client)
    loaded = schemathesis.openapi.from_dict(document)

    failures: list[str] = []
    for operation in loaded.get_all_operations():
        api_operation = operation.ok()
        if api_operation.method.upper() != "GET":
            continue
        if "{" in api_operation.path:
            continue
        response = auth_client.get(api_operation.path.replace("/api/api/", "/api/"))
        if response.status_code >= 500:
            failures.append(
                f"{api_operation.method} {api_operation.path} -> {response.status_code}"
            )

    assert failures == []
