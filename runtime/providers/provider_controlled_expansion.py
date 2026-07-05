from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.providers.provider_payload_governance import (
    PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,
    PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY,
    PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED,
    PAYLOAD_EXPANSION_OK_INERT_METADATA,
    PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW,
    PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
    ProviderPayloadExpansionGovernanceResult,
    compute_provider_payload_expansion_hash,
)


CONTROLLED_PROVIDER_EXPANSION_SCHEMA_VERSION = "1A"
PROVIDER_EXPANSION_HUMAN_BARRIER_SCHEMA_VERSION = "AOIA_PROVIDER_EXPANSION_HUMAN_BARRIER_1A"

PROVIDER_EXPANSION_OPERATION_APPLY_INERT_PAYLOAD = "APPLY_INERT_PROVIDER_PAYLOAD_EXPANSION"

CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT = "CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED"

CONTROLLED_PROVIDER_EXPANSION_REASON_APPLIED_INERT = "CONTROLLED_PROVIDER_EXPANSION_REASON_APPLIED_INERT"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MISSING_HUMAN_BARRIER = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MISSING_HUMAN_BARRIER"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_SCOPE_MISMATCH = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_SCOPE_MISMATCH"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_APPROVED = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_APPROVED"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_GOVERNED = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_GOVERNED"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_PAYLOAD_COLLISION = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_PAYLOAD_COLLISION"
CONTROLLED_PROVIDER_EXPANSION_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_PROVIDER_EXPANSION_BLOCKED_AUTHORITY_CLAIM"

_HEX = frozenset("0123456789abcdef")
_ALLOWED_GOVERNANCE_CATEGORIES = frozenset(
    {
        PAYLOAD_EXPANSION_OK_INERT_METADATA,
        PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW,
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "authority",
        "authority_granted",
        "human_approved",
        "can_approve",
        "can_execute",
        "can_write",
        "can_push",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "provider_call_allowed",
    }
)
_DANGEROUS_FIELD_NAMES = frozenset(
    {
        "tool",
        "tools",
        "tool_call",
        "tool_calls",
        "function_call",
        "functions",
        "stream",
        "streaming",
        "retry",
        "fallback",
        "fallback_provider",
        "url",
        "endpoint",
        "callback_url",
        "browser",
        "package_install",
        "git",
        "git_operation",
        "headers",
        "authorization",
        "secret",
        "token",
        "api" + "_key",
        "env",
        "get" + "env",
        "os." + "environ",
        "full_context",
        "unbounded_context",
        "messages",
        "contents",
    }
)
_AUTHORITY_FLAGS = (
    "can_approve",
    "can_execute",
    "can_write",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "gate_satisfied",
    "provider_call_authorized",
    "execution_authorized",
    "write_authorized",
    "human_barrier_satisfied",
)


@dataclass(frozen=True)
class ProviderExpansionHumanBarrier:
    schema_version: str
    proposal_hash: str
    governance_hash: str
    base_payload_hash: str
    provider_id: str
    operation: str
    approved_fields: tuple[str, ...]
    approved_by: str
    approval_reason: str
    barrier_hash: str
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    provider_call_authorized: bool = False
    execution_authorized: bool = False
    write_authorized: bool = False
    human_barrier_satisfied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "proposal_hash", _required_hash("proposal_hash", self.proposal_hash))
        object.__setattr__(self, "governance_hash", _required_hash("governance_hash", self.governance_hash))
        object.__setattr__(self, "base_payload_hash", _required_hash("base_payload_hash", self.base_payload_hash))
        object.__setattr__(self, "provider_id", _required_text("provider_id", self.provider_id))
        object.__setattr__(self, "operation", _required_text("operation", self.operation))
        object.__setattr__(self, "approved_fields", _text_tuple("approved_fields", self.approved_fields))
        object.__setattr__(self, "approved_by", _required_text("approved_by", self.approved_by))
        object.__setattr__(self, "approval_reason", _required_text("approval_reason", self.approval_reason))
        object.__setattr__(self, "barrier_hash", _required_hash("barrier_hash", self.barrier_hash))
        for field_name in _AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)
        if self.schema_version != PROVIDER_EXPANSION_HUMAN_BARRIER_SCHEMA_VERSION:
            raise ValueError("unsupported provider expansion human barrier schema version")
        if self.operation != PROVIDER_EXPANSION_OPERATION_APPLY_INERT_PAYLOAD:
            raise ValueError("unsupported provider expansion operation")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "proposal_hash": self.proposal_hash,
            "governance_hash": self.governance_hash,
            "base_payload_hash": self.base_payload_hash,
            "provider_id": self.provider_id,
            "operation": self.operation,
            "approved_fields": self.approved_fields,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason,
            "barrier_hash": self.barrier_hash,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "provider_call_authorized": False,
            "execution_authorized": False,
            "write_authorized": False,
            "human_barrier_satisfied": False,
        }


