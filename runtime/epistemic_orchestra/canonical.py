"""Strict canonical serialization for inert epistemic-orchestra contracts.

Hashes bind reviewed metadata.  They never grant authority or permission.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Mapping


SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class EpistemicContractError(ValueError):
    """Fail-closed validation error for an inert orchestra contract."""


def _canonical_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("canonical object keys must be strings")
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("set-like values must be normalized before serialization")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_value(value: Any) -> Any:
    """Return a JSON-compatible value without implicit string conversion."""

    return _canonical_value(value)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a supported value as deterministic compact UTF-8 JSON."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 over the canonical JSON representation."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def exact_text_sha256(value: str) -> str:
    """Return SHA-256 over exact UTF-8 text bytes."""

    if not isinstance(value, str):
        raise TypeError("value must be str")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise EpistemicContractError(f"{name} must be a lowercase SHA-256")
    return value


def require_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    label: str,
) -> None:
    if not isinstance(value, Mapping):
        raise EpistemicContractError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise EpistemicContractError(
            f"{label} fields differ; "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _reject_json_constant(value: str) -> None:
    raise EpistemicContractError(f"non-finite JSON number is forbidden: {value}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EpistemicContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_strict_json_object(value: str | bytes) -> dict[str, Any]:
    """Parse exactly one JSON object, rejecting duplicates and non-finite values."""

    if isinstance(value, bytes):
        try:
            text = value.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise EpistemicContractError("payload must be valid UTF-8") from exc
    elif isinstance(value, str):
        text = value
    else:
        raise EpistemicContractError("payload must be str or bytes")
    if not text.strip():
        raise EpistemicContractError("payload must not be empty")
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
        )
    except EpistemicContractError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise EpistemicContractError("payload must be one strict JSON object") from exc
    if not isinstance(decoded, dict):
        raise EpistemicContractError("payload must be one strict JSON object")
    return decoded
