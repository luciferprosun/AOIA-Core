from __future__ import annotations

import hashlib
import json
import math
import posix
import posixpath
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from runtime.provider_controlled_flow import (
    NO_ARTIFACT_WRITE,
    NO_EXECUTION,
    REVIEW_REQUIRED,
)
from runtime.provider_critic_review import INERT_PROVIDER_CRITIC_REVIEW
from runtime.provider_live_adapter import LIVE_PROVIDER_ADAPTER_BLOCKED
from runtime.provider_request_flow import UNTRUSTED_PROVIDER_OUTPUT
from runtime.provider_review_projection import (
    DEFAULT_OFF_LIVE_ADAPTER,
    HUMAN_REVIEW_REQUIRED,
    NO_AUTO_APPROVAL,
    NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE,
    PROVIDER_REVIEW_PROJECTION,
    ProviderReviewProjection,
)


# Provider-G is a scoped record builder and verifier, not the final durable audit system.
PROVIDER_FLOW_AUDIT_RECORD = "PROVIDER_FLOW_AUDIT_RECORD"
PROVIDER_FLOW_AUDIT_SCHEMA_VERSION = "1.0"
CALLER_SUPPLIED_TEMP_ONLY = "CALLER_SUPPLIED_TEMP_ONLY"
PROVIDER_FLOW_RECORD_BUILDER = "PROVIDER_FLOW_RECORD_BUILDER"
NO_LIVE_PROVIDER_CALL = "NO_LIVE_PROVIDER_CALL"
NO_NETWORK = "NO_NETWORK"
DEFAULT_PROVIDER_SNIPPET_MAX_LENGTH = 512
MAX_PROVIDER_FLOW_AUDIT_BYTES = 64 * 1024

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SECRET_FIELD_NAMES = frozenset(
    {
        "secret",
        "token",
        "key",
        "api_key",
        "password",
        "authorization",
        "bearer",
    }
)
_FORBIDDEN_PERSISTED_KEY_FRAGMENTS = (
    "raw_payload",
    "raw_provider_output",
    "unredacted_payload",
    "encrypted_raw_payload",
    "original_secret",
    "forensic_secret",
)
_OSC_ESCAPE = re.compile(r"\x1b\][^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)")
_CSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_SINGLE_ESCAPE = re.compile(r"\x1b[@-_]")
_UNSAFE_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_EXPLICIT_CREDENTIAL_PATTERNS = (
    re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(secret|token|key|api_key|password|authorization|bearer)\b"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    re.IGNORECASE,
)
_TOKEN_CANDIDATE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_+/=-]{40,}(?![A-Za-z0-9_-])")
_HEX_HASH = re.compile(r"^[0-9a-f]{64}$")
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
    r"|[0-9]{1,8}[A-Za-z]?"
    r"|[a-z]{2,20}[0-9]{1,4}"
    r"|[A-Z][a-z]{1,19}[0-9]{1,4}"
    r"|[A-Z]{2,12}[0-9]{1,4}"
    r"|[0-9a-fA-F]{7,32}"
    r")"
)
_READABLE_IDENTITY_LABEL_SUFFIX = re.compile(r"[A-Z]{2,12}[0-9]{1,4}")
_READABLE_BRANCH_PREFIX = re.compile(r"[a-z][a-z0-9_-]{1,31}")


class ProviderFlowAuditError(ValueError):
    """Base fail-closed error for Provider-G record and verification boundaries."""


class ProviderFlowAuditPathError(ProviderFlowAuditError):
    """Raised when a path is outside its explicit caller-supplied scope."""


class ProviderFlowAuditVerificationError(ProviderFlowAuditError):
    """Raised when JSONL syntax, integrity, or chain verification fails."""


class ProviderFlowAuditBoundary(str, Enum):
    NO_LIVE_PROVIDER_CALL = NO_LIVE_PROVIDER_CALL
    NO_NETWORK = NO_NETWORK
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_AUTO_APPROVAL = NO_AUTO_APPROVAL
    HUMAN_REVIEW_REQUIRED = HUMAN_REVIEW_REQUIRED


