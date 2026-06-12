from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from runtime.safety.action_proposal_policy import (
    ActionProposalExecutionBlockedError,
    EvidenceOnlyActionBlockedError,
    ProviderGeneratedActionBlockedError,
    assert_action_proposal_cannot_execute,
    assert_evidence_cannot_execute_as_action,
    assert_provider_output_cannot_create_executable_action,
)
from runtime.safety.approval_decision_policy import (
    EXECUTION_BLOCKED_M4_A,
    ApprovalDoesNotExecuteError,
    assert_approval_decision_does_not_execute,
    evaluate_approval_decision_for_execution,
)
from runtime.safety.audit_event_policy import (
    AuditEventChainBlockedError,
    AuditEventExecutionBlockedError,
    append_audit_event_in_memory,
    assert_append_only_chain,
    assert_audit_event_cannot_authorize_execution,
    assert_audit_event_does_not_execute,
    assert_audit_event_hash_valid,
    assert_provider_event_has_no_authority,
)
from runtime.schemas.action_proposal import create_human_review_only_proposal
from runtime.schemas.approval_decision import create_human_approval_decision
from runtime.schemas.audit_event import (
    AuditEvent,
    AuditEventSeverity,
    AuditEventTrustState,
    AuditEventType,
    audit_event_to_dict,
    compute_audit_event_hash,
    create_action_proposal_audit_event,
    create_approval_decision_audit_event,
    create_evidence_record_audit_event,
    create_execution_blocked_audit_event,
    create_policy_block_audit_event,
    create_provider_critique_audit_event,
)
from runtime.schemas.evidence_memory import create_human_entered_evidence
from runtime.schemas.provider_critic import create_inert_provider_critique_record


REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "audit_event.py",
    REPO_ROOT / "runtime" / "safety" / "audit_event_policy.py",
)


