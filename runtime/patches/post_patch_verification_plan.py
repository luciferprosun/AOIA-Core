from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from runtime.patches.controlled_patch_apply import (
    CONTROLLED_PATCH_APPLIED,
    CONTROLLED_PATCH_FILE_APPLIED,
    CONTROLLED_PATCH_PARTIAL,
    ControlledPatchApplyResult,
    compute_controlled_patch_apply_hash,
)
from runtime.patches.patch_barrier import (
    PATCH_BARRIER_VERIFIED,
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
    PatchPreviewResult,
    compute_patch_preview_hash,
)


POST_PATCH_VERIFICATION_READY = "READY"
POST_PATCH_VERIFICATION_BLOCKED = "BLOCKED"

POST_PATCH_VERIFICATION_BLOCKED_MISSING_APPLY = "POST_PATCH_VERIFICATION_BLOCKED_MISSING_APPLY"
POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW = "POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW"
POST_PATCH_VERIFICATION_BLOCKED_MISSING_POLICY = "POST_PATCH_VERIFICATION_BLOCKED_MISSING_POLICY"
POST_PATCH_VERIFICATION_BLOCKED_MISSING_BARRIER = "POST_PATCH_VERIFICATION_BLOCKED_MISSING_BARRIER"
POST_PATCH_VERIFICATION_BLOCKED_MALFORMED_INPUT = "POST_PATCH_VERIFICATION_BLOCKED_MALFORMED_INPUT"
POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM = "POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM"
POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED = "POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED"
POST_PATCH_VERIFICATION_BLOCKED_PARTIAL_APPLY = "POST_PATCH_VERIFICATION_BLOCKED_PARTIAL_APPLY"
POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_CONTENT_HASH_MISMATCH = "POST_PATCH_VERIFICATION_BLOCKED_CONTENT_HASH_MISMATCH"
POST_PATCH_VERIFICATION_BLOCKED_POLICY_STATUS = "POST_PATCH_VERIFICATION_BLOCKED_POLICY_STATUS"

CHECK_KIND_COMPILE = "compile"
CHECK_KIND_TEST = "test"
CHECK_KIND_STATIC = "static"
CHECK_KIND_STYLE = "style"
CHECK_KIND_REVIEW = "review"

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
_PATCH_REGRESSION_CHECKS = (
    ("step-21-patch-preview-regression", "tests.test_diff_based_edit_proposal_patch_preview_1a", "patch_preview"),
    ("step-22-patch-policy-regression", "tests.test_patch_local_policy_check_1a", "patch_policy"),
    ("step-23-human-patch-barrier-regression", "tests.test_human_patch_barrier_1a", "human_patch_barrier"),
    ("step-24-controlled-patch-apply-regression", "tests.test_controlled_patch_apply_1a", "controlled_patch_apply"),
)
_SAFETY_REGRESSION_CHECKS = (
    ("step-12-authority-bypass-regression", "tests.test_authority_bypass_adversarial_1a", "authority_boundary"),
    ("step-13-durable-ledger-regression", "tests.test_durable_audit_ledger_1a", "durable_ledger"),
    ("step-14-static-boundary-regression", "tests.test_static_capability_boundary_1a", "static_boundary"),
    ("step-15-kill-switch-regression", "tests.test_global_write_kill_switch_1a", "write_kill_switch"),
    ("step-16-workspace-guard-regression", "tests.test_workspace_guard_toctou_1a", "workspace_guard"),
    ("step-17-full-chain-fail-closed-regression", "tests.test_full_chain_fail_closed_1a", "fail_closed_chain"),
)


@dataclass(frozen=True)
class PostPatchVerificationCheck:
    check_id: str
    check_kind: str
    command: str | None
    test_target: str | None
    reason: str
    related_target_paths: tuple[str, ...]
    required: bool
    risk_category: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "related_target_paths", tuple(self.related_target_paths))

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_kind": self.check_kind,
            "command": self.command,
            "test_target": self.test_target,
            "reason": self.reason,
            "related_target_paths": list(self.related_target_paths),
            "required": self.required,
            "risk_category": self.risk_category,
        }


