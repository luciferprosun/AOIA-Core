from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from runtime.patches.patch_policy import (
    PATCH_POLICY_BLOCK,
    PATCH_POLICY_NEEDS_REVIEW,
    PATCH_POLICY_PASS,
    PatchPolicyCheckResult,
)
from runtime.patches.patch_preview import PatchPreview, PatchPreviewResult


PATCH_BARRIER_SCHEMA_VERSION = "AOIA_HUMAN_PATCH_BARRIER_1A"

PATCH_DECISION_APPROVE = "APPROVE"
PATCH_DECISION_REJECT = "REJECT"
PATCH_DECISION_REQUEST_CHANGES = "REQUEST_CHANGES"

PATCH_BARRIER_APPROVED = "PATCH_BARRIER_APPROVED"
PATCH_BARRIER_REJECTED = "PATCH_BARRIER_REJECTED"
PATCH_BARRIER_REQUESTED_CHANGES = "PATCH_BARRIER_REQUESTED_CHANGES"
PATCH_BARRIER_VERIFIED = "PATCH_BARRIER_VERIFIED"
PATCH_BARRIER_BLOCKED = "PATCH_BARRIER_BLOCKED"

PATCH_BARRIER_BLOCKED_MISSING_BARRIER = "PATCH_BARRIER_BLOCKED_MISSING_BARRIER"
PATCH_BARRIER_BLOCKED_MALFORMED_BARRIER = "PATCH_BARRIER_BLOCKED_MALFORMED_BARRIER"
PATCH_BARRIER_BLOCKED_MISSING_DECISION = "PATCH_BARRIER_BLOCKED_MISSING_DECISION"
PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION = "PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION"
PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID = "PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID"
PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH = "PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH"
PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH = "PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH"
PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH = "PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH"
PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH = "PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH"
PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH = "PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH"
PATCH_BARRIER_BLOCKED_HASH_MISMATCH = "PATCH_BARRIER_BLOCKED_HASH_MISMATCH"
PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE = "PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE"
PATCH_BARRIER_BLOCKED_INVALID_POLICY_STATUS = "PATCH_BARRIER_BLOCKED_INVALID_POLICY_STATUS"
PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM = "PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM"

PATCH_BARRIER_RISK_NEEDS_REVIEW_HUMAN_OVERRIDE = "needs_review_human_override"
PATCH_BARRIER_RISK_POLICY_BLOCK_REJECTION_RECORD = "policy_block_rejection_record"

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_VALID_DECISIONS = frozenset(
    {
        PATCH_DECISION_APPROVE,
        PATCH_DECISION_REJECT,
        PATCH_DECISION_REQUEST_CHANGES,
    }
)
_VALID_POLICY_STATUSES = frozenset(
    {
        PATCH_POLICY_PASS,
        PATCH_POLICY_NEEDS_REVIEW,
        PATCH_POLICY_BLOCK,
    }
)
_AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "write_authority_granted",
    "execution_authority_granted",
    "provider_authority_granted",
)


@dataclass(frozen=True)
class HumanPatchDecision:
    schema_version: str
    decision_id: str
    decision_value: str
    reviewer_id: str | None
    created_at: str
    patch_preview_hash: str
    patch_policy_hash: str
    policy_status: str
    policy_profile_name: str | None
    policy_profile_version: str | None
    target_paths: tuple[str, ...]
    target_binding_hash: str
    patch_preview_id: str | None
    reason: str | None
    barrier_hash: str
    risk_flags: tuple[str, ...] = ()
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_paths", tuple(self.target_paths))
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "decision_value": self.decision_value,
            "reviewer_id": self.reviewer_id,
            "created_at": self.created_at,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "policy_status": self.policy_status,
            "policy_profile_name": self.policy_profile_name,
            "policy_profile_version": self.policy_profile_version,
            "target_paths": list(self.target_paths),
            "target_binding_hash": self.target_binding_hash,
            "patch_preview_id": self.patch_preview_id,
            "reason": self.reason,
            "barrier_hash": self.barrier_hash,
            "risk_flags": list(self.risk_flags),
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


