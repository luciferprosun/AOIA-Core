from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from runtime.auth_chain_assembler import (
    ASSEMBLY_NOT_AUTHORITY,
    AUTH_CHAIN_ASSEMBLED_NO_EXECUTION,
    AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION,
    DEFAULT_DENY_ON_INVALID_CHAIN,
    END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY,
    INERT_AUTH_CHAIN_ASSEMBLY,
    NO_ARTIFACT_WRITE,
    NO_CANONICAL_PROMOTION,
    NO_EXECUTION,
    NO_GITHUB_ACTION,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION,
    AuthChainAssemblyResult,
    AuthChainAssemblyStatus,
)


# AUTH-1F emits terminal review data only. Nothing in this module can dispatch
# work or turn a human/policy review outcome into runtime authority.
EXECUTION_READINESS_RECORD = "EXECUTION_READINESS_RECORD"
EXECUTION_READINESS_REJECTION = "EXECUTION_READINESS_REJECTION"
EXECUTION_READINESS_SCHEMA_VERSION = "1.0"
INERT_RECORD_REVIEW_READY = "INERT_RECORD_REVIEW_READY"
INERT_PROPOSAL_REVIEW_READY = "INERT_PROPOSAL_REVIEW_READY"

_RECORD_NOTE = (
    "Terminal inert review data only; this is not an instruction to execute."
)
_REJECTION_NOTE = (
    "No execution or readiness authority is created by this rejection."
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_BOUNDARIES = (
    NO_EXECUTION,
    NO_ARTIFACT_WRITE,
    NO_PROVIDER_LIVE_CALL,
    NO_PROVIDER_TRUST_CHANGE,
    NO_GITHUB_ACTION,
    NO_CANONICAL_PROMOTION,
    ASSEMBLY_NOT_AUTHORITY,
    REVIEW_REQUIRED_BEFORE_ANY_FUTURE_ACTION,
    DEFAULT_DENY_ON_INVALID_CHAIN,
)


@dataclass(frozen=True)
class ExecutionReadinessRecord:
    label: str
    schema_version: str
    readiness_status: str
    assembly_hash: str
    source_status_summary: str
    readiness_hash: str
    inert_note: str
    execution_allowed: bool
    dispatch_allowed: bool
    artifact_write_allowed: bool
    provider_call_allowed: bool
    github_action_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "readiness_status": self.readiness_status,
            "assembly_hash": self.assembly_hash,
            "source_status_summary": self.source_status_summary,
            "readiness_hash": self.readiness_hash,
            "inert_note": self.inert_note,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "github_action_allowed": self.github_action_allowed,
        }


@dataclass(frozen=True)
class ExecutionReadinessRejection:
    label: str
    schema_version: str
    rejection_reason: str
    assembly_hash: str | None
    source_status_summary: str
    rejection_hash: str
    inert_note: str
    execution_allowed: bool
    dispatch_allowed: bool
    artifact_write_allowed: bool
    provider_call_allowed: bool
    github_action_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "rejection_reason": self.rejection_reason,
            "assembly_hash": self.assembly_hash,
            "source_status_summary": self.source_status_summary,
            "rejection_hash": self.rejection_hash,
            "inert_note": self.inert_note,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "github_action_allowed": self.github_action_allowed,
        }


def evaluate_execution_readiness(
    assembly: object,
) -> ExecutionReadinessRecord | ExecutionReadinessRejection:
    """Classify a verified AUTH-1E result without creating action authority."""
    if not isinstance(assembly, AuthChainAssemblyResult):
        return _reject(
            reason="AUTH-1E assembly result is missing or malformed",
            assembly_hash=None,
            source_status_summary="AUTH_CHAIN_SOURCE_INVALID",
        )

    raw_assembly_hash = assembly.assembly_hash
    assembly_hash = (
        raw_assembly_hash
        if isinstance(raw_assembly_hash, str)
        and _SHA256_PATTERN.fullmatch(raw_assembly_hash)
        else None
    )
    source_status_summary = _source_summary(assembly)
    try:
        contract_error = _validate_assembly(assembly)
    except (AttributeError, TypeError, ValueError):
        contract_error = "AUTH-1E assembly contains malformed contract fields"
    if contract_error is not None:
        return _reject(
            reason=contract_error,
            assembly_hash=assembly_hash,
            source_status_summary=source_status_summary,
        )

    if assembly.assembly_status is AuthChainAssemblyStatus.AUTH_CHAIN_RECORD_ONLY:
        return _record(
            readiness_status=INERT_RECORD_REVIEW_READY,
            assembly_hash=assembly.assembly_hash,
            source_status_summary=source_status_summary,
        )
    if assembly.assembly_status is AuthChainAssemblyStatus.AUTH_CHAIN_PROPOSAL_ONLY:
        return _record(
            readiness_status=INERT_PROPOSAL_REVIEW_READY,
            assembly_hash=assembly.assembly_hash,
            source_status_summary=source_status_summary,
        )
    if assembly.assembly_status is AuthChainAssemblyStatus.AUTH_CHAIN_DENIED:
        reason = "AUTH-1E assembly denied the requested action"
    elif assembly.assembly_status is (
        AuthChainAssemblyStatus.AUTH_CHAIN_REQUIRES_FUTURE_MILESTONE
    ):
        reason = "AUTH-1E assembly requires a separately reviewed future milestone"
    else:
        reason = "AUTH-1E assembly is invalid or incomplete"
    return _reject(
        reason=reason,
        assembly_hash=assembly.assembly_hash,
        source_status_summary=source_status_summary,
    )


