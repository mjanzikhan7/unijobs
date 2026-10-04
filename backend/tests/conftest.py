"""Shared test configuration.

The most important part is :func:`no_outbound_network`. "No test uses the real internet" is
enforced, not remembered: a connection to anything but the test database, Redis or localhost
fails the test and names the host.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from accounts.enums import Role
from accounts.models import UserAccount
from screening.domain import Thresholds
from screening.models import Ruleset
from screening.services import create_ruleset_version
from tests.factories import DEFAULT_OWNER_USERNAME

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
HTML_FIXTURES = FIXTURE_ROOT / "captured_pages"

_ALLOWED_HOSTS = {"db", "redis", "localhost", "postgres", "testserver"}


class OutboundNetworkBlocked(RuntimeError):
    """A test tried to open a connection to the outside world."""


def _is_test_infrastructure(host: str) -> bool:
    """Whether ``host`` is part of the test setup, not the internet.

    Loopback and private (RFC 1918) addresses are the compose network. Checking the address range,
    not a list of names, keeps working when Docker gives ``redis`` a new address.
    """
    if host in _ALLOWED_HOSTS:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


@pytest.fixture(autouse=True)
def no_outbound_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that tries to reach a host outside the test setup.

    A crawler test suite that quietly contacts universities would be slow, unreliable and impolite
    to people who never agreed to it.
    """
    real_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else str(address)
        if isinstance(host, str) and not _is_test_infrastructure(host):
            raise OutboundNetworkBlocked(
                f"Test attempted an outbound connection to {host!r}. Adapters must be tested "
                "against cached fixtures — inject a FixtureHttpClient."
            )
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture
def html_fixture() -> Any:
    """Return a loader for committed HTML fixtures."""

    def load(relative_path: str) -> str:
        path = HTML_FIXTURES / relative_path
        if not path.exists():
            raise FileNotFoundError(
                f"Missing fixture {relative_path}. Regenerate with `make refresh-fixtures` "
                "and review the diff before committing."
            )
        return path.read_text(encoding="utf-8")

    return load


@pytest.fixture
def thresholds() -> Thresholds:
    """The August 2026 figures, written out.

    Fixed numbers are fine *here*, because this is the test that proves the banding is right.
    """
    return Thresholds(
        personal_floor=Decimal("37000"),
        current_package=Decimal("50275"),
        going_rate=Decimal("54700"),
        standard_general=Decimal("41700"),
        transitional_general=Decimal("31300"),
    )


@pytest.fixture
def ruleset(db: None) -> Ruleset:
    """An active ruleset carrying the August 2026 figures."""
    return create_ruleset_version(
        name="Test ruleset",
        effective_from=date(2026, 8, 19),
        verified_at=date(2026, 8, 22),
        source_url="https://www.gov.uk/",
        figures={
            "transitional_general_threshold": "31300",
            "standard_general_threshold": "41700",
            "soc_2134_going_rate": "54700",
            "soc_2139_going_rate": "52300",
            "soc_2133_going_rate": "54900",
            "soc_2162_going_rate": "43600",
            "soc_3131_going_rate": "35200",
            "soc_3133_going_rate": "34600",
            "current_package": "50275",
            "personal_floor": "37000",
        },
    )


def _make_user(username: str, role: Role) -> User:
    """Create a user and put them in a role, verified."""
    user = User.objects.create_user(
        username=username,
        password="not-a-real-password",
        email=f"{username}@example.test",
    )
    account = UserAccount.objects.get(user=user)
    account.role = role
    account.email_verified_at = timezone.now()
    account.save(update_fields=["role", "email_verified_at"])
    user.account = account
    return user


def _client_for(user: User) -> APIClient:
    """An API client carrying that user's token."""
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def user(db: None) -> User:
    """The operator account, with every permission.

    It has the same username as ``factories.DEFAULT_OWNER_USERNAME``, so a plain
    ``SavedJobFactory()`` in a test using ``auth_client`` belongs to that client.
    """
    return _make_user(DEFAULT_OWNER_USERNAME, Role.ADMIN)


@pytest.fixture
def manager_user(db: None) -> User:
    """Runs the estate, but cannot change threshold figures or accounts."""
    return _make_user("manager", Role.MANAGER)


@pytest.fixture
def recruiter_user(db: None) -> User:
    """An institution's own staff. Scoped to whichever institutions a test assigns them to."""
    return _make_user("recruiter", Role.RECRUITER)


@pytest.fixture
def candidate_user(db: None) -> User:
    """A job seeker. Sees jobs and their own data, and nothing operational."""
    return _make_user("candidate", Role.CANDIDATE)


@pytest.fixture
def second_candidate_user(db: None) -> User:
    """A second job seeker, for proving one candidate cannot see the other's rows."""
    return _make_user("candidate-two", Role.CANDIDATE)


@pytest.fixture
def api_client() -> APIClient:
    """An unauthenticated API client."""
    return APIClient()


@pytest.fixture
def auth_client(user: User) -> APIClient:
    """An API client carrying a valid token. The operator, so pre-role tests still pass."""
    return _client_for(user)


@pytest.fixture
def manager_client(manager_user: User) -> APIClient:
    """An API client authenticated as a manager."""
    return _client_for(manager_user)


@pytest.fixture
def recruiter_client(recruiter_user: User) -> APIClient:
    """An API client authenticated as a recruiter."""
    return _client_for(recruiter_user)


@pytest.fixture
def candidate_client(candidate_user: User) -> APIClient:
    """An API client authenticated as a candidate."""
    return _client_for(candidate_user)


@pytest.fixture
def second_candidate_client(second_candidate_user: User) -> APIClient:
    """An API client authenticated as a second, unrelated candidate."""
    return _client_for(second_candidate_user)


@pytest.fixture(autouse=True)
def clear_throttle_counters() -> Iterator[None]:
    """Reset rate limit counters between tests.

    They live in the cache, which is not rolled back like the database. Tests run in random order,
    so a leftover counter would make results depend on what ran before.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def clean_progress_stream() -> Iterator[None]:
    """Clear published crawl progress events between tests.

    The database rolls back after each test, but Redis does not. Run ids start from 1 in every test,
    so a run could otherwise see an earlier test's events.
    """
    yield

    try:
        import redis
        from django.conf import settings

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        keys = list(client.scan_iter(match="crawl:run:*", count=500))
        if keys:
            client.delete(*keys)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_adapter_registry() -> Iterator[None]:
    """Make sure every adapter is registered before each test.

    Tests run in random order, and a module that never imports an adapter would see an empty
    registry.
    """
    import crawler.adapters  # noqa: F401

    yield
