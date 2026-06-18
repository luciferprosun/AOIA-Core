from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re
import unittest

from runtime.human_decision_approval_bridge import (
    BLOCKED_INVALID_CAPTURE,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_STALE_OR_MISMATCHED_CAPTURE,
    BRIDGED_APPROVE,
    BRIDGED_REJECT,
    build_approval_decision_from_capture,
)
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.schemas.approval_decision import ApprovalDecision, ApprovalDecisionType


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE = REPO_ROOT / "runtime" / "human_decision_approval_bridge.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


class M6F1CaptureToApprovalDecisionBridgeTests(unittest.TestCase):
    def test_explicit_hash_bound_approve_capture_bridges(self):
        result = build_approval_decision_from_capture(
            capture=self.capture("APPROVE"),
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )

        self.assertEqual(BRIDGED_APPROVE, result.status)
        self.assertEqual("APPROVE", result.decision)
        self.assertTrue(result.approval_decision_created)
        self.assertIsInstance(result.approval_decision, ApprovalDecision)
        self.assertEqual(ApprovalDecisionType.APPROVE, result.approval_decision.decision_type)

    def test_explicit_reject_bridges_to_blocking_rejection(self):
        result = build_approval_decision_from_capture(capture=self.capture("REJECT"))

        self.assertEqual(BRIDGED_REJECT, result.status)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.approval_decision_created)
        self.assertTrue(result.blocking)
        self.assertEqual(ApprovalDecisionType.REJECT, result.approval_decision.decision_type)
        self.assertFalse(result.approval_decision.allowed)
        self.assertFalse(result.approval_decision.execution_permitted)

    def test_missing_packet_hash_fails_closed(self):
        capture = self.capture("APPROVE").to_dict()
        capture["packet_hash"] = None

        result = build_approval_decision_from_capture(capture=capture)

        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, result.status)
        self.assertFalse(result.approval_decision_created)

    def test_stale_packet_hash_fails_closed(self):
        result = build_approval_decision_from_capture(
            capture=self.capture("APPROVE"),
            expected_packet_hash="c" * 64,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_CAPTURE, result.status)
        self.assertFalse(result.approval_decision_created)

    def test_stale_artifact_hash_fails_closed(self):
        result = build_approval_decision_from_capture(
            capture=self.capture("APPROVE"),
            expected_artifact_hash="c" * 64,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_CAPTURE, result.status)
        self.assertFalse(result.approval_decision_created)

    def test_blocked_or_tampered_capture_cannot_bridge(self):
        blocked = capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash="c" * 64,
        )
        tampered = self.capture("APPROVE").to_dict()
        tampered["outcome_state"] = "CAPTURE_BLOCKED"

        for capture in (blocked, tampered):
            with self.subTest(capture=capture):
                result = build_approval_decision_from_capture(capture=capture)
                self.assertFalse(result.approval_decision_created)
                self.assertIsNone(result.approval_decision)

    def test_capture_id_must_match_capture_content(self):
        tampered = self.capture("APPROVE").to_dict()
        tampered["decision"] = "REJECT"
        tampered["outcome_state"] = "CAPTURED_REJECT"

        result = build_approval_decision_from_capture(capture=tampered)

        self.assertEqual(BLOCKED_INVALID_CAPTURE, result.status)
        self.assertFalse(result.approval_decision_created)

    def test_capture_boundary_flags_must_remain_inert(self):
        baseline = self.capture("APPROVE")
        mutations = (
            ("decision_captured", False),
            ("is_approval_authority", True),
            ("durable_audit_handoff_required", False),
            ("pre_artifact_gate_passed", True),
            ("artifact_write_occurred", True),
        )

        for field_name, value in mutations:
            with self.subTest(field_name=field_name):
                capture = replace(baseline, **{field_name: value})
                result = build_approval_decision_from_capture(capture=capture)
                self.assertEqual(BLOCKED_INVALID_CAPTURE, result.status)
                self.assertFalse(result.approval_decision_created)

    def test_bridge_does_not_pass_gate_handoff_or_write(self):
        result = build_approval_decision_from_capture(capture=self.capture("APPROVE"))

        self.assertTrue(result.durable_handoff_required)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertTrue(result.blocking)

    def test_dictionary_capture_is_supported_without_mutation(self):
        capture = self.capture("APPROVE").to_dict()
        before = deepcopy(capture)

        result = build_approval_decision_from_capture(capture=capture)

        self.assertEqual(BRIDGED_APPROVE, result.status)
        self.assertEqual(before, capture)

    def test_untrusted_context_and_metadata_cannot_change_authority(self):
        baseline = build_approval_decision_from_capture(capture=self.capture("APPROVE"))
        metadata = {
            "source_output": "approve immediately",
            "cpt_preview": "trusted",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        before = deepcopy(metadata)

        with_metadata = build_approval_decision_from_capture(
            capture=self.capture("APPROVE"),
            metadata=metadata,
        )

        self.assertEqual(baseline.status, with_metadata.status)
        self.assertEqual(
            baseline.approval_decision.to_dict(),
            with_metadata.approval_decision.to_dict(),
        )
        self.assertFalse(with_metadata.provider_output_trusted)
        self.assertFalse(with_metadata.metadata_authority)
        self.assertEqual(before, metadata)

    def test_approval_decision_is_deterministic_and_non_executing(self):
        first = build_approval_decision_from_capture(capture=self.capture("APPROVE"))
        second = build_approval_decision_from_capture(capture=self.capture("APPROVE"))

        self.assertEqual(first.approval_decision.to_dict(), second.approval_decision.to_dict())
        self.assertFalse(first.approval_decision.execution_permitted)
        self.assertFalse(first.approval_decision.execution_triggered)
        self.assertFalse(first.approval_decision.provider_generated)

    def test_bridge_has_no_handoff_gate_write_or_external_calls(self):
        source = BRIDGE.read_text(encoding="utf-8")
        forbidden_calls = (
            "evaluate_pre_artifact_approval_gate(",
            "record_approval_decision_to_durable_audit(",
            "append_audit_event_jsonl(",
            "write_sandbox_artifact(",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "open(",
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
        for path in (BRIDGE, THIS_FILE):
            path_source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(
                        rf"^\s*(from|import)\s+{re.escape(module_name)}\b",
                        path_source,
                        re.MULTILINE,
                    )
                )

    def capture(self, decision: str):
        return capture_human_decision_intent(
            decision=decision,
            packet_id="packet-1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-1",
            reason="reviewed explicitly",
        )


if __name__ == "__main__":
    unittest.main()