@dataclass(frozen=True)
class ProviderFlowAuditRecord:
    label: str
    schema_version: str
    record_id: str
    flow_id: str
    timestamp_utc: str | None
    storage_scope: str
    audit_role: str
    content_hash: str
    previous_record_hash: str
    full_record_hash: str
    context_packet_hash: str | None
    context_packet_ref: str | None
    dissonance_flags: tuple[str, ...]
    provider_request_summary: Mapping[str, Any]
    provider_id: str
    provider_profile_id: str
    registry_decision_summary: Mapping[str, Any]
    live_adapter_status: Mapping[str, Any]
    provider_output_trust_label: str
    provider_output_hash: str
    provider_snippet: str | None
    critic_label: str
    critic_finding_count: int
    critic_finding_categories: tuple[str, ...]
    review_projection_label: str
    review_projection_status: str
    final_status: str
    safety_boundaries: tuple[ProviderFlowAuditBoundary, ...]
    source_object_ids: Mapping[str, str]
    source_object_hashes: Mapping[str, str]
    live_call_attempted: bool
    live_call_blocked: bool
    network_used: bool
    approved: bool
    automatic_approval: bool
    gate_eligible: bool
    execution_occurred: bool
    artifact_write_occurred: bool
    requires_human_review: bool
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "flow_id": self.flow_id,
            "timestamp_utc": self.timestamp_utc,
            "storage_scope": self.storage_scope,
            "audit_role": self.audit_role,
            "content_hash": self.content_hash,
            "previous_record_hash": self.previous_record_hash,
            "full_record_hash": self.full_record_hash,
            "context_packet_hash": self.context_packet_hash,
            "context_packet_ref": self.context_packet_ref,
            "dissonance_flags": list(self.dissonance_flags),
            "provider_request_summary": dict(self.provider_request_summary),
            "provider_id": self.provider_id,
            "provider_profile_id": self.provider_profile_id,
            "registry_decision_summary": dict(self.registry_decision_summary),
            "live_adapter_status": dict(self.live_adapter_status),
            "provider_output_trust_label": self.provider_output_trust_label,
            "provider_output_hash": self.provider_output_hash,
            "provider_snippet": self.provider_snippet,
            "critic_label": self.critic_label,
            "critic_finding_count": self.critic_finding_count,
            "critic_finding_categories": list(self.critic_finding_categories),
            "review_projection_label": self.review_projection_label,
            "review_projection_status": self.review_projection_status,
            "final_status": self.final_status,
            "safety_boundaries": [item.value for item in self.safety_boundaries],
            "source_object_ids": dict(self.source_object_ids),
            "source_object_hashes": dict(self.source_object_hashes),
            "live_call_attempted": self.live_call_attempted,
            "live_call_blocked": self.live_call_blocked,
            "network_used": self.network_used,
            "approved": self.approved,
            "automatic_approval": self.automatic_approval,
            "gate_eligible": self.gate_eligible,
            "execution_occurred": self.execution_occurred,
            "artifact_write_occurred": self.artifact_write_occurred,
            "requires_human_review": self.requires_human_review,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class ProviderFlowAuditAppendResult:
    audit_path: str
    record_id: str
    content_hash: str
    full_record_hash: str
    previous_record_hash: str
    bytes_written: int
    append_only: bool
    fsync_completed: bool


@dataclass(frozen=True)
class ProviderFlowAuditVerificationResult:
    valid: bool
    audit_path: str
    record_count: int
    record_ids: tuple[str, ...]
    content_hashes: tuple[str, ...]
    last_full_record_hash: str
    final_status: str | None
    records: tuple[ProviderFlowAuditRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "audit_path": self.audit_path,
            "record_count": self.record_count,
            "record_ids": list(self.record_ids),
            "content_hashes": list(self.content_hashes),
            "last_full_record_hash": self.last_full_record_hash,
            "final_status": self.final_status,
            "records": [record.to_dict() for record in self.records],
        }


def sanitize_audit_text(value: str) -> str:
    """Remove terminal controls while preserving readable text, safe tabs, and newlines."""
    if not isinstance(value, str):
        raise TypeError("audit text must be a string")
    text = _OSC_ESCAPE.sub("", value)
    text = _CSI_ESCAPE.sub("", text)
    text = _SINGLE_ESCAPE.sub("", text)
    text = text.replace("\x1b", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\b", "")
    return _UNSAFE_CONTROLS.sub("", text)


def redact_audit_text(
    value: str,
    *,
    known_secrets: Iterable[str] = (),
) -> str:
    """Redact explicit credential patterns without treating every long ID as a secret."""
    text = sanitize_audit_text(value)
    secrets = _normalized_known_secrets(known_secrets)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED]")
    text = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        text,
    )
    for pattern in _EXPLICIT_CREDENTIAL_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return _TOKEN_CANDIDATE.sub(_redact_high_entropy_candidate, text)


