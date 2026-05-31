"""Standalone normalization and fingerprint helpers for Memory Hats.

This module performs pure string normalization and deterministic SHA-256
fingerprinting only. It does not parse shell grammar, execute commands, read
files, access storage, or integrate with runtime routing.
"""

from __future__ import annotations

import hashlib
import re

_FIELD_SEPARATOR = "\x1f"
_WHITESPACE_RE = re.compile(r"\s+")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_trigger(value: str) -> str:
    """Normalize a trigger string without interpreting its meaning."""

    if not isinstance(value, str):
        raise TypeError("value must be a str")
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def compute_fingerprint(
    normalized_trigger: str,
    hat_id: str,
    tag_type: str,
) -> str:
    """Compute a deterministic SHA-256 fingerprint for normalized tag input."""

    for name, value in (
        ("normalized_trigger", normalized_trigger),
        ("hat_id", hat_id),
        ("tag_type", tag_type),
    ):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a str")

    payload = _FIELD_SEPARATOR.join((hat_id, tag_type, normalized_trigger))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_for_trigger(
    trigger: str,
    hat_id: str,
    tag_type: str,
) -> str:
    """Normalize a trigger and compute its deterministic fingerprint."""

    normalized_trigger = normalize_trigger(trigger)
    return compute_fingerprint(normalized_trigger, hat_id, tag_type)


def is_sha256_hex(value: str) -> bool:
    """Return True when value is a lowercase SHA-256 hex digest."""

    if not isinstance(value, str):
        return False
    return bool(_SHA256_HEX_RE.fullmatch(value))
