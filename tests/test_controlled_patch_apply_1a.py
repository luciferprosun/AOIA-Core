from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from runtime.control_write import ControlWriteContext
from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate
from runtime.human_decision_gated_artifact_write import ARTIFACT_WRITTEN, write_artifact_after_human_gate
from runtime.patches.controlled_patch_apply import (
    CONTROLLED_PATCH_APPLIED,
    CONTROLLED_PATCH_BLOCKED,
    CONTROLLED_PATCH_FILE_APPLIED,
    PATCH_APPLY_BLOCKED_BARRIER_HASH_MISMATCH,
    PATCH_APPLY_BLOCKED_BARRIER_INVALID,
    PATCH_APPLY_BLOCKED_CONTROLLED_WRITE,
    PATCH_APPLY_BLOCKED_CREATE_TARGET_EXISTS,
    PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE,
    PATCH_APPLY_BLOCKED_KILL_SWITCH,
    PATCH_APPLY_BLOCKED_MISSING_BARRIER,
    PATCH_APPLY_BLOCKED_MISSING_GATE,
    PATCH_APPLY_BLOCKED_MISSING_POLICY,
    PATCH_APPLY_BLOCKED_MISSING_PREVIEW,
    PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISMATCH,
    PATCH_APPLY_BLOCKED_POLICY_HASH_MISSING,
    PATCH_APPLY_BLOCKED_POLICY_HASH_MISMATCH,
    PATCH_APPLY_BLOCKED_POLICY_PREVIEW_MISMATCH,
    PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH,
    PATCH_APPLY_BLOCKED_POLICY_STATUS,
    PATCH_APPLY_BLOCKED_PROPOSED_HASH_MISMATCH,
    PATCH_APPLY_BLOCKED_TARGET_MISMATCH,
    PATCH_APPLY_BLOCKED_UNSUPPORTED_OPERATION,
    PATCH_APPLY_BLOCKED_WORKSPACE_GUARD,
    ControlledPatchApplyRequest,
    ControlledPatchApplyResult,
    apply_controlled_patch as apply_controlled_patch_runtime,
    canonical_controlled_patch_apply_json,
    compute_controlled_patch_apply_hash,
)
from runtime.patches.patch_barrier import (
    PATCH_DECISION_APPROVE,
    PATCH_DECISION_REJECT,
    create_human_patch_barrier,
)
from runtime.patches.patch_policy import (
    PATCH_POLICY_BLOCK,
    PATCH_POLICY_NEEDS_REVIEW,
    PATCH_POLICY_PASS,
    check_patch_local_policy,
)
from runtime.patches.patch_preview import PatchFileEdit, build_patch_preview, compute_patch_preview_hash
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_APPLY_MODULE = REPO_ROOT / "runtime" / "patches" / "controlled_patch_apply.py"
CONTENT = "# Controlled patch apply fixture\n"
UPDATED_CONTENT = "# Controlled patch apply fixture\n\nUpdated.\n"
TARGET_PATH = "docs/controlled-patch-apply.md"
PACKET_HASH = "d" * 64


def apply_controlled_patch(request):
    def gated_writer_for_file(current_request, _file_preview):
        def gated_writer(**kwargs):
            writer = (
                current_request.gated_writer
                or ControlledPatchApply1ATests.gated_writer_with_enabled_switch
            )
            return writer(**kwargs)

        return gated_writer

    with patch(
        "runtime.patches.controlled_patch_apply._gated_writer_for_file",
        side_effect=gated_writer_for_file,
    ):
        return apply_controlled_patch_runtime(request)


