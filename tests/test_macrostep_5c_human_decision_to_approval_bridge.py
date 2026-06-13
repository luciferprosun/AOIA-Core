from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
)
from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import (
    HumanDecisionCapture,
    capture_human_decision,
    hash_human_approval_review_packet,
)
from runtime.safety import (
    audit_event_logger,
    dry_run_artifact_integration,
    local_agent_entrypoint,
    sandbox_artifact_runner,
)
from runtime.safety.human_decision_to_approval_policy import (
    create_approval_decision_from_human_capture,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "human_decision_to_approval_policy.py"


class Macrostep5CHumanDecisionToApprovalBridgeTests(unittest.TestCase):
    def test_bridge_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(create_approval_decision_from_human_capture))

    def test_bridge_consumes_valid_review_packet_and_decision_capture(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet, decision="approve")

        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )

        self.assertIsInstance(decision, ApprovalDecision)
        self.assertEqual(decision.decision_type, ApprovalDecisionType.APPROVE)
        self.assertEqual(decision.decision_state, ApprovalDecisionState.RECORDED)

    def test_bridge_rejects_conversion_without_decision_capture(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(
                review_packet=self.make_packet(),
                decision_capture=None,  # type: ignore[arg-type]
            )

    def test_bridge_creates_decision_only_through_explicit_helper_call(self) -> None:
        packet = self.make_packet()

        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(  # type: ignore[call-arg]
                review_packet=packet,
            )

    def test_bridge_supports_approve_capture(self) -> None:
        packet = self.make_packet()
        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=self.make_capture(packet=packet, decision="approve"),
        )

        self.assertEqual(decision.decision_type, ApprovalDecisionType.APPROVE)
        self.assertTrue(decision.human_reviewed)
        self.assertEqual(decision.actor_type, ApprovalActorType.HUMAN_REVIEWER)

    def test_bridge_supports_deny_capture_as_reject(self) -> None:
        packet = self.make_packet()
        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=self.make_capture(packet=packet, decision="deny"),
        )

        self.assertEqual(decision.decision_type, ApprovalDecisionType.REJECT)
        self.assertNotEqual(decision.decision_type, ApprovalDecisionType.APPROVE)
        self.assertFalse(decision.execution_permitted)
        self.assertFalse(decision.execution_triggered)

    def test_bridge_binds_decision_to_review_packet_and_capture_metadata(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet, decision="approve")

        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )

        self.assertEqual(decision.proposal_id, packet.proposal_id)
        self.assertEqual(decision.reviewed_exact_payload_hash, capture.review_packet_hash)
        self.assertIn(packet.packet_id, decision.notes)
        self.assertIn(hash_human_approval_review_packet(packet), decision.notes)
        self.assertIn(capture.decision_id, decision.notes)
        self.assertIn(capture.decision_hash, decision.notes)

    def test_bridge_preserves_reviewer_and_reason(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet, decision="approve", reviewer_id="human-reviewer-5")

        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )

        self.assertEqual(decision.actor_id, "human-reviewer-5")
        self.assertEqual(decision.reason, "Reviewed the packet.")

    def test_bridge_returns_deterministic_result_for_deterministic_inputs(self) -> None:
        packet = self.make_packet()
        first_capture = self.make_capture(packet=packet, decision="approve")
        second_capture = self.make_capture(packet=packet, decision="approve")

        first = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=first_capture,
        )
        second = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=second_capture,
        )

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertTrue(first.decision_id.startswith("approval-decision-from-human-capture-"))

    def test_bridge_does_not_write_or_call_agent_paths(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet, decision="approve")

        with TemporaryDirectory() as tmpdir:
            before = self.snapshot(tmpdir)
            with patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("bridge must not append audit logs"),
            ), patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("bridge must not write artifacts"),
            ), patch.object(
                local_agent_entrypoint,
                "run_durable_local_agent_entrypoint",
                side_effect=AssertionError("bridge must not run local entrypoint"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("bridge must not call old non-durable path"),
            ):
                create_approval_decision_from_human_capture(
                    review_packet=packet,
                    decision_capture=capture,
                )
            after = self.snapshot(tmpdir)

        self.assertEqual(before, after)

    def test_bridge_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_file_does_not_call_forbidden_capabilities()

    def make_packet(self):
        return create_human_approval_review_packet(
            goal="Create a safe approval bridge.",
            proposal_id="proposal-decision-bridge-1",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="decision_bridge_run",
            artifact_relative_path="decision-bridge.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="unit-test",
        )

    def make_capture(
        self,
        *,
        packet,
        decision: str,
        reviewer_id: str = "reviewer-1",
    ) -> HumanDecisionCapture:
        return capture_human_decision(
            review_packet=packet,
            decision=decision,
            reviewer_id=reviewer_id,
            captured_at="2026-06-13T17:41:00Z",
            reason="Reviewed the packet.",
        )

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))

    def assert_runtime_file_does_not_call_forbidden_capabilities(self) -> None:
        forbidden_modules = {
            "subprocess",
            "pty",
            "pexpect",
            "requests",
            "urllib",
            "http.client",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "google.cloud",
            "google.generativeai",
            "dotenv",
            "sqlite3",
            "shutil",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "safe_file_writer",
            "workspace_registry",
            "append_audit_event_jsonl(",
            "write_sandbox_artifact(",
            "run_durable_local_agent_entrypoint(",
            "run_dry_run_agent_and_write_artifact(",
            "input(",
            "readline(",
            "mkdir(",
            "write_text(",
            "open(",
        )
        source = BRIDGE_RUNTIME_FILE.read_text(encoding="utf-8")
        for term in forbidden_text:
            self.assertNotIn(term, source)
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            self.assertNotIn(module_name, forbidden_modules)
            self.assertFalse(any(module_name == item or module_name.startswith(item + ".") for item in forbidden_modules))


if __name__ == "__main__":
    unittest.main()
