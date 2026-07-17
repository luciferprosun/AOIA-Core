from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, ControlWriteContext, write_preview_artifact_after_human_gate
from runtime.git_ops.git_checkpoint import (
    GIT_CHECKPOINT_BLOCKED,
    GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM,
    GIT_CHECKPOINT_BLOCKED_DETACHED_HEAD,
    GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH,
    GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS,
    GIT_CHECKPOINT_BLOCKED_GOVERNANCE_BLOCK,
    GIT_CHECKPOINT_BLOCKED_GOVERNANCE_REVIEW,
    GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH,
    GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH,
    GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ,
    GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ_HASH,
    GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE,
    GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH,
    GIT_CHECKPOINT_BLOCKED_MISSING_HEAD,
    GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT,
    GIT_CHECKPOINT_CREATED,
    GIT_CHECKPOINT_VALID,
    GitStateCheckpointRequest,
    canonical_git_checkpoint_json,
    compute_git_checkpoint_hash,
    create_git_state_checkpoint,
    verify_git_state_checkpoint,
)
from runtime.git_ops.git_governance import (
    GIT_GOVERNANCE_BLOCK,
    GIT_GOVERNANCE_NEEDS_REVIEW,
    GIT_GOVERNANCE_PASS,
    GitGovernanceFinding,
    GitGovernanceResult,
)
from runtime.git_ops.git_read import GIT_READ_BLOCKED, GIT_READ_ERROR, GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate
from runtime.safety.write_kill_switch import WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_checkpoint.py"
CONTENT = "# checkpoint evidence\n"
PACKET_HASH = "a" * 64
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
DEFAULT = object()