def build_provider_flow_audit_record(
    projection: ProviderReviewProjection,
    *,
    timestamp_utc: str | None = None,
    previous_record_hash: str = "",
    context_packet_hash: str | None = None,
    context_packet_ref: str | None = None,
    dissonance_flags: Iterable[str] = (),
    provider_snippet: str | None = None,
    snippet_max_length: int = DEFAULT_PROVIDER_SNIPPET_MAX_LENGTH,
    known_secrets: Iterable[str] = (),
) -> ProviderFlowAuditRecord:
    _validate_projection(projection)
    secrets = _normalized_known_secrets(known_secrets)
    timestamp = _optional_redacted_text(timestamp_utc, secrets, 128)
    previous_hash = _optional_chain_hash(previous_record_hash)
    context_hash = _optional_full_hash(context_packet_hash, "context_packet_hash")
    context_ref = _optional_redacted_text(context_packet_ref, secrets, 512)
    flags = _dissonance_flags(dissonance_flags, secrets)
    snippet = _provider_snippet(
        provider_snippet,
        snippet_max_length,
        secrets,
    )

    request = projection.provider_request_summary
    live = projection.live_adapter_section.details
    critic = projection.critic_section.details
    request_summary = _sanitize_mapping(
        {
            "request_id": request.get("request_id"),
            "request_hash": request.get("request_hash"),
            "provider_id": request.get("provider_id"),
            "purpose": request.get("purpose"),
            "caller_label": request.get("caller_label"),
            "request_metadata_present": bool(request.get("request_metadata")),
        },
        secrets,
    )
    registry_summary = _sanitize_mapping(
        projection.registry_decision_summary,
        secrets,
    )
    live_status = _sanitize_mapping(
        {
            "status": projection.live_adapter_section.status,
            "adapter_label": live.get("adapter_label"),
            "attempted": False,
            "blocked": True,
            "reason": live.get("blocked_reason"),
            "network_allowed": False,
        },
        secrets,
    )
    categories = tuple(
        redact_audit_text(finding.category, known_secrets=secrets)[:256]
        for finding in projection.critic_findings
    )
    boundaries = _required_boundaries()
    source_ids = _sanitize_string_mapping(
        {
            "provider_review_projection_id": projection.projection_id,
            "human_review_projection_id": projection.human_review_projection_id,
            "review_packet_id": projection.review_packet_id,
            "provider_output_id": projection.provider_output_summary.get("output_id"),
            "critic_review_id": critic.get("critic_review_id"),
            "live_adapter_decision_id": live.get("decision_id"),
        },
        secrets,
    )
    source_hashes = _sanitize_string_mapping(
        {
            "provider_review_projection_hash": projection.projection_hash,
            "human_review_projection_hash": projection.human_review_projection_hash,
            "review_packet_hash": projection.review_packet_hash,
            "provider_output_hash": projection.provider_output_summary.get("output_hash"),
            "critic_review_hash": critic.get("critic_review_hash"),
            "live_adapter_decision_hash": live.get("decision_hash"),
        },
        secrets,
    )
    semantic = {
        "label": PROVIDER_FLOW_AUDIT_RECORD,
        "schema_version": PROVIDER_FLOW_AUDIT_SCHEMA_VERSION,
        "flow_id": projection.projection_id,
        "storage_scope": CALLER_SUPPLIED_TEMP_ONLY,
        "audit_role": PROVIDER_FLOW_RECORD_BUILDER,
        "context_packet_hash": context_hash,
        "context_packet_ref": context_ref,
        "dissonance_flags": list(flags),
        "provider_request_summary": request_summary,
        "provider_id": projection.provider_id,
        "provider_profile_id": projection.provider_profile_id,
        "registry_decision_summary": registry_summary,
        "live_adapter_status": live_status,
        "provider_output_trust_label": UNTRUSTED_PROVIDER_OUTPUT,
        "provider_output_hash": str(
            projection.provider_output_summary.get("output_hash")
        ),
        "provider_snippet": snippet,
        "critic_label": INERT_PROVIDER_CRITIC_REVIEW,
        "critic_finding_count": len(categories),
        "critic_finding_categories": list(categories),
        "review_projection_label": PROVIDER_REVIEW_PROJECTION,
        "review_projection_status": REVIEW_REQUIRED,
        "final_status": REVIEW_REQUIRED,
        "safety_boundaries": [boundary.value for boundary in boundaries],
        "source_object_ids": source_ids,
        "source_object_hashes": source_hashes,
        "live_call_attempted": False,
        "live_call_blocked": True,
        "network_used": False,
        "approved": False,
        "automatic_approval": False,
        "gate_eligible": False,
        "execution_occurred": False,
        "artifact_write_occurred": False,
        "requires_human_review": True,
        "blocking": True,
    }
    content_hash = _stable_hash(semantic)
    record_id = "provider-g-flow-audit-" + content_hash[:24]
    full_material = {
        **semantic,
        "record_id": record_id,
        "timestamp_utc": timestamp,
        "content_hash": content_hash,
        "previous_record_hash": previous_hash,
    }
    full_record_hash = _stable_hash(full_material)
    return ProviderFlowAuditRecord(
        label=PROVIDER_FLOW_AUDIT_RECORD,
        schema_version=PROVIDER_FLOW_AUDIT_SCHEMA_VERSION,
        record_id=record_id,
        flow_id=projection.projection_id,
        timestamp_utc=timestamp,
        storage_scope=CALLER_SUPPLIED_TEMP_ONLY,
        audit_role=PROVIDER_FLOW_RECORD_BUILDER,
        content_hash=content_hash,
        previous_record_hash=previous_hash,
        full_record_hash=full_record_hash,
        context_packet_hash=context_hash,
        context_packet_ref=context_ref,
        dissonance_flags=flags,
        provider_request_summary=request_summary,
        provider_id=projection.provider_id,
        provider_profile_id=projection.provider_profile_id,
        registry_decision_summary=registry_summary,
        live_adapter_status=live_status,
        provider_output_trust_label=UNTRUSTED_PROVIDER_OUTPUT,
        provider_output_hash=str(
            projection.provider_output_summary.get("output_hash")
        ),
        provider_snippet=snippet,
        critic_label=INERT_PROVIDER_CRITIC_REVIEW,
        critic_finding_count=len(categories),
        critic_finding_categories=categories,
        review_projection_label=PROVIDER_REVIEW_PROJECTION,
        review_projection_status=REVIEW_REQUIRED,
        final_status=REVIEW_REQUIRED,
        safety_boundaries=boundaries,
        source_object_ids=source_ids,
        source_object_hashes=source_hashes,
        live_call_attempted=False,
        live_call_blocked=True,
        network_used=False,
        approved=False,
        automatic_approval=False,
        gate_eligible=False,
        execution_occurred=False,
        artifact_write_occurred=False,
        requires_human_review=True,
        blocking=True,
    )


