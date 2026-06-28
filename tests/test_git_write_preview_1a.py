from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, ControlWriteContext, write_preview_artifact_after_human_gate
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, compute_git_checkpoint_hash, create_git_state_checkpoint
from runtime.git_ops.git_governance import GIT_GOVERNANCE_BLOCK, GIT_GOVERNANCE_NEEDS_REVIEW, GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.git_ops.git_write_preview import (
    GIT_WRITE_PREVIEW_BLOCKED,
    GIT_WRITE_PREVIEW_BLOCKED_ABSOLUTE_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
    GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_INVALID,
    GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND,
    GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA,
    GIT_WRITE_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_GIT_INTERNAL_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_BLOCK,
    GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_REVIEW,
    GIT_WRITE_PREVIEW_BLOCKED_HASH_MISMATCH,
    GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT,
    GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH,
    GIT_WRITE_PREVIEW_BLOCKED_MISSING_OPERATION_KIND,
    GIT_WRITE_PREVIEW_BLOCKED_MISSING_TARGET_PATHS,
    GIT_WRITE_PREVIEW_BLOCKED_OPTION_LIKE_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_PATHSPEC_MAGIC,
    GIT_WRITE_PREVIEW_BLOCKED_PROTECTED_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT,
    GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT,
    GIT_WRITE_PREVIEW_BLOCKED_REPLAY_MISMATCH,
    GIT_WRITE_PREVIEW_BLOCKED_SHELL_TEXT,
    GIT_WRITE_PREVIEW_BLOCKED_TRAVERSAL_PATH,
    GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND,
    GIT_WRITE_PREVIEW_CREATED,
    GIT_WRITE_PREVIEW_VALID,
    GitWriteIntent,
    GitWritePreviewPolicy,
    GitWritePreviewRequest,
    canonical_git_write_preview_json,
    compute_git_write_preview_hash,
    create_git_write_preview,
    verify_git_write_preview,
)
from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_write_preview.py"
CONTENT = "# git write preview evidence\n"
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