@dataclass(frozen=True)
class HumanPatchBarrierResult:
    schema_version: str
    status: str
    barrier_valid: bool
    barrier_hash: str | None
    barrier_id: str | None
    decision: HumanPatchDecision | None
    decision_id: str | None
    decision_value: str | None
    patch_preview_hash: str | None
    patch_policy_hash: str | None
    target_binding_hash: str | None
    target_paths: tuple[str, ...]
    policy_status: str | None
    policy_profile_name: str | None
    policy_profile_version: str | None
    reason_code: str
    reason: str
    risk_flags: tuple[str, ...] = ()
    patch_approved: bool = False
    patch_rejected: bool = False
    patch_changes_requested: bool = False
    patch_applied: bool = False
    file_written: bool = False
    provider_called: bool = False
    action_dispatched: bool = False
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_paths", tuple(self.target_paths))
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        object.__setattr__(self, "patch_approved", self.status in (PATCH_BARRIER_APPROVED, PATCH_BARRIER_VERIFIED) and self.decision_value == PATCH_DECISION_APPROVE)
        object.__setattr__(self, "patch_rejected", self.status in (PATCH_BARRIER_REJECTED, PATCH_BARRIER_VERIFIED) and self.decision_value == PATCH_DECISION_REJECT)
        object.__setattr__(self, "patch_changes_requested", self.status in (PATCH_BARRIER_REQUESTED_CHANGES, PATCH_BARRIER_VERIFIED) and self.decision_value == PATCH_DECISION_REQUEST_CHANGES)
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)
        for field_name in ("patch_applied", "file_written", "provider_called", "action_dispatched"):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "barrier_valid": self.barrier_valid,
            "barrier_hash": self.barrier_hash,
            "barrier_id": self.barrier_id,
            "decision": self.decision.to_dict() if self.decision is not None else None,
            "decision_id": self.decision_id,
            "decision_value": self.decision_value,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "target_binding_hash": self.target_binding_hash,
            "target_paths": list(self.target_paths),
            "policy_status": self.policy_status,
            "policy_profile_name": self.policy_profile_name,
            "policy_profile_version": self.policy_profile_version,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "risk_flags": list(self.risk_flags),
            "patch_approved": self.patch_approved,
            "patch_rejected": self.patch_rejected,
            "patch_changes_requested": self.patch_changes_requested,
            "patch_applied": self.patch_applied,
            "file_written": self.file_written,
            "provider_called": self.provider_called,
            "action_dispatched": self.action_dispatched,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


def canonical_patch_barrier_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_patch_barrier_hash(value: Any) -> str:
    return hashlib.sha256(canonical_patch_barrier_json(value).encode("utf-8")).hexdigest()


def create_human_patch_barrier(
    *,
    decision_value: str | None,
    patch_preview: PatchPreview | PatchPreviewResult | None,
    patch_policy: PatchPolicyCheckResult | None,
    decision_id: str | None = None,
    reviewer_id: str | None = None,
    created_at: str | None = None,
    reason: str | None = None,
) -> HumanPatchBarrierResult:
    decision = _normalize_decision(decision_value)
    if decision is None:
        return _blocked(PATCH_BARRIER_BLOCKED_MISSING_DECISION, "human patch decision is required")
    if decision not in _VALID_DECISIONS:
        return _blocked(PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION, "human patch decision is not recognized")
    if not _non_empty(decision_id):
        return _blocked(PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID, "human patch decision id is required")

    preview_metadata, preview_error = _preview_metadata(patch_preview)
    if preview_error is not None:
        return _blocked(preview_error, "patch preview hash binding is missing or malformed")
    policy_metadata, policy_error = _policy_metadata(patch_policy)
    if policy_error is not None:
        return _blocked(policy_error, "patch policy hash binding is missing or malformed")

    assert preview_metadata is not None
    assert policy_metadata is not None

    if preview_metadata["preview_hash"] != policy_metadata["patch_preview_hash"]:
        return _blocked(PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH, "patch preview hash does not match policy binding")
    if tuple(preview_metadata["target_paths"]) != tuple(policy_metadata["target_paths"]):
        return _blocked(PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH, "patch target binding does not match policy binding")
    if policy_metadata["policy_status"] == PATCH_POLICY_BLOCK and decision == PATCH_DECISION_APPROVE:
        return _blocked(PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE, "blocked patch policy cannot be approved")

    risk_flags = _risk_flags_for_policy(decision, policy_metadata["policy_status"])
    target_paths = tuple(preview_metadata["target_paths"])
    target_binding_hash = compute_patch_barrier_hash({"target_paths": list(target_paths)})
    material = _decision_material(
        decision_id=decision_id or "",
        decision_value=decision,
        reviewer_id=_optional_text(reviewer_id),
        created_at=_timestamp(created_at),
        patch_preview_hash=preview_metadata["preview_hash"],
        patch_policy_hash=policy_metadata["policy_hash"],
        policy_status=policy_metadata["policy_status"],
        policy_profile_name=policy_metadata["policy_profile_name"],
        policy_profile_version=policy_metadata["policy_profile_version"],
        target_paths=target_paths,
        target_binding_hash=target_binding_hash,
        patch_preview_id=preview_metadata["preview_id"],
        reason=_optional_text(reason),
        risk_flags=risk_flags,
    )
    barrier_hash = compute_patch_barrier_hash(material)
    decision_record = HumanPatchDecision(
        **material,
        barrier_hash=barrier_hash,
    )
    if decision == PATCH_DECISION_APPROVE:
        status = PATCH_BARRIER_APPROVED
        reason_code = PATCH_BARRIER_APPROVED
        reason_text = "human approved this hash-bound patch evidence only"
    elif decision == PATCH_DECISION_REJECT:
        status = PATCH_BARRIER_REJECTED
        reason_code = PATCH_BARRIER_REJECTED
        reason_text = "human rejected this hash-bound patch evidence"
    else:
        status = PATCH_BARRIER_REQUESTED_CHANGES
        reason_code = PATCH_BARRIER_REQUESTED_CHANGES
        reason_text = "human requested changes for this hash-bound patch evidence"
    return _result(
        status=status,
        barrier_valid=True,
        decision=decision_record,
        reason_code=reason_code,
        reason=reason_text,
    )