@dataclass(frozen=True)
class PostPatchVerificationPlan:
    plan_id: str
    plan_hash: str
    status: str
    apply_hash: str
    patch_preview_hash: str
    patch_policy_hash: str
    patch_barrier_hash: str
    target_paths: tuple[str, ...]
    applied_content_hashes: tuple[tuple[str, str], ...]
    policy_status: str
    apply_status: str
    scope_classification: str
    checks: tuple[PostPatchVerificationCheck, ...]
    reason_codes: tuple[str, ...]
    risk_flags: tuple[str, ...]
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
        object.__setattr__(self, "applied_content_hashes", tuple(tuple(item) for item in self.applied_content_hashes))
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "status": self.status,
            "apply_hash": self.apply_hash,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "patch_barrier_hash": self.patch_barrier_hash,
            "target_paths": list(self.target_paths),
            "applied_content_hashes": [list(item) for item in self.applied_content_hashes],
            "policy_status": self.policy_status,
            "apply_status": self.apply_status,
            "scope_classification": self.scope_classification,
            "checks": [item.to_dict() for item in self.checks],
            "reason_codes": list(self.reason_codes),
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


@dataclass(frozen=True)
class PostPatchVerificationPlanResult:
    status: str
    plan_ready: bool
    plan_hash: str
    apply_hash: str | None
    patch_preview_hash: str | None
    patch_policy_hash: str | None
    patch_barrier_hash: str | None
    target_paths: tuple[str, ...]
    checks: tuple[PostPatchVerificationCheck, ...]
    reason_codes: tuple[str, ...]
    reason: str
    risk_flags: tuple[str, ...] = ()
    plan: PostPatchVerificationPlan | None = None
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
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        object.__setattr__(self, "plan_ready", self.status == POST_PATCH_VERIFICATION_READY)
        for field_name in _AUTHORITY_FIELDS:
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "plan_ready": self.plan_ready,
            "plan_hash": self.plan_hash,
            "apply_hash": self.apply_hash,
            "patch_preview_hash": self.patch_preview_hash,
            "patch_policy_hash": self.patch_policy_hash,
            "patch_barrier_hash": self.patch_barrier_hash,
            "target_paths": list(self.target_paths),
            "checks": [item.to_dict() for item in self.checks],
            "reason_codes": list(self.reason_codes),
            "reason": self.reason,
            "risk_flags": list(self.risk_flags),
            "plan": self.plan.to_dict() if self.plan is not None else None,
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


def canonical_post_patch_verification_plan_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_post_patch_verification_plan_hash(value: Any) -> str:
    return hashlib.sha256(canonical_post_patch_verification_plan_json(value).encode("utf-8")).hexdigest()


