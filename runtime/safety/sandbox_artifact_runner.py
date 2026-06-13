from __future__ import annotations

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
    if output_path.exists() and not allow_overwrite:
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact overwrite blocked by default",
            notes="M8-A artifact write blocked before opening output path",
        )
    if output_path.exists() and output_path.is_symlink():
        return create_blocked_sandbox_artifact_result(
            request,
            workspace_root=workspace_root,
            resolved_output_path=resolved_output_path,
            blocked_reason="sandbox artifact output path is a symlink",
            notes="M8-A artifact write blocked before opening output path",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if allow_overwrite else "x"
    try:
        with output_path.open(mode, encoding="utf-8") as handle:
            handle.write(request.content_text)
    except FileExistsError as exc:
        raise SandboxOverwriteBlockedError("sandbox artifact overwrite blocked by default") from exc
    except OSError as exc:
        raise SandboxArtifactWriteBlockedError("sandbox artifact write failed") from exc

    return create_written_sandbox_artifact_result(
        request,
        workspace_root=workspace_root,
        resolved_output_path=resolved_output_path,
        bytes_written=len(content_bytes),
        notes="M8-A wrote one workspace-bound text artifact",
    )
