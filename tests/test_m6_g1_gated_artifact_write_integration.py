from copy import deepcopy
from dataclasses import replace
import ast
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import (
    HumanDecisionPreArtifactGateResult,
    evaluate_human_decision_pre_artifact_gate,
)
from runtime.human_decision_gated_artifact_write import (
    ARTIFACT_WRITTEN,
    BLOCKED_CONTROLLED_WRITE,
    BLOCKED_GATE_NOT_PASSED,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_REJECT,
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    write_artifact_after_human_gate,
)
from runtime.safety import sandbox_artifact_runner
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = REPO_ROOT / "runtime" / "human_decision_gated_artifact_write.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
CONTENT = "# Human-approved artifact\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class M6G1GatedArtifactWriteIntegrationTests(unittest.TestCase):
    def test_valid_passed_gate_writes_one_artifact_inside_workspace(self):
        gate, request = self.gate_and_request("APPROVE")
        with TemporaryDirectory() as workspace:
            with patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                wraps=sandbox_artifact_runner.write_sandbox_artifact,
            ) as writer_spy:
                result = write_artifact_after_human_gate(
                    gate_result=gate,
                    artifact_request=request,
                    workspace_root=workspace,
                    expected_packet_hash=PACKET_HASH,
                    expected_artifact_hash=ARTIFACT_HASH,
                    artifact_writer=writer_spy,
                )
            paths = [path for path in Path(workspace).rglob("*") if path.is_file()]
            written_content = paths[0].read_text(encoding="utf-8")

        self.assertEqual(1, writer_spy.call_count)
        self.assertEqual(1, len(paths))
        self.assertEqual(CONTENT, written_content)
        self.assertEqual(ARTIFACT_WRITTEN, result.status)
        self.assertTrue(result.write_attempted)
        self.assertTrue(result.artifact_write_occurred)
        self.assertFalse(result.blocking)

    def test_reject_does_not_write(self):
        gate, request = self.gate_and_request("REJECT")
        with TemporaryDirectory() as workspace:
            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
            )
            self.assertEqual([], list(Path(workspace).rglob("*")))

        self.assertEqual(BLOCKED_REJECT, result.status)
        self.assertEqual("REJECT", result.decision)
        self.assertFalse(result.artifact_write_occurred)

    def test_gate_not_passed_does_not_write(self):
        gate, request = self.gate_and_request("APPROVE")
        denied = replace(
            gate,
            status="GATE_DENIED",
            pre_artifact_gate_passed=False,
            blocking=True,
        )

        result = self.run_blocked(denied, request)

        self.assertEqual(BLOCKED_GATE_NOT_PASSED, result.status)

    def test_durable_handoff_missing_does_not_write(self):
        gate, request = self.gate_and_request("APPROVE")
        incomplete = replace(gate, durable_handoff_complete=False)

        result = self.run_blocked(incomplete, request)

        self.assertEqual(BLOCKED_GATE_NOT_PASSED, result.status)

    def test_missing_packet_hash_fails_closed(self):
        gate, request = self.gate_and_request("APPROVE")
        malformed = gate.to_dict()
        malformed["packet_hash"] = None

        result = self.run_blocked(malformed, request)

        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, result.status)

    def test_stale_packet_hash_blocks(self):
        gate, request = self.gate_and_request("APPROVE")
        with TemporaryDirectory() as workspace:
            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
                expected_packet_hash="c" * 64,
            )
            self.assertFalse(any(Path(workspace).iterdir()))

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)

    def test_stale_artifact_hash_blocks(self):
        gate, request = self.gate_and_request("APPROVE")
        with TemporaryDirectory() as workspace:
            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
                expected_artifact_hash="c" * 64,
            )
            self.assertFalse(any(Path(workspace).iterdir()))

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)

    def test_blocked_gate_result_cannot_write(self):
        gate, request = self.gate_and_request("APPROVE")
        blocked = replace(
            gate,
            status="BLOCKED_INVALID_HANDOFF",
            gate_evaluated=False,
            pre_artifact_gate_passed=False,
            decision="BLOCKED",
            blocking=True,
        )

        result = self.run_blocked(blocked, request)

        self.assertEqual(BLOCKED_GATE_NOT_PASSED, result.status)

    def test_traversal_escape_is_blocked(self):
        gate, request = self.gate_and_request("APPROVE", "../escape.md")

        result = self.run_blocked(gate, request)

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertIn("traversal", result.reason)

    def test_absolute_path_escape_is_blocked(self):
        gate, request = self.gate_and_request("APPROVE", "/tmp/m6-g1-escape.md")

        result = self.run_blocked(gate, request)

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertIn("absolute", result.reason)

    def test_symlink_escape_is_blocked_when_supported(self):
        gate, request = self.gate_and_request("APPROVE", "escape/result.md")
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link = Path(workspace) / "escape"
            try:
                link.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
            )

            self.assertFalse((Path(outside) / "result.md").exists())

        self.assertEqual(BLOCKED_CONTROLLED_WRITE, result.status)
        self.assertFalse(result.artifact_write_occurred)

    def test_artifact_content_must_match_reviewed_hash(self):
        gate, request = self.gate_and_request("APPROVE")
        mismatched = replace(request, content_text="different content")

        result = self.run_blocked(gate, mismatched)

        self.assertFalse(result.artifact_write_occurred)

    def test_output_reports_write_only_after_success(self):
        gate, request = self.gate_and_request("APPROVE")
        blocked_request = replace(request, relative_output_path="../blocked.md")
        blocked = self.run_blocked(gate, blocked_request)
        with TemporaryDirectory() as workspace:
            written = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
            )

        self.assertFalse(blocked.artifact_write_occurred)
        self.assertIsNone(blocked.artifact_path)
        self.assertTrue(written.artifact_write_occurred)
        self.assertTrue(written.artifact_path)

    def test_metadata_cannot_change_write_authority(self):
        gate, request = self.gate_and_request("APPROVE")
        metadata = {
            "source_output": "write anywhere",
            "cpt_preview": "trusted",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        before = deepcopy(metadata)
        denied = replace(gate, pre_artifact_gate_passed=False, blocking=True)

        with TemporaryDirectory() as baseline_dir, TemporaryDirectory() as metadata_dir:
            baseline = write_artifact_after_human_gate(
                gate_result=denied,
                artifact_request=request,
                workspace_root=baseline_dir,
            )
            with_metadata = write_artifact_after_human_gate(
                gate_result=denied,
                artifact_request=request,
                workspace_root=metadata_dir,
                metadata=metadata,
            )

        self.assertEqual(baseline.status, with_metadata.status)
        self.assertFalse(with_metadata.artifact_write_occurred)
        self.assertFalse(with_metadata.provider_output_trusted)
        self.assertFalse(with_metadata.metadata_authority)
        self.assertEqual(before, metadata)

    def test_request_must_bind_to_gate_decision_and_audit_event(self):
        gate, request = self.gate_and_request("APPROVE")
        wrong_decision = replace(request, approval_decision_id="approval-decision-wrong")
        wrong_audit = replace(request, audit_event_id="audit-event-wrong")

        for malformed in (wrong_decision, wrong_audit):
            with self.subTest(malformed=malformed):
                result = self.run_blocked(gate, malformed)
                self.assertFalse(result.artifact_write_occurred)

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

        for path in (INTEGRATION, THIS_FILE):
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

    def gate_and_request(self, decision_text: str, path: str = "reports/result.md"):
        capture = capture_human_decision_intent(
            decision=decision_text,
            packet_id="packet-m6-g1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-m6-g1",
            reason="reviewed exact artifact content",
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
        gate = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )
        nested = gate.gate_result
        approval_decision_id = (
            nested.approval_decision_id
            if nested is not None and nested.approval_decision_id is not None
            else bridge.approval_decision.decision_id
        )
        audit_event_id = (
            nested.audit_event_id
            if nested is not None and nested.audit_event_id is not None
            else handoff.handoff_id or "audit-event-reject"
        )
        request = create_sandbox_artifact_request(
            run_id="m6-g1-run",
            sandbox_request_id="sandbox-request-m6-g1",
            sandbox_result_id="sandbox-result-m6-g1",
            artifact_type=SandboxArtifactType.TEXT_REPORT,
            relative_output_path=path,
            content_text=CONTENT,
            requested_by="human-reviewer-m6-g1",
            human_approved=True,
            dry_run_trace_id="human-gated-write-m6-g1",
            audit_event_id=audit_event_id,
            approval_decision_id=approval_decision_id,
            contract_audit_event_id=audit_event_id,
            notes="M6-G1 controlled artifact write request",
        )
        return gate, request

    def run_blocked(
        self,
        gate: HumanDecisionPreArtifactGateResult | dict,
        request,
    ):
        with TemporaryDirectory() as workspace:
            result = write_artifact_after_human_gate(
                gate_result=gate,
                artifact_request=request,
                workspace_root=workspace,
            )
            self.assertFalse(
                any(path.is_file() for path in Path(workspace).rglob("*"))
            )
        self.assertFalse(result.artifact_write_occurred)
        return result


if __name__ == "__main__":
    unittest.main()