def append_provider_flow_audit_record(
    audit_path: str | Path,
    record: ProviderFlowAuditRecord,
    *,
    allowed_root: str | Path,
) -> ProviderFlowAuditAppendResult:
    _validate_record(record)
    root, path = _resolve_scoped_path(audit_path, allowed_root)
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _assert_no_symlink(parent, "audit parent")
    _assert_no_symlink(path, "audit path")

    if path.exists():
        verification = verify_provider_flow_audit_log(
            path,
            allowed_root=root,
        )
        if record.record_id in verification.record_ids:
            raise ProviderFlowAuditError("duplicate provider-flow audit record id")
        if record.previous_record_hash != verification.last_full_record_hash:
            raise ProviderFlowAuditError("previous_record_hash does not match audit log")
    elif record.previous_record_hash:
        raise ProviderFlowAuditError(
            "first provider-flow audit record cannot declare a previous hash"
        )

    record_data = record.to_dict()
    line_hash = _stable_hash(record_data)
    envelope = {"line_hash": line_hash, "record": record_data}
    encoded = (_canonical_json(envelope) + "\n").encode("utf-8")
    if len(encoded) > MAX_PROVIDER_FLOW_AUDIT_BYTES:
        raise ProviderFlowAuditError("serialized provider-flow audit is too large")
    _append_and_fsync(path, encoded)
    return ProviderFlowAuditAppendResult(
        audit_path=str(path),
        record_id=record.record_id,
        content_hash=record.content_hash,
        full_record_hash=record.full_record_hash,
        previous_record_hash=record.previous_record_hash,
        bytes_written=len(encoded),
        append_only=True,
        fsync_completed=True,
    )


