from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import (
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.human_decision_gated_artifact_write import (
    ARTIFACT_WRITTEN,
    HumanDecisionGatedArtifactWriteResult,
    write_artifact_after_human_gate,
)
from runtime.patches.patch_barrier import (
    PATCH_BARRIER_VERIFIED,
    PATCH_BARRIER_BLOCKED_HASH_MISMATCH,
    PATCH_DECISION_APPROVE,
    HumanPatchBarrierResult,
    verify_human_patch_barrier,
)
from runtime.patches.patch_policy import (
    PATCH_POLICY_BLOCK,
    PATCH_POLICY_NEEDS_REVIEW,
    PATCH_POLICY_PASS,
    PatchPolicyCheckResult,
    compute_patch_policy_hash,
)
from runtime.patches.patch_preview import (
    PATCH_PREVIEW_READY,
    PatchPreview,
    PatchPreviewFile,
    PatchPreviewResult,
    compute_patch_preview_hash,
)
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.workspace_guard import validate_workspace_target_path
from runtime.safety.write_kill_switch import check_write_kill_switch_file
from runtime.schemas.sandbox_artifact import SandboxArtifactRequest, SandboxArtifactResult


CONTROLLED_PATCH_APPLIED = "CONTROLLED_PATCH_APPLIED"
CONTROLLED_PATCH_BLOCKED = "CONTROLLED_PATCH_BLOCKED"
CONTROLLED_PATCH_PARTIAL = "CONTROLLED_PATCH_PARTIAL"

CONTROLLED_PATCH_FILE_APPLIED = "CONTROLLED_PATCH_FILE_APPLIED"
CONTROLLED_PATCH_FILE_BLOCKED = "CONTROLLED_PATCH_FILE_BLOCKED"
CONTROLLED_PATCH_FILE_NOT_ATTEMPTED = "CONTROLLED_PATCH_FILE_NOT_ATTEMPTED"

PATCH_APPLY_BLOCKED_MISSING_PREVIEW = "PATCH_APPLY_BLOCKED_MISSING_PREVIEW"
PATCH_APPLY_BLOCKED_MALFORMED_PREVIEW = "PATCH_APPLY_BLOCKED_MALFORMED_PREVIEW"
PATCH_APPLY_BLOCKED_PREVIEW_NOT_READY = "PATCH_APPLY_BLOCKED_PREVIEW_NOT_READY"
PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH = "PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH"
PATCH_APPLY_BLOCKED_MISSING_POLICY = "PATCH_APPLY_BLOCKED_MISSING_POLICY"
PATCH_APPLY_BLOCKED_POLICY_HASH_MISSING = "PATCH_APPLY_BLOCKED_POLICY_HASH_MISSING"
PATCH_APPLY_BLOCKED_POLICY_HASH_MISMATCH = "PATCH_APPLY_BLOCKED_POLICY_HASH_MISMATCH"
PATCH_APPLY_BLOCKED_POLICY_PREVIEW_MISMATCH = "PATCH_APPLY_BLOCKED_POLICY_PREVIEW_MISMATCH"
PATCH_APPLY_BLOCKED_POLICY_STATUS = "PATCH_APPLY_BLOCKED_POLICY_STATUS"
PATCH_APPLY_BLOCKED_POLICY_HARD_FINDING = "PATCH_APPLY_BLOCKED_POLICY_HARD_FINDING"
PATCH_APPLY_BLOCKED_POLICY_PROFILE_MISMATCH = "PATCH_APPLY_BLOCKED_POLICY_PROFILE_MISMATCH"
PATCH_APPLY_BLOCKED_MISSING_BARRIER = "PATCH_APPLY_BLOCKED_MISSING_BARRIER"
PATCH_APPLY_BLOCKED_BARRIER_INVALID = "PATCH_APPLY_BLOCKED_BARRIER_INVALID"
PATCH_APPLY_BLOCKED_BARRIER_HASH_MISSING = "PATCH_APPLY_BLOCKED_BARRIER_HASH_MISSING"
PATCH_APPLY_BLOCKED_BARRIER_HASH_MISMATCH = "PATCH_APPLY_BLOCKED_BARRIER_HASH_MISMATCH"
PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE = "PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE"
PATCH_APPLY_BLOCKED_TARGET_MISMATCH = "PATCH_APPLY_BLOCKED_TARGET_MISMATCH"
PATCH_APPLY_BLOCKED_DUPLICATE_TARGET = "PATCH_APPLY_BLOCKED_DUPLICATE_TARGET"
PATCH_APPLY_BLOCKED_UNSUPPORTED_OPERATION = "PATCH_APPLY_BLOCKED_UNSUPPORTED_OPERATION"
PATCH_APPLY_BLOCKED_MISSING_PROPOSED_CONTENT = "PATCH_APPLY_BLOCKED_MISSING_PROPOSED_CONTENT"
PATCH_APPLY_BLOCKED_PROPOSED_HASH_MISMATCH = "PATCH_APPLY_BLOCKED_PROPOSED_HASH_MISMATCH"
PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISSING = "PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISSING"
PATCH_APPLY_BLOCKED_ORIGINAL_FILE_MISSING = "PATCH_APPLY_BLOCKED_ORIGINAL_FILE_MISSING"
PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISMATCH = "PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISMATCH"
PATCH_APPLY_BLOCKED_CREATE_TARGET_EXISTS = "PATCH_APPLY_BLOCKED_CREATE_TARGET_EXISTS"
PATCH_APPLY_BLOCKED_WORKSPACE_GUARD = "PATCH_APPLY_BLOCKED_WORKSPACE_GUARD"
PATCH_APPLY_BLOCKED_KILL_SWITCH = "PATCH_APPLY_BLOCKED_KILL_SWITCH"
PATCH_APPLY_BLOCKED_MISSING_GATE = "PATCH_APPLY_BLOCKED_MISSING_GATE"
PATCH_APPLY_BLOCKED_MISSING_CONTEXT = "PATCH_APPLY_BLOCKED_MISSING_CONTEXT"
PATCH_APPLY_BLOCKED_CONTROLLED_WRITE = "PATCH_APPLY_BLOCKED_CONTROLLED_WRITE"
PATCH_APPLY_BLOCKED_FAIL_CLOSED = "PATCH_APPLY_BLOCKED_FAIL_CLOSED"

_SHA256_HEX = frozenset("0123456789abcdef")
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

ControlledPatchGatedWriter = Callable[..., HumanDecisionGatedArtifactWriteResult]


@dataclass(frozen=True)
class ControlledPatchApplyRequest:
    patch_preview: PatchPreview | PatchPreviewResult | None
    patch_policy: PatchPolicyCheckResult | None
    human_patch_barrier: HumanPatchBarrierResult | Mapping[str, Any] | None
    proposed_contents: Mapping[str, str]
    workspace_root: str
    gate_results: Mapping[str, Any]
    context: ControlWriteContext
    write_kill_switch_path: str
    write_kill_switch_directory: str | None = None
    expected_packet_hash: str | None = None
    expected_policy_profile_name: str | None = None
    expected_policy_profile_version: str | None = None
    gated_writer: ControlledPatchGatedWriter | None = None


@dataclass(frozen=True)
class ControlledPatchApplyFileResult:
    target_path: str
    operation: str | None
    status: str
    reason_code: str
    reason: str
    proposed_sha256: str | None
    original_sha256: str | None
    artifact_path: str | None = None
    controlled_write_status: str | None = None
    write_attempted: bool = False
    artifact_write_occurred: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_path": self.target_path,
            "operation": self.operation,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "proposed_sha256": self.proposed_sha256,
            "original_sha256": self.original_sha256,
            "artifact_path": self.artifact_path,
            "controlled_write_status": self.controlled_write_status,
            "write_attempted": self.write_attempted,
            "artifact_write_occurred": self.artifact_write_occurred,
        }


