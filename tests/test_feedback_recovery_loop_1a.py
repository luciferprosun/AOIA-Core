from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.orchestration.feedback_recovery_loop import (
    FEEDBACK_RECOVERY_BLOCKED_AGENT_LOOP,
    FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE,
    FEEDBACK_RECOVERY_BLOCKED_AUTHORITY_CLAIM,
    FEEDBACK_RECOVERY_BLOCKED_BROWSER_ACTION,
    FEEDBACK_RECOVERY_BLOCKED_CODEX_AIDER,
    FEEDBACK_RECOVERY_BLOCKED_COMMAND_INJECTION,
    FEEDBACK_RECOVERY_BLOCKED_DUPLICATE_OPTION_ID,
    FEEDBACK_RECOVERY_BLOCKED_EMPTY_OPTIONS,
    FEEDBACK_RECOVERY_BLOCKED_ENV_OR_SECRET,
    FEEDBACK_RECOVERY_BLOCKED_EXPIRED_FAILURE,
    FEEDBACK_RECOVERY_BLOCKED_EXPIRED_PLAN,
    FEEDBACK_RECOVERY_BLOCKED_FAILURE_HASH_MISMATCH,
    FEEDBACK_RECOVERY_BLOCKED_FALLBACK_POLICY,
    FEEDBACK_RECOVERY_BLOCKED_GIT_ACTION,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_FAILURE_KIND,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_OBSERVED_STATUS,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_OPTION_KIND,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_SEVERITY,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_SOURCE_STEP,
    FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME,
    FEEDBACK_RECOVERY_BLOCKED_MCP_TOOL,
    FEEDBACK_RECOVERY_BLOCKED_NON_JSON_SERIALIZABLE,
    FEEDBACK_RECOVERY_BLOCKED_OBSERVATION_HASH_MISMATCH,
    FEEDBACK_RECOVERY_BLOCKED_PACKAGE_INSTALL,
    FEEDBACK_RECOVERY_BLOCKED_PROVIDER_CALL,
    FEEDBACK_RECOVERY_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING,
    FEEDBACK_RECOVERY_BLOCKED_RETRY_POLICY,
    FEEDBACK_RECOVERY_BLOCKED_SELECTED_OPTION_MISSING,
    FEEDBACK_RECOVERY_NON_AUTHORITY,
    FEEDBACK_RECOVERY_OK,
    FEEDBACK_RECOVERY_OPTION_MANUAL_REVIEW,
    FEEDBACK_RECOVERY_OPTION_NEW_EVIDENCE,
    FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH_REASON,
    FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW_REASON,
    RecoveryReviewResult,
    build_feedback_observation,
    build_recovery_failure_report,
    build_recovery_option,
    build_recovery_plan,
    canonical_feedback_recovery_json,
    evaluate_recovery_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "orchestration" / "feedback_recovery_loop.py"


class FeedbackRecoveryLoop1ATests(unittest.TestCase):
    def test_valid_feedback_recovery_review_is_deterministic_inert_and_hash_bound(self):
        evidence = self.evidence()

        first = evaluate_recovery_plan(**evidence, now=15)
        second = evaluate_recovery_plan(**self.evidence(), now=15)

        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(evidence["observation"].observation_hash, first.observation_hash)
        self.assertEqual(evidence["failure"].failure_hash, first.failure_hash)
        self.assertEqual(evidence["plan"].plan_hash, first.plan_hash)
        self.assertEqual(evidence["plan"].recovery_options[0].option_hash, first.selected_option_hash)
        self.assertIn(FEEDBACK_RECOVERY_OK, first.reason_codes)
        self.assertIn(FEEDBACK_RECOVERY_REQUIRES_HUMAN_REVIEW_REASON, first.reason_codes)
        self.assertIn(FEEDBACK_RECOVERY_REQUIRES_CONTROLLED_PATH_REASON, first.reason_codes)
        self.assertIn(FEEDBACK_RECOVERY_OPTION_NEW_EVIDENCE, first.recovery_codes)
        self.assertIn(FEEDBACK_RECOVERY_OPTION_MANUAL_REVIEW, first.recovery_codes)
        self.assertIn(FEEDBACK_RECOVERY_NON_AUTHORITY, first.recovery_codes)
        self.assert_metadata_only(first.to_dict())

    def test_hashes_change_when_bound_evidence_changes(self):
        observation = self.observation(observer="tester")
        changed_observation = self.observation(observer="other")
        self.assertNotEqual(observation.observation_hash, changed_observation.observation_hash)

        failure = self.failure(observation, severity="medium")
        changed_failure = self.failure(observation, severity="high")
        self.assertNotEqual(failure.failure_hash, changed_failure.failure_hash)

        option = self.option("new-evidence", "request_new_evidence")
        changed_option = self.option("new-evidence", "ask_human_review")
        self.assertNotEqual(option.option_hash, changed_option.option_hash)

        plan = self.plan(failure, (option,), selected_option_id=option.option_id)
        changed_plan = self.plan(failure, (option,), selected_option_id=None)
        self.assertNotEqual(plan.plan_hash, changed_plan.plan_hash)

        first = evaluate_recovery_plan(observation=observation, failure=failure, plan=plan, now=15)
        second = evaluate_recovery_plan(observation=changed_observation, failure=self.failure(changed_observation), plan=self.plan(self.failure(changed_observation), (option,), selected_option_id=option.option_id), now=15)
        self.assertNotEqual(first.review_hash, second.review_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_feedback_recovery_json({"b": 1, "a": ("x",)}),
            canonical_feedback_recovery_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("nan")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_feedback_recovery_json(value)

    def test_unknown_labels_and_invalid_severity_fail_closed(self):
        cases = (
            ({**self.evidence(), "observation": self.observation(source_step="step_99_future")}, FEEDBACK_RECOVERY_BLOCKED_INVALID_SOURCE_STEP),
            ({**self.evidence(), "observation": self.observation(observed_status="auto_fixed")}, FEEDBACK_RECOVERY_BLOCKED_INVALID_OBSERVED_STATUS),
            ({**self.evidence(), "failure": self.failure(self.observation(), failure_kind="provider_fallback")}, FEEDBACK_RECOVERY_BLOCKED_INVALID_FAILURE_KIND),
            ({**self.evidence(), "failure": self.failure(self.observation(), severity="urgent")}, FEEDBACK_RECOVERY_BLOCKED_INVALID_SEVERITY),
            (self.evidence_with_option(self.option("bad", "execute_recovery")), FEEDBACK_RECOVERY_BLOCKED_INVALID_OPTION_KIND),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                altered = self.rebind(altered)
                result = evaluate_recovery_plan(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_empty_duplicate_and_missing_selected_options_fail_closed(self):
        observation = self.observation()
        failure = self.failure(observation)
        option = self.option("new-evidence", "request_new_evidence")
        duplicate = self.option("new-evidence", "ask_human_review")
        cases = (
            (self.plan(failure, (), selected_option_id=None), FEEDBACK_RECOVERY_BLOCKED_EMPTY_OPTIONS),
            (self.plan(failure, (option, duplicate), selected_option_id=option.option_id), FEEDBACK_RECOVERY_BLOCKED_DUPLICATE_OPTION_ID),
            (self.plan(failure, (option,), selected_option_id="missing"), FEEDBACK_RECOVERY_BLOCKED_SELECTED_OPTION_MISSING),
        )
        for plan, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_recovery_plan(observation=observation, failure=failure, plan=plan, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_retry_fallback_policy_and_time_evidence_fail_closed(self):
        cases = (
            ({**self.evidence(), "plan": self.plan(self.failure(self.observation()), (self.option("new-evidence", "request_new_evidence"),), retry_policy="automatic_retry")}, FEEDBACK_RECOVERY_BLOCKED_RETRY_POLICY, 15),
            ({**self.evidence(), "plan": self.plan(self.failure(self.observation()), (self.option("new-evidence", "request_new_evidence"),), fallback_policy="auto_fallback")}, FEEDBACK_RECOVERY_BLOCKED_FALLBACK_POLICY, 15),
            (self.evidence(), FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME, None),
            (self.evidence(), FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME, -1),
            ({**self.evidence(), "observation": self.observation(observed_at=20)}, FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME, 15),
            ({**self.evidence(), "failure": self.failure(self.observation(), reported_at=20, expires_at=40)}, FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME, 15),
            ({**self.evidence(), "plan": self.plan(self.failure(self.observation()), (self.option("new-evidence", "request_new_evidence"),), created_at=20, expires_at=100)}, FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME, 15),
            ({**self.evidence(), "failure": self.failure(self.observation(), reported_at=1, expires_at=12)}, FEEDBACK_RECOVERY_BLOCKED_EXPIRED_FAILURE, 15),
            ({**self.evidence(), "plan": self.plan(self.failure(self.observation()), (self.option("new-evidence", "request_new_evidence"),), created_at=1, expires_at=12)}, FEEDBACK_RECOVERY_BLOCKED_EXPIRED_PLAN, 15),
        )
        for altered, reason, now in cases:
            with self.subTest(reason=reason):
                altered = self.rebind(altered)
                result = evaluate_recovery_plan(**altered, now=now)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_invalid_hash_and_cross_hash_mismatches_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "observation": {**evidence["observation"].to_dict(), "source_result_hash": "bad"}}, FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH),
            ({**evidence, "failure": {**evidence["failure"].to_dict(), "failed_evidence_hashes": ("bad",)}}, FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH),
            ({**evidence, "plan": {**evidence["plan"].to_dict(), "plan_hash": "0" * 64}}, FEEDBACK_RECOVERY_BLOCKED_INVALID_HASH),
            ({**evidence, "failure": {**evidence["failure"].to_dict(), "observation_hash": "3" * 64}}, FEEDBACK_RECOVERY_BLOCKED_OBSERVATION_HASH_MISMATCH),
            ({**evidence, "plan": {**evidence["plan"].to_dict(), "failure_hash": "4" * 64}}, FEEDBACK_RECOVERY_BLOCKED_FAILURE_HASH_MISMATCH),
            ({**evidence, "failure": {**evidence["failure"].to_dict(), "expires_at": 1}}, FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME),
            ({**evidence, "plan": {**evidence["plan"].to_dict(), "expires_at": 1}}, FEEDBACK_RECOVERY_BLOCKED_INVALID_TIME),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_recovery_plan(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_dangerous_smuggling_fails_closed(self):
        cases = (
            ("command", "bash -lc whoami", FEEDBACK_RECOVERY_BLOCKED_COMMAND_INJECTION),
            ("provider_call", "provider_call", FEEDBACK_RECOVERY_BLOCKED_PROVIDER_CALL),
            ("git_action", "git_push", FEEDBACK_RECOVERY_BLOCKED_GIT_ACTION),
            ("package_install", "pip install thing", FEEDBACK_RECOVERY_BLOCKED_PACKAGE_INSTALL),
            ("browser_action", "playwright click", FEEDBACK_RECOVERY_BLOCKED_BROWSER_ACTION),
            ("mcp_tool", "call_tool", FEEDBACK_RECOVERY_BLOCKED_MCP_TOOL),
            ("codex", "codex run", FEEDBACK_RECOVERY_BLOCKED_CODEX_AIDER),
            ("agent_loop", "create_task", FEEDBACK_RECOVERY_BLOCKED_AGENT_LOOP),
            ("retry_now", "automatic_retry", FEEDBACK_RECOVERY_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING),
            ("api_key", "secret-token", FEEDBACK_RECOVERY_BLOCKED_ENV_OR_SECRET),
            ("approved", True, FEEDBACK_RECOVERY_BLOCKED_AUTHORITY_CLAIM),
            ("unknown_metadata", "ambiguous", FEEDBACK_RECOVERY_BLOCKED_AMBIGUOUS_EVIDENCE),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                evidence = self.evidence()
                plan_data = evidence["plan"].to_dict()
                plan_data[key] = value
                result = evaluate_recovery_plan(observation=evidence["observation"], failure=evidence["failure"], plan=plan_data, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_non_json_serializable_evidence_fails_closed(self):
        evidence = self.evidence()
        data = evidence["plan"].to_dict()
        data["bad"] = object()

        result = evaluate_recovery_plan(observation=evidence["observation"], failure=evidence["failure"], plan=data, now=15)

        self.assertTrue(result.blocked)
        self.assertIn(FEEDBACK_RECOVERY_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_review_result_cannot_be_forged_into_authority(self):
        result = evaluate_recovery_plan(**self.evidence(), now=15)
        forced = replace(
            result,
            recovery_allowed=True,
            retry_allowed=True,
            fallback_allowed=True,
            execution_allowed=True,
            dispatch_allowed=True,
            requires_human_review=False,
            requires_controlled_path=False,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            can_recover=True,
            can_execute=True,
            can_dispatch=True,
            can_retry=True,
            can_fallback=True,
            can_stream=True,
            can_call_tool=True,
            can_call_provider=True,
            can_call_mcp=True,
            approval_created=True,
            dispatcher_created=True,
            recovery_executed=True,
            selected_option_executed=True,
            retry_started=True,
            fallback_started=True,
            streaming_started=True,
            process_started=True,
            network_called=True,
            provider_called=True,
            mcp_called=True,
            browser_opened=True,
            package_manager_called=True,
            git_action_performed=True,
            agent_loop_started=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in (
            "approve",
            "authorize",
            "dispatch",
            "execute",
            "run",
            "retry",
            "fallback",
            "recover",
            "worker",
            "create_task",
            "call_tool",
            "call_provider",
            "read_resource",
            "write",
            "push",
            "commit",
            "provider_call",
            "gate_pass",
            "grant_permission",
            "start_agent_loop",
        ):
            self.assertFalse(hasattr(result, method_name))

    def test_static_surface_has_no_runtime_execution_or_future_steps(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        for forbidden_import in (
            "asyncio",
            "threading",
            "multiprocessing",
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "runtime.integration_boundaries.mcp_boundary",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.execution",
            "runtime.git_ops",
            "runtime.package_ops.controlled_package_install",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_call in (
            "asyncio.run",
            "asyncio.create_task",
            "asyncio.gather",
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
        ):
            self.assertNotIn(forbidden_call, scan.calls)
        for forbidden_text in (
            "shell=true",
            "os.environ",
            "getenv",
            "step 52",
            "step 53",
            "step 54",
        ):
            self.assertNotIn(forbidden_text, source)

    def evidence(self):
        observation = self.observation()
        failure = self.failure(observation)
        options = (
            self.option("new-evidence", "request_new_evidence"),
            self.option("manual-review", "ask_human_review"),
        )
        plan = self.plan(failure, options, selected_option_id=options[0].option_id)
        return {"observation": observation, "failure": failure, "plan": plan}

    def rebind(self, evidence):
        observation = evidence["observation"]
        failure = evidence["failure"]
        plan = evidence["plan"]
        if not isinstance(observation, dict) and not isinstance(failure, dict):
            if failure.observation_hash != observation.observation_hash:
                failure = self.failure(observation, failure_kind=failure.failure_kind, severity=failure.severity, reported_at=failure.reported_at, expires_at=failure.expires_at)
        if not isinstance(failure, dict) and not isinstance(plan, dict):
            if plan.failure_hash != failure.failure_hash:
                plan = self.plan(failure, plan.recovery_options, selected_option_id=plan.selected_option_id, retry_policy=plan.retry_policy, fallback_policy=plan.fallback_policy, created_at=plan.created_at, expires_at=plan.expires_at)
        return {"observation": observation, "failure": failure, "plan": plan}

    def evidence_with_option(self, option):
        observation = self.observation()
        failure = self.failure(observation)
        return {"observation": observation, "failure": failure, "plan": self.plan(failure, (option,), selected_option_id=option.option_id)}

    def observation(self, *, source_step="step_50_async_io_orchestration", observed_status="failed", observer="tester", observed_at=10):
        return build_feedback_observation(
            observation_id="obs",
            source_step=source_step,
            source_result_hash="1" * 64,
            observed_status=observed_status,
            observed_codes=("ASYNC_IO_ORCHESTRATION_BLOCKED_BY_DEPENDENCY",),
            observed_at=observed_at,
            observer=observer,
        )

    def failure(self, observation, *, failure_kind="validation_failure", severity="medium", reported_at=10, expires_at=100):
        return build_recovery_failure_report(
            failure_id="failure",
            observation_hash=observation.observation_hash,
            failure_kind=failure_kind,
            failed_operation_id="operation",
            failed_evidence_hashes=("2" * 64,),
            failure_summary="Validation metadata did not match expected evidence.",
            severity=severity,
            reported_at=reported_at,
            expires_at=expires_at,
        )

    def option(self, option_id, option_kind):
        return build_recovery_option(
            option_id=option_id,
            option_kind=option_kind,
            target_operation_id="operation",
            required_new_evidence_hashes=("3" * 64,),
            blocked_until_human_review=True,
            recovery_summary="Collect fresh evidence for manual review.",
        )

    def plan(
        self,
        failure,
        options,
        *,
        selected_option_id=None,
        retry_policy="none",
        fallback_policy="manual_review_required",
        created_at=10,
        expires_at=100,
    ):
        return build_recovery_plan(
            plan_id="plan",
            failure_hash=failure.failure_hash,
            recovery_options=tuple(options),
            selected_option_id=selected_option_id,
            retry_policy=retry_policy,
            fallback_policy=fallback_policy,
            created_at=created_at,
            expires_at=expires_at,
        )

    def assert_metadata_only(self, data):
        for field in (
            "recovery_allowed",
            "retry_allowed",
            "fallback_allowed",
            "execution_allowed",
            "dispatch_allowed",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_recover",
            "can_execute",
            "can_dispatch",
            "can_retry",
            "can_fallback",
            "can_stream",
            "can_call_tool",
            "can_call_provider",
            "can_call_mcp",
            "approval_created",
            "dispatcher_created",
            "recovery_executed",
            "selected_option_executed",
            "retry_started",
            "fallback_started",
            "streaming_started",
            "process_started",
            "network_called",
            "provider_called",
            "mcp_called",
            "browser_opened",
            "package_manager_called",
            "git_action_performed",
            "agent_loop_started",
        ):
            self.assertIs(data[field], False)
        self.assertIs(data["requires_human_review"], True)
        self.assertIs(data["requires_controlled_path"], True)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(call_name(node.func))
    return type("Scan", (), {"imports": tuple(sorted(imports)), "calls": tuple(sorted(calls))})()


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


if __name__ == "__main__":
    unittest.main()
