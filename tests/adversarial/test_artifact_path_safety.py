from __future__ import annotations

import posixpath
import unittest
import unicodedata
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.safety.write_kill_switch import WRITES_ENABLED
from runtime.safety.sandbox_workspace import (
    SandboxPathTraversalBlockedError,
    assert_path_inside_workspace,
    normalize_relative_artifact_path,
    resolve_sandbox_artifact_path,
)
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactState,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)
from tests.canonical_human_gate_support import canonical_gate_and_artifact_request


class ArtifactPathSafetyAdversarialTests(unittest.TestCase):
    def make_request(self, relative_output_path: str, content_text: str = "safe artifact\n") -> SandboxArtifactRequest:
        return create_sandbox_artifact_request(
            run_id="adversarial-path-safety",
            sandbox_request_id="sandbox-request-path-safety",
            sandbox_result_id="sandbox-result-path-safety",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=relative_output_path,
            content_text=content_text,
            requested_by="unit-test",
            human_approved=True,
            dry_run_trace_id="trace-path-safety",
            audit_event_id="audit-path-safety",
        )

    def make_authorized_request(self, relative_output_path: str, content_text: str = "safe artifact\n"):
        return canonical_gate_and_artifact_request(
            relative_output_path=relative_output_path,
            content_text=content_text,
            run_id="adversarial-path-safety",
            requested_by="unit-test",
        )

    def test_absolute_path_rejected(self) -> None:
        result = self.run_blocked("/etc/passwd")

        self.assertIn("absolute artifact paths are blocked", result.blocked_reason)

    def test_relative_traversal_rejected(self) -> None:
        result = self.run_blocked("../../../etc/passwd")

        self.assertIn("artifact path traversal is blocked", result.blocked_reason)

    def test_any_parent_component_rejected(self) -> None:
        result = self.run_blocked("reports/../escape.md")

        self.assertIn("artifact path traversal is blocked", result.blocked_reason)

    def test_empty_path_component_rejected(self) -> None:
        result = self.run_blocked("reports//result.md")

        self.assertIn("empty", result.blocked_reason)

    def test_control_character_path_segment_rejected(self) -> None:
        result = self.run_blocked("reports/bad\nname.md")

        self.assertIn("control characters", result.blocked_reason)

    def test_null_byte_like_path_string_rejected(self) -> None:
        result = self.run_blocked("reports/bad\x00name.md")

        self.assertIn("control characters", result.blocked_reason)

    def test_unicode_normalization_edge_case_uses_nfc(self) -> None:
        nfc_path = "reports/caf\u00e9.md"
        nfd_path = "reports/" + unicodedata.normalize("NFD", "caf\u00e9") + ".md"

        self.assertEqual(normalize_relative_artifact_path(nfd_path), nfc_path)

    def test_symlink_inside_workspace_pointing_outside_is_not_writable(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link_path = Path(workspace) / "escape.md"
            try:
                link_path.symlink_to(Path(outside) / "outside.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            gate, request = self.make_authorized_request("escape.md")
            result = self.write_with_enabled_switch(
                request, workspace, approval_evidence=gate
            )

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse((Path(outside) / "outside.md").exists())

    def test_symlink_parent_directory_rejected(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link_path = Path(workspace) / "escape"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            gate, request = self.make_authorized_request("escape/result.md")
            result = self.write_with_enabled_switch(
                request, workspace, approval_evidence=gate
            )

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse((Path(outside) / "result.md").exists())

    def test_realpath_commonpath_containment_blocks_escape(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            outside_target = Path(outside) / "result.md"
            root = posixpath.realpath(workspace)
            target = posixpath.realpath(str(outside_target))

            self.assertNotEqual(posixpath.commonpath([root, target]), root)
            with self.assertRaises(SandboxPathTraversalBlockedError):
                assert_path_inside_workspace(workspace, str(outside_target))

    def test_realpath_commonpath_containment_allows_inside_target(self) -> None:
        with TemporaryDirectory() as workspace:
            resolved = resolve_sandbox_artifact_path(workspace, "reports/result.md")
            root = posixpath.realpath(workspace)

            self.assertEqual(posixpath.commonpath([root, resolved]), root)

    def test_extension_allowlist_rejects_executable_extensions(self) -> None:
        for bad_path in ("run.sh", "script.py", "tool.exe", "batch.bat", "cmd.cmd"):
            with self.subTest(bad_path=bad_path):
                result = self.run_blocked(bad_path)
                self.assertIn("artifact extension is not allowed", result.blocked_reason)

    def test_extension_case_handling_is_explicitly_allowed(self) -> None:
        for allowed_path in ("report.MD", "summary.Json", "notes.TXT"):
            with self.subTest(allowed_path=allowed_path):
                with TemporaryDirectory() as workspace:
                    gate, request = self.make_authorized_request(allowed_path)
                    result = self.write_with_enabled_switch(
                        request, workspace, approval_evidence=gate
                    )
                    self.assertEqual(result.state, SandboxArtifactState.WRITTEN)

    def test_double_extension_rejects_final_unsafe_suffix(self) -> None:
        result = self.run_blocked("safe.md.sh")

        self.assertIn("artifact extension is not allowed", result.blocked_reason)

    def test_write_once_overwrite_prevention(self) -> None:
        with TemporaryDirectory() as workspace:
            first_gate, request = self.make_authorized_request("result.md", "first")
            first = self.write_with_enabled_switch(
                request, workspace, approval_evidence=first_gate
            )
            second_gate, second_request = self.make_authorized_request("result.md", "second")
            second = self.write_with_enabled_switch(
                second_request, workspace, approval_evidence=second_gate
            )

            self.assertEqual(first.state, SandboxArtifactState.WRITTEN)
            self.assertEqual(second.state, SandboxArtifactState.BLOCKED)
            self.assertEqual((Path(workspace) / "result.md").read_text(encoding="utf-8"), "first")

    def test_atomic_write_failure_leaves_no_partial_target_file(self) -> None:
        oversized_content = "x" * (64 * 1024 + 1)
        with TemporaryDirectory() as workspace:
            target = Path(workspace) / "oversized.md"

            gate, request = self.make_authorized_request("oversized.md", oversized_content)
            result = self.write_with_enabled_switch(
                request, workspace, approval_evidence=gate
            )

            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(target.exists())

    def run_blocked(self, relative_output_path: str):
        with TemporaryDirectory() as workspace:
            gate, request = self.make_authorized_request(relative_output_path)
            result = self.write_with_enabled_switch(
                request, workspace, approval_evidence=gate
            )
            self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(result.write_attempted)
            self.assertFalse(result.write_completed)
            return result

    @staticmethod
    def write_with_enabled_switch(request, workspace, *args, **kwargs):
        with TemporaryDirectory() as switch_dir:
            switch_path = Path(switch_dir) / "write_kill_switch.state"
            switch_path.write_text(WRITES_ENABLED, encoding="utf-8")
            return write_sandbox_artifact(
                request,
                workspace,
                *args,
                **kwargs,
                write_kill_switch_path=str(switch_path),
                write_kill_switch_directory=switch_dir,
            )


if __name__ == "__main__":
    unittest.main()