@dataclass(frozen=True)
class ControlledPatchApplyResult:
    status: str
    apply_hash: str | None
    patch_preview_hash: str | None
    patch_policy_hash: str | None
    patch_barrier_hash: str | None
    target_paths: tuple[str, ...]
    file_results: tuple[ControlledPatchApplyFileResult, ...]
    reason_code: str
    reason: str
    partial_apply: bool = False
    patch_applied: bool = False
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
        object.__setattr__(self, "target_paths", tuple(self.target_paths))
        object.__setattr__(self, "file_results", tuple(self.file_results))
        object.__setattr__(self, "patch_applied", self.status == CONTROLLED_PATCH_APPLIED)
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "apply_hash": self.apply_hash,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "patch_barrier_hash": self.patch_barrier_hash,
            "target_paths": list(self.target_paths),
            "file_results": [item.to_dict() for item in self.file_results],
            "reason_code": self.reason_code,
            "reason": self.reason,
            "partial_apply": self.partial_apply,
            "patch_applied": self.patch_applied,
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


def canonical_controlled_patch_apply_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_controlled_patch_apply_hash(value: Any) -> str:
    return hashlib.sha256(canonical_controlled_patch_apply_json(value).encode("utf-8")).hexdigest()


def apply_controlled_patch(request: ControlledPatchApplyRequest | Mapping[str, Any] | None) -> ControlledPatchApplyResult:
    try:
        if not isinstance(request, ControlledPatchApplyRequest):
            return _blocked(PATCH_APPLY_BLOCKED_FAIL_CLOSED, "controlled patch apply requires a typed request")

        preview, preview_error = _coerce_preview(request.patch_preview)
        if preview_error is not None:
            return _blocked(preview_error, "valid patch preview evidence is required")
        assert preview is not None
        preview_integrity_error = _preview_integrity_error(preview)
        if preview_integrity_error is not None:
            return _blocked(preview_integrity_error, "patch preview hash does not match deterministic preview metadata", preview=preview)

        policy_error = _policy_error(
            preview=preview,
            policy=request.patch_policy,
            expected_name=request.expected_policy_profile_name,
            expected_version=request.expected_policy_profile_version,
        )
        if policy_error is not None:
            return _blocked(policy_error, "valid patch policy evidence is required", preview=preview, policy=request.patch_policy)

        assert request.patch_policy is not None
        if request.human_patch_barrier is None:
            return _blocked(
                PATCH_APPLY_BLOCKED_MISSING_BARRIER,
                "valid APPROVE human patch barrier evidence is required",
                preview=preview,
                policy=request.patch_policy,
            )

        verified_barrier = verify_human_patch_barrier(
            request.human_patch_barrier,
            expected_patch_preview_hash=preview.preview_hash,
            expected_patch_policy_hash=request.patch_policy.policy_hash,
            expected_target_paths=preview.target_paths,
            expected_policy_status=request.patch_policy.status,
        )
        barrier_error = _barrier_error(verified_barrier, request.patch_policy.status)
        if barrier_error is not None:
            return _blocked(
                barrier_error,
                "valid APPROVE human patch barrier evidence is required",
                preview=preview,
                policy=request.patch_policy,
                barrier=verified_barrier,
            )

        preflight = _preflight_files(preview, request)
        if preflight is not None:
            return _blocked(
                preflight.reason_code,
                preflight.reason,
                preview=preview,
                policy=request.patch_policy,
                barrier=verified_barrier,
                file_results=(preflight,),
            )

        kill_switch = check_write_kill_switch_file(
            request.write_kill_switch_path,
            allowed_switch_directory=request.write_kill_switch_directory,
        )
        if not kill_switch.writes_allowed:
            return _blocked(
                PATCH_APPLY_BLOCKED_KILL_SWITCH,
                kill_switch.reason,
                preview=preview,
                policy=request.patch_policy,
                barrier=verified_barrier,
            )

        file_results: list[ControlledPatchApplyFileResult] = []
        for file_preview in preview.files:
            proposed_content = request.proposed_contents[file_preview.target_path]
            gate_result = request.gate_results.get(file_preview.target_path)
            if gate_result is None:
                file_results.append(_file_blocked(file_preview, PATCH_APPLY_BLOCKED_MISSING_GATE, "per-file gate evidence is required"))
                return _result(
                    status=CONTROLLED_PATCH_PARTIAL if any(item.artifact_write_occurred for item in file_results) else CONTROLLED_PATCH_BLOCKED,
                    reason_code=PATCH_APPLY_BLOCKED_MISSING_GATE,
                    reason="per-file gate evidence is required",
                    preview=preview,
                    policy=request.patch_policy,
                    barrier=verified_barrier,
                    file_results=tuple(file_results),
                )

            artifact_preview = build_artifact_preview(
                ArtifactPreviewRequest(
                    target_path=file_preview.target_path,
                    proposed_content=proposed_content,
                    original_content=_original_content_for_artifact_preview(request.workspace_root, file_preview),
                    artifact_kind="text",
                    reason="Step 24 controlled patch apply reviewed text content",
                    provider_output_trust="untrusted",
                )
            )
            controlled = write_preview_artifact_after_human_gate(
                preview=artifact_preview,
                proposed_content_text=proposed_content,
                workspace_root=request.workspace_root,
                gate_result=gate_result,
                context=_context_for_file(request.context, file_preview),
                expected_packet_hash=request.expected_packet_hash,
                expected_artifact_hash=file_preview.proposed_sha256,
                gated_writer=_gated_writer_for_file(request, file_preview),
                write_kill_switch_path=request.write_kill_switch_path,
                write_kill_switch_directory=request.write_kill_switch_directory,
            )
            if controlled.status != ARTIFACT_WRITTEN or not controlled.artifact_write_occurred:
                file_results.append(
                    ControlledPatchApplyFileResult(
                        target_path=file_preview.target_path,
                        operation=file_preview.operation,
                        status=CONTROLLED_PATCH_FILE_BLOCKED,
                        reason_code=PATCH_APPLY_BLOCKED_CONTROLLED_WRITE,
                        reason=controlled.reason,
                        proposed_sha256=file_preview.proposed_sha256,
                        original_sha256=file_preview.original_sha256,
                        artifact_path=controlled.artifact_path,
                        controlled_write_status=controlled.status,
                        write_attempted=controlled.write_attempted,
                        artifact_write_occurred=False,
                    )
                )
                return _result(
                    status=CONTROLLED_PATCH_PARTIAL if any(item.artifact_write_occurred for item in file_results) else CONTROLLED_PATCH_BLOCKED,
                    reason_code=PATCH_APPLY_BLOCKED_CONTROLLED_WRITE,
                    reason=controlled.reason,
                    preview=preview,
                    policy=request.patch_policy,
                    barrier=verified_barrier,
                    file_results=tuple(file_results),
                )

            file_results.append(
                ControlledPatchApplyFileResult(
                    target_path=file_preview.target_path,
                    operation=file_preview.operation,
                    status=CONTROLLED_PATCH_FILE_APPLIED,
                    reason_code=CONTROLLED_PATCH_FILE_APPLIED,
                    reason="controlled patch file write completed through existing gated sandbox path",
                    proposed_sha256=file_preview.proposed_sha256,
                    original_sha256=file_preview.original_sha256,
                    artifact_path=controlled.artifact_path,
                    controlled_write_status=controlled.status,
                    write_attempted=controlled.write_attempted,
                    artifact_write_occurred=True,
                )
            )

        return _result(
            status=CONTROLLED_PATCH_APPLIED,
            reason_code=CONTROLLED_PATCH_APPLIED,
            reason="controlled patch apply completed after all evidence and controlled write checks passed",
            preview=preview,
            policy=request.patch_policy,
            barrier=verified_barrier,
            file_results=tuple(file_results),
        )
    except Exception:
        return _blocked(PATCH_APPLY_BLOCKED_FAIL_CLOSED, "controlled patch apply failed closed")