def _validate_assembly(assembly: AuthChainAssemblyResult) -> str | None:
    if not isinstance(assembly.assembly_hash, str) or not _SHA256_PATTERN.fullmatch(
        assembly.assembly_hash
    ):
        return "AUTH-1E assembly hash is missing or malformed"
    if (
        assembly.label != INERT_AUTH_CHAIN_ASSEMBLY
        or assembly.schema_version != AUTH_CHAIN_ASSEMBLY_SCHEMA_VERSION
        or assembly.assembly_role != END_TO_END_AUTH_REVIEW_ASSEMBLER_ONLY
        or assembly.final_status != AUTH_CHAIN_ASSEMBLED_NO_EXECUTION
    ):
        return "AUTH-1E assembly contract is invalid"
    if not isinstance(assembly.assembly_status, AuthChainAssemblyStatus):
        return "AUTH-1E assembly status is invalid"
    if tuple(item.value for item in assembly.safety_boundaries) != _EXPECTED_BOUNDARIES:
        return "AUTH-1E safety boundaries are incomplete or changed"
    if any(
        (
            assembly.execution_authority,
            assembly.artifact_write_authority,
            assembly.provider_live_call_authority,
            assembly.provider_trust_authority,
            assembly.github_authority,
            assembly.canonical_promotion_authority,
        )
    ):
        return "AUTH-1E source claims authority outside the readiness boundary"
    if _recompute_assembly_hash(assembly) != assembly.assembly_hash:
        return "AUTH-1E assembly hash verification failed"
    return None


def _recompute_assembly_hash(assembly: AuthChainAssemblyResult) -> str:
    semantic = assembly.to_dict()
    semantic.pop("created_at_utc", None)
    semantic.pop("assembly_hash", None)
    return _stable_hash(semantic)


def _source_summary(assembly: AuthChainAssemblyResult) -> str:
    status = (
        assembly.assembly_status.value
        if isinstance(assembly.assembly_status, AuthChainAssemblyStatus)
        else "INVALID"
    )
    return " | ".join(
        (
            f"assembly_status={status}",
            f"bridge_status={_summary_value(assembly.bridge_status)}",
            f"review_packet_status={_summary_value(assembly.review_packet_status)}",
            f"final_status={_summary_value(assembly.final_status)}",
        )
    )


def _summary_value(value: object) -> str:
    if value is None:
        return "NOT_ATTACHED"
    if isinstance(value, str) and re.fullmatch(r"[A-Z0-9_]+", value):
        return value
    return "INVALID"


def _record(
    *,
    readiness_status: str,
    assembly_hash: str,
    source_status_summary: str,
) -> ExecutionReadinessRecord:
    semantic = {
        "label": EXECUTION_READINESS_RECORD,
        "schema_version": EXECUTION_READINESS_SCHEMA_VERSION,
        "readiness_status": readiness_status,
        "assembly_hash": assembly_hash,
        "source_status_summary": source_status_summary,
        "inert_note": _RECORD_NOTE,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "artifact_write_allowed": False,
        "provider_call_allowed": False,
        "github_action_allowed": False,
    }
    return ExecutionReadinessRecord(
        **semantic,
        readiness_hash=_stable_hash(semantic),
    )


def _reject(
    *,
    reason: str,
    assembly_hash: str | None,
    source_status_summary: str,
) -> ExecutionReadinessRejection:
    semantic = {
        "label": EXECUTION_READINESS_REJECTION,
        "schema_version": EXECUTION_READINESS_SCHEMA_VERSION,
        "rejection_reason": reason,
        "assembly_hash": assembly_hash,
        "source_status_summary": source_status_summary,
        "inert_note": _REJECTION_NOTE,
        "execution_allowed": False,
        "dispatch_allowed": False,
        "artifact_write_allowed": False,
        "provider_call_allowed": False,
        "github_action_allowed": False,
    }
    return ExecutionReadinessRejection(
        **semantic,
        rejection_hash=_stable_hash(semantic),
    )


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
