from __future__ import annotations

import ast
import hashlib
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from runtime.artifact_preview import ArtifactPreviewRequest, build_artifact_preview
from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate
from runtime.human_decision_gated_artifact_write import (
    BLOCKED_WRITE_KILL_SWITCH,
    write_artifact_after_human_gate,
)
from runtime.safety import sandbox_artifact_runner
from runtime.safety.workspace_guard import (
    WORKSPACE_GUARD_ALLOWED,
    WORKSPACE_GUARD_BLOCKED_ABSOLUTE_TARGET_PATH,
    WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL,
    WORKSPACE_GUARD_BLOCKED_DIRECTORY_TARGET,
    WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET,
    WORKSPACE_GUARD_BLOCKED_EMPTY_WORKSPACE_ROOT,
    WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT,
    WORKSPACE_GUARD_BLOCKED_PARENT_SYMLINK,
    WORKSPACE_GUARD_BLOCKED_SYMLINK_TARGET,
    WORKSPACE_GUARD_BLOCKED_TARGET_EMPTY,
    WORKSPACE_GUARD_BLOCKED_TARGET_NULL_BYTE,
    WORKSPACE_GUARD_BLOCKED_TARGET_POLICY,
    WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL,
    WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK,
    WorkspaceGuardResult,
    validate_workspace_root,
    validate_workspace_target_path,
)
from runtime.safety.write_kill_switch import WRITES_DISABLED, WRITES_ENABLED
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_GUARD_MODULE = REPO_ROOT / "runtime" / "safety" / "workspace_guard.py"
PACKET_HASH = "a" * 64
CONTENT = "# Step 16 workspace guard fixture\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class WorkspaceGuardToctou1ATests(unittest.TestCase):
    def test_valid_workspace_root_accepted(self):
        with TemporaryDirectory() as workspace:
            result = validate_workspace_root(workspace)

        self.assertEqual(WORKSPACE_GUARD_ALLOWED, result.status.value)
        self.assertTrue(result.allowed)
        self.assertFalse(result.can_write)

    def test_missing_and_empty_workspace_root_blocks(self):
        cases = {
            "missing": (None, WORKSPACE_GUARD_BLOCKED_MISSING_WORKSPACE_ROOT),
            "empty": ("", WORKSPACE_GUARD_BLOCKED_EMPTY_WORKSPACE_ROOT),
        }

        for name, (workspace_root, status) in cases.items():
            with self.subTest(name=name):
                result = validate_workspace_root(workspace_root)

                self.assertEqual(status, result.status.value)
                self.assertFalse(result.allowed)

    def test_wrong_type_missing_and_non_directory_workspace_roots_block(self):
        with TemporaryDirectory() as parent:
            base = Path(parent)
            missing = base / "missing"
            regular_file = base / "not-a-directory"
            regular_file.write_text("not a workspace", encoding="utf-8")
            cases = {
                "boolean": False,
                "integer": 1,
                "mapping": {"workspace_safe": True},
                "missing_path": str(missing),
                "regular_file": str(regular_file),
            }

            for name, workspace_root in cases.items():
                with self.subTest(name=name):
                    result = validate_workspace_root(workspace_root)  # type: ignore[arg-type]
                    self.assertFalse(result.allowed)

    def test_symlink_workspace_root_blocks(self):
        with TemporaryDirectory() as parent:
            real_root = Path(parent) / "real"
            real_root.mkdir()
            symlink_root = Path(parent) / "linked"
            try:
                symlink_root.symlink_to(real_root, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = validate_workspace_root(str(symlink_root))

        self.assertEqual(WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK, result.status.value)
        self.assertFalse(result.allowed)

    def test_workspace_root_with_symlink_ancestor_blocks(self):
        with TemporaryDirectory() as parent, TemporaryDirectory() as outside:
            real_parent = Path(outside) / "real-parent"
            real_parent.mkdir()
            workspace = real_parent / "workspace"
            workspace.mkdir()
            linked_parent = Path(parent) / "linked-parent"
            try:
                linked_parent.symlink_to(real_parent, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = validate_workspace_root(str(linked_parent / "workspace"))

        self.assertEqual(WORKSPACE_GUARD_BLOCKED_WORKSPACE_ROOT_SYMLINK, result.status.value)
        self.assertFalse(result.allowed)

    def test_target_path_rejections_are_deterministic(self):
        cases = {
            "empty": ("", WORKSPACE_GUARD_BLOCKED_TARGET_EMPTY),
            "absolute": ("/absolute/path.txt", WORKSPACE_GUARD_BLOCKED_ABSOLUTE_TARGET_PATH),
            "parent_traversal": ("../escape.txt", WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL),
            "nested_parent_traversal": ("docs/../../escape.txt", WORKSPACE_GUARD_BLOCKED_TARGET_TRAVERSAL),
            "backslash_traversal": ("..\\escape.txt", WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL),
            "nested_backslash_traversal": ("docs\\..\\escape.txt", WORKSPACE_GUARD_BLOCKED_BACKSLASH_TRAVERSAL),
            "null_byte": ("reports/bad\x00name.txt", WORKSPACE_GUARD_BLOCKED_TARGET_NULL_BYTE),
            "dot_git_config": (".git/config.txt", WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET),
            "inside_dot_git": ("reports/.git/config.txt", WORKSPACE_GUARD_BLOCKED_DOT_GIT_TARGET),
            "dot": (".", WORKSPACE_GUARD_BLOCKED_TARGET_POLICY),
            "trailing_separator": ("reports/", WORKSPACE_GUARD_BLOCKED_TARGET_POLICY),
        }

        with TemporaryDirectory() as workspace:
            for name, (target_path, status) in cases.items():
                with self.subTest(name=name):
                    result = validate_workspace_target_path(workspace, target_path)

                    self.assertEqual(status, result.status.value)
                    self.assertFalse(result.allowed)

    def test_symlink_target_parent_symlink_and_directory_target_block(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            root = Path(workspace)
            symlink_target = root / "linked.txt"
            parent_link = root / "linked-parent"
            directory_target = root / "existing.txt"
            directory_target.mkdir()
            try:
                symlink_target.symlink_to(Path(outside) / "outside.txt")
                parent_link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            cases = {
                "symlink_target": ("linked.txt", WORKSPACE_GUARD_BLOCKED_SYMLINK_TARGET),
                "parent_symlink": ("linked-parent/result.txt", WORKSPACE_GUARD_BLOCKED_PARENT_SYMLINK),
                "directory_target": ("existing.txt", WORKSPACE_GUARD_BLOCKED_DIRECTORY_TARGET),
            }

            for name, (target_path, status) in cases.items():
                with self.subTest(name=name):
                    result = validate_workspace_target_path(workspace, target_path)

                    self.assertEqual(status, result.status.value)
                    self.assertFalse(result.allowed)

    def test_valid_relative_target_inside_workspace_accepted_as_safety_precondition(self):
        with TemporaryDirectory() as workspace:
            result = validate_workspace_target_path(workspace, "reports/result.txt")

        self.assertEqual(WORKSPACE_GUARD_ALLOWED, result.status.value)
        self.assertTrue(result.allowed)
        self.assertEqual("reports/result.txt", result.normalized_relative_target_path)
        self.assertTrue(result.resolved_absolute_target_path)
        self.assertFalse(result.write_authority_granted)

    def test_allowed_workspace_guard_result_does_not_bypass_missing_gate_evidence(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            guard = validate_workspace_target_path(workspace, "reports/step16.txt")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result={},
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertTrue(guard.allowed)
        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertEqual(0, writer.call_count)

    def test_allowed_workspace_guard_result_does_not_bypass_hash_mismatch(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            guard = validate_workspace_target_path(workspace, "reports/step16.txt")
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text="changed after preview\n",
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertTrue(guard.allowed)
        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertEqual(0, writer.call_count)

    def test_allowed_workspace_guard_result_does_not_bypass_kill_switch_disabled(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            guard = validate_workspace_target_path(workspace, "reports/step16.txt")
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_DISABLED, encoding="utf-8")

            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

        self.assertTrue(guard.allowed)
        self.assertEqual(BLOCKED_WRITE_KILL_SWITCH, result.status)
        self.assertEqual(0, writer.call_count)

    def test_target_symlink_swap_before_write_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/swap-target.txt", gate_result=gate)
            original_guard = sandbox_artifact_runner.validate_workspace_target_path
            calls = {"count": 0}

            def swap_after_second_validation(workspace_root, target_path):
                result = original_guard(workspace_root, target_path)
                calls["count"] += 1
                if calls["count"] == 3 and result.allowed:
                    target = Path(result.resolved_absolute_target_path or "")
                    target.symlink_to(Path(outside) / "escaped.txt")
                return result

            with patch.object(
                sandbox_artifact_runner,
                "validate_workspace_target_path",
                side_effect=swap_after_second_validation,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse(result.write_attempted)
            self.assertFalse((Path(outside) / "escaped.txt").exists())
            self.assertIn("symlink", result.blocked_reason)

    def test_parent_symlink_swap_before_write_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/swap-parent.txt", gate_result=gate)
            original_guard = sandbox_artifact_runner.validate_workspace_target_path
            calls = {"count": 0}

            def swap_parent_after_second_validation(workspace_root, target_path):
                result = original_guard(workspace_root, target_path)
                calls["count"] += 1
                if calls["count"] == 3 and result.allowed:
                    parent = Path(result.resolved_absolute_target_path or "").parent
                    parent.rmdir()
                    parent.symlink_to(Path(outside), target_is_directory=True)
                return result

            with patch.object(
                sandbox_artifact_runner,
                "validate_workspace_target_path",
                side_effect=swap_parent_after_second_validation,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse(result.write_attempted)
            self.assertFalse((Path(outside) / "swap-parent.txt").exists())
            self.assertIn("symlink", result.blocked_reason)

    def test_workspace_root_replacement_after_initial_validation_blocks(self):
        with TemporaryDirectory() as base, TemporaryDirectory() as switch_dir:
            base_path = Path(base)
            workspace = base_path / "workspace"
            displaced = base_path / "displaced-workspace"
            workspace.mkdir()
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/root-race.txt", gate_result=gate)
            original_guard = sandbox_artifact_runner.validate_workspace_target_path
            calls = {"count": 0}

            def replace_root_before_revalidation(workspace_root, target_path):
                calls["count"] += 1
                if calls["count"] == 2:
                    workspace.rename(displaced)
                    workspace.mkdir()
                return original_guard(workspace_root, target_path)

            with patch.object(
                sandbox_artifact_runner,
                "validate_workspace_target_path",
                side_effect=replace_root_before_revalidation,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    str(workspace),
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse((workspace / "reports" / "root-race.txt").exists())
            self.assertFalse((displaced / "reports" / "root-race.txt").exists())

    def test_parent_directory_replacement_after_initial_validation_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            parent = root / "reports"
            displaced = Path(outside) / "displaced-reports"
            parent.mkdir()
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/parent-race.txt", gate_result=gate)
            original_guard = sandbox_artifact_runner.validate_workspace_target_path
            calls = {"count": 0}

            def replace_parent_before_revalidation(workspace_root, target_path):
                calls["count"] += 1
                if calls["count"] == 2:
                    parent.rename(displaced)
                    parent.mkdir()
                return original_guard(workspace_root, target_path)

            with patch.object(
                sandbox_artifact_runner,
                "validate_workspace_target_path",
                side_effect=replace_parent_before_revalidation,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse((parent / "parent-race.txt").exists())
            self.assertFalse((displaced / "parent-race.txt").exists())

    def test_failed_pre_effect_revalidation_creates_no_parent_directory(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/no-directory.txt", gate_result=gate)
            original_guard = sandbox_artifact_runner.validate_workspace_target_path
            calls = {"count": 0}

            def block_second_validation(workspace_root, target_path):
                calls["count"] += 1
                if calls["count"] == 2:
                    return original_guard(None, target_path)
                return original_guard(workspace_root, target_path)

            with patch.object(
                sandbox_artifact_runner,
                "validate_workspace_target_path",
                side_effect=block_second_validation,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse((root / "reports").exists())

    def test_preexisting_temporary_collision_is_not_deleted(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            parent = root / "reports"
            parent.mkdir()
            temporary = parent / ".collision.txt.tmp"
            temporary.write_text("unrelated sentinel", encoding="utf-8")
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/collision.txt", gate_result=gate)

            result = sandbox_artifact_runner.write_sandbox_artifact(
                request,
                workspace,
                approval_evidence=gate,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertEqual("unrelated sentinel", temporary.read_text(encoding="utf-8"))
            self.assertFalse((parent / "collision.txt").exists())

    def test_overwrite_target_replacement_before_final_placement_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            target = root / "replace.txt"
            displaced = root / "reviewed-target.txt"
            target.write_text("reviewed target", encoding="utf-8")
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="replace.txt", gate_result=gate)
            real_fsync = sandbox_artifact_runner.posix.fsync
            calls = {"count": 0}

            def replace_target_after_temp_write(fd):
                real_fsync(fd)
                calls["count"] += 1
                if calls["count"] == 1:
                    target.rename(displaced)
                    target.write_text("foreign target", encoding="utf-8")

            with patch.object(
                sandbox_artifact_runner.posix,
                "fsync",
                side_effect=replace_target_after_temp_write,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    allow_overwrite=True,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertEqual("foreign target", target.read_text(encoding="utf-8"))
            self.assertEqual("reviewed target", displaced.read_text(encoding="utf-8"))
            self.assertFalse((root / ".replace.txt.tmp").exists())

    def test_target_created_by_another_actor_before_final_placement_is_preserved(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            target = root / "created-race.txt"
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="created-race.txt", gate_result=gate)
            real_fsync = sandbox_artifact_runner.posix.fsync
            calls = {"count": 0}

            def create_target_after_temp_write(fd):
                real_fsync(fd)
                calls["count"] += 1
                if calls["count"] == 1:
                    target.write_text("foreign target", encoding="utf-8")

            with patch.object(
                sandbox_artifact_runner.posix,
                "fsync",
                side_effect=create_target_after_temp_write,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertEqual("foreign target", target.read_text(encoding="utf-8"))
            self.assertFalse((root / ".created-race.txt.tmp").exists())

    def test_temporary_file_replaced_by_symlink_before_placement_blocks(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            parent = root / "reports"
            parent.mkdir()
            target = parent / "temp-swap.txt"
            temporary = parent / ".temp-swap.txt.tmp"
            outside_file = Path(outside) / "outside.txt"
            outside_file.write_text("outside sentinel", encoding="utf-8")
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/temp-swap.txt", gate_result=gate)
            real_fsync = sandbox_artifact_runner.posix.fsync
            calls = {"count": 0}

            def swap_temp_after_write(fd):
                real_fsync(fd)
                calls["count"] += 1
                if calls["count"] == 1:
                    temporary.unlink()
                    temporary.symlink_to(outside_file)

            with patch.object(
                sandbox_artifact_runner.posix,
                "fsync",
                side_effect=swap_temp_after_write,
            ):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertFalse(target.exists())
            self.assertTrue(temporary.is_symlink())
            self.assertEqual("outside sentinel", outside_file.read_text(encoding="utf-8"))

    def test_partial_write_failure_removes_only_owned_temp_and_created_parent(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            root = Path(workspace)
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/partial.txt", gate_result=gate)

            with patch.object(sandbox_artifact_runner.posix, "write", return_value=0):
                result = sandbox_artifact_runner.write_sandbox_artifact(
                    request,
                    workspace,
                    approval_evidence=gate,
                    write_kill_switch_path=str(switch_path),
                    write_kill_switch_directory=switch_dir,
                )

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertEqual([], list(root.iterdir()))

    def test_workspace_guard_result_cannot_substitute_for_human_gate(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            guard = validate_workspace_target_path(workspace, "reports/inert.txt")
            gate = self.gate()
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            request = self.request(relative_output_path="reports/inert.txt", gate_result=gate)

            result = sandbox_artifact_runner.write_sandbox_artifact(
                request,
                workspace,
                approval_evidence=guard,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )

            self.assertTrue(guard.allowed)
            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertEqual([], list(Path(workspace).iterdir()))

    def test_environment_and_metadata_cannot_supply_workspace_boundary(self):
        authority_looking = {
            "allowed": True,
            "trusted": True,
            "validated": True,
            "workspace_safe": True,
            "path_safe": True,
            "toctou_safe": True,
            "approved": True,
            "authority": True,
            "allow_write": True,
        }
        with patch.dict(
            os.environ,
            {
                "AOIA_WORKSPACE_ROOT": "/tmp/authority-looking-workspace",
                "WORKSPACE_SAFE": "true",
            },
        ):
            missing = validate_workspace_root(None)
            metadata = validate_workspace_root(authority_looking)  # type: ignore[arg-type]

        self.assertFalse(missing.allowed)
        self.assertFalse(metadata.allowed)

    def test_valid_full_control_write_chain_writes_only_reviewed_target(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as switch_dir:
            switch_path = self.write_switch(switch_dir, WRITES_ENABLED)
            result = write_preview_artifact_after_human_gate(
                preview=self.preview(),
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=self.gate(),
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )
            output = Path(workspace) / "reports" / "step16.txt"

            self.assertTrue(result.artifact_write_occurred)
            self.assertEqual(CONTENT, output.read_text(encoding="utf-8"))
            self.assertEqual([output], [path for path in Path(workspace).rglob("*") if path.is_file()])

    def test_workspace_guard_authority_fields_remain_false(self):
        forced = WorkspaceGuardResult(
            status=WORKSPACE_GUARD_ALLOWED,
            allowed=True,
            reason_code=WORKSPACE_GUARD_ALLOWED,
            reason="forced fields are normalized",
            workspace_root="/tmp/workspace",
            normalized_relative_target_path="reports/result.txt",
            resolved_absolute_target_path="/tmp/workspace/reports/result.txt",
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

        self.assertTrue(forced.allowed)
        self.assertFalse(forced.can_approve)
        self.assertFalse(forced.can_write)
        self.assertFalse(forced.can_execute)
        self.assertFalse(forced.can_commit)
        self.assertFalse(forced.can_push)
        self.assertFalse(forced.can_call_provider)
        self.assertFalse(forced.can_change_gate)
        self.assertFalse(forced.write_authority_granted)
        self.assertFalse(forced.execution_authority_granted)
        self.assertFalse(forced.provider_authority_granted)

    def test_static_no_new_capability_scan_includes_workspace_guard_module(self):
        forbidden_import_prefixes = (
            "subprocess",
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
        )
        forbidden_calls = {
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "Popen",
            "eval",
            "exec",
            "__import__",
        }
        scan = scan_module(WORKSPACE_GUARD_MODULE)

        self.assertEqual(
            [],
            [
                module_name
                for module_name in scan["imports"]
                if matches_any_prefix(module_name, forbidden_import_prefixes)
            ],
        )
        self.assertEqual(
            [],
            [call_name for call_name in scan["calls"] if call_name in forbidden_calls],
        )

    def preview(self):
        return build_artifact_preview(
            ArtifactPreviewRequest(
                target_path="reports/step16.txt",
                proposed_content=CONTENT,
                artifact_kind="text",
            )
        )

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="step-16-run",
            sandbox_request_id="step-16-sandbox-request",
            sandbox_result_id="step-16-sandbox-result",
            requested_by="human-reviewer-step-16",
            dry_run_trace_id="step-16-dry-run-trace",
            sandbox_policy_decision_id="step-16-sandbox-policy-decision",
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-step-16",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-step-16",
            reason="reviewed exact Step 16 artifact content",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )
        with TemporaryDirectory() as audit_dir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(audit_dir),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
            )
        return evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )

    def request(self, *, relative_output_path: str = "reports/step16.txt", gate_result=None):
        nested_gate = (gate_result or self.gate()).gate_result
        assert nested_gate is not None
        return create_sandbox_artifact_request(
            run_id="step-16-run",
            sandbox_request_id="step-16-sandbox-request",
            sandbox_result_id="step-16-sandbox-result",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=relative_output_path,
            content_text=CONTENT,
            requested_by="human-reviewer-step-16",
            human_approved=True,
            dry_run_trace_id="step-16-dry-run-trace",
            audit_event_id=nested_gate.audit_event_id or "audit-event-step-16",
            approval_decision_id=nested_gate.approval_decision_id or "approval-decision-step-16",
            sandbox_policy_decision_id="step-16-sandbox-policy-decision",
            contract_audit_event_id=nested_gate.audit_event_id or "audit-event-step-16",
        )

    @staticmethod
    def write_switch(switch_dir: str, value: str) -> Path:
        switch_path = Path(switch_dir) / "write_kill_switch.state"
        switch_path.write_text(value, encoding="utf-8")
        return switch_path


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
