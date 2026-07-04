from __future__ import annotations

import ast
import hashlib
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.execution.human_execution_barrier import (
    HumanDecisionSource,
    HumanDecisionVerdict,
    HumanExecutionBarrierRequest,
    HumanExecutionSourceTrust,
    evaluate_human_execution_barrier,
)
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, create_git_state_checkpoint
from runtime.git_ops.git_controlled_push import (
    CONTROLLED_GIT_PUSH_BLOCKED,
    CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_GIT_PUSH_BLOCKED_BARRIER_INVALID,
    CONTROLLED_GIT_PUSH_BLOCKED_DIRTY_WORKTREE,
    CONTROLLED_GIT_PUSH_BLOCKED_HEAD_CHANGED,
    CONTROLLED_GIT_PUSH_BLOCKED_MISSING_BARRIER,
    CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH,
    CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_CHANGED,
    CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_HEAD_MISSING,
    CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_NOT_LOCAL,
    CONTROLLED_GIT_PUSH_PUSHED,
    ControlledGitPushResult,
    controlled_git_push,
)
from runtime.git_ops.git_governance import GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_push_preview import GitPushPreviewRequest, create_git_push_preview
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.providers.critic import critique_provider_result
from runtime.schemas.action_proposal import (
    ActionProposalKind,
    ActionProposalRequest,
    ActionProposalSourceTrust,
    build_action_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_controlled_push.py"
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
    "approved",
    "eligible",
)