def verify_human_patch_barrier(
    barrier: HumanPatchBarrierResult | HumanPatchDecision | dict[str, Any] | None,
    *,
    expected_patch_preview_hash: str | None = None,
    expected_patch_policy_hash: str | None = None,
    expected_target_paths: tuple[str, ...] | list[str] | None = None,
    expected_policy_status: str | None = None,
) -> HumanPatchBarrierResult:
    if _has_authority_claim(barrier) or _raw_authority_claim(barrier):
        return _blocked(PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM, "human patch barrier contains authority-like claims")
    decision, error = _coerce_decision(barrier)
    if error is not None:
        return _blocked(error, "human patch barrier is missing or malformed")
    assert decision is not None

    if _has_authority_claim(decision):
        return _blocked(PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM, "human patch barrier contains authority-like claims")
    if not _non_empty(decision.decision_id):
        return _blocked(PATCH_BARRIER_BLOCKED_MISSING_DECISION_ID, "human patch decision id is required")
    normalized_decision = _normalize_decision(decision.decision_value)
    if normalized_decision not in _VALID_DECISIONS:
        return _blocked(PATCH_BARRIER_BLOCKED_UNKNOWN_DECISION, "human patch decision is not recognized")
    if not _full_hash(decision.patch_preview_hash):
        return _blocked(PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH, "patch preview hash is required")
    if not _full_hash(decision.patch_policy_hash):
        return _blocked(PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH, "patch policy hash is required")
    if decision.policy_status not in _VALID_POLICY_STATUSES:
        return _blocked(PATCH_BARRIER_BLOCKED_INVALID_POLICY_STATUS, "patch policy status is invalid")
    if decision.policy_status == PATCH_POLICY_BLOCK and normalized_decision == PATCH_DECISION_APPROVE:
        return _blocked(PATCH_BARRIER_BLOCKED_POLICY_BLOCK_APPROVE, "blocked patch policy cannot be approved")
    if expected_patch_preview_hash is not None and decision.patch_preview_hash != expected_patch_preview_hash:
        return _blocked(PATCH_BARRIER_BLOCKED_PATCH_PREVIEW_HASH_MISMATCH, "barrier is bound to a different patch preview hash")
    if expected_patch_policy_hash is not None and decision.patch_policy_hash != expected_patch_policy_hash:
        return _blocked(PATCH_BARRIER_BLOCKED_PATCH_POLICY_HASH_MISMATCH, "barrier is bound to a different patch policy hash")
    if expected_policy_status is not None and decision.policy_status != expected_policy_status:
        return _blocked(PATCH_BARRIER_BLOCKED_INVALID_POLICY_STATUS, "barrier is bound to a different patch policy status")
    expected_targets = tuple(expected_target_paths) if expected_target_paths is not None else None
    if expected_targets is not None and tuple(decision.target_paths) != expected_targets:
        return _blocked(PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH, "barrier is bound to a different target set")
    expected_target_hash = compute_patch_barrier_hash({"target_paths": list(decision.target_paths)})
    if decision.target_binding_hash != expected_target_hash:
        return _blocked(PATCH_BARRIER_BLOCKED_TARGET_BINDING_MISMATCH, "barrier target binding hash is invalid")

    material = _decision_material(
        decision_id=decision.decision_id,
        decision_value=normalized_decision or "",
        reviewer_id=decision.reviewer_id,
        created_at=decision.created_at,
        patch_preview_hash=decision.patch_preview_hash,
        patch_policy_hash=decision.patch_policy_hash,
        policy_status=decision.policy_status,
        policy_profile_name=decision.policy_profile_name,
        policy_profile_version=decision.policy_profile_version,
        target_paths=tuple(decision.target_paths),
        target_binding_hash=decision.target_binding_hash,
        patch_preview_id=decision.patch_preview_id,
        reason=decision.reason,
        risk_flags=tuple(decision.risk_flags),
    )
    if compute_patch_barrier_hash(material) != decision.barrier_hash:
        return _blocked(PATCH_BARRIER_BLOCKED_HASH_MISMATCH, "human patch barrier hash does not match its material")

    return _result(
        status=PATCH_BARRIER_VERIFIED,
        barrier_valid=True,
        decision=decision,
        reason_code=PATCH_BARRIER_VERIFIED,
        reason="human patch barrier verified as hash-bound evidence only",
    )


