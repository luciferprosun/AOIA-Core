from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.execution.human_execution_barrier import (
    HumanDecisionSource,
    HumanDecisionVerdict,
    HumanExecutionBarrierFlag,
    HumanExecutionBarrierRequest,
    HumanExecutionBarrierStatus,
    HumanExecutionSourceTrust,
    evaluate_human_execution_barrier,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
HUMAN_EXECUTION_BARRIER = REPO_ROOT / "runtime" / "execution" / "human_execution_barrier.py"
COMMAND_HASH = "a" * 64
TEST_RUNNER_HASH = "b" * 64
SANDBOX_HASH = "c" * 64
POLICY_HASH = "d" * 64
DECISION_HASH = "e" * 64
CONTROLLED_REQUEST_HASH = "f" * 64


class HumanExecutionBarrier1ATests(unittest.TestCase):
    def test_no_preexisting_duplicate_human_execution_barrier_modules(self):
        matches = sorted(
            path
            for path in (REPO_ROOT / "runtime").rglob("*barrier*")
            if path.is_file() and path.suffix == ".py" and path != HUMAN_EXECUTION_BARRIER
        )

        self.assertEqual([], [path for path in matches if "execution" in path.name])

    def test_valid_human_approve_with_matching_hashes_passes(self):
        result = self.result()

        self.assertEqual(HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED, result.status)
        self.assertTrue(result.execution_barrier_passed)
        self.assertEqual("human-exec-barrier-" + result.execution_barrier_hash[:24], result.execution_barrier_id)
        self.assertIn(HumanExecutionBarrierFlag.COMMAND_HASH_BOUND, result.flags)
        self.assertIn(HumanExecutionBarrierFlag.TEST_RUNNER_HASH_BOUND, result.flags)
        self.assertIn(HumanExecutionBarrierFlag.SANDBOX_HASH_BOUND, result.flags)
        self.assertIn(HumanExecutionBarrierFlag.POLICY_HASH_BOUND, result.flags)
        self.assertIn(HumanExecutionBarrierFlag.CONTROLLED_EXECUTION_REQUEST_HASH_BOUND, result.flags)
        self.assertIn(HumanExecutionBarrierFlag.BARRIER_PASSED_FOR_CONTROLLED_TEST_RUNNER_ONLY, result.flags)
        self.assert_all_effects_false(result)

    def test_same_valid_request_produces_same_hash_id(self):
        first = self.result()
        second = self.result()

        self.assertEqual(first.execution_barrier_hash, second.execution_barrier_hash)
        self.assertEqual(first.execution_barrier_id, second.execution_barrier_id)

    def test_changing_human_decision_hash_changes_barrier_hash_id(self):
        first = self.result(human_decision_hash=DECISION_HASH)
        second = self.result(human_decision_hash="1" * 64)

        self.assertNotEqual(first.execution_barrier_hash, second.execution_barrier_hash)
        self.assertNotEqual(first.execution_barrier_id, second.execution_barrier_id)

    def test_changing_command_hash_creates_mismatch_and_blocks(self):
        result = self.result(requested_command_hash="1" * 64)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_COMMAND_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED, result.flags)
        self.assert_all_effects_false(result)

    def test_changing_test_runner_control_hash_creates_mismatch_and_blocks(self):
        result = self.result(source_test_runner_control_hash="1" * 64)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_TEST_RUNNER_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED, result.flags)
        self.assert_all_effects_false(result)

    def test_changing_sandbox_envelope_hash_creates_mismatch_and_blocks(self):
        result = self.result(source_sandbox_envelope_hash="1" * 64)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_SANDBOX_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED, result.flags)
        self.assert_all_effects_false(result)

    def test_changing_policy_hash_creates_mismatch_and_blocks_when_present(self):
        result = self.result(source_policy_check_hash="1" * 64)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_POLICY_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HASH_MISMATCH_BLOCKED, result.flags)
        self.assert_all_effects_false(result)

    def test_missing_human_decision_id_blocks(self):
        result = self.result(human_decision_id=None)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_MISSING_HUMAN_DECISION, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HUMAN_DECISION_REQUIRED, result.flags)

    def test_missing_human_decision_hash_blocks(self):
        result = self.result(human_decision_hash=None)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_MISSING_HUMAN_DECISION, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_human_reject_blocks(self):
        result = self.result(human_decision_verdict=HumanDecisionVerdict.REJECT)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_REJECTED_BY_HUMAN, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.HUMAN_DECISION_REJECT, result.flags)
        self.assert_all_effects_false(result)

    def test_non_human_decision_source_blocks(self):
        result = self.result(human_decision_source=HumanDecisionSource.PROVIDER_MODEL)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_NON_HUMAN_DECISION_SOURCE, result.status)
        self.assertFalse(result.execution_barrier_passed)
        self.assertIn(HumanExecutionBarrierFlag.NON_HUMAN_DECISION_SOURCE_BLOCKED, result.flags)
        self.assert_all_effects_false(result)

    def test_provider_or_untrusted_source_blocks(self):
        for source_trust in (
            HumanExecutionSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
            HumanExecutionSourceTrust.PROVIDER_UNTRUSTED,
            HumanExecutionSourceTrust.MODEL_UNTRUSTED,
        ):
            with self.subTest(source_trust=source_trust):
                result = self.result(source_trust=source_trust)

                self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_UNTRUSTED_PROVIDER_SOURCE, result.status)
                self.assertFalse(result.execution_barrier_passed)
                self.assertIn(HumanExecutionBarrierFlag.PROVIDER_OUTPUT_UNTRUSTED, result.flags)
                self.assert_all_effects_false(result)

    def test_missing_requested_command_hash_blocks(self):
        result = self.result(requested_command_hash=None, human_decision_binds_to_command_hash=None)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_COMMAND_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_missing_test_runner_control_hash_blocks(self):
        result = self.result(source_test_runner_control_hash=None, human_decision_binds_to_test_runner_control_hash=None)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_TEST_RUNNER_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_missing_sandbox_envelope_hash_blocks(self):
        result = self.result(source_sandbox_envelope_hash=None, human_decision_binds_to_sandbox_envelope_hash=None)

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_SANDBOX_HASH_MISMATCH, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_blocked_policy_status_blocks(self):
        for status in ("BLOCKED_UNSAFE", "MALFORMED_REQUEST", "INCONSISTENT_METADATA", "DENIED"):
            with self.subTest(status=status):
                result = self.result(source_policy_check_status=status)

                self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_INVALID_POLICY_STATUS, result.status)
                self.assertFalse(result.execution_barrier_passed)

    def test_blocked_test_runner_controller_status_blocks(self):
        result = self.result(source_test_runner_control_status="BLOCKED_UNSAFE_TEST_COMMAND")

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_INVALID_TEST_RUNNER_STATUS, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_blocked_sandbox_envelope_status_blocks(self):
        result = self.result(source_sandbox_envelope_status="BLOCKED_UNSAFE_EXECUTION_REQUEST")

        self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_INVALID_SANDBOX_STATUS, result.status)
        self.assertFalse(result.execution_barrier_passed)

    def test_review_required_statuses_do_not_block_by_themselves(self):
        result = self.result(
            source_policy_check_status="REVIEW_REQUIRED",
            source_test_runner_control_status="FOCUSED_TEST_REVIEW_REQUIRED",
            source_sandbox_envelope_status="REVIEW_REQUIRED",
        )

        self.assertEqual(HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED, result.status)
        self.assertTrue(result.execution_barrier_passed)
        self.assert_all_effects_false(result)

    def test_unsafe_risk_flags_block(self):
        unsafe_flags = (
            "UNSAFE_COMMAND",
            "SHELL_COMMAND_BLOCKED",
            "ARBITRARY_COMMAND",
            "NETWORK_ACCESS_BLOCKED",
            "ENV_ACCESS_BLOCKED",
            "API_KEY_ACCESS_BLOCKED",
            "SECRET_OR_TOKEN_PATTERN",
            "BROWSER_RELATED",
            "DOWNLOAD_ENVELOPE_BLOCKED",
            "GITHUB_WRITE",
            "PROVIDER_CALL",
            "APPROVAL_MUTATION",
            "GATE_CHANGE",
            "CONTROL_WRITE_CHANGE",
        )
        for risk_flag in unsafe_flags:
            with self.subTest(risk_flag=risk_flag):
                result = self.result(risk_flags=(risk_flag,))

                self.assertEqual(HumanExecutionBarrierStatus.BLOCKED_UNSAFE_RISK_FLAG, result.status)
                self.assertFalse(result.execution_barrier_passed)
                self.assertIn(HumanExecutionBarrierFlag.UNSAFE_RISK_FLAG_BLOCKED, result.flags)
                self.assert_all_effects_false(result)

    def test_safety_flags_do_not_block(self):
        result = self.result(risk_flags=("NO_NETWORK", "NO_BROWSER", "NO_DOWNLOAD", "NO_PROVIDER_CALL"))

        self.assertEqual(HumanExecutionBarrierStatus.EXECUTION_BARRIER_PASSED, result.status)
        self.assertTrue(result.execution_barrier_passed)
        self.assert_all_effects_false(result)

    def test_barrier_pass_performs_no_execution(self):
        result = self.result()

        self.assertTrue(result.execution_barrier_passed)
        self.assert_all_effects_false(result)

    def test_blocked_result_sets_barrier_passed_false(self):
        result = self.result(human_decision_verdict=HumanDecisionVerdict.REJECT)

        self.assertFalse(result.execution_barrier_passed)
        self.assert_all_effects_false(result)

    def test_input_claims_cannot_enable_effect_or_authority_fields(self):
        result = self.result(authority_claims={"execution_performed": True, "can_execute": True, "approval_created": True, "gate_changed": True})
        replaced = replace(
            result,
            execution_performed=True,
            subprocess_started=True,
            shell_invoked=True,
            command_executed=True,
            test_command_executed=True,
            browser_opened=True,
            download_performed=True,
            file_read=True,
            file_written=True,
            directory_created=True,
            network_called=True,
            env_read=True,
            api_key_loaded=True,
            provider_called=True,
            approval_created=True,
            gate_changed=True,
            control_write_changed=True,
            tool_called=True,
            can_call_tool=True,
            can_execute_arbitrary_command=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )

        self.assert_all_effects_false(result)
        self.assert_all_effects_false(replaced)

    def test_barrier_result_is_frozen(self):
        result = self.result()

        with self.assertRaises(FrozenInstanceError):
            result.status = HumanExecutionBarrierStatus.MALFORMED_REQUEST

    def test_no_runtime_creation_routing_policy_or_dispatch_methods(self):
        result = self.result()
        forbidden_methods = (
            "create_action_proposal",
            "build_action_proposal",
            "create_preview",
            "build_tool_call_preview",
            "register_tool",
            "route_intent",
            "evaluate_local_policy",
            "build_test_runner_control_preview",
            "execute_controlled_test_run",
            "build_download_governance_preview",
            "build_statement_governance_preview",
            "build_browser_governance_check",
            "build_safe_execution_sandbox_envelope",
            "dispatch",
            "create_approval",
            "approve",
            "allow",
            "deny",
        )

        for method_name in forbidden_methods:
            with self.subTest(method_name=method_name):
                self.assertFalse(callable(getattr(result, method_name, None)))

    def test_no_filesystem_reads_or_writes_occur(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            _result = self.result(requested_command=f"python -m unittest tests.test_action_proposal_1a -v {workspace}")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        source = HUMAN_EXECUTION_BARRIER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess",
            "os",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "http.client",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "git",
            "dotenv",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
            "runtime.execution.controlled_test_runner",
            "runtime.schemas.action_proposal",
            "runtime.schemas.tool_call_preview",
            "runtime.schemas.intent_router",
            "runtime.schemas.local_policy_engine",
            "runtime.schemas.test_runner_controller",
            "runtime.schemas.download_manager_governance",
            "runtime.schemas.statement_manager_governance",
            "runtime.schemas.browser_governance",
            "runtime.schemas.safe_execution_sandbox",
            "runtime.schemas.approval_decision",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

        lowered = source.casefold()
        forbidden_terms = (
            "os" + "." + "system",
            "popen",
            "shell=true",
            "eval(",
            "exec(",
            "open(",
            ".read(",
            ".write(",
            "mkdir(",
            "socket",
            "requests",
            "urllib",
            "http.client",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "dotenv",
            "os.environ",
            "getenv(",
            "git push",
            "git commit",
            "git reset",
            "git checkout",
            "dispatch(",
            "invoke(",
            "execute(",
            "approve(",
            "allow(",
            "deny(",
            "run_tests(",
            "start_subprocess(",
            "open_browser(",
            "download(",
            "write_file(",
            "execute_controlled_test_run(",
            "build_action_proposal(",
            "build_tool_call_preview(",
            "route_intent(",
            "evaluate_local_policy(",
            "build_test_runner_control_preview(",
            "build_download_governance_preview(",
            "build_statement_governance_preview(",
            "build_browser_governance_check(",
            "build_safe_execution_sandbox_envelope(",
            "create_action_proposal",
            "create_preview",
            "create_approval",
            "approvaldecision",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

    def request(self, **overrides):
        base = {
            "requested_execution_kind": "TEST_RUN",
            "requested_command": "python -m unittest tests.test_action_proposal_1a -v",
            "requested_command_hash": COMMAND_HASH,
            "source_trust": HumanExecutionSourceTrust.USER_SUPPLIED,
            "human_decision_id": "human-decision-example",
            "human_decision_hash": DECISION_HASH,
            "human_decision_verdict": HumanDecisionVerdict.APPROVE,
            "human_decision_source": HumanDecisionSource.HUMAN_OPERATOR,
            "human_decision_binds_to_command_hash": COMMAND_HASH,
            "human_decision_binds_to_test_runner_control_hash": TEST_RUNNER_HASH,
            "human_decision_binds_to_sandbox_envelope_hash": SANDBOX_HASH,
            "human_decision_binds_to_policy_check_hash": POLICY_HASH,
            "human_decision_binds_to_controlled_execution_request_hash": CONTROLLED_REQUEST_HASH,
            "source_action_proposal_id": "action-proposal-example",
            "source_action_proposal_hash": "1" * 64,
            "source_tool_call_preview_id": "tool-call-preview-example",
            "source_tool_call_preview_hash": "2" * 64,
            "source_intent_route_id": "intent-route-example",
            "source_intent_route_hash": "3" * 64,
            "source_policy_check_id": "local-policy-check-example",
            "source_policy_check_hash": POLICY_HASH,
            "source_policy_check_status": "REVIEW_REQUIRED",
            "source_test_runner_control_id": "test-runner-control-example",
            "source_test_runner_control_hash": TEST_RUNNER_HASH,
            "source_test_runner_control_status": "FOCUSED_TEST_REVIEW_REQUIRED",
            "source_sandbox_envelope_id": "safe-exec-sandbox-example",
            "source_sandbox_envelope_hash": SANDBOX_HASH,
            "source_sandbox_envelope_status": "REVIEW_REQUIRED",
            "source_controlled_execution_request_hash": CONTROLLED_REQUEST_HASH,
            "human_review_required": True,
            "risk_flags": (),
            "authority_claims": None,
        }
        base.update(overrides)
        return HumanExecutionBarrierRequest(**base)

    def result(self, **overrides):
        return evaluate_human_execution_barrier(self.request(**overrides))

    def assert_all_effects_false(self, result):
        fields = (
            "execution_performed",
            "subprocess_started",
            "shell_invoked",
            "command_executed",
            "test_command_executed",
            "browser_opened",
            "download_performed",
            "file_read",
            "file_written",
            "directory_created",
            "network_called",
            "env_read",
            "api_key_loaded",
            "provider_called",
            "approval_created",
            "gate_changed",
            "control_write_changed",
            "tool_called",
            "can_call_tool",
            "can_execute_arbitrary_command",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                self.assertFalse(getattr(result, field_name))


if __name__ == "__main__":
    unittest.main()