class ControlledPatchApply1ATests(unittest.TestCase):
    def test_valid_single_file_controlled_patch_apply_succeeds(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                )
            )

            target = Path(workspace) / TARGET_PATH
            self.assertEqual(CONTROLLED_PATCH_APPLIED, result.status)
            self.assertTrue(result.patch_applied)
            self.assertFalse(result.partial_apply)
            self.assertEqual(UPDATED_CONTENT, target.read_text(encoding="utf-8"))
            self.assertEqual((TARGET_PATH,), result.target_paths)
            self.assertEqual(CONTROLLED_PATCH_FILE_APPLIED, result.file_results[0].status)
            self.assertEqual(ARTIFACT_WRITTEN, result.file_results[0].controlled_write_status)

    def test_valid_multi_file_controlled_patch_apply_succeeds_deterministically(self):
        edits = [
            PatchFileEdit("docs/z-apply-fixture.txt", "Z = 2\n", "Z = 1\n"),
            PatchFileEdit("docs/a-apply-fixture.md", "A2\n", "A1\n"),
        ]
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, "docs/z-apply-fixture.txt", "Z = 1\n")
            self.write_file(workspace, "docs/a-apply-fixture.md", "A1\n")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            preview = self.preview(edits)
            policy = check_patch_local_policy(preview)
            barrier = self.barrier(preview, policy)
            gates = {
                path: self.gate(hashlib.sha256(content.encode("utf-8")).hexdigest())
                for path, content in {
                    "docs/z-apply-fixture.txt": "Z = 2\n",
                    "docs/a-apply-fixture.md": "A2\n",
                }.items()
            }

            result = apply_controlled_patch(
                ControlledPatchApplyRequest(
                    patch_preview=preview,
                    patch_policy=policy,
                    human_patch_barrier=barrier,
                    proposed_contents={
                        "docs/z-apply-fixture.txt": "Z = 2\n",
                        "docs/a-apply-fixture.md": "A2\n",
                    },
                    workspace_root=workspace,
                    gate_results=gates,
                    context=self.context(),
                    expected_packet_hash=PACKET_HASH,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )
            )

            self.assertEqual(CONTROLLED_PATCH_APPLIED, result.status)
            self.assertEqual(("docs/a-apply-fixture.md", "docs/z-apply-fixture.txt"), result.target_paths)
            self.assertEqual(
                ["docs/a-apply-fixture.md", "docs/z-apply-fixture.txt"],
                [item.target_path for item in result.file_results],
            )
            self.assertEqual("A2\n", (Path(workspace) / "docs/a-apply-fixture.md").read_text(encoding="utf-8"))
            self.assertEqual("Z = 2\n", (Path(workspace) / "docs/z-apply-fixture.txt").read_text(encoding="utf-8"))

    def test_controlled_patch_apply_uses_existing_controlled_sandbox_write_path(self):
        writer = Mock(wraps=self.gated_writer_with_enabled_switch)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)

            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    gated_writer=writer,
                )
            )

        self.assertEqual(CONTROLLED_PATCH_APPLIED, result.status)
        self.assertEqual(1, writer.call_count)

    def test_missing_required_evidence_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            base = self.request(workspace=workspace, switch_path=switch_path, switch_dir=switch_dir)
            cases = {
                "preview": (replace(base, patch_preview=None), PATCH_APPLY_BLOCKED_MISSING_PREVIEW),
                "policy": (replace(base, patch_policy=None), PATCH_APPLY_BLOCKED_MISSING_POLICY),
                "barrier": (replace(base, human_patch_barrier=None), PATCH_APPLY_BLOCKED_MISSING_BARRIER),
                "gate": (replace(base, gate_results={}), PATCH_APPLY_BLOCKED_MISSING_GATE),
            }

            for name, (request, reason_code) in cases.items():
                with self.subTest(name=name):
                    result = apply_controlled_patch(request)

                    self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
                    self.assertEqual(reason_code, result.reason_code)

    def test_multi_file_missing_gate_blocks_before_any_mutation(self):
        edits = [
            PatchFileEdit("docs/first-preflight.md", "first updated\n", "first\n"),
            PatchFileEdit("docs/second-preflight.md", "second updated\n", "second\n"),
        ]
        preview = self.preview(edits)
        policy = check_patch_local_policy(preview)
        barrier = self.barrier(preview, policy)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, "docs/first-preflight.md", "first\n")
            self.write_file(workspace, "docs/second-preflight.md", "second\n")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=preview,
                    policy=policy,
                    barrier=barrier,
                    contents={
                        "docs/first-preflight.md": "first updated\n",
                        "docs/second-preflight.md": "second updated\n",
                    },
                    gates={
                        "docs/first-preflight.md": self.gate(hashlib.sha256("first updated\n".encode("utf-8")).hexdigest())
                    },
                )
            )

            self.assertEqual("first\n", (Path(workspace) / "docs/first-preflight.md").read_text(encoding="utf-8"))
            self.assertEqual("second\n", (Path(workspace) / "docs/second-preflight.md").read_text(encoding="utf-8"))

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_MISSING_GATE, result.reason_code)

    def test_reject_decision_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            preview = self.preview()
            policy = check_patch_local_policy(preview)
            reject = self.barrier(preview, policy, PATCH_DECISION_REJECT)

            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=preview,
                    policy=policy,
                    barrier=reject,
                )
            )

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE, result.reason_code)

    def test_block_policy_blocks_apply(self):
        preview = self.preview([PatchFileEdit(".env", "TOKEN=value\n", "")])
        policy = check_patch_local_policy(preview)
        self.assertEqual(PATCH_POLICY_BLOCK, policy.status)
        reject = self.barrier(preview, policy, PATCH_DECISION_REJECT)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=preview,
                    policy=policy,
                    barrier=reject,
                    contents={".env": "TOKEN=value\n"},
                    gates={".env": self.gate(hashlib.sha256("TOKEN=value\n".encode("utf-8")).hexdigest())},
                )
            )

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_POLICY_STATUS, result.reason_code)

    def test_needs_review_is_allowed_only_with_valid_approve_barrier(self):
        preview = self.preview([PatchFileEdit("docs/needs-review.md", "can_write=True\n", "old\n")])
        policy = check_patch_local_policy(preview)
        self.assertEqual(PATCH_POLICY_NEEDS_REVIEW, policy.status)
        approved = self.barrier(preview, policy, PATCH_DECISION_APPROVE)
        rejected = self.barrier(preview, policy, PATCH_DECISION_REJECT)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, "docs/needs-review.md", "old\n")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            base = self.request(
                workspace=workspace,
                switch_path=switch_path,
                switch_dir=switch_dir,
                preview=preview,
                policy=policy,
                barrier=approved,
                contents={"docs/needs-review.md": "can_write=True\n"},
                gates={"docs/needs-review.md": self.gate(hashlib.sha256("can_write=True\n".encode("utf-8")).hexdigest())},
            )

            allowed = apply_controlled_patch(base)
            blocked = apply_controlled_patch(replace(base, human_patch_barrier=rejected))

        self.assertEqual(CONTROLLED_PATCH_APPLIED, allowed.status)
        self.assertEqual(CONTROLLED_PATCH_BLOCKED, blocked.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_DECISION_NOT_APPROVE, blocked.reason_code)

    def test_hash_binding_mismatches_block(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            preview = self.preview()
            policy = check_patch_local_policy(preview)
            barrier = self.barrier(preview, policy)
            cases = {
                "policy_preview": (
                    replace(policy, patch_preview_hash="b" * 64),
                    barrier,
                    PATCH_APPLY_BLOCKED_POLICY_HASH_MISMATCH,
                ),
                "policy_hash_missing": (
                    replace(policy, policy_hash="not-a-hash"),
                    barrier,
                    PATCH_APPLY_BLOCKED_POLICY_HASH_MISSING,
                ),
                "barrier_hash": (
                    policy,
                    replace(barrier.decision, barrier_hash="c" * 64),
                    PATCH_APPLY_BLOCKED_BARRIER_HASH_MISMATCH,
                ),
            }

            for name, (case_policy, case_barrier, reason_code) in cases.items():
                with self.subTest(name=name):
                    result = apply_controlled_patch(
                        self.request(
                            workspace=workspace,
                            switch_path=switch_path,
                            switch_dir=switch_dir,
                            preview=preview,
                            policy=case_policy,
                            barrier=case_barrier,
                        )
                    )

                    self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
                    self.assertEqual(reason_code, result.reason_code)

    def test_stale_replayed_barrier_for_different_patch_blocks(self):
        preview = self.preview()
        policy = check_patch_local_policy(preview)
        stale_barrier = self.barrier(preview, policy)
        other_preview = self.preview([PatchFileEdit("docs/other-apply.md", "new\n", "old\n")])
        other_policy = check_patch_local_policy(other_preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, "docs/other-apply.md", "old\n")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=other_preview,
                    policy=other_policy,
                    barrier=stale_barrier,
                    contents={"docs/other-apply.md": "new\n"},
                    gates={"docs/other-apply.md": self.gate(hashlib.sha256("new\n".encode("utf-8")).hexdigest())},
                )
            )

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_BARRIER_INVALID, result.reason_code)

    def test_target_and_proposed_content_hash_mismatches_block(self):
        preview = self.preview()
        policy = check_patch_local_policy(preview)
        barrier = self.barrier(preview, policy)
        tampered_preview = replace(preview, target_paths=("docs/other.md",))

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            target_result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=tampered_preview,
                    policy=policy,
                    barrier=barrier,
                )
            )
            content_result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    contents={TARGET_PATH: "changed after preview\n"},
                )
            )

        self.assertEqual(PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH, target_result.reason_code)
        self.assertEqual(PATCH_APPLY_BLOCKED_PROPOSED_HASH_MISMATCH, content_result.reason_code)

    def test_duplicate_target_paths_block_before_mutation(self):
        first = self.preview().files[0]
        duplicate_preview = self.rehash_preview(
            replace(
                self.preview(),
                target_paths=(TARGET_PATH, TARGET_PATH),
                files=(first, first),
                total_file_count=2,
            )
        )
        policy = check_patch_local_policy(duplicate_preview)
        barrier = self.barrier(duplicate_preview, policy, PATCH_DECISION_REJECT)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=duplicate_preview,
                    policy=policy,
                    barrier=barrier,
                )
            )

            self.assertEqual(CONTENT, (Path(workspace) / TARGET_PATH).read_text(encoding="utf-8"))

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_POLICY_STATUS, result.reason_code)

    def test_changed_original_content_after_preview_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            preview = self.preview()
            self.write_file(workspace, TARGET_PATH, "changed by someone else\n")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=preview,
                    policy=check_patch_local_policy(preview),
                    barrier=self.barrier(preview, check_patch_local_policy(preview)),
                )
            )

        self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_ORIGINAL_HASH_MISMATCH, result.reason_code)

    def test_kill_switch_disabled_and_missing_block(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            self.write_file(workspace, TARGET_PATH, CONTENT)
            disabled = self.write_switch(switch_dir, WRITES_DISABLED)
            missing = Path(switch_dir) / "missing.state"

            for name, switch_path in {"disabled": disabled, "missing": missing}.items():
                with self.subTest(name=name):
                    result = apply_controlled_patch(
                        self.request(workspace=workspace, switch_path=switch_path, switch_dir=switch_dir)
                    )

                    self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
                    self.assertEqual(PATCH_APPLY_BLOCKED_KILL_SWITCH, result.reason_code)

    def test_workspace_guard_unsafe_targets_block(self):
        cases = {
            "absolute": "/tmp/escape.txt",
            "traversal": "../escape.txt",
            "dot_git": ".git/config",
        }
        for name, target_path in cases.items():
            with self.subTest(name=name):
                preview = self.forged_preview(target_path)
                policy = replace(check_patch_local_policy(self.preview()), patch_preview_hash=preview.preview_hash, target_paths=(target_path,))
                barrier = self.barrier(preview, policy)
                with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
                    switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
                    result = apply_controlled_patch(
                        self.request(
                            workspace=workspace,
                            switch_path=switch_path,
                            switch_dir=switch_dir,
                            preview=preview,
                            policy=policy,
                            barrier=barrier,
                            contents={target_path: UPDATED_CONTENT},
                            gates={target_path: self.gate(hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest())},
                        )
                    )

                self.assertEqual(CONTROLLED_PATCH_BLOCKED, result.status)
                self.assertEqual(PATCH_APPLY_BLOCKED_PREVIEW_HASH_MISMATCH, result.reason_code)

    def test_symlink_and_directory_targets_block_where_testable(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            symlink_target = Path(workspace) / "docs" / "linked.md"
            symlink_target.parent.mkdir(parents=True, exist_ok=True)
            directory_target = Path(workspace) / "docs" / "directory.md"
            directory_target.mkdir()
            try:
                symlink_target.symlink_to(Path(outside) / "escape.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            for target_path in ("docs/linked.md", "docs/directory.md"):
                with self.subTest(target_path=target_path):
                    preview = self.preview([PatchFileEdit(target_path, UPDATED_CONTENT, CONTENT)])
                    policy = check_patch_local_policy(preview)
                    result = apply_controlled_patch(
                        self.request(
                            workspace=workspace,
                            switch_path=switch_path,
                            switch_dir=switch_dir,
                            preview=preview,
                            policy=policy,
                            barrier=self.barrier(preview, policy),
                            contents={target_path: UPDATED_CONTENT},
                            gates={target_path: self.gate(hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest())},
                        )
                    )

                    self.assertEqual(PATCH_APPLY_BLOCKED_WORKSPACE_GUARD, result.reason_code)

    def test_create_operation_and_delete_operation_behavior(self):
        create_preview = self.preview([PatchFileEdit("docs/new-controlled.md", "new\n", None, operation="create")])
        create_policy = check_patch_local_policy(create_preview)
        delete_preview = self.forged_preview("docs/delete.md", operation="delete", recompute_hash=True)
        delete_policy = check_patch_local_policy(delete_preview)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            created = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=create_preview,
                    policy=create_policy,
                    barrier=self.barrier(create_preview, create_policy),
                    contents={"docs/new-controlled.md": "new\n"},
                    gates={"docs/new-controlled.md": self.gate(hashlib.sha256("new\n".encode("utf-8")).hexdigest())},
                )
            )
            create_exists = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=create_preview,
                    policy=create_policy,
                    barrier=self.barrier(create_preview, create_policy),
                    contents={"docs/new-controlled.md": "new\n"},
                    gates={"docs/new-controlled.md": self.gate(hashlib.sha256("new\n".encode("utf-8")).hexdigest())},
                )
            )
            delete_blocked = apply_controlled_patch(
                self.request(
                    workspace=workspace,
                    switch_path=switch_path,
                    switch_dir=switch_dir,
                    preview=delete_preview,
                    policy=delete_policy,
                    barrier=self.barrier(delete_preview, delete_policy),
                    contents={"docs/delete.md": ""},
                    gates={"docs/delete.md": self.gate(hashlib.sha256("".encode("utf-8")).hexdigest())},
                )
            )

        self.assertEqual(CONTROLLED_PATCH_APPLIED, created.status)
        self.assertEqual(PATCH_APPLY_BLOCKED_CREATE_TARGET_EXISTS, create_exists.reason_code)
        self.assertEqual(PATCH_APPLY_BLOCKED_UNSUPPORTED_OPERATION, delete_blocked.reason_code)

    def test_result_authority_fields_are_false_and_not_future_gate_evidence(self):
        result = ControlledPatchApplyResult(
            status=CONTROLLED_PATCH_APPLIED,
            apply_hash="a" * 64,
            patch_preview_hash="b" * 64,
            patch_policy_hash="c" * 64,
            patch_barrier_hash="d" * 64,
            target_paths=(TARGET_PATH,),
            file_results=(),
            reason_code=CONTROLLED_PATCH_APPLIED,
            reason="forced fields normalize",
            can_approve=True,
            can_write=True,
            can_execute=True,
            can_commit=True,
            can_push=True,
            can_call_provider=True,
            can_change_gate=True,
            write_authority_granted=True,
            execution_authority_granted=True,
            provider_authority_granted=True,
        )

        for field_name in self.authority_fields():
            self.assertIs(False, getattr(result, field_name))
            self.assertIs(False, result.to_dict()[field_name])
        self.assertNotIn("gate_result", result.to_dict())
        self.assertNotIn("artifact_hash", result.to_dict())
        self.assertNotIn("packet_hash", result.to_dict())

    def test_canonical_apply_hash_is_deterministic(self):
        left = {"b": {"z": 1, "a": 2}, "a": [3, {"d": 4, "c": 5}]}
        right = {"a": [3, {"c": 5, "d": 4}], "b": {"a": 2, "z": 1}}

        self.assertEqual(canonical_controlled_patch_apply_json(left), canonical_controlled_patch_apply_json(right))
        self.assertEqual(compute_controlled_patch_apply_hash(left), compute_controlled_patch_apply_hash(right))

    def test_static_no_new_capability_scan_includes_controlled_patch_apply_module(self):
        forbidden_import_prefixes = (
            "subprocess",
            "os",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "requests",
            "httpx",
            "git",
            "openai",
            "anthropic",
            "google.generativeai",
            "google.genai",
            "ollama",
            "pip",
            "venv",
            "runtime.providers.gateway",
            "runtime.execution",
        )
        forbidden_calls = {
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "os.popen",
            "Popen",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
            "import_module",
            "open",
        }

        scan = scan_module(PATCH_APPLY_MODULE)

        self.assertEqual(
            [],
            [
                module_name
                for module_name in scan["imports"]
                if matches_any_prefix(module_name, forbidden_import_prefixes)
            ],
        )
        self.assertEqual([], [call_name for call_name in scan["calls"] if call_name in forbidden_calls])

    def preview(self, edits=None):
        result = build_patch_preview(
            edits
            if edits is not None
            else [PatchFileEdit(TARGET_PATH, UPDATED_CONTENT, CONTENT)]
        )
        assert result.patch_preview is not None
        return result.patch_preview

    def forged_preview(self, target_path: str, operation: str = "update", recompute_hash: bool = False):
        preview = self.preview()
        file_preview = replace(
            preview.files[0],
            target_path=target_path,
            operation=operation,
        )
        forged = replace(
            preview,
            target_paths=(target_path,),
            files=(file_preview,),
        )
        if not recompute_hash:
            return forged
        return self.rehash_preview(forged)

    def rehash_preview(self, forged):
        material = {
            "schema_version": "AOIA_PATCH_PREVIEW_1A",
            "target_paths": list(forged.target_paths),
            "files": [item.to_dict() for item in forged.files],
            "total_file_count": forged.total_file_count,
            "total_proposed_size_bytes": forged.total_proposed_size_bytes,
            "total_proposed_char_count": forged.total_proposed_char_count,
            "risk_flags": list(forged.risk_flags),
        }
        preview_hash = compute_patch_preview_hash(material)
        return replace(
            forged,
            preview_hash=preview_hash,
            preview_id="patch-preview-" + preview_hash[:24],
        )

    def barrier(self, preview, policy, decision=PATCH_DECISION_APPROVE):
        return create_human_patch_barrier(
            decision_value=decision,
            patch_preview=preview,
            patch_policy=policy,
            decision_id="controlled-patch-apply-decision",
            reviewer_id="step-24-reviewer",
            created_at="2026-06-27T08:03:00Z",
            reason="reviewed controlled patch apply evidence",
        )

    def request(
        self,
        *,
        workspace,
        switch_path,
        switch_dir,
        preview=None,
        policy=None,
        barrier=None,
        contents=None,
        gates=None,
        gated_writer=None,
    ):
        patch_preview = preview or self.preview()
        patch_policy = policy or check_patch_local_policy(patch_preview)
        patch_barrier = barrier or self.barrier(patch_preview, patch_policy)
        proposed_contents = contents or {TARGET_PATH: UPDATED_CONTENT}
        gate_results = gates or {TARGET_PATH: self.gate(hashlib.sha256(UPDATED_CONTENT.encode("utf-8")).hexdigest())}
        return ControlledPatchApplyRequest(
            patch_preview=patch_preview,
            patch_policy=patch_policy,
            human_patch_barrier=patch_barrier,
            proposed_contents=proposed_contents,
            workspace_root=workspace,
            gate_results=gate_results,
            context=self.context(),
            expected_packet_hash=PACKET_HASH,
            write_kill_switch_path=str(switch_path),
            write_kill_switch_directory=switch_dir,
            gated_writer=gated_writer or self.gated_writer_with_enabled_switch,
        )

    @staticmethod
    def gated_writer_with_enabled_switch(**kwargs):
        kwargs.pop("artifact_writer", None)

        def sandbox_writer(
            request,
            workspace_root,
            *,
            approval_evidence=None,
            write_kill_switch_path=None,
            write_kill_switch_directory=None,
        ):
            output_path = Path(workspace_root) / request.relative_output_path
            return write_sandbox_artifact(
                request,
                workspace_root,
                allow_overwrite=output_path.exists(),
                approval_evidence=approval_evidence,
                write_kill_switch_path=write_kill_switch_path,
                write_kill_switch_directory=write_kill_switch_directory,
            )

        return write_artifact_after_human_gate(
            **kwargs,
            artifact_writer=sandbox_writer,
        )

    def context(self):
        return ControlWriteContext(
            run_id="step-24-run",
            sandbox_request_id="step-24-sandbox-request",
            sandbox_result_id="step-24-sandbox-result",
            requested_by="human-reviewer-step-24",
            dry_run_trace_id="step-24-dry-run-trace",
            sandbox_policy_decision_id="step-24-sandbox-policy-decision",
        )

    def gate(self, artifact_hash: str):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-step-24",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=artifact_hash,
            current_artifact_hash=artifact_hash,
            human_actor="human-reviewer-step-24",
            reason="reviewed exact Step 24 artifact content",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=artifact_hash,
        )
        with TemporaryDirectory() as audit_dir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(audit_dir),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=artifact_hash,
            )
        return evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=artifact_hash,
        )

    @staticmethod
    def write_file(workspace: str, relative_path: str, content: str) -> Path:
        path = Path(workspace) / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def write_switch(switch_dir: str, value: str) -> Path:
        switch_path = Path(switch_dir) / "write_kill_switch.state"
        switch_path.write_text(value, encoding="utf-8")
        return switch_path

    @staticmethod
    def authority_fields():
        return (
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


def scan_module(path: Path) -> dict[str, tuple[str, ...]]:
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
                full_name = f"{node.module}.{alias.name}"
                imports.append(full_name)
                aliases[alias.asname or alias.name] = full_name
        elif isinstance(node, ast.Call):
            name = call_name(node.func, aliases)
            if name:
                calls.append(name)

    return {"imports": tuple(imports), "calls": tuple(calls)}


def call_name(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        parts = attribute_parts(node)
        if not parts:
            return ""
        root = aliases.get(parts[0], parts[0])
        return ".".join((root, *parts[1:]))
    return ""


def attribute_parts(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*attribute_parts(node.value), node.attr)
    return ()


def matches_any_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in prefixes
    )


if __name__ == "__main__":
    unittest.main()