class GitWritePreview1ATests(unittest.TestCase):
    def test_valid_checkpoint_with_pass_governance_creates_local_commit_intent_preview(self):
        result = self.preview()

        self.assertEqual(GIT_WRITE_PREVIEW_CREATED, result.status)
        preview = result.preview
        self.assertEqual(self.checkpoint().checkpoint_hash, preview.checkpoint_hash)
        self.assertEqual(self.checkpoint().git_read_hash, preview.git_read_hash)
        self.assertEqual(self.checkpoint().governance_hash, preview.governance_hash)
        self.assertEqual(self.checkpoint().repo_identity_hash, preview.repo_identity_hash)
        self.assertEqual(self.checkpoint().head_sha, preview.head_sha)
        self.assertEqual(self.checkpoint().branch_name, preview.branch_name)
        self.assertEqual(GitWriteIntent.LOCAL_COMMIT_INTENT.value, preview.operation_kind)
        self.assertEqual(("runtime/example.py",), preview.target_paths)
        self.assert_authority_false(result)
        self.assert_authority_false(preview)

    def test_needs_review_blocks_by_default_and_can_be_allowed_explicitly(self):
        checkpoint = self.checkpoint(governance_status=GIT_GOVERNANCE_NEEDS_REVIEW)

        blocked = self.preview(checkpoint=checkpoint)
        allowed = self.preview(checkpoint=checkpoint, policy=GitWritePreviewPolicy(allow_review_previews=True))

        self.assertIn(GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_REVIEW, blocked.reason_codes)
        self.assertEqual(GIT_WRITE_PREVIEW_CREATED, allowed.status)

    def test_governance_block_blocks_preview(self):
        result = self.preview(checkpoint=self.checkpoint_dict(governance_status=GIT_GOVERNANCE_BLOCK))

        self.assertIn(GIT_WRITE_PREVIEW_BLOCKED_GOVERNANCE_BLOCK, result.reason_codes)

    def test_missing_invalid_checkpoint_schema_kind_and_hash_block(self):
        checkpoint = self.checkpoint().to_dict()
        cases = {
            "missing": (None, GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT),
            "hash": ({**checkpoint, "checkpoint_hash": None}, GIT_WRITE_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH),
            "invalid": ({**checkpoint, "head_sha": "2" * 40}, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_INVALID),
            "kind": ({**checkpoint, "checkpoint_kind": "WRONG"}, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_KIND),
            "schema": ({**checkpoint, "schema_version": "WRONG"}, GIT_WRITE_PREVIEW_BLOCKED_CHECKPOINT_SCHEMA),
        }
        for name, (candidate, code) in cases.items():
            with self.subTest(name=name):
                result = self.preview(checkpoint=candidate)
                self.assertEqual(GIT_WRITE_PREVIEW_BLOCKED, result.status)
                self.assertIn(code, result.reason_codes)

    def test_authority_claims_in_checkpoint_request_or_metadata_block(self):
        checkpoint = self.checkpoint().to_dict()
        cases = (
            {"checkpoint": {**checkpoint, "can_commit": True}},
            {"claims": {"can_approve": True}},
            {"claims": {"can_write": True}},
            {"claims": {"can_commit": True}},
            {"claims": {"can_push": True}},
            {"claims": {"can_call_provider": True}},
            {"metadata": {"note": "provider authority"}},
        )
        for case in cases:
            with self.subTest(case=case):
                result = self.preview(**case)
                self.assertIn(GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM, result.reason_codes)

    def test_operation_kind_blocks_missing_unsupported_push_and_github(self):
        cases = {
            "missing": (None, GIT_WRITE_PREVIEW_BLOCKED_MISSING_OPERATION_KIND),
            "unsupported": ("LOCAL_BRANCH_INTENT", GIT_WRITE_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND),
            "push": (GitWriteIntent.LOCAL_PUSH_INTENT, GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT),
            "github": (GitWriteIntent.GITHUB_WRITE_INTENT, GIT_WRITE_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT),
        }
        for name, (kind, code) in cases.items():
            with self.subTest(name=name):
                result = self.preview(operation_kind=kind)
                self.assertIn(code, result.reason_codes)

    def test_target_path_policy_blocks_invalid_paths(self):
        cases = {
            "missing": (None, GIT_WRITE_PREVIEW_BLOCKED_MISSING_TARGET_PATHS),
            "duplicate": (("docs/a.md", "docs//a.md"), GIT_WRITE_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH),
            "traversal": (("../escape",), GIT_WRITE_PREVIEW_BLOCKED_TRAVERSAL_PATH),
            "pathspec": ((":(glob)*",), GIT_WRITE_PREVIEW_BLOCKED_PATHSPEC_MAGIC),
            "dash": (("--force",), GIT_WRITE_PREVIEW_BLOCKED_OPTION_LIKE_PATH),
            "absolute": (("/tmp/a",), GIT_WRITE_PREVIEW_BLOCKED_ABSOLUTE_PATH),
            "git-internal": ((".git/config",), GIT_WRITE_PREVIEW_BLOCKED_GIT_INTERNAL_PATH),
            "protected": (("runtime/git_ops/git_write_preview.py",), GIT_WRITE_PREVIEW_BLOCKED_PROTECTED_PATH),
            "gitmodules": ((".gitmodules",), GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH),
            "gitattributes": ((".gitattributes",), GIT_WRITE_PREVIEW_BLOCKED_GIT_METADATA_PATH),
        }
        for name, (paths, code) in cases.items():
            with self.subTest(name=name):
                result = self.preview(target_paths=paths)
                self.assertIn(code, result.reason_codes)

    def test_raw_git_shell_and_provider_text_block(self):
        cases = {
            "raw-key": ({"command": "git add x"}, GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT),
            "raw-text": ({"note": "git commit -m x"}, GIT_WRITE_PREVIEW_BLOCKED_RAW_COMMAND_TEXT),
            "shell": ({"note": "echo x && git status"}, GIT_WRITE_PREVIEW_BLOCKED_SHELL_TEXT),
            "provider": ({"note": "permission to commit"}, GIT_WRITE_PREVIEW_BLOCKED_AUTHORITY_CLAIM),
        }
        for name, (metadata, code) in cases.items():
            with self.subTest(name=name):
                result = self.preview(metadata=metadata)
                self.assertIn(code, result.reason_codes)

    def test_canonical_preview_json_and_hash_are_deterministic(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        first = self.preview().preview
        second = self.preview().preview

        self.assertEqual(canonical_git_write_preview_json(left), canonical_git_write_preview_json(right))
        self.assertEqual(compute_git_write_preview_hash(left), compute_git_write_preview_hash(right))
        self.assertEqual(first.preview_hash, second.preview_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_preview_hash_changes_for_bound_inputs_and_policy(self):
        base = self.preview().preview.preview_hash
        cases = (
            self.preview(checkpoint=self.checkpoint(checkpoint_hash_seed="b" * 64)).preview.preview_hash,
            self.preview(checkpoint=self.checkpoint(git_read_hash="c" * 64)).preview.preview_hash,
            self.preview(checkpoint=self.checkpoint(governance_hash="d" * 64)).preview.preview_hash,
            self.preview(checkpoint=self.checkpoint(head_sha="2" * 40)).preview.preview_hash,
            self.preview(checkpoint=self.checkpoint(branch_name="release")).preview.preview_hash,
            self.preview(operation_kind="LOCAL_REVIEW_INTENT").reason_codes,
            self.preview(target_paths=("docs/b.md",)).preview.preview_hash,
            self.preview(policy=GitWritePreviewPolicy(policy_version="2A")).preview.preview_hash,
        )
        for value in cases:
            self.assertNotEqual(base, value)

    def test_path_and_finding_order_do_not_change_canonical_result(self):
        left = self.preview(target_paths=("docs/b.md", "docs/a.md")).preview
        right = self.preview(target_paths=("docs/a.md", "docs/b.md")).preview

        self.assertEqual(left.preview_hash, right.preview_hash)
        self.assertEqual(left.to_dict(), right.to_dict())

    def test_verification_accepts_exact_checkpoint_and_rejects_replay(self):
        checkpoint = self.checkpoint()
        preview = self.preview(checkpoint=checkpoint).preview

        valid = verify_git_write_preview(preview, checkpoint)
        changed_checkpoint = self.checkpoint(head_sha="2" * 40)
        replay = verify_git_write_preview(preview, changed_checkpoint)

        self.assertEqual(GIT_WRITE_PREVIEW_VALID, valid.status)
        self.assertIn(GIT_WRITE_PREVIEW_BLOCKED_REPLAY_MISMATCH, replay.reason_codes)

    def test_verification_rejects_changed_preview_hash_head_branch_and_target_path_hash(self):
        checkpoint = self.checkpoint()
        preview = self.preview(checkpoint=checkpoint).preview.to_dict()
        cases = (
            {**preview, "preview_hash": "f" * 64},
            {**preview, "head_sha": "2" * 40},
            {**preview, "branch_name": "release"},
            {**preview, "target_paths_hash": "e" * 64},
        )
        for candidate in cases:
            with self.subTest(candidate=candidate):
                result = verify_git_write_preview(candidate, checkpoint)
                self.assertIn(result.status, ("INVALID", "BLOCKED"))

    def test_preview_cannot_satisfy_control_write_gate_or_commit_push_authority(self):
        preview_result = self.preview()
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace:
            result = write_preview_artifact_after_human_gate(
                preview=self.artifact_preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=preview_result,
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)
        self.assert_authority_false(preview_result)
        self.assert_authority_false(preview_result.preview)

    def test_valid_preview_cannot_bypass_hash_workspace_or_future_authority_checks(self):
        preview = self.preview().preview

        self.assertFalse(preview.can_write)
        self.assertFalse(preview.can_commit)
        self.assertFalse(preview.can_push)
        self.assertFalse(preview.can_call_provider)

    def test_preview_module_imports_no_subprocess_network_provider_browser_package_or_env_libs(self):
        scan = scan_module(PREVIEW_MODULE)
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
        source = PREVIEW_MODULE.read_text(encoding="utf-8").casefold()
        for forbidden in ("shell=true", "api.github.com", "os.environ", "getenv", "api_key", "git tag", "git branch", "refs/tags", "refs/heads"):
            self.assertNotIn(forbidden, source)

    def preview(
        self,
        *,
        checkpoint=DEFAULT,
        operation_kind=GitWriteIntent.LOCAL_COMMIT_INTENT,
        target_paths=("runtime/example.py",),
        policy=None,
        metadata=None,
        claims=None,
    ):
        if checkpoint is DEFAULT:
            checkpoint = self.checkpoint()
        return create_git_write_preview(
            GitWritePreviewRequest(
                checkpoint=checkpoint,
                operation_kind=operation_kind,
                target_paths=target_paths,
                target_branch="feature/m2-b0-provider-critic-inert-core",
                created_at="2026-06-28T00:00:00Z",
                preview_nonce="preview-session",
                policy=policy,
                metadata=metadata,
                claims=claims,
            )
        )

    def checkpoint(
        self,
        *,
        governance_status=GIT_GOVERNANCE_PASS,
        checkpoint_hash_seed=None,
        git_read_hash="a" * 64,
        governance_hash="b" * 64,
        head_sha="1" * 40,
        branch_name="main",
    ):
        git_read = GitReadResult(
            status=GIT_READ_READY,
            git_read_hash=git_read_hash,
            repo_root="/workspace/repo",
            head_sha=head_sha,
            branch_name=branch_name,
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
            status=governance_status,
            governance_hash=governance_hash,
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
                created_at="2026-06-28T00:00:00Z",
                checkpoint_nonce=checkpoint_hash_seed or "checkpoint-session",
                allow_review_checkpoint=True,
            )
        )
        return result.checkpoint

    def checkpoint_dict(self, **kwargs):
        governance_status = kwargs.pop("governance_status", None)
        data = self.checkpoint(**kwargs).to_dict()
        if governance_status is not None:
            data["governance_status"] = governance_status
        material = dict(data)
        material.pop("checkpoint_hash", None)
        for field in AUTHORITY_FIELDS:
            material.pop(field, None)
        data["checkpoint_hash"] = compute_git_checkpoint_hash(material)
        return data

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
    def artifact_preview():
        return build_artifact_preview(
            ArtifactPreviewRequest(target_path="artifact.md", proposed_content=CONTENT, original_content="", reason="git write preview regression")
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
