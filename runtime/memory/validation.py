from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import fields, is_dataclass
from types import MappingProxyType
from typing import Any, Mapping


KNOWLEDGE_CARD_SCHEMA_VERSION = "AOIA_KNOWLEDGE_CARD_1A"
KNOWLEDGE_CLAIM_SCHEMA_VERSION = "AOIA_KNOWLEDGE_CLAIM_1A"
KNOWLEDGE_SOURCE_SCHEMA_VERSION = "AOIA_KNOWLEDGE_SOURCE_1A"
KNOWLEDGE_EVIDENCE_LINK_SCHEMA_VERSION = "AOIA_KNOWLEDGE_EVIDENCE_LINK_1A"
KNOWLEDGE_PROVENANCE_SCHEMA_VERSION = "AOIA_KNOWLEDGE_PROVENANCE_1A"

KNOWLEDGE_REVIEW_ONLY = "review_only"
KNOWLEDGE_NEEDS_REVIEW = "needs_review"
KNOWLEDGE_HUMAN_REVIEWED_NON_AUTHORITY = "human_reviewed_non_authority"
KNOWLEDGE_SOURCE_CANDIDATE = "source_candidate"
KNOWLEDGE_DISCOVERY_ONLY = "discovery_only"
SUPPORTED_REVIEW_STATUSES = frozenset(
    {
        KNOWLEDGE_REVIEW_ONLY,
        KNOWLEDGE_NEEDS_REVIEW,
        KNOWLEDGE_HUMAN_REVIEWED_NON_AUTHORITY,
    }
)

NON_EVIDENCE_SOURCE_TYPES = frozenset(
    {
        "action_proposal",
        "critic_report",
        "hat_metadata",
        "model_output",
        "pheromone_metadata",
        "preview",
        "provider_output",
    }
)
SUPPORTED_SOURCE_TYPES = frozenset(
    {
        "document",
        "human_review",
        "standard",
        "web",
        *NON_EVIDENCE_SOURCE_TYPES,
    }
)
SUPPORTED_AUTHOR_TYPES = frozenset({"human", "source", "model"})

AUTHORITY_FLAG_FIELDS = ("can_execute", "can_write", "gate_satisfied", "can_dispatch", "can_approve")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

PERMISSION_METADATA_KEYS = frozenset(
    {
        "approved",
        "approval",
        "approval_status",
        "authorized",
        "browser_allowed",
        "execute",
        "execute_allowed",
        "execution_allowed",
        "authority",
        "human_approved",
        "trusted",
        "truth",
        "is_truth",
        "permission",
        "can_execute",
        "can_write",
        "can_dispatch",
        "can_approve",
        "gate_satisfied",
        "provider_allowed",
        "provider_call_allowed",
        "retrieval_permission",
        "score_permission",
        "write_allowed",
    }
)


class KnowledgeValidationError(ValueError):
    """Raised when inert knowledge-card data fails closed."""


