from __future__ import annotations

import hashlib
import json
import posix
import posixpath
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

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


PROVIDER_FLOW_AUDIT_RECORD = "PROVIDER_FLOW_AUDIT_RECORD"
NO_LIVE_PROVIDER_CALL = "NO_LIVE_PROVIDER_CALL"
NO_NETWORK = "NO_NETWORK"
MAX_PROVIDER_FLOW_AUDIT_BYTES = 64 * 1024

_REPO_ROOT = Path(__file__).resolve().parents[1]


class ProviderFlowAuditBlocked(ValueError):
    """Raised when a provider-flow audit input violates the inert boundary."""


class ProviderFlowAuditPathBlocked(ProviderFlowAuditBlocked):
    """Raised when a durable audit path is outside its explicit safe root."""


class ProviderFlowAuditStatus(str, Enum):
    REVIEW_REQUIRED = REVIEW_REQUIRED


class ProviderFlowAuditBoundary(str, Enum):
    NO_LIVE_PROVIDER_CALL = NO_LIVE_PROVIDER_CALL
    NO_NETWORK = NO_NETWORK
    NO_EXECUTION = NO_EXECUTION
    NO_ARTIFACT_WRITE = NO_ARTIFACT_WRITE
    NO_AUTO_APPROVAL = NO_AUTO_APPROVAL
    HUMAN_REVIEW_REQUIRED = HUMAN_REVIEW_REQUIRED


@dataclass(frozen=True)
class ProviderFlowAuditRecord:
    audit_label: str
    record_id: str
    content_hash: str
    recorded_at: str | None
    provider_request_summary: Mapping[str, Any]
    provider_id: str
    provider_profile_id: str
    registry_decision_summary: Mapping[str, Any]
    live_adapter_status: Mapping[str, Any]
    provider_output_trust_label: str
    critic_label: str
    critic_finding_count: int
    critic_finding_categories: tuple[str, ...]
    review_projection_label: str
    review_projection_status: str
    final_status: ProviderFlowAuditStatus
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
            "audit_label": self.audit_label,
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "recorded_at": self.recorded_at,
            "provider_request_summary": dict(self.provider_request_summary),
            "provider_id": self.provider_id,
            "provider_profile_id": self.provider_profile_id,
            "registry_decision_summary": dict(self.registry_decision_summary),
            "live_adapter_status": dict(self.live_adapter_status),
            "provider_output_trust_label": self.provider_output_trust_label,
            "critic_label": self.critic_label,
            "critic_finding_count": self.critic_finding_count,
            "critic_finding_categories": list(self.critic_finding_categories),
            "review_projection_label": self.review_projection_label,
            "review_projection_status": self.review_projection_status,
            "final_status": self.final_status.value,
            "safety_boundaries": [
                boundary.value for boundary in self.safety_boundaries
            ],
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
    bytes_written: int
    append_only: bool
    fsync_completed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_path": self.audit_path,
            "record_id": self.record_id,
            "content_hash": self.content_hash,
            "bytes_written": self.bytes_written,
            "append_only": self.append_only,
            "fsync_completed": self.fsync_completed,
        }