@dataclass(frozen=True)
class ControlledProviderExpansionResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    provider_id: str | None
    base_payload_hash: str | None
    proposal_hash: str | None
    governance_hash: str | None
    barrier_hash: str | None
    expanded_payload_hash: str | None
    expanded_payload: Mapping[str, Any] | None
    applied_fields: tuple[str, ...]
    result_hash: str
    human_review_required: bool = True
    inert_payload_expanded: bool = False
    provider_called: bool = False
    network_called: bool = False
    execution_performed: bool = False
    file_written: bool = False
    browser_opened: bool = False
    package_installed: bool = False
    git_action_performed: bool = False
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", CONTROLLED_PROVIDER_EXPANSION_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "applied_fields", tuple(sorted(set(self.applied_fields))))
        if self.status not in {CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT, CONTROLLED_PROVIDER_EXPANSION_BLOCKED}:
            raise ValueError("unsupported controlled provider expansion status")
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "inert_payload_expanded", self.status == CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT)
        for field_name in (
            "provider_called",
            "network_called",
            "execution_performed",
            "file_written",
            "browser_opened",
            "package_installed",
            "git_action_performed",
            "can_approve",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "gate_satisfied",
            "human_barrier_satisfied",
        ):
            object.__setattr__(self, field_name, False)
        if not _sha256_like(self.result_hash):
            raise ValueError("result_hash must be a sha256 hex digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLED_PROVIDER_EXPANSION_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "provider_id": self.provider_id,
            "base_payload_hash": self.base_payload_hash,
            "proposal_hash": self.proposal_hash,
            "governance_hash": self.governance_hash,
            "barrier_hash": self.barrier_hash,
            "expanded_payload_hash": self.expanded_payload_hash,
            "expanded_payload": _fingerprint(self.expanded_payload),
            "applied_fields": self.applied_fields,
            "result_hash": self.result_hash,
            "human_review_required": True,
            "inert_payload_expanded": self.inert_payload_expanded,
            "provider_called": False,
            "network_called": False,
            "execution_performed": False,
            "file_written": False,
            "browser_opened": False,
            "package_installed": False,
            "git_action_performed": False,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
        }


def create_provider_expansion_human_barrier(
    *,
    proposal_hash: str,
    governance_hash: str,
    base_payload_hash: str,
    provider_id: str,
    approved_fields: tuple[str, ...],
    approved_by: str,
    approval_reason: str,
) -> ProviderExpansionHumanBarrier:
    material = {
        "schema_version": PROVIDER_EXPANSION_HUMAN_BARRIER_SCHEMA_VERSION,
        "proposal_hash": _required_hash("proposal_hash", proposal_hash),
        "governance_hash": _required_hash("governance_hash", governance_hash),
        "base_payload_hash": _required_hash("base_payload_hash", base_payload_hash),
        "provider_id": _required_text("provider_id", provider_id),
        "operation": PROVIDER_EXPANSION_OPERATION_APPLY_INERT_PAYLOAD,
        "approved_fields": _text_tuple("approved_fields", approved_fields),
        "approved_by": _required_text("approved_by", approved_by),
        "approval_reason": _required_text("approval_reason", approval_reason),
    }
    return ProviderExpansionHumanBarrier(
        **material,
        barrier_hash=compute_provider_expansion_barrier_hash(material),
    )