def _coerce_preview(value: PatchPreview | PatchPreviewResult | None) -> tuple[PatchPreview | None, str | None]:
    if value is None:
        return None, PATCH_APPLY_BLOCKED_MISSING_PREVIEW
    if isinstance(value, PatchPreviewResult):
        if value.patch_preview is None:
            return None, PATCH_APPLY_BLOCKED_MISSING_PREVIEW
        if value.status != PATCH_PREVIEW_READY or not value.preview_ready:
            return None, PATCH_APPLY_BLOCKED_PREVIEW_NOT_READY
        return value.patch_preview, None
    if isinstance(value, PatchPreview):
        if value.status != PATCH_PREVIEW_READY:
            return None, PATCH_APPLY_BLOCKED_PREVIEW_NOT_READY
        return value, None
    return None, PATCH_APPLY_BLOCKED_MALFORMED_PREVIEW


def _policy_error(
    *,
    preview: PatchPreview,
    policy: PatchPolicyCheckResult | None,
    expected_name: str | None,
    expected_version: str | None,
) -> str | None:
    if not isinstance(policy, PatchPolicyCheckResult):
        return PATCH_APPLY_BLOCKED_MISSING_POLICY
    if not _full_hash(policy.policy_hash):
        return PATCH_APPLY_BLOCKED_POLICY_HASH_MISSING
    if _expected_policy_hash(policy) != policy.policy_hash:
        return PATCH_APPLY_BLOCKED_POLICY_HASH_MISMATCH
    if policy.patch_preview_hash != preview.preview_hash:
        return PATCH_APPLY_BLOCKED_POLICY_PREVIEW_MISMATCH
    if tuple(policy.target_paths) != tuple(preview.target_paths):
        return PATCH_APPLY_BLOCKED_TARGET_MISMATCH
    if policy.status == PATCH_POLICY_BLOCK:
        return PATCH_APPLY_BLOCKED_POLICY_STATUS
    if policy.status not in (PATCH_POLICY_PASS, PATCH_POLICY_NEEDS_REVIEW):
        return PATCH_APPLY_BLOCKED_POLICY_STATUS
    if any(item.severity == "block" for item in policy.findings):
        return PATCH_APPLY_BLOCKED_POLICY_HARD_FINDING
    if expected_name is not None and policy.policy_profile_name != expected_name:
        return PATCH_APPLY_BLOCKED_POLICY_PROFILE_MISMATCH
    if expected_version is not None and policy.policy_profile_version != expected_version:
        return PATCH_APPLY_BLOCKED_POLICY_PROFILE_MISMATCH
    return None


