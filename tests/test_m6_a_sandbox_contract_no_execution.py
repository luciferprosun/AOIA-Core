from __future__ import annotations

import ast
import unittest
from pathlib import Path

from runtime.safety.audit_event_policy import assert_audit_event_cannot_authorize_execution
from runtime.safety.proposal_decision_audit_bridge import (
    assert_bridge_does_not_execute,
    record_decision_with_audit,
    record_proposal_with_audit,
)
from runtime.safety.sandbox_policy import (
    SandboxApprovalDoesNotExecuteError,
    SandboxExecutionBlockedError,
    SandboxNotImplementedError,
    assert_audit_event_does_not_enable_sandbox_execution,
    assert_human_approval_does_not_enable_sandbox_execution,
    assert_sandbox_action_blocked_by_default,
    assert_sandbox_contract_does_not_execute,
    assert_sandbox_execution_not_implemented,
    create_sandbox_not_run_result,
    evaluate_sandbox_request,
)
from runtime.schemas.action_proposal import (
    ActionProposalType,
    create_human_review_only_proposal,
    create_inert_action_proposal,
)
from runtime.schemas.approval_decision import create_human_approval_decision
from runtime.schemas.sandbox_contract import (
    SandboxActionType,
    SandboxDecisionType,
    SandboxPolicyDecision,
    SandboxRequest,
    SandboxResult,
    SandboxResultState,
    create_blocked_sandbox_policy_decision,
    create_blocked_sandbox_result,
    create_not_implemented_sandbox_policy_decision,
    create_sandbox_request_from_action_proposal,
    sandbox_policy_decision_to_dict,
    sandbox_request_to_dict,
    sandbox_result_to_dict,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
M6_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "sandbox_contract.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_policy.py",
)


