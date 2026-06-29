from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.execution.human_execution_barrier import (
    HumanDecisionSource,
    HumanDecisionVerdict,
    HumanExecutionBarrierRequest,
    HumanExecutionSourceTrust,
    evaluate_human_execution_barrier,
)
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, create_git_state_checkpoint
from runtime.git_ops.git_commit_barrier import (
    GIT_COMMIT_BARRIER_BLOCKED,
    GIT_COMMIT_BARRIER_BLOCKED_AUTHORITY_CLAIM,
    GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH,
    GIT_COMMIT_BARRIER_BLOCKED_HUMAN_BARRIER_NOT_PASSED,
    GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_HASH_MISMATCH,
    GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_MISSING,
    GIT_COMMIT_BARRIER_BLOCKED_INVALID_COMMIT_PREVIEW,
    GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER,
    GIT_COMMIT_BARRIER_BLOCKED_UNSAFE_RISK_FLAG,
    GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE,
    GIT_COMMIT_BARRIER_ELIGIBLE,
    GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY,
    GitCommitBarrierRequest,
    evaluate_git_commit_barrier,
)
from runtime.git_ops.git_commit_preview import GitCommitPreviewRequest, create_git_commit_preview
from runtime.git_ops.git_governance import GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.git_ops.git_write_preview import GitWriteIntent, GitWritePreviewRequest, create_git_write_preview


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMIT_BARRIER_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_commit_barrier.py"
DECISION_HASH = "e" * 64
SANDBOX_HASH = "b" * 64
POLICY_HASH = "c" * 64
CONTROLLED_REQUEST_HASH = "d" * 64
AUTHORITY_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "git_write_authority_granted",
    "git_commit_authority_granted",
    "git_push_authority_granted",
    "provider_authority_granted",
    "execution_authority_granted",
)
EFFECT_FIELDS = (
    "commit_performed",
    "push_performed",
    "subprocess_started",
    "shell_invoked",
    "command_executed",
    "network_called",
    "github_called",
    "provider_called",
    "env_read",
    "api_key_loaded",
    "approval_created",
    "gate_changed",
    "control_write_changed",
)


