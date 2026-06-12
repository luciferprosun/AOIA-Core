from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.safety.action_proposal_policy import (
    ActionProposalExecutionBlockedError,
    assert_action_proposal_cannot_execute,
)
from runtime.safety.approval_decision_policy import (
    ApprovalDoesNotExecuteError,
    ApprovalTimeoutBlockedError,
    ProviderApprovalBlockedError,
    assert_approval_decision_does_not_execute,
    assert_timeout_does_not_approve,
)
from runtime.safety.audit_event_policy import (
    append_audit_event_in_memory,
    assert_append_only_chain,
    assert_audit_event_hash_valid,
)
from runtime.safety.proposal_decision_audit_bridge import (
    BRIDGE_STATUS_DECISION_RECORDED,
    BRIDGE_STATUS_EXECUTION_BLOCKED_RECORDED,
    BRIDGE_STATUS_POLICY_BLOCK_RECORDED,
    BRIDGE_STATUS_PROPOSAL_RECORDED,
    ProposalDecisionAuditResult,
    assert_bridge_does_not_execute,
    proposal_decision_audit_result_to_dict,
    record_decision_with_audit,
    record_execution_blocked_with_audit,
    record_policy_block_with_audit,
    record_proposal_with_audit,
)
from runtime.schemas.action_proposal import create_human_review_only_proposal
from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
    create_human_approval_decision,
)
from runtime.schemas.audit_event import AuditEventSeverity, AuditEventType


REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_BRIDGE_FILE = REPO_ROOT / "runtime" / "safety" / "proposal_decision_audit_bridge.py"