class GitNativeStateCheckpoint1ATests(unittest.TestCase):
    def test_valid_pass_governance_creates_checkpoint(self):
        result = self.checkpoint()

        self.assertEqual(GIT_CHECKPOINT_CREATED, result.status)
        self.assertIsNotNone(result.checkpoint)
        checkpoint = result.checkpoint
        assert checkpoint is not None
        self.assertEqual(self.git_read().git_read_hash, checkpoint.git_read_hash)
        self.assertEqual(self.governance().governance_hash, checkpoint.governance_hash)
        self.assertEqual("AOIA_GIT_READ_ONLY_GOVERNANCE", checkpoint.governance_policy_name)
        self.assertEqual("1A", checkpoint.governance_policy_version)
        self.assertEqual("/workspace/repo", checkpoint.repo_root)
        self.assertEqual(compute_git_checkpoint_hash({"repo_root": "/workspace/repo"}), checkpoint.repo_identity_hash)
        self.assertEqual("1" * 40, checkpoint.head_sha)
        self.assertEqual("main", checkpoint.branch_name)
        self.assert_authority_false(result)
        self.assert_authority_false(checkpoint)

    def test_valid_needs_review_governance_blocks_by_default(self):
        governance = self.governance(status=GIT_GOVERNANCE_NEEDS_REVIEW)

        result = self.checkpoint(governance=governance)

        self.assertEqual(GIT_CHECKPOINT_BLOCKED, result.status)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_GOVERNANCE_REVIEW, result.reason_codes)

    def test_needs_review_governance_can_create_checkpoint_only_if_policy_allows_review_checkpoints(self):
        governance = self.governance(status=GIT_GOVERNANCE_NEEDS_REVIEW)

        result = self.checkpoint(governance=governance, allow_review_checkpoint=True)

        self.assertEqual(GIT_CHECKPOINT_CREATED, result.status)
        self.assertEqual(GIT_GOVERNANCE_NEEDS_REVIEW, result.checkpoint.governance_status)

    def test_block_governance_blocks_checkpoint_creation(self):
        result = self.checkpoint(governance=self.governance(status=GIT_GOVERNANCE_BLOCK))

        self.assertEqual(GIT_CHECKPOINT_BLOCKED, result.status)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_GOVERNANCE_BLOCK, result.reason_codes)

    def test_missing_inputs_block(self):
        missing_read = self.checkpoint(git_read=None)
        missing_governance = self.checkpoint(governance=None)

        self.assertEqual(GIT_CHECKPOINT_BLOCKED, missing_read.status)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ, missing_read.reason_codes)
        self.assertEqual(GIT_CHECKPOINT_BLOCKED, missing_governance.status)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE, missing_governance.reason_codes)

    def test_missing_hashes_and_governance_input_hash_mismatch_block(self):
        missing_git_hash = self.checkpoint(git_read={**self.git_read().to_dict(), "git_read_hash": None})
        missing_governance_hash = self.checkpoint(governance={**self.governance().to_dict(), "governance_hash": None})
        mismatch = self.checkpoint(governance={**self.governance().to_dict(), "input_git_read_hash": "b" * 64})

        self.assertIn(GIT_CHECKPOINT_BLOCKED_MISSING_GIT_READ_HASH, missing_git_hash.reason_codes)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH, missing_governance_hash.reason_codes)
        self.assertIn(GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH, mismatch.reason_codes)

    def test_git_read_error_blocked_missing_repo_head_branch_and_detached_head_block(self):
        cases = {
            "error": (replace(self.git_read(), status=GIT_READ_ERROR), GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS),
            "blocked": (replace(self.git_read(), status=GIT_READ_BLOCKED), GIT_CHECKPOINT_BLOCKED_GIT_READ_STATUS),
            "repo": (replace(self.git_read(), repo_root=None), GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT),
            "head": (replace(self.git_read(), head_sha=None), GIT_CHECKPOINT_BLOCKED_MISSING_HEAD),
            "branch": (replace(self.git_read(), branch_name=None), GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH),
            "detached": (replace(self.git_read(), detached_head=True, branch_name=None), GIT_CHECKPOINT_BLOCKED_DETACHED_HEAD),
        }
        for name, (git_read, code) in cases.items():
            with self.subTest(name=name):
                result = self.checkpoint(git_read=git_read, governance=self.governance(git_read=git_read))

                self.assertEqual(GIT_CHECKPOINT_BLOCKED, result.status)
                self.assertIn(code, result.reason_codes)

    def test_authority_claims_in_inputs_block(self):
        cases = {
            "read": ({**self.git_read().to_dict(), "can_push": True}, self.governance()),
            "governance": (self.git_read(), {**self.governance().to_dict(), "can_commit": True}),
            "approve": (self.git_read(), self.governance(), {"can_approve": True}),
            "write": (self.git_read(), self.governance(), {"can_write": True}),
            "commit": (self.git_read(), self.governance(), {"can_commit": True}),
            "push": (self.git_read(), self.governance(), {"can_push": True}),
            "provider": (self.git_read(), self.governance(), {"can_call_provider": True}),
        }
        for name, values in cases.items():
            with self.subTest(name=name):
                git_read, governance, *claim = values
                result = self.checkpoint(git_read=git_read, governance=governance, claims=claim[0] if claim else None)

                self.assertEqual(GIT_CHECKPOINT_BLOCKED, result.status)
                self.assertIn(GIT_CHECKPOINT_BLOCKED_AUTHORITY_CLAIM, result.reason_codes)

    def test_checkpoint_canonical_json_and_hash_are_deterministic(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        first = self.checkpoint().checkpoint
        second = self.checkpoint().checkpoint

        self.assertEqual(canonical_git_checkpoint_json(left), canonical_git_checkpoint_json(right))
        self.assertEqual(compute_git_checkpoint_hash(left), compute_git_checkpoint_hash(right))
        self.assertEqual(first.checkpoint_hash, second.checkpoint_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_checkpoint_hash_changes_for_bound_evidence_and_policy_changes(self):
        base = self.checkpoint().checkpoint
        changes = (
            self.git_read(git_read_hash="b" * 64),
            self.git_read(head_sha="2" * 40),
            self.git_read(branch_name="release"),
            self.git_read(staged_paths=("docs/a.md",)),
            self.git_read(unstaged_paths=("docs/b.md",)),
            self.git_read(untracked_paths=("docs/c.md",)),
        )
        for git_read in changes:
            with self.subTest(change=git_read.to_dict()):
                changed = self.checkpoint(git_read=git_read, governance=self.governance(git_read=git_read)).checkpoint
                self.assertNotEqual(base.checkpoint_hash, changed.checkpoint_hash)

        changed_governance_hash = self.governance(governance_hash="d" * 64)
        changed_policy = self.governance(policy_version="2A")
        self.assertNotEqual(base.checkpoint_hash, self.checkpoint(governance=changed_governance_hash).checkpoint.checkpoint_hash)
        self.assertNotEqual(base.checkpoint_hash, self.checkpoint(governance=changed_policy).checkpoint.checkpoint_hash)

    def test_path_and_finding_order_do_not_change_canonical_result(self):
        left_read = self.git_read(staged_paths=("docs/b.md", "docs/a.md"))
        right_read = self.git_read(staged_paths=("docs/a.md", "docs/b.md"))
        left_governance = self.governance(
            git_read=left_read,
            findings=(
                GitGovernanceFinding("NEEDS_REVIEW", "GIT_GOVERNANCE_REVIEW_STAGED_PATHS", "review", ("docs/b.md", "docs/a.md")),
                GitGovernanceFinding("NEEDS_REVIEW", "GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK", "review", (".gitmodules",)),
            ),
            status=GIT_GOVERNANCE_NEEDS_REVIEW,
        )
        right_governance = self.governance(
            git_read=right_read,
            findings=tuple(reversed(left_governance.findings)),
            status=GIT_GOVERNANCE_NEEDS_REVIEW,
            governance_hash=left_governance.governance_hash,
        )

        left = self.checkpoint(git_read=left_read, governance=left_governance, allow_review_checkpoint=True).checkpoint
        right = self.checkpoint(git_read=right_read, governance=right_governance, allow_review_checkpoint=True).checkpoint

        self.assertEqual(left.checkpoint_hash, right.checkpoint_hash)
        self.assertEqual(left.to_dict(), right.to_dict())

    def test_checkpoint_verification_accepts_exact_matching_evidence(self):
        result = self.checkpoint()

        verified = verify_git_state_checkpoint(result.checkpoint, self.git_read(), self.governance())

        self.assertEqual(GIT_CHECKPOINT_VALID, verified.status)
        self.assertEqual(result.checkpoint.checkpoint_hash, verified.checkpoint.checkpoint_hash)

    def test_checkpoint_verification_rejects_replay_against_changed_evidence(self):
        checkpoint = self.checkpoint().checkpoint
        cases = {
            "git_read_hash": (self.git_read(git_read_hash="b" * 64), self.governance(git_read=self.git_read(git_read_hash="b" * 64)), GIT_CHECKPOINT_BLOCKED_GIT_READ_HASH_MISMATCH),
            "governance_hash": (self.git_read(), self.governance(governance_hash="c" * 64), GIT_CHECKPOINT_BLOCKED_MISSING_GOVERNANCE_HASH),
            "head": (self.git_read(head_sha="2" * 40), self.governance(git_read=self.git_read(head_sha="2" * 40)), GIT_CHECKPOINT_BLOCKED_MISSING_HEAD),
            "branch": (self.git_read(branch_name="release"), self.governance(git_read=self.git_read(branch_name="release")), GIT_CHECKPOINT_BLOCKED_MISSING_BRANCH),
            "path": (self.git_read(staged_paths=("docs/a.md",)), self.governance(git_read=self.git_read(staged_paths=("docs/a.md",))), GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH),
            "repo": (self.git_read(repo_root="/workspace/other"), self.governance(git_read=self.git_read(repo_root="/workspace/other")), GIT_CHECKPOINT_BLOCKED_MISSING_REPO_ROOT),
        }
        for name, (git_read, governance, code) in cases.items():
            with self.subTest(name=name):
                verified = verify_git_state_checkpoint(checkpoint, git_read, governance)

                self.assertIn(code, verified.reason_codes)

    def test_tampered_checkpoint_hash_is_rejected(self):
        checkpoint = self.checkpoint().checkpoint.to_dict()
        checkpoint["checkpoint_hash"] = "f" * 64

        verified = verify_git_state_checkpoint(checkpoint, self.git_read(), self.governance())

        self.assertIn(GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH, verified.reason_codes)

    def test_checkpoint_result_cannot_satisfy_control_write_gate_or_commit_push_authority(self):
        checkpoint_result = self.checkpoint()
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=checkpoint_result,
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)
        self.assert_authority_false(checkpoint_result)
        self.assert_authority_false(checkpoint_result.checkpoint)

    def test_valid_checkpoint_cannot_bypass_kill_switch_workspace_or_hash_checks(self):
        checkpoint = self.checkpoint().checkpoint
        tampered = {**checkpoint.to_dict(), "head_sha": "2" * 40}

        verified = verify_git_state_checkpoint(tampered, self.git_read(), self.governance())

        self.assertIn(GIT_CHECKPOINT_BLOCKED_HASH_MISMATCH, verified.reason_codes)
        self.assertFalse(checkpoint.can_write)
        self.assertFalse(checkpoint.can_commit)
        self.assertFalse(checkpoint.can_push)

    def test_checkpoint_module_imports_no_subprocess_network_provider_browser_package_or_env_libs(self):
        scan = scan_module(CHECKPOINT_MODULE)
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
        )

        self.assertEqual([], [item for item in scan.imports if matches_any_prefix(item, forbidden_import_prefixes)])
        self.assertNotIn("subprocess.run", scan.calls)
        source = CHECKPOINT_MODULE.read_text(encoding="utf-8").casefold()
        for forbidden in ("shell=true", "api.github.com", "ls-remote", "os.environ", "getenv", "api_key", "git tag", "git branch", "refs/tags", "refs/heads"):
            self.assertNotIn(forbidden, source)

    def git_read(
        self,
        *,
        status: str = GIT_READ_READY,
        git_read_hash: str = "a" * 64,
        repo_root: str | None = "/workspace/repo",
        head_sha: str | None = "1" * 40,
        branch_name: str | None = "main",
        detached_head: bool = False,
        clean: bool = True,
        staged_paths: tuple[str, ...] = (),
        unstaged_paths: tuple[str, ...] = (),
        untracked_paths: tuple[str, ...] = (),
        command_evidence: tuple[GitCommandEvidence, ...] | None = None,
    ) -> GitReadResult:
        return GitReadResult(
            status=status,
            git_read_hash=git_read_hash,
            repo_root=repo_root,
            head_sha=head_sha,
            branch_name=branch_name,
            detached_head=detached_head,
            clean=clean,
            staged_paths=staged_paths,
            unstaged_paths=unstaged_paths,
            untracked_paths=untracked_paths,
            command_evidence=command_evidence if command_evidence is not None else (self.evidence(),),
            reason_codes=("GIT_READ_READY_EVIDENCE_ONLY",),
            reason="evidence only",
        )

    def governance(
        self,
        *,
        git_read: GitReadResult | None = None,
        status: str = GIT_GOVERNANCE_PASS,
        governance_hash: str = "b" * 64,
        policy_name: str = "AOIA_GIT_READ_ONLY_GOVERNANCE",
        policy_version: str = "1A",
        findings: tuple[GitGovernanceFinding, ...] = (),
    ) -> GitGovernanceResult:
        git_read = git_read or self.git_read()
        input_hash = git_read.get("git_read_hash") if isinstance(git_read, dict) else git_read.git_read_hash
        return GitGovernanceResult(
            status=status,
            governance_hash=governance_hash,
            input_git_read_hash=input_hash,
            policy_name=policy_name,
            policy_version=policy_version,
            findings=findings,
            reason_codes=("GIT_GOVERNANCE_PASS_METADATA_ONLY",) if status == GIT_GOVERNANCE_PASS else ("GIT_GOVERNANCE_REVIEW_STAGED_PATHS",),
            risk_flags=(),
        )

    def checkpoint(self, *, git_read=DEFAULT, governance=DEFAULT, allow_review_checkpoint=False, claims=None):
        if git_read is DEFAULT:
            git_read = self.git_read()
        if governance is DEFAULT:
            governance = self.governance(git_read=git_read)
        return create_git_state_checkpoint(
            GitStateCheckpointRequest(
                git_read_result=git_read,
                git_governance_result=governance,
                created_at="2026-06-28T00:00:00Z",
                checkpoint_nonce="session-1",
                allow_review_checkpoint=allow_review_checkpoint,
                claims=claims,
            )
        )

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

    @staticmethod
    def preview():
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path="artifact.md",
                proposed_content=CONTENT,
                original_content="",
                reason="checkpoint regression",
            )
        )

    @staticmethod
    def context() -> ControlWriteContext:
        return ControlWriteContext(
            run_id="run",
            sandbox_request_id="sandbox-request",
            sandbox_result_id="sandbox-result",
            requested_by="test",
            dry_run_trace_id="dry-run",
            sandbox_policy_decision_id="policy",
        )

    def assert_authority_false(self, result) -> None:
        for field in AUTHORITY_FIELDS:
            self.assertIs(getattr(result, field), False)
        data = result.to_dict()
        for field in AUTHORITY_FIELDS:
            self.assertIs(data[field], False)


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
