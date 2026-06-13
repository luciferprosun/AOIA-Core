from __future__ import annotations

import ast
import unittest
from pathlib import Path

from runtime.safety.audit_event_policy import assert_append_only_chain
from runtime.safety.dry_run_agent_loop import run_dry_run_agent_loop
from runtime.safety.dry_run_agent_policy import (
    DryRunAgentExecutionBlockedError,
    DryRunAgentInvalidRequestError,
    DryRunAgentPersistenceBlockedError,
    DryRunAgentProviderCallBlockedError,
    assert_dry_run_agent_does_not_call_provider,
    assert_dry_run_agent_does_not_execute,
    assert_dry_run_agent_does_not_persist,
    assert_dry_run_request_valid,
    assert_plan_steps_are_inert,
)
from runtime.safety.proposal_decision_audit_bridge import (
    assert_bridge_does_not_execute,
    record_proposal_with_audit,
)
from runtime.safety.sandbox_policy import assert_sandbox_contract_does_not_execute
from runtime.schemas.action_proposal import ActionProposalType, create_human_review_only_proposal
from runtime.schemas.dry_run_agent import (
    DryRunAgentFinalState,
    DryRunAgentRequest,
    DryRunAgentState,
    DryRunAgentTrace,
    DryRunPlanStep,
    create_dry_run_agent_request,
    create_dry_run_plan_step,
    dry_run_agent_trace_to_dict,
)
from runtime.schemas.sandbox_contract import SandboxDecisionType, SandboxResultState


REPO_ROOT = Path(__file__).resolve().parents[1]
M7_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "dry_run_agent.py",
    REPO_ROOT / "runtime" / "safety" / "dry_run_agent_policy.py",
    REPO_ROOT / "runtime" / "safety" / "dry_run_agent_loop.py",
)