def build_post_patch_verification_plan(
    *,
    apply_result: ControlledPatchApplyResult | None,
    patch_preview: PatchPreview | PatchPreviewResult | None,
    patch_policy: PatchPolicyCheckResult | None,
    human_patch_barrier: HumanPatchBarrierResult | Mapping[str, Any] | None,
    allow_partial_apply: bool = False,
) -> PostPatchVerificationPlanResult:
    preview, preview_error = _coerce_preview(patch_preview)
    if not isinstance(apply_result, ControlledPatchApplyResult):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_MISSING_APPLY, "controlled patch apply result is required")
    if _has_authority_claim(apply_result):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM, "apply result contains authority-like claims", apply_result=apply_result)
    if preview_error is not None:
        return _blocked(preview_error, "valid patch preview evidence is required", apply_result=apply_result)
    assert preview is not None
    if _has_authority_claim(preview):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM, "patch preview contains authority-like claims", apply_result=apply_result, preview=preview)
    if _preview_integrity_error(preview):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH, "patch preview hash does not match deterministic metadata", apply_result=apply_result, preview=preview)

    if not isinstance(patch_policy, PatchPolicyCheckResult):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_MISSING_POLICY, "patch policy result is required", apply_result=apply_result, preview=preview)
    if _has_authority_claim(patch_policy):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM, "patch policy contains authority-like claims", apply_result=apply_result, preview=preview, policy=patch_policy)
    policy_error = _policy_error(preview, patch_policy)
    if policy_error is not None:
        return _blocked(policy_error, "patch policy evidence is stale or malformed", apply_result=apply_result, preview=preview, policy=patch_policy)

    if human_patch_barrier is None:
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_MISSING_BARRIER, "human patch barrier result is required", apply_result=apply_result, preview=preview, policy=patch_policy)
    verified_barrier = verify_human_patch_barrier(
        human_patch_barrier,
        expected_patch_preview_hash=preview.preview_hash,
        expected_patch_policy_hash=patch_policy.policy_hash,
        expected_target_paths=preview.target_paths,
        expected_policy_status=patch_policy.status,
    )
    if verified_barrier.status != PATCH_BARRIER_VERIFIED or not verified_barrier.barrier_valid:
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH, "human patch barrier is stale or malformed", apply_result=apply_result, preview=preview, policy=patch_policy, barrier=verified_barrier)
    if _has_authority_claim(verified_barrier):
        return _blocked(POST_PATCH_VERIFICATION_BLOCKED_AUTHORITY_CLAIM, "human patch barrier contains authority-like claims", apply_result=apply_result, preview=preview, policy=patch_policy, barrier=verified_barrier)

    apply_error = _apply_error(apply_result, preview, patch_policy, verified_barrier, allow_partial_apply)
    if apply_error is not None:
        return _blocked(apply_error, "controlled patch apply evidence is stale, failed, partial, or mismatched", apply_result=apply_result, preview=preview, policy=patch_policy, barrier=verified_barrier)

    target_paths = tuple(apply_result.target_paths)
    content_hashes = _content_hashes(apply_result)
    checks = _verification_checks(target_paths, patch_policy)
    risk_flags = tuple(sorted(set((*patch_policy.risk_flags, *preview.risk_flags, *_check_risk_flags(checks)))))
    reason_codes = ("POST_PATCH_VERIFICATION_READY",)
    material = _plan_material(
        status=POST_PATCH_VERIFICATION_READY,
        apply_hash=apply_result.apply_hash or "",
        preview_hash=preview.preview_hash,
        policy_hash=patch_policy.policy_hash,
        barrier_hash=verified_barrier.barrier_hash or "",
        target_paths=target_paths,
        content_hashes=content_hashes,
        policy_status=patch_policy.status,
        apply_status=apply_result.status,
        scope_classification=patch_policy.scope_classification,
        checks=checks,
        reason_codes=reason_codes,
        risk_flags=risk_flags,
    )
    plan_hash = compute_post_patch_verification_plan_hash(material)
    plan = PostPatchVerificationPlan(
        plan_id="post-patch-verification-plan-" + plan_hash[:24],
        plan_hash=plan_hash,
        status=POST_PATCH_VERIFICATION_READY,
        apply_hash=apply_result.apply_hash or "",
        patch_preview_hash=preview.preview_hash,
        patch_policy_hash=patch_policy.policy_hash,
        patch_barrier_hash=verified_barrier.barrier_hash or "",
        target_paths=target_paths,
        applied_content_hashes=content_hashes,
        policy_status=patch_policy.status,
        apply_status=apply_result.status,
        scope_classification=patch_policy.scope_classification,
        checks=checks,
        reason_codes=reason_codes,
        risk_flags=risk_flags,
    )
    return PostPatchVerificationPlanResult(
        status=POST_PATCH_VERIFICATION_READY,
        plan_ready=True,
        plan_hash=plan_hash,
        apply_hash=apply_result.apply_hash,
        patch_preview_hash=preview.preview_hash,
        patch_policy_hash=patch_policy.policy_hash,
        patch_barrier_hash=verified_barrier.barrier_hash,
        target_paths=target_paths,
        checks=checks,
        reason_codes=reason_codes,
        reason="post-patch verification plan is deterministic metadata only and grants no execution authority",
        risk_flags=risk_flags,
        plan=plan,
    )


