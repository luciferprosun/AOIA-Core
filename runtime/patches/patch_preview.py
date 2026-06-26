from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping


PATCH_PREVIEW_READY = "PATCH_PREVIEW_READY"
PATCH_PREVIEW_BLOCKED_EMPTY_EDIT_LIST = "PATCH_PREVIEW_BLOCKED_EMPTY_EDIT_LIST"
PATCH_PREVIEW_BLOCKED_TOO_MANY_FILES = "PATCH_PREVIEW_BLOCKED_TOO_MANY_FILES"
PATCH_PREVIEW_BLOCKED_INVALID_EDIT = "PATCH_PREVIEW_BLOCKED_INVALID_EDIT"
PATCH_PREVIEW_BLOCKED_UNSAFE_PATH = "PATCH_PREVIEW_BLOCKED_UNSAFE_PATH"
PATCH_PREVIEW_BLOCKED_DUPLICATE_TARGET = "PATCH_PREVIEW_BLOCKED_DUPLICATE_TARGET"
PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT = "PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT"
PATCH_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION = "PATCH_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION"

PATCH_RISK_MULTIPLE_FILES = "multiple_files"
PATCH_RISK_RUNTIME_TARGET = "runtime_file_target"
PATCH_RISK_TEST_TARGET = "test_file_target"
PATCH_RISK_DOCS_TARGET = "docs_file_target"
PATCH_RISK_HIDDEN_TARGET = "hidden_file_target"
PATCH_RISK_RISKY_PATH = "risky_path"
PATCH_RISK_OVERSIZED_CONTENT = "oversized_content"
PATCH_RISK_DIFF_TRUNCATED = "diff_truncated"
PATCH_RISK_CREATE_OPERATION = "create_operation"
PATCH_RISK_UPDATE_OPERATION = "update_operation"

MAX_PATCH_PREVIEW_FILES = 8
MAX_PATCH_PREVIEW_FILE_BYTES = 200_000
MAX_PATCH_PREVIEW_TOTAL_BYTES = 500_000
MAX_PATCH_PREVIEW_DIFF_LINES = 200
MAX_PATCH_PREVIEW_DIFF_CHARS = 12_000


@dataclass(frozen=True)
class PatchFileEdit:
    target_path: str
    proposed_content: str
    original_content: str | None = None
    declared_original_sha256: str | None = None
    operation: str = "update"


@dataclass(frozen=True)
class PatchPreviewFile:
    target_path: str
    operation: str
    proposed_sha256: str
    original_sha256: str | None
    declared_original_sha256: str | None
    proposed_size_bytes: int
    proposed_char_count: int
    original_size_bytes: int | None
    original_char_count: int | None
    diff_preview: str | None
    diff_truncated: bool
    risk_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_path": self.target_path,
            "operation": self.operation,
            "proposed_sha256": self.proposed_sha256,
            "original_sha256": self.original_sha256,
            "declared_original_sha256": self.declared_original_sha256,
            "proposed_size_bytes": self.proposed_size_bytes,
            "proposed_char_count": self.proposed_char_count,
            "original_size_bytes": self.original_size_bytes,
            "original_char_count": self.original_char_count,
            "diff_preview": self.diff_preview,
            "diff_truncated": self.diff_truncated,
            "risk_flags": list(self.risk_flags),
        }


@dataclass(frozen=True)
class PatchPreview:
    preview_id: str
    preview_hash: str
    status: str
    target_paths: tuple[str, ...]
    files: tuple[PatchPreviewFile, ...]
    total_file_count: int
    total_proposed_size_bytes: int
    total_proposed_char_count: int
    risk_flags: tuple[str, ...]
    reason_code: str
    reason: str
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
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preview_id": self.preview_id,
            "preview_hash": self.preview_hash,
            "status": self.status,
            "target_paths": list(self.target_paths),
            "files": [item.to_dict() for item in self.files],
            "total_file_count": self.total_file_count,
            "total_proposed_size_bytes": self.total_proposed_size_bytes,
            "total_proposed_char_count": self.total_proposed_char_count,
            "risk_flags": list(self.risk_flags),
            "reason_code": self.reason_code,
            "reason": self.reason,
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
class PatchPreviewResult:
    status: str
    preview_ready: bool
    reason_code: str
    reason: str
    patch_preview: PatchPreview | None = None
    preview_id: str | None = None
    preview_hash: str | None = None
    target_paths: tuple[str, ...] = ()
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
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "preview_ready": self.preview_ready,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "patch_preview": self.patch_preview.to_dict() if self.patch_preview is not None else None,
            "preview_id": self.preview_id,
            "preview_hash": self.preview_hash,
            "target_paths": list(self.target_paths),
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