def apply_controlled_provider_expansion(
    *,
    base_payload: object,
    proposal: object,
    governance_result: object,
    human_barrier: object,
) -> ControlledProviderExpansionResult:
    try:
        normalized_base = _normalize_payload_mapping(base_payload)
        proposal_data = _coerce_mapping(proposal)
        governance_data = _coerce_governance(governance_result)
        barrier = _coerce_barrier(human_barrier)
    except (TypeError, ValueError):
        return _blocked((CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE,))

    try:
        provider_id = _required_text("provider_id", proposal_data.get("provider_id"))
        proposed_fields = _normalize_payload_mapping(proposal_data.get("proposed_fields"))
        field_names = tuple(sorted(proposed_fields))
        base_payload_hash = compute_provider_base_payload_hash(normalized_base)
        proposal_hash = _proposal_hash(proposal_data)
        governance_hash = _required_hash("governance_hash", governance_data.get("governance_hash"))
    except (TypeError, ValueError):
        return _blocked((CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE,))

    reason_codes: list[str] = []
    if base_payload_hash != proposal_data.get("base_payload_hash") or base_payload_hash != governance_data.get("base_payload_hash"):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH)
    if proposal_hash != proposal_data.get("proposal_hash") or proposal_hash != governance_data.get("proposal_hash"):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH)
    if governance_data.get("provider_id") != provider_id:
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH)
    if governance_data.get("status") not in (
        PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY,
        PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED,
    ):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED)
    governance_categories = tuple(str(item) for item in governance_data.get("categories", ()))
    if not governance_categories or any(category not in _ALLOWED_GOVERNANCE_CATEGORIES for category in governance_categories):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_GOVERNANCE_NOT_ALLOWED)
    if tuple(sorted(governance_data.get("proposed_field_names", ()))) != field_names:
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_GOVERNED)

    barrier_codes = _barrier_reason_codes(
        barrier=barrier,
        provider_id=provider_id,
        proposal_hash=proposal_hash,
        governance_hash=governance_hash,
        base_payload_hash=base_payload_hash,
        field_names=field_names,
    )
    reason_codes.extend(barrier_codes)
    if governance_hash != barrier.governance_hash:
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_HASH_MISMATCH)

    if _has_forbidden_key(proposal_data) or _has_forbidden_key(proposed_fields):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_DANGEROUS_FIELD)
    if _has_authority_key(proposal_data) or _has_authority_key(proposed_fields) or _has_authority_key(_barrier_hash_material(barrier)):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_AUTHORITY_CLAIM)

    expanded_payload: dict[str, Any] | None = None
    if not reason_codes:
        expanded_payload, collision = _apply_additions(normalized_base, proposed_fields)
        if collision:
            reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_PAYLOAD_COLLISION)

    if reason_codes or expanded_payload is None:
        return _blocked(
            tuple(reason_codes or (CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MALFORMED_EVIDENCE,)),
            provider_id=provider_id,
            base_payload_hash=base_payload_hash,
            proposal_hash=proposal_hash,
            governance_hash=governance_hash,
            barrier_hash=barrier.barrier_hash,
        )

    expanded_hash = compute_provider_base_payload_hash(expanded_payload)
    return _result(
        status=CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT,
        reason_codes=(CONTROLLED_PROVIDER_EXPANSION_REASON_APPLIED_INERT,),
        provider_id=provider_id,
        base_payload_hash=base_payload_hash,
        proposal_hash=proposal_hash,
        governance_hash=governance_hash,
        barrier_hash=barrier.barrier_hash,
        expanded_payload_hash=expanded_hash,
        expanded_payload=expanded_payload,
        applied_fields=field_names,
    )


def compute_provider_base_payload_hash(payload: object) -> str:
    return _stable_hash(_normalize_payload_mapping(payload))


def compute_provider_expansion_barrier_hash(value: Mapping[str, Any]) -> str:
    return _stable_hash(_fingerprint(value))


def _apply_additions(base_payload: Mapping[str, Any], proposed_fields: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
    expanded = dict(base_payload)
    for field_name, field_value in proposed_fields.items():
        if field_name in expanded:
            if (
                field_name == "metadata"
                and isinstance(expanded[field_name], Mapping)
                and isinstance(field_value, Mapping)
            ):
                merged = dict(expanded[field_name])
                if any(key in merged for key in field_value):
                    return {}, True
                merged.update(field_value)
                expanded[field_name] = _normalize_payload_mapping(merged)
            else:
                return {}, True
        else:
            expanded[field_name] = field_value
    return _normalize_payload_mapping(expanded), False


def _barrier_reason_codes(
    *,
    barrier: ProviderExpansionHumanBarrier,
    provider_id: str,
    proposal_hash: str,
    governance_hash: str,
    base_payload_hash: str,
    field_names: tuple[str, ...],
) -> tuple[str, ...]:
    reason_codes: list[str] = []
    if barrier is None:
        return (CONTROLLED_PROVIDER_EXPANSION_BLOCKED_MISSING_HUMAN_BARRIER,)
    try:
        if barrier.barrier_hash != compute_provider_expansion_barrier_hash(_barrier_hash_material(barrier)):
            reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH)
    except (TypeError, ValueError):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_HASH_MISMATCH)
    if (
        barrier.provider_id != provider_id
        or barrier.proposal_hash != proposal_hash
        or barrier.governance_hash != governance_hash
        or barrier.base_payload_hash != base_payload_hash
        or barrier.operation != PROVIDER_EXPANSION_OPERATION_APPLY_INERT_PAYLOAD
    ):
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_BARRIER_SCOPE_MISMATCH)
    if tuple(sorted(barrier.approved_fields)) != field_names:
        reason_codes.append(CONTROLLED_PROVIDER_EXPANSION_BLOCKED_FIELD_NOT_APPROVED)
    return tuple(reason_codes)


def _coerce_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            return dict(mapped)
    raise TypeError("expected mapping evidence")


