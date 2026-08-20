from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import main
import tools.executor as executor_module
from runtime import webapp
from runtime.providers import cli as provider_cli
from runtime.providers.contracts import LIVE_SUCCESS, ProviderRuntimeResult
from runtime.safety.atomic_persistence import PersistenceError
from runtime.task_checkpoints import (
    TaskPhase,
    TaskState,
    safe_context_metadata,
)
from runtime.task_recovery import (
    RecoveryClaimStatus,
    RecoveryClassification,
    RecoveryInputError,
    RecoveryOperationStatus,
    TaskRecoveryService,
)
from tools.capability_policy import evaluate_action_policy
from tools.executor import ExecutionEngine, ToolSpec
from tools.memory import MemoryStore
from runtime.trace_context import TraceContext


class _SimulatedProcessDeath(BaseException):
    pass


class _ObservingProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0
        self.runtime: main.AgentRuntime | None = None
        self.active_token_seen = False
        self.contender_error: BaseException | None = None

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        assert self.runtime is not None
        token = self.runtime._task_execution_token.get()
        assert token is not None
        self.runtime.task_recovery_service.classify_under_claim(token.task_id, token)
        self.active_token_seen = True
        contender = TaskRecoveryService(
            self.runtime.memory_store.paths.state_dir,
            project_dir=self.runtime.project_dir,
            checkpoint_store=self.runtime.task_checkpoint_store,
            idempotency_store=self.runtime.executor.idempotency_store,
            provenance_store=self.runtime.provenance_store,
            lock_timeout_seconds=0.01,
        )
        try:
            with contender.execution_guard(token.task_id):
                raise AssertionError("contender unexpectedly acquired the live task")
        except PersistenceError as error:
            self.contender_error = error
        return self.response

    def describe(self) -> str:
        return "fake/integration"

    def active_fallback_chain(self) -> list[str]:
        return ["fake/integration"]

    def provider_status(self) -> list[dict[str, object]]:
        return []

    def available_models(self) -> list[str]:
        return ["fake/integration"]


class RecoveryRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        )
        self.root = Path(self.temporary.name)
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
        self.temporary.cleanup()

    @staticmethod
    def _force_model_path(runtime: main.AgentRuntime) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(
            patch.object(runtime, "handle_external_review_route", return_value=False)
        )
        stack.enter_context(
            patch.object(runtime, "handle_local_route", return_value=False)
        )
        stack.enter_context(
            patch.object(runtime, "handle_knowledge_route", return_value=False)
        )
        return stack

    @staticmethod
    def _claim_payloads(state_dir: Path) -> list[dict[str, object]]:
        root = state_dir / "recovery" / "claims"
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(root.glob("*/*.json"))
        ]

    def _crash_nonstandalone_action(
        self,
        runtime: main.AgentRuntime,
        action: dict[str, object],
        handler: Mock,
        *,
        waiting_for_approval: bool = False,
    ):
        trace = TraceContext.new_request()
        request_text = f"nonstandalone recovery for {action['action']}"
        runtime.task_checkpoint_store.create_task(
            trace,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )
        runtime._start_task(trace, request_text)
        reservation = runtime.task_checkpoint_store.reserve_step(trace.task_id)
        name = str(action["action"])
        runtime.executor.tools[name] = ToolSpec(
            name,
            handler,
            "nonstandalone recovery handler",
        )
        boundary = (
            patch.object(
                runtime.executor,
                "_request_approval",
                side_effect=_SimulatedProcessDeath("approval wait crash"),
            )
            if waiting_for_approval
            else patch.object(
                runtime.executor,
                "_before_tool_dispatch",
                side_effect=_SimulatedProcessDeath("reserved action crash"),
            )
        )
        with boundary:
            with self.assertRaises(_SimulatedProcessDeath):
                with runtime._live_task_execution_guard(trace, request_text) as token:
                    runtime.executor.execute(
                        action,
                        action_context=trace.new_action(),
                        step_reservation=reservation,
                        recovery_token=token,
                    )
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        return trace, checkpoint

    def test_request_holds_one_live_generation_through_provider_and_handler(self) -> None:
        provider = _ObservingProvider(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "done",
                            "reason": "integration test",
                        }
                    ]
                }
            )
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = runtime
        handler_observations: list[int] = []
        original = runtime.executor.tools["respond"]

        def observing_handler(action):
            token = runtime._task_execution_token.get()
            self.assertIsNotNone(token)
            assert token is not None
            runtime.task_recovery_service.classify_under_claim(
                token.task_id,
                token,
            )
            handler_observations.append(token.generation)
            return original.handler(action)

        runtime.executor.tools["respond"] = ToolSpec(
            original.name,
            observing_handler,
            original.description,
        )
        trace = TraceContext.new_request()
        with self._force_model_path(runtime):
            result = runtime.run_text_request(
                "perform one safe response",
                trace_context=trace,
                ingress="TUI",
            )

        self.assertTrue(provider.active_token_seen)
        self.assertIsNotNone(provider.contender_error)
        self.assertEqual([1], handler_observations)
        self.assertEqual(trace.task_id, result["task_id"])
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        claim = runtime.task_recovery_service._read_claim(trace.task_id)
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertEqual(1, claim.generation)
        self.assertIs(RecoveryClaimStatus.RELEASED, claim.status)
        records = runtime.provenance_store.read_runtime_all()
        self.assertEqual(
            1,
            sum(
                item["event_type"] == "RECOVERY_CLAIMED"
                and item["task_id"] == trace.task_id
                for item in records
            ),
        )

    def test_startup_discovery_is_read_only_and_never_dispatches(self) -> None:
        provider = _ObservingProvider('{}')
        first = main.AgentRuntime(provider, "test prompt", self.project)
        trace = TraceContext.new_request()
        created = first.task_checkpoint_store.create_task(
            trace,
            max_steps=1,
            retry_budget=1,
            safe_context=safe_context_metadata("pending startup task"),
        )

        second_provider = _ObservingProvider('{}')
        second = main.AgentRuntime(second_provider, "test prompt", self.project)

        self.assertEqual(0, provider.calls)
        self.assertEqual(0, second_provider.calls)
        self.assertTrue(
            any(
                decision.task_id == trace.task_id
                for decision in second.recovery_discovery.decisions
            )
        )
        unchanged = second.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(created.checkpoint_hash, unchanged.checkpoint_hash)

    def test_crashed_slash_command_is_never_repeated_as_safe_model_resume(self) -> None:
        provider = _ObservingProvider("{}")
        first = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = first
        calls = 0

        def mutating_command(_args, _runtime, _trace_context=None):
            nonlocal calls
            calls += 1
            raise _SimulatedProcessDeath(
                "command effect completed before terminal request checkpoint"
            )

        first.command_registry.register("recovery-mutation", mutating_command)
        trace = TraceContext.new_request()
        with self.assertRaises(_SimulatedProcessDeath):
            first.dispatch_text_request("/recovery-mutation", trace)

        checkpoint = first.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskState.RUNNING, checkpoint.state)
        self.assertEqual(TaskPhase.BETWEEN_STEPS, checkpoint.phase)
        self.assertEqual(0, checkpoint.step_index)
        decision = first.task_recovery_service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(
            "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            decision.reason_code,
        )
        self.assertEqual(1, calls)
        self.assertEqual(0, provider.calls)

        restarted_provider = _ObservingProvider("{}")
        restarted = main.AgentRuntime(
            restarted_provider,
            "test prompt",
            self.project,
        )
        restarted_provider.runtime = restarted
        restarted.command_registry.register(
            "recovery-mutation",
            mutating_command,
        )
        with self.assertRaises(RecoveryInputError):
            restarted.resume_recovery_task(
                trace.task_id,
                request_text="/recovery-mutation",
            )

        self.assertEqual(1, calls)
        self.assertEqual(0, restarted_provider.calls)
        unchanged = restarted.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(checkpoint.checkpoint_hash, unchanged.checkpoint_hash)

    def test_created_task_resumes_with_same_task_and_new_request_identity(self) -> None:
        request_text = "resume this exact created request"
        provider = _ObservingProvider(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "recovered",
                            "reason": "recovery integration test",
                        }
                    ]
                }
            )
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = runtime
        original_trace = TraceContext.new_request()
        runtime.task_checkpoint_store.create_task(
            original_trace,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )

        with self._force_model_path(runtime), redirect_stdout(StringIO()):
            recovered = runtime.resume_recovery_task(
                original_trace.task_id,
                request_text=request_text,
            )

        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        self.assertTrue(recovered.success)
        self.assertEqual(original_trace.task_id, recovered.task_id)
        self.assertNotEqual(original_trace.request_id, recovered.request_id)
        self.assertNotEqual(original_trace.trace_id, recovered.trace_id)
        self.assertEqual(1, provider.calls)
        self.assertTrue(provider.active_token_seen)
        checkpoint = runtime.task_checkpoint_store.load(original_trace.task_id)
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)
        self.assertEqual(TaskPhase.TERMINAL, checkpoint.phase)

    def test_before_model_recovery_reuses_step_and_only_debits_provider_attempt(self) -> None:
        request_text = "resume this exact pre-model request"
        first_provider = _ObservingProvider("{}")
        first = main.AgentRuntime(first_provider, "test prompt", self.project)
        original_trace = TraceContext.new_request()
        first.task_checkpoint_store.create_task(
            original_trace,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )
        first._start_task(original_trace, request_text)
        first.task_checkpoint_store.reserve_step(original_trace.task_id)
        before = first.task_checkpoint_store.load(original_trace.task_id)
        self.assertIsNotNone(before)
        assert before is not None
        self.assertEqual(TaskPhase.BEFORE_MODEL_CALL, before.phase)

        provider = _ObservingProvider(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "recovered",
                            "reason": "recovery integration test",
                        }
                    ]
                }
            )
        )
        restarted = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = restarted
        with (
            patch.object(
                restarted.command_registry,
                "execute",
                side_effect=AssertionError("command routing repeated"),
            ),
            patch.object(
                restarted,
                "handle_external_review_route",
                side_effect=AssertionError("external routing repeated"),
            ),
            patch.object(
                restarted,
                "handle_local_route",
                side_effect=AssertionError("local routing repeated"),
            ),
            patch.object(
                restarted,
                "handle_knowledge_route",
                side_effect=AssertionError("knowledge routing repeated"),
            ),
            patch.object(
                restarted,
                "bootstrap_local_context",
                side_effect=AssertionError("local bootstrap repeated"),
            ),
            redirect_stdout(StringIO()),
        ):
            recovered = restarted.resume_recovery_task(
                original_trace.task_id,
                request_text=request_text,
            )

        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        self.assertEqual(1, provider.calls)
        after = restarted.task_checkpoint_store.load(original_trace.task_id)
        self.assertIsNotNone(after)
        assert after is not None
        self.assertEqual(before.step_index, after.step_index)
        self.assertEqual(before.remaining_steps, after.remaining_steps)
        self.assertEqual(
            before.provider_attempts_used + 1,
            after.provider_attempts_used,
        )
        self.assertEqual(
            before.remaining_retry_budget - 1,
            after.remaining_retry_budget,
        )

    def test_safe_between_steps_resume_uses_normal_next_step_budget(self) -> None:
        request_text = "continue this safe read-only request"
        first_provider = _ObservingProvider("{}")
        first = main.AgentRuntime(first_provider, "test prompt", self.project)
        original_trace = TraceContext.new_request()
        first.task_checkpoint_store.create_task(
            original_trace,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )
        before = first._start_task(original_trace, request_text)
        self.assertEqual(TaskPhase.BETWEEN_STEPS, before.phase)
        self.assertEqual(0, before.step_index)

        provider = _ObservingProvider(
            json.dumps(
                {
                    "plan": [
                        {
                            "action": "respond",
                            "message": "recovered",
                            "reason": "safe continuation",
                        }
                    ]
                }
            )
        )
        restarted = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = restarted
        with self._force_model_path(restarted), redirect_stdout(StringIO()):
            recovered = restarted.resume_recovery_task(
                original_trace.task_id,
                request_text=request_text,
            )

        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        after = restarted.task_checkpoint_store.load(original_trace.task_id)
        self.assertIsNotNone(after)
        assert after is not None
        self.assertEqual(before.step_index + 1, after.step_index)
        self.assertEqual(before.remaining_steps - 1, after.remaining_steps)
        self.assertEqual(
            before.provider_attempts_used + 1,
            after.provider_attempts_used,
        )
        self.assertEqual(
            before.remaining_retry_budget - 1,
            after.remaining_retry_budget,
        )

    def test_terminal_task_is_shown_but_never_resumed(self) -> None:
        request_text = "already completed request"
        provider = _ObservingProvider("{}")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        original_trace = TraceContext.new_request()
        runtime.task_checkpoint_store.create_task(
            original_trace,
            max_steps=1,
            retry_budget=1,
            safe_context=safe_context_metadata(request_text),
        )
        runtime._finish_task(original_trace, TaskState.COMPLETED)

        shown = runtime.show_recovery_task(original_trace.task_id)
        self.assertIs(RecoveryClassification.ALREADY_COMPLETED, shown.classification)
        with self.assertRaises(RecoveryInputError):
            runtime.resume_recovery_task(
                original_trace.task_id,
                request_text=request_text,
            )

        self.assertEqual(0, provider.calls)
        self.assertEqual({}, runtime.task_recovery_service._trusted_inputs)
        final = runtime.task_checkpoint_store.load(original_trace.task_id)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertEqual(TaskState.COMPLETED, final.state)

    def test_waiting_action_resume_requests_fresh_approval_and_preserves_budget(self) -> None:
        provider = _ObservingProvider("{}")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        action = {
            "action": "write_file",
            "path": "recovered.txt",
            "content": "bounded integration content",
        }
        handler = Mock(return_value={"success": True})
        runtime.executor.tools["write_file"] = ToolSpec(
            "write_file", handler, "recovery integration handler"
        )
        with patch.object(
            runtime.executor,
            "_request_approval",
            side_effect=_SimulatedProcessDeath("approval wait crash"),
        ):
            with self.assertRaises(_SimulatedProcessDeath):
                runtime.executor.execute(action)

        pending = runtime.list_recovery_tasks()
        self.assertEqual(1, len(pending))
        decision = runtime.show_recovery_task(pending[0].task_id or "")
        self.assertIs(
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
            decision.classification,
        )
        checkpoint = runtime.task_checkpoint_store.load(decision.task_id or "")
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        budget = (
            checkpoint.step_index,
            checkpoint.remaining_steps,
            checkpoint.provider_attempts_used,
            checkpoint.remaining_retry_budget,
        )

        with patch.object(
            runtime.executor,
            "_request_approval",
            return_value=True,
        ) as fresh_approval:
            recovered = runtime.request_fresh_recovery_approval(
                checkpoint.task_id,
                action=action,
            )

        fresh_approval.assert_called_once()
        handler.assert_called_once()
        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        final = runtime.task_checkpoint_store.load(checkpoint.task_id)
        self.assertIsNotNone(final)
        assert final is not None
        self.assertEqual(TaskState.COMPLETED, final.state)
        self.assertEqual(
            budget,
            (
                final.step_index,
                final.remaining_steps,
                final.provider_attempts_used,
                final.remaining_retry_budget,
            ),
        )

    def test_tightened_policy_blocks_waiting_recovery_without_dispatch(self) -> None:
        provider = _ObservingProvider("{}")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        action = {
            "action": "write_file",
            "path": "blocked.txt",
            "content": "must not dispatch",
        }
        handler = Mock(return_value={"success": True})
        runtime.executor.tools["write_file"] = ToolSpec(
            "write_file", handler, "policy tightening handler"
        )
        with patch.object(
            runtime.executor,
            "_request_approval",
            side_effect=_SimulatedProcessDeath("approval wait crash"),
        ):
            with self.assertRaises(_SimulatedProcessDeath):
                runtime.executor.execute(action)
        waiting = next(
            item
            for item in runtime.list_recovery_tasks()
            if item.classification
            is RecoveryClassification.WAITING_FOR_FRESH_APPROVAL
        )

        def tightened_policy(candidate, context=None):
            return replace(
                evaluate_action_policy(candidate, context),
                allowed=False,
                requires_confirmation=False,
                reason_code="ACTION_NOT_CLASSIFIED",
                reason="Current policy no longer authorizes this action.",
                runtime_requires_confirmation=False,
            )

        with patch.object(
            executor_module,
            "evaluate_action_policy",
            side_effect=tightened_policy,
        ):
            recovered = runtime.request_fresh_recovery_approval(
                waiting.task_id or "",
                action=action,
            )

        handler.assert_not_called()
        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        self.assertTrue(recovered.success)
        self.assertEqual(TaskState.BLOCKED.value, recovered.task_state)
        final = runtime.task_checkpoint_store.load(waiting.task_id or "")
        self.assertIsNotNone(final)
        assert final is not None
        self.assertEqual(TaskState.BLOCKED, final.state)
        self.assertEqual(TaskPhase.TERMINAL, final.phase)

    def test_nonstandalone_recovery_terminalizes_exact_aggregate_outcome(self) -> None:
        provider = _ObservingProvider("{}")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)

        succeeded_action = {"action": "read_file", "path": "success.txt"}
        succeeded_handler = Mock(
            return_value={"success": True, "content": "bounded"}
        )
        succeeded_trace, _ = self._crash_nonstandalone_action(
            runtime,
            succeeded_action,
            succeeded_handler,
        )
        succeeded = runtime.resume_recovery_task(
            succeeded_trace.task_id,
            action=succeeded_action,
        )
        self.assertEqual(TaskState.PARTIAL.value, succeeded.task_state)
        succeeded_final = runtime.task_checkpoint_store.load(
            succeeded_trace.task_id
        )
        self.assertIsNotNone(succeeded_final)
        assert succeeded_final is not None
        self.assertEqual(TaskState.PARTIAL, succeeded_final.state)
        self.assertEqual(TaskPhase.TERMINAL, succeeded_final.phase)
        self.assertIsNone(succeeded_final.current_action_id)
        self.assertIsNone(succeeded_final.current_idempotency_key)
        self.assertIsNone(succeeded_final.current_action_fingerprint)
        succeeded_handler.assert_called_once()

        respond_action = {
            "action": "respond",
            "message": "recovered response",
        }
        respond_handler = Mock(
            return_value={
                "success": True,
                "message": "recovered response",
                "stop_loop": True,
            }
        )
        respond_trace, _ = self._crash_nonstandalone_action(
            runtime,
            respond_action,
            respond_handler,
        )
        responded = runtime.resume_recovery_task(
            respond_trace.task_id,
            action=respond_action,
        )
        self.assertEqual(TaskState.COMPLETED.value, responded.task_state)
        respond_handler.assert_called_once()

        failed_action = {"action": "read_file", "path": "failed.txt"}
        failed_handler = Mock(
            return_value={"success": False, "message": "reported failure"}
        )
        failed_trace, _ = self._crash_nonstandalone_action(
            runtime,
            failed_action,
            failed_handler,
        )
        failed = runtime.resume_recovery_task(
            failed_trace.task_id,
            action=failed_action,
        )
        self.assertEqual(TaskState.FAILED.value, failed.task_state)
        failed_handler.assert_called_once()

        blocked_action = {
            "action": "write_file",
            "path": "blocked-nonstandalone.txt",
            "content": "must not dispatch",
        }
        blocked_handler = Mock(return_value={"success": True})
        blocked_trace, _ = self._crash_nonstandalone_action(
            runtime,
            blocked_action,
            blocked_handler,
            waiting_for_approval=True,
        )

        def tightened_policy(candidate, context=None):
            return replace(
                evaluate_action_policy(candidate, context),
                allowed=False,
                requires_confirmation=False,
                reason_code="ACTION_NOT_CLASSIFIED",
                reason="Current policy no longer authorizes this action.",
                runtime_requires_confirmation=False,
            )

        with patch.object(
            executor_module,
            "evaluate_action_policy",
            side_effect=tightened_policy,
        ):
            blocked = runtime.resume_recovery_task(
                blocked_trace.task_id,
                action=blocked_action,
            )
        self.assertEqual(TaskState.BLOCKED.value, blocked.task_state)
        self.assertIs(RecoveryOperationStatus.COMPLETED, blocked.status)
        self.assertTrue(blocked.success)
        blocked_handler.assert_not_called()

        cancelled_action = {
            "action": "write_file",
            "path": "cancelled-nonstandalone.txt",
            "content": "must not dispatch",
        }
        cancelled_handler = Mock(return_value={"success": True})
        cancelled_trace, _ = self._crash_nonstandalone_action(
            runtime,
            cancelled_action,
            cancelled_handler,
            waiting_for_approval=True,
        )
        with patch.object(
            runtime.executor,
            "_request_approval",
            return_value=False,
        ) as fresh_approval:
            cancelled = runtime.resume_recovery_task(
                cancelled_trace.task_id,
                action=cancelled_action,
            )
        fresh_approval.assert_called_once()
        self.assertEqual(TaskState.CANCELLED.value, cancelled.task_state)
        self.assertIs(RecoveryOperationStatus.COMPLETED, cancelled.status)
        self.assertTrue(cancelled.success)
        cancelled_handler.assert_not_called()

    def test_local_cancel_handles_waiting_and_reserved_but_rejects_unknown(self) -> None:
        provider = _ObservingProvider("{}")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)

        waiting_action = {
            "action": "write_file",
            "path": "waiting.txt",
            "content": "bounded",
        }
        waiting_handler = Mock(return_value={"success": True})
        runtime.executor.tools["write_file"] = ToolSpec(
            "write_file", waiting_handler, "waiting cancellation handler"
        )
        with patch.object(
            runtime.executor,
            "_request_approval",
            side_effect=_SimulatedProcessDeath("approval wait crash"),
        ):
            with self.assertRaises(_SimulatedProcessDeath):
                runtime.executor.execute(waiting_action)
        waiting = next(
            item
            for item in runtime.list_recovery_tasks()
            if item.classification
            is RecoveryClassification.WAITING_FOR_FRESH_APPROVAL
        )
        waiting_cancelled = runtime.cancel_recovery_task(waiting.task_id or "")
        self.assertIs(RecoveryOperationStatus.CANCELLED, waiting_cancelled.status)
        self.assertFalse(waiting_cancelled.success)
        waiting_handler.assert_not_called()

        reserved_action = {"action": "read_file", "path": "reserved.txt"}
        reserved_handler = Mock(return_value={"success": True, "content": "safe"})
        runtime.executor.tools["read_file"] = ToolSpec(
            "read_file", reserved_handler, "reserved cancellation handler"
        )
        with patch.object(
            runtime.executor,
            "_before_tool_dispatch",
            side_effect=_SimulatedProcessDeath("reserved crash"),
        ):
            with self.assertRaises(_SimulatedProcessDeath):
                runtime.executor.execute(reserved_action)
        reserved = next(
            item
            for item in runtime.list_recovery_tasks()
            if item.idempotency_state == "RESERVED"
        )
        reserved_cancelled = runtime.cancel_recovery_task(reserved.task_id or "")
        self.assertIs(RecoveryOperationStatus.CANCELLED, reserved_cancelled.status)
        self.assertFalse(reserved_cancelled.success)
        reserved_handler.assert_not_called()

        unknown_action = {"action": "read_file", "path": "unknown.txt"}
        unknown_handler = Mock(
            side_effect=_SimulatedProcessDeath("handler outcome unknown")
        )
        runtime.executor.tools["read_file"] = ToolSpec(
            "read_file", unknown_handler, "unknown cancellation handler"
        )
        with self.assertRaises(_SimulatedProcessDeath):
            runtime.executor.execute(unknown_action)
        unknown = next(
            item
            for item in runtime.list_recovery_tasks()
            if item.classification is RecoveryClassification.UNKNOWN_OUTCOME
        )
        before_unknown = runtime.task_checkpoint_store.load(unknown.task_id or "")
        self.assertIsNotNone(before_unknown)
        assert before_unknown is not None
        with self.assertRaises(RecoveryInputError):
            runtime.cancel_recovery_task(before_unknown.task_id)
        unchanged = runtime.task_checkpoint_store.load(before_unknown.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(before_unknown.checkpoint_hash, unchanged.checkpoint_hash)
        self.assertEqual(before_unknown.state, unchanged.state)
        acknowledged = runtime.acknowledge_recovery_task(before_unknown.task_id)
        self.assertIs(RecoveryOperationStatus.ACKNOWLEDGED, acknowledged.status)
        self.assertFalse(acknowledged.success)
        after_ack = runtime.task_checkpoint_store.load(before_unknown.task_id)
        self.assertIsNotNone(after_ack)
        assert after_ack is not None
        self.assertEqual(before_unknown.checkpoint_hash, after_ack.checkpoint_hash)
        unknown_handler.assert_called_once()

    def test_direct_executor_call_uses_a_live_guard_at_handler_boundary(self) -> None:
        memory = MemoryStore(self.project, self.project)
        engine = ExecutionEngine(self.project, memory)
        observed: list[tuple[str, int]] = []
        original = engine.tools["respond"]

        def observing_handler(action):
            service = engine.task_recovery_service
            self.assertIsNotNone(service)
            assert service is not None
            self.assertEqual(1, len(service._active_tokens))
            task_id, token = next(iter(service._active_tokens.items()))
            service.classify_under_claim(task_id, token)
            observed.append((task_id, token.generation))
            return original.handler(action)

        engine.tools["respond"] = ToolSpec(
            original.name,
            observing_handler,
            original.description,
        )
        result = engine.execute(
            {"action": "respond", "message": "direct guarded call"}
        )

        self.assertTrue(result["success"])
        self.assertEqual(1, len(observed))
        assert engine.task_recovery_service is not None
        claim = engine.task_recovery_service._read_claim(observed[0][0])
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertIs(RecoveryClaimStatus.RELEASED, claim.status)

    def test_provider_cli_mock_runs_inside_live_claim_and_releases_it(self) -> None:
        state_parent = self.root / "cli-runtime"
        observed_active: list[bool] = []
        result = ProviderRuntimeResult(
            provider_id="kimi_chat",
            model_id="mock-model",
            mode="live",
            status=LIVE_SUCCESS,
            redacted_request_preview="redacted",
            response_text="mocked",
        )

        def provider_side_effect(**_kwargs):
            claims = self._claim_payloads(state_parent / "state")
            observed_active.append(
                len(claims) == 1 and claims[0]["status"] == "ACTIVE"
            )
            return result

        output = StringIO()
        with (
            patch.object(provider_cli, "runtime_state_dir", return_value=state_parent),
            patch.object(
                provider_cli,
                "run_selected_provider",
                side_effect=provider_side_effect,
            ),
            redirect_stdout(output),
        ):
            exit_code = provider_cli.main(
                [
                    "--provider",
                    "kimi_chat",
                    "--model",
                    "mock-model",
                    "--prompt",
                    "mock cli prompt",
                    "--max-tokens",
                    "16",
                    "--live",
                    "--acknowledge-live-provider-test",
                    "--activate-manual-live-test",
                ]
            )

        self.assertEqual(0, exit_code)
        self.assertEqual([True], observed_active)
        payload = json.loads(output.getvalue().strip().splitlines()[-1])
        self.assertTrue(payload["task_id"].startswith("task_"))
        self.assertTrue(payload["request_id"].startswith("request_"))
        self.assertTrue(payload["trace_id"].startswith("trace_"))
        self.assertTrue(payload["model_call_id"].startswith("model_call_"))
        claims = self._claim_payloads(state_parent / "state")
        self.assertEqual("RELEASED", claims[0]["status"])

    def test_operator_chat_mock_uses_live_claim_without_recovery_routes(self) -> None:
        state_parent = self.root / "web-runtime"
        observed_active: list[bool] = []
        result = ProviderRuntimeResult(
            provider_id="kimi_chat",
            model_id="mock-model",
            mode="live",
            status=LIVE_SUCCESS,
            redacted_request_preview="redacted",
            response_text="mocked",
        )

        def provider_side_effect(**_kwargs):
            claims = self._claim_payloads(state_parent / "state")
            observed_active.append(
                len(claims) == 1 and claims[0]["status"] == "ACTIVE"
            )
            return result

        with (
            patch.object(webapp, "PROJECT_DIR", self.project),
            patch(
                "runtime.runtime_paths.runtime_state_dir",
                return_value=state_parent,
            ),
            patch(
                "runtime.providers.selector.run_selected_provider",
                side_effect=provider_side_effect,
            ),
        ):
            payload = webapp.build_operator_chat_payload(
                {
                    "provider_id": "kimi_chat",
                    "model_id": "mock-model",
                    "prompt": "mock operator prompt",
                }
            )

        self.assertTrue(payload["ok"])
        self.assertEqual([True], observed_active)
        claims = self._claim_payloads(state_parent / "state")
        self.assertEqual("RELEASED", claims[0]["status"])
        self.assertIsNone(webapp.route_get_payload("/api/recovery/tasks"))
        status, missing = webapp.route_post_payload(
            "/api/recovery/cancel",
            {"task_id": "task_client_controlled"},
        )
        self.assertEqual(404, status)
        self.assertFalse(missing["ok"])

    def test_active_provider_callsite_inventory_stays_fenced(self) -> None:
        """Make new live-provider callsites opt in to an explicit fence test."""

        repository = Path(main.__file__).resolve().parent.parent
        paths = tuple(
            sorted(
                (
                    *repository.joinpath("runtime").rglob("*.py"),
                    *repository.joinpath("tui").rglob("*.py"),
                )
            )
        )
        watched = {
            "generate", "generate_traced", "generate_with_fallback",
            "run_selected_provider", "create_plan", "action_for_step",
            "create_traced_plan", "action_for_step_traced",
        }
        inventory: set[tuple[str, str, str]] = set()
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parents: dict[ast.AST, ast.AST] = {}
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    parents[child] = node
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                callee = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                    if isinstance(node.func, ast.Name)
                    else None
                )
                if callee not in watched:
                    continue
                owner = node
                function = "<module>"
                while owner in parents:
                    owner = parents[owner]
                    if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function = owner.name
                        break
                inventory.add(
                    (path.relative_to(repository).as_posix(), function, callee)
                )

        self.assertEqual(
            {
                ("runtime/main.py", "ask_model", "generate"),
                ("runtime/main.py", "handle_user_request", "create_plan"),
                ("runtime/main.py", "handle_orchestrated_request", "create_traced_plan"),
                ("runtime/main.py", "handle_orchestrated_request", "action_for_step_traced"),
                ("runtime/orchestrator/gemini_gemma.py", "create_plan", "generate_with_fallback"),
                ("runtime/orchestrator/gemini_gemma.py", "create_traced_plan", "generate_traced"),
                ("runtime/orchestrator/gemini_gemma.py", "action_for_step", "generate"),
                ("runtime/orchestrator/gemini_gemma.py", "action_for_step_traced", "generate"),
                ("runtime/providers/cli.py", "invoke_provider", "run_selected_provider"),
                ("runtime/providers/config.py", "generate", "generate_with_fallback"),
                ("runtime/providers/config.py", "generate_traced", "generate"),
                ("runtime/providers/config.py", "generate_with_fallback", "generate"),
                ("runtime/providers/gemma_provider.py", "generate", "generate"),
                ("runtime/providers/selector.py", "run_configured_provider", "run_selected_provider"),
                ("runtime/webapp.py", "build_operator_chat_payload", "run_selected_provider"),
            },
            inventory,
        )
        source = Path(main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("self.orchestrator.create_plan(", source)
        self.assertNotIn("self.orchestrator.action_for_step(", source)


if __name__ == "__main__":
    unittest.main()
