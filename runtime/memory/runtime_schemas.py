from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


TETRAD_KNOWLEDGE_OBJECT_SCHEMA_VERSION = "AOIA_TETRAD_KNOWLEDGE_OBJECT_1A"
PHEROMONE_MEMORY_TAG_SCHEMA_VERSION = "AOIA_PHEROMONE_MEMORY_TAG_1A"
MEMORY_RUNTIME_VALIDATION_SCHEMA_VERSION = "AOIA_MEMORY_RUNTIME_VALIDATION_1A"

MEMORY_RUNTIME_OK = "MEMORY_RUNTIME_OK"
MEMORY_RUNTIME_TETRAD_METADATA_ONLY = "MEMORY_RUNTIME_TETRAD_METADATA_ONLY"
MEMORY_RUNTIME_PHEROMONE_TAG_METADATA_ONLY = "MEMORY_RUNTIME_PHEROMONE_TAG_METADATA_ONLY"
MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW = "MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW"
MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH = "MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH"
MEMORY_RUNTIME_NON_AUTHORITY = "MEMORY_RUNTIME_NON_AUTHORITY"

MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD = "MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD"
MEMORY_RUNTIME_BLOCKED_INVALID_TAG = "MEMORY_RUNTIME_BLOCKED_INVALID_TAG"
MEMORY_RUNTIME_BLOCKED_INVALID_HASH = "MEMORY_RUNTIME_BLOCKED_INVALID_HASH"
MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH = "MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH"
MEMORY_RUNTIME_BLOCKED_INVALID_TIME = "MEMORY_RUNTIME_BLOCKED_INVALID_TIME"
MEMORY_RUNTIME_BLOCKED_EXPIRED_TETRAD = "MEMORY_RUNTIME_BLOCKED_EXPIRED_TETRAD"
MEMORY_RUNTIME_BLOCKED_EXPIRED_TAG = "MEMORY_RUNTIME_BLOCKED_EXPIRED_TAG"
MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND = "MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND"
MEMORY_RUNTIME_BLOCKED_UNKNOWN_TARGET = "MEMORY_RUNTIME_BLOCKED_UNKNOWN_TARGET"
MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_ID = "MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_ID"
MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_HASH = "MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_HASH"
MEMORY_RUNTIME_BLOCKED_STORAGE_SMUGGLING = "MEMORY_RUNTIME_BLOCKED_STORAGE_SMUGGLING"
MEMORY_RUNTIME_BLOCKED_RETRIEVAL_SMUGGLING = "MEMORY_RUNTIME_BLOCKED_RETRIEVAL_SMUGGLING"
MEMORY_RUNTIME_BLOCKED_EMBEDDING_SMUGGLING = "MEMORY_RUNTIME_BLOCKED_EMBEDDING_SMUGGLING"
MEMORY_RUNTIME_BLOCKED_AUTONOMY_SMUGGLING = "MEMORY_RUNTIME_BLOCKED_AUTONOMY_SMUGGLING"
MEMORY_RUNTIME_BLOCKED_EXECUTION_SMUGGLING = "MEMORY_RUNTIME_BLOCKED_EXECUTION_SMUGGLING"
MEMORY_RUNTIME_BLOCKED_PROVIDER_CALL = "MEMORY_RUNTIME_BLOCKED_PROVIDER_CALL"
MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM = "MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM"
MEMORY_RUNTIME_BLOCKED_NON_JSON_SERIALIZABLE = "MEMORY_RUNTIME_BLOCKED_NON_JSON_SERIALIZABLE"
MEMORY_RUNTIME_BLOCKED_AMBIGUOUS_EVIDENCE = "MEMORY_RUNTIME_BLOCKED_AMBIGUOUS_EVIDENCE"

SUPPORTED_TETRAD_STATUS_LABELS = frozenset(
    {
        "candidate",
        "needs_review",
        "stale",
        "contradiction_seen",
        "invalid",
    }
)
SUPPORTED_PHEROMONE_TAG_KINDS = frozenset(
    {
        "recently_referenced",
        "operator_bookmarked",
        "needs_revalidation",
        "stale_evidence",
        "contradiction_seen",
        "high_review_value",
        "unsafe_for_execution",
    }
)
SUPPORTED_PHEROMONE_SIGNAL_LABELS = frozenset({"low", "medium", "high", "blocked"})

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

