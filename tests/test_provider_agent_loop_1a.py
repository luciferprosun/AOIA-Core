from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.agent_loops.provider_agent_loop import (
    PROVIDER_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION,
    PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE,
    PROVIDER_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM,
    PROVIDER_AGENT_LOOP_BLOCKED_BROWSER_ACTION,
    PROVIDER_AGENT_LOOP_BLOCKED_CODEX_AIDER,
    PROVIDER_AGENT_LOOP_BLOCKED_COMMAND_INJECTION,
    PROVIDER_AGENT_LOOP_BLOCKED_COMMIT_OR_PUSH,
    PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH,
    PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID,
    PROVIDER_AGENT_LOOP_BLOCKED_ENV_OR_SECRET,
    PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE,
    PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_INPUT_EVIDENCE,
    PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE,
    PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND,
    PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_PROVIDER_KIND,
    PROVIDER_AGENT_LOOP_BLOCKED_GIT_ACTION,
    PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH,
    PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND,
    PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH,
    PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE,
    PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND,
    PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME,
    PROVIDER_AGENT_LOOP_BLOCKED_LOCAL_LLM,
    PROVIDER_AGENT_LOOP_BLOCKED_MCP_TOOL,
    PROVIDER_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE,
    PROVIDER_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL,
    PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK,
    PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL,
    PROVIDER_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING,
    PROVIDER_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED,
    PROVIDER_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE,
    PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH,
    PROVIDER_AGENT_LOOP_NON_AUTHORITY,
    PROVIDER_AGENT_LOOP_OK,
    PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED,
    PROVIDER_AGENT_LOOP_READY_METADATA,
    PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON,
    PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON,
    PROVIDER_AGENT_LOOP_SELECTED_METADATA_ONLY,
    build_provider_agent_candidate_action,
    build_provider_agent_input_evidence,
    build_provider_agent_objective,
    canonical_provider_agent_loop_json,
    evaluate_provider_agent_loop_iteration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "agent_loops" / "provider_agent_loop.py"


class ProviderAgentLoop1ATests(unittest.TestCase):
    def test_valid_provider_loop_review_is_deterministic_inert_untrusted_and_hash_bound(self):
        evidence = self.evidence()

        first = evaluate_provider_agent_loop_iteration(**evidence, now=15)
        second = evaluate_provider_agent_loop_iteration(**self.evidence(), now=15)

        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertTrue(first.selected)
        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(evidence["objective"].objective_hash, first.objective_hash)
        self.assertEqual(evidence["input_evidence"].evidence_hash, first.input_evidence_hash)
        self.assertEqual(evidence["candidates"][0].candidate_hash, first.selected_candidate_hash)
        self.assertIn(evidence["candidates"][0].candidate_hash, first.ready_candidate_hashes)
        self.assertIn(PROVIDER_AGENT_LOOP_OK, first.reason_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON, first.reason_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON, first.reason_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_READY_METADATA, first.loop_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_SELECTED_METADATA_ONLY, first.loop_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED, first.loop_codes)
        self.assertIn(PROVIDER_AGENT_LOOP_NON_AUTHORITY, first.loop_codes)
        self.assert_metadata_only(first.to_dict())

    def test_hashes_change_when_bound_evidence_changes(self):
        objective = self.objective(objective_summary="Review provider metadata.")
        changed_objective = self.objective(objective_summary="Review provider metadata for a human.")
        self.assertNotEqual(objective.objective_hash, changed_objective.objective_hash)

        input_evidence = self.input_evidence(provider_kind="mock_provider_output")
        changed_input_evidence = self.input_evidence(provider_kind="generic_provider_output")
        self.assertNotEqual(input_evidence.evidence_hash, changed_input_evidence.evidence_hash)

        candidate = self.candidate("candidate-a", "request_human_review")
        changed_candidate = self.candidate("candidate-a", "mark_blocked")
        self.assertNotEqual(candidate.candidate_hash, changed_candidate.candidate_hash)

        first = evaluate_provider_agent_loop_iteration(
            objective=objective,
            input_evidence=input_evidence,
            candidates=(candidate,),
            now=15,
        )
        second = evaluate_provider_agent_loop_iteration(
            objective=changed_objective,
            input_evidence=input_evidence,
            candidates=(candidate,),
            now=15,
        )
        third = evaluate_provider_agent_loop_iteration(
            objective=objective,
            input_evidence=input_evidence,
            candidates=(candidate,),
            completed_candidate_hashes=(candidate.candidate_hash,),
            now=15,
        )
        self.assertNotEqual(first.review_hash, second.review_hash)
        self.assertNotEqual(first.review_hash, third.review_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_provider_agent_loop_json({"b": 1, "a": ("x",)}),
            canonical_provider_agent_loop_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("inf")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_provider_agent_loop_json(value)

    def test_provider_kind_validation_fails_closed(self):
        evidence = self.evidence()
        objective_forbidden = self.objective(
            allowed_provider_kinds=("mock_provider_output",),
            forbidden_provider_kinds=("mock_provider_output",),
        )
        cases = (
            ({**evidence, "input_evidence": self.input_evidence(provider_kind="future_model_label")}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND),
            ({**evidence, "objective": self.objective(allowed_provider_kinds=("generic_provider_output",))}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_PROVIDER_KIND),
            ({**evidence, "objective": objective_forbidden}, PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_PROVIDER_KIND),
            ({**evidence, "objective": self.objective(allowed_provider_kinds=("future_model_label",))}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_provider_agent_loop_iteration(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_action_kind_and_target_step_validation_fails_closed(self):
        evidence = self.evidence()
        objective_forbidden = self.objective(
            allowed_next_action_kinds=("request_human_review",),
            forbidden_next_action_kinds=("request_human_review",),
        )
        cases = (
            ({**evidence, "candidates": (self.candidate("bad", "run_provider_agent"),)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND),
            ({**evidence, "objective": self.objective(allowed_next_action_kinds=("mark_blocked",))}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND),
            ({**evidence, "objective": objective_forbidden}, PROVIDER_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND),
            ({**evidence, "objective": self.objective(allowed_next_action_kinds=("unknown_action",))}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="step_99_future"),)}, PROVIDER_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="step_55"),)}, PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="prototype_freeze"),)}, PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="knowledge_hub"),)}, PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="tetrad"),)}, PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="pheromone"),)}, PROVIDER_AGENT_LOOP_BLOCKED_POST54_WORK),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_provider_agent_loop_iteration(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_duplicate_unknown_completed_and_tie_break_are_deterministic(self):
        objective = self.objective(allowed_next_action_kinds=("request_human_review", "mark_blocked"))
        input_evidence = self.input_evidence()
        first = self.candidate("b-candidate", "mark_blocked")
        second = self.candidate("a-candidate", "request_human_review")

        result = evaluate_provider_agent_loop_iteration(objective=objective, input_evidence=input_evidence, candidates=(first, second), now=15)

        self.assertTrue(result.ok)
        self.assertEqual(second.candidate_hash, result.selected_candidate_hash)

        duplicate_id = self.candidate("b-candidate", "request_human_review")
        cases = (
            ((first, duplicate_id), (), PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID),
            ((first, {**second.to_dict(), "candidate_hash": first.candidate_hash}), (), PROVIDER_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH),
            ((first, second), ("9" * 64,), PROVIDER_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE),
        )
        for candidates, completed, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_provider_agent_loop_iteration(
                    objective=objective,
                    input_evidence=input_evidence,
                    candidates=candidates,
                    completed_candidate_hashes=completed,
                    now=15,
                )

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_time_evidence_fails_closed(self):
        evidence = self.evidence()
        cases = (
            (evidence, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, None),
            (evidence, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, -1),
            ({**evidence, "objective": self.objective(requested_at=20, expires_at=100)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "input_evidence": self.input_evidence(observed_at=20, expires_at=100)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", suggested_at=20, expires_at=100),)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "objective": self.objective(requested_at=1, expires_at=12)}, PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE, 15),
            ({**evidence, "input_evidence": self.input_evidence(observed_at=1, expires_at=12)}, PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_INPUT_EVIDENCE, 15),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", suggested_at=1, expires_at=12),)}, PROVIDER_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE, 15),
            ({**evidence, "objective": {**evidence["objective"].to_dict(), "expires_at": 1}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "input_evidence": {**evidence["input_evidence"].to_dict(), "expires_at": 1}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "expires_at": 1},)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
        )
        for altered, reason, now in cases:
            with self.subTest(reason=reason):
                result = evaluate_provider_agent_loop_iteration(**altered, now=now)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_hash_validation_and_mismatch_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "objective": {**evidence["objective"].to_dict(), "objective_hash": "9" * 64}}, PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH),
            ({**evidence, "input_evidence": {**evidence["input_evidence"].to_dict(), "evidence_hash": "9" * 64}}, PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "candidate_hash": "8" * 64},)}, PROVIDER_AGENT_LOOP_BLOCKED_HASH_MISMATCH),
            ({**evidence, "objective": {**evidence["objective"].to_dict(), "context_hashes": ("bad",)}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "input_evidence": {**evidence["input_evidence"].to_dict(), "provider_response_hash": "bad"}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "input_evidence": {**evidence["input_evidence"].to_dict(), "provider_schema_validation_hash": "bad"}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "input_evidence": {**evidence["input_evidence"].to_dict(), "local_agent_loop_review_hash": "bad"}}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "required_evidence_hashes": ("bad",)},)}, PROVIDER_AGENT_LOOP_BLOCKED_INVALID_HASH),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_provider_agent_loop_iteration(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_dangerous_smuggling_fails_closed(self):
        cases = (
            ("command", "bash -lc whoami", PROVIDER_AGENT_LOOP_BLOCKED_COMMAND_INJECTION),
            ("provider_call", "provider_call", PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL),
            ("provider_claims", ("openai client call",), PROVIDER_AGENT_LOOP_BLOCKED_PROVIDER_CALL),
            ("local_llm", "ollama run", PROVIDER_AGENT_LOOP_BLOCKED_LOCAL_LLM),
            ("git_action", "git_push", PROVIDER_AGENT_LOOP_BLOCKED_GIT_ACTION),
            ("package_install", "pip install thing", PROVIDER_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL),
            ("browser_action", "playwright click", PROVIDER_AGENT_LOOP_BLOCKED_BROWSER_ACTION),
            ("mcp_tool", "call_tool", PROVIDER_AGENT_LOOP_BLOCKED_MCP_TOOL),
            ("codex", "run_codex", PROVIDER_AGENT_LOOP_BLOCKED_CODEX_AIDER),
            ("agent_loop", "invoke_agent", PROVIDER_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION),
            ("retry_now", "automatic_retry", PROVIDER_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING),
            ("write_files", "apply_patch", PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH),
            ("run_tests", "run_tests", PROVIDER_AGENT_LOOP_BLOCKED_WRITE_OR_PATCH),
            ("git_commit", "git_commit", PROVIDER_AGENT_LOOP_BLOCKED_COMMIT_OR_PUSH),
            ("api_key", "secret-token", PROVIDER_AGENT_LOOP_BLOCKED_ENV_OR_SECRET),
            ("approved", True, PROVIDER_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM),
            ("unknown_metadata", "ambiguous", PROVIDER_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                evidence = self.evidence()
                candidate = evidence["candidates"][0].to_dict()
                candidate[key] = value
                result = evaluate_provider_agent_loop_iteration(
                    objective=evidence["objective"],
                    input_evidence=evidence["input_evidence"],
                    candidates=(candidate,),
                    now=15,
                )

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_non_json_serializable_evidence_fails_closed(self):
        evidence = self.evidence()
        objective = evidence["objective"].to_dict()
        objective["bad"] = object()

        result = evaluate_provider_agent_loop_iteration(
            objective=objective,
            input_evidence=evidence["input_evidence"],
            candidates=evidence["candidates"],
            now=15,
        )

        self.assertTrue(result.blocked)
        self.assertIn(PROVIDER_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_review_result_cannot_be_forged_into_authority(self):
        result = evaluate_provider_agent_loop_iteration(**self.evidence(), now=15)
        forced = replace(
            result,
            provider_call_allowed=True,
            local_llm_allowed=True,
            tool_call_allowed=True,
            execution_allowed=True,
            dispatch_allowed=True,
            retry_allowed=True,
            fallback_allowed=True,
            streaming_allowed=True,
            write_allowed=True,
            patch_apply_allowed=True,
            test_execution_allowed=True,
            commit_allowed=True,
            push_allowed=True,
            requires_human_review=False,
            requires_controlled_path=False,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            can_execute=True,
            can_dispatch=True,
            can_retry=True,
            can_fallback=True,
            can_stream=True,
            can_write=True,
            can_apply=True,
            can_run_tests=True,
            can_commit=True,
            can_push=True,
            can_call_tool=True,
            can_call_provider=True,
            can_call_mcp=True,
            can_call_llm=True,
            approval_created=True,
            dispatcher_created=True,
            selected_candidate_executed=True,
            tool_called=True,
            provider_called=True,
            local_llm_called=True,
            retry_started=True,
            fallback_started=True,
            streaming_started=True,
            files_written=True,
            patch_applied=True,
            tests_run=True,
            commit_created=True,
            push_performed=True,
            process_started=True,
            network_called=True,
            mcp_called=True,
            browser_opened=True,
            package_manager_called=True,
            git_action_performed=True,
            agent_loop_started=True,
            post54_work_started=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in (
            "approve",
            "authorize",
            "dispatch",
            "execute",
            "run",
            "run_agent",
            "invoke_agent",
            "start_agent_loop",
            "run_provider",
            "call_provider",
            "run_local_llm",
            "call_llm",
            "call_tool",
            "read_resource",
            "write",
            "apply_patch",
            "run_tests",
            "commit",
            "push",
            "retry",
            "fallback",
            "worker",
            "create_task",
            "provider_call",
            "gate_pass",
            "grant_permission",
        ):
            self.assertFalse(hasattr(result, method_name))

    def test_static_surface_has_no_execution_imports_calls_or_post54_implementation(self):
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
            "google.generativeai",
            "google.genai",
            "ollama",
            "transformers",
            "vllm",
            "llama_cpp",
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
        for forbidden_text in ("shell=true", "os.environ", "getenv"):
            self.assertNotIn(forbidden_text, source)
        self.assertNotIn("prototype_freeze.py", source)
        self.assertNotIn("knowledge_hub.py", source)

    def evidence(self):
        return {
            "objective": self.objective(),
            "input_evidence": self.input_evidence(),
            "candidates": (self.candidate("candidate-a", "request_human_review"),),
        }

    def objective(
        self,
        *,
        objective_summary="Review provider metadata.",
        allowed_provider_kinds=("mock_provider_output", "generic_provider_output"),
        forbidden_provider_kinds=(),
        allowed_next_action_kinds=("request_human_review", "mark_blocked"),
        forbidden_next_action_kinds=(),
        requested_at=10,
        expires_at=100,
    ):
        return build_provider_agent_objective(
            objective_id="objective",
            objective_summary=objective_summary,
            allowed_provider_kinds=allowed_provider_kinds,
            forbidden_provider_kinds=forbidden_provider_kinds,
            allowed_next_action_kinds=allowed_next_action_kinds,
            forbidden_next_action_kinds=forbidden_next_action_kinds,
            context_hashes=("1" * 64,),
            requested_by="tester",
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def input_evidence(self, *, provider_kind="mock_provider_output", observed_at=10, expires_at=100):
        return build_provider_agent_input_evidence(
            evidence_id="evidence",
            provider_kind=provider_kind,
            provider_response_hash="2" * 64,
            provider_schema_validation_hash="3" * 64,
            provider_critic_hash="4" * 64,
            provider_governance_hash="5" * 64,
            local_agent_loop_review_hash="6" * 64,
            orchestration_review_hash="7" * 64,
            recovery_review_hash="8" * 64,
            evidence_summary="Untrusted model suggestion metadata.",
            observed_at=observed_at,
            expires_at=expires_at,
        )

    def candidate(
        self,
        candidate_id,
        action_kind,
        *,
        target_step="step_54_provider_agent_loop",
        suggested_at=10,
        expires_at=100,
    ):
        return build_provider_agent_candidate_action(
            candidate_id=candidate_id,
            action_kind=action_kind,
            action_summary="Record provider loop metadata for human review.",
            target_step=target_step,
            required_evidence_hashes=("9" * 64,),
            provider_claims=("untrusted suggestion only",),
            risk_notes=("metadata only",),
            suggested_by="tester",
            suggested_at=suggested_at,
            expires_at=expires_at,
        )

    def assert_metadata_only(self, data):
        for field in (
            "provider_call_allowed",
            "local_llm_allowed",
            "tool_call_allowed",
            "execution_allowed",
            "dispatch_allowed",
            "retry_allowed",
            "fallback_allowed",
            "streaming_allowed",
            "write_allowed",
            "patch_apply_allowed",
            "test_execution_allowed",
            "commit_allowed",
            "push_allowed",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_execute",
            "can_dispatch",
            "can_retry",
            "can_fallback",
            "can_stream",
            "can_write",
            "can_apply",
            "can_run_tests",
            "can_commit",
            "can_push",
            "can_call_tool",
            "can_call_provider",
            "can_call_mcp",
            "can_call_llm",
            "approval_created",
            "dispatcher_created",
            "selected_candidate_executed",
            "tool_called",
            "provider_called",
            "local_llm_called",
            "retry_started",
            "fallback_started",
            "streaming_started",
            "files_written",
            "patch_applied",
            "tests_run",
            "commit_created",
            "push_performed",
            "process_started",
            "network_called",
            "mcp_called",
            "browser_opened",
            "package_manager_called",
            "git_action_performed",
            "agent_loop_started",
            "post54_work_started",
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
