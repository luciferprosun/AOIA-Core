from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from runtime.sensitive_redaction import REDACTION_MARKER, build_current_runtime_redactor

REDACTED_PROVIDER_SECRET = REDACTION_MARKER


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

    return build_current_runtime_redactor(
        additional_values=_known_secret_values(known_secrets),
    ).redact_text(text)


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
    return build_current_runtime_redactor(
        additional_values=_known_secret_values(known_secrets),
    ).redact(value)


def redact_mapping_values(
    data: dict[Any, Any] | None,
    known_secrets: list[str] | None = None,
) -> dict[Any, Any]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TypeError("data must be a dict or None")
    redacted = build_current_runtime_redactor(
        additional_values=_known_secret_values(known_secrets),
    ).redact(data)
    assert isinstance(redacted, dict)
    return redacted