_ALLOWED_TETRAD_FIELDS = frozenset(
    {
        "schema_version",
        "object_id",
        "raw_evidence_hash",
        "structured_claims_hash",
        "semantic_view_hash",
        "audit_risk_hash",
        "source_hashes",
        "status_label",
        "summary",
        "created_at",
        "expires_at",
        "object_hash",
    }
)
_ALLOWED_TAG_FIELDS = frozenset(
    {
        "schema_version",
        "tag_id",
        "target_hash",
        "tag_kind",
        "signal_label",
        "reason",
        "created_at",
        "expires_at",
        "tag_hash",
    }
)

_AUTHORITY_TERMS = (
    "approve",
    "approved",
    "authorize",
    "authorized",
    "authority",
    "trusted",
    "truth",
    "canonical",
    "gate_satisfied",
    "human_approved",
    "can_execute",
    "can_dispatch",
    "can_write",
    "can_commit",
    "can_push",
    "grant_permission",
)
_STORAGE_TERMS = (
    "sqlite",
    "database",
    "db_write",
    "storage_write",
    "append_log",
    "jsonl_append",
    "write_memory",
    "persist",
)
_RETRIEVAL_TERMS = (
    "retrieval_ranking",
    "rank_result",
    "search_index",
    "fts",
    "bm25",
    "auto_retrieve",
)
_EMBEDDING_TERMS = ("embedding", "vector", "semantic_index", "ann_index")
_AUTONOMY_TERMS = (
    "agent_memory_autonomy",
    "autonomous",
    "agent_loop",
    "worker",
    "background",
    "scheduler",
    "decay",
    "reinforcement",
    "auto_reinforce",
)
_EXECUTION_TERMS = (
    "execute_now",
    "selected_to_execute",
    "dispatch",
    "tool_call",
    "call_tool",
    "shell",
    "command",
    "sub" + "process",
    "git_push",
    "package_install",
    "browser_automation",
    "mcp_tool",
)
_PROVIDER_TERMS = ("provider_call", "call_provider", "run_provider", "invoke_provider")


@dataclass(frozen=True)
class TetradKnowledgeObject:
    schema_version: str
    object_id: str
    raw_evidence_hash: str
    structured_claims_hash: str
    semantic_view_hash: str
    audit_risk_hash: str
    source_hashes: tuple[str, ...]
    status_label: str
    summary: str
    created_at: int
    expires_at: int
    object_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "object_id": self.object_id,
            "raw_evidence_hash": self.raw_evidence_hash,
            "structured_claims_hash": self.structured_claims_hash,
            "semantic_view_hash": self.semantic_view_hash,
            "audit_risk_hash": self.audit_risk_hash,
            "source_hashes": self.source_hashes,
            "status_label": self.status_label,
            "summary": self.summary,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "object_hash": self.object_hash,
        }


@dataclass(frozen=True)
class PheromoneMemoryTag:
    schema_version: str
    tag_id: str
    target_hash: str
    tag_kind: str
    signal_label: str
    reason: str
    created_at: int
    expires_at: int
    tag_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tag_id": self.tag_id,
            "target_hash": self.target_hash,
            "tag_kind": self.tag_kind,
            "signal_label": self.signal_label,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "tag_hash": self.tag_hash,
        }


@dataclass(frozen=True)
class MemoryRuntimeValidationResult:
    schema_version: str
    ok: bool
    blocked: bool
    authority_allowed: bool
    storage_allowed: bool
    retrieval_allowed: bool
    ranking_allowed: bool
    embedding_allowed: bool
    decay_allowed: bool
    reinforcement_allowed: bool
    provider_call_allowed: bool
    execution_allowed: bool
    dispatch_allowed: bool
    autonomous_memory_allowed: bool
    requires_human_review: bool
    requires_controlled_path: bool
    tetrad_hash: str | None
    tag_hashes: tuple[str, ...]
    memory_codes: tuple[str, ...]
    reason_codes: tuple[str, ...]
    validation_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "blocked": self.blocked,
            "authority_allowed": self.authority_allowed,
            "storage_allowed": self.storage_allowed,
            "retrieval_allowed": self.retrieval_allowed,
            "ranking_allowed": self.ranking_allowed,
            "embedding_allowed": self.embedding_allowed,
            "decay_allowed": self.decay_allowed,
            "reinforcement_allowed": self.reinforcement_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "autonomous_memory_allowed": self.autonomous_memory_allowed,
            "requires_human_review": self.requires_human_review,
            "requires_controlled_path": self.requires_controlled_path,
            "tetrad_hash": self.tetrad_hash,
            "tag_hashes": self.tag_hashes,
            "memory_codes": self.memory_codes,
            "reason_codes": self.reason_codes,
            "validation_hash": self.validation_hash,
        }


