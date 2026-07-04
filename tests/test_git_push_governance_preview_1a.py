from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, ControlWriteContext, write_preview_artifact_after_human_gate
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, compute_git_checkpoint_hash, create_git_state_checkpoint
from runtime.git_ops.git_governance import GIT_GOVERNANCE_BLOCK, GIT_GOVERNANCE_NEEDS_REVIEW, GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_push_preview import (
    GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
    GIT_PUSH_PREVIEW_BLOCKED_BRANCH_MISMATCH,
    GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_INVALID,
    GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE,
    GIT_PUSH_PREVIEW_BLOCKED_DETACHED_HEAD,
    GIT_PUSH_PREVIEW_BLOCKED_DUPLICATE_COMMIT,
    GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_BLOCK,
    GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_REVIEW,
    GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_LOCAL_HEAD,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_NAME,
    GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_REF,
    GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT,
    GIT_PUSH_PREVIEW_BLOCKED_REMOTE_HEAD,
    GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH,
    GIT_PUSH_PREVIEW_BLOCKED_SHELL_TEXT,
    GIT_PUSH_PREVIEW_BLOCKED_TAG_REF,
    GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_NAME,
    GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_REF,
    GIT_PUSH_PREVIEW_CREATED,
    GIT_PUSH_PREVIEW_NEEDS_REVIEW,
    GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS,
    GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD,
    GIT_PUSH_PREVIEW_REVIEW_REMOTE_DIVERGED,
    GIT_PUSH_PREVIEW_VALID,
    GitPushPreviewPolicy,
    GitPushPreviewRequest,
    canonical_git_push_preview_json,
    compute_git_push_preview_hash,
    create_git_push_preview,
    verify_git_push_preview,
)
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_push_preview.py"
CONTENT = "# git push preview evidence\n"
PACKET_HASH = "a" * 64
BRANCH = "feature/m2-b0-provider-critic-inert-core"
REMOTE_REF = "refs/heads/feature/m2-b0-provider-critic-inert-core"
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