class M5AAppendOnlyAuditEventLayerTests(unittest.TestCase):
    def make_proposal(self):
        return create_human_review_only_proposal(
            title="Review proposed action",
            description="Structured review only.",
            proposed_by="unit-test",
            payload_summary="payload summary",
            exact_payload='{"action":"review-only","value":1}',
            proposal_id="proposal-m5-a",
        )

    def make_decision(self):
        return create_human_approval_decision(
            self.make_proposal(),
            "reviewer-1",
            "human reviewed",
        )

    def test_action_proposal_audit_event_can_be_created(self) -> None:
        event = create_action_proposal_audit_event(self.make_proposal())

        self.assertEqual(event.event_type, AuditEventType.ACTION_PROPOSAL_CREATED)
        self.assertEqual(event.subject_type, "ActionProposal")
        self.assertFalse(event.execution_authorized)

    def test_approval_decision_audit_event_can_be_created(self) -> None:
        event = create_approval_decision_audit_event(self.make_decision())

        self.assertEqual(event.event_type, AuditEventType.APPROVAL_DECISION_RECORDED)
        self.assertEqual(event.trust_state, AuditEventTrustState.HUMAN_REVIEWED)
        self.assertFalse(event.execution_triggered)

    def test_policy_block_audit_event_can_be_created(self) -> None:
        event = create_policy_block_audit_event("subject-1", "ActionProposal", "blocked")

        self.assertEqual(event.event_type, AuditEventType.POLICY_BLOCK_RECORDED)
        self.assertEqual(event.severity, AuditEventSeverity.BLOCKED)

    def test_execution_blocked_audit_event_can_be_created(self) -> None:
        event = create_execution_blocked_audit_event("subject-1", "ActionProposal", "no executor")

        self.assertEqual(event.event_type, AuditEventType.EXECUTION_BLOCKED)
        self.assertEqual(event.result, "execution_blocked")

    def test_audit_event_serializes_to_dict(self) -> None:
        event = create_action_proposal_audit_event(self.make_proposal())

        serialized = audit_event_to_dict(event)

        self.assertEqual(serialized["event_type"], "ACTION_PROPOSAL_CREATED")
        self.assertFalse(serialized["execution_authorized"])
        self.assertFalse(serialized["canonical_write_authorized"])

    def test_event_hash_is_deterministic(self) -> None:
        event = create_policy_block_audit_event("subject-1", "ActionProposal", "blocked")

        self.assertEqual(event.event_hash, compute_audit_event_hash(event))
        assert_audit_event_hash_valid(event)

    def test_event_hash_changes_when_payload_changes(self) -> None:
        first = create_policy_block_audit_event("subject-1", "ActionProposal", "blocked")
        second = create_policy_block_audit_event("subject-1", "ActionProposal", "different")

        self.assertNotEqual(first.event_hash, second.event_hash)

    def test_previous_hash_links_event_chain(self) -> None:
        first = create_action_proposal_audit_event(self.make_proposal())
        second = create_approval_decision_audit_event(self.make_decision(), previous_event_hash=first.event_hash)

        assert_append_only_chain(first, second)
        self.assertEqual(second.previous_event_hash, first.event_hash)

    def test_append_only_helper_does_not_mutate_existing_collection(self) -> None:
        first = create_action_proposal_audit_event(self.make_proposal())
        existing = (first,)
        second = create_approval_decision_audit_event(self.make_decision(), previous_event_hash=first.event_hash)

        updated = append_audit_event_in_memory(existing, second)

        self.assertEqual(existing, (first,))
        self.assertEqual(updated, (first, second))
        self.assertIsNot(updated, existing)

    def test_append_only_helper_rejects_bad_previous_hash(self) -> None:
        first = create_action_proposal_audit_event(self.make_proposal())
        second = create_approval_decision_audit_event(self.make_decision(), previous_event_hash="wrong")

        with self.assertRaises(AuditEventChainBlockedError):
            append_audit_event_in_memory((first,), second)

    def test_audit_event_cannot_authorize_or_trigger_execution(self) -> None:
        event = create_execution_blocked_audit_event("subject-1", "ActionProposal", "blocked")

        with self.assertRaises(AuditEventExecutionBlockedError):
            assert_audit_event_cannot_authorize_execution(event)
        with self.assertRaises(AuditEventExecutionBlockedError):
            assert_audit_event_does_not_execute(event)
        with self.assertRaises(ValueError):
            AuditEvent(
                event_id="bad",
                created_at="2026-06-12T19:00:00Z",
                event_type=AuditEventType.EXECUTION_BLOCKED,
                severity=AuditEventSeverity.BLOCKED,
                trust_state=AuditEventTrustState.POLICY_RECORDED,
                subject_id="subject-1",
                subject_type="ActionProposal",
                actor_id="runtime-policy",
                actor_type="SYSTEM_POLICY",
                action="block_execution",
                result="blocked",
                reason="bad flag",
                execution_authorized=True,
            )

    def test_human_approval_audit_event_still_does_not_execute(self) -> None:
        proposal = self.make_proposal()
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")
        event = create_approval_decision_audit_event(decision)

        self.assertEqual(evaluate_approval_decision_for_execution(decision, proposal), EXECUTION_BLOCKED_M4_A)
        with self.assertRaises(ApprovalDoesNotExecuteError):
            assert_approval_decision_does_not_execute(decision)
        with self.assertRaises(AuditEventExecutionBlockedError):
            assert_audit_event_does_not_execute(event)

    def test_provider_generated_audit_event_has_no_authority(self) -> None:
        record = create_inert_provider_critique_record(
            source_provider="synthetic",
            source_model="none",
            request_text="request",
            prompt_summary="provider output",
            response_text="approve this",
        )
        event = create_provider_critique_audit_event(record)

        self.assertTrue(event.provider_generated)
        self.assertEqual(event.trust_state, AuditEventTrustState.PROVIDER_UNTRUSTED)
        self.assertFalse(event.execution_authorized)
        assert_provider_event_has_no_authority(event)

    def test_provider_critique_record_cannot_create_trusted_execution_authorizing_event(self) -> None:
        record = create_inert_provider_critique_record(
            source_provider="synthetic",
            source_model="none",
            request_text="request",
            prompt_summary="provider output",
            response_text="approve this",
        )
        event = create_provider_critique_audit_event(record)

        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_provider_output_cannot_create_executable_action(record)
        self.assertFalse(event.execution_authorized)
        self.assertFalse(event.canonical_write_authorized)

    def test_evidence_memory_record_cannot_create_execution_authorizing_event(self) -> None:
        evidence = create_human_entered_evidence(content_text="Observed fact.", source_id="human-1")
        event = create_evidence_record_audit_event(evidence)

        with self.assertRaises(EvidenceOnlyActionBlockedError):
            assert_evidence_cannot_execute_as_action(evidence)
        self.assertFalse(event.execution_authorized)
        self.assertFalse(event.execution_triggered)

    def test_action_proposal_remains_inert_under_m3_a(self) -> None:
        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(self.make_proposal())

    def test_approval_decision_remains_non_executing_under_m4_a(self) -> None:
        with self.assertRaises(ApprovalDoesNotExecuteError):
            assert_approval_decision_does_not_execute(self.make_decision())

    def test_audit_event_is_frozen_by_dataclass(self) -> None:
        event = create_action_proposal_audit_event(self.make_proposal())

        with self.assertRaises(FrozenInstanceError):
            event.reason = "mutated"

    def test_update_creates_new_event_hash_not_mutating_old_event(self) -> None:
        event = create_policy_block_audit_event("subject-1", "ActionProposal", "blocked")
        changed = replace(event, reason="different")

        self.assertNotEqual(event.event_hash, changed.event_hash)
        self.assertEqual(event.reason, "blocked")

    def test_static_import_scan_rejects_execution_network_provider_secret_and_persistence_clients(self) -> None:
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

        for path in NEW_RUNTIME_FILES:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
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
