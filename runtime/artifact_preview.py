from __future__ import annotations

import difflib
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath


class ArtifactPreviewStatus:
    PREVIEW_READY = "preview_ready"
    INVALID_TARGET = "invalid_target"
    INVALID_CONTENT = "invalid_content"
    BLOCKED_BY_POLICY = "blocked_by_policy"


class ArtifactPreviewFlag:
    PREVIEW_ONLY = "preview_only"
    NO_WRITE_PERFORMED = "no_write_performed"
    TARGET_PATH_NORMALIZED = "target_path_normalized"
    TARGET_PATH_REJECTED = "target_path_rejected"
    PATH_TRAVERSAL_DETECTED = "path_traversal_detected"
    ABSOLUTE_PATH_REJECTED = "absolute_path_rejected"
    EMPTY_CONTENT = "empty_content"
    LARGE_CONTENT_WARNING = "large_content_warning"
    PROVIDER_OUTPUT_UNTRUSTED = "provider_output_untrusted"
    CRITIC_WARNING_PRESENT = "critic_warning_present"
    DIFF_AVAILABLE = "diff_available"
    DIFF_NOT_AVAILABLE = "diff_not_available"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


_LARGE_CONTENT_BYTES = 1_000_000
_MAX_DIFF_LINES = 200
_MAX_DIFF_CHARS = 12_000


@dataclass(frozen=True)
class ArtifactPreviewRequest:
    target_path: str
    proposed_content: str
    original_content: str | None = None
    artifact_kind: str = "text"
    reason: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    provider_output_trust: str | None = None
    critic_verdict: str | None = None


@dataclass(frozen=True)
class ArtifactPreview:
    preview_id: str
    target_path: str
    artifact_kind: str
    status: str
    flags: tuple[str, ...]
    proposed_sha256: str
    original_sha256: str | None
    proposed_size_bytes: int
    proposed_line_count: int
    original_line_count: int | None
    diff_preview: str | None
    summary: str
    human_review_required: bool
    write_performed: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_change_gate: bool = False
    provider_output_trust: str | None = None
    critic_verdict: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "write_performed",
            "can_write",
            "can_execute",
            "can_commit",
            "can_change_gate",
        ):
            object.__setattr__(self, field_name, False)


def build_artifact_preview(request: ArtifactPreviewRequest) -> ArtifactPreview:
    if not isinstance(request, ArtifactPreviewRequest):
        raise TypeError("request must be an ArtifactPreviewRequest")

    flags = [ArtifactPreviewFlag.PREVIEW_ONLY, ArtifactPreviewFlag.NO_WRITE_PERFORMED]
    target_path, path_error = _normalize_target_path(request.target_path)
    if path_error:
        flags.append(ArtifactPreviewFlag.TARGET_PATH_REJECTED)
        if path_error != ArtifactPreviewFlag.TARGET_PATH_REJECTED:
            flags.append(path_error)
        status = ArtifactPreviewStatus.INVALID_TARGET
    else:
        flags.append(ArtifactPreviewFlag.TARGET_PATH_NORMALIZED)
        status = ArtifactPreviewStatus.PREVIEW_READY

    content_valid = isinstance(request.proposed_content, str)
    proposed = request.proposed_content if content_valid else ""
    if not proposed:
        flags.append(ArtifactPreviewFlag.EMPTY_CONTENT)
        if status == ArtifactPreviewStatus.PREVIEW_READY:
            status = ArtifactPreviewStatus.INVALID_CONTENT

    proposed_bytes = proposed.encode("utf-8")
    if len(proposed_bytes) > _LARGE_CONTENT_BYTES:
        flags.append(ArtifactPreviewFlag.LARGE_CONTENT_WARNING)

    original = request.original_content
    diff_preview = None
    diff_truncated = False
    if original is not None:
        diff_preview, diff_truncated = _bounded_unified_diff(target_path, original, proposed)
        flags.append(ArtifactPreviewFlag.DIFF_AVAILABLE)
    else:
        flags.append(ArtifactPreviewFlag.DIFF_NOT_AVAILABLE)

    human_review = False
    if request.provider_output_trust and request.provider_output_trust.strip().casefold() == "untrusted":
        flags.append(ArtifactPreviewFlag.PROVIDER_OUTPUT_UNTRUSTED)
        human_review = True
    if request.critic_verdict and any(
        marker in request.critic_verdict.strip().casefold()
        for marker in ("warn", "block", "reject")
    ):
        flags.append(ArtifactPreviewFlag.CRITIC_WARNING_PRESENT)
        human_review = True
    if human_review:
        flags.append(ArtifactPreviewFlag.HUMAN_REVIEW_REQUIRED)

    proposed_hash = _sha256(proposed)
    original_hash = _sha256(original) if original is not None else None
    summary = _summary(status, request.reason, diff_truncated)
    preview_id = _preview_id(
        target_path=target_path,
        artifact_kind=request.artifact_kind,
        proposed_hash=proposed_hash,
        original_hash=original_hash,
        provider_output_trust=request.provider_output_trust,
        critic_verdict=request.critic_verdict,
        reason=request.reason,
    )
    return ArtifactPreview(
        preview_id=preview_id,
        target_path=target_path,
        artifact_kind=request.artifact_kind,
        status=status,
        flags=tuple(flags),
        proposed_sha256=proposed_hash,
        original_sha256=original_hash,
        proposed_size_bytes=len(proposed_bytes),
        proposed_line_count=_line_count(proposed),
        original_line_count=_line_count(original) if original is not None else None,
        diff_preview=diff_preview,
        summary=summary,
        human_review_required=human_review,
        provider_output_trust=request.provider_output_trust,
        critic_verdict=request.critic_verdict,
    )


def _normalize_target_path(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", ArtifactPreviewFlag.TARGET_PATH_REJECTED
    candidate = value.strip().replace("\\", "/")
    if not candidate or "\x00" in candidate:
        return candidate, ArtifactPreviewFlag.TARGET_PATH_REJECTED
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return candidate, ArtifactPreviewFlag.ABSOLUTE_PATH_REJECTED
    if ".." in PurePosixPath(candidate).parts:
        return candidate, ArtifactPreviewFlag.PATH_TRAVERSAL_DETECTED
    normalized = PurePosixPath(candidate).as_posix()
    if normalized in ("", "."):
        return normalized, ArtifactPreviewFlag.TARGET_PATH_REJECTED
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
    text = "".join(lines[:_MAX_DIFF_LINES])
    truncated = len(lines) > _MAX_DIFF_LINES or len(text) > _MAX_DIFF_CHARS
    if len(text) > _MAX_DIFF_CHARS:
        text = text[:_MAX_DIFF_CHARS]
    if truncated:
        text = text.rstrip("\n") + "\n... diff preview truncated ...\n"
    return text, truncated


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _line_count(value: str) -> int:
    return len(value.splitlines())


def _summary(status: str, reason: str | None, truncated: bool) -> str:
    parts = [f"Artifact preview status: {status}."]
    if reason:
        parts.append(" ".join(reason.split())[:240])
    if truncated:
        parts.append("Unified diff preview was truncated.")
    return " ".join(parts)


def _preview_id(**values: str | None) -> str:
    canonical = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"artifact-preview-{_sha256(canonical)[:24]}"
