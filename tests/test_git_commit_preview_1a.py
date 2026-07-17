from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, ControlWriteContext, write_preview_artifact_after_human_gate
from runtime.git_ops.git_checkpoint import GitStateCheckpointRequest, compute_git_checkpoint_hash, create_git_state_checkpoint
from runtime.git_ops.git_commit_preview import (
    GIT_COMMIT_PREVIEW_BLOCKED_ABSOLUTE_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_ANSI_ESCAPE,
    GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
    GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_LANGUAGE,
    GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_HASH_MISMATCH,
    GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID,
    GIT_COMMIT_PREVIEW_BLOCKED_CONTROL_CHARACTER,
    GIT_COMMIT_PREVIEW_BLOCKED_CREDENTIAL_URL,
    GIT_COMMIT_PREVIEW_BLOCKED_DETACHED_HEAD,
    GIT_COMMIT_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER,
    GIT_COMMIT_PREVIEW_BLOCKED_GIT_INTERNAL_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_GITHUB_TOKEN,
    GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_BLOCK,
    GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_REVIEW,
    GIT_COMMIT_PREVIEW_BLOCKED_HASH_MISMATCH,
    GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_FIRST_LINE_LENGTH,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_BRANCH,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_CHECKPOINT,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_MESSAGE,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_PARENT_HEAD,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_TARGET_PATHS,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW,
    GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW_HASH,
    GIT_COMMIT_PREVIEW_BLOCKED_OPTION_LIKE_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_PATHSPEC_MAGIC,
    GIT_COMMIT_PREVIEW_BLOCKED_PROTECTED_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT,
    GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT,
    GIT_COMMIT_PREVIEW_BLOCKED_REPLAY_MISMATCH,
    GIT_COMMIT_PREVIEW_BLOCKED_SHELL_TEXT,
    GIT_COMMIT_PREVIEW_BLOCKED_SKIP_CI,
    GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH,
    GIT_COMMIT_PREVIEW_BLOCKED_TOKEN_FIELD,
    GIT_COMMIT_PREVIEW_BLOCKED_TRAVERSAL_PATH,
    GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND,
    GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_INVALID,
    GIT_COMMIT_PREVIEW_CREATED,
    GIT_COMMIT_PREVIEW_VALID,
    GitCommitPreviewPolicy,
    GitCommitPreviewRequest,
    canonical_git_commit_preview_json,
    compute_commit_message_hash,
    compute_git_commit_preview_hash,
    create_git_commit_preview,
    verify_git_commit_preview,
)
from runtime.git_ops.git_governance import GIT_GOVERNANCE_BLOCK, GIT_GOVERNANCE_NEEDS_REVIEW, GIT_GOVERNANCE_PASS, GitGovernanceResult
from runtime.git_ops.git_read import GIT_READ_READY, GitCommandEvidence, GitReadResult
from runtime.git_ops.git_write_preview import (
    GitWriteIntent,
    GitWritePreviewRequest,
    compute_git_write_preview_hash,
    create_git_write_preview,
)
from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate
from runtime.safety.write_kill_switch import WRITES_ENABLED


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_MODULE = REPO_ROOT / "runtime" / "git_ops" / "git_commit_preview.py"
CONTENT = "# git commit preview evidence\n"
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