def _decision_material(
    *,
    decision_id: str,
    decision_value: str,
    reviewer_id: str | None,
    created_at: str,
    patch_preview_hash: str,
    patch_policy_hash: str,
    policy_status: str,
    policy_profile_name: str | None,
    policy_profile_version: str | None,
    target_paths: tuple[str, ...],
    target_binding_hash: str,
    patch_preview_id: str | None,
    reason: str | None,
    risk_flags: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": PATCH_BARRIER_SCHEMA_VERSION,
        "decision_id": decision_id,
        "decision_value": decision_value,
        "reviewer_id": reviewer_id,
        "created_at": created_at,
        "patch_preview_hash": patch_preview_hash,
        "patch_policy_hash": patch_policy_hash,
        "policy_status": policy_status,
        "policy_profile_name": policy_profile_name,
        "policy_profile_version": policy_profile_version,
        "target_paths": list(target_paths),
        "target_binding_hash": target_binding_hash,
        "patch_preview_id": patch_preview_id,
        "reason": reason,
        "risk_flags": list(risk_flags),
    }


def _preview_metadata(value: PatchPreview | PatchPreviewResult | None) -> tuple[dict[str, Any] | None, str | None]:
    preview: PatchPreview | None
    if isinstance(value, PatchPreviewResult):
        preview = value.patch_preview
    elif isinstance(value, PatchPreview):
        preview = value
    else:
        preview = None
    if preview is None or not _full_hash(preview.preview_hash):
        return None, PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH
    return {
        "preview_id": preview.preview_id,
        "preview_hash": preview.preview_hash,
        "target_paths": tuple(preview.target_paths),
    }, None


def _policy_metadata(value: PatchPolicyCheckResult | None) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, PatchPolicyCheckResult):
        return None, PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH
    if _has_authority_claim(value):
        return None, PATCH_BARRIER_BLOCKED_AUTHORITY_CLAIM
    if not _full_hash(value.policy_hash):
        return None, PATCH_BARRIER_BLOCKED_MISSING_PATCH_POLICY_HASH
    if not _full_hash(value.patch_preview_hash):
        return None, PATCH_BARRIER_BLOCKED_MISSING_PATCH_PREVIEW_HASH
    if value.status not in _VALID_POLICY_STATUSES:
        return None, PATCH_BARRIER_BLOCKED_INVALID_POLICY_STATUS
    return {
        "policy_hash": value.policy_hash,
        "patch_preview_hash": value.patch_preview_hash,
        "target_paths": tuple(value.target_paths),
        "policy_status": value.status,
        "policy_profile_name": value.policy_profile_name,
        "policy_profile_version": value.policy_profile_version,
    }, None


