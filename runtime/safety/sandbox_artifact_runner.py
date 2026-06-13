from __future__ import annotations

import posix
from pathlib import Path

from runtime.safety.sandbox_workspace import (
    SandboxOverwriteBlockedError,
    SandboxWorkspaceViolationError,
    assert_safe_artifact_write_path,
)
from runtime.schemas.sandbox_artifact import (
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


def write_sandbox_artifact(
    request: SandboxArtifactRequest,
    workspace_root: str,
    allow_overwrite: bool = False,
) -> SandboxArtifactResult:
    if not isinstance(request, SandboxArtifactRequest):
        raise TypeError("request must be a SandboxArtifactRequest")
    if not request.human_approved:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason="sandbox artifact request requires explicit human approval",
            notes="M8-A artifact write blocked before filesystem access",
        )
    content_bytes = request.content_text.encode("utf-8")
    if len(content_bytes) > MAX_SANDBOX_ARTIFACT_BYTES:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason="sandbox artifact content exceeds M8-A size limit",
            notes="M8-A artifact write blocked before filesystem access",
        )
    try:
        resolved_output_path = assert_safe_artifact_write_path(workspace_root, request.relative_output_path)
    except SandboxWorkspaceViolationError as exc:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            blocked_reason=str(exc),
            notes="M8-A workspace guard blocked artifact write",
        )

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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resolved_output_path = assert_safe_artifact_write_path(workspace_root, request.relative_output_path)
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
        _write_text_artifact_atomically(output_path, content_bytes, allow_overwrite)
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


def _write_text_artifact_atomically(output_path: Path, content_bytes: bytes, allow_overwrite: bool) -> None:
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