class M5BProposalDecisionAuditBridgeTests(unittest.TestCase):
    def make_proposal(self):
        return create_human_review_only_proposal(
            title="Review proposed action",
            description="Structured review only.",
            proposed_by="unit-test",
            payload_summary="payload summary",
            exact_payload='{"action":"review-only","value":1}',
            proposal_id="proposal-m5-b",
        )

    def make_decision(self):
        return create_human_approval_decision(
            self.make_proposal(),
            "reviewer-1",
            "human approved for audit only",
        )

    def test_proposal_can_be_recorded_with_audit_event(self) -> None:
        result, events = record_proposal_with_audit(self.make_proposal())

        self.assertIsInstance(result, ProposalDecisionAuditResult)
        self.assertEqual(result.bridge_status, BRIDGE_STATUS_PROPOSAL_RECORDED)
        self.assertEqual(events[-1].event_type, AuditEventType.ACTION_PROPOSAL_CREATED)
        self.assertEqual(result.audit_event_id, events[-1].event_id)

    def test_decision_can_be_recorded_with_audit_event(self) -> None:
        proposal = self.make_proposal()
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")
        proposal_result, events = record_proposal_with_audit(proposal)

        result, updated = record_decision_with_audit(proposal, decision, events)

        self.assertEqual(proposal_result.audit_chain_length, 1)
        self.assertEqual(result.bridge_status, BRIDGE_STATUS_DECISION_RECORDED)
        self.assertEqual(updated[-1].event_type, AuditEventType.APPROVAL_DECISION_RECORDED)
        self.assertEqual(result.decision_id, decision.decision_id)

    def test_policy_block_can_be_recorded_with_audit_event(self) -> None:
        result, events = record_policy_block_with_audit("subject-1", "ActionProposal", "blocked")

        self.assertEqual(result.bridge_status, BRIDGE_STATUS_POLICY_BLOCK_RECORDED)
        self.assertEqual(events[-1].event_type, AuditEventType.POLICY_BLOCK_RECORDED)

    def test_execution_blocked_event_can_be_recorded_with_audit_event(self) -> None:
        result, events = record_execution_blocked_with_audit("subject-1", "ActionProposal", "no executor")

        self.assertEqual(result.bridge_status, BRIDGE_STATUS_EXECUTION_BLOCKED_RECORDED)
        self.assertEqual(events[-1].event_type, AuditEventType.EXECUTION_BLOCKED)
        self.assertEqual(events[-1].severity, AuditEventSeverity.BLOCKED)

    def test_bridge_result_exposes_plain_data_safely(self) -> None:
        result, _events = record_proposal_with_audit(self.make_proposal())

        serialized = proposal_decision_audit_result_to_dict(result)

        self.assertEqual(serialized["bridge_status"], BRIDGE_STATUS_PROPOSAL_RECORDED)
        self.assertFalse(serialized["execution_permitted"])
        self.assertFalse(serialized["execution_triggered"])

    def test_proposal_audit_event_appends_to_in_memory_chain(self) -> None:
        result, events = record_proposal_with_audit(self.make_proposal())

        self.assertEqual(result.audit_chain_length, 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(result.latest_event_hash, events[-1].event_hash)

    def test_decision_audit_event_appends_after_proposal_event(self) -> None:
        proposal = self.make_proposal()
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")
        _proposal_result, events = record_proposal_with_audit(proposal)

        result, updated = record_decision_with_audit(proposal, decision, events)

        self.assertEqual(result.audit_chain_length, 2)
        self.assertEqual(updated[1].previous_event_hash, updated[0].event_hash)

    def test_previous_hash_chain_is_valid(self) -> None:
        proposal = self.make_proposal()
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")
        _proposal_result, events = record_proposal_with_audit(proposal)
        _decision_result, updated = record_decision_with_audit(proposal, decision, events)

        assert_append_only_chain(updated[0], updated[1])
        assert_audit_event_hash_valid(updated[0])
        assert_audit_event_hash_valid(updated[1])

    def test_existing_audit_event_collection_is_not_mutated(self) -> None:
        proposal = self.make_proposal()
        _proposal_result, events = record_proposal_with_audit(proposal)
        original_events = events
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")

        _result, updated = record_decision_with_audit(proposal, decision, events)

        self.assertEqual(events, original_events)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(updated), 2)
        self.assertIsNot(updated, events)

    def test_human_approval_decision_still_does_not_execute(self) -> None:
        decision = self.make_decision()

        with self.assertRaises(ApprovalDoesNotExecuteError):
            assert_approval_decision_does_not_execute(decision)

    def test_bridge_does_not_permit_or_trigger_execution(self) -> None:
        result, events = record_proposal_with_audit(self.make_proposal())

        self.assertFalse(result.execution_permitted)
        self.assertFalse(result.execution_triggered)
        assert_bridge_does_not_execute(result, events)

    def test_audit_event_created_by_bridge_does_not_authorize_execution(self) -> None:
        _result, events = record_execution_blocked_with_audit("subject-1", "ActionProposal", "blocked")

        self.assertFalse(events[-1].execution_authorized)
        self.assertFalse(events[-1].execution_triggered)
        self.assertFalse(events[-1].canonical_write_authorized)

    def test_provider_model_approval_remains_blocked(self) -> None:
        proposal = self.make_proposal()
        decision = ApprovalDecision(
            decision_id="provider-attempt",
            created_at="2026-06-12T19:12:00Z",
            proposal_id=proposal.proposal_id,
            proposal_type=proposal.proposal_type.value,
            decision_type=ApprovalDecisionType.APPROVE,
            decision_state=ApprovalDecisionState.INVALID,
            actor_type=ApprovalActorType.PROVIDER_MODEL,
            actor_id="model",
            reason="provider says approve",
            reviewed_exact_payload_hash="wrong",
            provider_generated=True,
        )

        with self.assertRaises(ProviderApprovalBlockedError):
            record_decision_with_audit(proposal, decision)

    def test_timeout_or_missing_decision_remains_blocked(self) -> None:
        proposal = self.make_proposal()
        expired = replace(
            create_human_approval_decision(proposal, "reviewer-1", "approved"),
            expires_at="2020-01-01T00:00:00Z",
        )

        with self.assertRaises(ApprovalTimeoutBlockedError):
            assert_timeout_does_not_approve(None)
        with self.assertRaises(ApprovalTimeoutBlockedError):
            record_decision_with_audit(proposal, expired)

    def test_action_proposal_remains_inert(self) -> None:
        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(self.make_proposal())

    def test_approval_decision_remains_non_executing(self) -> None:
        with self.assertRaises(ApprovalDoesNotExecuteError):
            assert_approval_decision_does_not_execute(self.make_decision())

    def test_audit_event_append_only_policy_still_passes(self) -> None:
        proposal = self.make_proposal()
        _result, events = record_proposal_with_audit(proposal)
        block_result, block_events = record_policy_block_with_audit(
            proposal.proposal_id,
            "ActionProposal",
            "blocked",
            events,
        )

        self.assertEqual(block_result.audit_chain_length, 2)
        self.assertEqual(append_audit_event_in_memory(events, block_events[-1]), block_events)

    def test_no_filesystem_database_provider_network_secret_or_execution_clients_are_imported(self) -> None:
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
            "os",
            "sqlite3",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "Path.write_text",
            "Path.open",
            "open(",
            "API_KEY",
            "SECRET",
            "TOKEN",
        )

        source = NEW_BRIDGE_FILE.read_text(encoding="utf-8")
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