def _preview_integrity_error(preview: PatchPreview) -> str | None:
    if not _full_hash(preview.preview_hash):
        return PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH
    material = {
        "schema_version": "AOIA_PATCH_PREVIEW_1A",
        "target_paths": list(preview.target_paths),
        "files": [item.to_dict() for item in preview.files],
        "total_file_count": preview.total_file_count,
        "total_proposed_size_bytes": preview.total_proposed_size_bytes,
        "total_proposed_char_count": preview.total_proposed_char_count,
        "risk_flags": list(preview.risk_flags),
    }
    if compute_patch_preview_hash(material) != preview.preview_hash:
        return PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH
    return None


def _expected_policy_hash(policy: PatchPolicyCheckResult) -> str:
    material = {
        "schema_version": "AOIA_PATCH_POLICY_1A",
        "status": policy.status,
        "policy_profile_name": policy.policy_profile_name,
        "policy_profile_version": policy.policy_profile_version,
        "patch_preview_hash": policy.patch_preview_hash,
        "target_paths": list(policy.target_paths),
        "file_count": policy.file_count,
        "scope_classification": policy.scope_classification,
        "findings": [item.to_dict() for item in policy.findings],
        "risk_flags": list(policy.risk_flags),
        "reason_codes": list(policy.reason_codes),
    }
    return compute_patch_policy_hash(material)