def _coerce_preview(value: PatchPreview | PatchPreviewResult | None) -> tuple[PatchPreview | None, str | None]:
    if value is None:
        return None, POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW
    if isinstance(value, PatchPreviewResult):
        if value.patch_preview is None:
            return None, POST_PATCH_VERIFICATION_BLOCKED_MISSING_PREVIEW
        if value.status != PATCH_PREVIEW_READY or value.preview_ready is not True:
            return None, POST_PATCH_VERIFICATION_BLOCKED_MALFORMED_INPUT
        if value.preview_hash != value.patch_preview.preview_hash:
            return None, POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH
        return value.patch_preview, None
    if isinstance(value, PatchPreview):
        if value.status != PATCH_PREVIEW_READY:
            return None, POST_PATCH_VERIFICATION_BLOCKED_MALFORMED_INPUT
        return value, None
    return None, POST_PATCH_VERIFICATION_BLOCKED_MALFORMED_INPUT


def _apply_error(
    apply_result: ControlledPatchApplyResult,
    preview: PatchPreview,
    policy: PatchPolicyCheckResult,
    barrier: HumanPatchBarrierResult,
    allow_partial_apply: bool,
) -> str | None:
    if apply_result.status == CONTROLLED_PATCH_PARTIAL or apply_result.partial_apply:
        return None if allow_partial_apply else POST_PATCH_VERIFICATION_BLOCKED_PARTIAL_APPLY
    if apply_result.status != CONTROLLED_PATCH_APPLIED or not apply_result.patch_applied:
        return POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED
    if not _full_hash(apply_result.apply_hash):
        return POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH
    if _expected_apply_hash(apply_result) != apply_result.apply_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_APPLY_HASH_MISMATCH
    if apply_result.patch_preview_hash != preview.preview_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH
    if apply_result.patch_policy_hash != policy.policy_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH
    if apply_result.patch_barrier_hash != barrier.barrier_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_BARRIER_HASH_MISMATCH
    if tuple(apply_result.target_paths) != tuple(preview.target_paths):
        return POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH
    file_targets = tuple(item.target_path for item in apply_result.file_results)
    if file_targets != tuple(preview.target_paths):
        return POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH
    preview_hashes = {item.target_path: item.proposed_sha256 for item in preview.files}
    for item in apply_result.file_results:
        if item.status != CONTROLLED_PATCH_FILE_APPLIED or not item.artifact_write_occurred:
            return POST_PATCH_VERIFICATION_BLOCKED_APPLY_FAILED
        if preview_hashes.get(item.target_path) != item.proposed_sha256:
            return POST_PATCH_VERIFICATION_BLOCKED_CONTENT_HASH_MISMATCH
    return None


def _preview_integrity_error(preview: PatchPreview) -> bool:
    if not _full_hash(preview.preview_hash):
        return True
    material = {
        "schema_version": "AOIA_PATCH_PREVIEW_1A",
        "target_paths": list(preview.target_paths),
        "files": [item.to_dict() for item in preview.files],
        "total_file_count": preview.total_file_count,
        "total_proposed_size_bytes": preview.total_proposed_size_bytes,
        "total_proposed_char_count": preview.total_proposed_char_count,
        "risk_flags": list(preview.risk_flags),
    }
    return compute_patch_preview_hash(material) != preview.preview_hash


