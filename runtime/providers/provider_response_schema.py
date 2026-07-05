from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


PROVIDER_RESPONSE_SCHEMA_VERSION = "1A"

PROVIDER_RESPONSE_SCHEMA_VALID_METADATA_ONLY = "PROVIDER_RESPONSE_SCHEMA_VALID_METADATA_ONLY"
PROVIDER_RESPONSE_SCHEMA_INVALID_NON_OBJECT = "PROVIDER_RESPONSE_SCHEMA_INVALID_NON_OBJECT"
PROVIDER_RESPONSE_SCHEMA_MISSING_REQUIRED_FIELD = "PROVIDER_RESPONSE_SCHEMA_MISSING_REQUIRED_FIELD"
PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_SCHEMA_VERSION = "PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_SCHEMA_VERSION"
PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD = "PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD"
PROVIDER_RESPONSE_SCHEMA_PROVIDER_ID_MISMATCH = "PROVIDER_RESPONSE_SCHEMA_PROVIDER_ID_MISMATCH"
PROVIDER_RESPONSE_SCHEMA_HASH_MISMATCH = "PROVIDER_RESPONSE_SCHEMA_HASH_MISMATCH"
PROVIDER_RESPONSE_SCHEMA_FORBIDDEN_AUTHORITY_CLAIM = "PROVIDER_RESPONSE_SCHEMA_FORBIDDEN_AUTHORITY_CLAIM"
PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_TOOLING = "PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_TOOLING"
PROVIDER_RESPONSE_SCHEMA_UNKNOWN_FIELD = "PROVIDER_RESPONSE_SCHEMA_UNKNOWN_FIELD"

_REQUIRED_FIELDS = frozenset(
    {"schema_version", "provider_id", "response_id", "response_hash", "content", "metadata"}
)
_OPTIONAL_HASH_FIELDS = ("request_hash", "prompt_hash", "context_hash")
_ALLOWED_FIELDS = _REQUIRED_FIELDS | frozenset(_OPTIONAL_HASH_FIELDS)
_HEX = frozenset("0123456789abcdef")
_FORBIDDEN_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "human_approved",
        "authority_granted",
        "can_approve",
        "can_execute",
        "can_write",
        "can_push",
        "can_call_provider",
        "can_change_gate",
        "can_satisfy_gate",
        "execution_allowed",
        "write_allowed",
        "artifact_write_allowed",
        "gate_satisfied",
        "gate_eligible",
        "write_eligible",
    }
)
_UNSUPPORTED_TOOLING_FIELD_NAMES = frozenset(
    {
        "tool_call",
        "tool_calls",
        "tools",
        "function_call",
        "function_calls",
        "browser",
        "browser_action",
        "package_install",
        "package_manager",
        "git_operation",
        "network_request",
        "command",
        "commands",
    }
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"authorization\s+granted|safe\s+to\s+(?:execute|write|push|call)|"
    r"gate\s+satisfied)\b"
)
_TOOLING_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:tool[_ -]?call|function[_ -]?call|open\s+(?:the\s+)?browser|"
    r"browser\s+action|pip\s+install|npm\s+install|package\s+install|"
    r"git\s+(?:push|commit|checkout|reset)|curl\s+https?://|wget\s+https?://|"
    r"network\s+request|run\s+(?:this\s+)?command|execute\s+this|"
    r"write\s+(?:this\s+)?file)\b"
)


@dataclass(frozen=True)
class ProviderResponseSchemaValidationResult:
    schema_version: str
    ok: bool
    provider_id: str | None
    response_id: str | None
    response_hash: str | None
    reason_codes: tuple[str, ...]
    normalized_content: str | None
    validation_hash: str
    human_review_required: bool = True
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", PROVIDER_RESPONSE_SCHEMA_VERSION)
        if not isinstance(self.ok, bool):
            raise ValueError("ok must be boolean")
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "can_approve", False)
        object.__setattr__(self, "can_execute", False)
        object.__setattr__(self, "can_write", False)
        object.__setattr__(self, "can_push", False)
        object.__setattr__(self, "can_call_provider", False)
        object.__setattr__(self, "can_change_gate", False)
        object.__setattr__(self, "gate_satisfied", False)
        if not _sha256_like(self.validation_hash):
            raise ValueError("validation_hash must be a sha256 hex digest")
        if self.response_hash is not None and not _sha256_like(self.response_hash):
            raise ValueError("response_hash must be a sha256 hex digest or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROVIDER_RESPONSE_SCHEMA_VERSION,
            "ok": self.ok,
            "provider_id": self.provider_id,
            "response_id": self.response_id,
            "response_hash": self.response_hash,
            "reason_codes": self.reason_codes,
            "normalized_content": self.normalized_content,
            "validation_hash": self.validation_hash,
            "human_review_required": True,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
        }


