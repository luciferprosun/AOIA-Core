from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class SandboxArtifactType(str, Enum):
    TEXT_REPORT = "TEXT_REPORT"
    JSON_SUMMARY = "JSON_SUMMARY"


class SandboxArtifactState(str, Enum):
    REQUESTED = "REQUESTED"
    WRITTEN = "WRITTEN"
    BLOCKED = "BLOCKED"
    INVALID = "INVALID"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _coerce_bool(name: str, value: bool) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value


def _coerce_int(name: str, value: int) -> int:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    return value


@dataclass(frozen=True)
class SandboxArtifactRequest:
    artifact_request_id: str
    created_at: str
    run_id: str
    sandbox_request_id: str
    sandbox_result_id: str
    artifact_type: SandboxArtifactType
    relative_output_path: str
    content_text: str
    content_hash: str
    requested_by: str
    human_approved: bool
    dry_run_trace_id: str
    audit_event_id: str
    notes: str

    def __post_init__(self) -> None:
        artifact_type = SandboxArtifactType(self.artifact_type)
        content_text = _coerce_text("content_text", self.content_text)
        object.__setattr__(self, "artifact_request_id", _coerce_text("artifact_request_id", self.artifact_request_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "run_id", _coerce_text("run_id", self.run_id))
        object.__setattr__(self, "sandbox_request_id", _coerce_text("sandbox_request_id", self.sandbox_request_id))
        object.__setattr__(self, "sandbox_result_id", _coerce_text("sandbox_result_id", self.sandbox_result_id))
        object.__setattr__(self, "artifact_type", artifact_type)
        object.__setattr__(self, "relative_output_path", _coerce_text("relative_output_path", self.relative_output_path))
        object.__setattr__(self, "content_text", content_text)
        object.__setattr__(self, "content_hash", _hash_text(content_text))
        object.__setattr__(self, "requested_by", _coerce_text("requested_by", self.requested_by))
        object.__setattr__(self, "human_approved", _coerce_bool("human_approved", self.human_approved))
        object.__setattr__(self, "dry_run_trace_id", _coerce_text("dry_run_trace_id", self.dry_run_trace_id))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_request_id": self.artifact_request_id,
            "created_at": self.created_at,
            "run_id": self.run_id,
            "sandbox_request_id": self.sandbox_request_id,
            "sandbox_result_id": self.sandbox_result_id,
            "artifact_type": self.artifact_type.value,
            "relative_output_path": self.relative_output_path,
            "content_text": self.content_text,
            "content_hash": self.content_hash,
            "requested_by": self.requested_by,
            "human_approved": self.human_approved,
            "dry_run_trace_id": self.dry_run_trace_id,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SandboxArtifactResult:
    artifact_result_id: str
    created_at: str
    artifact_request_id: str
    state: SandboxArtifactState
    workspace_root: str
    relative_output_path: str
    resolved_output_path: str
    content_hash: str
    bytes_written: int
    write_attempted: bool
    write_completed: bool
    blocked_reason: str
    audit_event_id: str
    notes: str

    def __post_init__(self) -> None:
        state = SandboxArtifactState(self.state)
        object.__setattr__(self, "artifact_result_id", _coerce_text("artifact_result_id", self.artifact_result_id))
        object.__setattr__(self, "created_at", _coerce_text("created_at", self.created_at))
        object.__setattr__(self, "artifact_request_id", _coerce_text("artifact_request_id", self.artifact_request_id))
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "workspace_root", _coerce_text("workspace_root", self.workspace_root))
        object.__setattr__(self, "relative_output_path", _coerce_text("relative_output_path", self.relative_output_path))
        object.__setattr__(self, "resolved_output_path", _coerce_text("resolved_output_path", self.resolved_output_path))
        object.__setattr__(self, "content_hash", _coerce_text("content_hash", self.content_hash))
        object.__setattr__(self, "bytes_written", _coerce_int("bytes_written", self.bytes_written))
        object.__setattr__(self, "write_attempted", _coerce_bool("write_attempted", self.write_attempted))
        object.__setattr__(self, "write_completed", _coerce_bool("write_completed", self.write_completed))
        object.__setattr__(self, "blocked_reason", _coerce_text("blocked_reason", self.blocked_reason))
        object.__setattr__(self, "audit_event_id", _coerce_text("audit_event_id", self.audit_event_id))
        object.__setattr__(self, "notes", _coerce_text("notes", self.notes))
        if state is SandboxArtifactState.WRITTEN:
            if self.write_attempted is not True or self.write_completed is not True:
                raise ValueError("written artifacts must have write_attempted and write_completed true")
        else:
            if self.write_completed is not False:
                raise ValueError("non-written artifacts cannot have write_completed true")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_result_id": self.artifact_result_id,
            "created_at": self.created_at,
            "artifact_request_id": self.artifact_request_id,
            "state": self.state.value,
            "workspace_root": self.workspace_root,
            "relative_output_path": self.relative_output_path,
            "resolved_output_path": self.resolved_output_path,
            "content_hash": self.content_hash,
            "bytes_written": self.bytes_written,
            "write_attempted": self.write_attempted,
            "write_completed": self.write_completed,
            "blocked_reason": self.blocked_reason,
            "audit_event_id": self.audit_event_id,
            "notes": self.notes,
        }


