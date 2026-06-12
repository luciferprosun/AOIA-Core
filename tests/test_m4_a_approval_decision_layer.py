from __future__ import annotations

import ast
import unittest
from dataclasses import replace
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
    ApprovalDecisionBlockedError,
    ApprovalDoesNotExecuteError,
    ApprovalTimeoutBlockedError,
    ProviderApprovalBlockedError,
    assert_approval_decision_does_not_execute,
    assert_approval_requires_human,
    assert_decision_matches_proposal,
    assert_provider_cannot_approve,
    assert_timeout_does_not_approve,
    assert_unknown_actor_cannot_approve,
    evaluate_approval_decision_for_execution,
)
from runtime.schemas.action_proposal import (
    ActionProposalType,
    create_human_review_only_proposal,
    create_inert_action_proposal,
)
from runtime.schemas.approval_decision import (
    ApprovalActorType,
    ApprovalDecision,
    ApprovalDecisionState,
    ApprovalDecisionType,
    approval_decision_to_dict,
    create_human_approval_decision,
    create_needs_changes_decision,
    create_policy_block_decision,
    create_rejection_decision,
)
from runtime.schemas.evidence_memory import create_human_entered_evidence
from runtime.schemas.provider_critic import create_inert_provider_critique_record


REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "approval_decision.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_policy.py",
)


