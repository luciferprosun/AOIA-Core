"""Strict, inert canonical JSON primitives for authority contracts.

This module deliberately contains no clocks, environment access, filesystem I/O,
external calls, or runtime dispatch.  It accepts only an explicitly bounded JSON
value model and fails closed for every other Python object.
"""

from __future__ import annotations

if __name__ != "runtime.execution.canonical_serialization":
    raise ImportError(
        "canonical serialization must be imported as "
        "runtime.execution.canonical_serialization"
    )

import hashlib
import hmac
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Final


_DOMAIN_PATTERN: Final = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
_MAX_DEPTH: Final = 64
_MAX_CONTAINER_ITEMS: Final = 10_000
_MAX_STRING_BYTES: Final = 1_048_576


class CanonicalSerializationError(ValueError):
    """Raised when a value cannot enter the canonical JSON value model."""


@dataclass(frozen=True, slots=True, init=False)
class FrozenDict(Mapping[str, Any]):
    """Small immutable mapping used for deeply frozen contract values."""

    _items: tuple[tuple[str, Any], ...]

    def __init__(self, items: tuple[tuple[str, Any], ...]) -> None:
        if type(items) is not tuple:
            raise CanonicalSerializationError("FrozenDict items must be an immutable tuple")
        if len(items) > _MAX_CONTAINER_ITEMS:
            raise CanonicalSerializationError("canonical JSON object is too large")
        checked: list[tuple[str, Any]] = []
        for pair in items:
            if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str:
                raise CanonicalSerializationError("FrozenDict entries must be string-key pairs")
            key = _freeze_json(pair[0], active_ids=set(), depth=1)
            checked.append(
                (
                    key,
                    _freeze_json(pair[1], active_ids=set(), depth=1),
                )
            )
        keys = tuple(key for key, _value in checked)
        if keys != tuple(sorted(set(keys))):
            raise CanonicalSerializationError("FrozenDict keys must be sorted and unique")
        object.__setattr__(self, "_items", tuple(checked))

    def __getitem__(self, key: str) -> Any:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._items)


def freeze_json(value: object) -> Any:
    """Return a deeply immutable copy of an exact JSON-compatible value."""

    return _freeze_json(value, active_ids=set(), depth=0)


def thaw_json(value: object) -> Any:
    """Return a fresh mutable JSON graph from a value produced by freeze_json."""

    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is FrozenDict:
        return {key: thaw_json(item) for key, item in value._items}
    if type(value) is tuple:
        return [thaw_json(item) for item in value]
    raise CanonicalSerializationError("value is not frozen canonical JSON")


def canonical_json_bytes(value: object) -> bytes:
    """Serialize an exact JSON value as deterministic, compact UTF-8 JSON."""

    plain = thaw_json(freeze_json(value))
    try:
        rendered = json.dumps(
            plain,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return rendered.encode("utf-8", errors="strict")
    except (UnicodeError, TypeError, ValueError) as exc:
        raise CanonicalSerializationError("value cannot be serialized canonically") from exc


def domain_separated_sha256(domain: str, value: object) -> str:
    """Hash canonical JSON with an explicit ASCII domain and NUL separator."""

    if type(domain) is not str or not _DOMAIN_PATTERN.fullmatch(domain):
        raise CanonicalSerializationError("hash domain must be a stable uppercase ASCII identifier")
    preimage = domain.encode("ascii") + b"\0" + canonical_json_bytes(value)
    return hashlib.sha256(preimage).hexdigest()


def require_sha256(value: object, *, field_name: str) -> str:
    """Require a lowercase hexadecimal SHA-256 digest without normalization."""

    if type(field_name) is not str or not field_name:
        raise CanonicalSerializationError("field_name is required")
    if type(value) is not str or not _SHA256_PATTERN.fullmatch(value):
        raise CanonicalSerializationError(f"{field_name} must be a lowercase SHA-256 digest")
    return value


def hashes_equal(left: object, right: object) -> bool:
    """Compare two already encoded SHA-256 claims in constant time."""

    if type(left) is not str or type(right) is not str:
        return False
    if not _SHA256_PATTERN.fullmatch(left) or not _SHA256_PATTERN.fullmatch(right):
        return False
    return hmac.compare_digest(left, right)


def _freeze_json(value: object, *, active_ids: set[int], depth: int) -> Any:
    if depth > _MAX_DEPTH:
        raise CanonicalSerializationError("canonical JSON nesting is too deep")
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise CanonicalSerializationError("strings must be valid UTF-8") from exc
        if len(encoded) > _MAX_STRING_BYTES:
            raise CanonicalSerializationError("canonical JSON string is too large")
        return value
    if type(value) is float:
        raise CanonicalSerializationError("floating-point values are forbidden")
    if type(value) is FrozenDict:
        keys = tuple(key for key, _item in value._items)
        if any(type(key) is not str for key in keys):
            raise CanonicalSerializationError("canonical JSON object keys must be strings")
        if keys != tuple(sorted(set(keys))):
            raise CanonicalSerializationError("frozen canonical JSON keys must be sorted and unique")
        return FrozenDict(
            tuple(
                (
                    key,
                    _freeze_json(item, active_ids=active_ids, depth=depth + 1),
                )
                for key, item in value._items
            )
        )
    if type(value) is dict:
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise CanonicalSerializationError("canonical JSON object is too large")
        object_id = id(value)
        if object_id in active_ids:
            raise CanonicalSerializationError("cyclic canonical JSON is forbidden")
        active_ids.add(object_id)
        try:
            items: list[tuple[str, Any]] = []
            for key, item in value.items():
                if type(key) is not str:
                    raise CanonicalSerializationError("canonical JSON object keys must be strings")
                _freeze_json(key, active_ids=active_ids, depth=depth + 1)
                items.append(
                    (
                        key,
                        _freeze_json(item, active_ids=active_ids, depth=depth + 1),
                    )
                )
            items.sort(key=lambda pair: pair[0])
            return FrozenDict(tuple(items))
        finally:
            active_ids.remove(object_id)
    if type(value) in (list, tuple):
        if len(value) > _MAX_CONTAINER_ITEMS:
            raise CanonicalSerializationError("canonical JSON array is too large")
        object_id = id(value)
        if object_id in active_ids:
            raise CanonicalSerializationError("cyclic canonical JSON is forbidden")
        active_ids.add(object_id)
        try:
            return tuple(
                _freeze_json(item, active_ids=active_ids, depth=depth + 1)
                for item in value
            )
        finally:
            active_ids.remove(object_id)
    if isinstance(value, Mapping):
        raise CanonicalSerializationError("custom mapping implementations are forbidden")
    raise CanonicalSerializationError(
        f"unsupported canonical JSON type: {type(value).__name__}"
    )


__all__ = (
    "CanonicalSerializationError",
    "FrozenDict",
    "canonical_json_bytes",
    "domain_separated_sha256",
    "freeze_json",
    "hashes_equal",
    "require_sha256",
    "thaw_json",
)
