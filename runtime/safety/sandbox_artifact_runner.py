from __future__ import annotations

import posix
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.safety.sandbox_workspace import SandboxWorkspaceViolationError
from runtime.safety.workspace_guard import WorkspaceGuardResult, validate_workspace_target_path
from runtime.safety.write_kill_switch import resolve_required_write_kill_switch
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

_FileIdentity = tuple[int, int, int]


@dataclass(frozen=True)
class _WorkspaceSnapshot:
    root_path: Path
    root_identity: _FileIdentity
    parent_identities: tuple[tuple[str, _FileIdentity], ...]
    target_identity: _FileIdentity | None
    relative_output_path: str
    output_path: Path


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
    kill_switch = resolve_required_write_kill_switch(
        write_kill_switch_path,
        switch_directory=write_kill_switch_directory,
    )
    if not kill_switch.writes_allowed:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason=kill_switch.reason,
            notes="Step 15 global write kill-switch blocked artifact write",
        )
    contract_violation = _artifact_contract_violation_reason(request)
    if contract_violation:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason=contract_violation,
            notes="2A-2 artifact contract guard blocked artifact write",
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

    initial_snapshot = _snapshot_from_guard(workspace_guard)
    resolved_output_path = str(initial_snapshot.output_path)
    if initial_snapshot.target_identity is not None and not allow_overwrite:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact overwrite blocked by default",
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

    try:
        _write_text_artifact_atomically(
            content_bytes,
            allow_overwrite,
            initial_snapshot,
        )
    except FileExistsError:
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
    except OSError:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact filesystem state changed or write failed closed",
            notes="Step 16 workspace write failed closed without path fallback",
        )

    return create_written_sandbox_artifact_result(
        request,
        workspace_root=workspace_root,
        resolved_output_path=resolved_output_path,
        bytes_written=len(content_bytes),
        notes="M8-A wrote one workspace-bound text artifact",
    )


