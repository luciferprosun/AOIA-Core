from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest

from runtime.safety.approval_gate import evaluate_approval
from runtime.safety.bash_parser import parse_bash_command
from runtime.schemas.approval_audit_event import (
    APPROVAL_AUDIT_EVENT_TYPE,
    ApprovalAuditEvent,
    from_proposal_and_decision,
)
from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.command_proposal import CommandProposal


class InertMiniStackIntegrationTests(unittest.TestCase):
    def _audit_command(
        self,
        command: str,
        *,
        event_id: str,
    ) -> tuple[CommandProposal, ApprovalDecision, ApprovalAuditEvent]:
        proposal = parse_bash_command(command, source="gt-runtime-8g-test")
        decision = evaluate_approval(proposal)
        event = from_proposal_and_decision(
            proposal,
            decision,
            event_id=event_id,
            created_at_utc="2026-06-03T00:00:00Z",
        )
        return proposal, decision, event

    def _assert_common_inert_boundary(
        self,
        proposal: CommandProposal,
        decision: ApprovalDecision,
        event: ApprovalAuditEvent,
    ) -> None:
        self.assertIsInstance(proposal, CommandProposal)
        self.assertIsInstance(decision, ApprovalDecision)
        self.assertIsInstance(event, ApprovalAuditEvent)
        self.assertTrue(proposal.dry_run)
        self.assertFalse(decision.execution_permitted)
        self.assertFalse(event.execution_permitted)
        self.assertEqual(event.event_type, APPROVAL_AUDIT_EVENT_TYPE)
        self.assertEqual(event.raw_command, proposal.raw_command)
        self.assertEqual(event.normalized_command, proposal.normalized_command)
        self.assertEqual(event.classification, proposal.classification)
        self.assertEqual(event.proposal_approval_state, proposal.approval_state)
        self.assertEqual(event.decision_approval_state, decision.approval_state)
        self.assertEqual(event.decision_allowed, decision.allowed)
        self.assertEqual(event.dry_run, proposal.dry_run)
        self.assertEqual(event.dry_run, decision.dry_run)
        self.assertEqual(event.requires_human_review, decision.requires_human_review)
        self.assertEqual(event.proposal_reason, proposal.reason)
        self.assertEqual(event.decision_reason, decision.reason)

    def test_safe_command_flows_through_dry_run_audit_event(self) -> None:
        proposal, decision, event = self._audit_command(
            "ls -la",
            event_id="gt-runtime-8g-safe",
        )

        self._assert_common_inert_boundary(proposal, decision, event)
        self.assertEqual(proposal.classification, "safe")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_human_review)
        self.assertTrue(event.decision_allowed)
        self.assertFalse(event.requires_human_review)
        with self.assertRaises(FrozenInstanceError):
            event.decision_allowed = False

    def test_dangerous_command_requires_review_and_never_permits_execution(self) -> None:
        proposal, decision, event = self._audit_command(
            "rm -rf /",
            event_id="gt-runtime-8g-dangerous",
        )

        self._assert_common_inert_boundary(proposal, decision, event)
        self.assertEqual(proposal.classification, "dangerous")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(event.decision_allowed)
        self.assertTrue(event.requires_human_review)

    def test_ambiguous_command_requires_review_and_never_permits_execution(self) -> None:
        proposal, decision, event = self._audit_command(
            "echo $(whoami)",
            event_id="gt-runtime-8g-ambiguous",
        )

        self._assert_common_inert_boundary(proposal, decision, event)
        self.assertIn(proposal.classification, {"ambiguous", "dangerous", "unknown"})
        self.assertNotEqual(proposal.classification, "safe")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(event.decision_allowed)
        self.assertTrue(event.requires_human_review)

    def test_unknown_parse_error_requires_review_and_never_permits_execution(self) -> None:
        proposal, decision, event = self._audit_command(
            'echo "unterminated',
            event_id="gt-runtime-8g-unknown",
        )

        self._assert_common_inert_boundary(proposal, decision, event)
        self.assertEqual(proposal.classification, "unknown")
        self.assertIn("tokenization failed", proposal.reason)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_human_review)
        self.assertFalse(event.decision_allowed)
        self.assertTrue(event.requires_human_review)

    def test_raw_string_cannot_reach_approval_gate(self) -> None:
        with self.assertRaises(TypeError):
            evaluate_approval("ls -la")  # type: ignore[arg-type]

    def test_execution_lock_cannot_be_flipped(self) -> None:
        with self.assertRaises(ValueError):
            ApprovalDecision(
                allowed=True,
                approval_state="not_required",
                reason="invalid execution attempt",
                dry_run=True,
                requires_human_review=False,
                execution_permitted=True,
            )
        with self.assertRaises(ValueError):
            ApprovalAuditEvent(
                event_id="gt-runtime-8g-invalid-event",
                event_type=APPROVAL_AUDIT_EVENT_TYPE,
                created_at_utc="2026-06-03T00:00:00Z",
                source="gt-runtime-8g-test",
                raw_command="ls -la",
                normalized_command="ls -la",
                classification="safe",
                proposal_approval_state="not_required",
                decision_approval_state="not_required",
                decision_allowed=True,
                execution_permitted=True,
                dry_run=True,
                requires_human_review=False,
                proposal_reason="recognized read-only command shape",
                decision_reason="safe proposal may pass only as a dry-run decision",
            )
        proposal, decision, _event = self._audit_command(
            "ls -la",
            event_id="gt-runtime-8g-frozen-decision",
        )
        self.assertFalse(proposal.requires_human_approval)
        with self.assertRaises(FrozenInstanceError):
            decision.execution_permitted = True

    def test_source_contains_no_forbidden_runtime_imports_or_execution_calls(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        forbidden_fragments = (
            "sub" + "process",
            "os" + ".system",
            "shell" + "=" + "True",
            "P" + "open",
            "ev" + "al(",
            "ex" + "ec(",
            "event" + "_ledger",
            "shell" + "_tools",
            "ex" + "ecutor",
            "pro" + "viders",
            "rou" + "ting",
        )
        for forbidden in forbidden_fragments:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
