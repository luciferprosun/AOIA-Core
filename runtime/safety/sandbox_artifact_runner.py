from __future__ import annotations

import posix
from pathlib import Path
from typing import Any

from runtime.safety.sandbox_workspace import SandboxWorkspaceViolationError
from runtime.safety.workspace_guard import validate_workspace_target_path
from runtime.safety.write_kill_switch import check_write_kill_switch_file
from runtime.schemas.sandbox_artifact import (
    SANDBOX_ARTIFACT_CONTRACT_VERSION,
    SandboxArtifactRequest,
    SandboxArtifactResult,
    create_blocked_sandbox_artifact_result,
    create_written_sandbox_artifact_result,
)


MAX_SANDBOX_ARTIFACT_BYTES = 64 * 1024


class SandboxArtifactExecutionBlockedError(RuntimeError):
    pass


class SandboxArtifactWriteBlockedError(RuntimeError):
    pass


_ELIGIBLE_SANDBOX_RESULT_STATES = frozenset({"BLOCKED", "NOT_IMPLEMENTED"})


def write_sandbox_artifact(
    request: SandboxArtifactRequest,
    workspace_root: str,
    allow_overwrite: bool = False,
    write_kill_switch_path: str | None = None,
    write_kill_switch_directory: str | None = None,
    *,
    approval_evidence: Any | None = None,
) -> SandboxArtifactResult:
    if not isinstance(request, SandboxArtifactRequest):
        raise TypeError("request must be a SandboxArtifactRequest")
    contract_violation = _artifact_contract_violation_reason(request)
    if contract_violation:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason=contract_violation,
            notes="2A-2 artifact contract guard blocked artifact write",
        )
    if write_kill_switch_path is not None:
        kill_switch = check_write_kill_switch_file(
            write_kill_switch_path,
            allowed_switch_directory=write_kill_switch_directory,
        )
        if not kill_switch.writes_allowed:
            return create_blocked_sandbox_artifact_result(
                request,
                workspace_root=workspace_root,
                blocked_reason=kill_switch.reason,
                notes="Step 15 global write kill-switch blocked artifact write",
            )
    content_bytes = request.content_text.encode("utf-8")
    if len(content_bytes) > MAX_SANDBOX_ARTIFACT_BYTES:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason="sandbox artifact content exceeds M8-A size limit",
            notes="M8-A artifact write blocked before filesystem access",
        )
    workspace_guard = validate_workspace_target_path(workspace_root, request.relative_output_path)
    if not workspace_guard.allowed:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=workspace_guard.resolved_absolute_target_path or "",
            blocked_reason=workspace_guard.reason,
            notes="M8-A workspace guard blocked artifact write",
        )

    resolved_output_path = workspace_guard.resolved_absolute_target_path or ""
    output_path = Path(resolved_output_path)
    if output_path.is_symlink():
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact output path is a symlink",
            notes="M8-A artifact write blocked before opening output path",
        )
    if output_path.exists() and not allow_overwrite:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact overwrite blocked by default",
            notes="M8-A artifact write blocked before opening output path",
        )
    if output_path.exists() and output_path.is_dir():
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact output path is a directory",
            notes="M8-A artifact write blocked before opening output path",
        )

    approval_violation = _approval_evidence_violation_reason(request, approval_evidence)
    if approval_violation:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason=approval_violation,
            notes="Step 12C canonical human gate evidence blocked artifact write",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        workspace_guard = validate_workspace_target_path(workspace_root, request.relative_output_path)
        if not workspace_guard.allowed:
            raise SandboxWorkspaceViolationError(workspace_guard.reason)
        resolved_output_path = workspace_guard.resolved_absolute_target_path or ""
        output_path = Path(resolved_output_path)
        if output_path.is_symlink():
            return create_blocked_sandbox_artifact_result(
                request,
                workspace_root=workspace_root,
                resolved_output_path=resolved_output_path,
                blocked_reason="sandbox artifact output path is a symlink",
                notes="M8-A artifact write blocked before opening output path",
            )
        if output_path.exists() and not allow_overwrite:
            return create_blocked_sandbox_artifact_result(
                request,
                workspace_root=workspace_root,
                resolved_output_path=resolved_output_path,
                blocked_reason="sandbox artifact overwrite blocked by default",
                notes="M8-A artifact write blocked before opening output path",
            )
        _write_text_artifact_atomically(
            output_path,
            content_bytes,
            allow_overwrite,
            workspace_root,
            request.relative_output_path,
        )
    except FileExistsError as exc:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact overwrite blocked by default",
            notes="M8-A artifact write blocked before replacing output path",
        )
    except SandboxWorkspaceViolationError as exc:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason=str(exc),
            notes="M8-A workspace guard blocked artifact write",
        )
    except OSError as exc:
        raise SandboxArtifactWriteBlockedError("sandbox artifact write failed") from exc

    return create_written_sandbox_artifact_result(
        request,
        workspace_root=workspace_root,
        resolved_output_path=resolved_output_path,
        bytes_written=len(content_bytes),
        notes="M8-A wrote one workspace-bound text artifact",
    )