def _coerce_decision(value: HumanPatchBarrierResult | HumanPatchDecision | dict[str, Any] | None) -> tuple[HumanPatchDecision | None, str | None]:
    if value is None:
        return None, PATCH_BARRIER_BLOCKED_MISSING_BARRIER
    if isinstance(value, HumanPatchBarrierResult):
        if value.decision is None:
            return None, PATCH_BARRIER_BLOCKED_MISSING_BARRIER
        return value.decision, None
    if isinstance(value, HumanPatchDecision):
        return value, None
    if isinstance(value, dict):
        material = value.get("decision") if isinstance(value.get("decision"), dict) else value
        try:
            return HumanPatchDecision(
                schema_version=str(material["schema_version"]),
                decision_id=str(material["decision_id"]),
                decision_value=str(material["decision_value"]),
                reviewer_id=_optional_text(material.get("reviewer_id")),
                created_at=str(material["created_at"]),
                patch_preview_hash=str(material["patch_preview_hash"]),
                patch_policy_hash=str(material["patch_policy_hash"]),
                policy_status=str(material["policy_status"]),
                policy_profile_name=_optional_text(material.get("policy_profile_name")),
                policy_profile_version=_optional_text(material.get("policy_profile_version")),
                target_paths=tuple(material["target_paths"]),
                target_binding_hash=str(material["target_binding_hash"]),
                patch_preview_id=_optional_text(material.get("patch_preview_id")),
                reason=_optional_text(material.get("reason")),
                barrier_hash=str(material["barrier_hash"]),
                risk_flags=tuple(material.get("risk_flags", ())),
            ), None
        except (KeyError, TypeError, ValueError):
            return None, PATCH_BARRIER_BLOCKED_MALFORMED_BARRIER
    return None, PATCH_BARRIER_BLOCKED_MALFORMED_BARRIER


def _result(
    *,
    status: str,
    barrier_valid: bool,
    decision: HumanPatchDecision | None,
    reason_code: str,
    reason: str,
) -> HumanPatchBarrierResult:
    return HumanPatchBarrierResult(
        schema_version=PATCH_BARRIER_SCHEMA_VERSION,
        status=status,
        barrier_valid=barrier_valid,
        barrier_hash=decision.barrier_hash if decision is not None else None,
        barrier_id=f"human-patch-barrier-{decision.barrier_hash[:16]}" if decision is not None else None,
        decision=decision,
        decision_id=decision.decision_id if decision is not None else None,
        decision_value=decision.decision_value if decision is not None else None,
        patch_preview_hash=decision.patch_preview_hash if decision is not None else None,
        patch_policy_hash=decision.patch_policy_hash if decision is not None else None,
        target_binding_hash=decision.target_binding_hash if decision is not None else None,
        target_paths=decision.target_paths if decision is not None else (),
        policy_status=decision.policy_status if decision is not None else None,
        policy_profile_name=decision.policy_profile_name if decision is not None else None,
        policy_profile_version=decision.policy_profile_version if decision is not None else None,
        reason_code=reason_code,
        reason=reason,
        risk_flags=decision.risk_flags if decision is not None else (),
    )


def _blocked(reason_code: str, reason: str) -> HumanPatchBarrierResult:
    return HumanPatchBarrierResult(
        schema_version=PATCH_BARRIER_SCHEMA_VERSION,
        status=PATCH_BARRIER_BLOCKED,
        barrier_valid=False,
        barrier_hash=None,
        barrier_id=None,
        decision=None,
        decision_id=None,
        decision_value=None,
        patch_preview_hash=None,
        patch_policy_hash=None,
        target_binding_hash=None,
        target_paths=(),
        policy_status=None,
        policy_profile_name=None,
        policy_profile_version=None,
        reason_code=reason_code,
        reason=reason,
    )


def _risk_flags_for_policy(decision: str, policy_status: str) -> tuple[str, ...]:
    flags: list[str] = []
    if policy_status == PATCH_POLICY_NEEDS_REVIEW and decision == PATCH_DECISION_APPROVE:
        flags.append(PATCH_BARRIER_RISK_NEEDS_REVIEW_HUMAN_OVERRIDE)
    if policy_status == PATCH_POLICY_BLOCK and decision == PATCH_DECISION_REJECT:
        flags.append(PATCH_BARRIER_RISK_POLICY_BLOCK_REJECTION_RECORD)
    return tuple(flags)


def _normalize_decision(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    if normalized in ("", "APPROVED", "YES", "NO"):
        return None
    return normalized


def _timestamp(value: str | None) -> str:
    if _non_empty(value):
        return str(value).strip()
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _full_hash(value: Any) -> str | None:
    if isinstance(value, str) and _SHA256_HEX.fullmatch(value):
        return value
    return None


def _has_authority_claim(value: Any) -> bool:
    return any(getattr(value, field_name, False) is not False for field_name in _AUTHORITY_FIELDS)


def _raw_authority_claim(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if any(field_name in value and value[field_name] is not False for field_name in _AUTHORITY_FIELDS):
        return True
    nested = value.get("decision")
    return isinstance(nested, dict) and any(
        field_name in nested and nested[field_name] is not False for field_name in _AUTHORITY_FIELDS
    )


def _stable_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
