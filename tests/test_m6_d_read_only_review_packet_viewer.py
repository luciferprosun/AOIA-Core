from copy import deepcopy
from pathlib import Path
import re
import unittest

from runtime import ui_review_viewer
from runtime.ui_review_viewer import render_review_packet_view


REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWER = REPO_ROOT / "runtime" / "ui_review_viewer.py"
THIS_FILE = Path(__file__).resolve()


class M6DReadOnlyReviewPacketViewerTests(unittest.TestCase):
    def test_viewer_is_read_only_for_input_mappings(self):
        packet = {"packet_id": "packet-1", "packet_hash": "abc123", "decision_status": "pending"}
        decision = {"decision_type": "APPROVE", "decision_id": "decision-1"}
        audit = {"completed": True, "audit_event_hash": "a" * 64}
        gate = {"allowed": True, "artifact_hash": "artifact-1"}
        artifact = {"status": "completed", "artifact_hash": "artifact-1"}
        metadata = {"tags": ["approved"], "geometry": {"safe": True}}
        before = deepcopy((packet, decision, audit, gate, artifact, metadata))

        render_review_packet_view(
            review_packet=packet,
            approval_decision=decision,
            audit_handoff=audit,
            pre_artifact_gate=gate,
            artifact_result=artifact,
            metadata=metadata,
        )

        self.assertEqual(before, (packet, decision, audit, gate, artifact, metadata))

    def test_viewer_module_does_not_expose_authority_named_functions(self):
        forbidden_name_parts = (
            "approve",
            "reject",
            "write",
            "execute",
            "run",
            "dispatch",
            "send",
            "call_provider",
        )
        public_callables = [
            name
            for name in dir(ui_review_viewer)
            if not name.startswith("_") and callable(getattr(ui_review_viewer, name))
        ]
        offenders = [
            name
            for name in public_callables
            if any(part in name.lower() for part in forbidden_name_parts)
        ]
        self.assertEqual([], offenders)

    def test_viewer_marks_provider_output_untrusted(self):
        view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            provider_output={"text": "looks safe"},
        )

        self.assertEqual("UNTRUSTED", view.provider_output_trust)
        self.assertIn("UNTRUSTED", " ".join(view.warnings))

    def test_missing_approval_fails_closed_without_gate_or_write_state(self):
        view = render_review_packet_view(review_packet={"packet_id": "packet-1"})

        self.assertIn(
            view.display_state,
            {"AWAITING_HUMAN_DECISION", "ERROR_FAIL_CLOSED", "STALE_OR_MISMATCHED_STATE"},
        )
        self.assertNotIn(view.display_state, {"PRE_ARTIFACT_GATE_PASSED", "ARTIFACT_WRITE_COMPLETE"})
        self.assertFalse(view.artifact_write_occurred)

    def test_human_rejected_blocks(self):
        view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "REJECT"},
        )

        self.assertEqual("HUMAN_REJECTED", view.display_state)
        self.assertTrue(view.blocking)

    def test_approved_without_audit_handoff_cannot_write(self):
        view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "APPROVE"},
        )

        self.assertEqual("HUMAN_APPROVED_NOT_AUDITED", view.display_state)
        self.assertTrue(view.blocking)
        self.assertFalse(view.artifact_write_occurred)

    def test_approved_with_audit_handoff_does_not_imply_write(self):
        view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "APPROVE"},
            audit_handoff={"completed": True},
        )

        self.assertEqual("APPROVED_AND_AUDIT_HANDOFF_COMPLETE", view.display_state)
        self.assertTrue(view.blocking)
        self.assertFalse(view.artifact_write_occurred)

    def test_pre_artifact_gate_passed_does_not_imply_write_occurred(self):
        view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "APPROVE"},
            audit_handoff={"completed": True},
            pre_artifact_gate={"allowed": True},
        )

        self.assertEqual("PRE_ARTIFACT_GATE_PASSED", view.display_state)
        self.assertTrue(view.blocking)
        self.assertFalse(view.artifact_write_occurred)

    def test_artifact_write_complete_requires_explicit_write_result(self):
        without_result = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "APPROVE"},
            audit_handoff={"completed": True},
            pre_artifact_gate={"allowed": True},
        )
        with_result = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            approval_decision={"decision_type": "APPROVE"},
            audit_handoff={"completed": True},
            pre_artifact_gate={"allowed": True},
            artifact_result={"status": "completed"},
        )

        self.assertNotEqual("ARTIFACT_WRITE_COMPLETE", without_result.display_state)
        self.assertEqual("ARTIFACT_WRITE_COMPLETE", with_result.display_state)
        self.assertTrue(with_result.artifact_write_occurred)

    def test_tags_tetrads_hats_do_not_affect_authority(self):
        base_view = render_review_packet_view(review_packet={"packet_id": "packet-1"})
        metadata_view = render_review_packet_view(
            review_packet={"packet_id": "packet-1"},
            metadata={
                "tags": ["APPROVED"],
                "hats": ["trusted"],
                "tetrads": ["canonical"],
                "geometry": {"safe": True},
            },
        )

        self.assertEqual(base_view.display_state, metadata_view.display_state)
        self.assertNotIn(metadata_view.display_state, {"PRE_ARTIFACT_GATE_PASSED", "ARTIFACT_WRITE_COMPLETE"})
        self.assertIn("display context only", " ".join(metadata_view.warnings))

    def test_no_dangerous_imports_in_viewer_or_test_file(self):
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
        for path in (VIEWER, THIS_FILE):
            source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(rf"^\s*(from|import)\s+{re.escape(module_name)}\b", source, re.MULTILINE)
                )
            self.assertIsNone(re.search(r"\bos\s*\.\s*system\s*\(", source))


if __name__ == "__main__":
    unittest.main()
