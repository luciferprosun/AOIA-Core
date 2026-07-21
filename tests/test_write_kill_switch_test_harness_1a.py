from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.write_kill_switch import (
    WRITES_DISABLED,
    WRITES_ENABLED,
    WRITE_KILL_SWITCH_BLOCKED_DISABLED,
    WRITE_KILL_SWITCH_BLOCKED_EMPTY,
    WRITE_KILL_SWITCH_BLOCKED_MALFORMED,
    WRITE_KILL_SWITCH_BLOCKED_MISSING,
    evaluate_write_kill_switch_value,
    resolve_required_write_kill_switch,
)
from runtime.schemas.sandbox_artifact import SandboxArtifactState
from tests.canonical_human_gate_support import canonical_gate_and_artifact_request
from tests.write_kill_switch_test_support_1a import enabled_test_write_kill_switch


class WriteKillSwitchTestHarness1ATests(unittest.TestCase):
    def test_missing_empty_malformed_and_explicit_off_remain_fail_closed(self) -> None:
        cases = (
            (resolve_required_write_kill_switch(), WRITE_KILL_SWITCH_BLOCKED_MISSING),
            (evaluate_write_kill_switch_value(""), WRITE_KILL_SWITCH_BLOCKED_EMPTY),
            (
                evaluate_write_kill_switch_value(WRITES_ENABLED + "\n" + WRITES_DISABLED),
                WRITE_KILL_SWITCH_BLOCKED_MALFORMED,
            ),
            (evaluate_write_kill_switch_value(WRITES_DISABLED), WRITE_KILL_SWITCH_BLOCKED_DISABLED),
        )

        for result, expected_status in cases:
            with self.subTest(status=expected_status):
                self.assertFalse(result.writes_allowed)
                self.assertEqual(expected_status, result.status.value)

    def test_enabled_test_switch_is_explicit_non_authoritative_and_removed_on_exit(self) -> None:
        with enabled_test_write_kill_switch() as switch:
            switch_path = Path(switch.path)
            switch_directory = Path(switch.directory)
            result = switch.check()

            self.assertTrue(switch_path.is_file())
            self.assertEqual(0o600, switch_path.stat().st_mode & 0o777)
            self.assertTrue(result.writes_allowed)
            self.assertFalse(result.can_approve)
            self.assertFalse(result.can_write)
            self.assertFalse(result.can_change_gate)
            self.assertFalse(result.write_authority_granted)

        self.assertFalse(switch_path.exists())
        self.assertFalse(switch_directory.exists())
        self.assertFalse(resolve_required_write_kill_switch().writes_allowed)

    def test_nested_test_switches_are_isolated(self) -> None:
        with enabled_test_write_kill_switch() as first:
            first_path = Path(first.path)
            with enabled_test_write_kill_switch() as second:
                second_path = Path(second.path)
                self.assertNotEqual(first.path, second.path)
                self.assertTrue(first.check().writes_allowed)
                self.assertTrue(second.check().writes_allowed)
            self.assertFalse(second_path.exists())
            self.assertTrue(first_path.exists())
            self.assertTrue(first.check().writes_allowed)

        self.assertFalse(first_path.exists())

    def test_enabled_switch_alone_does_not_grant_human_gate_authority(self) -> None:
        _gate, request = canonical_gate_and_artifact_request(
            relative_output_path="missing-gate.md",
            content_text="kill-switch is not approval\n",
        )
        with TemporaryDirectory() as workspace, enabled_test_write_kill_switch() as switch:
            result = switch.write_sandbox_artifact(request, workspace)

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertIn("canonical human gate evidence", result.blocked_reason)
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_enabled_switch_does_not_bypass_hash_binding(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="hash-bound.md",
            content_text="human-reviewed content\n",
        )
        changed = replace(request, content_text="different unreviewed content\n")
        changed = replace(
            changed,
            contract_payload_hash=hashlib.sha256(changed.content_text.encode("utf-8")).hexdigest(),
        )
        with TemporaryDirectory() as workspace, enabled_test_write_kill_switch() as switch:
            result = switch.write_sandbox_artifact(changed, workspace, approval_evidence=gate)

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertIn("artifact hash", result.blocked_reason)
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_enabled_switch_does_not_bypass_workspace_or_path_traversal(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="../outside.md",
            content_text="workspace confinement remains mandatory\n",
        )
        with TemporaryDirectory() as workspace, enabled_test_write_kill_switch() as switch:
            result = switch.write_sandbox_artifact(request, workspace, approval_evidence=gate)

            self.assertEqual(SandboxArtifactState.BLOCKED, result.state)
            self.assertIn("path traversal", result.blocked_reason)
            self.assertFalse(any(Path(workspace).iterdir()))
            self.assertFalse((Path(workspace).parent / "outside.md").exists())

    def test_exact_gate_and_scoped_switch_allow_only_the_bound_controlled_write(self) -> None:
        gate, request = canonical_gate_and_artifact_request(
            relative_output_path="reports/controlled.md",
            content_text="exactly reviewed controlled write\n",
        )
        with TemporaryDirectory() as workspace, enabled_test_write_kill_switch() as switch:
            result = switch.write_sandbox_artifact(request, workspace, approval_evidence=gate)
            target = Path(workspace) / "reports" / "controlled.md"

            self.assertEqual(SandboxArtifactState.WRITTEN, result.state)
            self.assertEqual(request.content_text, target.read_text(encoding="utf-8"))
            self.assertEqual((target,), tuple(path for path in Path(workspace).rglob("*") if path.is_file()))


if __name__ == "__main__":
    unittest.main()