def _barrier_error(barrier: HumanPatchBarrierResult, policy_status: str) -> str | None:
    if not isinstance(barrier, HumanPatchBarrierResult):
        return PATCH_APPLY_BLOCKED_MISSING_BARRIER
    if barrier.status != PATCH_BARRIER_VERIFIED or not barrier.barrier_valid:
        if barrier.reason_code == PATCH_BARRIER_BLOCKED_HASH_MISMATCH:
            return PATCH_APPLY_BLOCKED_BARRIER_HASH_MISMATCH
        return PATCH_APPLY_BLOCKED_BARRIER_INVALID
    if not _full_hash(barrier.barrier_hash):
        return PATCH_APPLY_BLOCKED_BARRIER_HASH_MISSING
    if barrier.decision_value != PATCH_DECISION_APPROVE or not barrier.patch_approved:
        return PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE
    if barrier.policy_status != policy_status:
        return PATCH_APPLY_BLOCKED_BARRIER_INVALID
    return None


def _preflight_files(
    preview: PatchPreview,
    request: ControlledPatchApplyRequest,
) -> ControlledPatchApplyFileResult | None:
    if not isinstance(request.context, ControlWriteContext):
        return ControlledPatchApplyFileResult("", None, CONTROLLED_PATCH_FILE_BLOCKED, PATCH_APPLY_BLOCKED_MISSING_CONTEXT, "control write context is required", None, None)
    if not isinstance(request.proposed_contents, Mapping):
        return ControlledPatchApplyFileResult("", None, CONTROLLED_PATCH_FILE_BLOCKED, PATCH_APPLY_BLOCKED_MISSING_PROPOSED_CONTENT, "proposed content mapping is required", None, None)
    if not isinstance(request.gate_results, Mapping):
        return ControlledPatchApplyFileResult("", None, CONTROLLED_PATCH_FILE_BLOCKED, PATCH_APPLY_BLOCKED_MISSING_GATE, "gate evidence mapping is required", None, None)

    targets = tuple(file_preview.target_path for file_preview in preview.files)
    if tuple(preview.target_paths) != targets:
        return ControlledPatchApplyFileResult("", None, CONTROLLED_PATCH_FILE_BLOCKED, PATCH_APPLY_BLOCKED_TARGET_MISMATCH, "patch preview target list differs from file metadata", None, None)
    if len(set(targets)) != len(targets):
        return ControlledPatchApplyFileResult("", None, CONTROLLED_PATCH_FILE_BLOCKED, PATCH_APPLY_BLOCKED_DUPLICATE_TARGET, "duplicate target paths are blocked", None, None)

    for file_preview in preview.files:
        if file_preview.operation not in ("create", "update"):
            return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_UNSUPPORTED_OPERATION, "controlled patch apply supports create/update text files only")
        proposed_content = request.proposed_contents.get(file_preview.target_path)
        if not isinstance(proposed_content, str):
            return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_MISSING_PROPOSED_CONTENT, "reviewed proposed content is required")
        if file_preview.target_path not in request.gate_results:
            return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_MISSING_GATE, "per-file gate evidence is required")
        if _sha256(proposed_content) != file_preview.proposed_sha256:
            return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_PROPOSED_HASH_MISMATCH, "proposed content hash does not match patch preview")

        guard = validate_workspace_target_path(request.workspace_root, file_preview.target_path)
        if not guard.allowed:
            return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_WORKSPACE_GUARD, guard.reason)

        target = Path(guard.resolved_absolute_target_path or "")
        if file_preview.operation == "create":
            if target.exists():
                return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_CREATE_TARGET_EXISTS, "create target already exists")
        else:
            if not _full_hash(file_preview.original_sha256):
                return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISSING, "update requires reviewed original content hash")
            if not target.exists():
                return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_ORIGINAL_FILE_MISSING, "update target is missing")
            try:
                current = target.read_text(encoding="utf-8")
            except OSError:
                return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_ORIGINAL_FILE_MISSING, "update target cannot be read")
            if _sha256(current) != file_preview.original_sha256:
                return _file_blocked(file_preview, PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISMATCH, "target content changed after patch preview")
    return None


