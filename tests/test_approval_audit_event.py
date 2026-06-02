from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.schemas.approval_audit_event import (
    APPROVAL_AUDIT_EVENT_TYPE,
    ApprovalAuditEvent,
    from_proposal_and_decision,
)
from runtime.schemas.approval_decision import ApprovalDecision
from runtime.schemas.command_proposal import CommandProposal


class ApprovalAuditEventTests(unittest.TestCase):
    def make_proposal(
        self,
        *,
        command: str = "ls -la",
        classification: str = "safe",
        approval_state: str | None = None,
        reason: str = "proposal reason",
    ) -> CommandProposal:
        return CommandProposal(
            raw_command=command,
            normalized_command=" ".join(command.split()),
            tokens=tuple(command.split()),
            classification=classification,
            approval_state=approval_state,
            reason=reason,
            source="unit_test",
            created_by="tests.test_approval_audit_event",
            dry_run=True,
        )

    def make_decision(
        self,
        *,
        allowed: bool = True,
        approval_state: str = "not_required",
        reason: str = "decision reason",
        dry_run: bool = True,
        requires_human_review: bool = False,
    ) -> ApprovalDecision:
        return ApprovalDecision(
            allowed=allowed,
            approval_state=approval_state,
            reason=reason,
            dry_run=dry_run,
            requires_human_review=requires_human_review,
        )

    def test_valid_event_can_be_constructed(self) -> None:
        event = ApprovalAuditEvent(
            event_id="event-001",
            event_type=APPROVAL_AUDIT_EVENT_TYPE,
            created_at_utc="2026-06-02T21:13:00Z",
            source="unit_test",
            raw_command="ls -la",
            normalized_command="ls -la",
            classification="safe",
            proposal_approval_state="not_required",
            decision_approval_state="not_required",
            decision_allowed=True,
            execution_permitted=False,
            dry_run=True,
            requires_human_review=False,
            proposal_reason="proposal reason",
            decision_reason="decision reason",
        )
        self.assertEqual(event.event_type, "approval_decision_dry_run")
        self.assertFalse(event.execution_permitted)

    def test_event_is_frozen(self) -> None:
        event = from_proposal_and_decision(
            self.make_proposal(),
            self.make_decision(),
            event_id="event-002",
            created_at_utc="2026-06-02T21:14:00Z",
        )
        with self.assertRaises(FrozenInstanceError):
            event.event_id = "changed"

    def test_execution_permitted_true_raises(self) -> None:
        with self.assertRaises(ValueError):
            ApprovalAuditEvent(
                event_id="event-003",
                event_type=APPROVAL_AUDIT_EVENT_TYPE,
                created_at_utc="2026-06-02T21:15:00Z",
                source="unit_test",
                raw_command="ls -la",
                normalized_command="ls -la",
                classification="safe",
                proposal_approval_state="not_required",
                decision_approval_state="not_required",
                decision_allowed=True,
                execution_permitted=True,
                dry_run=True,
                requires_human_review=False,
                proposal_reason="proposal reason",
                decision_reason="decision reason",
            )

    def test_invalid_event_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            ApprovalAuditEvent(
                event_id="event-004",
                event_type="wrong_type",
                created_at_utc="2026-06-02T21:16:00Z",
                source="unit_test",
                raw_command="ls -la",
                normalized_command="ls -la",
                classification="safe",
                proposal_approval_state="not_required",
                decision_approval_state="not_required",
                decision_allowed=True,
                execution_permitted=False,
                dry_run=True,
                requires_human_review=False,
                proposal_reason="proposal reason",
                decision_reason="decision reason",
            )

    def test_empty_event_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            ApprovalAuditEvent(
                event_id="",
                event_type=APPROVAL_AUDIT_EVENT_TYPE,
                created_at_utc="2026-06-02T21:17:00Z",
                source="unit_test",
                raw_command="ls -la",
                normalized_command="ls -la",
                classification="safe",
                proposal_approval_state="not_required",
                decision_approval_state="not_required",
                decision_allowed=True,
                execution_permitted=False,
                dry_run=True,
                requires_human_review=False,
                proposal_reason="proposal reason",
                decision_reason="decision reason",
            )

    def test_from_proposal_and_decision_safe_event_fields(self) -> None:
        proposal = self.make_proposal(
            command="ls -la",
            classification="safe",
            approval_state="not_required",
            reason="recognized read-only command shape",
        )
        decision = self.make_decision(
            allowed=True,
            approval_state="not_required",
            reason="safe proposal may pass only as a dry-run decision",
        )
        event = from_proposal_and_decision(
            proposal,
            decision,
            event_id="event-005",
            created_at_utc="2026-06-02T21:18:00Z",
        )
        self.assertEqual(event.raw_command, "ls -la")
        self.assertEqual(event.normalized_command, "ls -la")
        self.assertEqual(event.classification, "safe")
        self.assertEqual(event.proposal_approval_state, "not_required")
        self.assertEqual(event.decision_approval_state, "not_required")
        self.assertTrue(event.decision_allowed)
        self.assertTrue(event.dry_run)
        self.assertFalse(event.requires_human_review)
        self.assertFalse(event.execution_permitted)
        self.assertEqual(event.proposal_reason, "recognized read-only command shape")
        self.assertEqual(
            event.decision_reason,
            "safe proposal may pass only as a dry-run decision",
        )

    def test_from_proposal_and_decision_review_event_fields(self) -> None:
        proposal = self.make_proposal(
            command="rm -rf /",
            classification="dangerous",
            approval_state="requires_human_review",
            reason="recursive root removal pattern detected",
        )
        decision = self.make_decision(
            allowed=False,
            approval_state="requires_human_review",
            reason="dangerous proposals require human review",
            requires_human_review=True,
        )
        event = from_proposal_and_decision(
            proposal,
            decision,
            event_id="event-006",
            created_at_utc="2026-06-02T21:19:00Z",
        )
        self.assertEqual(event.raw_command, "rm -rf /")
        self.assertEqual(event.classification, "dangerous")
        self.assertEqual(event.proposal_approval_state, "requires_human_review")
        self.assertEqual(event.decision_approval_state, "requires_human_review")
        self.assertFalse(event.decision_allowed)
        self.assertTrue(event.requires_human_review)
        self.assertFalse(event.execution_permitted)

    def test_from_proposal_and_decision_rejects_wrong_proposal_type(self) -> None:
        with self.assertRaises(TypeError):
            from_proposal_and_decision(
                {},
                self.make_decision(),
                event_id="event-007",
                created_at_utc="2026-06-02T21:20:00Z",
            )

    def test_from_proposal_and_decision_rejects_wrong_decision_type(self) -> None:
        with self.assertRaises(TypeError):
            from_proposal_and_decision(
                self.make_proposal(),
                {},
                event_id="event-008",
                created_at_utc="2026-06-02T21:21:00Z",
            )

    def test_from_proposal_and_decision_does_not_mutate_inputs(self) -> None:
        proposal = self.make_proposal()
        decision = self.make_decision()
        proposal_before = proposal.to_dict()
        decision_before = decision
        from_proposal_and_decision(
            proposal,
            decision,
            event_id="event-009",
            created_at_utc="2026-06-02T21:22:00Z",
        )
        self.assertEqual(proposal_before, proposal.to_dict())
        self.assertEqual(decision_before, decision)

    def test_source_has_no_forbidden_execution_or_io_patterns(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "runtime"
            / "schemas"
            / "approval_audit_event.py"
        ).read_text(encoding="utf-8")
        for needle in (
            "subprocess",
            "os.system",
            "shell=True",
            "eval(",
            "exec(",
            "open(",
            "pathlib",
            "requests",
            "socket",
            "importlib",
            "runtime.tools.event_ledger",
        ):
            self.assertNotIn(needle, source)


if __name__ == "__main__":
    unittest.main()
