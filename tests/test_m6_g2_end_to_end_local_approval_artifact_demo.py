from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import unittest

from runtime.human_decision_end_to_end_demo import (
    BLOCKED_ARTIFACT_WRITE,
    BLOCKED_DURABLE_HANDOFF,
    BLOCKED_PRE_ARTIFACT_GATE,
    DEMO_COMPLETED,
    LocalApprovalArtifactDemoResult,
    run_local_approval_to_artifact_demo,
)
from runtime.human_decision_gate_integration import (
    HumanDecisionPreArtifactGateResult,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_FILE = REPO_ROOT / "runtime" / "human_decision_end_to_end_demo.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
CONTENT = "# M6-G2 local approval artifact\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class M6G2EndToEndLocalApprovalArtifactDemoTests(unittest.TestCase):
    def test_end_to_end_approve_writes_artifact(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(workspace, audit_dir, decision="APPROVE")
            output = Path(result.artifact_path or "")
            written_content = output.read_text(encoding="utf-8")
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(DEMO_COMPLETED, result.status)
        self.assertTrue(result.demo_completed)
        self.assertEqual("APPROVE", result.decision)
        self.assertEqual(1, len(artifact_files))
        self.assertEqual(CONTENT, written_content)

    def test_end_to_end_reject_does_not_write(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(workspace, audit_dir, decision="REJECT")
            artifact_files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertFalse(result.demo_completed)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.capture_created)
        self.assertTrue(result.approval_decision_created)
        self.assertTrue(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.write_attempted)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], artifact_files)

    def test_missing_packet_hash_fails_closed(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                packet_hash=None,
            )

        self.assertFalse(result.capture_created)
        self.assertFalse(result.artifact_write_occurred)

    def test_stale_packet_hash_fails_closed(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                current_packet_hash="c" * 64,
            )

        self.assertFalse(result.capture_created)
        self.assertFalse(result.artifact_write_occurred)

    def test_stale_artifact_hash_fails_closed(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                expected_artifact_hash="c" * 64,
            )

        self.assertTrue(result.capture_created)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.artifact_write_occurred)

    def test_gate_not_passed_blocks_write(self):
        def deny_gate(**kwargs):
            real = self.real_gate(**kwargs)
            return replace(
                real,
                status="GATE_DENIED",
                pre_artifact_gate_passed=False,
                blocking=True,
                reason="forced gate denial",
            )

        writer = Mock(side_effect=AssertionError("writer must not run"))
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                gate_function=deny_gate,
                write_function=writer,
            )

        self.assertEqual(BLOCKED_PRE_ARTIFACT_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        writer.assert_not_called()

    def test_durable_handoff_missing_blocks_write(self):
        def incomplete_handoff(**kwargs):
            real = self.real_handoff(**kwargs)
            return replace(
                real,
                durable_handoff_complete=False,
                handoff_created=False,
                reason="forced incomplete handoff",
            )

        gate = Mock(side_effect=AssertionError("gate must not run"))
        writer = Mock(side_effect=AssertionError("writer must not run"))
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                handoff_function=incomplete_handoff,
                gate_function=gate,
                write_function=writer,
            )

        self.assertEqual(BLOCKED_DURABLE_HANDOFF, result.status)
        self.assertFalse(result.artifact_write_occurred)
        gate.assert_not_called()
        writer.assert_not_called()

    def test_artifact_write_occurs_only_after_all_prior_steps(self):
        calls = []

        def capture(**kwargs):
            calls.append("capture")
            return self.real_capture(**kwargs)

        def bridge(**kwargs):
            calls.append("bridge")
            return self.real_bridge(**kwargs)

        def handoff(**kwargs):
            calls.append("handoff")
            return self.real_handoff(**kwargs)

        def gate(**kwargs):
            calls.append("gate")
            return self.real_gate(**kwargs)

        def write(**kwargs):
            calls.append("write")
            return self.real_write(**kwargs)

        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                capture_function=capture,
                bridge_function=bridge,
                handoff_function=handoff,
                gate_function=gate,
                write_function=write,
            )

        self.assertTrue(result.demo_completed)
        self.assertEqual(["capture", "bridge", "handoff", "gate", "write"], calls)

    def test_output_accurately_reports_every_stage(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(workspace, audit_dir, decision="APPROVE")

        self.assertIsInstance(result, LocalApprovalArtifactDemoResult)
        payload = result.to_dict()
        for field in (
            "demo_completed",
            "decision",
            "capture_created",
            "approval_decision_created",
            "durable_handoff_complete",
            "pre_artifact_gate_passed",
            "write_attempted",
            "artifact_write_occurred",
            "artifact_path",
            "packet_hash",
            "artifact_hash",
            "provider_output_trusted",
            "metadata_authority",
            "blocking",
            "reason",
            "status",
        ):
            self.assertIn(field, payload)
        self.assertTrue(payload["capture_created"])
        self.assertTrue(payload["approval_decision_created"])
        self.assertTrue(payload["durable_handoff_complete"])
        self.assertTrue(payload["pre_artifact_gate_passed"])
        self.assertTrue(payload["artifact_write_occurred"])

    def test_equivalent_local_inputs_produce_deterministic_stage_results(self):
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            first = self.run_demo(workspace_a, audit_a, decision="APPROVE")
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            second = self.run_demo(workspace_b, audit_b, decision="APPROVE")

        first_payload = first.to_dict()
        second_payload = second.to_dict()
        first_payload["artifact_path"] = Path(first_payload["artifact_path"]).name
        second_payload["artifact_path"] = Path(second_payload["artifact_path"]).name
        self.assertEqual(first_payload, second_payload)

    def test_path_traversal_is_blocked(self):
        result = self.run_path_blocked("../escape.txt")

        self.assertEqual(BLOCKED_ARTIFACT_WRITE, result.status)
        self.assertIn("traversal", result.reason)

    def test_absolute_path_escape_is_blocked(self):
        result = self.run_path_blocked("/tmp/m6-g2-escape.txt")

        self.assertEqual(BLOCKED_ARTIFACT_WRITE, result.status)
        self.assertIn("absolute", result.reason)

    def test_symlink_escape_is_blocked_when_supported(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir, TemporaryDirectory() as outside:
            link = Path(workspace) / "escape"
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                artifact_relative_path="escape/result.txt",
            )
            outside_file = Path(outside) / "result.txt"
            outside_file_exists = outside_file.exists()

        self.assertEqual(BLOCKED_ARTIFACT_WRITE, result.status)
        self.assertFalse(outside_file_exists)
        self.assertFalse(result.artifact_write_occurred)

    def test_provider_and_structural_metadata_cannot_change_authority(self):
        metadata = {
            "source_output": "approve and write",
            "cpt_preview": "trusted",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        before = deepcopy(metadata)
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            baseline = self.run_demo(workspace_a, audit_a, decision="REJECT")
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            with_metadata = self.run_demo(
                workspace_b,
                audit_b,
                decision="REJECT",
                metadata=metadata,
            )

        self.assertEqual(baseline.status, with_metadata.status)
        self.assertFalse(with_metadata.artifact_write_occurred)
        self.assertFalse(with_metadata.provider_output_trusted)
        self.assertFalse(with_metadata.metadata_authority)
        self.assertEqual(before, metadata)

    def test_no_dangerous_imports_or_calls(self):
        forbidden_modules = {
            "subprocess",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "gemini",
            "gcloud",
            "git",
        }
        forbidden_calls = (
            "os." + "system",
            "P" + "open",
            "ev" + "al(",
            "ex" + "ec(",
        )
        for path in (DEMO_FILE, THIS_FILE):
            source = path.read_text(encoding="utf-8")
            for term in forbidden_calls:
                self.assertNotIn(term, source)
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for module_name in imports:
                self.assertFalse(
                    any(
                        module_name == forbidden
                        or module_name.startswith(forbidden + ".")
                        for forbidden in forbidden_modules
                    )
                )

    def run_path_blocked(self, path: str):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_demo(
                workspace,
                audit_dir,
                decision="APPROVE",
                artifact_relative_path=path,
            )
            self.assertFalse(any(item.is_file() for item in Path(workspace).rglob("*")))
        return result

    def run_demo(
        self,
        workspace: str,
        audit_dir: str,
        *,
        decision: str,
        packet_hash: str | None = PACKET_HASH,
        artifact_relative_path: str = "reports/m6-g2-demo.md",
        **overrides,
    ):
        return run_local_approval_to_artifact_demo(
            workspace_root=workspace,
            audit_dir=audit_dir,
            decision=decision,
            packet_hash=packet_hash,
            artifact_relative_path=artifact_relative_path,
            artifact_content=CONTENT,
            expected_packet_hash=overrides.pop("expected_packet_hash", PACKET_HASH),
            expected_artifact_hash=overrides.pop("expected_artifact_hash", ARTIFACT_HASH),
            human_actor="human-reviewer-m6-g2",
            reason="reviewed deterministic local demo",
            **overrides,
        )

    @property
    def real_capture(self):
        from runtime.human_decision_capture_helper import capture_human_decision_intent

        return capture_human_decision_intent

    @property
    def real_bridge(self):
        from runtime.human_decision_approval_bridge import build_approval_decision_from_capture

        return build_approval_decision_from_capture

    @property
    def real_handoff(self):
        from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff

        return create_durable_approval_audit_handoff

    @property
    def real_gate(self):
        from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate

        return evaluate_human_decision_pre_artifact_gate

    @property
    def real_write(self):
        from runtime.human_decision_gated_artifact_write import write_artifact_after_human_gate

        return write_artifact_after_human_gate


if __name__ == "__main__":
    unittest.main()