def _write_text_artifact_atomically(
    output_path: Path,
    content_bytes: bytes,
    allow_overwrite: bool,
    workspace_root: str,
    relative_output_path: str,
) -> None:
    output_path = _rechecked_output_path(output_path, workspace_root, relative_output_path)
    temp_path = _temporary_artifact_path(output_path)
    flags = posix.O_CREAT | posix.O_EXCL | posix.O_WRONLY
    if hasattr(posix, "O_NOFOLLOW"):
        flags |= posix.O_NOFOLLOW

    fd = -1
    try:
        fd = posix.open(str(temp_path), flags, 0o600)
        offset = 0
        while offset < len(content_bytes):
            written = posix.write(fd, content_bytes[offset:])
            if written <= 0:
                raise OSError("sandbox artifact write made no progress")
            offset += written
        posix.fsync(fd)
    except Exception:
        if fd >= 0:
            posix.close(fd)
            fd = -1
        _remove_temp_artifact(temp_path)
        raise
    finally:
        if fd >= 0:
            posix.close(fd)

    try:
        output_path = _rechecked_output_path(output_path, workspace_root, relative_output_path)
        if allow_overwrite:
            if output_path.is_symlink():
                raise SandboxWorkspaceViolationError("sandbox artifact output path is a symlink")
            posix.replace(str(temp_path), str(output_path))
        else:
            posix.link(str(temp_path), str(output_path))
            posix.unlink(str(temp_path))
        _fsync_parent_directory(output_path)
    except Exception:
        _remove_temp_artifact(temp_path)
        raise


def _rechecked_output_path(
    expected_output_path: Path,
    workspace_root: str,
    relative_output_path: str,
) -> Path:
    workspace_guard = validate_workspace_target_path(workspace_root, relative_output_path)
    if not workspace_guard.allowed:
        raise SandboxWorkspaceViolationError(workspace_guard.reason)
    resolved_output_path = Path(workspace_guard.resolved_absolute_target_path or "")
    if resolved_output_path != expected_output_path:
        raise SandboxWorkspaceViolationError("workspace guard target path changed before artifact write")
    if resolved_output_path.parent.is_symlink():
        raise SandboxWorkspaceViolationError("artifact parent path contains a symlink")
    if resolved_output_path.is_symlink():
        raise SandboxWorkspaceViolationError("sandbox artifact output path is a symlink")
    return resolved_output_path


def _temporary_artifact_path(output_path: Path) -> Path:
    return output_path.with_name(f".{output_path.name}.tmp")


def _remove_temp_artifact(temp_path: Path) -> None:
    try:
        posix.unlink(str(temp_path))
    except FileNotFoundError:
        return


def _fsync_parent_directory(output_path: Path) -> None:
    fd = posix.open(str(output_path.parent), posix.O_RDONLY)
    try:
        posix.fsync(fd)
    finally:
        posix.close(fd)


def _artifact_contract_violation_reason(request: SandboxArtifactRequest) -> str:
    if request.artifact_contract_version != SANDBOX_ARTIFACT_CONTRACT_VERSION:
        return "artifact contract version is invalid"
    if request.artifact_write_allowed is not True:
        return "artifact contract does not allow workspace write"
    if not request.human_approved:
        return "sandbox artifact request requires explicit human approval"
    if not request.run_id or not request.dry_run_trace_id:
        return "artifact contract requires dry-run identifiers"
    if not request.approval_decision_id:
        return "artifact contract requires approval decision id"
    if not request.sandbox_request_id or not request.sandbox_result_id:
        return "artifact contract requires sandbox request and result ids"
    if not request.sandbox_policy_decision_id:
        return "artifact contract requires sandbox policy decision id"
    if request.sandbox_result_state not in _ELIGIBLE_SANDBOX_RESULT_STATES:
        return "sandbox result state is not eligible for artifact write"
    if request.contract_payload_hash != request.content_hash:
        return "artifact content hash must match contract payload hash"
    if not request.audit_event_id or not request.contract_audit_event_id:
        return "artifact contract requires audit event ids"
    if request.audit_event_id != request.contract_audit_event_id:
        return "artifact audit event must match contract audit event"
    return ""


def _approval_evidence_violation_reason(
    request: SandboxArtifactRequest,
    approval_evidence: Any,
) -> str:
    from runtime.human_decision_gate_integration import (
        validate_canonical_human_gate_authority,
    )

    return validate_canonical_human_gate_authority(
        approval_evidence,
        expected_artifact_hash=request.content_hash,
        expected_approval_decision_id=request.approval_decision_id,
        expected_audit_event_id=request.audit_event_id,
        expected_contract_audit_event_id=request.contract_audit_event_id,
    )