def _gated_writer_for_file(
    request: ControlledPatchApplyRequest,
    file_preview: PatchPreviewFile,
) -> ControlledPatchGatedWriter:
    allow_overwrite = file_preview.operation == "update"

    def gated_writer(**kwargs: Any) -> HumanDecisionGatedArtifactWriteResult:
        writer = request.gated_writer or write_artifact_after_human_gate
        return writer(
            **kwargs,
            artifact_writer=_artifact_writer(allow_overwrite),
            write_kill_switch_path=request.write_kill_switch_path,
            write_kill_switch_directory=request.write_kill_switch_directory,
        )

    return gated_writer


def _artifact_writer(allow_overwrite: bool) -> Callable[[SandboxArtifactRequest, str], SandboxArtifactResult]:
    def artifact_writer(request: SandboxArtifactRequest, workspace_root: str) -> SandboxArtifactResult:
        return write_sandbox_artifact(request, workspace_root, allow_overwrite=allow_overwrite)

    return artifact_writer


def _context_for_file(context: ControlWriteContext, file_preview: PatchPreviewFile) -> ControlWriteContext:
    suffix = file_preview.proposed_sha256[:12]
    return replace(
        context,
        sandbox_request_id=f"{context.sandbox_request_id}-{suffix}",
        sandbox_result_id=f"{context.sandbox_result_id}-{suffix}",
    )


