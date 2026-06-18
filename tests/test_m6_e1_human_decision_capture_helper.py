from copy import deepcopy
from pathlib import Path
import re
import unittest

from runtime.human_decision_capture_helper import (
    BLOCKED_INVALID_DECISION,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_STALE_OR_MISMATCHED_PACKET,
    CAPTURED_APPROVE,
    CAPTURED_REJECT,
    HumanDecisionCaptureIntent,
    capture_human_decision_intent,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER = REPO_ROOT / "runtime" / "human_decision_capture_helper.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


class M6E1HumanDecisionCaptureHelperTests(unittest.TestCase):
    def test_no_default_approve(self):
        missing = capture_human_decision_intent(
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
        )
        empty = capture_human_decision_intent(
            decision="",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
        )

        self.assertEqual(BLOCKED_INVALID_DECISION, missing.outcome_state)
        self.assertEqual(BLOCKED_INVALID_DECISION, empty.outcome_state)
        self.assertFalse(missing.decision_captured)
        self.assertFalse(empty.decision_captured)

    def test_explicit_approve_only(self):
        result = self.make_result("APPROVE")

        self.assertEqual(CAPTURED_APPROVE, result.outcome_state)
        self.assertEqual("APPROVE", result.decision)
        self.assertTrue(result.decision_captured)
        self.assertFalse(result.is_approval_authority)

    def test_explicit_reject_only(self):
        result = self.make_result("REJECT")

        self.assertEqual(CAPTURED_REJECT, result.outcome_state)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.decision_captured)

    def test_reject_is_first_class_and_blocking(self):
        result = self.make_result("REJECT")

        self.assertEqual(CAPTURED_REJECT, result.outcome_state)
        self.assertTrue(result.blocking)
        self.assertIn("REJECT is blocking", result.messages)

    def test_unknown_decisions_fail_closed(self):
        for decision in ("YES", "OK", "ACCEPT", "TRUE", "CANONICAL", "approve", "deny"):
            with self.subTest(decision=decision):
                result = self.make_result(decision)
                self.assertEqual(BLOCKED_INVALID_DECISION, result.outcome_state)
                self.assertFalse(result.decision_captured)

    def test_missing_or_non_full_packet_hash_fails_closed(self):
        missing = capture_human_decision_intent(decision="APPROVE")
        short = capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash="abc",
            current_packet_hash="abc",
        )

        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, missing.outcome_state)
        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, short.outcome_state)
        self.assertIsNone(missing.capture_id)

    def test_stale_packet_hash_blocks(self):
        result = capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash="a" * 64,
            current_packet_hash="c" * 64,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_PACKET, result.outcome_state)
        self.assertTrue(result.blocking)
        self.assertFalse(result.decision_captured)

    def test_stale_or_incomplete_artifact_hash_blocks_when_present(self):
        mismatch = capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash="b" * 64,
            current_artifact_hash="c" * 64,
        )
        incomplete = capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            current_artifact_hash=ARTIFACT_HASH,
        )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_PACKET, mismatch.outcome_state)
        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_PACKET, incomplete.outcome_state)

    def test_capture_object_is_only_an_inert_intent(self):
        result = self.make_result("APPROVE")

        self.assertIsInstance(result, HumanDecisionCaptureIntent)
        self.assertNotEqual("ApprovalDecision", type(result).__name__)
        self.assertFalse(result.is_approval_authority)
        self.assertIn("capture intent is not approval authority", result.messages)

    def test_capture_alone_does_not_pass_gate_or_write(self):
        result = self.make_result("APPROVE")

        self.assertTrue(result.durable_audit_handoff_required)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertIn("durable audit handoff is still required", result.messages)
        self.assertIn("pre-artifact gate is not passed by capture", result.messages)
        self.assertIn("no artifact write occurred", result.messages)

    def test_helper_does_not_mutate_input_metadata(self):
        metadata = {
            "tags": ["TAG_APPROVED", "CANONICAL"],
            "hats": ["SAFE_FOR_RUNTIME"],
            "tetrads": {"geometry": "approved"},
        }
        before = deepcopy(metadata)

        capture_human_decision_intent(
            decision="APPROVE",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            metadata=metadata,
        )

        self.assertEqual(before, metadata)

    def test_tags_tetrads_hats_and_metadata_cannot_change_capture(self):
        baseline = self.make_result("APPROVE")
        with_metadata = capture_human_decision_intent(
            decision="APPROVE",
            packet_id="packet-1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-1",
            reason="reviewed",
            metadata={
                "tags": ["TAG_APPROVED", "CANONICAL"],
                "hats": ["SAFE_FOR_RUNTIME"],
                "tetrads": ["APPROVED"],
                "geometry": {"safe": True},
            },
        )

        self.assertEqual(baseline.outcome_state, with_metadata.outcome_state)
        self.assertEqual(baseline.capture_id, with_metadata.capture_id)
        self.assertTrue(with_metadata.metadata_ignored)
        self.assertFalse(with_metadata.is_approval_authority)

    def test_capture_id_is_deterministic_and_inspectable(self):
        first = self.make_result("APPROVE")
        second = self.make_result("APPROVE")
        rejected = self.make_result("REJECT")

        self.assertEqual(first.capture_id, second.capture_id)
        self.assertNotEqual(first.capture_id, rejected.capture_id)
        self.assertTrue(first.capture_id.startswith("human-decision-intent-"))

    def test_no_artifact_or_audit_write_apis_or_gate_call(self):
        source = HELPER.read_text(encoding="utf-8")
        forbidden_terms = (
            "evaluate_pre_artifact_approval_gate",
            "append_audit_event_jsonl",
            "write_sandbox_artifact",
            "gated_durable_artifact",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "open(",
        )
        for term in forbidden_terms:
            self.assertNotIn(term, source)

    def test_no_dangerous_imports_or_external_integration_paths(self):
        forbidden_imports = (
            "subprocess",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "requests",
            "httpx",
        )
        for path in (HELPER, THIS_FILE):
            source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(rf"^\s*(from|import)\s+{re.escape(module_name)}\b", source, re.MULTILINE)
                )
            self.assertIsNone(re.search(r"\bos\s*\.\s*system\s*\(", source))

        helper_source = HELPER.read_text(encoding="utf-8").lower()
        forbidden_helper_terms = (
            "pro" + "vider",
            "mo" + "del",
            "g" + "pt",
            "net" + "work",
        )
        for term in forbidden_helper_terms:
            self.assertNotIn(term, helper_source)

    def test_helper_does_not_import_existing_bridge_or_authority_types(self):
        source = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("runtime.schemas.human_decision_capture", source)
        self.assertNotIn("runtime.schemas.approval_decision", source)
        self.assertNotIn("runtime.safety", source)

    def make_result(self, decision: str) -> HumanDecisionCaptureIntent:
        return capture_human_decision_intent(
            decision=decision,
            packet_id="packet-1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-1",
            reason="reviewed",
        )


if __name__ == "__main__":
    unittest.main()
