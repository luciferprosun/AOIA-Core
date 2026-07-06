from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.orchestration.async_io_orchestration import (
    ASYNC_IO_ORCHESTRATION_BLOCKED_AGENT_LOOP,
    ASYNC_IO_ORCHESTRATION_BLOCKED_AMBIGUOUS_EVIDENCE,
    ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM,
    ASYNC_IO_ORCHESTRATION_BLOCKED_BROWSER_ACTION,
    ASYNC_IO_ORCHESTRATION_BLOCKED_CODEX_AIDER,
    ASYNC_IO_ORCHESTRATION_BLOCKED_COMMAND_INJECTION,
    ASYNC_IO_ORCHESTRATION_BLOCKED_DEPENDENCY_CYCLE,
    ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_COMPLETED_ID,
    ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_DEPENDENCY_ID,
    ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_OPERATION_ID,
    ASYNC_IO_ORCHESTRATION_BLOCKED_ENV_OR_SECRET,
    ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_OPERATION,
    ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_PLAN,
    ASYNC_IO_ORCHESTRATION_BLOCKED_GIT_ACTION,
    ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH,
    ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION_KIND,
    ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_ORDERING_POLICY,
    ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME,
    ASYNC_IO_ORCHESTRATION_BLOCKED_MCP_TOOL,
    ASYNC_IO_ORCHESTRATION_BLOCKED_MISSING_DEPENDENCY,
    ASYNC_IO_ORCHESTRATION_BLOCKED_NON_JSON_SERIALIZABLE,
    ASYNC_IO_ORCHESTRATION_BLOCKED_PACKAGE_INSTALL,
    ASYNC_IO_ORCHESTRATION_BLOCKED_PROVIDER_CALL,
    ASYNC_IO_ORCHESTRATION_BLOCKED_RETRY_POLICY,
    ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_OPERATIONS,
    ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_READY_OPERATIONS,
    ASYNC_IO_ORCHESTRATION_BLOCKED_UNKNOWN_COMPLETED_ID,
    ASYNC_IO_ORCHESTRATION_DEPENDENCY_ORDERED,
    ASYNC_IO_ORCHESTRATION_OK,
    ASYNC_IO_ORCHESTRATION_READY_METADATA,
    ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH_REASON,
    ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW_REASON,
    AsyncIOOrchestrationReviewResult,
    build_async_io_operation_envelope,
    build_async_io_orchestration_plan,
    canonical_async_io_orchestration_json,
    evaluate_async_io_orchestration,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "orchestration" / "async_io_orchestration.py"


class AsyncIOOrchestration1ATests(unittest.TestCase):
    def test_valid_orchestration_plan_builds_deterministically_and_is_not_authority(self):
        plan = self.plan()

        first = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read",), now=15)
        second = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read",), now=15)

        self.assertTrue(first.ok)
        self.assertFalse(first.blocked)
        self.assertEqual(first.review_hash, second.review_hash)
        self.assertEqual(("govern",), first.ready_operation_ids)
        self.assertEqual(("automate",), first.blocked_operation_ids)
        self.assertIn(ASYNC_IO_ORCHESTRATION_READY_METADATA, first.orchestration_codes)
        self.assertIn(ASYNC_IO_ORCHESTRATION_DEPENDENCY_ORDERED, first.orchestration_codes)
        self.assertIn(ASYNC_IO_ORCHESTRATION_OK, first.reason_codes)
        self.assertIn(ASYNC_IO_ORCHESTRATION_REQUIRES_HUMAN_REVIEW_REASON, first.reason_codes)
        self.assertIn(ASYNC_IO_ORCHESTRATION_REQUIRES_CONTROLLED_PATH_REASON, first.reason_codes)
        self.assert_metadata_only(first.to_dict())

    def test_hashes_change_when_bound_evidence_changes(self):
        first = self.operation("read", "controlled_browser_read", requested_by="tester")
        changed_operation = self.operation("read", "controlled_browser_read", requested_by="other")
        self.assertNotEqual(first.operation_hash, changed_operation.operation_hash)

        plan = self.plan()
        changed_plan = build_async_io_orchestration_plan(
            plan_id="plan",
            operations=plan.operations,
            ordering_policy="declaration_order",
            created_at=10,
            expires_at=100,
        )
        self.assertNotEqual(plan.plan_hash, changed_plan.plan_hash)

        review = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read",), now=15)
        changed_review = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read", "govern"), now=15)
        self.assertNotEqual(review.review_hash, changed_review.review_hash)

    def test_canonical_json_is_deterministic_and_rejects_non_json_values(self):
        self.assertEqual(
            canonical_async_io_orchestration_json({"b": 1, "a": ("x",)}),
            canonical_async_io_orchestration_json({"a": ["x"], "b": 1}),
        )
        for value in ({"bad": object()}, {"bad": b"bytes"}, {"bad": {1, 2}}, {1: "bad"}, {"bad": float("nan")}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    canonical_async_io_orchestration_json(value)

    def test_dependency_order_ready_and_blocked_are_deterministic(self):
        plan = self.plan()

        none_done = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=(), now=15)
        read_done = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read",), now=15)
        govern_done = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=("read", "govern"), now=15)

        self.assertEqual(("read", "govern", "automate"), none_done.ordered_operation_ids)
        self.assertEqual(("read",), none_done.ready_operation_ids)
        self.assertEqual(("automate", "govern"), none_done.blocked_operation_ids)
        self.assertEqual(("govern",), read_done.ready_operation_ids)
        self.assertEqual(("automate",), read_done.blocked_operation_ids)
        self.assertEqual(("automate",), govern_done.ready_operation_ids)
        self.assertEqual((), govern_done.blocked_operation_ids)

    def test_declaration_and_blocked_only_ordering_policies_are_inert(self):
        declaration_order = self.plan(ordering_policy="declaration_order")
        blocked_only = self.plan(ordering_policy="blocked_only_review")

        declaration = evaluate_async_io_orchestration(plan=declaration_order, completed_operation_ids=(), now=15)
        blocked = evaluate_async_io_orchestration(plan=blocked_only, completed_operation_ids=(), now=15)

        self.assertEqual(("read", "govern", "automate"), declaration.ordered_operation_ids)
        self.assertEqual(("automate", "govern"), blocked.ordered_operation_ids)
        self.assert_metadata_only(declaration.to_dict())
        self.assert_metadata_only(blocked.to_dict())

    def test_duplicate_missing_unknown_and_cyclic_dependencies_fail_closed(self):
        cases = (
            (self.plan_with_operations((self.operation("dup", "controlled_browser_read"), self.operation("dup", "mcp_boundary"))), (), ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_OPERATION_ID),
            (self.plan_with_operations((self.operation("read", "controlled_browser_read"), self.operation("govern", "mcp_boundary", deps=("read", "read")))), (), ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_DEPENDENCY_ID),
            (self.plan_with_operations((self.operation("govern", "mcp_boundary", deps=("missing",)),)), (), ASYNC_IO_ORCHESTRATION_BLOCKED_MISSING_DEPENDENCY),
            (self.cyclic_plan(), (), ASYNC_IO_ORCHESTRATION_BLOCKED_DEPENDENCY_CYCLE),
            (self.plan(), ("read", "read"), ASYNC_IO_ORCHESTRATION_BLOCKED_DUPLICATE_COMPLETED_ID),
            (self.plan(), ("missing",), ASYNC_IO_ORCHESTRATION_BLOCKED_UNKNOWN_COMPLETED_ID),
        )
        for plan, completed, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=completed, now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_unsupported_kinds_policies_limits_and_hashes_fail_closed(self):
        cases = (
            (self.plan_with_operations((self.operation("x", "unknown_kind"),)), ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_OPERATION_KIND),
            (self.plan(ordering_policy="live_scheduler"), ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_ORDERING_POLICY),
            (self.plan(retry_policy="retry_once"), ASYNC_IO_ORCHESTRATION_BLOCKED_RETRY_POLICY),
            (self.plan(max_operations=2), ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_OPERATIONS),
            (
                self.plan_with_operations(
                    (
                        self.operation("read-a", "controlled_browser_read"),
                        self.operation("read-b", "browser_automation_preview"),
                    ),
                    max_ready_operations=1,
                ),
                ASYNC_IO_ORCHESTRATION_BLOCKED_TOO_MANY_READY_OPERATIONS,
            ),
            ({**self.plan().to_dict(), "plan_hash": "0" * 64}, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH),
            ({**self.plan().to_dict(), "operations": [{**self.plan().operations[0].to_dict(), "input_hashes": ("bad",)}]}, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH),
            ({**self.plan().to_dict(), "operations": [{**self.plan().operations[0].to_dict(), "expected_output_hash": "bad"}]}, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_HASH),
        )
        for plan, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=(), now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_time_evidence_fails_closed(self):
        cases = (
            (self.plan(), None, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
            (self.plan(), -1, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
            (self.plan(created_at=20, expires_at=100), 15, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
            (self.plan(created_at=10, expires_at=12), 15, ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_PLAN),
            (self.plan_with_operations((self.operation("read", "controlled_browser_read", requested_at=20, expires_at=40),)), 15, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
            (self.plan_with_operations((self.operation("read", "controlled_browser_read", requested_at=1, expires_at=12),)), 15, ASYNC_IO_ORCHESTRATION_BLOCKED_EXPIRED_OPERATION),
            ({**self.plan().to_dict(), "created_at": "bad"}, 15, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
            ({**self.plan().to_dict(), "operations": [{**self.plan().operations[0].to_dict(), "expires_at": 1}]}, 15, ASYNC_IO_ORCHESTRATION_BLOCKED_INVALID_TIME),
        )
        for plan, now, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_async_io_orchestration(plan=plan, completed_operation_ids=(), now=now)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_dangerous_smuggling_fails_closed(self):
        cases = (
            ("command", "bash -lc whoami", ASYNC_IO_ORCHESTRATION_BLOCKED_COMMAND_INJECTION),
            ("provider_call", "provider_call", ASYNC_IO_ORCHESTRATION_BLOCKED_PROVIDER_CALL),
            ("git_action", "git_push", ASYNC_IO_ORCHESTRATION_BLOCKED_GIT_ACTION),
            ("package_install", "pip install thing", ASYNC_IO_ORCHESTRATION_BLOCKED_PACKAGE_INSTALL),
            ("browser_action", "playwright click", ASYNC_IO_ORCHESTRATION_BLOCKED_BROWSER_ACTION),
            ("mcp_tool", "call_tool", ASYNC_IO_ORCHESTRATION_BLOCKED_MCP_TOOL),
            ("codex", "codex run", ASYNC_IO_ORCHESTRATION_BLOCKED_CODEX_AIDER),
            ("agent_loop", "create_task", ASYNC_IO_ORCHESTRATION_BLOCKED_AGENT_LOOP),
            ("api_key", "secret-token", ASYNC_IO_ORCHESTRATION_BLOCKED_ENV_OR_SECRET),
            ("approved", True, ASYNC_IO_ORCHESTRATION_BLOCKED_AUTHORITY_CLAIM),
            ("unknown_metadata", "ambiguous", ASYNC_IO_ORCHESTRATION_BLOCKED_AMBIGUOUS_EVIDENCE),
        )
        for key, value, reason in cases:
            with self.subTest(reason=reason):
                data = self.plan().to_dict()
                data[key] = value
                result = evaluate_async_io_orchestration(plan=data, completed_operation_ids=(), now=15)

                self.assertTrue(result.blocked)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_non_json_serializable_evidence_fails_closed(self):
        data = self.plan().to_dict()
        data["bad"] = object()

        result = evaluate_async_io_orchestration(plan=data, completed_operation_ids=(), now=15)

        self.assertTrue(result.blocked)
        self.assertIn(ASYNC_IO_ORCHESTRATION_BLOCKED_NON_JSON_SERIALIZABLE, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_review_result_cannot_be_forged_into_authority(self):
        result = evaluate_async_io_orchestration(plan=self.plan(), completed_operation_ids=("read",), now=15)
        forced = replace(
            result,
            execution_allowed=True,
            dispatch_allowed=True,
            retry_allowed=True,
            fallback_allowed=True,
            streaming_allowed=True,
            requires_human_review=False,
            requires_controlled_path=False,
            gate_satisfied=True,
            human_barrier_satisfied=True,
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
            operation_executed=True,
            tool_call_invoked=True,
            provider_called=True,
            mcp_called=True,
            process_started=True,
            network_called=True,
            browser_opened=True,
            package_manager_called=True,
            git_action_performed=True,
            retry_started=True,
            fallback_started=True,
            streaming_started=True,
            agent_loop_started=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in (
            "approve",
            "authorize",
            "dispatch",
            "execute",
            "run",
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
            "step 51",
            "step 52",
            "step 53",
            "step 54",
        ):
            self.assertNotIn(forbidden_text, source)

    def operation(
        self,
        operation_id,
        operation_kind,
        *,
        deps=(),
        requested_by="tester",
        requested_at=10,
        expires_at=100,
    ):
        return build_async_io_operation_envelope(
            operation_id=operation_id,
            operation_kind=operation_kind,
            input_hashes=("1" * 64,),
            dependency_operation_ids=deps,
            expected_output_hash="2" * 64,
            requested_by=requested_by,
            requested_at=requested_at,
            expires_at=expires_at,
        )

    def plan(self, *, ordering_policy="dependency_topological", retry_policy="none", max_operations=50, max_ready_operations=10, created_at=10, expires_at=100):
        return self.plan_with_operations(
            (
                self.operation("read", "controlled_browser_read"),
                self.operation("govern", "browser_automation_governance", deps=("read",)),
                self.operation("automate", "controlled_browser_automation", deps=("govern",)),
            ),
            ordering_policy=ordering_policy,
            retry_policy=retry_policy,
            max_operations=max_operations,
            max_ready_operations=max_ready_operations,
            created_at=created_at,
            expires_at=expires_at,
        )

    def plan_with_operations(
        self,
        operations,
        *,
        ordering_policy="dependency_topological",
        retry_policy="none",
        max_operations=50,
        max_ready_operations=10,
        created_at=10,
        expires_at=100,
    ):
        return build_async_io_orchestration_plan(
            plan_id="plan",
            operations=tuple(operations),
            ordering_policy=ordering_policy,
            max_operations=max_operations,
            max_ready_operations=max_ready_operations,
            retry_policy=retry_policy,
            created_at=created_at,
            expires_at=expires_at,
        )

    def cyclic_plan(self):
        first = self.operation("first", "controlled_browser_read", deps=("second",))
        second = self.operation("second", "mcp_boundary", deps=("first",))
        return self.plan_with_operations((first, second))

    def assert_metadata_only(self, data):
        for field in (
            "execution_allowed",
            "dispatch_allowed",
            "retry_allowed",
            "fallback_allowed",
            "streaming_allowed",
            "gate_satisfied",
            "human_barrier_satisfied",
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
            "operation_executed",
            "tool_call_invoked",
            "provider_called",
            "mcp_called",
            "process_started",
            "network_called",
            "browser_opened",
            "package_manager_called",
            "git_action_performed",
            "retry_started",
            "fallback_started",
            "streaming_started",
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