def build_provider_flow_audit_record(
    projection: ProviderReviewProjection,
    *,
    recorded_at: str | None = None,
) -> ProviderFlowAuditRecord:
    _validate_projection(projection)

    request = projection.provider_request_summary
    live = projection.live_adapter_section.details
    critic = projection.critic_section.details
    request_summary = {
        "request_id": request.get("request_id"),
        "request_hash": request.get("request_hash"),
        "provider_id": request.get("provider_id"),
        "purpose": request.get("purpose"),
        "caller_label": request.get("caller_label"),
        "request_metadata_present": bool(request.get("request_metadata")),
    }
    live_status = {
        "status": projection.live_adapter_section.status,
        "adapter_label": live.get("adapter_label"),
        "attempted": False,
        "blocked": True,
        "reason": live.get("blocked_reason"),
        "network_allowed": False,
    }
    categories = tuple(finding.category for finding in projection.critic_findings)
    boundaries = (
        ProviderFlowAuditBoundary.NO_LIVE_PROVIDER_CALL,
        ProviderFlowAuditBoundary.NO_NETWORK,
        ProviderFlowAuditBoundary.NO_EXECUTION,
        ProviderFlowAuditBoundary.NO_ARTIFACT_WRITE,
        ProviderFlowAuditBoundary.NO_AUTO_APPROVAL,
        ProviderFlowAuditBoundary.HUMAN_REVIEW_REQUIRED,
    )
    source_ids = {
        "provider_review_projection_id": projection.projection_id,
        "human_review_projection_id": projection.human_review_projection_id,
        "review_packet_id": projection.review_packet_id,
        "provider_output_id": str(
            projection.provider_output_summary.get("output_id")
        ),
        "critic_review_id": str(critic.get("critic_review_id")),
        "live_adapter_decision_id": str(live.get("decision_id")),
    }
    source_hashes = {
        "provider_review_projection_hash": projection.projection_hash,
        "human_review_projection_hash": projection.human_review_projection_hash,
        "review_packet_hash": projection.review_packet_hash,
        "provider_output_hash": str(
            projection.provider_output_summary.get("output_hash")
        ),
        "critic_review_hash": str(critic.get("critic_review_hash")),
        "live_adapter_decision_hash": str(live.get("decision_hash")),
    }
    material = {
        "audit_label": PROVIDER_FLOW_AUDIT_RECORD,
        "provider_request_summary": request_summary,
        "provider_id": projection.provider_id,
        "provider_profile_id": projection.provider_profile_id,
        "registry_decision_summary": dict(projection.registry_decision_summary),
        "live_adapter_status": live_status,
        "provider_output_trust_label": UNTRUSTED_PROVIDER_OUTPUT,
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
    content_hash = _stable_hash(material)
    return ProviderFlowAuditRecord(
        audit_label=PROVIDER_FLOW_AUDIT_RECORD,
        record_id="provider-g-flow-audit-" + content_hash[:24],
        content_hash=content_hash,
        recorded_at=_optional_text(recorded_at),
        provider_request_summary=request_summary,
        provider_id=projection.provider_id,
        provider_profile_id=projection.provider_profile_id,
        registry_decision_summary=dict(projection.registry_decision_summary),
        live_adapter_status=live_status,
        provider_output_trust_label=UNTRUSTED_PROVIDER_OUTPUT,
        critic_label=INERT_PROVIDER_CRITIC_REVIEW,
        critic_finding_count=len(categories),
        critic_finding_categories=categories,
        review_projection_label=PROVIDER_REVIEW_PROJECTION,
        review_projection_status=REVIEW_REQUIRED,
        final_status=ProviderFlowAuditStatus.REVIEW_REQUIRED,
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
    if not isinstance(record, ProviderFlowAuditRecord):
        raise TypeError("record must be a ProviderFlowAuditRecord")
    _assert_record_valid(record)
    root, path = _resolve_append_path(audit_path, allowed_root)
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.is_symlink() or path.is_symlink():
        raise ProviderFlowAuditPathBlocked("audit symlinks are blocked")
    if posixpath.commonpath([str(root), posixpath.realpath(str(parent))]) != str(root):
        raise ProviderFlowAuditPathBlocked("audit parent escapes allowed_root")

    line = json.dumps(
        record.to_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"
    encoded = line.encode("utf-8")
    if len(encoded) > MAX_PROVIDER_FLOW_AUDIT_BYTES:
        raise ProviderFlowAuditBlocked("serialized provider-flow audit is too large")
    _assert_existing_log_is_jsonl(path)
    _append_and_fsync(path, encoded)
    return ProviderFlowAuditAppendResult(
        audit_path=str(path),
        record_id=record.record_id,
        content_hash=record.content_hash,
        bytes_written=len(encoded),
        append_only=True,
        fsync_completed=True,
    )


def _validate_projection(projection: ProviderReviewProjection) -> None:
    if not isinstance(projection, ProviderReviewProjection):
        raise ProviderFlowAuditBlocked(
            "a Provider-F review projection is required"
        )
    live = projection.live_adapter_section
    critic = projection.critic_section
    output = projection.provider_output_summary
    registry = projection.registry_decision_summary
    required_boundaries = (
        NO_EXECUTION,
        NO_ARTIFACT_WRITE,
        NO_AUTO_APPROVAL,
        NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE,
    )
    if (
        projection.projection_label != PROVIDER_REVIEW_PROJECTION
        or projection.status != REVIEW_REQUIRED
        or projection.provider_output_trust_label
        != UNTRUSTED_PROVIDER_OUTPUT
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
        or tuple(projection.safety_boundary_summary) != required_boundaries
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
        raise ProviderFlowAuditBlocked(
            "provider review projection violates the inert audit boundary"
        )
    if not live.details.get("blocked_reason"):
        raise ProviderFlowAuditBlocked("live adapter blocked reason is required")
    if not projection.critic_findings:
        raise ProviderFlowAuditBlocked("attached critic findings are required")


def _assert_record_valid(record: ProviderFlowAuditRecord) -> None:
    _validate_record_boundary(record)
    expected = build_provider_flow_audit_record_from_dict(record.to_dict())
    if expected != record:
        raise ProviderFlowAuditBlocked("provider-flow audit record hash mismatch")


def _validate_record_boundary(record: ProviderFlowAuditRecord) -> None:
    expected_boundaries = (
        ProviderFlowAuditBoundary.NO_LIVE_PROVIDER_CALL,
        ProviderFlowAuditBoundary.NO_NETWORK,
        ProviderFlowAuditBoundary.NO_EXECUTION,
        ProviderFlowAuditBoundary.NO_ARTIFACT_WRITE,
        ProviderFlowAuditBoundary.NO_AUTO_APPROVAL,
        ProviderFlowAuditBoundary.HUMAN_REVIEW_REQUIRED,
    )
    live = record.live_adapter_status
    if (
        record.audit_label != PROVIDER_FLOW_AUDIT_RECORD
        or record.provider_output_trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or record.critic_label != INERT_PROVIDER_CRITIC_REVIEW
        or record.review_projection_label != PROVIDER_REVIEW_PROJECTION
        or record.review_projection_status != REVIEW_REQUIRED
        or record.final_status is not ProviderFlowAuditStatus.REVIEW_REQUIRED
        or tuple(record.safety_boundaries) != expected_boundaries
        or live.get("status") != LIVE_PROVIDER_ADAPTER_BLOCKED
        or live.get("adapter_label") != DEFAULT_OFF_LIVE_ADAPTER
        or live.get("attempted") is not False
        or live.get("blocked") is not True
        or live.get("network_allowed") is not False
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
        raise ProviderFlowAuditBlocked(
            "provider-flow audit record violates the inert boundary"
        )


def build_provider_flow_audit_record_from_dict(
    values: Mapping[str, Any],
) -> ProviderFlowAuditRecord:
    if not isinstance(values, Mapping):
        raise TypeError("values must be a mapping")
    material = dict(values)
    record_id = material.pop("record_id", None)
    content_hash = material.pop("content_hash", None)
    recorded_at = material.pop("recorded_at", None)
    expected_hash = _stable_hash(material)
    if content_hash != expected_hash:
        raise ProviderFlowAuditBlocked("provider-flow audit content hash is invalid")
    if record_id != "provider-g-flow-audit-" + expected_hash[:24]:
        raise ProviderFlowAuditBlocked("provider-flow audit record id is invalid")
    return ProviderFlowAuditRecord(
        audit_label=material["audit_label"],
        record_id=record_id,
        content_hash=content_hash,
        recorded_at=_optional_text(recorded_at),
        provider_request_summary=dict(material["provider_request_summary"]),
        provider_id=material["provider_id"],
        provider_profile_id=material["provider_profile_id"],
        registry_decision_summary=dict(material["registry_decision_summary"]),
        live_adapter_status=dict(material["live_adapter_status"]),
        provider_output_trust_label=material["provider_output_trust_label"],
        critic_label=material["critic_label"],
        critic_finding_count=material["critic_finding_count"],
        critic_finding_categories=tuple(material["critic_finding_categories"]),
        review_projection_label=material["review_projection_label"],
        review_projection_status=material["review_projection_status"],
        final_status=ProviderFlowAuditStatus(material["final_status"]),
        safety_boundaries=tuple(
            ProviderFlowAuditBoundary(value)
            for value in material["safety_boundaries"]
        ),
        source_object_ids=dict(material["source_object_ids"]),
        source_object_hashes=dict(material["source_object_hashes"]),
        live_call_attempted=material["live_call_attempted"],
        live_call_blocked=material["live_call_blocked"],
        network_used=material["network_used"],
        approved=material["approved"],
        automatic_approval=material["automatic_approval"],
        gate_eligible=material["gate_eligible"],
        execution_occurred=material["execution_occurred"],
        artifact_write_occurred=material["artifact_write_occurred"],
        requires_human_review=material["requires_human_review"],
        blocking=material["blocking"],
    )


def _resolve_append_path(
    audit_path: str | Path,
    allowed_root: str | Path,
) -> tuple[Path, Path]:
    raw_root = _absolute_path(allowed_root, "allowed_root")
    raw_path = _absolute_path(audit_path, "audit_path")
    root = Path(posixpath.realpath(str(raw_root)))
    path = Path(posixpath.realpath(str(raw_path)))
    repo = Path(posixpath.realpath(str(_REPO_ROOT)))
    if _is_within(path, repo):
        raise ProviderFlowAuditPathBlocked("audit writes inside the repo are blocked")
    if not _is_within(path, root) or path == root:
        raise ProviderFlowAuditPathBlocked("audit path must be inside allowed_root")
    if path.suffix != ".jsonl":
        raise ProviderFlowAuditPathBlocked("audit path must use a .jsonl suffix")
    if raw_root.exists() and raw_root.is_symlink():
        raise ProviderFlowAuditPathBlocked("allowed_root symlinks are blocked")
    if raw_path.exists() and raw_path.is_symlink():
        raise ProviderFlowAuditPathBlocked("audit path symlinks are blocked")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root, path


def _absolute_path(value: str | Path, name: str) -> Path:
    if isinstance(value, str):
        result = Path(value)
    elif isinstance(value, Path):
        result = value
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not str(result).strip() or not result.is_absolute():
        raise ProviderFlowAuditPathBlocked(f"{name} must be explicit and absolute")
    return result


def _is_within(path: Path, root: Path) -> bool:
    try:
        return posixpath.commonpath([str(path), str(root)]) == str(root)
    except ValueError:
        return False


def _assert_existing_log_is_jsonl(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_file() or path.is_symlink():
        raise ProviderFlowAuditPathBlocked(
            "existing audit path must be a regular non-symlink file"
        )
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                decoded = json.loads(line)
            except json.JSONDecodeError as error:
                raise ProviderFlowAuditBlocked(
                    "existing audit log contains invalid JSONL"
                ) from error
            if decoded.get("audit_label") != PROVIDER_FLOW_AUDIT_RECORD:
                raise ProviderFlowAuditBlocked(
                    "existing audit log contains an unexpected record type"
                )


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


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("recorded_at must be a string or None")
    stripped = value.strip()
    return stripped or None


def _stable_hash(values: Mapping[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