class M4AApprovalDecisionLayerTests(unittest.TestCase):
    def make_proposal(self):
        return create_human_review_only_proposal(
            title="Review proposed action",
            description="Structured review only.",
            proposed_by="unit-test",
            payload_summary="summarized payload",
            exact_payload='{"action":"review-only","value":1}',
            proposal_id="proposal-m4-a",
        )

    def test_human_approval_decision_can_be_recorded(self) -> None:
        decision = create_human_approval_decision(self.make_proposal(), "reviewer-1", "looks correct")

        self.assertEqual(decision.decision_type, ApprovalDecisionType.APPROVE)
        self.assertEqual(decision.actor_type, ApprovalActorType.HUMAN_REVIEWER)
        self.assertTrue(decision.human_reviewed)
        self.assertEqual(decision.decision_state, ApprovalDecisionState.RECORDED)

    def test_rejection_decision_can_be_recorded(self) -> None:
        decision = create_rejection_decision(self.make_proposal(), "reviewer-1", "reject")

        self.assertEqual(decision.decision_type, ApprovalDecisionType.REJECT)
        self.assertFalse(decision.execution_permitted)

    def test_needs_changes_decision_can_be_recorded(self) -> None:
        decision = create_needs_changes_decision(self.make_proposal(), "reviewer-1", "revise")

        self.assertEqual(decision.decision_type, ApprovalDecisionType.NEEDS_CHANGES)
        self.assertFalse(decision.execution_triggered)

    def test_policy_block_decision_can_be_recorded(self) -> None:
        decision = create_policy_block_decision(self.make_proposal(), "blocked by policy")

        self.assertEqual(decision.decision_type, ApprovalDecisionType.BLOCKED_BY_POLICY)
        self.assertTrue(decision.policy_blocked)

    def test_approval_decision_serializes_to_dict(self) -> None:
        decision = create_human_approval_decision(self.make_proposal(), "reviewer-1", "record")

        serialized = approval_decision_to_dict(decision)

        self.assertEqual(serialized["decision_type"], "APPROVE")
        self.assertEqual(serialized["actor_type"], "HUMAN_REVIEWER")
        self.assertFalse(serialized["execution_permitted"])
        self.assertFalse(serialized["execution_triggered"])

    def test_human_approval_keeps_execution_flags_false(self) -> None:
        decision = create_human_approval_decision(self.make_proposal(), "reviewer-1", "approved")

        self.assertFalse(decision.execution_permitted)
        self.assertFalse(decision.execution_triggered)

    def test_approval_decision_does_not_execute(self) -> None:
        decision = create_human_approval_decision(self.make_proposal(), "reviewer-1", "approved")

        with self.assertRaises(ApprovalDoesNotExecuteError):
            assert_approval_decision_does_not_execute(decision)

    def test_provider_model_actor_cannot_approve(self) -> None:
        proposal = self.make_proposal()
        decision = ApprovalDecision(
            decision_id="provider-attempt",
            created_at="2026-06-12T18:30:00Z",
            proposal_id=proposal.proposal_id,
            proposal_type=proposal.proposal_type.value,
            decision_type=ApprovalDecisionType.APPROVE,
            actor_type=ApprovalActorType.PROVIDER_MODEL,
            actor_id="model",
            reason="model says approve",
            reviewed_exact_payload_hash="mismatch",
            provider_generated=True,
        )

        self.assertEqual(decision.decision_state, ApprovalDecisionState.INVALID)
        with self.assertRaises(ProviderApprovalBlockedError):
            assert_provider_cannot_approve(decision)

    def test_unknown_actor_cannot_approve(self) -> None:
        proposal = self.make_proposal()
        decision = ApprovalDecision(
            decision_id="unknown-attempt",
            created_at="2026-06-12T18:30:00Z",
            proposal_id=proposal.proposal_id,
            proposal_type=proposal.proposal_type.value,
            decision_type=ApprovalDecisionType.APPROVE,
            actor_type=ApprovalActorType.UNKNOWN,
            actor_id="",
            reason="unknown",
            reviewed_exact_payload_hash="mismatch",
        )

        with self.assertRaises(ApprovalDecisionBlockedError):
            assert_unknown_actor_cannot_approve(decision)

    def test_missing_decision_or_timeout_does_not_approve(self) -> None:
        with self.assertRaises(ApprovalTimeoutBlockedError):
            assert_timeout_does_not_approve(None)

        expired = replace(
            create_human_approval_decision(self.make_proposal(), "reviewer-1", "approved"),
            expires_at="2020-01-01T00:00:00Z",
        )
        with self.assertRaises(ApprovalTimeoutBlockedError):
            assert_timeout_does_not_approve(expired)

    def test_payload_hash_mismatch_blocks_execution(self) -> None:
        proposal = self.make_proposal()
        decision = replace(
            create_human_approval_decision(proposal, "reviewer-1", "approved"),
            reviewed_exact_payload_hash="wrong",
        )

        with self.assertRaises(ApprovalDecisionBlockedError):
            assert_decision_matches_proposal(decision, proposal)

    def test_rejection_needs_changes_defer_and_policy_block_are_execution_blocked(self) -> None:
        proposal = self.make_proposal()
        decisions = (
            create_rejection_decision(proposal, "reviewer-1", "reject"),
            create_needs_changes_decision(proposal, "reviewer-1", "revise"),
            ApprovalDecision(
                decision_id="defer-1",
                created_at="2026-06-12T18:30:00Z",
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type.value,
                decision_type=ApprovalDecisionType.DEFER,
                actor_type=ApprovalActorType.HUMAN_REVIEWER,
                actor_id="reviewer-1",
                reason="defer",
                reviewed_exact_payload_hash=create_human_approval_decision(
                    proposal, "reviewer-1", "hash source"
                ).reviewed_exact_payload_hash,
                human_reviewed=True,
            ),
            create_policy_block_decision(proposal, "policy"),
        )

        for decision in decisions:
            with self.subTest(decision_type=decision.decision_type):
                self.assertEqual(evaluate_approval_decision_for_execution(decision, proposal), EXECUTION_BLOCKED_M4_A)

    def test_valid_human_approval_still_blocks_execution(self) -> None:
        proposal = self.make_proposal()
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")

        assert_timeout_does_not_approve(decision)
        assert_approval_requires_human(decision)
        assert_decision_matches_proposal(decision, proposal)
        self.assertEqual(evaluate_approval_decision_for_execution(decision, proposal), EXECUTION_BLOCKED_M4_A)

    def test_static_import_scan_rejects_execution_network_provider_secret_clients(self) -> None:
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
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
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

    def test_action_proposal_m3_a_still_remains_inert(self) -> None:
        proposal = self.make_proposal()

        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(proposal)

    def test_provider_critique_record_cannot_approve_action(self) -> None:
        critique = create_inert_provider_critique_record(
            source_provider="synthetic",
            source_model="none",
            request_text="request",
            response_text="approve action",
            prompt_summary="test",
        )

        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_provider_output_cannot_create_executable_action(critique)
        self.assertFalse(critique.action_approval_allowed)

    def test_evidence_memory_record_cannot_approve_action(self) -> None:
        evidence = create_human_entered_evidence(content_text="Observed fact.", source_id="human-1")

        with self.assertRaises(EvidenceOnlyActionBlockedError):
            assert_evidence_cannot_execute_as_action(evidence)
        self.assertFalse(evidence.action_approval_allowed)

    def test_operational_action_types_remain_data_only_under_decision_layer(self) -> None:
        for proposal_type in (
            ActionProposalType.SHELL_COMMAND,
            ActionProposalType.BROWSER_ACTION,
            ActionProposalType.FILESYSTEM_ACTION,
            ActionProposalType.GIT_ACTION,
            ActionProposalType.PROVIDER_CALL,
            ActionProposalType.CLOUD_ACTION,
        ):
            with self.subTest(proposal_type=proposal_type):
                proposal = create_inert_action_proposal(
                    proposal_type=proposal_type,
                    title="Review only",
                    description="No dispatch.",
                    proposed_by="unit-test",
                    exact_payload=proposal_type.value,
                )
                decision = create_human_approval_decision(proposal, "reviewer-1", "recorded")
                self.assertFalse(decision.execution_permitted)
                self.assertFalse(decision.execution_triggered)


if __name__ == "__main__":
    unittest.main()