def canonical_knowledge_json(value: Any) -> str:
    return json.dumps(
        _json_fingerprint(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def hash_knowledge_value(value: Any) -> str:
    return hashlib.sha256(canonical_knowledge_json(value).encode("utf-8")).hexdigest()


def require_identifier(name: str, value: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise KnowledgeValidationError(f"{name} must be a stable local identifier")
    return value


def require_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeValidationError(f"{name} must be non-empty text")
    return value


def require_hash(name: str, value: str) -> str:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise KnowledgeValidationError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def optional_hash(name: str, value: str) -> str:
    if value == "":
        return value
    return require_hash(name, value)


def require_hash_tuple(name: str, value: tuple[str, ...], *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise KnowledgeValidationError(f"{name} must be a tuple")
    if not allow_empty and not value:
        raise KnowledgeValidationError(f"{name} must not be empty")
    for item in value:
        require_hash(name, item)
    return value


def require_metadata(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(metadata, Mapping):
        raise KnowledgeValidationError("metadata must be a mapping")
    try:
        normalized = _freeze_json_value(metadata)
        canonical_knowledge_json(normalized)
    except (TypeError, ValueError) as exc:
        raise KnowledgeValidationError("metadata must be deterministic JSON data") from exc
    _reject_authority_smuggling(normalized)
    return normalized


def metadata_to_dict(metadata: Mapping[str, Any]) -> dict[str, Any]:
    value = _json_fingerprint(metadata)
    if not isinstance(value, dict):
        raise KnowledgeValidationError("metadata must serialize as an object")
    return value


def require_review_status(value: str) -> str:
    if value not in SUPPORTED_REVIEW_STATUSES:
        raise KnowledgeValidationError("review_status must remain review-only and non-authoritative")
    return value


def require_source_type(value: str) -> str:
    if value not in SUPPORTED_SOURCE_TYPES:
        raise KnowledgeValidationError("unsupported source_type")
    return value


def normalize_unique_records(
    name: str,
    value: tuple[Any, ...],
    *,
    record_type: type[Any],
    identifier_field: str,
) -> tuple[Any, ...]:
    if not isinstance(value, tuple):
        raise KnowledgeValidationError(f"{name} must be an immutable tuple")
    if not value:
        raise KnowledgeValidationError(f"{name} must not be empty")
    seen: set[str] = set()
    normalized: list[Any] = []
    for item in value:
        if not isinstance(item, record_type):
            raise KnowledgeValidationError(f"{name} must contain only {record_type.__name__} records")
        identifier = require_identifier(identifier_field, getattr(item, identifier_field, None))
        if identifier in seen:
            raise KnowledgeValidationError(f"duplicate {identifier_field}: {identifier}")
        seen.add(identifier)
        normalized.append(item)
    return tuple(sorted(normalized, key=lambda item: getattr(item, identifier_field)))


def normalize_hash_tuple(name: str, value: tuple[str, ...]) -> tuple[str, ...]:
    require_hash_tuple(name, value)
    if len(set(value)) != len(value):
        raise KnowledgeValidationError(f"{name} must not contain duplicate hashes")
    return tuple(sorted(value))


def require_author_type(value: str) -> str:
    if value not in SUPPORTED_AUTHOR_TYPES:
        raise KnowledgeValidationError("unsupported author_type")
    return value


def assert_inert_authority_flags(payload: Mapping[str, Any]) -> None:
    for flag in AUTHORITY_FLAG_FIELDS:
        if payload.get(flag, False) is not False:
            raise KnowledgeValidationError(f"{flag} must be forced false")


def authority_flags() -> dict[str, bool]:
    return {flag: False for flag in AUTHORITY_FLAG_FIELDS}


def validate_claim_safety(*, statement: str, author_type: str, review_status: str, metadata: Mapping[str, Any]) -> None:
    require_text("statement", statement)
    require_author_type(author_type)
    require_review_status(review_status)
    require_metadata(metadata)
    if _statement_claims_authority(statement):
        raise KnowledgeValidationError("claim text must not pretend to grant authority")
    if author_type == "model" and _metadata_marks_truth_or_permission(metadata):
        raise KnowledgeValidationError("model output cannot be marked as truth or authority")


def validate_source_safety(*, source_type: str, authority_label: str, metadata: Mapping[str, Any]) -> None:
    require_source_type(source_type)
    require_metadata(metadata)
    if authority_label != "evidence_only":
        raise KnowledgeValidationError("source authority_label must remain evidence_only")
    if source_type in NON_EVIDENCE_SOURCE_TYPES and _metadata_marks_truth_or_permission(metadata):
        raise KnowledgeValidationError("generated or advisory sources cannot be marked as truth or authority")


def source_evidence_status(source_type: str) -> str:
    require_source_type(source_type)
    if source_type in NON_EVIDENCE_SOURCE_TYPES:
        return KNOWLEDGE_DISCOVERY_ONLY
    return KNOWLEDGE_SOURCE_CANDIDATE


def verify_recorded_hash(name: str, recorded_hash: str, material: Mapping[str, Any]) -> str:
    if recorded_hash == "":
        return hash_knowledge_value(material)
    require_hash(name, recorded_hash)
    computed = hash_knowledge_value(material)
    if recorded_hash != computed:
        raise KnowledgeValidationError(f"{name} mismatch")
    return recorded_hash


def _metadata_marks_truth_or_permission(metadata: Mapping[str, Any]) -> bool:
    for key, value in metadata.items():
        lowered_key = str(key).lower()
        if lowered_key in PERMISSION_METADATA_KEYS and value not in (False, None, "", 0):
            return True
        if lowered_key in {"retrieval_score", "score", "rank"} and isinstance(value, (int, float)) and value > 0:
            permission_value = metadata.get("permission") or metadata.get("gate_satisfied") or metadata.get("approved")
            if permission_value:
                return True
    return False


def _statement_claims_authority(statement: str) -> bool:
    lowered = statement.lower()
    forbidden_phrases = (
        "is approved",
        "was approved",
        "is authorized",
        "was authorized",
        "grants permission",
        "grant permission",
        "satisfies the gate",
        "gate_satisfied",
        "can execute",
        "can dispatch",
        "can write",
        "can approve",
        "metadata is approval",
        "score is permission",
        "model output is truth",
        "debate winner is truth",
    )
    return any(phrase in lowered for phrase in forbidden_phrases)


def _reject_authority_smuggling(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if _looks_like_authority_key(lowered_key) and item not in (False, None, "", 0):
                raise KnowledgeValidationError("metadata cannot become approval or permission")
            _reject_authority_smuggling(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _reject_authority_smuggling(item)


def _looks_like_authority_key(value: str) -> bool:
    if value in PERMISSION_METADATA_KEYS or value.startswith("can_"):
        return True
    return any(
        token in value
        for token in (
            "approval",
            "approve",
            "authoriz",
            "can_approve",
            "can_dispatch",
            "can_execute",
            "can_write",
            "gate_satisfied",
            "grant_permission",
            "permission_granted",
        )
    )


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("canonical knowledge JSON requires string keys")
            frozen[key] = _freeze_json_value(value[key])
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_json_value(item) for item in value)
    if isinstance(value, bool) or value is None or isinstance(value, str) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("canonical knowledge JSON rejects non-finite floats")
        return value
    raise TypeError(f"canonical knowledge JSON rejects {type(value).__name__}")


def _json_fingerprint(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: _json_fingerprint(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        converted: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical knowledge JSON requires string keys")
            converted[key] = _json_fingerprint(item)
        return converted
    if isinstance(value, tuple):
        return [_json_fingerprint(item) for item in value]
    if isinstance(value, list):
        return [_json_fingerprint(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("canonical knowledge JSON rejects non-finite floats")
        return value
    raise TypeError(f"canonical knowledge JSON rejects {type(value).__name__}")
