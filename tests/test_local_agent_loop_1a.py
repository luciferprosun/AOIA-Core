from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.agent_loops.local_agent_loop import (
    LOCAL_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION,
    LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE,
    LOCAL_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM,
    LOCAL_AGENT_LOOP_BLOCKED_BROWSER_ACTION,
    LOCAL_AGENT_LOOP_BLOCKED_CODEX_AIDER,
    LOCAL_AGENT_LOOP_BLOCKED_COMMAND_INJECTION,
    LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH,
    LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID,
    LOCAL_AGENT_LOOP_BLOCKED_ENV_OR_SECRET,
    LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE,
    LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE,
    LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_STATE,
    LOCAL_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND,
    LOCAL_AGENT_LOOP_BLOCKED_GIT_ACTION,
    LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH,
    LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND,
    LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH,
    LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE,
    LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME,
    LOCAL_AGENT_LOOP_BLOCKED_LOCAL_LLM,
    LOCAL_AGENT_LOOP_BLOCKED_MCP_TOOL,
    LOCAL_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE,
    LOCAL_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL,
    LOCAL_AGENT_LOOP_BLOCKED_PROVIDER_CALL,
    LOCAL_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING,
    LOCAL_AGENT_LOOP_BLOCKED_STEP54_NOT_AVAILABLE,
    LOCAL_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED,
    LOCAL_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE,
    LOCAL_AGENT_LOOP_NON_AUTHORITY,
    LOCAL_AGENT_LOOP_OK,
    LOCAL_AGENT_LOOP_READY_METADATA,
    LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON,
    LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON,
    LOCAL_AGENT_LOOP_SELECTED_METADATA_ONLY,
    build_local_agent_candidate_action,
    build_local_agent_loop_state,
    build_local_agent_objective,
    canonical_local_agent_loop_json,
    evaluate_local_agent_loop_iteration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "agent_loops" / "local_agent_loop.py"


class LocalAgentLoop1ATests(unittest.TestCase):
    def test_valid_local_agent_loop_review_is_deterministic_inert_and_hash_bound(self):
        evidence = self.evidence()

        first = evaluate_local_agent_loop_iteration(**evidence, now=15)
        second = evaluate_local_agent_loop_iteration(**self.evidence(), now=15)

        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertTrue(first.selected)
        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(evidence["objective"].objective_hash, first.objective_hash)
        self.assertEqual(evidence["state"].state_hash, first.state_hash)
        self.assertEqual(evidence["candidates"][0].candidate_hash, first.selected_candidate_hash)
        self.assertIn(evidence["candidates"][0].candidate_hash, first.ready_candidate_hashes)
        self.assertIn(LOCAL_AGENT_LOOP_OK, first.reason_codes)
        self.assertIn(LOCAL_AGENT_LOOP_REQUIRES_HUMAN_REVIEW_REASON, first.reason_codes)
        self.assertIn(LOCAL_AGENT_LOOP_REQUIRES_CONTROLLED_PATH_REASON, first.reason_codes)
        self.assertIn(LOCAL_AGENT_LOOP_READY_METADATA, first.loop_codes)
        self.assertIn(LOCAL_AGENT_LOOP_SELECTED_METADATA_ONLY, first.loop_codes)
        self.assertIn(LOCAL_AGENT_LOOP_NON_AUTHORITY, first.loop_codes)
        self.assert_metadata_only(first.to_dict())

    def test_hashes_change_when_bound_evidence_changes(self):
        objective = self.objective(objective_summary="Review local metadata.")
        changed_objective = self.objective(objective_summary="Review local metadata for a human.")
        self.assertNotEqual(objective.objective_hash, changed_objective.objective_hash)

        state = self.state(objective, iteration_index=1)
        changed_state = self.state(objective, iteration_index=2)
        self.assertNotEqual(state.state_hash, changed_state.state_hash)

        candidate = self.candidate("candidate-a", "request_human_review")
        changed_candidate = self.candidate("candidate-a", "mark_blocked")
        self.assertNotEqual(candidate.candidate_hash, changed_candidate.candidate_hash)

        first = evaluate_local_agent_loop_iteration(objective=objective, state=state, candidates=(candidate,), now=15)
        second = evaluate_local_agent_loop_iteration(objective=changed_objective, state=self.state(changed_objective), candidates=(candidate,), now=15)
        self.assertNotEqual(first.review_hash, second.review_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_local_agent_loop_json({"b": 1, "a": ("x",)}),
            canonical_local_agent_loop_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("nan")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_local_agent_loop_json(value)

    def test_state_objective_mismatch_and_invalid_hashes_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "state": {**evidence["state"].to_dict(), "objective_hash": "9" * 64}}, LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH),
            ({**evidence, "objective": {**evidence["objective"].to_dict(), "context_hashes": ("bad",)}}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "state": {**evidence["state"].to_dict(), "current_evidence_hashes": ("bad",)}}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "required_evidence_hashes": ("bad",)},)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_HASH),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "candidate_hash": "8" * 64},)}, LOCAL_AGENT_LOOP_BLOCKED_HASH_MISMATCH),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_local_agent_loop_iteration(**altered, now=15)

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
            ({**evidence, "candidates": (self.candidate("bad", "run_local_agent"),)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND),
            ({**evidence, "objective": self.objective(allowed_next_action_kinds=("mark_blocked",))}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_ACTION_KIND),
            (self.rebind(objective_forbidden, candidates=(self.candidate("candidate-a", "request_human_review"),)), LOCAL_AGENT_LOOP_BLOCKED_FORBIDDEN_ACTION_KIND),
            ({**evidence, "objective": self.objective(allowed_next_action_kinds=("unknown_action",))}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_OBJECTIVE),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="step_99_future"),)}, LOCAL_AGENT_LOOP_BLOCKED_TARGET_STEP_NOT_ALLOWED),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", target_step="step_54_provider_agent_loop"),)}, LOCAL_AGENT_LOOP_BLOCKED_STEP54_NOT_AVAILABLE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                altered = self.rebind(altered["objective"], altered.get("state"), altered["candidates"]) if isinstance(altered, dict) and altered.get("state") is None else altered
                result = evaluate_local_agent_loop_iteration(**altered, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_duplicate_unknown_completed_and_tie_break_are_deterministic(self):
        objective = self.objective(allowed_next_action_kinds=("request_human_review", "mark_blocked"))
        state = self.state(objective)
        first = self.candidate("b-candidate", "mark_blocked")
        second = self.candidate("a-candidate", "request_human_review")

        result = evaluate_local_agent_loop_iteration(objective=objective, state=state, candidates=(first, second), now=15)

        self.assertTrue(result.ok)
        self.assertEqual(second.candidate_hash, result.selected_candidate_hash)

        duplicate_id = self.candidate("b-candidate", "request_human_review")
        cases = (
            ((first, duplicate_id), (), LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_ID),
            ((first, {**second.to_dict(), "candidate_hash": first.candidate_hash}), (), LOCAL_AGENT_LOOP_BLOCKED_DUPLICATE_CANDIDATE_HASH),
            ((first, second), ("9" * 64,), LOCAL_AGENT_LOOP_BLOCKED_UNKNOWN_COMPLETED_CANDIDATE),
        )
        for candidates, completed, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_local_agent_loop_iteration(
                    objective=objective,
                    state=state,
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
            (evidence, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, None),
            (evidence, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, -1),
            ({**evidence, "objective": self.objective(requested_at=20, expires_at=100)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "state": self.state(evidence["objective"], state_created_at=20, state_expires_at=100)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", proposed_at=20, expires_at=100),)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "objective": self.objective(requested_at=1, expires_at=12)}, LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_OBJECTIVE, 15),
            ({**evidence, "state": self.state(evidence["objective"], state_created_at=1, state_expires_at=12)}, LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_STATE, 15),
            ({**evidence, "candidates": (self.candidate("candidate-a", "request_human_review", proposed_at=1, expires_at=12),)}, LOCAL_AGENT_LOOP_BLOCKED_EXPIRED_CANDIDATE, 15),
            ({**evidence, "objective": {**evidence["objective"].to_dict(), "expires_at": 1}}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "state": {**evidence["state"].to_dict(), "state_expires_at": 1}}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
            ({**evidence, "candidates": ({**evidence["candidates"][0].to_dict(), "expires_at": 1},)}, LOCAL_AGENT_LOOP_BLOCKED_INVALID_TIME, 15),
        )
        for altered, reason, now in cases:
            with self.subTest(reason=reason):
                result = evaluate_local_agent_loop_iteration(**altered, now=now)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_dangerous_smuggling_fails_closed(self):
        cases = (
            ("command", "bash -lc whoami", LOCAL_AGENT_LOOP_BLOCKED_COMMAND_INJECTION),
            ("provider_call", "provider_call", LOCAL_AGENT_LOOP_BLOCKED_PROVIDER_CALL),
            ("git_action", "git_push", LOCAL_AGENT_LOOP_BLOCKED_GIT_ACTION),
            ("package_install", "pip install thing", LOCAL_AGENT_LOOP_BLOCKED_PACKAGE_INSTALL),
            ("browser_action", "playwright click", LOCAL_AGENT_LOOP_BLOCKED_BROWSER_ACTION),
            ("mcp_tool", "call_tool", LOCAL_AGENT_LOOP_BLOCKED_MCP_TOOL),
            ("codex", "run_codex", LOCAL_AGENT_LOOP_BLOCKED_CODEX_AIDER),
            ("local_llm", "ollama run", LOCAL_AGENT_LOOP_BLOCKED_LOCAL_LLM),
            ("agent_loop", "invoke_agent", LOCAL_AGENT_LOOP_BLOCKED_AGENT_LOOP_EXECUTION),
            ("retry_now", "automatic_retry", LOCAL_AGENT_LOOP_BLOCKED_RETRY_OR_FALLBACK_SMUGGLING),
            ("api_key", "secret-token", LOCAL_AGENT_LOOP_BLOCKED_ENV_OR_SECRET),
            ("approved", True, LOCAL_AGENT_LOOP_BLOCKED_AUTHORITY_CLAIM),
            ("unknown_metadata", "ambiguous", LOCAL_AGENT_LOOP_BLOCKED_AMBIGUOUS_EVIDENCE),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                evidence = self.evidence()
                candidate = evidence["candidates"][0].to_dict()
                candidate[key] = value
                result = evaluate_local_agent_loop_iteration(
                    objective=evidence["objective"],
                    state=evidence["state"],
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

        result = evaluate_local_agent_loop_iteration(objective=objective, state=evidence["state"], candidates=evidence["candidates"], now=15)

        self.assertTrue(result.blocked)
        self.assertIn(LOCAL_AGENT_LOOP_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_review_result_cannot_be_forged_into_authority(self):
        result = evaluate_local_agent_loop_iteration(**self.evidence(), now=15)
        forced = replace(
            result,
            execution_allowed=True,
            dispatch_allowed=True,
            tool_call_allowed=True,
            provider_call_allowed=True,
            local_llm_allowed=True,
            retry_allowed=True,
            fallback_allowed=True,
            streaming_allowed=True,
            write_allowed=True,
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
            commit_created=True,
            push_performed=True,
            process_started=True,
            network_called=True,
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
            "run_agent",
            "invoke_agent",
            "start_agent_loop",
            "run_local_llm",
            "call_llm",
            "call_tool",
            "call_provider",
            "read_resource",
            "write",
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

    def test_static_surface_has_no_execution_imports_or_step54(self):
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

    def evidence(self):
        objective = self.objective()
        state = self.state(objective)
        candidates = (self.candidate("candidate-a", "request_human_review"),)
        return {"objective": objective, "state": state, "candidates": candidates}

    def rebind(self, objective, state=None, candidates=None):
        if state is None or (not isinstance(state, dict) and state.objective_hash != objective.objective_hash):
            state = self.state(objective)
        return {"objective": objective, "state": state, "candidates": candidates or (self.candidate("candidate-a", "request_human_review"),)}

    def objective(
        self,
        *,
        objective_summary="Review local metadata.",
        allowed_next_action_kinds=("request_human_review", "mark_blocked"),
        forbidden_next_action_kinds=(),
        requested_at=10,
        expires_at=100,
    ):
        return build_local_agent_objective(
            objective_id="objective",
            objective_summary=objective_summary,
            allowed_next_action_kinds=allowed_next_action_kinds,
            forbidden_next_action_kinds=forbidden_next_action_kinds,
            context_hashes=("1" * 64,),
            requested_by="tester",
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def state(self, objective, *, iteration_index=1, state_created_at=10, state_expires_at=100):
        return build_local_agent_loop_state(
            loop_id="loop",
            objective_hash=objective.objective_hash,
            iteration_index=iteration_index,
            completed_iteration_hashes=("2" * 64,),
            current_evidence_hashes=("3" * 64,),
            orchestration_review_hash="4" * 64,
            recovery_review_hash="5" * 64,
            codex_live_flow_review_hash="6" * 64,
            state_created_at=state_created_at,
            state_expires_at=state_expires_at,
        )

    def candidate(
        self,
        candidate_id,
        action_kind,
        *,
        target_step="step_53_local_agent_loop",
        proposed_at=10,
        expires_at=100,
    ):
        return build_local_agent_candidate_action(
            candidate_id=candidate_id,
            action_kind=action_kind,
            action_summary="Record local loop metadata for human review.",
            target_step=target_step,
            required_evidence_hashes=("7" * 64,),
            risk_notes=("metadata only",),
            proposed_by="tester",
            proposed_at=proposed_at,
            expires_at=expires_at,
        )

    def assert_metadata_only(self, data):
        for field in (
            "execution_allowed",
            "dispatch_allowed",
            "tool_call_allowed",
            "provider_call_allowed",
            "local_llm_allowed",
            "retry_allowed",
            "fallback_allowed",
            "streaming_allowed",
            "write_allowed",
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
            "commit_created",
            "push_performed",
            "process_started",
            "network_called",
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