class GitPushGovernancePreview1ATests(unittest.TestCase):
    def test_valid_checkpoint_creates_push_preview_with_remote_evidence(self):
        checkpoint = self.checkpoint()
        result = self.preview(checkpoint=checkpoint)

        self.assertEqual(GIT_PUSH_PREVIEW_CREATED, result.status)
        preview = result.preview
        self.assertEqual("1A", preview.schema_version)
        self.assertEqual("/workspace/repo", preview.repo_path)
        self.assertEqual(BRANCH, preview.branch)
        self.assertEqual("origin", preview.remote_name)
        self.assertEqual(REMOTE_REF, preview.remote_ref)
        self.assertEqual(checkpoint.head_sha, preview.local_head)
        self.assertEqual("2" * 40, preview.remote_head)
        self.assertEqual(("1" * 40,), preview.commits_ahead)
        self.assertEqual((), preview.commits_behind)
        self.assertTrue(preview.push_would_update_remote)
        self.assertTrue(preview.push_would_be_fast_forward)
        self.assertTrue(preview.requires_human_barrier)
        self.assertEqual(checkpoint.checkpoint_hash, preview.checkpoint_hash)
        self.assertEqual(checkpoint.git_read_hash, preview.git_read_hash)
        self.assertEqual(checkpoint.governance_hash, preview.governance_hash)
        self.assertEqual(checkpoint.repo_identity_hash, preview.repo_identity_hash)
        self.assert_authority_false(result)
        self.assert_authority_false(preview)

    def test_review_checkpoint_blocks_by_default_and_can_be_allowed(self):
        checkpoint = self.checkpoint(governance_status=GIT_GOVERNANCE_NEEDS_REVIEW)

        blocked = self.preview(checkpoint=checkpoint)
        allowed = self.preview(checkpoint=checkpoint, policy=GitPushPreviewPolicy(allow_review_previews=True))

        self.assertIn(GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_REVIEW, blocked.reason_codes)
        self.assertEqual(GIT_PUSH_PREVIEW_CREATED, allowed.status)

    def test_governance_block_blocks_push_preview(self):
        result = self.preview(checkpoint=self.checkpoint_dict(governance_status=GIT_GOVERNANCE_BLOCK))

        self.assertIn(GIT_PUSH_PREVIEW_BLOCKED_GOVERNANCE_BLOCK, result.reason_codes)

    def test_missing_invalid_checkpoint_branch_and_head_block(self):
        checkpoint = self.checkpoint().to_dict()
        cases = {
            "missing": (None, GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT),
            "missing-hash": ({**checkpoint, "checkpoint_hash": None}, GIT_PUSH_PREVIEW_BLOCKED_MISSING_CHECKPOINT_HASH),
            "invalid": ({**checkpoint, "head_sha": "2" * 40}, GIT_PUSH_PREVIEW_BLOCKED_CHECKPOINT_INVALID),
            "missing-head": (self.rehashed_checkpoint(checkpoint, head_sha=""), GIT_PUSH_PREVIEW_BLOCKED_MISSING_LOCAL_HEAD),
            "missing-branch": (self.rehashed_checkpoint(checkpoint, branch_name=None), GIT_PUSH_PREVIEW_BLOCKED_MISSING_BRANCH),
            "detached": (self.rehashed_checkpoint(checkpoint, detached_head=True), GIT_PUSH_PREVIEW_BLOCKED_DETACHED_HEAD),
        }
        for name, (candidate, code) in cases.items():
            with self.subTest(name=name):
                result = self.preview(checkpoint=candidate)
                self.assertIn(code, result.reason_codes)

        mismatch = self.preview(branch="release")
        self.assertIn(GIT_PUSH_PREVIEW_BLOCKED_BRANCH_MISMATCH, mismatch.reason_codes)

    def test_remote_name_ref_head_and_commit_evidence_policy_blocks_invalid_inputs(self):
        cases = {
            "missing-remote": {"remote_name": None, "code": GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_NAME},
            "unsafe-remote": {"remote_name": "origin/evil", "code": GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_NAME},
            "missing-ref": {"remote_ref": None, "code": GIT_PUSH_PREVIEW_BLOCKED_MISSING_REMOTE_REF},
            "unsafe-ref": {"remote_ref": "../main", "code": GIT_PUSH_PREVIEW_BLOCKED_UNSAFE_REMOTE_REF},
            "tag-ref": {"remote_ref": "refs/tags/v1", "code": GIT_PUSH_PREVIEW_BLOCKED_TAG_REF},
            "bad-remote-head": {"remote_head": "not-a-sha", "code": GIT_PUSH_PREVIEW_BLOCKED_REMOTE_HEAD},
            "bad-ahead": {"commits_ahead": ("not-a-sha",), "code": GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE},
            "non-string-ahead": {"commits_ahead": (123,), "code": GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE},
            "bad-behind": {"commits_behind": ("not-a-sha",), "code": GIT_PUSH_PREVIEW_BLOCKED_COMMIT_EVIDENCE},
            "duplicate-ahead": {"commits_ahead": ("1" * 40, "1" * 40), "code": GIT_PUSH_PREVIEW_BLOCKED_DUPLICATE_COMMIT},
        }
        for name, case in cases.items():
            with self.subTest(name=name):
                code = case.pop("code")
                result = self.preview(**case)
                self.assertIn(code, result.reason_codes)

    def test_new_remote_ref_diverged_remote_and_noop_are_review_metadata(self):
        new_remote = self.preview(remote_head=None)
        diverged = self.preview(commits_behind=("3" * 40,))
        noop = self.preview(commits_ahead=())

        self.assertEqual(GIT_PUSH_PREVIEW_CREATED, new_remote.status)
        self.assertEqual(GIT_PUSH_PREVIEW_NEEDS_REVIEW, new_remote.preview.status)
        self.assertIn(GIT_PUSH_PREVIEW_REVIEW_NO_REMOTE_HEAD, new_remote.preview.risk_flags)
        self.assertFalse(new_remote.preview.push_would_be_fast_forward)

        self.assertEqual(GIT_PUSH_PREVIEW_CREATED, diverged.status)
        self.assertEqual(GIT_PUSH_PREVIEW_NEEDS_REVIEW, diverged.preview.status)
        self.assertIn(GIT_PUSH_PREVIEW_REVIEW_REMOTE_DIVERGED, diverged.preview.risk_flags)
        self.assertFalse(diverged.preview.push_would_be_fast_forward)

        self.assertEqual(GIT_PUSH_PREVIEW_CREATED, noop.status)
        self.assertEqual(GIT_PUSH_PREVIEW_NEEDS_REVIEW, noop.preview.status)
        self.assertIn(GIT_PUSH_PREVIEW_REVIEW_NO_AHEAD_COMMITS, noop.preview.risk_flags)
        self.assertFalse(noop.preview.push_would_update_remote)

    def test_authority_raw_command_and_shell_metadata_block(self):
        cases = {
            "authority-claim": {"claims": {"can_push": True}, "code": GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM},
            "authority-metadata": {"metadata": {"note": "permission to push"}, "code": GIT_PUSH_PREVIEW_BLOCKED_AUTHORITY_CLAIM},
            "raw-key": {"metadata": {"command": "push origin branch"}, "code": GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT},
            "raw-text": {"metadata": {"note": "git remote update"}, "code": GIT_PUSH_PREVIEW_BLOCKED_RAW_COMMAND_TEXT},
            "shell": {"metadata": {"note": "push && notify"}, "code": GIT_PUSH_PREVIEW_BLOCKED_SHELL_TEXT},
        }
        for name, case in cases.items():
            with self.subTest(name=name):
                code = case.pop("code")
                result = self.preview(**case)
                self.assertIn(code, result.reason_codes)

    def test_canonical_json_and_hash_are_deterministic_and_bound_to_remote_evidence(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        first = self.preview().preview
        second = self.preview().preview
        base = first.preview_hash
        changed = (
            self.preview(remote_name="upstream").preview.preview_hash,
            self.preview(remote_ref="refs/heads/release").preview.preview_hash,
            self.preview(remote_head="3" * 40).preview.preview_hash,
            self.preview(commits_ahead=("4" * 40,)).preview.preview_hash,
            self.preview(commits_behind=("5" * 40,)).preview.preview_hash,
            self.preview(policy=GitPushPreviewPolicy(policy_version="2A")).preview.preview_hash,
        )

        self.assertEqual(canonical_git_push_preview_json(left), canonical_git_push_preview_json(right))
        self.assertEqual(compute_git_push_preview_hash(left), compute_git_push_preview_hash(right))
        self.assertEqual(first.preview_hash, second.preview_hash)
        self.assertEqual(first.to_dict(), second.to_dict())
        for value in changed:
            self.assertNotEqual(base, value)

    def test_verification_accepts_exact_evidence_and_rejects_tampering_or_replay(self):
        checkpoint = self.checkpoint()
        preview = self.preview(checkpoint=checkpoint).preview
        changed_checkpoint = self.checkpoint(head_sha="6" * 40)

        valid = verify_git_push_preview(preview, checkpoint)
        cases = (
            verify_git_push_preview({**preview.to_dict(), "preview_hash": "f" * 64}, checkpoint),
            verify_git_push_preview({**preview.to_dict(), "checkpoint_hash": changed_checkpoint.checkpoint_hash}, checkpoint),
            verify_git_push_preview({**preview.to_dict(), "git_read_hash": "e" * 64}, checkpoint),
            verify_git_push_preview({**preview.to_dict(), "requires_human_barrier": False}, checkpoint),
            verify_git_push_preview(preview, changed_checkpoint),
        )

        self.assertEqual(GIT_PUSH_PREVIEW_VALID, valid.status)
        for result in cases:
            self.assertIn(result.status, ("INVALID", "BLOCKED"))
            self.assertTrue(
                GIT_PUSH_PREVIEW_BLOCKED_HASH_MISMATCH in result.reason_codes
                or GIT_PUSH_PREVIEW_BLOCKED_REPLAY_MISMATCH in result.reason_codes
            )

    def test_push_preview_cannot_satisfy_control_write_gate_or_future_authority(self):
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

    def test_push_preview_module_imports_no_execution_network_provider_browser_package_or_env_libs(self):
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
        for forbidden in ("shell=true", "api.github.com", "os.environ", "getenv", "api_key", "subprocess.", "requests", "httpx"):
            self.assertNotIn(forbidden, source)

    def preview(
        self,
        *,
        checkpoint=DEFAULT,
        branch=BRANCH,
        remote_name="origin",
        remote_ref=REMOTE_REF,
        remote_head="2" * 40,
        commits_ahead=("1" * 40,),
        commits_behind=(),
        policy=None,
        metadata=None,
        claims=None,
    ):
        if checkpoint is DEFAULT:
            checkpoint = self.checkpoint()
        return create_git_push_preview(
            GitPushPreviewRequest(
                checkpoint=checkpoint,
                branch=branch,
                remote_name=remote_name,
                remote_ref=remote_ref,
                remote_head=remote_head,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind,
                created_at="2026-07-04T00:00:00Z",
                preview_nonce="push-preview-session",
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
        branch_name=BRANCH,
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
                created_at="2026-07-04T00:00:00Z",
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
        return self.rehashed_checkpoint(data)

    def rehashed_checkpoint(self, data, **updates):
        candidate = {**data, **updates}
        material = dict(candidate)
        material.pop("checkpoint_hash", None)
        for field in AUTHORITY_FIELDS:
            material.pop(field, None)
        candidate["checkpoint_hash"] = compute_git_checkpoint_hash(material)
        return candidate

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
            ArtifactPreviewRequest(target_path="artifact.md", proposed_content=CONTENT, original_content="", reason="git push preview regression")
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
