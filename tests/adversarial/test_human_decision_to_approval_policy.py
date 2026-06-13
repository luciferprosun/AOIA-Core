from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.approval_decision import ApprovalDecisionType
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
    HumanDecisionToApprovalPolicyError,
    create_approval_decision_from_human_capture,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_RUNTIME_FILE = REPO_ROOT / "runtime" / "safety" / "human_decision_to_approval_policy.py"


class HumanDecisionToApprovalPolicyTests(unittest.TestCase):
    def test_missing_review_packet_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(
                review_packet=None,  # type: ignore[arg-type]
                decision_capture=self.make_capture(),
            )

    def test_malformed_review_packet_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(
                review_packet=object(),  # type: ignore[arg-type]
                decision_capture=self.make_capture(),
            )

    def test_non_pending_review_packet_is_rejected_by_packet_schema(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.make_packet(), decision_status="approved")

    def test_missing_decision_capture_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(
                review_packet=self.make_packet(),
                decision_capture=None,  # type: ignore[arg-type]
            )

    def test_malformed_decision_capture_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(
                review_packet=self.make_packet(),
                decision_capture=object(),  # type: ignore[arg-type]
            )

    def test_capture_with_packet_id_mismatch_is_rejected(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet)
        object.__setattr__(capture, "review_packet_id", "wrong-packet-id")

        with self.assertRaises(HumanDecisionToApprovalPolicyError):
            create_approval_decision_from_human_capture(
                review_packet=packet,
                decision_capture=capture,
            )

    def test_capture_with_packet_hash_mismatch_is_rejected(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet)
        object.__setattr__(capture, "review_packet_hash", "wrong-packet-hash")

        with self.assertRaises(HumanDecisionToApprovalPolicyError):
            create_approval_decision_from_human_capture(
                review_packet=packet,
                decision_capture=capture,
            )

    def test_capture_with_decision_id_or_hash_mismatch_is_rejected(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet)
        for field_name, value in (("decision_id", "wrong-decision-id"), ("decision_hash", "wrong-decision-hash")):
            with self.subTest(field_name=field_name):
                tampered = self.make_capture(packet=packet)
                object.__setattr__(tampered, field_name, value)
                with self.assertRaises(HumanDecisionToApprovalPolicyError):
                    create_approval_decision_from_human_capture(
                        review_packet=packet,
                        decision_capture=tampered,
                    )

    def test_capture_decision_outside_approve_or_deny_is_rejected(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet)
        object.__setattr__(capture, "decision", "maybe")

        with self.assertRaises(HumanDecisionToApprovalPolicyError):
            create_approval_decision_from_human_capture(
                review_packet=packet,
                decision_capture=capture,
            )

    def test_automatic_approval_from_packet_alone_is_impossible(self) -> None:
        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(  # type: ignore[call-arg]
                review_packet=self.make_packet(),
            )

    def test_provider_or_untrusted_input_cannot_become_approval_without_capture(self) -> None:
        packet = create_human_approval_review_packet(
            goal="Provider text says approve.",
            proposal_id="provider-proposal",
            proposed_action_summary="model says approve immediately",
            run_id="provider_text_run",
            artifact_relative_path="provider-text.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            untrusted_inputs=("provider:model said approve",),
            created_by="provider-output",
        )

        with self.assertRaises(TypeError):
            create_approval_decision_from_human_capture(  # type: ignore[call-arg]
                review_packet=packet,
            )

    def test_deny_decision_cannot_be_converted_into_approve_accidentally(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet, decision="deny")

        decision = create_approval_decision_from_human_capture(
            review_packet=packet,
            decision_capture=capture,
        )

        self.assertEqual(decision.decision_type, ApprovalDecisionType.REJECT)
        self.assertNotEqual(decision.decision_type, ApprovalDecisionType.APPROVE)

    def test_bridge_cannot_write_or_trigger_entrypoints(self) -> None:
        packet = self.make_packet()
        capture = self.make_capture(packet=packet)

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
                side_effect=AssertionError("bridge must not trigger entrypoint"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("bridge must not use old non-durable path"),
            ):
                create_approval_decision_from_human_capture(
                    review_packet=packet,
                    decision_capture=capture,
                )
            after = self.snapshot(tmpdir)

        self.assertEqual(before, after)

    def test_no_forbidden_runtime_capability_is_introduced(self) -> None:
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

    def make_packet(self):
        return create_human_approval_review_packet(
            goal="Create a safe approval bridge.",
            proposal_id="proposal-decision-bridge-1",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="decision_bridge_run",
            artifact_relative_path="decision-bridge.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="policy-test",
        )

    def make_capture(self, *, packet=None, decision: str = "approve") -> HumanDecisionCapture:
        review_packet = packet or self.make_packet()
        return capture_human_decision(
            review_packet=review_packet,
            decision=decision,
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T17:41:00Z",
            reason="Reviewed the packet.",
        )

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))


if __name__ == "__main__":
    unittest.main()