def verify_provider_flow_audit_log(
    audit_path: str | Path,
    *,
    allowed_root: str | Path,
) -> ProviderFlowAuditVerificationResult:
    root, path = _resolve_scoped_path(
        audit_path,
        allowed_root,
        create_root=False,
    )
    if not path.exists():
        return _empty_verification(path)
    _assert_no_symlink(path, "audit path")
    if not path.is_file():
        raise ProviderFlowAuditPathError("audit path must be a regular file")

    records: list[ProviderFlowAuditRecord] = []
    seen_ids: set[str] = set()
    expected_previous = ""
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.endswith(b"\n"):
                raise ProviderFlowAuditVerificationError(
                    f"partial JSONL line at {line_number}"
                )
            try:
                line = raw_line.decode("utf-8")
            except UnicodeDecodeError as error:
                raise ProviderFlowAuditVerificationError(
                    f"invalid UTF-8 at line {line_number}"
                ) from error
            if not line[:-1].strip():
                raise ProviderFlowAuditVerificationError(
                    f"empty JSONL line at {line_number}"
                )
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError as error:
                raise ProviderFlowAuditVerificationError(
                    f"invalid JSON at line {line_number}"
                ) from error
            if not isinstance(envelope, dict) or set(envelope) != {
                "line_hash",
                "record",
            }:
                raise ProviderFlowAuditVerificationError(
                    f"invalid envelope at line {line_number}"
                )
            if raw_line != (_canonical_json(envelope) + "\n").encode("utf-8"):
                raise ProviderFlowAuditVerificationError(
                    f"non-canonical or tampered bytes at line {line_number}"
                )
            record_data = envelope["record"]
            if envelope["line_hash"] != _stable_hash(record_data):
                raise ProviderFlowAuditVerificationError(
                    f"line hash mismatch at line {line_number}"
                )
            record = _record_from_mapping(record_data)
            _validate_record(record)
            if record.record_id in seen_ids:
                raise ProviderFlowAuditVerificationError(
                    f"duplicate record id at line {line_number}"
                )
            if record.previous_record_hash != expected_previous:
                raise ProviderFlowAuditVerificationError(
                    f"previous hash mismatch at line {line_number}"
                )
            if record.final_status != REVIEW_REQUIRED:
                raise ProviderFlowAuditVerificationError(
                    f"unsafe final status at line {line_number}"
                )
            records.append(record)
            seen_ids.add(record.record_id)
            expected_previous = record.full_record_hash

    final_status = REVIEW_REQUIRED if records else None
    return ProviderFlowAuditVerificationResult(
        valid=True,
        audit_path=str(path),
        record_count=len(records),
        record_ids=tuple(record.record_id for record in records),
        content_hashes=tuple(record.content_hash for record in records),
        last_full_record_hash=expected_previous,
        final_status=final_status,
        records=tuple(records),
    )


def _validate_projection(projection: ProviderReviewProjection) -> None:
    if not isinstance(projection, ProviderReviewProjection):
        raise ProviderFlowAuditError("a Provider-F review projection is required")
    live = projection.live_adapter_section
    critic = projection.critic_section
    output = projection.provider_output_summary
    registry = projection.registry_decision_summary
    if (
        projection.projection_label != PROVIDER_REVIEW_PROJECTION
        or projection.status != REVIEW_REQUIRED
        or projection.provider_output_trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or output.get("trust_label") != UNTRUSTED_PROVIDER_OUTPUT
        or output.get("live_call_used") is not False
        or projection.critic_label != INERT_PROVIDER_CRITIC_REVIEW
        or critic.status != INERT_PROVIDER_CRITIC_REVIEW
        or critic.details.get("authoritative") is not False
        or live.status != LIVE_PROVIDER_ADAPTER_BLOCKED
        or live.details.get("adapter_label") != DEFAULT_OFF_LIVE_ADAPTER
        or live.details.get("live_call_attempted") is not False
        or live.details.get("live_call_blocked") is not True
        or live.details.get("network_allowed") is not False
        or registry.get("network_allowed") is not False
        or registry.get("live_call_allowed") is not False
        or projection.required_human_action != HUMAN_REVIEW_REQUIRED
        or tuple(projection.safety_boundary_summary)
        != (
            NO_EXECUTION,
            NO_ARTIFACT_WRITE,
            NO_AUTO_APPROVAL,
            NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE,
        )
        or projection.requires_human_review is not True
        or projection.approved is not False
        or projection.automatic_approval is not False
        or projection.authoritative is not False
        or projection.gate_eligible is not False
        or projection.write_eligible is not False
        or projection.execution_occurred is not False
        or projection.artifact_write_occurred is not False
        or projection.provider_live_call_used is not False
        or projection.blocking is not True
    ):
        raise ProviderFlowAuditError(
            "provider review projection violates the inert audit boundary"
        )
    if not live.details.get("blocked_reason"):
        raise ProviderFlowAuditError("live adapter blocked reason is required")
    if not projection.critic_findings:
        raise ProviderFlowAuditError("attached critic findings are required")