def create_sandbox_artifact_request(
    *,
    run_id: str,
    sandbox_request_id: str,
    sandbox_result_id: str,
    artifact_type: SandboxArtifactType | str,
    relative_output_path: str,
    content_text: str,
    requested_by: str,
    human_approved: bool,
    dry_run_trace_id: str,
    audit_event_id: str = "",
    notes: str = "",
    created_at: str | None = None,
    artifact_request_id: str | None = None,
) -> SandboxArtifactRequest:
    timestamp = created_at or _utc_now_iso()
    artifact_type_value = SandboxArtifactType(artifact_type)
    content = _coerce_text("content_text", content_text)
    record_id = artifact_request_id or "sandbox-artifact-request-" + _hash_text(
        "\n".join([run_id, sandbox_request_id, sandbox_result_id, relative_output_path, content, timestamp])
    )[:24]
    event_id = audit_event_id or "sandbox-artifact-audit-" + _hash_text(record_id)[:24]
    return SandboxArtifactRequest(
        artifact_request_id=record_id,
        created_at=timestamp,
        run_id=run_id,
        sandbox_request_id=sandbox_request_id,
        sandbox_result_id=sandbox_result_id,
        artifact_type=artifact_type_value,
        relative_output_path=relative_output_path,
        content_text=content,
        content_hash=_hash_text(content),
        requested_by=requested_by,
        human_approved=human_approved,
        dry_run_trace_id=dry_run_trace_id,
        audit_event_id=event_id,
        notes=notes,
    )


def create_blocked_sandbox_artifact_result(
    request: SandboxArtifactRequest,
    *,
    workspace_root: str,
    resolved_output_path: str = "",
    blocked_reason: str,
    notes: str = "",
) -> SandboxArtifactResult:
    if not isinstance(request, SandboxArtifactRequest):
        raise TypeError("request must be a SandboxArtifactRequest")
    timestamp = _utc_now_iso()
    record_id = "sandbox-artifact-result-" + _hash_text(
        "\n".join([request.artifact_request_id, "blocked", blocked_reason, timestamp])
    )[:24]
    return SandboxArtifactResult(
        artifact_result_id=record_id,
        created_at=timestamp,
        artifact_request_id=request.artifact_request_id,
        state=SandboxArtifactState.BLOCKED,
        workspace_root=workspace_root,
        relative_output_path=request.relative_output_path,
        resolved_output_path=resolved_output_path,
        content_hash=request.content_hash,
        bytes_written=0,
        write_attempted=False,
        write_completed=False,
        blocked_reason=blocked_reason,
        audit_event_id=request.audit_event_id,
        notes=notes,
    )


def create_written_sandbox_artifact_result(
    request: SandboxArtifactRequest,
    *,
    workspace_root: str,
    resolved_output_path: str,
    bytes_written: int,
    notes: str = "",
) -> SandboxArtifactResult:
    if not isinstance(request, SandboxArtifactRequest):
        raise TypeError("request must be a SandboxArtifactRequest")
    timestamp = _utc_now_iso()
    record_id = "sandbox-artifact-result-" + _hash_text(
        "\n".join([request.artifact_request_id, "written", resolved_output_path, request.content_hash, timestamp])
    )[:24]
    return SandboxArtifactResult(
        artifact_result_id=record_id,
        created_at=timestamp,
        artifact_request_id=request.artifact_request_id,
        state=SandboxArtifactState.WRITTEN,
        workspace_root=workspace_root,
        relative_output_path=request.relative_output_path,
        resolved_output_path=resolved_output_path,
        content_hash=request.content_hash,
        bytes_written=bytes_written,
        write_attempted=True,
        write_completed=True,
        blocked_reason="",
        audit_event_id=request.audit_event_id,
        notes=notes,
    )


def sandbox_artifact_request_to_dict(request: SandboxArtifactRequest) -> dict[str, Any]:
    if not isinstance(request, SandboxArtifactRequest):
        raise TypeError("request must be a SandboxArtifactRequest")
    return request.to_dict()


def sandbox_artifact_result_to_dict(result: SandboxArtifactResult) -> dict[str, Any]:
    if not isinstance(result, SandboxArtifactResult):
        raise TypeError("result must be a SandboxArtifactResult")
    return result.to_dict()
