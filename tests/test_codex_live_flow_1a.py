from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.live_flows.codex_live_flow import (
    CODEX_LIVE_FLOW_BLOCKED_AIDER_INVOCATION,
    CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE,
    CODEX_LIVE_FLOW_BLOCKED_AOIA_CODEX_INVOCATION,
    CODEX_LIVE_FLOW_BLOCKED_AGENT_LOOP,
    CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM,
    CODEX_LIVE_FLOW_BLOCKED_BROWSER_ACTION,
    CODEX_LIVE_FLOW_BLOCKED_CHANGED_FILE_OUT_OF_SCOPE,
    CODEX_LIVE_FLOW_BLOCKED_CODEX_INVOCATION_SMUGGLING,
    CODEX_LIVE_FLOW_BLOCKED_COMMAND_INJECTION,
    CODEX_LIVE_FLOW_BLOCKED_COMMIT_OR_PUSH,
    CODEX_LIVE_FLOW_BLOCKED_ENV_OR_SECRET,
    CODEX_LIVE_FLOW_BLOCKED_EXPIRED_HANDOFF,
    CODEX_LIVE_FLOW_BLOCKED_EXPIRED_OUTPUT,
    CODEX_LIVE_FLOW_BLOCKED_EXPIRED_REQUEST,
    CODEX_LIVE_FLOW_BLOCKED_FORBIDDEN_FILE,
    CODEX_LIVE_FLOW_BLOCKED_GIT_ACTION,
    CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH,
    CODEX_LIVE_FLOW_BLOCKED_HUMAN_OPERATOR_REQUIRED,
    CODEX_LIVE_FLOW_BLOCKED_INVALID_EXTERNAL_RUN_MODE,
    CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH,
    CODEX_LIVE_FLOW_BLOCKED_INVALID_REQUEST,
    CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME,
    CODEX_LIVE_FLOW_BLOCKED_MCP_TOOL,
    CODEX_LIVE_FLOW_BLOCKED_NON_JSON_SERIALIZABLE,
    CODEX_LIVE_FLOW_BLOCKED_PACKAGE_INSTALL,
    CODEX_LIVE_FLOW_BLOCKED_PATCH_APPLICATION,
    CODEX_LIVE_FLOW_BLOCKED_PROVIDER_CALL,
    CODEX_LIVE_FLOW_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING,
    CODEX_LIVE_FLOW_BLOCKED_TEST_EXECUTION,
    CODEX_LIVE_FLOW_BLOCKED_WRITE_CLAIM,
    CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED,
    CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY,
    CODEX_LIVE_FLOW_NON_AUTHORITY,
    CODEX_LIVE_FLOW_OK,
    CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW,
    CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH_REASON,
    CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW_REASON,
    build_codex_external_run_observation,
    build_codex_live_flow_handoff_packet,
    build_codex_live_flow_request,
    build_codex_returned_output_evidence,
    canonical_codex_live_flow_json,
    evaluate_codex_live_flow,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "live_flows" / "codex_live_flow.py"


class CodexLiveFlow1ATests(unittest.TestCase):
    def test_valid_live_flow_review_is_deterministic_inert_and_hash_bound(self):
        evidence = self.evidence()

        first = evaluate_codex_live_flow(**evidence, now=15)
        second = evaluate_codex_live_flow(**self.evidence(), now=15)

        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(evidence["request"].request_hash, first.request_hash)
        self.assertEqual(evidence["handoff"].handoff_hash, first.handoff_hash)
        self.assertEqual(evidence["observation"].observation_hash, first.observation_hash)
        self.assertEqual(evidence["output"].output_hash, first.output_hash)
        self.assertEqual(("runtime/live_flows/codex_live_flow.py",), first.claimed_changed_files)
        self.assertIn(CODEX_LIVE_FLOW_OK, first.reason_codes)
        self.assertIn(CODEX_LIVE_FLOW_REQUIRES_HUMAN_REVIEW_REASON, first.reason_codes)
        self.assertIn(CODEX_LIVE_FLOW_REQUIRES_CONTROLLED_PATH_REASON, first.reason_codes)
        self.assertIn(CODEX_LIVE_FLOW_HUMAN_MEDIATED_ONLY, first.live_flow_codes)
        self.assertIn(CODEX_LIVE_FLOW_EXTERNAL_OUTPUT_UNTRUSTED, first.live_flow_codes)
        self.assertIn(CODEX_LIVE_FLOW_REQUIRES_BOUNDARY_REVIEW, first.live_flow_codes)
        self.assertIn(CODEX_LIVE_FLOW_NON_AUTHORITY, first.live_flow_codes)
        self.assert_metadata_only(first.to_dict())

    def test_hashes_change_when_bound_evidence_changes(self):
        request = self.request(task_goal="Record returned metadata.")
        changed_request = self.request(task_goal="Record returned metadata for review.")
        self.assertNotEqual(request.request_hash, changed_request.request_hash)

        handoff = self.handoff(request, handoff_summary="Manual transfer only.")
        changed_handoff = self.handoff(request, handoff_summary="Manual transfer and report only.")
        self.assertNotEqual(handoff.handoff_hash, changed_handoff.handoff_hash)

        observation = self.observation(request, handoff, human_operator="tester")
        changed_observation = self.observation(request, handoff, human_operator="reviewer")
        self.assertNotEqual(observation.observation_hash, changed_observation.observation_hash)

        output = self.output(request, handoff, observation, output_summary="Returned summary.")
        changed_output = self.output(request, handoff, observation, output_summary="Returned summary for review.")
        self.assertNotEqual(output.output_hash, changed_output.output_hash)

        first = evaluate_codex_live_flow(request=request, handoff=handoff, observation=observation, output=output, now=15)
        second_request = changed_request
        second_handoff = self.handoff(second_request)
        second_observation = self.observation(second_request, second_handoff)
        second_output = self.output(second_request, second_handoff, second_observation)
        second = evaluate_codex_live_flow(request=second_request, handoff=second_handoff, observation=second_observation, output=second_output, now=15)
        self.assertNotEqual(first.review_hash, second.review_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_codex_live_flow_json({"b": 1, "a": ("x",)}),
            canonical_codex_live_flow_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("nan")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_codex_live_flow_json(value)

    def test_cross_hash_and_label_mismatches_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "request_hash": "9" * 64}}, CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH),
            ({**evidence, "observation": {**evidence["observation"].to_dict(), "handoff_hash": "8" * 64}}, CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH),
            ({**evidence, "output": {**evidence["output"].to_dict(), "observation_hash": "7" * 64}}, CODEX_LIVE_FLOW_BLOCKED_HASH_MISMATCH),
            ({**evidence, "request": {**evidence["request"].to_dict(), "step_id": "step_53_local_agent_loop"}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_REQUEST),
            ({**evidence, "observation": {**evidence["observation"].to_dict(), "external_run_mode": "aoia_runs_cli"}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_EXTERNAL_RUN_MODE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_codex_live_flow(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_time_and_required_human_controls_fail_closed(self):
        evidence = self.evidence()
        cases = (
            (evidence, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, None),
            (evidence, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, -1),
            ({**evidence, "request": self.request(requested_at=20, expires_at=100)}, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "request": self.request(requested_at=1, expires_at=12)}, CODEX_LIVE_FLOW_BLOCKED_EXPIRED_REQUEST, 15),
            ({**evidence, "handoff": self.handoff(evidence["request"], created_at=1, expires_at=12)}, CODEX_LIVE_FLOW_BLOCKED_EXPIRED_HANDOFF, 15),
            ({**evidence, "output": self.output(evidence["request"], evidence["handoff"], evidence["observation"], returned_at=1, expires_at=12)}, CODEX_LIVE_FLOW_BLOCKED_EXPIRED_OUTPUT, 15),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "expires_at": 1}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "output": {**evidence["output"].to_dict(), "expires_at": 1}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "observation": {**evidence["observation"].to_dict(), "external_run_started_at": 20, "external_run_reported_at": 10}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "human_operator_required": False}}, CODEX_LIVE_FLOW_BLOCKED_HUMAN_OPERATOR_REQUIRED, 15),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "codex_invocation_allowed_by_aoia": True}}, CODEX_LIVE_FLOW_BLOCKED_AOIA_CODEX_INVOCATION, 15),
        )
        for altered, reason, now in cases:
            with self.subTest(reason=reason):
                result = evaluate_codex_live_flow(**altered, now=now)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_paths_and_changed_file_claims_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "output": {**evidence["output"].to_dict(), "changed_files_claimed": ("runtime/other.py",)}}, CODEX_LIVE_FLOW_BLOCKED_CHANGED_FILE_OUT_OF_SCOPE),
            ({**evidence, "output": {**evidence["output"].to_dict(), "changed_files_claimed": ("runtime/secrets.py",)}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH),
            ({**evidence, "output": {**evidence["output"].to_dict(), "changed_files_claimed": ("runtime/blocked.py",)}}, CODEX_LIVE_FLOW_BLOCKED_FORBIDDEN_FILE),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "allowed_files": ("../escape.py",)}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "allowed_files": (".git/config",)}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH),
            ({**evidence, "handoff": {**evidence["handoff"].to_dict(), "allowed_files": ("runtime/.env",)}}, CODEX_LIVE_FLOW_BLOCKED_INVALID_PATH),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_codex_live_flow(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_dangerous_smuggling_fails_closed(self):
        cases = (
            ("command", "bash -lc whoami", CODEX_LIVE_FLOW_BLOCKED_COMMAND_INJECTION),
            ("codex_cli", "run_codex", CODEX_LIVE_FLOW_BLOCKED_CODEX_INVOCATION_SMUGGLING),
            ("aider", "invoke_aider", CODEX_LIVE_FLOW_BLOCKED_AIDER_INVOCATION),
            ("apply_patch", "patch_apply", CODEX_LIVE_FLOW_BLOCKED_PATCH_APPLICATION),
            ("write_files", "can_write", CODEX_LIVE_FLOW_BLOCKED_WRITE_CLAIM),
            ("test_execution", "can_run_tests", CODEX_LIVE_FLOW_BLOCKED_TEST_EXECUTION),
            ("git_push", "can_push", CODEX_LIVE_FLOW_BLOCKED_COMMIT_OR_PUSH),
            ("provider_call", "provider_call", CODEX_LIVE_FLOW_BLOCKED_PROVIDER_CALL),
            ("git_action", "git_action", CODEX_LIVE_FLOW_BLOCKED_GIT_ACTION),
            ("package_install", "pip install thing", CODEX_LIVE_FLOW_BLOCKED_PACKAGE_INSTALL),
            ("browser_action", "playwright click", CODEX_LIVE_FLOW_BLOCKED_BROWSER_ACTION),
            ("mcp_tool", "call_tool", CODEX_LIVE_FLOW_BLOCKED_MCP_TOOL),
            ("agent_loop", "create_task", CODEX_LIVE_FLOW_BLOCKED_AGENT_LOOP),
            ("retry_now", "automatic_retry", CODEX_LIVE_FLOW_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING),
            ("api_key", "secret-token", CODEX_LIVE_FLOW_BLOCKED_ENV_OR_SECRET),
            ("approved", True, CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM),
            ("unknown_metadata", "ambiguous", CODEX_LIVE_FLOW_BLOCKED_AMBIGUOUS_EVIDENCE),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                evidence = self.evidence()
                output_data = evidence["output"].to_dict()
                output_data[key] = value
                result = evaluate_codex_live_flow(request=evidence["request"], handoff=evidence["handoff"], observation=evidence["observation"], output=output_data, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_authority_claim_and_non_json_serializable_evidence_fail_closed(self):
        evidence = self.evidence()
        authority_output = {**evidence["output"].to_dict(), "authority_claims": ("approved",)}
        result = evaluate_codex_live_flow(request=evidence["request"], handoff=evidence["handoff"], observation=evidence["observation"], output=authority_output, now=15)
        self.assertTrue(result.blocked)
        self.assertIn(CODEX_LIVE_FLOW_BLOCKED_AUTHORITY_CLAIM, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

        bad_request = evidence["request"].to_dict()
        bad_request["bad"] = object()
        result = evaluate_codex_live_flow(request=bad_request, handoff=evidence["handoff"], observation=evidence["observation"], output=evidence["output"], now=15)
        self.assertTrue(result.blocked)
        self.assertIn(CODEX_LIVE_FLOW_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_review_result_cannot_be_forged_into_authority(self):
        result = evaluate_codex_live_flow(**self.evidence(), now=15)
        forced = replace(
            result,
            codex_invocation_allowed=True,
            execution_allowed=True,
            write_allowed=True,
            patch_apply_allowed=True,
            test_execution_allowed=True,
            commit_allowed=True,
            push_allowed=True,
            dispatch_allowed=True,
            retry_allowed=True,
            fallback_allowed=True,
            streaming_allowed=True,
            requires_human_review=False,
            requires_controlled_path=False,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            can_run_codex=True,
            can_apply=True,
            can_write=True,
            can_execute=True,
            can_dispatch=True,
            can_retry=True,
            can_fallback=True,
            can_stream=True,
            can_commit=True,
            can_push=True,
            can_run_tests=True,
            approval_created=True,
            dispatcher_created=True,
            patch_applied=True,
            files_written=True,
            tests_executed=True,
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
            "run_codex",
            "invoke_codex",
            "run_aider",
            "invoke_aider",
            "apply_patch",
            "write",
            "commit",
            "push",
            "retry",
            "fallback",
            "worker",
            "create_task",
            "call_tool",
            "call_provider",
            "read_resource",
            "provider_call",
            "gate_pass",
            "grant_permission",
            "start_agent_loop",
        ):
            self.assertFalse(hasattr(result, method_name))

    def test_static_surface_has_no_execution_imports_or_future_agent_loops(self):
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
            "step_53",
            "step_54",
            "local_agent_loop",
            "provider_agent_loop",
        ):
            self.assertNotIn(forbidden_text, source)

    def evidence(self):
        request = self.request()
        handoff = self.handoff(request)
        observation = self.observation(request, handoff)
        output = self.output(request, handoff, observation)
        return {"request": request, "handoff": handoff, "observation": observation, "output": output}

    def request(self, *, task_goal="Record returned metadata.", requested_at=10, expires_at=100):
        return build_codex_live_flow_request(
            flow_id="flow",
            task_id="task",
            step_id="step_52_minimal_codex_live_flow",
            task_goal=task_goal,
            prepared_prompt_hash="1" * 64,
            coding_assistant_request_hash="2" * 64,
            coding_assistant_boundary_review_hash="3" * 64,
            orchestration_plan_hash="4" * 64,
            requested_by="tester",
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def handoff(self, request, *, handoff_summary="Manual transfer only.", created_at=10, expires_at=100):
        return build_codex_live_flow_handoff_packet(
            flow_id=request.flow_id,
            request_hash=request.request_hash,
            task_id=request.task_id,
            handoff_summary=handoff_summary,
            allowed_files=("runtime/live_flows/codex_live_flow.py", "runtime/blocked.py"),
            forbidden_files=("runtime/blocked.py",),
            required_tests=("tests.test_codex_live_flow_1a",),
            forbidden_actions=("apply_patch", "git_push", "provider_call"),
            human_operator_required=True,
            codex_invocation_allowed_by_aoia=False,
            created_at=created_at,
            expires_at=expires_at,
        )

    def observation(self, request, handoff, *, human_operator="tester", external_run_mode="human_manual_codex_ui"):
        return build_codex_external_run_observation(
            flow_id=request.flow_id,
            request_hash=request.request_hash,
            handoff_hash=handoff.handoff_hash,
            human_operator=human_operator,
            external_run_mode=external_run_mode,
            external_run_started_at=10,
            external_run_reported_at=10,
            external_run_report_hash="5" * 64,
        )

    def output(self, request, handoff, observation, *, output_summary="Returned summary.", returned_at=10, expires_at=100):
        return build_codex_returned_output_evidence(
            flow_id=request.flow_id,
            request_hash=request.request_hash,
            handoff_hash=handoff.handoff_hash,
            observation_hash=observation.observation_hash,
            output_summary=output_summary,
            changed_files_claimed=("runtime/live_flows/codex_live_flow.py",),
            tests_claimed=("tests.test_codex_live_flow_1a",),
            commit_hash_claimed=None,
            risk_notes=("requires manual review",),
            authority_claims=(),
            returned_at=returned_at,
            expires_at=expires_at,
        )

    def assert_metadata_only(self, data):
        for field in (
            "codex_invocation_allowed",
            "execution_allowed",
            "write_allowed",
            "patch_apply_allowed",
            "test_execution_allowed",
            "commit_allowed",
            "push_allowed",
            "dispatch_allowed",
            "retry_allowed",
            "fallback_allowed",
            "streaming_allowed",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_run_codex",
            "can_apply",
            "can_write",
            "can_execute",
            "can_dispatch",
            "can_retry",
            "can_fallback",
            "can_stream",
            "can_commit",
            "can_push",
            "can_run_tests",
            "approval_created",
            "dispatcher_created",
            "patch_applied",
            "files_written",
            "tests_executed",
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