def _validate_record(record: ProviderFlowAuditRecord) -> None:
    if not isinstance(record, ProviderFlowAuditRecord):
        raise TypeError("record must be a ProviderFlowAuditRecord")
    if record.to_dict().keys() != _required_record_fields():
        raise ProviderFlowAuditError("provider-flow audit required fields mismatch")
    if (
        record.label != PROVIDER_FLOW_AUDIT_RECORD
        or record.schema_version != PROVIDER_FLOW_AUDIT_SCHEMA_VERSION
        or record.storage_scope != CALLER_SUPPLIED_TEMP_ONLY
        or record.audit_role != PROVIDER_FLOW_RECORD_BUILDER
        or record.provider_output_trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or record.critic_label != INERT_PROVIDER_CRITIC_REVIEW
        or record.review_projection_label != PROVIDER_REVIEW_PROJECTION
        or record.review_projection_status != REVIEW_REQUIRED
        or record.final_status != REVIEW_REQUIRED
        or tuple(record.safety_boundaries) != _required_boundaries()
        or record.live_adapter_status.get("attempted") is not False
        or record.live_adapter_status.get("blocked") is not True
        or record.live_adapter_status.get("network_allowed") is not False
        or record.live_call_attempted is not False
        or record.live_call_blocked is not True
        or record.network_used is not False
        or record.approved is not False
        or record.automatic_approval is not False
        or record.gate_eligible is not False
        or record.execution_occurred is not False
        or record.artifact_write_occurred is not False
        or record.requires_human_review is not True
        or record.blocking is not True
    ):
        raise ProviderFlowAuditError(
            "provider-flow audit record violates the inert boundary"
        )
    _assert_persisted_content_safe(record.to_dict())
    semantic = _semantic_material(record)
    expected_content_hash = _stable_hash(semantic)
    if record.content_hash != expected_content_hash:
        raise ProviderFlowAuditVerificationError("content hash mismatch")
    if record.record_id != "provider-g-flow-audit-" + expected_content_hash[:24]:
        raise ProviderFlowAuditVerificationError("record id mismatch")
    full_material = {
        **semantic,
        "record_id": record.record_id,
        "timestamp_utc": record.timestamp_utc,
        "content_hash": record.content_hash,
        "previous_record_hash": record.previous_record_hash,
    }
    if record.full_record_hash != _stable_hash(full_material):
        raise ProviderFlowAuditVerificationError("full record hash mismatch")