def _coerce_governance(value: object) -> dict[str, Any]:
    if isinstance(value, ProviderPayloadExpansionGovernanceResult):
        return value.to_dict()
    return _coerce_mapping(value)


def _coerce_barrier(value: object) -> ProviderExpansionHumanBarrier:
    if isinstance(value, ProviderExpansionHumanBarrier):
        return value
    if isinstance(value, Mapping):
        return ProviderExpansionHumanBarrier(**dict(value))
    raise TypeError("provider expansion human barrier is required")


def _proposal_hash(proposal: Mapping[str, Any]) -> str:
    return compute_provider_payload_expansion_hash(
        proposal_id=_required_text("proposal_id", proposal.get("proposal_id")),
        provider_id=_required_text("provider_id", proposal.get("provider_id")),
        base_payload_hash=_required_hash("base_payload_hash", proposal.get("base_payload_hash")),
        proposed_fields=_normalize_payload_mapping(proposal.get("proposed_fields")),
        rationale=_required_text("rationale", proposal.get("rationale")),
        created_at_tick=_nonnegative_int("created_at_tick", proposal.get("created_at_tick")),
        expires_at_tick=_nonnegative_int("expires_at_tick", proposal.get("expires_at_tick")),
    )


def _barrier_hash_material(barrier: ProviderExpansionHumanBarrier) -> dict[str, Any]:
    data = barrier.to_dict()
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _blocked(
    reason_codes: tuple[str, ...],
    *,
    provider_id: str | None = None,
    base_payload_hash: str | None = None,
    proposal_hash: str | None = None,
    governance_hash: str | None = None,
    barrier_hash: str | None = None,
) -> ControlledProviderExpansionResult:
    return _result(
        status=CONTROLLED_PROVIDER_EXPANSION_BLOCKED,
        reason_codes=reason_codes,
        provider_id=provider_id,
        base_payload_hash=base_payload_hash,
        proposal_hash=proposal_hash,
        governance_hash=governance_hash,
        barrier_hash=barrier_hash,
        expanded_payload_hash=None,
        expanded_payload=None,
        applied_fields=(),
    )


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    provider_id: str | None,
    base_payload_hash: str | None,
    proposal_hash: str | None,
    governance_hash: str | None,
    barrier_hash: str | None,
    expanded_payload_hash: str | None,
    expanded_payload: Mapping[str, Any] | None,
    applied_fields: tuple[str, ...],
) -> ControlledProviderExpansionResult:
    material = {
        "schema_version": CONTROLLED_PROVIDER_EXPANSION_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "provider_id": provider_id,
        "base_payload_hash": base_payload_hash,
        "proposal_hash": proposal_hash,
        "governance_hash": governance_hash,
        "barrier_hash": barrier_hash,
        "expanded_payload_hash": expanded_payload_hash,
        "expanded_payload": _fingerprint(expanded_payload),
        "applied_fields": tuple(sorted(set(applied_fields))),
        "human_review_required": True,
        "inert_payload_expanded": status == CONTROLLED_PROVIDER_EXPANSION_APPLIED_INERT,
        "provider_called": False,
        "network_called": False,
        "execution_performed": False,
        "file_written": False,
        "browser_opened": False,
        "package_installed": False,
        "git_action_performed": False,
        "can_call_provider": False,
    }
    return ControlledProviderExpansionResult(
        schema_version=CONTROLLED_PROVIDER_EXPANSION_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        provider_id=provider_id,
        base_payload_hash=base_payload_hash,
        proposal_hash=proposal_hash,
        governance_hash=governance_hash,
        barrier_hash=barrier_hash,
        expanded_payload_hash=expanded_payload_hash,
        expanded_payload=expanded_payload,
        applied_fields=applied_fields,
        result_hash=_stable_hash(material),
    )


def _normalize_payload_mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("payload evidence must be a mapping")
    normalized: dict[str, Any] = {}
    for key in sorted(value):
        name = _required_text("payload field", key)
        normalized[name] = _normalize_payload_value(value[key])
    return normalized


def _normalize_payload_value(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return _normalize_payload_mapping(value)
    if isinstance(value, (tuple, list)):
        return tuple(_normalize_payload_value(item) for item in value)
    raise TypeError("payload evidence contains unsupported value")


def _has_forbidden_key(value: object) -> bool:
    return _has_key(value, _DANGEROUS_FIELD_NAMES)


def _has_authority_key(value: object) -> bool:
    return _has_key(value, _AUTHORITY_FIELD_NAMES)


def _has_key(value: object, names: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in names:
                return True
            if _has_key(item, names):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_has_key(item, names) for item in value)
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


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value)
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized.lower()


def _text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError(f"{name} must be a non-empty text tuple")
    return tuple(sorted(_required_text(name, item) for item in value))


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: object) -> str:
    material = json.dumps(_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