def canonical_memory_runtime_json(value: Any) -> str:
    return json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def hash_memory_runtime_value(value: Any) -> str:
    return hashlib.sha256(canonical_memory_runtime_json(value).encode("utf-8")).hexdigest()


def build_tetrad_knowledge_object(
    *,
    object_id: str,
    raw_evidence_hash: str,
    structured_claims_hash: str,
    semantic_view_hash: str,
    audit_risk_hash: str,
    source_hashes: tuple[str, ...],
    status_label: str,
    summary: str,
    created_at: int,
    expires_at: int,
) -> TetradKnowledgeObject:
    material = {
        "schema_version": TETRAD_KNOWLEDGE_OBJECT_SCHEMA_VERSION,
        "object_id": _identifier("object_id", object_id),
        "raw_evidence_hash": _required_hash("raw_evidence_hash", raw_evidence_hash),
        "structured_claims_hash": _required_hash("structured_claims_hash", structured_claims_hash),
        "semantic_view_hash": _required_hash("semantic_view_hash", semantic_view_hash),
        "audit_risk_hash": _required_hash("audit_risk_hash", audit_risk_hash),
        "source_hashes": _hash_tuple("source_hashes", source_hashes, allow_empty=False),
        "status_label": _label("status_label", status_label),
        "summary": _required_text("summary", summary),
        "created_at": _nonnegative_int("created_at", created_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return TetradKnowledgeObject(**material, object_hash=hash_memory_runtime_value(material))


def build_pheromone_memory_tag(
    *,
    tag_id: str,
    target_hash: str,
    tag_kind: str,
    signal_label: str,
    reason: str,
    created_at: int,
    expires_at: int,
) -> PheromoneMemoryTag:
    material = {
        "schema_version": PHEROMONE_MEMORY_TAG_SCHEMA_VERSION,
        "tag_id": _identifier("tag_id", tag_id),
        "target_hash": _required_hash("target_hash", target_hash),
        "tag_kind": _label("tag_kind", tag_kind),
        "signal_label": _label("signal_label", signal_label),
        "reason": _required_text("reason", reason),
        "created_at": _nonnegative_int("created_at", created_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return PheromoneMemoryTag(**material, tag_hash=hash_memory_runtime_value(material))


def validate_memory_runtime_metadata(
    *,
    tetrad: TetradKnowledgeObject | Mapping[str, Any],
    tags: tuple[PheromoneMemoryTag | Mapping[str, Any], ...] = (),
    now: int,
) -> MemoryRuntimeValidationResult:
    reason_codes: list[str] = []
    tetrad_mapping: Mapping[str, Any] | None = None
    tag_mappings: tuple[Mapping[str, Any], ...] = ()

    try:
        canonical_memory_runtime_json({"tetrad": tetrad, "tags": tags, "now": now})
        tetrad_mapping = _as_mapping(tetrad)
        tag_mappings = tuple(_as_mapping(tag) for tag in tags)
    except TypeError:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_NON_JSON_SERIALIZABLE)

    if isinstance(now, bool) or not isinstance(now, int) or now < 0:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TIME)

    tetrad_hash: str | None = None
    tag_hashes: tuple[str, ...] = ()
    if tetrad_mapping is not None:
        tetrad_hash = _optional_hash("object_hash", tetrad_mapping.get("object_hash"))
        if tetrad_hash is None:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_HASH)
        reason_codes.extend(_validate_tetrad(tetrad_mapping, now=now if isinstance(now, int) else -1))
        tag_reason_codes, tag_hashes = _validate_tags(
            tag_mappings,
            target_hash=tetrad_hash,
            now=now if isinstance(now, int) else -1,
        )
        reason_codes.extend(tag_reason_codes)

    if tetrad_mapping is not None and _contains_dangerous_metadata(tetrad_mapping):
        reason_codes.extend(_classify_dangerous_metadata(tetrad_mapping))
    for tag_mapping in tag_mappings:
        if _contains_dangerous_metadata(tag_mapping):
            reason_codes.extend(_classify_dangerous_metadata(tag_mapping))

    reason_codes = _unique(reason_codes)
    ok = not reason_codes
    if ok:
        reason_codes = [
            MEMORY_RUNTIME_OK,
            MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW,
            MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH,
        ]
    material = {
        "schema_version": MEMORY_RUNTIME_VALIDATION_SCHEMA_VERSION,
        "ok": ok,
        "blocked": not ok,
        "authority_allowed": False,
        "storage_allowed": False,
        "retrieval_allowed": False,
        "ranking_allowed": False,
        "embedding_allowed": False,
        "decay_allowed": False,
        "reinforcement_allowed": False,
        "provider_call_allowed": False,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "autonomous_memory_allowed": False,
        "requires_human_review": True,
        "requires_controlled_path": True,
        "tetrad_hash": tetrad_hash if ok else tetrad_hash,
        "tag_hashes": tag_hashes,
        "memory_codes": (
            MEMORY_RUNTIME_TETRAD_METADATA_ONLY,
            MEMORY_RUNTIME_PHEROMONE_TAG_METADATA_ONLY,
            MEMORY_RUNTIME_REQUIRES_HUMAN_REVIEW,
            MEMORY_RUNTIME_REQUIRES_CONTROLLED_PATH,
            MEMORY_RUNTIME_NON_AUTHORITY,
        ),
        "reason_codes": tuple(reason_codes),
    }
    return MemoryRuntimeValidationResult(**material, validation_hash=hash_memory_runtime_value(material))


def _validate_tetrad(value: Mapping[str, Any], *, now: int) -> list[str]:
    reason_codes: list[str] = []
    if set(value.keys()) != _ALLOWED_TETRAD_FIELDS:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD)
    if value.get("schema_version") != TETRAD_KNOWLEDGE_OBJECT_SCHEMA_VERSION:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD)
    if not _valid_identifier(value.get("object_id")) or not _valid_required_text(value.get("summary")):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD)
    if value.get("status_label") not in SUPPORTED_TETRAD_STATUS_LABELS:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD)
    for field_name in ("raw_evidence_hash", "structured_claims_hash", "semantic_view_hash", "audit_risk_hash"):
        if _optional_hash(field_name, value.get(field_name)) is None:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_HASH)
    if not _valid_hash_tuple(value.get("source_hashes"), allow_empty=False):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_HASH)
    created_at = value.get("created_at")
    expires_at = value.get("expires_at")
    if not _valid_time_window(created_at, expires_at, now):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TIME)
    elif now >= expires_at:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_EXPIRED_TETRAD)
    material = {key: item for key, item in value.items() if key != "object_hash"}
    if value.get("object_hash") != hash_memory_runtime_value(material):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH)
    return reason_codes


