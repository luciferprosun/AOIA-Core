from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


REDACTED = "[REDACTED_PROVIDER_SECRET]"
_SENSITIVE_FIELD_PARTS = (
    "authorization",
    "api_key",
    "api-key",
    "apikey",
    "x-goog-api-key",
    "bearer",
    "credential",
    "secret",
    "token",
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{12,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
    re.compile(
        r"(?i)\b(?:authorization|api[_ -]?key|token|secret)\s*[:=]\s*[^\s,;]+"
    ),
)


def redact_provider_text(text: object, *, known_secrets: Sequence[str] = ()) -> str:
    value = str(text)
    replacement = REDACTED
    for candidate in (REDACTED, "[MASKED]", ""):
        if not any(
            isinstance(secret, str) and secret and secret in candidate
            for secret in known_secrets
        ):
            replacement = candidate
            break
    for secret in known_secrets:
        if isinstance(secret, str) and secret:
            value = value.replace(secret, replacement)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def redact_provider_data(
    value: object,
    *,
    known_secrets: Sequence[str] = (),
) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            normalized = key_text.casefold()
            if any(part in normalized for part in _SENSITIVE_FIELD_PARTS):
                redacted[key_text] = REDACTED
            else:
                redacted[key_text] = redact_provider_data(
                    item,
                    known_secrets=known_secrets,
                )
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_provider_data(item, known_secrets=known_secrets) for item in value]
    if isinstance(value, str):
        return redact_provider_text(value, known_secrets=known_secrets)
    return value