def validate_provider_response_schema(
    response: object,
    *,
    expected_provider_id: str | None = None,
    expected_request_hash: str | None = None,
    expected_prompt_hash: str | None = None,
    expected_context_hash: str | None = None,
) -> ProviderResponseSchemaValidationResult:
    reason_codes: list[str] = []
    provider_id: str | None = None
    response_id: str | None = None
    response_hash: str | None = None
    normalized_content: str | None = None
    normalized_metadata: dict[str, Any] | None = None
    optional_hashes: dict[str, str | None] = {name: None for name in _OPTIONAL_HASH_FIELDS}
    input_fingerprint = _fingerprint(response)

    expected_hashes = {
        "request_hash": expected_request_hash,
        "prompt_hash": expected_prompt_hash,
        "context_hash": expected_context_hash,
    }
    expected_provider = _optional_text(expected_provider_id)

    if not isinstance(response, Mapping):
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_INVALID_NON_OBJECT)
        return _result(
            ok=False,
            provider_id=None,
            response_id=None,
            response_hash=None,
            reason_codes=tuple(reason_codes),
            normalized_content=None,
            input_fingerprint=input_fingerprint,
            expected_provider_id=expected_provider,
            expected_hashes=expected_hashes,
        )

    data = dict(response)
    missing = sorted(field for field in _REQUIRED_FIELDS if field not in data)
    if missing:
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MISSING_REQUIRED_FIELD)

    unknown = sorted(str(field) for field in data if field not in _ALLOWED_FIELDS)
    if unknown:
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_UNKNOWN_FIELD)

    if _has_forbidden_authority_field(data):
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_FORBIDDEN_AUTHORITY_CLAIM)
    if _has_unsupported_tooling_field(data):
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_TOOLING)

    if "schema_version" in data:
        schema_version = data["schema_version"]
        if not isinstance(schema_version, str) or not schema_version.strip():
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)
        elif schema_version.strip() != PROVIDER_RESPONSE_SCHEMA_VERSION:
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_SCHEMA_VERSION)

    if "provider_id" in data:
        try:
            provider_id = _required_text("provider_id", data["provider_id"])
        except (TypeError, ValueError):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)
    if provider_id is not None and expected_provider is not None and provider_id != expected_provider:
        reason_codes.append(PROVIDER_RESPONSE_SCHEMA_PROVIDER_ID_MISMATCH)

    if "response_id" in data:
        try:
            response_id = _required_text("response_id", data["response_id"])
        except (TypeError, ValueError):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)

    if "content" in data:
        try:
            normalized_content = _normalize_content(data["content"])
        except (TypeError, ValueError):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)

    if "metadata" in data:
        try:
            normalized_metadata = _normalize_metadata(data["metadata"])
        except (TypeError, ValueError):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)

    for field_name in _OPTIONAL_HASH_FIELDS:
        if field_name in data:
            if _sha256_like(data[field_name]):
                optional_hashes[field_name] = str(data[field_name]).lower()
            else:
                reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)
        expected_hash = expected_hashes[field_name]
        if expected_hash is not None:
            if not _sha256_like(expected_hash):
                reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)
            elif optional_hashes[field_name] != expected_hash.lower():
                reason_codes.append(PROVIDER_RESPONSE_SCHEMA_HASH_MISMATCH)

    if "response_hash" in data:
        if _sha256_like(data["response_hash"]):
            response_hash = str(data["response_hash"]).lower()
        else:
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_MALFORMED_FIELD)

    if normalized_content is not None:
        text_values = (normalized_content, *_metadata_text_values(normalized_metadata or {}))
        if any(_AUTHORITY_TEXT_PATTERN.search(value) for value in text_values):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_FORBIDDEN_AUTHORITY_CLAIM)
        if any(_TOOLING_TEXT_PATTERN.search(value) for value in text_values):
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_UNSUPPORTED_TOOLING)

    if (
        provider_id is not None
        and response_id is not None
        and response_hash is not None
        and normalized_content is not None
        and normalized_metadata is not None
    ):
        computed_response_hash = compute_provider_response_hash(
            provider_id=provider_id,
            response_id=response_id,
            content=normalized_content,
            metadata=normalized_metadata,
            request_hash=optional_hashes["request_hash"],
            prompt_hash=optional_hashes["prompt_hash"],
            context_hash=optional_hashes["context_hash"],
        )
        if response_hash != computed_response_hash:
            reason_codes.append(PROVIDER_RESPONSE_SCHEMA_HASH_MISMATCH)

    deduped = tuple(sorted(set(reason_codes)))
    ok = not deduped
    if ok:
        deduped = (PROVIDER_RESPONSE_SCHEMA_VALID_METADATA_ONLY,)

    return _result(
        ok=ok,
        provider_id=provider_id,
        response_id=response_id,
        response_hash=response_hash,
        reason_codes=deduped,
        normalized_content=normalized_content,
        input_fingerprint=input_fingerprint,
        expected_provider_id=expected_provider,
        expected_hashes=expected_hashes,
    )


