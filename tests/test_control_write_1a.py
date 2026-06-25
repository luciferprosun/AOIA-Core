from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import unittest

from runtime.artifact_preview import (
    ArtifactPreviewRequest,
    ArtifactPreviewStatus,
    build_artifact_preview,
)
from runtime.control_write import (
    CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
    CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
    CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
    ControlWriteContext,
    write_preview_artifact_after_human_gate,
)
from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import evaluate_human_decision_pre_artifact_gate
from runtime.human_decision_gated_artifact_write import (
    ARTIFACT_WRITTEN,
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    write_artifact_after_human_gate,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_WRITE = REPO_ROOT / "runtime" / "control_write.py"
PACKET_HASH = "a" * 64
CONTENT = "# Step 10 controlled artifact\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class ControlWrite1ATests(unittest.TestCase):
    def test_valid_preview_and_gate_delegates_to_existing_writer(self):
        preview = self.preview()
        gate = self.gate()
        writer = Mock(wraps=write_artifact_after_human_gate)

        with TemporaryDirectory() as workspace:
            result = write_preview_artifact_after_human_gate(
                preview=preview,
                proposed_content_text=CONTENT,
                workspace_root=workspace,
                gate_result=gate,
                context=self.context(),
                expected_packet_hash=PACKET_HASH,
                gated_writer=writer,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]
            written_content = files[0].read_text(encoding="utf-8")

        self.assertEqual(1, writer.call_count)
        artifact_request = writer.call_args.kwargs["artifact_request"]
        self.assertEqual(preview.target_path, artifact_request.relative_output_path)
        self.assertEqual(preview.proposed_sha256, artifact_request.content_hash)
        self.assertTrue(artifact_request.human_approved)
        self.assertTrue(artifact_request.artifact_write_allowed)
        self.assertEqual(ARTIFACT_WRITTEN, result.status)
        self.assertTrue(result.artifact_write_occurred)
        self.assertEqual(1, len(files))
        self.assertEqual(CONTENT, written_content)

    def test_invalid_or_blocking_preview_fails_closed_before_writer(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        invalid = self.preview(target_path="../blocked.md")
        blocked = replace(self.preview(), status=ArtifactPreviewStatus.BLOCKED_BY_POLICY)

        for preview in (invalid, blocked):
            with self.subTest(status=preview.status):
                result = self.run_bridge(preview=preview, writer=writer)
                self.assertEqual(CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, result.status)
                self.assertFalse(result.artifact_write_occurred)

        self.assertEqual(0, writer.call_count)

    def test_hash_mismatch_fails_before_writer(self):
        writer = Mock(wraps=write_artifact_after_human_gate)

        result = self.run_bridge(proposed_content_text="changed\n", writer=writer)

        self.assertEqual(CONTROL_WRITE_BLOCKED_HASH_MISMATCH, result.status)
        self.assertEqual(0, writer.call_count)

    def test_missing_human_gate_evidence_fails_closed(self):
        writer = Mock(wraps=write_artifact_after_human_gate)

        result = self.run_bridge(gate_result={}, writer=writer)

        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)

    def test_stale_or_mismatched_packet_or_artifact_hash_fails_closed(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        stale_packet = self.run_bridge(expected_packet_hash="b" * 64, writer=writer)
        gate = self.gate().to_dict()
        gate["artifact_hash"] = "c" * 64
        stale_artifact = self.run_bridge(gate_result=gate, writer=writer)

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, stale_packet.status)
        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, stale_artifact.status)
        self.assertEqual(0, writer.call_count)

    def test_provider_critic_and_tag_metadata_cannot_approve(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        preview = self.preview(
            provider_output_trust="untrusted",
            critic_verdict="warning: review manually",
        )
        metadata = {
            "provider": "APPROVED",
            "critic": "APPROVE",
            "tags": ["TAG_APPROVED"],
            "tetrads": ["TETRAD_APPROVED"],
            "hats": ["HAT_APPROVED"],
        }

        result = self.run_bridge(
            preview=preview,
            gate_result={"decision": "APPROVE"},
            metadata=metadata,
            writer=writer,
        )

        self.assertTrue(preview.human_review_required)
        self.assertEqual(CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE, result.status)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)
        self.assertEqual(0, writer.call_count)

    def test_inert_authority_flags_cannot_be_bypassed(self):
        writer = Mock(wraps=write_artifact_after_human_gate)
        preview = self.preview()
        object.__setattr__(preview, "can_write", True)

        result = self.run_bridge(preview=preview, writer=writer)

        self.assertEqual(CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, result.status)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual(0, writer.call_count)

    def test_no_forbidden_imports_or_capabilities_added(self):
        forbidden_modules = {
            "subprocess",
            "os",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "git",
        }
        forbidden_calls = (
            "open(",
            ".write(",
            "system(",
            "popen(",
            "eval(",
            "exec(",
        )
        source = CONTROL_WRITE.read_text(encoding="utf-8")
        lowered = source.casefold()
        for term in forbidden_calls:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            with self.subTest(module=module_name):
                self.assertFalse(
                    any(
                        module_name == forbidden
                        or module_name.startswith(forbidden + ".")
                        for forbidden in forbidden_modules
                    )
                )

    def run_bridge(
        self,
        *,
        preview=None,
        proposed_content_text: str = CONTENT,
        gate_result=None,
        expected_packet_hash: str | None = PACKET_HASH,
        metadata=None,
        writer=None,
    ):
        with TemporaryDirectory() as workspace:
            result = write_preview_artifact_after_human_gate(
                preview=preview or self.preview(),
                proposed_content_text=proposed_content_text,
                workspace_root=workspace,
                gate_result=self.gate() if gate_result is None else gate_result,
                context=self.context(),
                expected_packet_hash=expected_packet_hash,
                metadata=metadata,
                gated_writer=writer or write_artifact_after_human_gate,
            )
            self.assertFalse(any(path.is_file() for path in Path(workspace).rglob("*")))
            return result

    def preview(self, **changes):
        values = {
            "target_path": "reports/step10.txt",
            "proposed_content": CONTENT,
            "artifact_kind": "text",
        }
        values.update(changes)
        return build_artifact_preview(ArtifactPreviewRequest(**values))

    def context(self) -> ControlWriteContext:
        return ControlWriteContext(
            run_id="step-10-run",
            sandbox_request_id="step-10-sandbox-request",
            sandbox_result_id="step-10-sandbox-result",
            requested_by="human-reviewer-step-10",
            dry_run_trace_id="step-10-dry-run-trace",
            sandbox_policy_decision_id="step-10-sandbox-policy-decision",
        )

    def gate(self):
        capture = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-step-10",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-step-10",
            reason="reviewed exact Step 10 artifact content",
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


if __name__ == "__main__":
    unittest.main()