class ControlledGitPush1ATests(unittest.TestCase):
    def test_happy_path_pushes_exact_reviewed_head_to_local_bare_remote_only(self):
        with TemporaryDirectory() as workspace:
            repo, remote, remote_head_before = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head_before)
            local_head = self.git(repo, "rev-parse", "HEAD")

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assertEqual(CONTROLLED_GIT_PUSH_PUSHED, result.status)
            self.assertIsInstance(result, ControlledGitPushResult)
            self.assertEqual(local_head, result.local_head_before)
            self.assertEqual(local_head, result.local_head_after)
            self.assertEqual(remote_head_before, result.remote_head_before)
            self.assertEqual(local_head, result.remote_head_after)
            self.assertEqual(local_head, self.git(remote, "rev-parse", f"refs/heads/{self.branch(repo)}"))
            self.assertEqual(preview.preview_hash, result.reviewed_push_preview_hash)
            self.assertEqual(1, result.commits_ahead_before)
            self.assertEqual(0, result.commits_behind_before)
            self.assert_metadata_only(result)

    def test_missing_barrier_evidence_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, _barrier = self.reviewed_evidence(repo, remote_head)

            result = controlled_git_push(repo, preview, None, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_MISSING_BARRIER)

    def test_forged_metadata_approval_cannot_authorize_push(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, _barrier = self.reviewed_evidence(repo, remote_head)

            result = controlled_git_push(
                repo,
                preview,
                {"approved": True, "eligible": True, "authority": True, "can_push": True},
                workspace_root=workspace,
            )

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_AUTHORITY_CLAIM)

    def test_push_preview_hash_mismatch_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            tampered = {**preview.to_dict(), "preview_hash": "f" * 64}

            result = controlled_git_push(repo, tampered, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_PREVIEW_HASH_MISMATCH)

    def test_stale_replayed_barrier_evidence_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            replayed = {**preview.to_dict(), "preview_nonce": "different"}
            replayed["preview_hash"] = self.rehash_preview(replayed)

            result = controlled_git_push(repo, replayed, barrier, workspace_root=workspace)

            self.assertNotEqual(preview.preview_hash, replayed["preview_hash"])
            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_BARRIER_INVALID)

    def test_local_head_changed_after_approval_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            (repo / "tracked.txt").write_text("third local commit\n", encoding="utf-8")
            self.run_git(repo, "add", "tracked.txt")
            self.run_git(repo, "commit", "-m", "third local commit")

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_HEAD_CHANGED)

    def test_remote_changed_after_approval_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            other = Path(workspace) / "other"
            self.run_git(Path(workspace), "clone", str(remote), str(other))
            self.run_git(other, "config", "user.name", "AOIA Other")
            self.run_git(other, "config", "user.email", "other@example.invalid")
            (other / "tracked.txt").write_text("remote changed\n", encoding="utf-8")
            self.run_git(other, "add", "tracked.txt")
            self.run_git(other, "commit", "-m", "remote changed")
            self.run_git(other, "push", "origin", self.branch(repo))

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_CHANGED)

    def test_dirty_working_tree_after_approval_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            (repo / "untracked.txt").write_text("not reviewed\n", encoding="utf-8")

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_DIRTY_WORKTREE)

    def test_missing_remote_head_fails_closed(self):
        with TemporaryDirectory() as workspace:
            repo, remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            self.run_git(remote, "update-ref", "-d", f"refs/heads/{self.branch(repo)}")

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_HEAD_MISSING)

    def test_non_local_remote_url_blocks_before_push(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            preview, barrier = self.reviewed_evidence(repo, remote_head)
            self.run_git(repo, "remote", "set-url", "origin", "https://example.invalid/repo.git")

            result = controlled_git_push(repo, preview, barrier, workspace_root=workspace)

            self.assert_blocked(result, CONTROLLED_GIT_PUSH_BLOCKED_REMOTE_NOT_LOCAL)

    def test_inert_metadata_objects_cannot_authorize_push(self):
        with TemporaryDirectory() as workspace:
            repo, _remote, remote_head = self.repo_ahead_of_local_bare_remote(workspace)
            _preview, barrier = self.reviewed_evidence(repo, remote_head)
            action = build_action_proposal(
                ActionProposalRequest(
                    action_kind=ActionProposalKind.GIT_PUSH,
                    target_refs=("origin",),
                    source_trust=ActionProposalSourceTrust.USER_SUPPLIED,
                    proposed_by="test",
                    summary="metadata only",
                )
            )
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

            for item in (action, critic):
                with self.subTest(item=type(item).__name__):
                    result = controlled_git_push(repo, item, barrier, workspace_root=workspace)
                    self.assertEqual(CONTROLLED_GIT_PUSH_BLOCKED, result.status)

    def test_runner_surface_is_narrow_push_only_without_shell_github_provider_or_browser(self):
        source = CONTROLLED_MODULE.read_text(encoding="utf-8").casefold()
        scan = scan_module(CONTROLLED_MODULE)

        self.assertIn("subprocess", scan.imports)
        self.assertIn("subprocess.run", scan.calls)
        self.assertNotIn("subprocess.Popen", scan.calls)
        self.assertNotIn("os.system", scan.calls)
        self.assertNotIn("Popen", scan.calls)
        self.assertNotIn("shell=true", source)
        self.assertNotIn("api.github.com", source)
        for forbidden in ("socket", "webbrowser", "selenium", "playwright", "requests", "httpx", "openai", "anthropic"):
            self.assertNotIn(forbidden, scan.imports)
        for forbidden_function in ("dispatch_git_push", "authorize_git_push", "approve_git_push"):
            self.assertNotIn(f"def {forbidden_function}", source)

    def repo_ahead_of_local_bare_remote(self, workspace: str):
        root = Path(workspace)
        remote = root / "remote.git"
        repo = root / "repo"
        self.run_git(root, "init", "--bare", str(remote))
        repo.mkdir()
        self.run_git(repo, "init")
        self.run_git(repo, "config", "user.name", "AOIA Test")
        self.run_git(repo, "config", "user.email", "aoia@example.invalid")
        (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
        self.run_git(repo, "add", "tracked.txt")
        self.run_git(repo, "commit", "-m", "initial commit")
        self.run_git(repo, "remote", "add", "origin", str(remote))
        self.run_git(repo, "push", "origin", self.branch(repo))
        remote_head = self.git(remote, "rev-parse", f"refs/heads/{self.branch(repo)}")
        (repo / "tracked.txt").write_text("reviewed local commit\n", encoding="utf-8")
        self.run_git(repo, "add", "tracked.txt")
        self.run_git(repo, "commit", "-m", "reviewed local commit")
        return repo, remote, remote_head

    def reviewed_evidence(self, repo: Path, remote_head: str):
        branch = self.branch(repo)
        local_head = self.git(repo, "rev-parse", "HEAD")
        preview = create_git_push_preview(
            GitPushPreviewRequest(
                checkpoint=self.checkpoint(repo),
                branch=branch,
                remote_name="origin",
                remote_ref=f"refs/heads/{branch}",
                remote_head=remote_head,
                commits_ahead=tuple(self.git(repo, "rev-list", f"{remote_head}..HEAD").splitlines()),
                commits_behind=(),
                created_at="2026-07-04T00:00:00Z",
                preview_nonce="push-preview-session",
            )
        ).preview
        self.assertIsNotNone(preview)
        self.assertEqual(local_head, preview.local_head)
        return preview, self.human_barrier(preview)

    def checkpoint(self, repo: Path):
        head = self.git(repo, "rev-parse", "HEAD")
        branch = self.branch(repo)
        git_read_hash = hashlib.sha256(f"{repo}:{head}".encode("utf-8")).hexdigest()
        git_read = GitReadResult(
            status=GIT_READ_READY,
            git_read_hash=git_read_hash,
            repo_root=str(repo.resolve()),
            head_sha=head,
            branch_name=branch,
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
                created_at="2026-07-04T00:00:00Z",
                checkpoint_nonce="checkpoint-session",
                allow_review_checkpoint=True,
            )
        )
        self.assertIsNotNone(result.checkpoint)
        return result.checkpoint

    def human_barrier(self, preview, **overrides):
        request = HumanExecutionBarrierRequest(
            requested_execution_kind="LOCAL_GIT_PUSH_PREVIEW_BARRIER",
            requested_command=f"push-preview:{preview.preview_hash}",
            requested_command_hash=preview.preview_hash,
            source_trust=HumanExecutionSourceTrust.USER_SUPPLIED,
            human_decision_id="decision-git-push",
            human_decision_hash=DECISION_HASH,
            human_decision_verdict=HumanDecisionVerdict.APPROVE,
            human_decision_source=HumanDecisionSource.HUMAN_OPERATOR,
            human_decision_binds_to_command_hash=preview.preview_hash,
            human_decision_binds_to_test_runner_control_hash=preview.preview_hash,
            human_decision_binds_to_sandbox_envelope_hash=SANDBOX_HASH,
            human_decision_binds_to_policy_check_hash=POLICY_HASH,
            human_decision_binds_to_controlled_execution_request_hash=CONTROLLED_REQUEST_HASH,
            source_test_runner_control_id="push-preview-control",
            source_test_runner_control_hash=preview.preview_hash,
            source_test_runner_control_status="REVIEW_REQUIRED",
            source_sandbox_envelope_id="push-preview-sandbox",
            source_sandbox_envelope_hash=SANDBOX_HASH,
            source_sandbox_envelope_status="REVIEW_REQUIRED",
            source_policy_check_id="push-preview-policy",
            source_policy_check_hash=POLICY_HASH,
            source_policy_check_status="REVIEW_REQUIRED",
            source_controlled_execution_request_hash=CONTROLLED_REQUEST_HASH,
        )
        result = evaluate_human_execution_barrier(replace(request, **overrides))
        data = result.to_dict()
        data["human_decision_binds_to_push_preview_hash"] = preview.preview_hash
        data["human_decision_binds_to_command_hash"] = preview.preview_hash
        data["risk_flags"] = ()
        return data

    @staticmethod
    def rehash_preview(data):
        material = dict(data)
        material.pop("preview_hash", None)
        for field in (
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
        ):
            material.pop(field, None)
        from runtime.git_ops.git_push_preview import compute_git_push_preview_hash

        return compute_git_push_preview_hash(material)

    def branch(self, repo: Path) -> str:
        return self.git(repo, "rev-parse", "--abbrev-ref", "HEAD")

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

    def assert_blocked(self, result: ControlledGitPushResult, reason_code: str) -> None:
        self.assertEqual(CONTROLLED_GIT_PUSH_BLOCKED, result.status)
        self.assertEqual(reason_code, result.reason_code)
        self.assert_metadata_only(result)

    def assert_metadata_only(self, result: ControlledGitPushResult) -> None:
        data = result.to_dict()
        for field in AUTHORITY_RESULT_FIELDS:
            self.assertNotIn(field, data)


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
