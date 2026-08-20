from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.git_ops.git_governance import (
    GIT_GOVERNANCE_BLOCK,
    GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM,
    GIT_GOVERNANCE_BLOCKED_BRANCH_MISMATCH,
    GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE,
    GIT_GOVERNANCE_BLOCKED_DETACHED_HEAD,
    GIT_GOVERNANCE_BLOCKED_DIRTY_WORKTREE,
    GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS,
    GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT,
    GIT_GOVERNANCE_BLOCKED_MISSING_HASH,
    GIT_GOVERNANCE_BLOCKED_MISSING_HEAD,
    GIT_GOVERNANCE_BLOCKED_MISSING_INPUT,
    GIT_GOVERNANCE_BLOCKED_MISSING_REPO_ROOT,
    GIT_GOVERNANCE_BLOCKED_OUTPUT_BOUND,
    GIT_GOVERNANCE_BLOCKED_PROTECTED_PATH,
    GIT_GOVERNANCE_BLOCKED_RAW_COMMAND_TEXT,
    GIT_GOVERNANCE_BLOCKED_SANITIZER,
    GIT_GOVERNANCE_BLOCKED_TIMEOUT,
    GIT_GOVERNANCE_BLOCKED_UNSAFE_PATH,
    GIT_GOVERNANCE_NEEDS_REVIEW,
    GIT_GOVERNANCE_PASS,
    GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK,
    GIT_GOVERNANCE_REVIEW_STAGED_PATHS,
    GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS,
    GIT_GOVERNANCE_REVIEW_UNTRACKED_PATHS,
    GitGovernancePolicy,
    canonical_git_governance_json,
    compute_git_governance_hash,
    evaluate_git_read_governance,
)
from runtime.git_ops.git_read import GIT_READ_BLOCKED, GIT_READ_ERROR, GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate
from runtime.safety.write_kill_switch import WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_GOVERNANCE_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_governance.py"
GIT_READ_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_read.py"
STEP26_MODULE = REPO_ROOT / "runtime" / "patches" / "post_patch_controlled_test_integration.py"
CONTENT = "# controlled content\n"
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