class GitCommitBarrier1ATests(unittest.TestCase):
    def test_valid_hash_bound_human_barrier_creates_metadata_only_eligibility(self):
        preview = self.commit_preview()
        result = self.barrier_result(preview=preview)

        self.assertEqual(GIT_COMMIT_BARRIER_ELIGIBLE, result.status)
        self.assertTrue(result.eligible_for_controlled_commit)
        self.assertEqual(preview.commit_preview_hash, result.commit_preview_hash)
        self.assertIn(GIT_COMMIT_BARRIER_ELIGIBLE_METADATA_ONLY, result.reason_codes)
        self.assert_authority_and_effects_false(result)

    def test_missing_human_barrier_blocks_commit_eligibility(self):
        result = evaluate_git_commit_barrier(GitCommitBarrierRequest(commit_preview=self.commit_preview(), human_barrier=None))

        self.assertEqual(GIT_COMMIT_BARRIER_BLOCKED, result.status)
        self.assertFalse(result.eligible_for_controlled_commit)
        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_MISSING_HUMAN_BARRIER, result.reason_codes)
        self.assert_authority_and_effects_false(result)

    def test_non_passed_human_barrier_blocks_commit_eligibility(self):
        preview = self.commit_preview()
        rejected = self.human_barrier(preview, human_decision_verdict=HumanDecisionVerdict.REJECT)
        result = self.barrier_result(preview=preview, human_barrier=rejected)

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_BARRIER_NOT_PASSED, result.reason_codes)
        self.assertFalse(result.eligible_for_controlled_commit)
        self.assert_authority_and_effects_false(result)

    def test_hash_mismatch_between_preview_and_barrier_blocks(self):
        preview = self.commit_preview()
        barrier = self.human_barrier(preview)
        tampered = {
            **barrier,
            "requested_command_hash": "f" * 64,
            "human_decision_binds_to_command_hash": "f" * 64,
            "human_decision_binds_to_commit_preview_hash": "f" * 64,
        }
        result = self.barrier_result(preview=preview, human_barrier=tampered)

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH, result.reason_codes)
        self.assert_authority_and_effects_false(result)

    def test_invalid_or_tampered_commit_preview_blocks(self):
        preview = self.commit_preview()
        tampered = {**preview.to_dict(), "branch_name": "other"}
        result = self.barrier_result(preview=tampered, human_barrier=self.human_barrier(preview))

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_INVALID_COMMIT_PREVIEW, result.reason_codes)
        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_COMMIT_PREVIEW_HASH_MISMATCH, result.reason_codes)
        self.assert_authority_and_effects_false(result)

    def test_missing_or_mismatched_human_decision_hash_blocks(self):
        preview = self.commit_preview()
        missing = {**self.human_barrier(preview), "human_decision_hash": None}
        mismatch = self.barrier_result(preview=preview, expected_human_decision_hash="f" * 64)

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_MISSING, self.barrier_result(preview=preview, human_barrier=missing).reason_codes)
        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_HUMAN_DECISION_HASH_MISMATCH, mismatch.reason_codes)

    def test_preview_metadata_policy_and_risk_flags_do_not_self_authorize(self):
        preview = self.commit_preview()
        barrier = self.human_barrier(preview)
        result = self.barrier_result(
            preview=preview,
            human_barrier=barrier,
            claims={"can_commit": True},
        )

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_AUTHORITY_CLAIM, result.reason_codes)
        self.assertFalse(result.eligible_for_controlled_commit)
        self.assert_authority_and_effects_false(result)

    def test_untrusted_source_and_unsafe_risk_flags_block(self):
        preview = self.commit_preview()
        untrusted = self.barrier_result(preview=preview, source_trust="UNTRUSTED_PROVIDER_OUTPUT")
        unsafe = self.barrier_result(
            preview={**preview.to_dict(), "risk_flags": ("GITHUB_PUSH",)},
            human_barrier=self.human_barrier(preview),
        )

        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_UNTRUSTED_BARRIER_SOURCE, untrusted.reason_codes)
        self.assertIn(GIT_COMMIT_BARRIER_BLOCKED_UNSAFE_RISK_FLAG, unsafe.reason_codes)
        self.assert_authority_and_effects_false(untrusted)
        self.assert_authority_and_effects_false(unsafe)

    def test_barrier_result_is_deterministic_and_hash_bound(self):
        preview = self.commit_preview()
        first = self.barrier_result(preview=preview)
        second = self.barrier_result(preview=preview)
        changed_preview = self.commit_preview(commit_message="feat(git): different")
        changed = self.barrier_result(preview=changed_preview)

        self.assertEqual(first.commit_barrier_hash, second.commit_barrier_hash)
        self.assertNotEqual(first.commit_barrier_hash, changed.commit_barrier_hash)

    def test_commit_barrier_module_imports_no_execution_network_provider_env_or_github_libs(self):
        scan = scan_module(COMMIT_BARRIER_MODULE)
        forbidden_import_prefixes = (
            "subprocess",
            "socket",
            "ssl",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "GitPython",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "ollama",
            "pip",
            "venv",
            "os",
            "runtime.execution",
        )

        self.assertEqual([], [item for item in scan.imports if matches_any_prefix(item, forbidden_import_prefixes)])
        self.assertEqual([], [item for item in scan.calls if item in {"subprocess.run", "eval", "exec"}])
        source = COMMIT_BARRIER_MODULE.read_text(encoding="utf-8").casefold()
        for forbidden in ("shell=true", "api.github.com", "os.environ", "getenv", "git commit", "git push"):
            self.assertNotIn(forbidden, source)

    def barrier_result(self, *, preview, human_barrier=None, expected_human_decision_hash=DECISION_HASH, source_trust="USER_SUPPLIED", claims=None):
        if human_barrier is None:
            human_barrier = self.human_barrier(preview)
        return evaluate_git_commit_barrier(
            GitCommitBarrierRequest(
                commit_preview=preview,
                human_barrier=human_barrier,
                expected_commit_preview_hash=preview.commit_preview_hash if hasattr(preview, "commit_preview_hash") else None,
                expected_human_decision_hash=expected_human_decision_hash,
                source_trust=source_trust,
                claims=claims,
            )
        )

    def human_barrier(self, preview, **overrides):
        request = HumanExecutionBarrierRequest(
            requested_execution_kind="LOCAL_GIT_COMMIT_PREVIEW_BARRIER",
            requested_command=f"commit-preview:{preview.commit_preview_hash}",
            requested_command_hash=preview.commit_preview_hash,
            source_trust=HumanExecutionSourceTrust.USER_SUPPLIED,
            human_decision_id="decision-git-commit",
            human_decision_hash=DECISION_HASH,
            human_decision_verdict=HumanDecisionVerdict.APPROVE,
            human_decision_source=HumanDecisionSource.HUMAN_OPERATOR,
            human_decision_binds_to_command_hash=preview.commit_preview_hash,
            human_decision_binds_to_test_runner_control_hash=preview.commit_preview_hash,
            human_decision_binds_to_sandbox_envelope_hash=SANDBOX_HASH,
            human_decision_binds_to_policy_check_hash=POLICY_HASH,
            human_decision_binds_to_controlled_execution_request_hash=CONTROLLED_REQUEST_HASH,
            source_test_runner_control_id="commit-preview-control",
            source_test_runner_control_hash=preview.commit_preview_hash,
            source_test_runner_control_status="REVIEW_REQUIRED",
            source_sandbox_envelope_id="commit-preview-sandbox",
            source_sandbox_envelope_hash=SANDBOX_HASH,
            source_sandbox_envelope_status="REVIEW_REQUIRED",
            source_policy_check_id="commit-preview-policy",
            source_policy_check_hash=POLICY_HASH,
            source_policy_check_status="REVIEW_REQUIRED",
            source_controlled_execution_request_hash=CONTROLLED_REQUEST_HASH,
        )
        result = evaluate_human_execution_barrier(replace(request, **overrides))
        data = result.to_dict()
        data["human_decision_binds_to_commit_preview_hash"] = preview.commit_preview_hash
        data["human_decision_binds_to_command_hash"] = preview.commit_preview_hash
        data["risk_flags"] = ()
        return data

    def commit_preview(self, *, commit_message="feat(git): add commit barrier"):
        checkpoint = self.checkpoint()
        write_preview = create_git_write_preview(
            GitWritePreviewRequest(
                checkpoint=checkpoint,
                operation_kind=GitWriteIntent.LOCAL_COMMIT_INTENT,
                target_paths=("runtime/example.py",),
                target_branch="feature/m2-b0-provider-critic-inert-core",
                created_at="2026-06-29T00:00:00Z",
                preview_nonce="write-preview-session",
            )
        ).preview
        return create_git_commit_preview(
            GitCommitPreviewRequest(
                write_preview=write_preview,
                checkpoint=checkpoint,
                commit_message=commit_message,
                target_paths=("runtime/example.py",),
                created_at="2026-06-29T00:00:00Z",
                preview_nonce="commit-preview-session",
            )
        ).preview

    def checkpoint(self):
        git_read = GitReadResult(
            status=GIT_READ_READY,
            git_read_hash="a" * 64,
            repo_root="/workspace/repo",
            head_sha="1" * 40,
            branch_name="main",
            detached_head=False,
            clean=True,
            staged_paths=(),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=(self.evidence(),),
            reason_codes=("GIT_READ_READY_EVIDENCE_ONLY",),
            reason="evidence only",
        )
        governance = GitGovernanceResult(
            status=GIT_GOVERNANCE_PASS,
            governance_hash="b" * 64,
            input_git_read_hash="a" * 64,
            policy_name="AOIA_GIT_READ_ONLY_GOVERNANCE",
            policy_version="1A",
            findings=(),
            reason_codes=("GIT_GOVERNANCE_PASS_METADATA_ONLY",),
            risk_flags=(),
        )
        return create_git_state_checkpoint(
            GitStateCheckpointRequest(
                git_read_result=git_read,
                git_governance_result=governance,
                created_at="2026-06-29T00:00:00Z",
                checkpoint_nonce="checkpoint-session",
                allow_review_checkpoint=True,
            )
        ).checkpoint

    @staticmethod
    def evidence() -> GitCommandEvidence:
        return GitCommandEvidence(
            command_id="VERIFY_HEAD",
            status="PASS",
            reason_code="GIT_READ_READY_EVIDENCE_ONLY",
            exit_code=0,
            timeout_expired=False,
            stdout_preview="",
            stderr_preview="",
            stdout_truncated=False,
            stderr_truncated=False,
            command_hash="c" * 64,
            subprocess_started=True,
            shell_invoked=False,
        )

    def assert_authority_and_effects_false(self, result) -> None:
        for field in (*AUTHORITY_FIELDS, *EFFECT_FIELDS):
            self.assertIs(getattr(result, field), False)
            self.assertIs(result.to_dict()[field], False)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)
    return type("Scan", (), {"imports": tuple(imports), "calls": tuple(calls)})()


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if parts:
            return ".".join((aliases.get(parts[0], parts[0]), *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def matches_any_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in prefixes)


if __name__ == "__main__":
    unittest.main()