def _write_text_artifact_atomically(
    content_bytes: bytes,
    allow_overwrite: bool,
    initial_snapshot: _WorkspaceSnapshot,
) -> None:
    _rechecked_snapshot(initial_snapshot, exact_parent_set=True)
    parent_fd = -1
    temp_fd = -1
    temp_identity: _FileIdentity | None = None
    created_directories: list[tuple[Path, _FileIdentity]] = []
    operation_succeeded = False
    parent_parts = initial_snapshot.relative_output_path.split("/")[:-1]
    target_name = initial_snapshot.output_path.name
    temp_name = f".{target_name}.tmp"
    flags = posix.O_CREAT | posix.O_EXCL | posix.O_WRONLY
    if hasattr(posix, "O_NOFOLLOW"):
        flags |= posix.O_NOFOLLOW
    if hasattr(posix, "O_CLOEXEC"):
        flags |= posix.O_CLOEXEC

    try:
        parent_fd = _open_target_parent_directory(
            initial_snapshot,
            parent_parts,
            created_directories,
        )
        operation_snapshot = _rechecked_snapshot(
            initial_snapshot,
            exact_parent_set=False,
        )
        _assert_parent_fd_matches_snapshot(parent_fd, operation_snapshot)
        _assert_target_identity(parent_fd, target_name, initial_snapshot.target_identity)
        _assert_pre_temp_state(
            initial_snapshot,
            operation_snapshot,
            parent_fd,
            target_name,
        )

        temp_fd = posix.open(temp_name, flags, 0o600, dir_fd=parent_fd)
        temp_identity = _identity_from_stat(posix.fstat(temp_fd))
        _assert_operation_state(
            initial_snapshot,
            operation_snapshot,
            parent_fd,
            target_name,
            temp_name,
            temp_identity,
        )

        offset = 0
        while offset < len(content_bytes):
            written = posix.write(temp_fd, content_bytes[offset:])
            if written <= 0:
                raise OSError("sandbox artifact write made no progress")
            offset += written
        posix.fsync(temp_fd)
        _assert_operation_state(
            initial_snapshot,
            operation_snapshot,
            parent_fd,
            target_name,
            temp_name,
            temp_identity,
        )
        posix.close(temp_fd)
        temp_fd = -1

        if allow_overwrite:
            posix.replace(
                temp_name,
                target_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        else:
            posix.link(
                temp_name,
                target_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            _remove_owned_temp_artifact(parent_fd, temp_name, temp_identity)
        posix.fsync(parent_fd)
        operation_succeeded = True
    except Exception:
        if temp_fd >= 0:
            posix.close(temp_fd)
            temp_fd = -1
        if parent_fd >= 0 and temp_identity is not None:
            _remove_owned_temp_artifact(parent_fd, temp_name, temp_identity)
        raise
    finally:
        if temp_fd >= 0:
            posix.close(temp_fd)
        if parent_fd >= 0:
            posix.close(parent_fd)
        if not operation_succeeded:
            _remove_created_directories(created_directories)


def _rechecked_snapshot(
    expected: _WorkspaceSnapshot,
    *,
    exact_parent_set: bool,
) -> _WorkspaceSnapshot:
    workspace_guard = validate_workspace_target_path(
        str(expected.root_path),
        expected.relative_output_path,
    )
    if not workspace_guard.allowed:
        raise SandboxWorkspaceViolationError(workspace_guard.reason)
    current = _snapshot_from_guard(workspace_guard)
    if current.output_path != expected.output_path:
        raise SandboxWorkspaceViolationError("workspace guard target path changed before artifact write")
    if current.root_identity != expected.root_identity:
        raise SandboxWorkspaceViolationError("workspace root identity changed before artifact write")
    expected_parents = dict(expected.parent_identities)
    current_parents = dict(current.parent_identities)
    if any(current_parents.get(path) != identity for path, identity in expected_parents.items()):
        raise SandboxWorkspaceViolationError("artifact parent identity changed before artifact write")
    if exact_parent_set and current.parent_identities != expected.parent_identities:
        raise SandboxWorkspaceViolationError("artifact parent chain changed before artifact write")
    if current.target_identity != expected.target_identity:
        raise SandboxWorkspaceViolationError("artifact target identity changed before artifact write")
    return current


def _snapshot_from_guard(result: WorkspaceGuardResult) -> _WorkspaceSnapshot:
    if (
        not result.allowed
        or result.workspace_root is None
        or result.normalized_relative_target_path is None
        or result.resolved_absolute_target_path is None
        or result.workspace_device is None
        or result.workspace_inode is None
    ):
        raise SandboxWorkspaceViolationError("workspace guard result lacks identity evidence")
    target_identity = None
    if result.target_device is not None or result.target_inode is not None or result.target_mode is not None:
        if result.target_device is None or result.target_inode is None or result.target_mode is None:
            raise SandboxWorkspaceViolationError("workspace target identity evidence is incomplete")
        target_identity = (
            result.target_device,
            result.target_inode,
            stat.S_IFMT(result.target_mode),
        )
    return _WorkspaceSnapshot(
        root_path=Path(result.workspace_root),
        root_identity=(result.workspace_device, result.workspace_inode, stat.S_IFDIR),
        parent_identities=tuple(
            (path, (device, inode, stat.S_IFDIR))
            for path, device, inode in result.parent_identities
        ),
        target_identity=target_identity,
        relative_output_path=result.normalized_relative_target_path,
        output_path=Path(result.resolved_absolute_target_path),
    )


def _open_target_parent_directory(
    snapshot: _WorkspaceSnapshot,
    parent_parts: list[str],
    created_directories: list[tuple[Path, _FileIdentity]],
) -> int:
    current_fd = _open_absolute_directory_without_symlinks(snapshot.root_path)
    if _identity_from_stat(posix.fstat(current_fd)) != snapshot.root_identity:
        posix.close(current_fd)
        raise SandboxWorkspaceViolationError("workspace root identity changed before directory access")

    current_path = snapshot.root_path
    expected_parents = dict(snapshot.parent_identities)
    relative_parts: list[str] = []
    try:
        for part in parent_parts:
            current_path = current_path / part
            relative_parts.append(part)
            relative_path = "/".join(relative_parts)
            expected_identity = expected_parents.get(relative_path)
            try:
                next_fd = posix.open(part, _directory_open_flags(), dir_fd=current_fd)
            except FileNotFoundError:
                if expected_identity is not None:
                    raise SandboxWorkspaceViolationError(
                        "artifact parent directory disappeared before filesystem effect"
                    )
                posix.mkdir(part, 0o700, dir_fd=current_fd)
                next_fd = posix.open(part, _directory_open_flags(), dir_fd=current_fd)
                created_directories.append(
                    (current_path, _identity_from_stat(posix.fstat(next_fd)))
                )
            else:
                actual_identity = _identity_from_stat(posix.fstat(next_fd))
                if expected_identity is None or actual_identity != expected_identity:
                    posix.close(next_fd)
                    raise SandboxWorkspaceViolationError(
                        "artifact parent directory appeared or changed before filesystem effect"
                    )
            posix.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        posix.close(current_fd)
        raise


def _open_absolute_directory_without_symlinks(path: Path) -> int:
    current_fd = posix.open(path.anchor, _directory_open_flags())
    try:
        for part in path.parts[1:]:
            next_fd = posix.open(part, _directory_open_flags(), dir_fd=current_fd)
            posix.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        posix.close(current_fd)
        raise


def _directory_open_flags() -> int:
    flags = posix.O_RDONLY
    if hasattr(posix, "O_DIRECTORY"):
        flags |= posix.O_DIRECTORY
    if hasattr(posix, "O_NOFOLLOW"):
        flags |= posix.O_NOFOLLOW
    if hasattr(posix, "O_CLOEXEC"):
        flags |= posix.O_CLOEXEC
    return flags


def _assert_operation_state(
    initial_snapshot: _WorkspaceSnapshot,
    operation_snapshot: _WorkspaceSnapshot,
    parent_fd: int,
    target_name: str,
    temp_name: str,
    temp_identity: _FileIdentity,
) -> None:
    current = _rechecked_snapshot(operation_snapshot, exact_parent_set=True)
    if current.root_identity != initial_snapshot.root_identity:
        raise SandboxWorkspaceViolationError("workspace root identity changed before filesystem effect")
    _assert_parent_fd_matches_snapshot(parent_fd, current)
    _assert_target_identity(parent_fd, target_name, initial_snapshot.target_identity)
    _assert_owned_temp_identity(parent_fd, temp_name, temp_identity)


def _assert_pre_temp_state(
    initial_snapshot: _WorkspaceSnapshot,
    operation_snapshot: _WorkspaceSnapshot,
    parent_fd: int,
    target_name: str,
) -> None:
    current = _rechecked_snapshot(operation_snapshot, exact_parent_set=True)
    if current.root_identity != initial_snapshot.root_identity:
        raise SandboxWorkspaceViolationError("workspace root identity changed before temporary-file creation")
    _assert_parent_fd_matches_snapshot(parent_fd, current)
    _assert_target_identity(parent_fd, target_name, initial_snapshot.target_identity)


def _assert_parent_fd_matches_snapshot(parent_fd: int, snapshot: _WorkspaceSnapshot) -> None:
    parent_parts = snapshot.relative_output_path.split("/")[:-1]
    if parent_parts:
        expected_identity = dict(snapshot.parent_identities).get("/".join(parent_parts))
    else:
        expected_identity = snapshot.root_identity
    if expected_identity is None:
        raise SandboxWorkspaceViolationError("artifact parent identity evidence is missing")
    if _identity_from_stat(posix.fstat(parent_fd)) != expected_identity:
        raise SandboxWorkspaceViolationError("artifact parent directory changed before filesystem effect")


def _assert_target_identity(
    parent_fd: int,
    target_name: str,
    expected_identity: _FileIdentity | None,
) -> None:
    current_identity = _identity_at(parent_fd, target_name)
    if current_identity is not None and current_identity[2] == stat.S_IFLNK:
        raise SandboxWorkspaceViolationError("sandbox artifact output path is a symlink")
    if current_identity != expected_identity:
        raise SandboxWorkspaceViolationError("artifact target identity changed before final placement")


def _assert_owned_temp_identity(
    parent_fd: int,
    temp_name: str,
    expected_identity: _FileIdentity,
) -> None:
    if _identity_at(parent_fd, temp_name) != expected_identity:
        raise SandboxWorkspaceViolationError("temporary artifact identity changed before final placement")
    if expected_identity[2] != stat.S_IFREG:
        raise SandboxWorkspaceViolationError("temporary artifact is not a regular file")


def _identity_at(parent_fd: int, name: str) -> _FileIdentity | None:
    try:
        return _identity_from_stat(
            posix.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        )
    except FileNotFoundError:
        return None


def _identity_from_stat(value: Any) -> _FileIdentity:
    return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))


def _remove_owned_temp_artifact(
    parent_fd: int,
    temp_name: str,
    expected_identity: _FileIdentity,
) -> None:
    if _identity_at(parent_fd, temp_name) != expected_identity:
        return
    try:
        posix.unlink(temp_name, dir_fd=parent_fd)
    except FileNotFoundError:
        return


def _remove_created_directories(
    created_directories: list[tuple[Path, _FileIdentity]],
) -> None:
    for path, expected_identity in reversed(created_directories):
        try:
            current = _identity_from_stat(path.stat(follow_symlinks=False))
            if current != expected_identity:
                continue
            posix.rmdir(str(path))
        except (FileNotFoundError, OSError):
            continue


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
