from __future__ import annotations

import ast
import hashlib
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.execution.human_execution_barrier import (
    HumanDecisionSource,
    HumanDecisionVerdict,
    HumanExecutionBarrierRequest,
    HumanExecutionSourceTrust,
    evaluate_human_execution_barrier,
)
from runtime.git_ops.controlled_git_commit import (
    CONTROLLED_GIT_COMMIT_BLOCKED,
    CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_GIT_COMMIT_BLOCKED_BARRIER_INVALID,
    CONTROLLED_GIT_COMMIT_BLOCKED_EMPTY_STAGED_DIFF,
    CONTROLLED_GIT_COMMIT_BLOCKED_HEAD_CHANGED,
    CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_BARRIER,
    CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH,
    CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_DIFF_CHANGED,
    CONTROLLED_GIT_COMMIT_BLOCKED_TIMEOUT,
    CONTROLLED_GIT_COMMIT_BLOCKED_UNSTAGED_CHANGES,
    CONTROLLED_GIT_COMMIT_BLOCKED_UNTRACKED_CHANGES,
    CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH,
    CONTROLLED_GIT_COMMIT_COMMITTED,
    ControlledGitCommitResult,
    _ControlledGitCommitRunner,
    controlled_git_commit,
)
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, create_git_state_checkpoint
from runtime.git_ops.git_commit_preview import GitCommitPreviewRequest, create_git_commit_preview
from runtime.git_ops.git_governance import GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.git_ops.git_write_preview import GitWriteIntent, GitWritePreviewRequest, create_git_write_preview
from runtime.providers.critic import critique_provider_result
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalSourceTrust,
    build_action_proposal,
)
from runtime.safety.bounded_subprocess import (
    PROCESS_CPU_LIMIT_REASON_CODE,
    PROCESS_CONTAINMENT_LOST_REASON_CODE,
    SubprocessContainmentError,
    SubprocessResourceLimitError,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_MODULE = REPO_ROOT / "runtime" / "git_ops" / "controlled_git_commit.py"
DECISION_HASH = "e" * 64
SANDBOX_HASH = "b" * 64
POLICY_HASH = "c" * 64
CONTROLLED_REQUEST_HASH = "d" * 64
AUTHORITY_RESULT_FIELDS = (
    "can_approve",
    "can_write",
    "can_execute",
    "can_commit",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "approval_authority",
    "write_authority",
    "push_authority",
    "provider_authority",
    "dispatcher",
    "automatic_retry",
    "fallback",
)


class ControlledGitCommit1ATests(unittest.TestCase):
    def test_happy_path_creates_exactly_one_local_commit_and_metadata_only_result(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace, content="reviewed\n")
            preview, barrier = self.reviewed_evidence(repo, "feat(git): controlled commit")
            old_head = self.git(repo, "rev-parse", "HEAD")

            result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

            self.assertEqual(CONTROLLED_GIT_COMMIT_COMMITTED, result.status)
            self.assertIsInstance(result, ControlledGitCommitResult)
            self.assertEqual(old_head, result.previous_head)
            self.assertNotEqual(old_head, result.new_head)
            self.assertEqual(result.new_head, result.commit_hash)
            self.assertEqual(preview.commit_preview_hash, result.reviewed_commit_preview_hash)
            self.assertEqual("feat(git): controlled commit", self.git(repo, "log", "-1", "--pretty=%B").strip())
            self.assertEqual(1, int(self.git(repo, "rev-list", "--count", f"{old_head}..HEAD")))
            self.assert_metadata_only(result)

    def test_missing_barrier_evidence_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, _barrier = self.reviewed_evidence(repo)

            result = controlled_git_commit(repo, preview, None, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_MISSING_BARRIER)

    def test_forged_barrier_authority_fields_fail_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, _barrier = self.reviewed_evidence(repo)

            result = controlled_git_commit(
                repo,
                preview,
                {"approved": True, "eligible": True, "authority": True, "can_commit": True},
                workspace_root=workspace,
            )

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_AUTHORITY_CLAIM)

    def test_commit_preview_hash_mismatch_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo)
            tampered = {**preview.to_dict(), "commit_preview_hash": "f" * 64}

            result = controlled_git_commit(repo, tampered, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_PREVIEW_HASH_MISMATCH)

    def test_staged_diff_changed_after_approval_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace, content="reviewed\n")
            preview, barrier = self.reviewed_evidence(repo)
            (repo / "tracked.txt").write_text("changed after review\n", encoding="utf-8")
            self.run_git(repo, "add", "tracked.txt")

            result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_STAGED_DIFF_CHANGED)

    def test_head_changed_after_approval_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo)
            self.run_git(repo, "commit", "-m", "outside commit")

            result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_HEAD_CHANGED)

    def test_stale_replayed_barrier_evidence_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo, "feat(git): first reviewed message")
            replayed_preview, _other_barrier = self.reviewed_evidence(repo, "feat(git): second reviewed message")

            result = controlled_git_commit(repo, replayed_preview, barrier, workspace_root=workspace)

            self.assertNotEqual(preview.commit_preview_hash, replayed_preview.commit_preview_hash)
            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_BARRIER_INVALID)

    def test_empty_staged_diff_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo)
            self.run_git(repo, "reset", "--", "tracked.txt")
            self.run_git(repo, "checkout", "--", "tracked.txt")

            result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_EMPTY_STAGED_DIFF)

    def test_unstaged_or_untracked_extra_changes_fail_closed(self):
        cases = (
            ("unstaged", "tracked.txt", CONTROLLED_GIT_COMMIT_BLOCKED_UNSTAGED_CHANGES, False),
            ("untracked", "untracked.txt", CONTROLLED_GIT_COMMIT_BLOCKED_UNTRACKED_CHANGES, True),
        )
        for name, filename, reason_code, untracked in cases:
            with self.subTest(name=name), TemporaryDirectory() as workspace:
                repo = self.repo_with_staged_change(workspace)
                preview, barrier = self.reviewed_evidence(repo)
                path = repo / filename
                if not untracked:
                    path.write_text("dirty after review\n", encoding="utf-8")
                else:
                    path.write_text("not reviewed\n", encoding="utf-8")

                result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

                self.assert_blocked(result, reason_code)

    def test_path_traversal_or_repo_outside_workspace_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo)

            traversal = controlled_git_commit(repo / ".." / repo.name, preview, barrier, workspace_root=workspace)
            outside = controlled_git_commit(repo, preview, barrier, workspace_root=Path(workspace) / "missing")

            self.assert_blocked(traversal, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH)
            self.assert_blocked(outside, CONTROLLED_GIT_COMMIT_BLOCKED_WORKSPACE_PATH)

    def test_inert_metadata_objects_cannot_authorize_commit(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            _preview, barrier = self.reviewed_evidence(repo)
            action = build_action_proposal(
                ActionProposalRequest(
                    action_kind=ActionProposalKind.GIT_COMMIT,
                    target_refs=("tracked.txt",),
                    source_trust=ActionProposalSourceTrust.USER_SUPPLIED,
                    proposed_by="test",
                    summary="metadata only",
                )
            )
            artifact = build_artifact_preview(ArtifactPreviewRequest(target_path="tracked.txt", proposed_content="reviewed\n", original_content="initial\n"))
            critic = critique_provider_result(
                {
                    "provider_id": "mock",
                    "model_id": "mock-model",
                    "mode": "mock",
                    "status": "ok",
                    "trust_status": "UNTRUSTED",
                    "output_text": "review only",
                }
            )

            for item in (action, artifact, critic):
                with self.subTest(item=type(item).__name__):
                    result = controlled_git_commit(repo, item, barrier, workspace_root=workspace)
                    self.assertEqual(CONTROLLED_GIT_COMMIT_BLOCKED, result.status)

    def test_commit_message_injection_text_is_literal_message_data(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            message = "feat: literal ; --allow-empty"
            preview, barrier = self.reviewed_evidence(repo, message)

            result = controlled_git_commit(repo, preview, barrier, workspace_root=workspace)

            self.assertEqual(CONTROLLED_GIT_COMMIT_COMMITTED, result.status)
            self.assertEqual(message, self.git(repo, "log", "-1", "--pretty=%B").strip())

    def test_git_timeout_is_distinct_and_creates_no_commit(self):
        with TemporaryDirectory() as workspace:
            repo = self.repo_with_staged_change(workspace)
            preview, barrier = self.reviewed_evidence(repo)
            old_head = self.git(repo, "rev-parse", "HEAD")

            result = controlled_git_commit(
                repo,
                preview,
                barrier,
                workspace_root=workspace,
                runner=TimeoutRunner(),
            )

            self.assert_blocked(result, CONTROLLED_GIT_COMMIT_BLOCKED_TIMEOUT)
            self.assertEqual(old_head, self.git(repo, "rev-parse", "HEAD"))

    def test_mutation_resource_and_containment_failures_remain_uncertain(self):
        failures = (
            SubprocessResourceLimitError(
                -24,
                ["git", "commit"],
                PROCESS_CPU_LIMIT_REASON_CODE,
            ),
            SubprocessContainmentError(PROCESS_CONTAINMENT_LOST_REASON_CODE),
        )
        for failure in failures:
            with self.subTest(reason=failure.reason_code), TemporaryDirectory() as workspace:
                repo = self.repo_with_staged_change(workspace)
                preview, barrier = self.reviewed_evidence(repo)
                with self.assertRaises(type(failure)) as caught:
                    controlled_git_commit(
                        repo,
                        preview,
                        barrier,
                        workspace_root=workspace,
                        runner=CommitMutationFailureRunner(failure),
                    )
                self.assertEqual(failure.reason_code, caught.exception.reason_code)

    def test_runner_surface_has_no_push_shell_true_or_broad_execution(self):
        source = CONTROLLED_MODULE.read_text(encoding="utf-8").casefold()
        scan = scan_module(CONTROLLED_MODULE)

        self.assertIn("subprocess", scan.imports)
        self.assertNotIn("subprocess.run", scan.calls)
        self.assertIn("runtime.safety.bounded_subprocess.run_bounded_subprocess", scan.calls)
        self.assertNotIn("subprocess.Popen", scan.calls)
        self.assertNotIn("os.system", scan.calls)
        self.assertNotIn("Popen", scan.calls)
        self.assertNotIn("git push", source)
        self.assertNotIn("shell=true", source)
        for forbidden in ("socket", "webbrowser", "selenium", "playwright", "requests", "httpx", "openai", "anthropic"):
            self.assertNotIn(forbidden, scan.imports)

    def repo_with_staged_change(self, workspace: str, *, content: str = "reviewed\n") -> Path:
        repo = Path(workspace) / "repo"
        repo.mkdir()
        self.run_git(repo, "init")
        self.run_git(repo, "config", "user.name", "AOIA Test")
        self.run_git(repo, "config", "user.email", "aoia@example.invalid")
        (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
        self.run_git(repo, "add", "tracked.txt")
        self.run_git(repo, "commit", "-m", "initial commit")
        (repo / "tracked.txt").write_text(content, encoding="utf-8")
        self.run_git(repo, "add", "tracked.txt")
        return repo

    def reviewed_evidence(self, repo: Path, commit_message: str = "feat(git): controlled commit"):
        checkpoint = self.checkpoint(repo)
        write_preview = create_git_write_preview(
            GitWritePreviewRequest(
                checkpoint=checkpoint,
                operation_kind=GitWriteIntent.LOCAL_COMMIT_INTENT,
                target_paths=("tracked.txt",),
                target_branch=self.git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
                created_at="2026-06-29T00:00:00Z",
                preview_nonce="write-preview-session",
            )
        ).preview
        self.assertIsNotNone(write_preview)
        preview = create_git_commit_preview(
            GitCommitPreviewRequest(
                write_preview=write_preview,
                checkpoint=checkpoint,
                commit_message=commit_message,
                target_paths=("tracked.txt",),
                reviewed_staged_diff_hash=self.staged_diff_hash(repo),
                created_at="2026-06-29T00:00:00Z",
                preview_nonce="commit-preview-session",
            )
        ).preview
        self.assertIsNotNone(preview)
        return preview, self.human_barrier(preview)

    def checkpoint(self, repo: Path):
        head = self.git(repo, "rev-parse", "HEAD")
        branch = self.git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        git_read_hash = hashlib.sha256(f"{repo}:{head}".encode("utf-8")).hexdigest()
        git_read = GitReadResult(
            status=GIT_READ_READY,
            git_read_hash=git_read_hash,
            repo_root=str(repo.resolve()),
            head_sha=head,
            branch_name=branch,
            detached_head=False,
            clean=False,
            staged_paths=("tracked.txt",),
            unstaged_paths=(),
            untracked_paths=(),
            command_evidence=(self.evidence(),),
            reason_codes=("GIT_READ_READY_EVIDENCE_ONLY",),
            reason="evidence only",
        )
        governance = GitGovernanceResult(
            status=GIT_GOVERNANCE_PASS,
            governance_hash=hashlib.sha256(f"governance:{repo}:{head}".encode("utf-8")).hexdigest(),
            input_git_read_hash=git_read_hash,
            policy_name="AOIA_GIT_READ_ONLY_GOVERNANCE",
            policy_version="1A",
            findings=(),
            reason_codes=("GIT_GOVERNANCE_PASS_METADATA_ONLY",),
            risk_flags=(),
        )
        result = create_git_state_checkpoint(
            GitStateCheckpointRequest(
                git_read_result=git_read,
                git_governance_result=governance,
                created_at="2026-06-29T00:00:00Z",
                checkpoint_nonce="checkpoint-session",
                allow_review_checkpoint=True,
            )
        )
        self.assertIsNotNone(result.checkpoint)
        return result.checkpoint

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

    def staged_diff_hash(self, repo: Path) -> str:
        result = subprocess.run(
            ["git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        return hashlib.sha256(result.stdout).hexdigest()

    def run_git(self, repo: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    def git(self, repo: Path, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

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
            command_hash="a" * 64,
            subprocess_started=True,
            shell_invoked=False,
        )

    def assert_blocked(self, result: ControlledGitCommitResult, reason_code: str) -> None:
        self.assertEqual(CONTROLLED_GIT_COMMIT_BLOCKED, result.status)
        self.assertEqual(reason_code, result.reason_code)
        self.assert_metadata_only(result)

    def assert_metadata_only(self, result: ControlledGitCommitResult) -> None:
        data = result.to_dict()
        for field in AUTHORITY_RESULT_FIELDS:
            self.assertNotIn(field, data)


class TimeoutRunner:
    def run(self, command_id, repo_path: Path, **kwargs):
        del repo_path, kwargs
        return type(
            "TimeoutResult",
            (),
            {
                "exit_code": None,
                "stdout": b"",
                "stderr": b"",
                "timeout_expired": True,
            },
        )()


class CommitMutationFailureRunner:
    def __init__(self, failure: Exception) -> None:
        self.delegate = _ControlledGitCommitRunner()
        self.failure = failure

    def run(self, command_id, repo_path: Path, **kwargs):
        if command_id.value == "COMMIT":
            raise self.failure
        return self.delegate.run(command_id, repo_path, **kwargs)


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


if __name__ == "__main__":
    unittest.main()
