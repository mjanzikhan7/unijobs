"""Typed environment readers.

Settings never call ``os.environ`` directly. A missing variable that quietly becomes ``None``
fails far from its cause. These helpers fail loudly at startup instead.
"""

from __future__ import annotations

import os
from pathlib import Path

_UNSET = object()


class MissingEnvVar(RuntimeError):
    """A required environment variable is absent."""


def env_str(key: str, default: str | object = _UNSET) -> str:
    """Return ``key`` as a string, raising if it is absent and no default was given."""
    value = os.environ.get(key)
    if value is None or value == "":
        if default is _UNSET:
            raise MissingEnvVar(f"{key} is required")
        return str(default)
    return value


_PLACEHOLDER_SECRETS = frozenset(
    {
        "replace-me",
        "change-me",
        "changeme",
        "hejobs",
        "insecure-development-key",
        "dev-only-not-a-real-secret-change-me",
        "build-time-only",
        "test-secret-key",
        "e2e-password",
    }
)


def env_secret(key: str, min_length: int = 0) -> str:
    """Return ``key`` as a required secret.

    Raises if it is absent, too short, or still one of the placeholder values that the example
    files and the development stack ship with. The value itself is never put in the message.
    """
    value = env_str(key)
    if value.strip().lower() in _PLACEHOLDER_SECRETS:
        raise MissingEnvVar(f"{key} is still a placeholder value, set a real secret")
    if len(value) < min_length:
        raise MissingEnvVar(f"{key} must be at least {min_length} characters long")
    return value


def env_bool(key: str, default: bool = False) -> bool:
    """Return ``key`` as a bool. ``1/true/yes/on`` are true, case-insensitively."""
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    """Return ``key`` as an int, falling back to ``default`` when unset or unparseable."""
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # pragma: no cover - configuration error, surfaced at boot
        raise MissingEnvVar(f"{key} must be an integer, got {raw!r}") from exc


def env_float(key: str, default: float) -> float:
    """Return ``key`` as a float, falling back to ``default`` when unset or unparseable."""
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:  # pragma: no cover - configuration error, surfaced at boot
        raise MissingEnvVar(f"{key} must be a number, got {raw!r}") from exc


def env_list(key: str, default: str = "") -> list[str]:
    """Return ``key`` as a comma-separated list with empty entries dropped."""
    raw = os.environ.get(key) or default
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_path(key: str, default: str) -> Path:
    """Return ``key`` as a filesystem path."""
    return Path(env_str(key, default))