class GitReadOnlyGovernance1ATests(unittest.TestCase):
    def test_valid_clean_git_read_result_passes_under_strict_policy_as_metadata_only(self):
        result = evaluate_git_read_governance(self.git_read(), GitGovernancePolicy(expected_branch="main"))

        self.assertEqual(GIT_GOVERNANCE_PASS, result.status)
        self.assertEqual(self.git_read().git_read_hash, result.input_git_read_hash)
        self.assertEqual((), result.findings)
        self.assertEqual(("GIT_GOVERNANCE_PASS_METADATA_ONLY",), result.reason_codes)
        self.assert_authority_false(result)

    def test_missing_malformed_error_and_blocked_git_read_results_block(self):
        cases = {
            "missing": (None, GIT_GOVERNANCE_BLOCKED_MISSING_INPUT),
            "malformed": ({}, GIT_GOVERNANCE_BLOCKED_MALFORMED_INPUT),
            "error": (replace(self.git_read(), status=GIT_READ_ERROR), GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS),
            "blocked": (replace(self.git_read(), status=GIT_READ_BLOCKED), GIT_GOVERNANCE_BLOCKED_GIT_READ_STATUS),
        }
        for name, (candidate, code) in cases.items():
            with self.subTest(name=name):
                result = evaluate_git_read_governance(candidate)

                self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
                self.assertIn(code, result.reason_codes)
                self.assert_authority_false(result)

    def test_missing_hash_repo_root_and_head_block(self):
        base = self.git_read().to_dict()
        cases = {
            "hash": ({**base, "git_read_hash": None}, GIT_GOVERNANCE_BLOCKED_MISSING_HASH),
            "repo": ({**base, "repo_root": None}, GIT_GOVERNANCE_BLOCKED_MISSING_REPO_ROOT),
            "head": ({**base, "head_sha": None}, GIT_GOVERNANCE_BLOCKED_MISSING_HEAD),
        }
        for name, (candidate, code) in cases.items():
            with self.subTest(name=name):
                result = evaluate_git_read_governance(candidate)

                self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
                self.assertIn(code, result.reason_codes)

    def test_detached_head_blocks_by_default(self):
        result = evaluate_git_read_governance(replace(self.git_read(), detached_head=True, branch_name=None))

        self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
        self.assertIn(GIT_GOVERNANCE_BLOCKED_DETACHED_HEAD, result.reason_codes)

    def test_expected_branch_mismatch_blocks_and_match_passes(self):
        mismatch = evaluate_git_read_governance(self.git_read(branch_name="feature"), GitGovernancePolicy(expected_branch="main"))
        match = evaluate_git_read_governance(self.git_read(branch_name="main"), GitGovernancePolicy(expected_branch="main"))

        self.assertEqual(GIT_GOVERNANCE_BLOCK, mismatch.status)
        self.assertIn(GIT_GOVERNANCE_BLOCKED_BRANCH_MISMATCH, mismatch.reason_codes)
        self.assertEqual(GIT_GOVERNANCE_PASS, match.status)

    def test_allowed_branches_policy_is_deterministic_and_can_review_or_block(self):
        review_policy = GitGovernancePolicy(allowed_branches=("main", "release"), review_branch_not_allowed=True, require_clean_worktree=True)
        block_policy = GitGovernancePolicy(allowed_branches=("main", "release"), review_branch_not_allowed=False)

        first = evaluate_git_read_governance(self.git_read(branch_name="topic"), review_policy)
        second = evaluate_git_read_governance(self.git_read(branch_name="topic"), GitGovernancePolicy(allowed_branches=("release", "main"), review_branch_not_allowed=True))
        blocked = evaluate_git_read_governance(self.git_read(branch_name="topic"), block_policy)

        self.assertEqual(GIT_GOVERNANCE_NEEDS_REVIEW, first.status)
        self.assertEqual(first.governance_hash, second.governance_hash)
        self.assertEqual(GIT_GOVERNANCE_BLOCK, blocked.status)

    def test_dirty_state_blocks_when_require_clean_and_reviews_when_not_required(self):
        dirty = self.git_read(clean=False, unstaged_paths=("docs/readme.md",))

        blocked = evaluate_git_read_governance(dirty)
        review = evaluate_git_read_governance(dirty, GitGovernancePolicy(require_clean_worktree=False))

        self.assertEqual(GIT_GOVERNANCE_BLOCK, blocked.status)
        self.assertIn(GIT_GOVERNANCE_BLOCKED_DIRTY_WORKTREE, blocked.reason_codes)
        self.assertEqual(GIT_GOVERNANCE_NEEDS_REVIEW, review.status)
        self.assertIn(GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS, review.reason_codes)

    def test_staged_unstaged_and_untracked_paths_review_or_block_according_to_policy(self):
        dirty = self.git_read(
            clean=False,
            staged_paths=("docs/a.md",),
            unstaged_paths=("docs/b.md",),
            untracked_paths=("docs/c.md",),
        )

        review = evaluate_git_read_governance(dirty, GitGovernancePolicy(require_clean_worktree=False))
        blocked = evaluate_git_read_governance(dirty, GitGovernancePolicy(require_clean_worktree=True))

        self.assertEqual(GIT_GOVERNANCE_NEEDS_REVIEW, review.status)
        self.assertIn(GIT_GOVERNANCE_REVIEW_STAGED_PATHS, review.reason_codes)
        self.assertIn(GIT_GOVERNANCE_REVIEW_UNSTAGED_PATHS, review.reason_codes)
        self.assertIn(GIT_GOVERNANCE_REVIEW_UNTRACKED_PATHS, review.reason_codes)
        self.assertEqual(GIT_GOVERNANCE_BLOCK, blocked.status)

    def test_protected_path_changes_block_by_default(self):
        result = evaluate_git_read_governance(
            self.git_read(clean=False, unstaged_paths=("runtime/git_ops/git_governance.py",)),
            GitGovernancePolicy(require_clean_worktree=False),
        )

        self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
        self.assertIn(GIT_GOVERNANCE_BLOCKED_PROTECTED_PATH, result.reason_codes)

    def test_gitmodules_and_gitattributes_risk_classified(self):
        for path in (".gitmodules", ".gitattributes"):
            with self.subTest(path=path):
                result = evaluate_git_read_governance(
                    self.git_read(clean=False, untracked_paths=(path,)),
                    GitGovernancePolicy(require_clean_worktree=False),
                )

                self.assertEqual(GIT_GOVERNANCE_NEEDS_REVIEW, result.status)
                self.assertIn(GIT_GOVERNANCE_REVIEW_GIT_ATTRIBUTE_RISK, result.reason_codes)

    def test_traversal_and_pathspec_magic_paths_block(self):
        for path in ("../escape", ":(glob)*", "docs/:(attr)x", ":(top)README.md"):
            with self.subTest(path=path):
                result = evaluate_git_read_governance(
                    self.git_read(clean=False, untracked_paths=(path,)),
                    GitGovernancePolicy(require_clean_worktree=False),
                )

                self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
                self.assertIn(GIT_GOVERNANCE_BLOCKED_UNSAFE_PATH, result.reason_codes)

    def test_command_evidence_raw_text_sanitizer_output_timeout_and_failure_block(self):
        cases = {
            "raw": ([{**self.evidence().to_dict(), "command_text": "git status"}], GIT_GOVERNANCE_BLOCKED_RAW_COMMAND_TEXT),
            "sanitize": ([{**self.evidence().to_dict(), "stdout_preview": "ghp_unredactedsecretvalue123"}], GIT_GOVERNANCE_BLOCKED_SANITIZER),
            "bounded": ([replace(self.evidence(), stdout_truncated=True).to_dict()], GIT_GOVERNANCE_BLOCKED_OUTPUT_BOUND),
            "timeout": ([replace(self.evidence(), timeout_expired=True).to_dict()], GIT_GOVERNANCE_BLOCKED_TIMEOUT),
            "failure": ([replace(self.evidence(), status="ERROR", reason_code="GIT_READ_ERROR_EXIT_CODE").to_dict()], GIT_GOVERNANCE_BLOCKED_COMMAND_EVIDENCE),
        }
        for name, (evidence, code) in cases.items():
            with self.subTest(name=name):
                candidate = self.git_read().to_dict()
                candidate["command_evidence"] = evidence
                result = evaluate_git_read_governance(candidate)

                self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
                self.assertIn(code, result.reason_codes)

    def test_authority_claims_in_git_read_evidence_block(self):
        for field in ("can_commit", "can_push", "provider_authority_granted", "git_write_authority_granted"):
            with self.subTest(field=field):
                candidate = self.git_read().to_dict()
                candidate[field] = True
                result = evaluate_git_read_governance(candidate)

                self.assertEqual(GIT_GOVERNANCE_BLOCK, result.status)
                self.assertIn(GIT_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM, result.reason_codes)

    def test_governance_canonical_json_and_hash_are_deterministic(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        first = evaluate_git_read_governance(self.git_read())
        second = evaluate_git_read_governance(self.git_read())

        self.assertEqual(canonical_git_governance_json(left), canonical_git_governance_json(right))
        self.assertEqual(compute_git_governance_hash(left), compute_git_governance_hash(right))
        self.assertEqual(first.governance_hash, second.governance_hash)

    def test_governance_hash_changes_when_git_read_hash_or_policy_changes(self):
        base = evaluate_git_read_governance(self.git_read())
        changed_input = evaluate_git_read_governance(replace(self.git_read(), git_read_hash="b" * 64))
        changed_policy = evaluate_git_read_governance(self.git_read(), GitGovernancePolicy(expected_branch="main"))

        self.assertNotEqual(base.governance_hash, changed_input.governance_hash)
        self.assertNotEqual(base.governance_hash, changed_policy.governance_hash)

    def test_findings_sorted_and_path_order_does_not_change_result(self):
        left = evaluate_git_read_governance(
            self.git_read(clean=False, staged_paths=("docs/b.md", "docs/a.md")),
            GitGovernancePolicy(require_clean_worktree=False),
        )
        right = evaluate_git_read_governance(
            self.git_read(clean=False, staged_paths=("docs/a.md", "docs/b.md")),
            GitGovernancePolicy(require_clean_worktree=False),
        )

        self.assertEqual(left.governance_hash, right.governance_hash)
        self.assertEqual(left.to_dict(), right.to_dict())
        self.assertEqual(tuple(sorted(left.findings, key=lambda item: item.reason_code)), left.findings)

    def test_governance_result_cannot_satisfy_control_write_gate_or_commit_push_authority(self):
        governance = evaluate_git_read_governance(self.git_read())
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=governance,
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)
        self.assert_authority_false(governance)

    def test_static_governance_module_imports_no_subprocess_network_provider_browser_or_package_libs(self):
        scan = scan_module(GIT_GOVERNANCE_MODULE)
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
        source = GIT_GOVERNANCE_MODULE.read_text(encoding="utf-8").casefold()
        self.assertNotIn("shell=true", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv", source)
        self.assertNotIn("api.github.com", source)

    def test_static_boundary_keeps_subprocess_out_of_step28_governance(self):
        allowed = {STEP26_MODULE, GIT_READ_MODULE}
        for path in (STEP26_MODULE, GIT_READ_MODULE, GIT_GOVERNANCE_MODULE):
            scan = scan_module(path)
            if path in allowed:
                self.assertNotIn("subprocess.run", scan.calls)
                self.assertIn(
                    "runtime.safety.bounded_subprocess.run_bounded_subprocess",
                    scan.calls,
                )
            else:
                self.assertNotIn("subprocess", scan.imports)
                self.assertNotIn("subprocess.run", scan.calls)

    def test_no_github_api_network_provider_or_env_secret_capability_added(self):
        text = GIT_GOVERNANCE_MODULE.read_text(encoding="utf-8").casefold()
        forbidden = (
            "api.github.com",
            "ls-remote",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "os.environ",
            "getenv",
            "api_key",
        )

        self.assertEqual([], [item for item in forbidden if item in text])

    def git_read(
        self,
        *,
        status: str = GIT_READ_READY,
        git_read_hash: str = "a" * 64,
        repo_root: str = "/workspace/repo",
        head_sha: str = "1" * 40,
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
                reason="control-write regression",
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