def _validate_tags(
    values: tuple[Mapping[str, Any], ...],
    *,
    target_hash: str | None,
    now: int,
) -> tuple[list[str], tuple[str, ...]]:
    reason_codes: list[str] = []
    tag_ids: set[str] = set()
    tag_hashes: list[str] = []
    for value in values:
        if set(value.keys()) != _ALLOWED_TAG_FIELDS:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TAG)
        tag_id = value.get("tag_id")
        tag_hash = _optional_hash("tag_hash", value.get("tag_hash"))
        if tag_hash is None:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_HASH)
        if isinstance(tag_id, str) and tag_id in tag_ids:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_ID)
        if tag_hash is not None and tag_hash in tag_hashes:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_DUPLICATE_TAG_HASH)
        if isinstance(tag_id, str):
            tag_ids.add(tag_id)
        if tag_hash is not None:
            tag_hashes.append(tag_hash)
        if value.get("schema_version") != PHEROMONE_MEMORY_TAG_SCHEMA_VERSION:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TAG)
        if not _valid_identifier(value.get("tag_id")) or not _valid_required_text(value.get("reason")):
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TAG)
        if value.get("tag_kind") not in SUPPORTED_PHEROMONE_TAG_KINDS:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND)
        if value.get("signal_label") not in SUPPORTED_PHEROMONE_SIGNAL_LABELS:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TAG)
        if _optional_hash("target_hash", value.get("target_hash")) is None:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_HASH)
        elif target_hash is not None and value.get("target_hash") != target_hash:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_UNKNOWN_TARGET)
        created_at = value.get("created_at")
        expires_at = value.get("expires_at")
        if not _valid_time_window(created_at, expires_at, now):
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_INVALID_TIME)
        elif now >= expires_at:
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_EXPIRED_TAG)
        material = {key: item for key, item in value.items() if key != "tag_hash"}
        if tag_hash is None or tag_hash != hash_memory_runtime_value(material):
            reason_codes.append(MEMORY_RUNTIME_BLOCKED_HASH_MISMATCH)
    return reason_codes, tuple(sorted(tag_hashes))