class M7ADryRunAgentLoopNoExecutionTests(unittest.TestCase):
    def make_step(self, action_type: ActionProposalType = ActionProposalType.SHELL_COMMAND) -> DryRunPlanStep:
        return create_dry_run_plan_step(
            title="Dry-run proposed step",
            description="Represent the action only.",
            proposed_action_type=action_type.value,
            payload_summary="payload summary only",
            exact_payload='{"command":"printf hello","mode":"dry-run"}',
            step_index=0,
            step_id="dry-run-step-m7-a-" + action_type.value.lower(),
        )

    def make_request(
        self,
        action_type: ActionProposalType = ActionProposalType.SHELL_COMMAND,
        *,
        provider_generated: bool = False,
        human_review_required: bool = True,
    ) -> DryRunAgentRequest:
        return create_dry_run_agent_request(
            goal_text="Validate proposed action without running it.",
            requested_by="unit-test",
            plan_steps=(self.make_step(action_type),),
            provider_generated=provider_generated,
            human_review_required=human_review_required,
            run_id="dry-run-agent-m7-a-" + action_type.value.lower(),
        )

    def run_sample(self):
        return run_dry_run_agent_loop(self.make_request())

    def test_dry_run_plan_step_can_be_created(self) -> None:
        step = self.make_step()

        self.assertIsInstance(step, DryRunPlanStep)
        self.assertFalse(step.execution_intended)

    def test_dry_run_agent_request_can_be_created(self) -> None:
        request = self.make_request()

        self.assertIsInstance(request, DryRunAgentRequest)
        self.assertEqual(len(request.plan_steps), 1)

    def test_empty_plan_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            create_dry_run_agent_request(
                goal_text="goal",
                requested_by="unit-test",
                plan_steps=(),
            )

    def test_plan_steps_are_inert(self) -> None:
        request = self.make_request()

        assert_plan_steps_are_inert(request)
        with self.assertRaises(ValueError):
            create_dry_run_plan_step(
                title="bad",
                description="bad",
                proposed_action_type=ActionProposalType.SHELL_COMMAND.value,
                payload_summary="bad",
                exact_payload="bad",
                execution_intended=True,
            )

    def test_dry_run_loop_returns_trace(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertIsInstance(trace, DryRunAgentTrace)
        self.assertEqual(trace.state, DryRunAgentState.COMPLETED_BLOCKED)

    def test_dry_run_loop_creates_action_proposal(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertTrue(trace.proposal_id.startswith("action-proposal-"))

    def test_dry_run_loop_records_approval_decision(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertTrue(trace.decision_id.startswith("approval-decision-"))

    def test_dry_run_loop_appends_audit_event_records(self) -> None:
        trace, events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertEqual(len(events), 2)
        self.assertEqual(trace.audit_chain_length, 2)
        self.assertEqual(trace.latest_audit_event_id, events[-1].event_id)

    def test_dry_run_loop_creates_sandbox_request(self) -> None:
        trace, _events, sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertEqual(trace.sandbox_request_id, sandbox_request.sandbox_request_id)

    def test_dry_run_loop_creates_sandbox_policy_decision(self) -> None:
        trace, _events, _sandbox_request, sandbox_decision, _sandbox_result = self.run_sample()

        self.assertEqual(trace.sandbox_policy_decision_id, sandbox_decision.decision_id)
        self.assertEqual(sandbox_decision.decision_type, SandboxDecisionType.BLOCKED_BY_DEFAULT)

    def test_dry_run_loop_creates_sandbox_result(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, sandbox_result = self.run_sample()

        self.assertEqual(trace.sandbox_result_id, sandbox_result.result_id)
        self.assertEqual(sandbox_result.result_state, SandboxResultState.BLOCKED)

    def test_final_trace_state_is_blocked_no_execution(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertEqual(trace.final_state, DryRunAgentFinalState.BLOCKED_NO_EXECUTION)

    def test_execution_permitted_is_false(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertFalse(trace.execution_permitted)

    def test_execution_triggered_is_false(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertFalse(trace.execution_triggered)

    def test_provider_call_permitted_is_false(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertFalse(trace.provider_call_permitted)

    def test_filesystem_persistence_permitted_is_false(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertFalse(trace.filesystem_persistence_permitted)

    def test_human_approval_does_not_enable_execution(self) -> None:
        trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        with self.assertRaises(DryRunAgentExecutionBlockedError):
            assert_dry_run_agent_does_not_execute(trace)

    def test_audit_event_does_not_authorize_execution(self) -> None:
        _trace, events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        self.assertFalse(events[-1].execution_authorized)
        self.assertFalse(events[-1].execution_triggered)

    def test_bridge_does_not_authorize_execution(self) -> None:
        proposal = create_human_review_only_proposal(
            title="review",
            description="review only",
            proposed_by="unit-test",
            payload_summary="summary",
            exact_payload="payload",
        )
        bridge_result, events = record_proposal_with_audit(proposal)

        assert_bridge_does_not_execute(bridge_result, events)

    def test_sandbox_does_not_execute(self) -> None:
        _trace, _events, sandbox_request, sandbox_decision, sandbox_result = self.run_sample()

        assert_sandbox_contract_does_not_execute(sandbox_request, sandbox_decision, sandbox_result)
        self.assertFalse(sandbox_decision.execution_allowed)
        self.assertFalse(sandbox_result.execution_attempted)

    def test_existing_audit_chain_is_not_mutated(self) -> None:
        proposal = create_human_review_only_proposal(
            title="existing",
            description="existing event",
            proposed_by="unit-test",
            payload_summary="summary",
            exact_payload="payload",
        )
        _bridge_result, existing_events = record_proposal_with_audit(proposal)
        original_events = existing_events

        _trace, new_events, _sandbox_request, _sandbox_decision, _sandbox_result = run_dry_run_agent_loop(
            self.make_request(),
            existing_audit_events=existing_events,
        )

        self.assertEqual(existing_events, original_events)
        self.assertEqual(len(existing_events), 1)
        self.assertEqual(len(new_events), 3)
        self.assertIsNot(new_events, existing_events)

    def test_previous_hash_chain_remains_valid(self) -> None:
        _trace, events, _sandbox_request, _sandbox_decision, _sandbox_result = self.run_sample()

        assert_append_only_chain(events[0], events[1])

    def test_exact_payload_remains_inert_string_data(self) -> None:
        request = self.make_request()
        step = request.plan_steps[0]
        trace, _events, sandbox_request, _sandbox_decision, _sandbox_result = run_dry_run_agent_loop(request)

        self.assertIn("printf hello", step.exact_payload)
        self.assertEqual(len(sandbox_request.exact_payload_hash), 64)
        self.assertNotIn(step.exact_payload, dry_run_agent_trace_to_dict(trace).values())

    def test_provider_generated_dry_run_request_cannot_gain_authority(self) -> None:
        request = self.make_request(provider_generated=True)

        with self.assertRaises(DryRunAgentProviderCallBlockedError):
            run_dry_run_agent_loop(request)

    def test_policy_blocks_provider_calls_and_persistence(self) -> None:
        request = self.make_request()

        assert_dry_run_request_valid(request)
        with self.assertRaises(DryRunAgentProviderCallBlockedError):
            assert_dry_run_agent_does_not_call_provider(request)
        with self.assertRaises(DryRunAgentPersistenceBlockedError):
            assert_dry_run_agent_does_not_persist(request)

    def test_invalid_request_type_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            assert_dry_run_request_valid(object())  # type: ignore[arg-type]

    def test_no_provider_api_network_call_is_added(self) -> None:
        self.assert_forbidden_runtime_imports_absent(
            {"requests", "urllib", "http.client", "socket", "openai", "anthropic", "google.cloud"}
        )

    def test_no_shell_browser_git_filesystem_cloud_capability_is_added(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"subprocess", "pty", "pexpect", "webbrowser", "selenium", "playwright", "git"})
        self.assert_forbidden_runtime_terms_absent(("os.system", "Popen"))

    def test_no_filesystem_database_persistence_is_added(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("Path.write_text", "Path.open", "open(", "sqlite3", "shutil"))

    def test_no_api_key_env_access_is_required(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("dotenv", "os.environ", "API_KEY", "SECRET", "TOKEN"))

    def test_trace_rejects_authority_flags_true(self) -> None:
        with self.assertRaises(ValueError):
            DryRunAgentTrace(
                run_id="bad",
                created_at="2026-06-13T00:00:00Z",
                state=DryRunAgentState.COMPLETED_BLOCKED,
                final_state=DryRunAgentFinalState.BLOCKED_NO_EXECUTION,
                goal_hash="hash",
                proposal_id="proposal",
                decision_id="decision",
                latest_audit_event_id="event",
                latest_audit_event_hash="event-hash",
                sandbox_request_id="sandbox-request",
                sandbox_policy_decision_id="sandbox-decision",
                sandbox_result_id="sandbox-result",
                execution_permitted=True,
                execution_triggered=False,
                provider_call_permitted=False,
                filesystem_persistence_permitted=False,
                audit_chain_length=0,
                reason="bad",
                notes="",
            )

    def test_policy_error_type_exists_for_empty_plan_contract(self) -> None:
        self.assertTrue(issubclass(DryRunAgentInvalidRequestError, ValueError))

    def test_static_import_scan_rejects_forbidden_clients_in_new_runtime_files(self) -> None:
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
            "threading",
            "asyncio",
            "sched",
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

        for source_file in M7_RUNTIME_FILES:
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

    def assert_forbidden_runtime_terms_absent(self, forbidden_text: tuple[str, ...]) -> None:
        for source_file in M7_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)

    def assert_forbidden_runtime_imports_absent(self, forbidden_modules: set[str]) -> None:
        for source_file in M7_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
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
