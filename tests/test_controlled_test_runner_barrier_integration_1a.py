from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

from runtime.execution.controlled_test_runner import (
    ControlledTestExecutionFlag,
    ControlledTestExecutionRequest,
    ControlledTestExecutionStatus,
    ControlledTestSourceTrust,
    execute_controlled_test_run,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_TEST_RUNNER = REPO_ROOT / "runtime" / "execution" / "controlled_test_runner.py"
TEST_RUNNER_HASH = "a" * 64
SANDBOX_HASH = "b" * 64
POLICY_HASH = "c" * 64
BARRIER_HASH = "d" * 64
HUMAN_DECISION_HASH = "e" * 64


class ControlledTestRunnerBarrierIntegration1ATests(unittest.TestCase):
    def test_no_preexisting_duplicate_barrier_integration_modules(self):
        matches = sorted(
            path
            for path in (REPO_ROOT / "runtime").rglob("*barrier*test*")
            if path.is_file() and path.suffix == ".py"
        )

        self.assertEqual([], matches)

    def test_valid_hash_bound_barrier_permits_focused_unittest_execution(self):
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="ok", stderr="")
        with patch("runtime.execution.controlled_test_runner.subprocess.run", return_value=completed) as run_mock:
            result = self.execute("python -m unittest tests.test_action_proposal_1a -v")

        self.assertEqual(ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED, result.status)
        self.assertTrue(result.barrier_verified)
        self.assertTrue(result.barrier_hashes_matched)
        self.assertIn(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_VERIFIED, result.flags)
        self.assertIn(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_HASH_BOUND, result.flags)
        self.assertEqual((sys.executable, "-m", "unittest", "tests.test_action_proposal_1a", "-v"), run_mock.call_args.args[0])
        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assert_success_execution_booleans(result)
        self.assert_authority_false(result)

    def test_valid_hash_bound_barrier_permits_unittest_discover_execution(self):
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="discover ok", stderr="")
        with patch("runtime.execution.controlled_test_runner.subprocess.run", return_value=completed) as run_mock:
            result = self.execute("python -m unittest discover -s tests -v")

        self.assertEqual(ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED, result.status)
        self.assertTrue(result.barrier_verified)
        self.assertEqual((sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"), run_mock.call_args.args[0])
        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assert_success_execution_booleans(result)
        self.assert_authority_false(result)

    def test_valid_hash_bound_barrier_permits_compileall_execution(self):
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="compile ok", stderr="")
        with patch("runtime.execution.controlled_test_runner.subprocess.run", return_value=completed) as run_mock:
            result = self.execute("python -m compileall runtime tests")

        self.assertEqual(ControlledTestExecutionStatus.CONTROLLED_TEST_EXECUTION_COMPLETED, result.status)
        self.assertTrue(result.barrier_verified)
        self.assertEqual((sys.executable, "-m", "compileall", "runtime", "tests"), run_mock.call_args.args[0])
        self.assertIs(run_mock.call_args.kwargs["shell"], False)
        self.assert_success_execution_booleans(result)
        self.assert_authority_false(result)

    def test_missing_barrier_id_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(source_execution_barrier_id=None),
            ControlledTestExecutionStatus.BLOCKED_MISSING_EXECUTION_BARRIER,
        )

    def test_missing_barrier_hash_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(source_execution_barrier_hash=None),
            ControlledTestExecutionStatus.BLOCKED_MISSING_EXECUTION_BARRIER,
        )

    def test_barrier_passed_false_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(source_execution_barrier_passed=False),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_NOT_PASSED,
        )

    def test_barrier_status_not_passed_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(source_execution_barrier_status="BLOCKED_REJECTED_BY_HUMAN"),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_NOT_PASSED,
        )

    def test_barrier_command_hash_mismatch_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(barrier_bound_command_hash="f" * 64),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH,
        )

    def test_barrier_test_runner_hash_mismatch_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(barrier_bound_test_runner_control_hash="f" * 64),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH,
        )

    def test_barrier_sandbox_hash_mismatch_blocks_execution(self):
        self.assert_barrier_blocked(
            self.execute(barrier_bound_sandbox_envelope_hash="f" * 64),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH,
        )

    def test_barrier_policy_hash_mismatch_blocks_when_policy_hash_is_present(self):
        self.assert_barrier_blocked(
            self.execute(barrier_bound_policy_check_hash="f" * 64),
            ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_HASH_MISMATCH,
        )

    def test_missing_human_decision_metadata_blocks_as_invalid_barrier(self):
        for overrides in (
            {"source_human_decision_id": None},
            {"source_human_decision_hash": None},
            {"source_human_decision_hash": "not-a-sha"},
        ):
            with self.subTest(overrides=overrides):
                self.assert_barrier_blocked(
                    self.execute(**overrides),
                    ControlledTestExecutionStatus.BLOCKED_EXECUTION_BARRIER_STALE_OR_INVALID,
                )

    def test_barrier_cannot_override_unsupported_command(self):
        result = self.execute("python -m pytest tests -v")

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_UNSUPPORTED_COMMAND, result.status)
        self.assert_blocked_execution_booleans(result)

    def test_barrier_cannot_override_unsafe_command(self):
        result = self.execute("rm -rf /")

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_UNSAFE_COMMAND, result.status)
        self.assert_blocked_execution_booleans(result)

    def test_barrier_cannot_override_untrusted_provider_source(self):
        result = self.execute(source_trust=ControlledTestSourceTrust.UNTRUSTED_PROVIDER_OUTPUT)

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_UNTRUSTED_SOURCE, result.status)
        self.assert_blocked_execution_booleans(result)

    def test_barrier_cannot_override_missing_sandbox_metadata(self):
        result = self.execute(source_sandbox_envelope_id=None, source_sandbox_envelope_hash=None)

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_INVALID_SANDBOX_ENVELOPE, result.status)
        self.assert_blocked_execution_booleans(result)

    def test_barrier_cannot_override_missing_test_runner_preview_metadata(self):
        result = self.execute(source_test_runner_control_id=None, source_test_runner_control_hash=None)

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_INVALID_TEST_CONTROLLER_PREVIEW, result.status)
        self.assert_blocked_execution_booleans(result)

    def test_direct_public_execution_without_barrier_no_longer_executes(self):
        with patch("runtime.execution.controlled_test_runner.subprocess.run") as run_mock:
            result = execute_controlled_test_run(
                ControlledTestExecutionRequest(
                    requested_command="python -m unittest tests.test_action_proposal_1a -v",
                    repo_root=str(REPO_ROOT),
                    explicit_operator_execution_confirmed=True,
                    source_trust=ControlledTestSourceTrust.USER_SUPPLIED,
                    source_test_runner_control_id="test-runner-control-example",
                    source_test_runner_control_hash=TEST_RUNNER_HASH,
                    source_test_runner_control_status="FOCUSED_TEST_REVIEW_REQUIRED",
                    source_sandbox_envelope_id="safe-exec-sandbox-example",
                    source_sandbox_envelope_hash=SANDBOX_HASH,
                    source_sandbox_envelope_status="REVIEW_REQUIRED",
                    source_policy_check_id="local-policy-check-example",
                    source_policy_check_hash=POLICY_HASH,
                )
            )

        self.assertEqual(ControlledTestExecutionStatus.BLOCKED_MISSING_EXECUTION_BARRIER, result.status)
        self.assertFalse(run_mock.called)
        self.assert_blocked_execution_booleans(result)

    def test_successful_controlled_execution_sets_only_narrow_execution_booleans_true(self):
        completed = subprocess.CompletedProcess(args=(sys.executable,), returncode=0, stdout="ok", stderr="")
        with patch("runtime.execution.controlled_test_runner.subprocess.run", return_value=completed):
            result = self.execute()

        self.assert_success_execution_booleans(result)
        self.assertFalse(result.shell_invoked)
        self.assert_authority_false(result)

    def test_blocked_barrier_cases_keep_execution_booleans_false(self):
        result = self.execute(source_execution_barrier_passed=False)

        self.assert_blocked_execution_booleans(result)
        self.assert_authority_false(result)

    def test_static_controlled_runner_barrier_integration_has_no_forbidden_capability_expansion(self):
        source = CONTROLLED_TEST_RUNNER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        self.assertIn("subprocess", imports)
        self.assertEqual(0, source.casefold().count("subprocess.run("))
        self.assertEqual(1, source.casefold().count("run_bounded_subprocess("))
        self.assertIn("shell=False", source)
        forbidden_modules = {
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
            "runtime.execution.human_execution_barrier",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
        }
        for module_name in imports:
            with self.subTest(module_name=module_name):
                self.assertFalse(
                    any(module_name == forbidden or module_name.startswith(forbidden + ".") for forbidden in forbidden_modules)
                )

        lowered = source.casefold()
        forbidden_terms = (
            "shell=true",
            "popen(",
            "os" + "." + "system(",
            "eval(",
            "exec(",
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
            "g" + "it push",
            "g" + "it commit",
            "g" + "it reset",
            "g" + "it checkout",
            "evaluate_human_execution_barrier(",
            "approvaldecision",
            "build_action_proposal(",
            "build_tool_call_preview(",
            "route_intent(",
            "evaluate_local_policy(",
            "build_safe_execution_sandbox_envelope(",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

    def request(self, command="python -m unittest tests.test_action_proposal_1a -v", **overrides):
        command_hash = self.command_hash(command)
        base = {
            "requested_command": command,
            "repo_root": str(REPO_ROOT),
            "explicit_operator_execution_confirmed": True,
            "timeout_seconds": 90,
            "max_output_bytes": 20000,
            "source_trust": ControlledTestSourceTrust.USER_SUPPLIED,
            "source_test_runner_control_id": "test-runner-control-example",
            "source_test_runner_control_hash": TEST_RUNNER_HASH,
            "source_test_runner_control_status": "FOCUSED_TEST_REVIEW_REQUIRED",
            "source_sandbox_envelope_id": "safe-exec-sandbox-example",
            "source_sandbox_envelope_hash": SANDBOX_HASH,
            "source_sandbox_envelope_status": "REVIEW_REQUIRED",
            "source_policy_check_id": "local-policy-check-example",
            "source_policy_check_hash": POLICY_HASH,
            "source_execution_barrier_id": "human-exec-barrier-example",
            "source_execution_barrier_hash": BARRIER_HASH,
            "source_execution_barrier_status": "EXECUTION_BARRIER_PASSED",
            "source_execution_barrier_passed": True,
            "barrier_bound_command_hash": command_hash,
            "barrier_bound_test_runner_control_hash": TEST_RUNNER_HASH,
            "barrier_bound_sandbox_envelope_hash": SANDBOX_HASH,
            "barrier_bound_policy_check_hash": POLICY_HASH,
            "source_human_decision_id": "human-decision-example",
            "source_human_decision_hash": HUMAN_DECISION_HASH,
            "human_review_required": True,
            "risk_flags": (),
        }
        base.update(overrides)
        return ControlledTestExecutionRequest(**base)

    def execute(self, command="python -m unittest tests.test_action_proposal_1a -v", **overrides):
        return execute_controlled_test_run(self.request(command, **overrides))

    def command_hash(self, command: str) -> str:
        normalized = " ".join(command.strip().split()).casefold()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def assert_barrier_blocked(self, result, expected_status):
        self.assertEqual(expected_status, result.status)
        self.assertFalse(result.barrier_verified)
        self.assertFalse(result.barrier_hashes_matched)
        self.assertIn(ControlledTestExecutionFlag.HUMAN_EXECUTION_BARRIER_REQUIRED, result.flags)
        self.assertIn(ControlledTestExecutionFlag.NO_BARRIER_BYPASS, result.flags)
        self.assert_blocked_execution_booleans(result)
        self.assert_authority_false(result)

    def assert_success_execution_booleans(self, result):
        self.assertTrue(result.execution_performed)
        self.assertTrue(result.subprocess_started)
        self.assertTrue(result.command_executed)
        self.assertTrue(result.test_command_executed)
        self.assertFalse(result.shell_invoked)

    def assert_blocked_execution_booleans(self, result):
        self.assertFalse(result.execution_performed)
        self.assertFalse(result.subprocess_started)
        self.assertFalse(result.shell_invoked)
        self.assertFalse(result.command_executed)
        self.assertFalse(result.test_command_executed)

    def assert_authority_false(self, result):
        fields = (
            "can_execute_arbitrary_command",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
            "provider_called",
            "approval_created",
            "gate_changed",
            "control_write_changed",
            "browser_opened",
            "download_performed",
            "network_called_by_aoia",
            "env_read",
            "api_key_loaded",
        )
        for field_name in fields:
            with self.subTest(field_name=field_name):
                self.assertFalse(getattr(result, field_name))


if __name__ == "__main__":
    unittest.main()