def _policy_error(preview: PatchPreview, policy: PatchPolicyCheckResult) -> str | None:
    if policy.status not in (PATCH_POLICY_PASS, PATCH_POLICY_NEEDS_REVIEW, PATCH_POLICY_BLOCK):
        return POST_PATCH_VERIFICATION_BLOCKED_POLICY_STATUS
    if policy.status == PATCH_POLICY_BLOCK:
        return POST_PATCH_VERIFICATION_BLOCKED_POLICY_STATUS
    if not _full_hash(policy.policy_hash) or _expected_policy_hash(policy) != policy.policy_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_POLICY_HASH_MISMATCH
    if policy.patch_preview_hash != preview.preview_hash:
        return POST_PATCH_VERIFICATION_BLOCKED_PREVIEW_HASH_MISMATCH
    if tuple(policy.target_paths) != tuple(preview.target_paths):
        return POST_PATCH_VERIFICATION_BLOCKED_TARGET_MISMATCH
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


def _expected_apply_hash(apply_result: ControlledPatchApplyResult) -> str:
    material = {
        "schema_version": "AOIA_CONTROLLED_PATCH_APPLY_1A",
        "status": apply_result.status,
        "patch_preview_hash": apply_result.patch_preview_hash,
        "patch_policy_hash": apply_result.patch_policy_hash,
        "patch_barrier_hash": apply_result.patch_barrier_hash,
        "target_paths": list(apply_result.target_paths),
        "file_results": [item.to_dict() for item in apply_result.file_results],
        "reason_code": apply_result.reason_code,
    }
    return compute_controlled_patch_apply_hash(material)


def _verification_checks(
    target_paths: tuple[str, ...],
    policy: PatchPolicyCheckResult,
) -> tuple[PostPatchVerificationCheck, ...]:
    checks: dict[str, PostPatchVerificationCheck] = {}

    def add(check: PostPatchVerificationCheck) -> None:
        checks[check.check_id] = check

    add(
        PostPatchVerificationCheck(
            check_id="diff-check-style",
            check_kind=CHECK_KIND_STYLE,
            command="git diff --check",
            test_target=None,
            reason="review metadata recommends whitespace/style diff validation after patch application",
            related_target_paths=target_paths,
            required=True,
            risk_category="lightweight",
        )
    )
    if _docs_only(target_paths):
        add(
            PostPatchVerificationCheck(
                check_id="docs-only-human-review",
                check_kind=CHECK_KIND_REVIEW,
                command=None,
                test_target="human-review:docs-only-patch",
                reason="docs-only patches still require conservative review metadata and do not reduce control assumptions",
                related_target_paths=target_paths,
                required=True,
                risk_category="docs",
            )
        )
    if any(path.startswith("runtime/") for path in target_paths):
        add(
            PostPatchVerificationCheck(
                check_id="compileall-runtime-tests",
                check_kind=CHECK_KIND_COMPILE,
                command="python3 -m compileall runtime tests",
                test_target=None,
                reason="runtime targets require Python compile validation metadata",
                related_target_paths=tuple(path for path in target_paths if path.startswith("runtime/")),
                required=True,
                risk_category="runtime",
            )
        )
        add(
            PostPatchVerificationCheck(
                check_id="runtime-focused-tests",
                check_kind=CHECK_KIND_TEST,
                command="PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p \"test*.py\" -v",
                test_target="tests",
                reason="runtime target touched; focused test selection must be reviewed before execution",
                related_target_paths=tuple(path for path in target_paths if path.startswith("runtime/")),
                required=True,
                risk_category="runtime",
            )
        )
    for test_module in _test_modules_for_paths(target_paths):
        add(
            PostPatchVerificationCheck(
                check_id="focused-" + test_module.replace(".", "-"),
                check_kind=CHECK_KIND_TEST,
                command=f"PYTHONPATH=runtime:. python3 -m unittest {test_module} -v",
                test_target=test_module,
                reason="test target touched; focused test metadata should cover the changed test module",
                related_target_paths=tuple(path for path in target_paths if _test_module_for_path(path) == test_module),
                required=True,
                risk_category="tests",
            )
        )
    if len(target_paths) > 1 or any(path.startswith(("runtime/", "tests/")) for path in target_paths):
        add(_full_suite_check(target_paths, "multi-file or code/test patch requires full-suite recommendation metadata"))
    if any(path.startswith("runtime/patches/") for path in target_paths):
        for check_id, test_target, risk_category in _PATCH_REGRESSION_CHECKS:
            add(_test_check(check_id, test_target, "patch subsystem target touched; include Step 21-24 regression metadata", target_paths, risk_category))
    if any(_safety_like_path(path) for path in target_paths):
        for check_id, test_target, risk_category in _SAFETY_REGRESSION_CHECKS:
            add(_test_check(check_id, test_target, "safety/control/write/gate boundary target touched; include Step 12-17 regression metadata", target_paths, risk_category))
    if any(_provider_critic_path(path) for path in target_paths):
        add(_test_check("provider-critic-regression", "tests.test_provider_critic_1a", "provider/critic target touched; include provider critic regression metadata", target_paths, "provider_critic"))
        add(_test_check("provider-e-inert-critic-regression", "tests.test_provider_e_inert_critic_review", "provider/critic target touched; include inert critic regression metadata", target_paths, "provider_critic"))
    if _high_risk_policy(policy):
        add(
            PostPatchVerificationCheck(
                check_id="static-capability-boundary-check",
                check_kind=CHECK_KIND_STATIC,
                command="PYTHONPATH=runtime:. python3 -m unittest tests.test_static_capability_boundary_1a -v",
                test_target="tests.test_static_capability_boundary_1a",
                reason="high-risk policy findings require static capability boundary check metadata",
                related_target_paths=target_paths,
                required=True,
                risk_category="static_boundary",
            )
        )
    if "full-unittest-discovery" not in checks and not _docs_only(target_paths):
        add(_full_suite_check(target_paths, "non-doc patch receives conservative full-suite recommendation metadata"))
    return tuple(checks[key] for key in sorted(checks))