class M6ASandboxContractNoExecutionTests(unittest.TestCase):
    def make_proposal(self, proposal_type: ActionProposalType = ActionProposalType.SHELL_COMMAND):
        return create_inert_action_proposal(
            proposal_type=proposal_type,
            title="Sandbox contract request",
            description="Represent request only.",
            proposed_by="unit-test",
            source_record_id="source-m6-a",
            source_record_type="unit-test",
            payload_summary="payload summary only",
            exact_payload='{"kind":"sample","value":1}',
            proposal_id="proposal-m6-a-" + proposal_type.value.lower(),
        )

    def make_human_review_request(self):
        proposal = create_human_review_only_proposal(
            title="Review only",
            description="No sandbox action.",
            proposed_by="unit-test",
            payload_summary="review summary only",
            exact_payload='{"kind":"review"}',
            proposal_id="proposal-m6-a-review",
        )
        return create_sandbox_request_from_action_proposal(proposal)

    def make_request_decision_result(self, proposal_type: ActionProposalType = ActionProposalType.SHELL_COMMAND):
        request = create_sandbox_request_from_action_proposal(self.make_proposal(proposal_type))
        decision = evaluate_sandbox_request(request)
        result = create_sandbox_not_run_result(request, decision)
        return request, decision, result

    def test_sandbox_request_can_be_created_from_action_proposal(self) -> None:
        proposal = self.make_proposal()

        request = create_sandbox_request_from_action_proposal(proposal)

        self.assertIsInstance(request, SandboxRequest)
        self.assertEqual(request.proposal_id, proposal.proposal_id)
        self.assertEqual(request.requested_action_type, SandboxActionType.SHELL_COMMAND)
        self.assertNotEqual(request.exact_payload_hash, proposal.exact_payload)

    def test_sandbox_policy_decision_can_be_created(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal())

        decision = create_blocked_sandbox_policy_decision(request, "blocked")

        self.assertIsInstance(decision, SandboxPolicyDecision)
        self.assertEqual(decision.sandbox_request_id, request.sandbox_request_id)
        self.assertFalse(decision.execution_allowed)

    def test_sandbox_result_can_be_created(self) -> None:
        request, decision, _result = self.make_request_decision_result()

        result = create_blocked_sandbox_result(request, decision, "blocked")

        self.assertIsInstance(result, SandboxResult)
        self.assertEqual(result.sandbox_request_id, request.sandbox_request_id)
        self.assertEqual(result.policy_decision_id, decision.decision_id)

    def test_sandbox_records_serialize_to_dict(self) -> None:
        request, decision, result = self.make_request_decision_result()

        self.assertIsInstance(sandbox_request_to_dict(request), dict)
        self.assertIsInstance(sandbox_policy_decision_to_dict(decision), dict)
        self.assertIsInstance(sandbox_result_to_dict(result), dict)

    def test_human_approval_does_not_enable_sandbox_execution(self) -> None:
        proposal = self.make_proposal(ActionProposalType.HUMAN_REVIEW_ONLY)
        approval = create_human_approval_decision(proposal, "reviewer-1", "approved for review")
        request = create_sandbox_request_from_action_proposal(proposal, approval)

        self.assertTrue(request.human_approved)
        with self.assertRaises(SandboxApprovalDoesNotExecuteError):
            assert_human_approval_does_not_enable_sandbox_execution(request, approval)

    def test_sandbox_execution_allowed_is_false(self) -> None:
        _request, decision, _result = self.make_request_decision_result()

        self.assertFalse(decision.execution_allowed)

    def test_sandbox_execution_implemented_is_false(self) -> None:
        _request, decision, _result = self.make_request_decision_result()

        self.assertFalse(decision.execution_implemented)

    def test_sandbox_execution_attempted_is_false(self) -> None:
        _request, _decision, result = self.make_request_decision_result()

        self.assertFalse(result.execution_attempted)

    def test_sandbox_execution_completed_is_false(self) -> None:
        _request, _decision, result = self.make_request_decision_result()

        self.assertFalse(result.execution_completed)

    def test_shell_command_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.SHELL_COMMAND)

    def test_browser_action_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.BROWSER_ACTION)

    def test_filesystem_action_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.FILESYSTEM_ACTION)

    def test_git_action_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.GIT_ACTION)

    def test_provider_call_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.PROVIDER_CALL)

    def test_cloud_action_sandbox_request_is_blocked(self) -> None:
        self.assert_action_type_blocked(ActionProposalType.CLOUD_ACTION)

    def test_human_review_only_request_still_does_not_execute(self) -> None:
        request = self.make_human_review_request()
        decision = evaluate_sandbox_request(request)
        result = create_sandbox_not_run_result(request, decision)

        self.assertEqual(decision.decision_type, SandboxDecisionType.NOT_IMPLEMENTED)
        self.assertEqual(result.result_state, SandboxResultState.NOT_IMPLEMENTED)
        with self.assertRaises(SandboxNotImplementedError):
            assert_sandbox_execution_not_implemented(decision)

    def test_audit_event_does_not_authorize_sandbox_execution(self) -> None:
        proposal = self.make_proposal(ActionProposalType.HUMAN_REVIEW_ONLY)
        _bridge_result, events = record_proposal_with_audit(proposal)

        with self.assertRaises(SandboxExecutionBlockedError):
            assert_audit_event_does_not_enable_sandbox_execution(events[-1])
        with self.assertRaises(Exception):
            assert_audit_event_cannot_authorize_execution(events[-1])

    def test_proposal_decision_audit_bridge_result_does_not_authorize_sandbox_execution(self) -> None:
        proposal = self.make_proposal(ActionProposalType.HUMAN_REVIEW_ONLY)
        decision = create_human_approval_decision(proposal, "reviewer-1", "approved")
        _proposal_result, events = record_proposal_with_audit(proposal)

        bridge_result, updated_events = record_decision_with_audit(proposal, decision, events)

        self.assertFalse(bridge_result.execution_permitted)
        self.assertFalse(bridge_result.execution_triggered)
        assert_bridge_does_not_execute(bridge_result, updated_events)

    def test_exact_payload_hash_and_summary_remain_inert_data(self) -> None:
        proposal = self.make_proposal()
        request = create_sandbox_request_from_action_proposal(proposal)
        serialized = sandbox_request_to_dict(request)

        self.assertEqual(serialized["payload_summary"], "payload summary only")
        self.assertEqual(len(serialized["exact_payload_hash"]), 64)
        self.assertNotIn(proposal.exact_payload, serialized.values())

    def test_no_filesystem_database_persistence_is_added(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("sqlite3", "Path.write_text", "Path.open", "open("))

    def test_no_provider_api_network_call_is_added(self) -> None:
        self.assert_forbidden_runtime_terms_absent(
            ("requests", "urllib", "http.client", "socket", "openai", "anthropic", "google.cloud")
        )

    def test_no_shell_browser_git_filesystem_cloud_capability_is_added(self) -> None:
        self.assert_forbidden_runtime_terms_absent(
            ("subprocess", "os.system", "Popen", "pty", "pexpect", "webbrowser", "selenium", "playwright")
        )

    def test_no_api_key_env_access_is_required(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("dotenv", "os.environ", "API_KEY", "SECRET", "TOKEN"))

    def test_constructor_rejects_execution_allowed_true(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal())

        with self.assertRaises(ValueError):
            SandboxPolicyDecision(
                decision_id="bad",
                created_at="2026-06-13T00:00:00Z",
                sandbox_request_id=request.sandbox_request_id,
                decision_type=SandboxDecisionType.NOT_IMPLEMENTED,
                reason="bad",
                execution_allowed=True,
                execution_implemented=False,
                requires_future_sandbox=True,
                policy_blocked=True,
                audit_event_id="event",
                notes="",
            )

    def test_constructor_rejects_execution_implemented_true(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal())

        with self.assertRaises(ValueError):
            SandboxPolicyDecision(
                decision_id="bad",
                created_at="2026-06-13T00:00:00Z",
                sandbox_request_id=request.sandbox_request_id,
                decision_type=SandboxDecisionType.NOT_IMPLEMENTED,
                reason="bad",
                execution_allowed=False,
                execution_implemented=True,
                requires_future_sandbox=True,
                policy_blocked=True,
                audit_event_id="event",
                notes="",
            )

    def test_constructor_rejects_execution_attempted_true(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal())

        with self.assertRaises(ValueError):
            SandboxResult(
                result_id="bad",
                created_at="2026-06-13T00:00:00Z",
                sandbox_request_id=request.sandbox_request_id,
                policy_decision_id="decision",
                result_state=SandboxResultState.NOT_RUN,
                execution_attempted=True,
                execution_completed=False,
                output_summary="",
                error_summary="bad",
                audit_event_id="event",
                notes="",
            )

    def test_constructor_rejects_execution_completed_true(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal())

        with self.assertRaises(ValueError):
            SandboxResult(
                result_id="bad",
                created_at="2026-06-13T00:00:00Z",
                sandbox_request_id=request.sandbox_request_id,
                policy_decision_id="decision",
                result_state=SandboxResultState.NOT_RUN,
                execution_attempted=False,
                execution_completed=True,
                output_summary="",
                error_summary="bad",
                audit_event_id="event",
                notes="",
            )

    def test_document_parse_requires_future_sandbox_but_still_does_not_execute(self) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal(ActionProposalType.DOCUMENT_PARSE))

        decision = evaluate_sandbox_request(request)
        result = create_sandbox_not_run_result(request, decision)

        self.assertEqual(decision.decision_type, SandboxDecisionType.REQUIRES_FUTURE_SANDBOX)
        self.assertFalse(decision.execution_allowed)
        self.assertFalse(result.execution_attempted)

    def test_not_implemented_decision_helper_remains_non_executable(self) -> None:
        request = self.make_human_review_request()

        decision = create_not_implemented_sandbox_policy_decision(request, "not implemented")

        self.assertEqual(decision.decision_type, SandboxDecisionType.NOT_IMPLEMENTED)
        self.assertFalse(decision.execution_allowed)

    def test_contract_assertion_accepts_safe_records(self) -> None:
        request, decision, result = self.make_request_decision_result()

        assert_sandbox_contract_does_not_execute(request, decision, result)

    def test_policy_rejects_mismatched_decision_or_result(self) -> None:
        request, decision, result = self.make_request_decision_result()
        other_request = self.make_human_review_request()

        with self.assertRaises(Exception):
            assert_sandbox_contract_does_not_execute(other_request, decision)
        with self.assertRaises(Exception):
            assert_sandbox_contract_does_not_execute(other_request, result=result)

    def assert_action_type_blocked(self, proposal_type: ActionProposalType) -> None:
        request = create_sandbox_request_from_action_proposal(self.make_proposal(proposal_type))

        decision = evaluate_sandbox_request(request)
        result = create_sandbox_not_run_result(request, decision)

        self.assertEqual(decision.decision_type, SandboxDecisionType.BLOCKED_BY_DEFAULT)
        self.assertTrue(decision.policy_blocked)
        self.assertFalse(decision.execution_allowed)
        self.assertEqual(result.result_state, SandboxResultState.BLOCKED)
        self.assertFalse(result.execution_attempted)
        with self.assertRaises(SandboxExecutionBlockedError):
            assert_sandbox_action_blocked_by_default(request)

    def assert_forbidden_runtime_terms_absent(self, forbidden_text: tuple[str, ...]) -> None:
        for source_file in M6_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)

    def test_new_runtime_files_import_only_allowed_modules(self) -> None:
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
            "shutil",
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
        )

        for source_file in M6_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
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