def canonical_patch_preview_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_patch_preview_hash(value: Any) -> str:
    return _sha256(canonical_patch_preview_json(value))


def build_patch_preview(edits: tuple[PatchFileEdit | Mapping[str, Any], ...] | list[PatchFileEdit | Mapping[str, Any]]) -> PatchPreviewResult:
    if not isinstance(edits, (tuple, list)):
        return _blocked(PATCH_PREVIEW_BLOCKED_INVALID_EDIT, "patch preview requires a tuple or list of edits")
    if not edits:
        return _blocked(PATCH_PREVIEW_BLOCKED_EMPTY_EDIT_LIST, "patch preview requires at least one edit")
    if len(edits) > MAX_PATCH_PREVIEW_FILES:
        return _blocked(PATCH_PREVIEW_BLOCKED_TOO_MANY_FILES, "patch preview edit count exceeds the limit")

    normalized_edits: list[tuple[str, PatchFileEdit]] = []
    seen_targets: set[str] = set()
    total_bytes = 0
    for item in edits:
        edit, edit_error = _coerce_edit(item)
        if edit_error:
            return _blocked(PATCH_PREVIEW_BLOCKED_INVALID_EDIT, edit_error)
        assert edit is not None

        operation = _normalize_operation(edit.operation)
        if operation not in ("create", "update"):
            return _blocked(PATCH_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION, "patch preview supports only create/update metadata")
        target_path, target_error = _safe_relative_target(edit.target_path)
        if target_error:
            return _blocked(PATCH_PREVIEW_BLOCKED_UNSAFE_PATH, target_error)
        if target_path in seen_targets:
            return _blocked(PATCH_PREVIEW_BLOCKED_DUPLICATE_TARGET, "duplicate target paths are blocked")
        seen_targets.add(target_path)

        proposed_size = len(edit.proposed_content.encode("utf-8"))
        if proposed_size > MAX_PATCH_PREVIEW_FILE_BYTES:
            return _blocked(PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT, "patch preview file content exceeds the limit")
        total_bytes += proposed_size
        if total_bytes > MAX_PATCH_PREVIEW_TOTAL_BYTES:
            return _blocked(PATCH_PREVIEW_BLOCKED_OVERSIZED_CONTENT, "patch preview total content exceeds the limit")
        normalized_edits.append((target_path, edit))

    files: list[PatchPreviewFile] = []
    for target_path, edit in sorted(normalized_edits, key=lambda pair: pair[0]):
        operation = _normalize_operation(edit.operation)
        diff_preview = None
        diff_truncated = False
        if edit.original_content is not None:
            diff_preview, diff_truncated = _bounded_unified_diff(target_path, edit.original_content, edit.proposed_content)
        file_risks = _risk_flags_for_file(target_path, operation, diff_truncated)
        files.append(
            PatchPreviewFile(
                target_path=target_path,
                operation=operation,
                proposed_sha256=_sha256(edit.proposed_content),
                original_sha256=_sha256(edit.original_content) if edit.original_content is not None else None,
                declared_original_sha256=edit.declared_original_sha256,
                proposed_size_bytes=len(edit.proposed_content.encode("utf-8")),
                proposed_char_count=len(edit.proposed_content),
                original_size_bytes=len(edit.original_content.encode("utf-8")) if edit.original_content is not None else None,
                original_char_count=len(edit.original_content) if edit.original_content is not None else None,
                diff_preview=diff_preview,
                diff_truncated=diff_truncated,
                risk_flags=file_risks,
            )
        )

    target_paths = tuple(item.target_path for item in files)
    total_proposed_bytes = sum(item.proposed_size_bytes for item in files)
    total_proposed_chars = sum(item.proposed_char_count for item in files)
    risk_flags = _aggregate_risk_flags(files)
    material = {
        "schema_version": "AOIA_PATCH_PREVIEW_1A",
        "target_paths": list(target_paths),
        "files": [item.to_dict() for item in files],
        "total_file_count": len(files),
        "total_proposed_size_bytes": total_proposed_bytes,
        "total_proposed_char_count": total_proposed_chars,
        "risk_flags": list(risk_flags),
    }
    preview_hash = compute_patch_preview_hash(material)
    preview = PatchPreview(
        preview_id="patch-preview-" + preview_hash[:24],
        preview_hash=preview_hash,
        status=PATCH_PREVIEW_READY,
        target_paths=target_paths,
        files=tuple(files),
        total_file_count=len(files),
        total_proposed_size_bytes=total_proposed_bytes,
        total_proposed_char_count=total_proposed_chars,
        risk_flags=risk_flags,
        reason_code=PATCH_PREVIEW_READY,
        reason="patch preview is deterministic review metadata only",
    )
    return PatchPreviewResult(
        status=PATCH_PREVIEW_READY,
        preview_ready=True,
        reason_code=PATCH_PREVIEW_READY,
        reason="patch preview is deterministic review metadata only",
        patch_preview=preview,
        preview_id=preview.preview_id,
        preview_hash=preview.preview_hash,
        target_paths=target_paths,
        risk_flags=risk_flags,
    )