def _test_check(
    check_id: str,
    test_target: str,
    reason: str,
    target_paths: tuple[str, ...],
    risk_category: str,
) -> PostPatchVerificationCheck:
    return PostPatchVerificationCheck(
        check_id=check_id,
        check_kind=CHECK_KIND_TEST,
        command=f"PYTHONPATH=runtime:. python3 -m unittest {test_target} -v",
        test_target=test_target,
        reason=reason,
        related_target_paths=target_paths,
        required=True,
        risk_category=risk_category,
    )


def _full_suite_check(target_paths: tuple[str, ...], reason: str) -> PostPatchVerificationCheck:
    return PostPatchVerificationCheck(
        check_id="full-unittest-discovery",
        check_kind=CHECK_KIND_TEST,
        command="PYTHONPATH=runtime:. python3 -m unittest discover -s tests -p \"test*.py\" -v",
        test_target="tests",
        reason=reason,
        related_target_paths=target_paths,
        required=True,
        risk_category="full_suite",
    )


def _test_modules_for_paths(target_paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({module for path in target_paths if (module := _test_module_for_path(path)) is not None}))


def _test_module_for_path(path: str) -> str | None:
    if not path.startswith("tests/") or not path.endswith(".py"):
        return None
    stem = PurePosixPath(path).with_suffix("").as_posix().replace("/", ".")
    return stem


def _docs_only(target_paths: tuple[str, ...]) -> bool:
    return bool(target_paths) and all(path.startswith("docs/") or path.endswith(".md") for path in target_paths)


def _safety_like_path(path: str) -> bool:
    lowered = path.casefold()
    markers = (
        "runtime/control_write.py",
        "runtime/human_decision_gated_artifact_write.py",
        "runtime/safety/",
        "runtime/audit/",
        "runtime/bridges/",
        "authority",
        "gate",
        "sandbox",
        "kill_switch",
        "workspace_guard",
    )
    return any(marker in lowered for marker in markers)


def _provider_critic_path(path: str) -> bool:
    lowered = path.casefold()
    return "provider" in lowered and "critic" in lowered