def compute_provider_response_hash(
    *,
    provider_id: str,
    response_id: str,
    content: str,
    metadata: Mapping[str, Any],
    request_hash: str | None = None,
    prompt_hash: str | None = None,
    context_hash: str | None = None,
) -> str:
    material = {
        "schema_version": PROVIDER_RESPONSE_SCHEMA_VERSION,
        "provider_id": _required_text("provider_id", provider_id),
        "response_id": _required_text("response_id", response_id),
        "content": _normalize_content(content),
        "metadata": _normalize_metadata(metadata),
        "request_hash": _optional_hash("request_hash", request_hash),
        "prompt_hash": _optional_hash("prompt_hash", prompt_hash),
        "context_hash": _optional_hash("context_hash", context_hash),
    }
    return _stable_hash(material)


def _result(
    *,
    ok: bool,
    provider_id: str | None,
    response_id: str | None,
    response_hash: str | None,
    reason_codes: tuple[str, ...],
    normalized_content: str | None,
    input_fingerprint: Any,
    expected_provider_id: str | None,
    expected_hashes: Mapping[str, str | None],
) -> ProviderResponseSchemaValidationResult:
    canonical_reason_codes = tuple(sorted(set(reason_codes)))
    material = {
        "schema_version": PROVIDER_RESPONSE_SCHEMA_VERSION,
        "ok": ok,
        "provider_id": provider_id,
        "response_id": response_id,
        "response_hash": response_hash,
        "reason_codes": canonical_reason_codes,
        "normalized_content": normalized_content,
        "input_fingerprint": input_fingerprint,
        "expected_provider_id": expected_provider_id,
        "expected_hashes": _fingerprint(expected_hashes),
        "human_review_required": True,
        "can_approve": False,
        "can_execute": False,
        "can_write": False,
        "can_push": False,
        "can_call_provider": False,
        "can_change_gate": False,
        "gate_satisfied": False,
    }
    return ProviderResponseSchemaValidationResult(
        schema_version=PROVIDER_RESPONSE_SCHEMA_VERSION,
        ok=ok,
        provider_id=provider_id,
        response_id=response_id,
        response_hash=response_hash,
        reason_codes=canonical_reason_codes,
        normalized_content=normalized_content,
        validation_hash=_stable_hash(material),
    )


def _normalize_content(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("content must be non-empty text")
    return value


def _normalize_metadata(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    normalized: dict[str, Any] = {}
    for key in sorted(value):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("metadata keys must be non-empty text")
        normalized[key.strip()] = _normalize_metadata_value(value[key])
    return normalized


def _normalize_metadata_value(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _normalize_metadata(value)
    if isinstance(value, (tuple, list)):
        return tuple(_normalize_metadata_value(item) for item in value)
    raise TypeError("metadata contains unsupported value")


def _metadata_text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_metadata_text_values(item))
        return tuple(values)
    if isinstance(value, (tuple, list)):
        values = []
        for item in value:
            values.extend(_metadata_text_values(item))
        return tuple(values)
    return ()


def _has_forbidden_authority_field(value: object) -> bool:
    return _has_forbidden_key(value, _FORBIDDEN_AUTHORITY_FIELD_NAMES)


def _has_unsupported_tooling_field(value: object) -> bool:
    return _has_forbidden_key(value, _UNSUPPORTED_TOOLING_FIELD_NAMES)


def _has_forbidden_key(value: object, forbidden: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in forbidden:
                return True
            if _has_forbidden_key(item, forbidden):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_has_forbidden_key(item, forbidden) for item in value)
    return False


def _fingerprint(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _fingerprint(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return tuple(_fingerprint(item) for item in value)
    return {"unsupported_type": type(value).__name__}


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text("expected_provider_id", value)


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    if not _sha256_like(value):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return str(value).lower()


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: Mapping[str, Any]) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