def _original_content_for_artifact_preview(workspace_root: str, file_preview: PatchPreviewFile) -> str | None:
    if file_preview.operation != "update":
        return None
    guard = validate_workspace_target_path(workspace_root, file_preview.target_path)
    if not guard.allowed:
        return None
    try:
        return Path(guard.resolved_absolute_target_path or "").read_text(encoding="utf-8")
    except OSError:
        return None


def _file_blocked(file_preview: PatchPreviewFile, reason_code: str, reason: str) -> ControlledPatchApplyFileResult:
    return ControlledPatchApplyFileResult(
        target_path=file_preview.target_path,
        operation=file_preview.operation,
        status=CONTROLLED_PATCH_FILE_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        proposed_sha256=file_preview.proposed_sha256,
        original_sha256=file_preview.original_sha256,
    )


def _blocked(
    reason_code: str,
    reason: str,
    *,
    preview: PatchPreview | None = None,
    policy: PatchPolicyCheckResult | None = None,
    barrier: HumanPatchBarrierResult | None = None,
    file_results: tuple[ControlledPatchApplyFileResult, ...] = (),
) -> ControlledPatchApplyResult:
    return _result(
        status=CONTROLLED_PATCH_BLOCKED,
        reason_code=reason_code,
        reason=reason,
        preview=preview,
        policy=policy,
        barrier=barrier,
        file_results=file_results,
    )


def _result(
    *,
    status: str,
    reason_code: str,
    reason: str,
    preview: PatchPreview | None,
    policy: PatchPolicyCheckResult | None,
    barrier: HumanPatchBarrierResult | None,
    file_results: tuple[ControlledPatchApplyFileResult, ...],
) -> ControlledPatchApplyResult:
    target_paths = tuple(preview.target_paths) if preview is not None else ()
    material = {
        "schema_version": "AOIA_CONTROLLED_PATCH_APPLY_1A",
        "status": status,
        "patch_preview_hash": preview.preview_hash if preview is not None else None,
        "patch_policy_hash": policy.policy_hash if policy is not None else None,
        "patch_barrier_hash": barrier.barrier_hash if barrier is not None else None,
        "target_paths": list(target_paths),
        "file_results": [item.to_dict() for item in file_results],
        "reason_code": reason_code,
    }
    any_written = any(item.artifact_write_occurred for item in file_results)
    all_written = bool(file_results) and all(item.artifact_write_occurred for item in file_results)
    return ControlledPatchApplyResult(
        status=status,
        apply_hash=compute_controlled_patch_apply_hash(material),
        patch_preview_hash=preview.preview_hash if preview is not None else None,
        patch_policy_hash=policy.policy_hash if policy is not None else None,
        patch_barrier_hash=barrier.barrier_hash if barrier is not None else None,
        target_paths=target_paths,
        file_results=file_results,
        reason_code=reason_code,
        reason=reason,
        partial_apply=any_written and not all_written,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _full_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) == 64 and all(character in _SHA256_HEX for character in text):
        return text
    return None


def _stable_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