def _high_risk_policy(policy: PatchPolicyCheckResult) -> bool:
    high_risk_markers = ("high_risk", "authority", "capability", "boundary", "provider", "gate", "control", "sandbox")
    if any(finding.severity == "block" for finding in policy.findings):
        return True
    return any(
        any(marker in finding.code.casefold() or marker in finding.scope.casefold() for marker in high_risk_markers)
        for finding in policy.findings
    )


def _check_risk_flags(checks: tuple[PostPatchVerificationCheck, ...]) -> tuple[str, ...]:
    return tuple(sorted({check.risk_category for check in checks}))


def _content_hashes(apply_result: ControlledPatchApplyResult) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((item.target_path, item.proposed_sha256 or "") for item in apply_result.file_results))


def _plan_material(
    *,
    status: str,
    apply_hash: str | None,
    preview_hash: str | None,
    policy_hash: str | None,
    barrier_hash: str | None,
    target_paths: tuple[str, ...],
    content_hashes: tuple[tuple[str, str], ...],
    policy_status: str | None,
    apply_status: str | None,
    scope_classification: str | None,
    checks: tuple[PostPatchVerificationCheck, ...],
    reason_codes: tuple[str, ...],
    risk_flags: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema_version": "AOIA_POST_PATCH_VERIFICATION_PLAN_1A",
        "status": status,
        "apply_hash": apply_hash,
        "patch_preview_hash": preview_hash,
        "patch_policy_hash": policy_hash,
        "patch_barrier_hash": barrier_hash,
        "target_paths": list(target_paths),
        "applied_content_hashes": [list(item) for item in content_hashes],
        "policy_status": policy_status,
        "apply_status": apply_status,
        "scope_classification": scope_classification,
        "checks": [item.to_dict() for item in checks],
        "reason_codes": list(reason_codes),
        "risk_flags": list(risk_flags),
    }


def _blocked(
    reason_code: str,
    reason: str,
    *,
    apply_result: ControlledPatchApplyResult | None = None,
    preview: PatchPreview | None = None,
    policy: PatchPolicyCheckResult | None = None,
    barrier: HumanPatchBarrierResult | None = None,
) -> PostPatchVerificationPlanResult:
    target_paths = tuple(apply_result.target_paths) if apply_result is not None else tuple(preview.target_paths) if preview is not None else ()
    material = _plan_material(
        status=POST_PATCH_VERIFICATION_BLOCKED,
        apply_hash=apply_result.apply_hash if apply_result is not None else None,
        preview_hash=preview.preview_hash if preview is not None else None,
        policy_hash=policy.policy_hash if policy is not None else None,
        barrier_hash=barrier.barrier_hash if barrier is not None else None,
        target_paths=target_paths,
        content_hashes=_content_hashes(apply_result) if apply_result is not None else (),
        policy_status=policy.status if policy is not None else None,
        apply_status=apply_result.status if apply_result is not None else None,
        scope_classification=policy.scope_classification if policy is not None else None,
        checks=(),
        reason_codes=(reason_code,),
        risk_flags=(),
    )
    return PostPatchVerificationPlanResult(
        status=POST_PATCH_VERIFICATION_BLOCKED,
        plan_ready=False,
        plan_hash=compute_post_patch_verification_plan_hash(material),
        apply_hash=apply_result.apply_hash if apply_result is not None else None,
        patch_preview_hash=preview.preview_hash if preview is not None else None,
        patch_policy_hash=policy.policy_hash if policy is not None else None,
        patch_barrier_hash=barrier.barrier_hash if barrier is not None else None,
        target_paths=target_paths,
        checks=(),
        reason_codes=(reason_code,),
        reason=reason,
    )


def _has_authority_claim(value: Any) -> bool:
    return any(getattr(value, field_name, False) is not False for field_name in _AUTHORITY_FIELDS)


def _full_hash(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip().lower()
        if len(text) == 64 and all(character in _SHA256_HEX for character in text):
            return text
    return None


def _stable_json_value(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _stable_json_value(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _stable_json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple | list):
        return [_stable_json_value(item) for item in value]
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
