from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


REDACTED_PROVIDER_SECRET = "[REDACTED_PROVIDER_SECRET]"

_PROVIDER_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"AIza[0-9A-Za-z_\-]{8,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{8,}"),
    re.compile(r"gsk_[0-9A-Za-z_\-]{8,}"),
    re.compile(r"xoxb-[0-9A-Za-z\-]{8,}"),
    re.compile(r"ghp_[0-9A-Za-z_]{8,}"),
)


def _known_secret_values(known_secrets: list[str] | None) -> tuple[str, ...]:
    if not known_secrets:
        return ()
    values = {value for value in known_secrets if isinstance(value, str) and value}
    return tuple(sorted(values, key=len, reverse=True))


def redact_provider_secret(text: str | None, known_secrets: list[str] | None = None) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        raise TypeError("text must be a string or None")

    redacted = text
    for secret in _known_secret_values(known_secrets):
        redacted = redacted.replace(secret, REDACTED_PROVIDER_SECRET)
    for pattern in _PROVIDER_SECRET_PATTERNS:
        redacted = pattern.sub(REDACTED_PROVIDER_SECRET, redacted)
    return redacted


def contains_unredacted_provider_secret(
    text: str | None,
    known_secrets: list[str] | None = None,
) -> bool:
    if text is None:
        return False
    if not isinstance(text, str):
        raise TypeError("text must be a string or None")
    return redact_provider_secret(text, known_secrets) != text


def _redact_value(value: Any, known_secrets: list[str] | None) -> Any:
    if isinstance(value, str) or value is None:
        return redact_provider_secret(value, known_secrets)
    if isinstance(value, Mapping):
        return redact_mapping_values(dict(value), known_secrets)
    if isinstance(value, list):
        return [_redact_value(item, known_secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, known_secrets) for item in value)
    return value


def redact_mapping_values(
    data: dict[Any, Any] | None,
    known_secrets: list[str] | None = None,
) -> dict[Any, Any]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TypeError("data must be a dict or None")
    return {key: _redact_value(value, known_secrets) for key, value in data.items()}