class GitCommitPreview1ATests(unittest.TestCase):
    def test_valid_git_write_preview_creates_git_commit_preview_and_binds_evidence(self):
        checkpoint = self.checkpoint()
        write_preview = self.write_preview(checkpoint=checkpoint).preview
        result = self.commit_preview(write_preview=write_preview, checkpoint=checkpoint)

        self.assertEqual(GIT_COMMIT_PREVIEW_CREATED, result.status)
        preview = result.preview
        self.assertEqual(write_preview.preview_hash, preview.write_preview_hash)
        self.assertEqual(checkpoint.checkpoint_hash, preview.checkpoint_hash)
        self.assertEqual(checkpoint.git_read_hash, preview.git_read_hash)
        self.assertEqual(checkpoint.governance_hash, preview.governance_hash)
        self.assertEqual(checkpoint.repo_identity_hash, preview.repo_identity_hash)
        self.assertEqual(checkpoint.head_sha, preview.parent_head_sha)
        self.assertEqual(checkpoint.branch_name, preview.branch_name)
        self.assertEqual(write_preview.target_paths, preview.target_paths)
        self.assertEqual(compute_commit_message_hash("feat(git): add commit preview"), preview.commit_message_hash)
        self.assertEqual("AOIA_COMMIT_AUTHOR_POLICY", preview.author_policy_id)
        self.assert_authority_false(result)
        self.assert_authority_false(preview)

    def test_missing_invalid_write_preview_and_operation_kind_block(self):
        checkpoint = self.checkpoint()
        write_preview = self.write_preview(checkpoint=checkpoint).preview.to_dict()
        cases = {
            "missing": (None, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW),
            "missing-hash": ({**write_preview, "preview_hash": None}, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_WRITE_PREVIEW_HASH),
            "invalid": ({**write_preview, "head_sha": "2" * 40}, GIT_COMMIT_PREVIEW_BLOCKED_WRITE_PREVIEW_INVALID),
            "wrong-kind": (self.rehashed_write_preview(write_preview, operation_kind="LOCAL_BRANCH_INTENT"), GIT_COMMIT_PREVIEW_BLOCKED_UNSUPPORTED_OPERATION_KIND),
            "push": (self.rehashed_write_preview(write_preview, operation_kind=GitWriteIntent.LOCAL_PUSH_INTENT.value), GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT),
            "github": (self.rehashed_write_preview(write_preview, operation_kind=GitWriteIntent.GITHUB_WRITE_INTENT.value), GIT_COMMIT_PREVIEW_BLOCKED_PUSH_OR_GITHUB_INTENT),
        }
        for name, (candidate, code) in cases.items():
            with self.subTest(name=name):
                result = self.commit_preview(write_preview=candidate, checkpoint=checkpoint)
                self.assertIn(code, result.reason_codes)

    def test_checkpoint_missing_invalid_mismatch_governance_review_and_block(self):
        checkpoint = self.checkpoint()
        write_preview = self.write_preview(checkpoint=checkpoint).preview
        mismatch = self.checkpoint(head_sha="2" * 40)
        block_checkpoint = self.rehashed_checkpoint(checkpoint.to_dict(), governance_status=GIT_GOVERNANCE_BLOCK)
        block_write = self.rehashed_write_preview(write_preview.to_dict(), checkpoint_hash=block_checkpoint["checkpoint_hash"], governance_status=GIT_GOVERNANCE_BLOCK)
        review_checkpoint = self.rehashed_checkpoint(checkpoint.to_dict(), governance_status=GIT_GOVERNANCE_NEEDS_REVIEW)
        review_write = self.rehashed_write_preview(write_preview.to_dict(), checkpoint_hash=review_checkpoint["checkpoint_hash"], governance_status=GIT_GOVERNANCE_NEEDS_REVIEW)
        cases = {
            "missing": (None, write_preview, GIT_COMMIT_PREVIEW_BLOCKED_MISSING_CHECKPOINT),
            "invalid": ({**checkpoint.to_dict(), "head_sha": "2" * 40}, write_preview, GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_INVALID),
            "mismatch": (mismatch, write_preview, GIT_COMMIT_PREVIEW_BLOCKED_CHECKPOINT_HASH_MISMATCH),
            "block": (block_checkpoint, block_write, GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_BLOCK),
            "review": (review_checkpoint, review_write, GIT_COMMIT_PREVIEW_BLOCKED_GOVERNANCE_REVIEW),
        }
        for name, (candidate_checkpoint, candidate_write_preview, code) in cases.items():
            with self.subTest(name=name):
                result = self.commit_preview(write_preview=candidate_write_preview, checkpoint=candidate_checkpoint)
                self.assertIn(code, result.reason_codes)

        allowed = self.commit_preview(write_preview=review_write, checkpoint=review_checkpoint, policy=GitCommitPreviewPolicy(allow_review_previews=True))
        self.assertEqual(GIT_COMMIT_PREVIEW_CREATED, allowed.status)

    def test_parent_branch_detached_target_path_and_authority_claims_block(self):
        checkpoint = self.checkpoint()
        write_preview = self.write_preview(checkpoint=checkpoint).preview
        cases = (
            {"checkpoint": self.rehashed_checkpoint(checkpoint.to_dict(), head_sha=""), "code": GIT_COMMIT_PREVIEW_BLOCKED_MISSING_PARENT_HEAD},
            {"checkpoint": self.rehashed_checkpoint(checkpoint.to_dict(), branch_name=None), "code": GIT_COMMIT_PREVIEW_BLOCKED_MISSING_BRANCH},
            {"checkpoint": self.rehashed_checkpoint(checkpoint.to_dict(), detached_head=True), "code": GIT_COMMIT_PREVIEW_BLOCKED_DETACHED_HEAD},
            {"target_paths": None, "write_preview": self.rehashed_write_preview(write_preview.to_dict(), target_paths=(), target_paths_hash=compute_git_write_preview_hash(())), "code": GIT_COMMIT_PREVIEW_BLOCKED_MISSING_TARGET_PATHS},
            {"target_paths": ("docs/a.md", "docs//a.md"), "code": GIT_COMMIT_PREVIEW_BLOCKED_DUPLICATE_TARGET_PATH},
            {"target_paths": ("../escape",), "code": GIT_COMMIT_PREVIEW_BLOCKED_TRAVERSAL_PATH},
            {"target_paths": (":(glob)*",), "code": GIT_COMMIT_PREVIEW_BLOCKED_PATHSPEC_MAGIC},
            {"target_paths": ("--force",), "code": GIT_COMMIT_PREVIEW_BLOCKED_OPTION_LIKE_PATH},
            {"target_paths": ("/tmp/a",), "code": GIT_COMMIT_PREVIEW_BLOCKED_ABSOLUTE_PATH},
            {"target_paths": (".git/config",), "code": GIT_COMMIT_PREVIEW_BLOCKED_GIT_INTERNAL_PATH},
            {"target_paths": ("runtime/git_ops/git_commit_preview.py",), "code": GIT_COMMIT_PREVIEW_BLOCKED_PROTECTED_PATH},
            {"write_preview": write_preview, "target_paths": ("docs/b.md",), "code": GIT_COMMIT_PREVIEW_BLOCKED_TARGET_PATH_HASH_MISMATCH},
            {"write_preview": {**write_preview.to_dict(), "can_commit": True}, "code": GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM},
            {"checkpoint": {**checkpoint.to_dict(), "can_push": True}, "code": GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM},
            {"claims": {"can_approve": True}, "code": GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM},
        )
        for case in cases:
            with self.subTest(case=case):
                result = self.commit_preview(**{key: value for key, value in case.items() if key != "code"})
                self.assertIn(case["code"], result.reason_codes)

    def test_commit_message_policy_blocks_risky_messages(self):
        cases = {
            "missing": ("", GIT_COMMIT_PREVIEW_BLOCKED_MISSING_MESSAGE),
            "long": ("x" * 73, GIT_COMMIT_PREVIEW_BLOCKED_MESSAGE_FIRST_LINE_LENGTH),
            "control": ("feat: bad\x01", GIT_COMMIT_PREVIEW_BLOCKED_CONTROL_CHARACTER),
            "ansi": ("feat: bad \x1b[31mred", GIT_COMMIT_PREVIEW_BLOCKED_ANSI_ESCAPE),
            "credential-url": ("feat: use https://user:pass@example.com/repo", GIT_COMMIT_PREVIEW_BLOCKED_CREDENTIAL_URL),
            "github-token": ("feat: ghp_abcdefghijklmnopqrstuvwxyz123456", GIT_COMMIT_PREVIEW_BLOCKED_GITHUB_TOKEN),
            "token-field": ("feat: token=secret", GIT_COMMIT_PREVIEW_BLOCKED_TOKEN_FIELD),
            "authority": ("feat: human approved", GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_LANGUAGE),
            "approved-by": ("feat: x\n\nApproved-by: AI", GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER),
            "signed-off": ("feat: x\n\nSigned-off-by: AI", GIT_COMMIT_PREVIEW_BLOCKED_FAKE_TRAILER),
            "skip-ci": ("feat: x [skip ci]", GIT_COMMIT_PREVIEW_BLOCKED_SKIP_CI),
        }
        for name, (message, code) in cases.items():
            with self.subTest(name=name):
                result = self.commit_preview(commit_message=message)
                self.assertIn(code, result.reason_codes)

        allowed = self.commit_preview(commit_message="feat: x\n\nSigned-off-by: Human", policy=GitCommitPreviewPolicy(allow_signed_off_by=True))
        self.assertEqual(GIT_COMMIT_PREVIEW_CREATED, allowed.status)

    def test_raw_git_shell_and_provider_metadata_block(self):
        cases = {
            "raw-key": ({"command": "git commit -m x"}, GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT),
            "raw-text": ({"note": "git commit -m x"}, GIT_COMMIT_PREVIEW_BLOCKED_RAW_COMMAND_TEXT),
            "shell": ({"note": "echo x && git commit"}, GIT_COMMIT_PREVIEW_BLOCKED_SHELL_TEXT),
            "provider": ({"note": "permission to commit"}, GIT_COMMIT_PREVIEW_BLOCKED_AUTHORITY_CLAIM),
        }
        for name, (metadata, code) in cases.items():
            with self.subTest(name=name):
                result = self.commit_preview(metadata=metadata)
                self.assertIn(code, result.reason_codes)

    def test_canonical_commit_preview_json_and_hash_are_deterministic(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}
        first = self.commit_preview().preview
        second = self.commit_preview().preview

        self.assertEqual(canonical_git_commit_preview_json(left), canonical_git_commit_preview_json(right))
        self.assertEqual(compute_git_commit_preview_hash(left), compute_git_commit_preview_hash(right))
        self.assertEqual(first.commit_preview_hash, second.commit_preview_hash)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_commit_preview_hash_changes_for_bound_inputs_message_author_and_policy(self):
        base = self.commit_preview().preview.commit_preview_hash
        changed_checkpoint = self.checkpoint(checkpoint_hash_seed="b" * 64)
        changed_write = self.write_preview(checkpoint=changed_checkpoint).preview
        cases = (
            self.commit_preview(write_preview=changed_write, checkpoint=changed_checkpoint).preview.commit_preview_hash,
            self.commit_preview_for_checkpoint(self.checkpoint(git_read_hash="c" * 64)).commit_preview_hash,
            self.commit_preview_for_checkpoint(self.checkpoint(governance_hash="d" * 64)).commit_preview_hash,
            self.commit_preview_for_checkpoint(self.checkpoint(head_sha="2" * 40)).commit_preview_hash,
            self.commit_preview_for_checkpoint(self.checkpoint(branch_name="release")).commit_preview_hash,
            self.commit_preview(target_paths=("docs/b.md",), write_preview=self.write_preview(target_paths=("docs/b.md",)).preview).preview.commit_preview_hash,
            self.commit_preview(commit_message="feat(git): change message").preview.commit_preview_hash,
            self.commit_preview(author_policy_version="2A").preview.commit_preview_hash,
            self.commit_preview(policy=GitCommitPreviewPolicy(policy_version="2A")).preview.commit_preview_hash,
        )
        for value in cases:
            self.assertNotEqual(base, value)

    def test_path_and_finding_order_do_not_change_canonical_result(self):
        write_left = self.write_preview(target_paths=("docs/b.md", "docs/a.md")).preview
        write_right = self.write_preview(target_paths=("docs/a.md", "docs/b.md")).preview
        left = self.commit_preview(write_preview=write_left, target_paths=("docs/b.md", "docs/a.md")).preview
        right = self.commit_preview(write_preview=write_right, target_paths=("docs/a.md", "docs/b.md")).preview

        self.assertEqual(left.commit_preview_hash, right.commit_preview_hash)
        self.assertEqual(left.to_dict(), right.to_dict())

    def test_verification_accepts_exact_evidence_and_rejects_replay_or_tampering(self):
        checkpoint = self.checkpoint()
        write_preview = self.write_preview(checkpoint=checkpoint).preview
        preview = self.commit_preview(write_preview=write_preview, checkpoint=checkpoint).preview

        valid = verify_git_commit_preview(preview, write_preview, checkpoint)
        changed_checkpoint = self.checkpoint(head_sha="2" * 40)
        changed_write = self.write_preview(checkpoint=changed_checkpoint).preview
        cases = (
            verify_git_commit_preview({**preview.to_dict(), "commit_preview_hash": "f" * 64}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "write_preview_hash": changed_write.preview_hash}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "checkpoint_hash": changed_checkpoint.checkpoint_hash}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "parent_head_sha": "2" * 40}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "branch_name": "release"}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "target_paths_hash": "e" * 64}, write_preview, checkpoint),
            verify_git_commit_preview({**preview.to_dict(), "commit_message_hash": "d" * 64}, write_preview, checkpoint),
            verify_git_commit_preview(preview, changed_write, changed_checkpoint),
        )

        self.assertEqual(GIT_COMMIT_PREVIEW_VALID, valid.status)
        for result in cases:
            self.assertIn(result.status, ("INVALID", "BLOCKED"))

    def test_commit_preview_cannot_satisfy_control_write_gate_or_future_authority(self):
        preview_result = self.commit_preview()
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            result = write_preview_artifact_after_human_gate(
                preview=self.artifact_preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=preview_result,
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)
        self.assertFalse(preview_result.can_write)
        self.assertFalse(preview_result.can_commit)
        self.assertFalse(preview_result.can_push)
        self.assertFalse(preview_result.can_call_provider)
        self.assert_authority_false(preview_result)
        self.assert_authority_false(preview_result.preview)

    def test_commit_preview_module_imports_no_subprocess_network_provider_browser_package_or_env_libs(self):
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

    def commit_preview(
        self,
        *,
        write_preview=DEFAULT,
        checkpoint=DEFAULT,
        commit_message="feat(git): add commit preview",
        target_paths=("runtime/example.py",),
        policy=None,
        metadata=None,
        claims=None,
        author_policy_version="1A",
    ):
        if checkpoint is DEFAULT:
            checkpoint = self.checkpoint()
        if write_preview is DEFAULT:
            write_preview = self.write_preview(checkpoint=checkpoint, target_paths=target_paths).preview
        return create_git_commit_preview(
            GitCommitPreviewRequest(
                write_preview=write_preview,
                checkpoint=checkpoint,
                commit_message=commit_message,
                target_paths=target_paths,
                created_at="2026-06-28T00:00:00Z",
                preview_nonce="commit-preview-session",
                policy=policy,
                author_policy_version=author_policy_version,
                author_identity_policy={"mode": "metadata-only"},
                committer_identity_policy={"mode": "metadata-only"},
                metadata=metadata,
                claims=claims,
            )
        )

    def commit_preview_for_checkpoint(self, checkpoint):
        return self.commit_preview(write_preview=self.write_preview(checkpoint=checkpoint).preview, checkpoint=checkpoint).preview

    def write_preview(self, *, checkpoint=DEFAULT, target_paths=("runtime/example.py",)):
        if checkpoint is DEFAULT:
            checkpoint = self.checkpoint()
        return create_git_write_preview(
            GitWritePreviewRequest(
                checkpoint=checkpoint,
                operation_kind=GitWriteIntent.LOCAL_COMMIT_INTENT,
                target_paths=target_paths,
                target_branch="feature/m2-b0-provider-critic-inert-core",
                created_at="2026-06-28T00:00:00Z",
                preview_nonce="write-preview-session",
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

    def rehashed_checkpoint(self, data, **updates):
        candidate = {**data, **updates}
        material = dict(candidate)
        material.pop("checkpoint_hash", None)
        for field in AUTHORITY_FIELDS:
            material.pop(field, None)
        candidate["checkpoint_hash"] = compute_git_checkpoint_hash(material)
        return candidate

    def rehashed_write_preview(self, data, **updates):
        candidate = {**data, **updates}
        material = dict(candidate)
        material.pop("preview_hash", None)
        for field in AUTHORITY_FIELDS:
            material.pop(field, None)
        candidate["preview_hash"] = compute_git_write_preview_hash(material)
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
            ArtifactPreviewRequest(target_path="artifact.md", proposed_content=CONTENT, original_content="", reason="git commit preview regression")
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
