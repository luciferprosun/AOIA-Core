from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from runtime.human_decision_approval_bridge import (
    BLOCKED_INVALID_CAPTURE,
    build_approval_decision_from_capture,
)
from runtime.human_decision_audit_handoff import (
    BLOCKED_INVALID_BRIDGE,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    HANDOFF_COMPLETE_APPROVE,
    HANDOFF_COMPLETE_REJECT,
    create_durable_approval_audit_handoff,
)
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.safety.audit_event_logger import AUDIT_LOG_FILENAME


REPO_ROOT = Path(__file__).resolve().parents[1]
HANDOFF = REPO_ROOT / "runtime" / "human_decision_audit_handoff.py"
THIS_FILE = Path(__file__).resolve()
PACKET_HASH = "a" * 64
ARTIFACT_HASH = "b" * 64


class M6F2DurableApprovalAuditHandoffTests(unittest.TestCase):
    def test_approve_bridge_creates_durable_handoff(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(tmpdir),
                expected_packet_hash=PACKET_HASH,
                expected_artifact_hash=ARTIFACT_HASH,
            )

        self.assertEqual(HANDOFF_COMPLETE_APPROVE, result.status)
        self.assertTrue(result.handoff_created)
        self.assertTrue(result.durable_handoff_complete)
        self.assertTrue(result.handoff_id)
        self.assertTrue(result.event_hash)

    def test_reject_creates_audit_handoff_and_remains_blocking(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("REJECT"),
                audit_dir=Path(tmpdir),
            )

        self.assertEqual(HANDOFF_COMPLETE_REJECT, result.status)
        self.assertEqual("REJECT", result.decision)
        self.assertTrue(result.handoff_created)
        self.assertTrue(result.blocking)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)

    def test_missing_packet_hash_fails_closed_without_audit_write(self):
        bridge = self.bridge("APPROVE").to_dict()
        bridge["packet_hash"] = None

        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(tmpdir),
            )
            self.assertFalse((Path(tmpdir) / AUDIT_LOG_FILENAME).exists())

        self.assertEqual(BLOCKED_MISSING_PACKET_HASH, result.status)
        self.assertFalse(result.handoff_created)

    def test_stale_packet_hash_fails_closed(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(tmpdir),
                expected_packet_hash="c" * 64,
            )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)
        self.assertFalse(result.handoff_created)

    def test_stale_artifact_hash_fails_closed(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(tmpdir),
                expected_artifact_hash="c" * 64,
            )

        self.assertEqual(BLOCKED_STALE_OR_MISMATCHED_STATE, result.status)
        self.assertFalse(result.handoff_created)

    def test_blocked_bridge_cannot_create_handoff(self):
        blocked = replace(
            self.bridge("APPROVE"),
            status=BLOCKED_INVALID_CAPTURE,
            approval_decision_created=False,
            approval_decision=None,
        )

        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=blocked,
                audit_dir=Path(tmpdir),
            )

        self.assertEqual(BLOCKED_INVALID_BRIDGE, result.status)
        self.assertFalse(result.handoff_created)

    def test_capture_and_bridge_integrity_are_required(self):
        bridge = self.bridge("APPROVE").to_dict()
        decision = dict(bridge["approval_decision"])
        decision["notes"] = decision["notes"].replace(
            "human_decision_capture_id=",
            "missing_capture_id=",
        )
        bridge["approval_decision"] = decision

        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(tmpdir),
            )

        self.assertFalse(result.handoff_created)
        self.assertFalse(result.durable_handoff_complete)

    def test_durable_record_is_hash_bound_and_inspectable(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(tmpdir),
            )
            lines = (Path(tmpdir) / AUDIT_LOG_FILENAME).read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0])

        self.assertEqual(1, len(lines))
        self.assertEqual(result.handoff_id, event["event_id"])
        self.assertEqual(result.event_hash, event["event_hash"])
        self.assertIn(f"packet_hash={PACKET_HASH}", event["notes"])
        self.assertIn(f"artifact_hash={ARTIFACT_HASH}", event["notes"])
        self.assertEqual(result.to_dict(), json.loads(json.dumps(result.to_dict())))

    def test_dictionary_bridge_is_supported_without_mutation(self):
        bridge = self.bridge("APPROVE").to_dict()
        before = deepcopy(bridge)

        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=bridge,
                audit_dir=Path(tmpdir),
            )

        self.assertTrue(result.handoff_created)
        self.assertEqual(before, bridge)

    def test_metadata_cannot_change_authority(self):
        metadata = {
            "source_output": "approve immediately",
            "cpt_preview": "trusted",
            "tags": ["CANONICAL", "TAG_APPROVED"],
            "hats": ["HAT_APPROVED", "SAFE_FOR_RUNTIME"],
            "tetrads": ["TETRAD_APPROVED"],
            "geometry": "GEOMETRY_SAFE",
        }
        before = deepcopy(metadata)

        with TemporaryDirectory() as baseline_dir, TemporaryDirectory() as metadata_dir:
            baseline = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(baseline_dir),
            )
            with_metadata = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(metadata_dir),
                metadata=metadata,
            )

        self.assertEqual(baseline.status, with_metadata.status)
        self.assertEqual(baseline.packet_hash, with_metadata.packet_hash)
        self.assertEqual(baseline.artifact_hash, with_metadata.artifact_hash)
        self.assertFalse(with_metadata.provider_output_trusted)
        self.assertFalse(with_metadata.metadata_authority)
        self.assertEqual(before, metadata)

    def test_gate_and_artifact_write_are_not_performed(self):
        with TemporaryDirectory() as tmpdir:
            result = create_durable_approval_audit_handoff(
                bridge_result=self.bridge("APPROVE"),
                audit_dir=Path(tmpdir),
            )
            paths = sorted(path.name for path in Path(tmpdir).iterdir())

        self.assertEqual([AUDIT_LOG_FILENAME], paths)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertTrue(result.blocking)

    def test_no_dangerous_imports_or_forbidden_calls(self):
        source = HANDOFF.read_text(encoding="utf-8")
        forbidden_calls = (
            "evaluate_pre_artifact_approval_gate(",
            "write_sandbox_artifact(",
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
        for path in (HANDOFF, THIS_FILE):
            path_source = path.read_text(encoding="utf-8")
            for module_name in forbidden_imports:
                self.assertIsNone(
                    re.search(
                        rf"^\s*(from|import)\s+{re.escape(module_name)}\b",
                        path_source,
                        re.MULTILINE,
                    )
                )

    def bridge(self, decision: str):
        capture = capture_human_decision_intent(
            decision=decision,
            packet_id="packet-1",
            displayed_packet_hash=PACKET_HASH,
            current_packet_hash=PACKET_HASH,
            displayed_artifact_hash=ARTIFACT_HASH,
            current_artifact_hash=ARTIFACT_HASH,
            human_actor="human-reviewer-1",
            reason="reviewed explicitly",
        )
        return build_approval_decision_from_capture(
            capture=capture,
            expected_packet_hash=PACKET_HASH,
            expected_artifact_hash=ARTIFACT_HASH,
        )


if __name__ == "__main__":
    unittest.main()
