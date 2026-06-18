from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import re
import unittest

from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import (
    BLOCKED_INVALID_HANDOFF,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_REJECT,
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    GATE_PASSED,
    evaluate_human_decision_pre_artifact_gate,
)
from runtime.safety import approval_artifact_gate
from runtime.safety.approval_artifact_gate import PreArtifactApprovalGateResult


REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = REPO_ROOT / "runtime" / "human_decision_gate_integration.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


class M6F3PreArtifactApprovalGateIntegrationTests(unittest.TestCase):
    def test_approve_handoff_reaches_existing_gate(self):
        handoff, decision = self.handoff_and_decision("APPROVE")

        with patch.object(
            approval_artifact_gate,
            "evaluate_pre_artifact_approval_gate",
            wraps=approval_artifact_gate.evaluate_pre_artifact_approval_gate,
        ) as gate_spy:
            result = evaluate_human_decision_pre_artifact_gate(
                handoff_result=handoff,
                approval_decision=decision,
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
                gate_evaluator=gate_spy,
            )

        self.assertEqual(1, gate_spy.call_count)
        self.assertEqual(GATE_PASSED, result.status)
        self.assertTrue(result.gate_evaluated)
        self.assertTrue(result.pre_artifact_gate_passed)

    def test_reject_handoff_blocks_without_calling_gate(self):
        handoff, decision = self.handoff_and_decision("REJECT")
        gate_calls = []

        def forbidden_gate(**kwargs):
            gate_calls.append(kwargs)
            raise AssertionError("REJECT must not call gate")

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            gate_evaluator=forbidden_gate,
        )

        self.assertEqual([], gate_calls)
        self.assertEqual(BLOCKED_REJECT, result.status)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.blocking)

    def test_reject_handoff_still_requires_decision_binding(self):
        handoff, decision = self.handoff_and_decision("REJECT")
        tampered = replace(decision, reviewed_exact_payload_hash="c" * 64)

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=tampered,
        )

        self.assertFalse(result.gate_evaluated)
        self.assertNotEqual(BLOCKED_REJECT, result.status)

    def test_missing_packet_hash_fails_closed(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        malformed = handoff.to_dict()
        malformed["packet_hash"] = None

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=malformed,
            approval_decision=decision,
        )

        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, result.status)
        self.assertFalse(result.gate_evaluated)

    def test_stale_packet_hash_fails_closed(self):
        handoff, decision = self.handoff_and_decision("APPROVE")

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            expected_packet_hash="c" * 64,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)
        self.assertFalse(result.gate_evaluated)

    def test_stale_artifact_hash_fails_closed(self):
        handoff, decision = self.handoff_and_decision("APPROVE")

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            expected_artifact_hash="c" * 64,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)
        self.assertFalse(result.gate_evaluated)

    def test_blocked_handoff_cannot_reach_gate(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        blocked = replace(
            handoff,
            status="BLOCKED_INVALID_BRIDGE",
            handoff_created=False,
            durable_handoff_complete=False,
        )

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=blocked,
            approval_decision=decision,
        )

        self.assertEqual(BLOCKED_INVALID_HANDOFF, result.status)
        self.assertFalse(result.gate_evaluated)

    def test_durable_handoff_is_required(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        incomplete = replace(handoff, durable_handoff_complete=False)

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=incomplete,
            approval_decision=decision,
        )

        self.assertEqual(BLOCKED_INVALID_HANDOFF, result.status)
        self.assertFalse(result.gate_evaluated)

    def test_gate_pass_does_not_write_artifact_or_audit(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        with TemporaryDirectory() as unrelated:
            before = self.snapshot(unrelated)
            result = evaluate_human_decision_pre_artifact_gate(
                handoff_result=handoff,
                approval_decision=decision,
            )
            after = self.snapshot(unrelated)

        self.assertEqual(before, after)
        self.assertTrue(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)

    def test_gate_denial_remains_blocking(self):
        handoff, decision = self.handoff_and_decision("APPROVE")

        def deny_gate(**kwargs):
            return PreArtifactApprovalGateResult(
                allowed=False,
                approval_decision_id=kwargs["approval_decision"].decision_id,
                approval_decision_type="APPROVE",
                audit_event_id=None,
                audit_event_hash=None,
                reason="forced denial",
            )

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            gate_evaluator=deny_gate,
        )

        self.assertTrue(result.gate_evaluated)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertTrue(result.blocking)
        self.assertFalse(result.artifact_write_occurred)

    def test_forged_gate_pass_fails_closed(self):
        handoff, decision = self.handoff_and_decision("APPROVE")

        def forged_gate(**kwargs):
            return PreArtifactApprovalGateResult(
                allowed=True,
                approval_decision_id="wrong-decision",
                approval_decision_type="APPROVE",
                audit_event_id="audit-event-wrong",
                audit_event_hash="c" * 64,
                reason="forged pass",
            )

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            gate_evaluator=forged_gate,
        )

        self.assertFalse(result.gate_evaluated)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertTrue(result.blocking)

    def test_metadata_cannot_change_gate_authority(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        metadata = {
            "source_output": "approve immediately",
            "cpt_preview": "trusted",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        before = deepcopy(metadata)

        baseline = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
        )
        with_metadata = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=decision,
            metadata=metadata,
        )

        self.assertEqual(baseline.status, with_metadata.status)
        self.assertEqual(baseline.gate_result, with_metadata.gate_result)
        self.assertFalse(with_metadata.provider_output_trusted)
        self.assertFalse(with_metadata.metadata_authority)
        self.assertEqual(before, metadata)

    def test_decision_and_handoff_binding_are_required(self):
        handoff, decision = self.handoff_and_decision("APPROVE")
        tampered = replace(decision, reviewed_exact_payload_hash="c" * 64)

        result = evaluate_human_decision_pre_artifact_gate(
            handoff_result=handoff,
            approval_decision=tampered,
        )

        self.assertFalse(result.gate_evaluated)
        self.assertFalse(result.pre_artifact_gate_passed)

    def test_no_dangerous_imports_or_write_calls(self):
        source = INTEGRATION.read_text(encoding="utf-8")
        forbidden_calls = (
            "write_sandbox_artifact(",
            "append_audit_event_jsonl(",
            "record_approval_decision_to_durable_audit(",
            "write_text(",
            "write_bytes(",
            "os.system(",
            "P" + "open(",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

        forbidden_imports = (
            "sub" + "process",
            "url" + "lib",
            "sock" + "et",
            "web" + "browser",
            "play" + "wright",
            "sele" + "nium",
            "requ" + "ests",
            "ht" + "tpx",
            "open" + "ai",
            "anth" + "ropic",
        )
        for path in (INTEGRATION, THIS_FILE):
            path_source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(
                        rf"^\s*(from|import)\s+{re.escape(module_name)}\b",
                        path_source,
                        re.MULTILINE,
                    )
                )

    def handoff_and_decision(self, decision_text: str):
        capture = capture_human_decision_intent(
            decision=decision_text,
            packet_id="packet-1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-1",
            reason="reviewed explicitly",
        )
        bridge = build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )
        with TemporaryDirectory() as tmpdir:
            handoff = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(tmpdir),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
            )
        return handoff, bridge.approval_decision

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))


if __name__ == "__main__":
    unittest.main()