def _blocked(status: str, reason: str) -> PatchPreviewResult:
    return PatchPreviewResult(
        status=status,
        preview_ready=False,
        reason_code=status,
        reason=reason,
    )


def _coerce_edit(value: PatchFileEdit | Mapping[str, Any]) -> tuple[PatchFileEdit | None, str]:
    if isinstance(value, PatchFileEdit):
        edit = value
    elif isinstance(value, Mapping):
        edit = PatchFileEdit(
            target_path=value.get("target_path"),
            proposed_content=value.get("proposed_content"),
            original_content=value.get("original_content"),
            declared_original_sha256=value.get("declared_original_sha256"),
            operation=value.get("operation", "update"),
        )
    else:
        return None, "edit must be a PatchFileEdit or mapping"
    if not isinstance(edit.target_path, str):
        return None, "edit target path must be text"
    if not isinstance(edit.proposed_content, str):
        return None, "edit proposed content must be text"
    if edit.original_content is not None and not isinstance(edit.original_content, str):
        return None, "edit original content must be text when supplied"
    if edit.declared_original_sha256 is not None and not isinstance(edit.declared_original_sha256, str):
        return None, "edit declared original hash must be text when supplied"
    if not isinstance(edit.operation, str):
        return None, "edit operation must be text"
    return edit, ""


def _normalize_operation(value: str) -> str:
    return value.strip().casefold().replace("-", "_").replace(" ", "_")


def _safe_relative_target(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", "target path must be text"
    candidate = value.strip()
    if not candidate:
        return "", "empty target paths are blocked"
    if "\x00" in candidate:
        return "", "target path contains a null byte"
    if "\\" in candidate:
        return "", "backslash traversal is blocked"
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return "", "absolute target paths are blocked"
    path = PurePosixPath(candidate)
    if ".." in path.parts:
        return "", "parent traversal target paths are blocked"
    if ".git" in path.parts:
        return "", ".git target paths are blocked"
    normalized = path.as_posix()
    if normalized in ("", "."):
        return "", "empty target paths are blocked"
    return normalized, None


def _bounded_unified_diff(path: str, original: str, proposed: str) -> tuple[str, bool]:
    lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            proposed.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )
    text = "".join(lines[:MAX_PATCH_PREVIEW_DIFF_LINES])
    truncated = len(lines) > MAX_PATCH_PREVIEW_DIFF_LINES or len(text) > MAX_PATCH_PREVIEW_DIFF_CHARS
    if len(text) > MAX_PATCH_PREVIEW_DIFF_CHARS:
        text = text[:MAX_PATCH_PREVIEW_DIFF_CHARS]
    if truncated:
        text = text.rstrip("\n") + "\n... patch preview diff truncated ...\n"
    return text, truncated


def _risk_flags_for_file(target_path: str, operation: str, diff_truncated: bool) -> tuple[str, ...]:
    flags: set[str] = set()
    if target_path.startswith("runtime/"):
        flags.add(PATCH_RISK_RUNTIME_TARGET)
    if target_path.startswith("tests/"):
        flags.add(PATCH_RISK_TEST_TARGET)
    if target_path.startswith("docs/") or target_path.endswith(".md"):
        flags.add(PATCH_RISK_DOCS_TARGET)
    if any(part.startswith(".") for part in PurePosixPath(target_path).parts):
        flags.add(PATCH_RISK_HIDDEN_TARGET)
        flags.add(PATCH_RISK_RISKY_PATH)
    if operation == "create":
        flags.add(PATCH_RISK_CREATE_OPERATION)
    if operation == "update":
        flags.add(PATCH_RISK_UPDATE_OPERATION)
    if diff_truncated:
        flags.add(PATCH_RISK_DIFF_TRUNCATED)
    return tuple(sorted(flags))


def _aggregate_risk_flags(files: list[PatchPreviewFile]) -> tuple[str, ...]:
    flags: set[str] = set()
    if len(files) > 1:
        flags.add(PATCH_RISK_MULTIPLE_FILES)
    for item in files:
        flags.update(item.risk_flags)
    return tuple(sorted(flags))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
