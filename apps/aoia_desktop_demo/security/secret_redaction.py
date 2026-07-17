"""Secret redaction for the desktop demo.

Self-contained on purpose: the demo does not import the production
runtime's ``runtime.providers`` package (that package is wired into the
production provider-approval/audit gate machinery, which is out of scope
for a standalone chat demo). The redaction patterns below follow the same
general approach as the production runtime's own redaction utility, but
are re-implemented here so this package has no import dependency on
anything outside ``apps.aoia_desktop_demo``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "api-key",
    "apikey",
    "bearer",
    "credential",
    "secret",
    "token",
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bor-[A-Za-z0-9_-]{16,}"),  # OpenRouter-style key prefix
    re.compile(r"(?i)\b(?:authorization|api[_ -]?key|token|secret)\s*[:=]\s*[^\s,;\"']+"),
)


def redact_secret_text(text: object, *, known_secrets: Sequence[str] = ()) -> str:
    """Return ``text`` with any known secret values and common key-shaped
    substrings replaced with a fixed placeholder. Never raises."""
    try:
        value = str(text)
    except Exception:  # pragma: no cover - defensive
        return REDACTED
    for secret in known_secrets:
        if isinstance(secret, str) and secret:
            value = value.replace(secret, REDACTED)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(REDACTED, value)
    return value


def redact_secret_data(value: object, *, known_secrets: Sequence[str] = ()) -> Any:
    """Recursively redact secret-shaped values inside dicts/lists/strings."""
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).casefold()
            if any(part in key_text for part in _SENSITIVE_KEY_PARTS):
                redacted[str(key)] = REDACTED
            else:
                redacted[str(key)] = redact_secret_data(item, known_secrets=known_secrets)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_secret_data(item, known_secrets=known_secrets) for item in value]
    if isinstance(value, str):
        return redact_secret_text(value, known_secrets=known_secrets)
    return value


def redact_exception(exc: BaseException, *, known_secrets: Sequence[str] = ()) -> str:
    """Return a redacted, user-safe string for an exception."""
    return redact_secret_text(str(exc), known_secrets=known_secrets)
