from __future__ import annotations

import math
import re
from collections import Counter
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
    re.compile(
        r"(?i)\bauthorization\s*[:=]\s*(?:bearer|basic)\s+"
        r"[A-Za-z0-9._~+/=-]{4,}"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{12,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
    re.compile(
        r"(?i)\b(?:authorization|api[_ -]?key|token|secret|password|credential)"
        r"\s*[:=]\s*[^\s,;]+"
    ),
)
_TOKEN_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9_-])[A-Za-z0-9_+/=-]{40,}(?![A-Za-z0-9_-])"
)
_IDENTITY_COMPONENT_SEPARATOR = re.compile(r"[-_]")
_READABLE_IDENTITY_WORD = re.compile(
    r"(?:[a-z]{1,24}|[A-Z]{1,12}|[A-Z][a-z]{1,23})"
)
_READABLE_IDENTITY_COMPONENT = re.compile(
    r"(?:"
    r"[a-z]{1,24}"
    r"|[A-Z]{1,12}"
    r"|[A-Z][a-z]{1,23}"
    r"|[A-Za-z][0-9]{1,4}"
    r"|[0-9]{1,6}[A-Za-z]?"
    r"|[a-z]{2,20}[0-9]{1,4}"
    r"|[A-Z][a-z]{1,19}[0-9]{1,4}"
    r"|[A-Z]{2,12}[0-9]{1,4}"
    r"|[0-9a-fA-F]{7,32}"
    r")"
)
_READABLE_BRANCH_PREFIX = re.compile(r"[a-z][a-z0-9_-]{1,31}")
_OSC_ESCAPE = re.compile(r"\x1b\][^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)")
_CSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_SINGLE_ESCAPE = re.compile(r"\x1b[@-_]")
_UNSAFE_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_UNSAFE_DIRECTIONAL_FORMATTING = re.compile(
    r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]"
)


def sanitize_provider_display_text(text: object) -> str:
    """Return deterministic terminal-safe display text without granting trust."""

    value = str(text)
    value = _OSC_ESCAPE.sub("", value)
    value = _CSI_ESCAPE.sub("", value)
    value = _SINGLE_ESCAPE.sub("", value)
    value = value.replace("\x1b", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = value.replace("\b", "")
    value = _UNSAFE_CONTROLS.sub("", value)
    return _UNSAFE_DIRECTIONAL_FORMATTING.sub("", value)


def _is_readable_display_identity(value: str) -> bool:
    """Recognize structured display identity without trusting opaque segments."""

    if "+" in value or "=" in value:
        return False
    if "/" not in value:
        return _is_readable_identity_segment(value, allow_simple=False)

    absolute = value.startswith("/")
    trimmed = value[1:] if absolute else value
    if trimmed.endswith("/"):
        trimmed = trimmed[:-1]
    segments = tuple(trimmed.split("/"))
    if not segments or any(not segment for segment in segments):
        return False
    if absolute:
        if len(segments) < 2:
            return False
    elif len(segments) < 2 or not _READABLE_BRANCH_PREFIX.fullmatch(segments[0]):
        return False
    return all(
        _is_readable_identity_segment(segment, allow_simple=True)
        for segment in segments
    )


def _is_readable_identity_segment(value: str, *, allow_simple: bool) -> bool:
    if re.fullmatch(r"[0-9a-fA-F]{40,}", value):
        return True
    components = tuple(_IDENTITY_COMPONENT_SEPARATOR.split(value))
    if not components or any(not component for component in components):
        return False
    if any(
        not _READABLE_IDENTITY_COMPONENT.fullmatch(component)
        for component in components
    ):
        return False
    if len(components) == 1:
        return allow_simple
    if not allow_simple and len(components) < 3:
        return False
    readable_words = sum(
        bool(_READABLE_IDENTITY_WORD.fullmatch(component))
        for component in components
    )
    return readable_words >= 2


def _redact_opaque_candidate(match: re.Match[str], *, replacement: str) -> str:
    value = match.group(0)
    if re.fullmatch(r"[0-9a-f]{64}", value):
        return value
    if _is_readable_display_identity(value):
        return value
    classes = sum(
        bool(pattern.search(value))
        for pattern in (
            re.compile(r"[a-z]"),
            re.compile(r"[A-Z]"),
            re.compile(r"[0-9]"),
            re.compile(r"[_+/=-]"),
        )
    )
    if classes < 3:
        return value
    counts = Counter(value)
    entropy = -sum(
        (count / len(value)) * math.log2(count / len(value))
        for count in counts.values()
    )
    return replacement if entropy >= 4.0 else value


def _redaction_replacement(known_secrets: Sequence[str]) -> str:
    for candidate in (REDACTED, "[MASKED]", ""):
        if not any(
            isinstance(secret, str) and secret and secret in candidate
            for secret in known_secrets
        ):
            return candidate
    return ""


def redact_provider_text(text: object, *, known_secrets: Sequence[str] = ()) -> str:
    value = str(text)
    replacement = _redaction_replacement(known_secrets)
    for secret in known_secrets:
        if isinstance(secret, str) and secret:
            value = value.replace(secret, replacement)
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def redact_provider_display_text(
    text: object,
    *,
    known_secrets: Sequence[str] = (),
) -> str:
    """Redact provider-controlled display text, including opaque token material."""

    value = redact_provider_text(text, known_secrets=known_secrets)
    replacement = _redaction_replacement(known_secrets)
    return _TOKEN_CANDIDATE.sub(
        lambda match: _redact_opaque_candidate(match, replacement=replacement),
        value,
    )


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
