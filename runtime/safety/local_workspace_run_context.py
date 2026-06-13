from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.safety.local_agent_entrypoint import (
    LocalAgentEntrypointResult,
    run_durable_local_agent_entrypoint,
)


RUNS_DIR_NAME = "runs"
ARTIFACTS_DIR_NAME = "artifacts"
AUDIT_DIR_NAME = "audit"
DEFAULT_RELATIVE_OUTPUT_PATH = "aoia_agent_v0_result.md"
MAX_LOCAL_RUN_ID_CHARS = 64
SAFE_LOCAL_RUN_ID_PATTERN = re.compile(r"^[a-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class LocalWorkspaceRunContext:
    prepared: bool
    base_workspace_root: str
    run_id: str
    run_root: str
    artifact_workspace_root: str
    audit_dir: str
    default_relative_output_path: str
    reason: str

    def __post_init__(self) -> None:
        if self.prepared is not True:
            raise ValueError("prepared must be True for a completed local workspace run context")
        object.__setattr__(self, "base_workspace_root", _coerce_text("base_workspace_root", self.base_workspace_root))
        object.__setattr__(self, "run_id", _validate_run_id(self.run_id))
        object.__setattr__(self, "run_root", _coerce_text("run_root", self.run_root))
        object.__setattr__(self, "artifact_workspace_root", _coerce_text("artifact_workspace_root", self.artifact_workspace_root))
        object.__setattr__(self, "audit_dir", _coerce_text("audit_dir", self.audit_dir))
        object.__setattr__(
            self,
            "default_relative_output_path",
            _validate_relative_output_path(self.default_relative_output_path),
        )
        object.__setattr__(self, "reason", _coerce_text("reason", self.reason))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prepared": self.prepared,
            "base_workspace_root": self.base_workspace_root,
            "run_id": self.run_id,
            "run_root": self.run_root,
            "artifact_workspace_root": self.artifact_workspace_root,
            "audit_dir": self.audit_dir,
            "default_relative_output_path": self.default_relative_output_path,
            "reason": self.reason,
        }


def prepare_local_workspace_run_context(
    *,
    base_workspace_root: str | Path,
    run_id: str | None = None,
    default_relative_output_path: str = DEFAULT_RELATIVE_OUTPUT_PATH,
) -> LocalWorkspaceRunContext:
    base_root = _prepare_base_workspace_root(base_workspace_root)
    safe_run_id = _validate_run_id(run_id or _generate_run_id())
    safe_output_path = _validate_relative_output_path(default_relative_output_path)

    runs_root = base_root / RUNS_DIR_NAME
    _assert_not_symlink(runs_root, "runs directory")
    runs_root.mkdir(mode=0o700, exist_ok=True)
    _assert_not_symlink(runs_root, "runs directory")

    run_root = runs_root / safe_run_id
    if run_root.exists():
        raise FileExistsError("local workspace run directory already exists")

    artifact_root = run_root / ARTIFACTS_DIR_NAME
    audit_dir = run_root / AUDIT_DIR_NAME
    _assert_inside(base_root, run_root, "run root")
    _assert_inside(run_root, artifact_root, "artifact directory")
    _assert_inside(run_root, audit_dir, "audit directory")

    run_root.mkdir(mode=0o700, exist_ok=False)
    artifact_root.mkdir(mode=0o700, exist_ok=False)
    audit_dir.mkdir(mode=0o700, exist_ok=False)

    _assert_inside(base_root, run_root, "run root")
    _assert_inside(run_root, artifact_root, "artifact directory")
    _assert_inside(run_root, audit_dir, "audit directory")
    _assert_not_symlink(artifact_root, "artifact directory")
    _assert_not_symlink(audit_dir, "audit directory")

    return LocalWorkspaceRunContext(
        prepared=True,
        base_workspace_root=os.path.realpath(str(base_root)),
        run_id=safe_run_id,
        run_root=os.path.realpath(str(run_root)),
        artifact_workspace_root=os.path.realpath(str(artifact_root)),
        audit_dir=os.path.realpath(str(audit_dir)),
        default_relative_output_path=safe_output_path,
        reason="Macrostep 4A local workspace run context prepared",
    )


def run_durable_local_agent_in_workspace(
    *,
    goal: str,
    base_workspace_root: str | Path,
    run_id: str | None = None,
    approval_actor_id: str = "human-reviewer",
) -> LocalAgentEntrypointResult:
    context = prepare_local_workspace_run_context(base_workspace_root=base_workspace_root, run_id=run_id)
    return run_durable_local_agent_entrypoint(
        goal=goal,
        workspace_root=context.artifact_workspace_root,
        audit_dir=context.audit_dir,
        relative_output_path=context.default_relative_output_path,
        approval_actor_id=approval_actor_id,
    )


def local_workspace_run_context_to_dict(context: LocalWorkspaceRunContext) -> dict[str, Any]:
    if not isinstance(context, LocalWorkspaceRunContext):
        raise TypeError("context must be a LocalWorkspaceRunContext")
    return context.to_dict()


def _prepare_base_workspace_root(value: str | Path) -> Path:
    raw_text = _path_value_to_text("base_workspace_root", value)
    _reject_control_characters("base_workspace_root", raw_text)
    raw_path = Path(raw_text)
    if not raw_path.is_absolute():
        raise ValueError("base_workspace_root must be absolute")
    if raw_path.exists() and raw_path.is_symlink():
        raise ValueError("base_workspace_root must not be a symlink")
    raw_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if raw_path.is_symlink():
        raise ValueError("base_workspace_root must not be a symlink")
    return Path(os.path.realpath(str(raw_path)))


def _validate_run_id(run_id: str) -> str:
    value = _coerce_text("run_id", run_id)
    _reject_control_characters("run_id", value)
    if not value:
        raise ValueError("run_id must not be empty")
    if len(value) > MAX_LOCAL_RUN_ID_CHARS:
        raise ValueError("run_id is too long")
    if not SAFE_LOCAL_RUN_ID_PATTERN.fullmatch(value):
        raise ValueError("run_id must contain only lowercase letters, digits, dash, or underscore")
    return value


def _validate_relative_output_path(relative_output_path: str) -> str:
    value = _coerce_text("default_relative_output_path", relative_output_path).strip()
    _reject_control_characters("default_relative_output_path", value)
    if not value:
        raise ValueError("default_relative_output_path must not be empty")
    if "\\" in value:
        raise ValueError("default_relative_output_path must not contain backslashes")
    output_path = Path(value)
    if output_path.is_absolute():
        raise ValueError("default_relative_output_path must be relative")
    parts = output_path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError("default_relative_output_path contains an unsafe path component")
    return value


def _path_value_to_text(name: str, value: str | Path) -> str:
    if isinstance(value, Path):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not text.strip():
        raise ValueError(f"{name} must be explicit")
    return text


def _reject_control_characters(name: str, value: str) -> None:
    for character in value:
        codepoint = ord(character)
        if codepoint < 32 or codepoint == 127:
            raise ValueError(f"{name} contains a blocked control character")


def _assert_not_symlink(path: Path, label: str) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")


def _assert_inside(root: Path, candidate: Path, label: str) -> None:
    root_real = os.path.realpath(str(root))
    candidate_real = os.path.realpath(str(candidate))
    try:
        common = os.path.commonpath((root_real, candidate_real))
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside local workspace root") from exc
    if common != root_real:
        raise ValueError(f"{label} must stay inside local workspace root")


def _generate_run_id() -> str:
    return uuid.uuid4().hex


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