def _record_from_mapping(value: Any) -> ProviderFlowAuditRecord:
    if not isinstance(value, Mapping) or set(value) != _required_record_fields():
        raise ProviderFlowAuditVerificationError("record required fields mismatch")
    try:
        return ProviderFlowAuditRecord(
            label=value["label"],
            schema_version=value["schema_version"],
            record_id=value["record_id"],
            flow_id=value["flow_id"],
            timestamp_utc=value["timestamp_utc"],
            storage_scope=value["storage_scope"],
            audit_role=value["audit_role"],
            content_hash=value["content_hash"],
            previous_record_hash=value["previous_record_hash"],
            full_record_hash=value["full_record_hash"],
            context_packet_hash=value["context_packet_hash"],
            context_packet_ref=value["context_packet_ref"],
            dissonance_flags=tuple(value["dissonance_flags"]),
            provider_request_summary=dict(value["provider_request_summary"]),
            provider_id=value["provider_id"],
            provider_profile_id=value["provider_profile_id"],
            registry_decision_summary=dict(value["registry_decision_summary"]),
            live_adapter_status=dict(value["live_adapter_status"]),
            provider_output_trust_label=value["provider_output_trust_label"],
            provider_output_hash=value["provider_output_hash"],
            provider_snippet=value["provider_snippet"],
            critic_label=value["critic_label"],
            critic_finding_count=value["critic_finding_count"],
            critic_finding_categories=tuple(value["critic_finding_categories"]),
            review_projection_label=value["review_projection_label"],
            review_projection_status=value["review_projection_status"],
            final_status=value["final_status"],
            safety_boundaries=tuple(
                ProviderFlowAuditBoundary(item) for item in value["safety_boundaries"]
            ),
            source_object_ids=dict(value["source_object_ids"]),
            source_object_hashes=dict(value["source_object_hashes"]),
            live_call_attempted=value["live_call_attempted"],
            live_call_blocked=value["live_call_blocked"],
            network_used=value["network_used"],
            approved=value["approved"],
            automatic_approval=value["automatic_approval"],
            gate_eligible=value["gate_eligible"],
            execution_occurred=value["execution_occurred"],
            artifact_write_occurred=value["artifact_write_occurred"],
            requires_human_review=value["requires_human_review"],
            blocking=value["blocking"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ProviderFlowAuditVerificationError("invalid provider-flow audit record") from error


def _semantic_material(record: ProviderFlowAuditRecord) -> dict[str, Any]:
    values = record.to_dict()
    for field in (
        "record_id",
        "timestamp_utc",
        "content_hash",
        "previous_record_hash",
        "full_record_hash",
    ):
        values.pop(field)
    return values


def _required_record_fields() -> set[str]:
    return {
        "label", "schema_version", "record_id", "flow_id", "timestamp_utc",
        "storage_scope", "audit_role", "content_hash", "previous_record_hash",
        "full_record_hash", "context_packet_hash", "context_packet_ref",
        "dissonance_flags", "provider_request_summary", "provider_id",
        "provider_profile_id", "registry_decision_summary", "live_adapter_status",
        "provider_output_trust_label", "provider_output_hash", "provider_snippet",
        "critic_label", "critic_finding_count", "critic_finding_categories",
        "review_projection_label", "review_projection_status", "final_status",
        "safety_boundaries", "source_object_ids", "source_object_hashes",
        "live_call_attempted", "live_call_blocked", "network_used", "approved",
        "automatic_approval", "gate_eligible", "execution_occurred",
        "artifact_write_occurred", "requires_human_review", "blocking",
    }


def _required_boundaries() -> tuple[ProviderFlowAuditBoundary, ...]:
    return (
        ProviderFlowAuditBoundary.NO_LIVE_PROVIDER_CALL,
        ProviderFlowAuditBoundary.NO_NETWORK,
        ProviderFlowAuditBoundary.NO_EXECUTION,
        ProviderFlowAuditBoundary.NO_ARTIFACT_WRITE,
        ProviderFlowAuditBoundary.NO_AUTO_APPROVAL,
        ProviderFlowAuditBoundary.HUMAN_REVIEW_REQUIRED,
    )


def _resolve_scoped_path(
    audit_path: str | Path,
    allowed_root: str | Path,
    *,
    create_root: bool = True,
) -> tuple[Path, Path]:
    raw_root = _absolute_path(allowed_root, "allowed_root")
    raw_path = _absolute_path(audit_path, "audit_path")
    if ".." in raw_root.parts or ".." in raw_path.parts:
        raise ProviderFlowAuditPathError("path traversal is blocked")
    if ".aoia" in raw_root.parts or ".aoia" in raw_path.parts:
        raise ProviderFlowAuditPathError("paths under .aoia are blocked")
    _assert_no_symlink(raw_root, "allowed_root")
    _assert_no_symlink(raw_path, "audit_path")
    root = Path(posixpath.realpath(str(raw_root)))
    path = Path(posixpath.realpath(str(raw_path)))
    repo = Path(posixpath.realpath(str(_REPO_ROOT)))
    if _is_within(path, repo):
        raise ProviderFlowAuditPathError("audit writes inside the repo are blocked")
    if not _is_within(path, root) or path == root:
        raise ProviderFlowAuditPathError("audit path must be inside allowed_root")
    if path.suffix != ".jsonl":
        raise ProviderFlowAuditPathError("audit path must use a .jsonl suffix")
    if create_root:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root, path


def _absolute_path(value: str | Path, name: str) -> Path:
    if isinstance(value, Path):
        result = value
    elif isinstance(value, str):
        result = Path(value)
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not str(result).strip() or not result.is_absolute():
        raise ProviderFlowAuditPathError(f"{name} must be explicit and absolute")
    return result


def _assert_no_symlink(path: Path, label: str) -> None:
    if path.exists() and path.is_symlink():
        raise ProviderFlowAuditPathError(f"{label} symlink is blocked")


def _is_within(path: Path, root: Path) -> bool:
    try:
        return posixpath.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def _append_and_fsync(path: Path, encoded: bytes) -> None:
    flags = posix.O_APPEND | posix.O_CREAT | posix.O_WRONLY
    if hasattr(posix, "O_NOFOLLOW"):
        flags |= posix.O_NOFOLLOW
    descriptor = posix.open(str(path), flags, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            written = posix.write(descriptor, encoded[offset:])
            if written <= 0:
                raise OSError("provider-flow audit append made no progress")
            offset += written
        posix.fsync(descriptor)
    finally:
        posix.close(descriptor)


def _empty_verification(path: Path) -> ProviderFlowAuditVerificationResult:
    return ProviderFlowAuditVerificationResult(
        valid=True,
        audit_path=str(path),
        record_count=0,
        record_ids=(),
        content_hashes=(),
        last_full_record_hash="",
        final_status=None,
        records=(),
    )


def _sanitize_mapping(
    value: Mapping[str, Any],
    secrets: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("audit mapping is required")
    result: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        _assert_key_allowed(key_text)
        result[key_text] = _sanitize_value(item, key_text, secrets)
    return result


def _sanitize_value(value: Any, key: str, secrets: tuple[str, ...]) -> Any:
    normalized_key = key.lower().replace("-", "_").strip()
    if normalized_key in _SECRET_FIELD_NAMES:
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_audit_text(value, known_secrets=secrets)
    if isinstance(value, Mapping):
        return _sanitize_mapping(value, secrets)
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item, "", secrets) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError("audit values must be deterministic JSON values")


def _assert_persisted_content_safe(value: Any, key: str = "") -> None:
    if isinstance(value, Mapping):
        for child_key, child_value in value.items():
            key_text = str(child_key)
            _assert_key_allowed(key_text)
            normalized = key_text.lower().replace("-", "_").strip()
            if normalized in _SECRET_FIELD_NAMES and child_value != "[REDACTED]":
                raise ProviderFlowAuditVerificationError(
                    f"secret-like field {key_text} is not redacted"
                )
            _assert_persisted_content_safe(child_value, key_text)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_persisted_content_safe(item, key)
        return
    if isinstance(value, str) and value != redact_audit_text(value):
        raise ProviderFlowAuditVerificationError(
            f"persisted audit text in {key or 'record'} is not sanitized"
        )
    if value is not None and not isinstance(value, (str, bool, int, float)):
        raise ProviderFlowAuditVerificationError(
            "persisted audit content is not deterministic JSON"
        )


def _assert_key_allowed(key: str) -> None:
    normalized = key.lower().replace("-", "_")
    if any(fragment in normalized for fragment in _FORBIDDEN_PERSISTED_KEY_FRAGMENTS):
        raise ProviderFlowAuditError(
            f"forbidden raw or forensic audit field: {key}"
        )


def _sanitize_string_mapping(
    value: Mapping[str, Any],
    secrets: tuple[str, ...],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, str) or not item:
            raise ProviderFlowAuditError(f"source field {key} must be a string")
        result[key] = redact_audit_text(item, known_secrets=secrets)
    return result


def _provider_snippet(
    value: str | None,
    max_length: int,
    secrets: tuple[str, ...],
) -> str | None:
    if value is None:
        return None
    if not isinstance(max_length, int) or isinstance(max_length, bool):
        raise TypeError("snippet_max_length must be an integer")
    if max_length < 1 or max_length > DEFAULT_PROVIDER_SNIPPET_MAX_LENGTH:
        raise ProviderFlowAuditError("snippet_max_length must be between 1 and 512")
    return redact_audit_text(value, known_secrets=secrets)[:max_length]


def _dissonance_flags(
    values: Iterable[str],
    secrets: tuple[str, ...],
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("dissonance_flags must be an iterable of strings")
    result = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("dissonance_flags must contain strings")
        result.append(redact_audit_text(value, known_secrets=secrets)[:256])
    return tuple(result)


def _optional_redacted_text(
    value: str | None,
    secrets: tuple[str, ...],
    max_length: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional audit text must be a string or None")
    result = redact_audit_text(value, known_secrets=secrets).strip()
    return result[:max_length] or None


def _optional_chain_hash(value: str) -> str:
    if value == "":
        return ""
    return _optional_full_hash(value, "previous_record_hash") or ""


def _optional_full_hash(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _HEX_HASH.fullmatch(value):
        raise ProviderFlowAuditError(f"{name} must be a lowercase SHA-256 hash")
    return value


def _normalized_known_secrets(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("known_secrets must be an iterable of strings")
    result = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError("known_secrets must contain strings")
        if value:
            result.append(value)
    return tuple(result)


def _redact_high_entropy_candidate(match: re.Match[str]) -> str:
    value = match.group(0)
    if re.fullmatch(r"[0-9a-fA-F]+", value):
        return value
    if _is_human_readable_identity_candidate(value):
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
    if classes < 3 or _shannon_entropy(value) < 4.0:
        return value
    return "[REDACTED]"


def _is_human_readable_identity_candidate(value: str) -> bool:
    """Recognize structured identity text without consulting machine state."""
    if not value or "+" in value or "=" in value:
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
    if (
        allow_simple
        and len(components) == 2
        and _READABLE_IDENTITY_WORD.fullmatch(components[0])
        and _READABLE_IDENTITY_LABEL_SUFFIX.fullmatch(components[1])
    ):
        return True
    if not allow_simple and len(components) < 3:
        return False
    readable_words = sum(
        bool(_READABLE_IDENTITY_WORD.fullmatch(component))
        for component in components
    )
    return readable_words >= 2


def _shannon_entropy(value: str) -> float:
    counts = Counter(value)
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
