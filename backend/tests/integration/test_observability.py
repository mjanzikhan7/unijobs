"""Request ids, JSON logs and the metrics endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from rest_framework.test import APIClient

from config.observability import JsonFormatter, RequestIdFilter
from tests.factories import JobFactory, ScreeningFactory

pytestmark = pytest.mark.django_db

_TOKEN = "metrics-test-token"


def test_every_response_carries_a_request_id(api_client: APIClient) -> None:
    response = api_client.get("/api/health/")

    assert len(response["X-Request-ID"]) == 32


def test_a_request_id_from_the_gateway_is_kept(api_client: APIClient) -> None:
    response = api_client.get("/api/health/", HTTP_X_REQUEST_ID="gateway-abc123")

    assert response["X-Request-ID"] == "gateway-abc123"


def test_an_unsafe_request_id_is_replaced(api_client: APIClient) -> None:
    """A header that could inject text into the logs is not trusted."""
    response = api_client.get("/api/health/", HTTP_X_REQUEST_ID="bad id\nforged log line")

    assert "\n" not in response["X-Request-ID"]
    assert response["X-Request-ID"] != "bad id\nforged log line"


def test_json_logs_are_one_object_per_line() -> None:
    record = logging.makeLogRecord(
        {"name": "crawler", "levelname": "INFO", "msg": "crawled %s", "args": ("bath",)}
    )
    RequestIdFilter().filter(record)

    entry = json.loads(JsonFormatter().format(record))

    assert entry["message"] == "crawled bath"
    assert entry["logger"] == "crawler"
    assert entry["request_id"] == "-"


def test_metrics_do_not_exist_without_a_token(api_client: APIClient, settings: Any) -> None:
    settings.METRICS_TOKEN = ""

    assert api_client.get("/api/metrics/").status_code == 404


def test_metrics_refuse_a_wrong_token(api_client: APIClient, settings: Any) -> None:
    settings.METRICS_TOKEN = _TOKEN

    response = api_client.get("/api/metrics/", HTTP_AUTHORIZATION="Bearer wrong")

    assert response.status_code == 404


def test_metrics_report_jobs_and_unscreened_jobs(
    api_client: APIClient, settings: Any, ruleset: Any
) -> None:
    settings.METRICS_TOKEN = _TOKEN
    ScreeningFactory(job=JobFactory(), ruleset=ruleset)
    JobFactory()

    response = api_client.get("/api/metrics/", HTTP_AUTHORIZATION=f"Bearer {_TOKEN}")
    body = response.content.decode()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain; version=0.0.4")
    assert 'unijobs_jobs{status="OPEN"} 2' in body
    assert "unijobs_jobs_unscreened 1" in body
