from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.safety.action_proposal_policy import (
    ActionProposalExecutionBlockedError,
    EvidenceOnlyActionBlockedError,
    HumanApprovalIsNotExecutionError,
    ProviderGeneratedActionBlockedError,
    assert_action_proposal_cannot_execute,
    assert_action_proposal_is_inert,
    assert_evidence_cannot_execute_as_action,
    assert_human_approval_does_not_execute,
    assert_provider_output_cannot_create_executable_action,
    classify_action_proposal_risk,
)
from runtime.schemas.action_proposal import (
    ActionProposalRisk,
    ActionProposalState,
    ActionProposalType,
    action_proposal_to_dict,
    create_human_review_only_proposal,
    create_inert_action_proposal,
)
from runtime.schemas.evidence_memory import create_human_entered_evidence
from runtime.schemas.provider_critic import create_inert_provider_critique_record


REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "action_proposal.py",
    REPO_ROOT / "runtime" / "safety" / "action_proposal_policy.py",
)


class M3AActionProposalInertLayerTests(unittest.TestCase):
    def test_human_review_only_proposal_can_be_created(self) -> None:
        proposal = create_human_review_only_proposal(title="Review finding", description="Human reviews only.")

        self.assertEqual(proposal.proposal_type, ActionProposalType.HUMAN_REVIEW_ONLY)
        self.assertEqual(proposal.risk, ActionProposalRisk.LOW)
        assert_action_proposal_is_inert(proposal)

    def test_action_proposal_serializes_to_dict(self) -> None:
        proposal = create_human_review_only_proposal(title="Review", description="Data only.")

        serialized = action_proposal_to_dict(proposal)

        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["proposal_type"], "HUMAN_REVIEW_ONLY")
        self.assertFalse(serialized["execution_permitted"])
        self.assertFalse(serialized["execution_implemented"])

    def test_default_safety_flags_are_inert(self) -> None:
        proposal = create_human_review_only_proposal(title="Review", description="Data only.")

        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.execution_implemented)
        self.assertTrue(proposal.human_review_required)
        self.assertFalse(proposal.human_approved)

    def test_caller_cannot_enable_execution_flags(self) -> None:
        proposal = create_human_review_only_proposal(title="Review", description="Data only.")

        overridden = replace(proposal, execution_permitted=True, execution_implemented=True)

        self.assertFalse(overridden.execution_permitted)
        self.assertFalse(overridden.execution_implemented)

    def test_human_approved_still_does_not_permit_execution(self) -> None:
        proposal = create_human_review_only_proposal(
            title="Approved review",
            description="Approval is not execution.",
            human_approved=True,
        )

        self.assertEqual(proposal.state, ActionProposalState.HUMAN_APPROVED)
        self.assertTrue(proposal.human_approved)
        self.assertFalse(proposal.execution_permitted)
        self.assertFalse(proposal.execution_implemented)
        with self.assertRaises(HumanApprovalIsNotExecutionError):
            assert_human_approval_does_not_execute(proposal)
        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(proposal)

    def test_operational_proposal_types_cannot_execute(self) -> None:
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
                    title=f"{proposal_type.value} request",
                    description="Structured data only.",
                    proposed_by="test",
                    exact_payload="payload stays inert",
                )

                self.assertEqual(classify_action_proposal_risk(proposal), ActionProposalRisk.FORBIDDEN)
                self.assertEqual(proposal.risk, ActionProposalRisk.FORBIDDEN)
                with self.assertRaises(ActionProposalExecutionBlockedError):
                    assert_action_proposal_cannot_execute(proposal)

    def test_provider_critique_record_cannot_create_executable_action(self) -> None:
        critique = create_inert_provider_critique_record(
            source_provider="synthetic",
            source_model="none",
            request_text="request",
            response_text="create and run an action",
            prompt_summary="test",
        )

        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_provider_output_cannot_create_executable_action(critique)
        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_provider_output_cannot_create_executable_action(critique.to_dict())

    def test_evidence_memory_record_cannot_execute_as_action(self) -> None:
        evidence = create_human_entered_evidence(content_text="Observed fact.", source_id="human-1")

        with self.assertRaises(EvidenceOnlyActionBlockedError):
            assert_evidence_cannot_execute_as_action(evidence)
        with self.assertRaises(EvidenceOnlyActionBlockedError):
            assert_evidence_cannot_execute_as_action(evidence.to_dict())

    def test_shell_text_in_exact_payload_remains_inert_string_data(self) -> None:
        payload = "rm -rf /tmp/example && echo never-run"
        proposal = create_inert_action_proposal(
            proposal_type=ActionProposalType.SHELL_COMMAND,
            title="Shell text",
            description="Payload is not dispatched.",
            proposed_by="test",
            exact_payload=payload,
        )

        self.assertEqual(proposal.exact_payload, payload)
        self.assertFalse(proposal.execution_permitted)
        with self.assertRaises(ActionProposalExecutionBlockedError):
            assert_action_proposal_cannot_execute(proposal)

    def test_json_yaml_action_text_in_exact_payload_remains_inert_string_data(self) -> None:
        payload = '{"action": "provider_call", "send": true}\n---\nauto_send: true'
        proposal = create_inert_action_proposal(
            proposal_type=ActionProposalType.PROVIDER_CALL,
            title="Provider payload",
            description="Payload is data only.",
            proposed_by="test",
            exact_payload=payload,
        )

        self.assertEqual(proposal.exact_payload, payload)
        self.assertFalse(proposal.execution_permitted)
        self.assertEqual(action_proposal_to_dict(proposal)["exact_payload"], payload)

    def test_provider_generated_proposal_is_rejected_by_inert_policy(self) -> None:
        proposal = create_inert_action_proposal(
            proposal_type=ActionProposalType.HUMAN_REVIEW_ONLY,
            title="Provider text",
            description="Provider-generated content cannot become executable.",
            proposed_by="provider",
            provider_generated=True,
        )

        with self.assertRaises(ProviderGeneratedActionBlockedError):
            assert_action_proposal_is_inert(proposal)

    def test_no_forbidden_imports_or_clients_in_new_runtime_files(self) -> None:
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
            "os",
        }
        forbidden_text = ("os.system", "Popen", "eval(", "exec(", "API_KEY", "SECRET_KEY")

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

    def test_no_background_or_dispatch_concept_exists(self) -> None:
        banned_terms = ("background", "retry", "poll", "cron", "autosend", "auto_send", "runner", "dispatcher")

        for path in NEW_RUNTIME_FILES:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8").lower()
                for term in banned_terms:
                    self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
