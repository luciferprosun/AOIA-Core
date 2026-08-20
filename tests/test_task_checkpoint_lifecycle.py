from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import main
from runtime import webapp
from runtime.providers import cli as provider_cli
from runtime.providers.contracts import (
    LIVE_SUCCESS,
    ProviderRuntimeResult,
)
from runtime.runtime_paths import runtime_state_dir
from runtime.task_checkpoints import TaskPhase, TaskState
from tools.provenance import AppendOnlyProvenanceStore, ProvenanceAppendError
from trace_context import ModelCallContext, TraceContext


class InspectingProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0
        self.runtime: main.AgentRuntime | None = None
        self.observed_checkpoint = None

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        assert self.runtime is not None
        self.observed_checkpoint = self.runtime.task_checkpoint_store.load(
            self.runtime._active_test_trace.task_id
        )
        return self.response

    def describe(self) -> str:
        return "fake/test-model"

    def active_fallback_chain(self) -> list[str]:
        return ["fake/test-model"]

    def provider_status(self) -> list[dict[str, object]]:
        return []


class SequencedProvider(InspectingProvider):
    def __init__(self, responses: list[str]) -> None:
        super().__init__(responses[0])
        self.responses = responses

    def generate(self, _prompt: str) -> str:
        response = self.responses[self.calls]
        self.response = response
        return super().generate(_prompt)


class FakeOrchestrator:
    def __init__(self) -> None:
        self.recorded: list[tuple[str, dict[str, object], dict[str, object]]] = []

    def create_traced_plan(
        self,
        _user_input,
        _runtime_status,
        trace_context,
        on_attempt,
    ):
        model_call = trace_context.new_model_call()
        on_attempt("started", model_call, "planner", "planner/model", 1)
        on_attempt("succeeded", model_call, "planner", "planner/model", 1)
        return {"strategy": "one safe step", "steps": ["respond"]}, model_call

    def action_for_step_traced(
        self,
        *,
        trace_context,
        on_attempt,
        **_kwargs,
    ):
        model_call = trace_context.new_model_call()
        on_attempt("started", model_call, "worker", "worker/model", 1)
        on_attempt("succeeded", model_call, "worker", "worker/model", 1)
        return {
            "action": "respond",
            "message": "orchestrated",
            "reason": "safe response",
        }, model_call

    def record_result(self, step, action, result) -> None:
        self.recorded.append((step, action, result))

    @staticmethod
    def error_payload(error: Exception) -> dict[str, str]:
        return {"error": str(error)}


class RetryingFakeOrchestrator(FakeOrchestrator):
    def action_for_step_traced(
        self,
        *,
        trace_context,
        on_attempt,
        **_kwargs,
    ):
        failed_call = trace_context.new_model_call()
        on_attempt("started", failed_call, "worker-a", "worker/model-a", 1)
        on_attempt("failed", failed_call, "worker-a", "worker/model-a", 1)
        successful_call = trace_context.new_model_call()
        on_attempt("started", successful_call, "worker-b", "worker/model-b", 2)
        on_attempt("succeeded", successful_call, "worker-b", "worker/model-b", 2)
        return {
            "action": "respond",
            "message": "orchestrated fallback",
            "reason": "safe response",
        }, successful_call


class TaskCheckpointLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.environment = patch.dict(
            os.environ,
            {"AOIA_HOME": str(self.root / "aoia-home")},
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    @staticmethod
    def force_model_path(runtime: main.AgentRuntime):
        return (
            patch.object(runtime, "handle_external_review_route", return_value=False),
            patch.object(runtime, "handle_local_route", return_value=False),
            patch.object(runtime, "handle_knowledge_route", return_value=False),
        )

    def build_runtime(self, response: str) -> tuple[main.AgentRuntime, InspectingProvider]:
        provider = InspectingProvider(response)
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = runtime
        return runtime, provider

    def test_task_anchor_provider_budget_token_handoff_and_terminal_order(self) -> None:
        runtime, provider = self.build_runtime(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "done",
                            "reason": "safe",
                        }
                    ]
                }
            )
        )
        trace = TraceContext.new_request()
        runtime._active_test_trace = trace
        consume_tokens = []
        execute_tokens = []
        original_consume = runtime.task_checkpoint_store.consume_provider_attempt
        original_execute = runtime.executor.execute

        def consume(model_call, *, step_reservation, model_continuation=None):
            consume_tokens.append(step_reservation)
            return original_consume(
                model_call,
                step_reservation=step_reservation,
                model_continuation=model_continuation,
            )

        def execute(action, *args, **kwargs):
            execute_tokens.append(kwargs.get("step_reservation"))
            return original_execute(action, *args, **kwargs)

        route_patches = self.force_model_path(runtime)
        with (
            route_patches[0],
            route_patches[1],
            route_patches[2],
            patch.object(
                runtime.task_checkpoint_store,
                "consume_provider_attempt",
                side_effect=consume,
            ),
            patch.object(runtime.executor, "execute", side_effect=execute),
        ):
            result = runtime.run_text_request(
                "synthetic lifecycle secret",
                trace_context=trace,
                ingress="TUI",
            )

        self.assertEqual(1, provider.calls)
        self.assertEqual(consume_tokens, execute_tokens)
        self.assertIs(consume_tokens[0], execute_tokens[0])
        observed = provider.observed_checkpoint
        self.assertIsNotNone(observed)
        self.assertEqual(TaskPhase.BEFORE_MODEL_CALL, observed.phase)
        self.assertEqual(1, observed.provider_attempts_used)
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(TaskPhase.TERMINAL, checkpoint.phase)
        self.assertEqual(trace.task_id, result["task_id"])

        records = runtime.provenance_store.read_runtime_all()
        request_start = next(
            index
            for index, record in enumerate(records)
            if record["event_type"] == "REQUEST_STARTED"
        )
        request_terminal = max(
            index
            for index, record in enumerate(records)
            if record["event_type"] == "REQUEST_COMPLETED"
        )
        task_terminal = max(
            index
            for index, record in enumerate(records)
            if record["event_type"] == "TASK_CHECKPOINTED"
            and record["task_state"] == "COMPLETED"
        )
        self.assertGreater(request_start, 0)
        self.assertTrue(
            all(
                records[index]["event_type"].startswith("TASK_CHECKPOINT")
                for index in range(request_start)
            )
        )
        self.assertLess(task_terminal, request_terminal)
        correlated = [
            record
            for record in records
            if record.get("request_id") == trace.request_id
        ]
        self.assertEqual({trace.task_id}, {record["task_id"] for record in correlated})
        session_records = [
            json.loads(line)
            for line in runtime.session_log.read_text(encoding="utf-8").splitlines()
        ]
        model_attempts = [
            record
            for record in session_records
            if record["kind"] == "model_call_attempt"
        ]
        self.assertEqual({trace.task_id}, {record["task_id"] for record in model_attempts})
        serialized = runtime.provenance_store.runtime_log_path.read_text(encoding="utf-8")
        self.assertNotIn("synthetic lifecycle secret", serialized)

    def test_pure_command_is_terminal_before_success_receipt(self) -> None:
        runtime, provider = self.build_runtime("unused")
        result = runtime.run_text_request("/status", ingress="WEB")
        checkpoint = runtime.task_checkpoint_store.load(result["task_id"])
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(0, provider.calls)
        records = runtime.provenance_store.read_runtime_all()
        terminal_checkpoint_index = max(
            index
            for index, record in enumerate(records)
            if record["event_type"] == "TASK_CHECKPOINTED"
            and record["task_state"] == "COMPLETED"
        )
        request_index = max(
            index
            for index, record in enumerate(records)
            if record["event_type"] == "REQUEST_COMPLETED"
        )
        self.assertLess(terminal_checkpoint_index, request_index)
        self.assertTrue(records[request_index]["success"])

    def test_multiaction_plan_checkpoints_between_steps(self) -> None:
        (self.project / "fixture.txt").write_text("safe\n", encoding="utf-8")
        runtime, _provider = self.build_runtime(
            json.dumps(
                {
                    "plan": [
                        {"action": "read_file", "path": "fixture.txt"},
                        {
                            "action": "respond",
                            "message": "done",
                            "reason": "safe",
                        },
                    ]
                }
            )
        )
        trace = TraceContext.new_request()
        runtime._active_test_trace = trace
        route_patches = self.force_model_path(runtime)
        with route_patches[0], route_patches[1], route_patches[2]:
            runtime.run_text_request("read then respond", trace_context=trace)

        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(2, checkpoint.step_index)
        self.assertEqual(1, checkpoint.provider_attempts_used)
        reasons = [transition.reason_code for transition in checkpoint.transitions]
        first_between = reasons.index("TASK_BETWEEN_STEPS")
        self.assertLess(first_between, len(reasons) - 1)
        self.assertEqual(2, reasons.count("TASK_STEP_RESERVED"))

    def test_orchestrator_continuation_keeps_one_step_and_same_token(self) -> None:
        runtime, _provider = self.build_runtime("unused")
        runtime.use_orchestrator = True
        runtime.orchestrator = FakeOrchestrator()
        consumed = []
        executed = []
        original_consume = runtime.task_checkpoint_store.consume_provider_attempt
        original_execute = runtime.executor.execute

        def consume(model_call, *, step_reservation, model_continuation=None):
            consumed.append((step_reservation, model_continuation))
            return original_consume(
                model_call,
                step_reservation=step_reservation,
                model_continuation=model_continuation,
            )

        def execute(action, *args, **kwargs):
            executed.append(kwargs["step_reservation"])
            return original_execute(action, *args, **kwargs)

        route_patches = self.force_model_path(runtime)
        with (
            route_patches[0],
            route_patches[1],
            route_patches[2],
            patch.object(
                runtime.task_checkpoint_store,
                "consume_provider_attempt",
                side_effect=consume,
            ),
            patch.object(runtime.executor, "execute", side_effect=execute),
        ):
            result = runtime.run_text_request("orchestrate one response")

        checkpoint = runtime.task_checkpoint_store.load(result["task_id"])
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(1, checkpoint.step_index)
        self.assertEqual(2, checkpoint.provider_attempts_used)
        self.assertEqual(2, len(consumed))
        self.assertIs(consumed[0][0], consumed[1][0])
        self.assertIsNotNone(consumed[1][1])
        self.assertIs(consumed[1][0], executed[0])

    def test_empty_plan_preserves_reactive_response_with_truthful_budget(self) -> None:
        provider = SequencedProvider(
            [
                json.dumps({"plan": []}),
                json.dumps(
                    {
                        "action": "respond",
                        "message": "reactive response",
                        "reason": "safe",
                    }
                ),
            ]
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = runtime
        trace = TraceContext.new_request()
        runtime._active_test_trace = trace
        consumed = []
        executed = []
        original_consume = runtime.task_checkpoint_store.consume_provider_attempt
        original_execute = runtime.executor.execute

        def consume(model_call, *, step_reservation, model_continuation=None):
            consumed.append((step_reservation, model_continuation))
            return original_consume(
                model_call,
                step_reservation=step_reservation,
                model_continuation=model_continuation,
            )

        def execute(action, *args, **kwargs):
            executed.append(kwargs["step_reservation"])
            return original_execute(action, *args, **kwargs)

        route_patches = self.force_model_path(runtime)
        with (
            route_patches[0],
            route_patches[1],
            route_patches[2],
            patch.object(
                runtime.task_checkpoint_store,
                "consume_provider_attempt",
                side_effect=consume,
            ),
            patch.object(runtime.executor, "execute", side_effect=execute),
        ):
            result = runtime.run_text_request(
                "fall back reactively",
                trace_context=trace,
            )

        self.assertEqual(2, provider.calls)
        self.assertIn("reactive response", result["transcript"])
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(1, checkpoint.step_index)
        self.assertEqual(2, checkpoint.provider_attempts_used)
        reasons = [transition.reason_code for transition in checkpoint.transitions]
        self.assertEqual(1, reasons.count("TASK_STEP_RESERVED"))
        self.assertEqual(1, reasons.count("TASK_MODEL_CONTINUATION_STARTED"))
        self.assertEqual(2, len(consumed))
        self.assertIs(consumed[0][0], consumed[1][0])
        self.assertIsNotNone(consumed[1][1])
        self.assertEqual([consumed[1][0]], executed)

    def test_orchestrator_retry_consumes_continuation_only_once(self) -> None:
        runtime, _provider = self.build_runtime("unused")
        runtime.use_orchestrator = True
        runtime.orchestrator = RetryingFakeOrchestrator()
        consumed = []
        original_consume = runtime.task_checkpoint_store.consume_provider_attempt

        def consume(model_call, *, step_reservation, model_continuation=None):
            consumed.append((step_reservation, model_continuation))
            return original_consume(
                model_call,
                step_reservation=step_reservation,
                model_continuation=model_continuation,
            )

        route_patches = self.force_model_path(runtime)
        with (
            route_patches[0],
            route_patches[1],
            route_patches[2],
            patch.object(
                runtime.task_checkpoint_store,
                "consume_provider_attempt",
                side_effect=consume,
            ),
        ):
            result = runtime.run_text_request("orchestrate with fallback")

        checkpoint = runtime.task_checkpoint_store.load(result["task_id"])
        self.assertIsNotNone(checkpoint)
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(1, checkpoint.step_index)
        self.assertEqual(3, checkpoint.provider_attempts_used)
        self.assertEqual(3, len(consumed))
        self.assertIsNone(consumed[0][1])
        self.assertIsNotNone(consumed[1][1])
        self.assertIsNone(consumed[2][1])
        self.assertIs(consumed[0][0], consumed[1][0])
        self.assertIs(consumed[1][0], consumed[2][0])

    def test_persistence_failure_never_becomes_task_or_request_success(self) -> None:
        runtime, provider = self.build_runtime(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "done",
                            "reason": "safe",
                        }
                    ]
                }
            )
        )
        trace = TraceContext.new_request()
        runtime._active_test_trace = trace
        original_append = runtime.provenance_store._append_runtime_without_recovery
        failed = False

        def fail_action_terminal_once(event):
            nonlocal failed
            if not failed and event.event_type == "ACTION_DISPATCH_SUCCEEDED":
                failed = True
                raise ProvenanceAppendError("forced terminal persistence fault")
            return original_append(event)

        route_patches = self.force_model_path(runtime)
        with (
            route_patches[0],
            route_patches[1],
            route_patches[2],
            patch.object(
                runtime.provenance_store,
                "_append_runtime_without_recovery",
                side_effect=fail_action_terminal_once,
            ),
        ):
            with self.assertRaises(ProvenanceAppendError):
                runtime.run_text_request("one action", trace_context=trace)

        self.assertEqual(1, provider.calls)
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        self.assertIsNot(checkpoint.state, TaskState.COMPLETED)
        request_terminals = [
            record
            for record in runtime.provenance_store.read_runtime_all()
            if record["event_type"] == "REQUEST_COMPLETED"
        ]
        self.assertNotIn(True, [record["success"] for record in request_terminals])

    def test_operator_and_cli_live_calls_have_terminal_tasks(self) -> None:
        provider_result = ProviderRuntimeResult(
            provider_id="kimi_chat",
            model_id="synthetic-model",
            mode="live",
            status=LIVE_SUCCESS,
            redacted_request_preview="redacted",
            response_text="synthetic response",
        )
        with patch(
            "runtime.providers.selector.run_selected_provider",
            return_value=provider_result,
        ):
            operator = webapp.build_operator_chat_payload(
                {
                    "provider_id": "kimi_chat",
                    "model_id": "synthetic-model",
                    "prompt": "operator secret",
                }
            )
        self.assertTrue(operator["ok"])

        with (
            patch.object(provider_cli, "run_selected_provider", return_value=provider_result),
            redirect_stdout(StringIO()),
        ):
            exit_code = provider_cli.main(
                [
                    "--provider",
                    "kimi_chat",
                    "--model",
                    "synthetic-model",
                    "--prompt",
                    "cli secret",
                    "--max-tokens",
                    "32",
                    "--live",
                    "--acknowledge-live-provider-test",
                    "--activate-manual-live-test",
                ]
            )
        self.assertEqual(0, exit_code)
        store = AppendOnlyProvenanceStore(runtime_state_dir(webapp.PROJECT_DIR) / "state")
        records = store.read_runtime_all()
        for ingress in ("OPERATOR_API", "CLI"):
            request = next(
                record
                for record in records
                if record["event_type"] == "REQUEST_STARTED"
                and record["ingress"] == ingress
            )
            task_terminals = [
                record
                for record in records
                if record["event_type"] == "TASK_CHECKPOINTED"
                and record["task_id"] == request["task_id"]
                and record["task_state"] == "COMPLETED"
            ]
            self.assertEqual(1, len(task_terminals))
            request_terminal = next(
                record
                for record in records
                if record["event_type"] == "REQUEST_COMPLETED"
                and record["task_id"] == request["task_id"]
            )
            self.assertTrue(request_terminal["success"])
        serialized = store.runtime_log_path.read_text(encoding="utf-8")
        self.assertNotIn("operator secret", serialized)
        self.assertNotIn("cli secret", serialized)

    def test_operator_and_cli_provider_failures_are_terminal_not_success(self) -> None:
        with (
            patch(
                "runtime.providers.selector.run_selected_provider",
                side_effect=RuntimeError("synthetic operator provider fault"),
            ),
            self.assertRaisesRegex(RuntimeError, "operator provider fault"),
        ):
            webapp.build_operator_chat_payload(
                {
                    "provider_id": "kimi_chat",
                    "model_id": "synthetic-model",
                    "prompt": "operator failure secret",
                }
            )

        with (
            patch.object(
                provider_cli,
                "run_selected_provider",
                side_effect=RuntimeError("synthetic cli provider fault"),
            ),
            redirect_stdout(StringIO()),
            self.assertRaisesRegex(RuntimeError, "cli provider fault"),
        ):
            provider_cli.main(
                [
                    "--provider",
                    "kimi_chat",
                    "--model",
                    "synthetic-model",
                    "--prompt",
                    "cli failure secret",
                    "--max-tokens",
                    "32",
                    "--live",
                    "--acknowledge-live-provider-test",
                    "--activate-manual-live-test",
                ]
            )

        store = AppendOnlyProvenanceStore(runtime_state_dir(webapp.PROJECT_DIR) / "state")
        records = store.read_runtime_all()
        for ingress in ("OPERATOR_API", "CLI"):
            request = next(
                record
                for record in records
                if record["event_type"] == "REQUEST_STARTED"
                and record["ingress"] == ingress
            )
            terminal = next(
                record
                for record in records
                if record["event_type"] == "REQUEST_COMPLETED"
                and record["task_id"] == request["task_id"]
            )
            self.assertFalse(terminal["success"])
            task_terminal = next(
                record
                for record in records
                if record["event_type"] == "TASK_CHECKPOINTED"
                and record["task_id"] == request["task_id"]
                and record["task_state"] == "FAILED"
            )
            self.assertEqual("TERMINAL", task_terminal["task_phase"])
        serialized = store.runtime_log_path.read_text(encoding="utf-8")
        self.assertNotIn("operator failure secret", serialized)
        self.assertNotIn("cli failure secret", serialized)
        self.assertNotIn("synthetic operator provider fault", serialized)
        self.assertNotIn("synthetic cli provider fault", serialized)

    def test_cli_invalid_input_keeps_json_exit_two_and_makes_no_call(self) -> None:
        output = StringIO()
        with (
            patch.object(provider_cli, "run_selected_provider") as provider_call,
            redirect_stdout(output),
        ):
            exit_code = provider_cli.main(
                [
                    "--provider",
                    "not-a-provider",
                    "--model",
                    "synthetic-model",
                    "--prompt",
                    "must not be sent",
                    "--max-tokens",
                    "32",
                    "--live",
                    "--acknowledge-live-provider-test",
                    "--activate-manual-live-test",
                ]
            )
        self.assertEqual(2, exit_code)
        self.assertEqual("invalid", json.loads(output.getvalue())["status"])
        provider_call.assert_not_called()

    def test_task_identity_is_validated_and_every_main_dispatch_has_token(self) -> None:
        trace = TraceContext.new_request()
        other = TraceContext.new_request()
        mismatched_model = ModelCallContext(
            request_id=trace.request_id,
            trace_id=trace.trace_id,
            task_id=other.task_id,
            model_call_id=other.new_model_call().model_call_id,
        )
        with self.assertRaises(ValueError):
            main.AgentRuntime._event_identity_fields(trace, mismatched_model)

        source = Path(main.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        dispatches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not (
                isinstance(function, ast.Attribute)
                and function.attr == "execute"
                and isinstance(function.value, ast.Attribute)
                and function.value.attr == "executor"
            ):
                continue
            dispatches.append(node)
        self.assertGreater(len(dispatches), 0)
        for dispatch in dispatches:
            self.assertIn(
                "step_reservation",
                {keyword.arg for keyword in dispatch.keywords},
                msg=f"executor call at line {dispatch.lineno} lacks a typed step token",
            )


if __name__ == "__main__":
    unittest.main()