def _valid_time_window(created_at: object, expires_at: object, now: int) -> bool:
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in (created_at, expires_at, now)):
        return False
    return created_at < expires_at and created_at <= now


def _classify_dangerous_metadata(value: Mapping[str, Any]) -> list[str]:
    text = canonical_memory_runtime_json(value).casefold()
    reason_codes: list[str] = []
    if _contains_any(text, _AUTHORITY_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_AUTHORITY_CLAIM)
    if _contains_any(text, _STORAGE_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_STORAGE_SMUGGLING)
    if _contains_any(text, _RETRIEVAL_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_RETRIEVAL_SMUGGLING)
    if _contains_any(text, _EMBEDDING_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_EMBEDDING_SMUGGLING)
    if _contains_any(text, _AUTONOMY_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_AUTONOMY_SMUGGLING)
    if _contains_any(text, _EXECUTION_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_EXECUTION_SMUGGLING)
    if _contains_any(text, _PROVIDER_TERMS):
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_PROVIDER_CALL)
    if "ambiguous" in text:
        reason_codes.append(MEMORY_RUNTIME_BLOCKED_AMBIGUOUS_EVIDENCE)
    return reason_codes


def _contains_dangerous_metadata(value: Mapping[str, Any]) -> bool:
    return bool(_classify_dangerous_metadata(value))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.casefold() in text for term in terms)


def _json_fingerprint(value: Any) -> Any:
    if isinstance(value, (TetradKnowledgeObject, PheromoneMemoryTag, MemoryRuntimeValidationResult)):
        return _json_fingerprint(value.to_dict())
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical memory JSON requires string mapping keys")
            normalized[key] = _json_fingerprint(item)
        return normalized
    if isinstance(value, tuple):
        return [_json_fingerprint(item) for item in value]
    if isinstance(value, list):
        return [_json_fingerprint(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        raise TypeError("canonical memory JSON rejects floats")
    raise TypeError("canonical memory JSON rejects non-JSON-serializable values")


def _as_mapping(value: TetradKnowledgeObject | PheromoneMemoryTag | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value, (TetradKnowledgeObject, PheromoneMemoryTag)):
        return value.to_dict()
    if isinstance(value, Mapping):
        return value
    raise TypeError("memory runtime value must be a supported mapping or dataclass")


def _identifier(field_name: str, value: object) -> str:
    text = _required_text(field_name, value)
    if not _ID_RE.match(text):
        raise ValueError(f"{field_name} must be a compact identifier")
    return text


def _required_text(field_name: str, value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _label(field_name: str, value: object) -> str:
    return _required_text(field_name, value).casefold()


def _required_hash(field_name: str, value: object) -> str:
    text = _required_text(field_name, value).casefold()
    if not _HASH_RE.match(text):
        raise ValueError(f"{field_name} must be a SHA-256 hex hash")
    return text


def _optional_hash(field_name: str, value: object) -> str | None:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        return None
    return value


def _hash_tuple(field_name: str, values: object, *, allow_empty: bool) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of hashes")
    if not allow_empty and not values:
        raise ValueError(f"{field_name} must not be empty")
    return tuple(_required_hash(field_name, value) for value in values)


def _valid_hash_tuple(values: object, *, allow_empty: bool) -> bool:
    if isinstance(values, (str, bytes)) or not isinstance(values, tuple):
        return False
    if not allow_empty and not values:
        return False
    return all(isinstance(value, str) and _HASH_RE.fullmatch(value) for value in values)


def _valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


def _valid_required_text(value: object) -> bool:
    return isinstance(value, str) and bool(" ".join(value.split()))


def _nonnegative_int(field_name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _unique(values: list[str]) -> list[str]:
    return sorted(set(values))
