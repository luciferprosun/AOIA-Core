from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager, nullcontext
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import tools.executor as executor_module
from runtime.task_checkpoints import ApprovalState, TaskPhase, TaskState
from runtime.task_recovery import (
    RecoveryClaimConflictError,
    RecoveryClassification,
    RecoveryDirective,
    RecoveryFencedError,
    RecoveryInputError,
    RecoveryPurpose,
)
from tools.capability_policy import CapabilityClass, evaluate_action_policy
from tools.executor import ExecutionEngine, ToolSpec
from tools.idempotency import (
    IdempotencyState,
    OperationContext,
)
from tools.memory import MemoryStore
from runtime.tools.provenance import (
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import ActionContext, TraceContext


class _CrashBeforeDispatch(BaseException):
    pass


class ReservedActionRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        )
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.root / "aoia-home"),
                "AOIA_LEGACY_FILESYSTEM_ENABLED": "1",
            },
            clear=False,
        )
        self.environment.start()
        self.memory = MemoryStore(
            self.project,
            self.project,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        self.engine = ExecutionEngine(self.project, self.memory)

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def _assert_recovery_checkpoint_identity(
        self,
        checkpoint,
        recovery_identity: tuple[str, str, str],
        *,
        original_request_id: str,
        original_trace_id: str,
    ) -> None:
        self.assertEqual(recovery_identity[0], checkpoint.latest_request_id)
        self.assertEqual(recovery_identity[1], checkpoint.latest_trace_id)
        self.assertEqual(recovery_identity[2], checkpoint.recovery_attempt_id)
        self.assertNotEqual(original_request_id, checkpoint.latest_request_id)
        self.assertNotEqual(original_trace_id, checkpoint.latest_trace_id)

    def _reserve_then_crash(
        self,
        action: dict[str, object],
        *,
        handler: Mock | None = None,
        operation: OperationContext | None = None,
    ):
        operation = operation or OperationContext.new_operation()
        original_context = TraceContext.new_request().new_action()
        handler = handler or Mock(return_value={"success": True})
        name = str(action["action"])
        self.engine.tools[name] = ToolSpec(name, handler, "recovery test handler")
        with (
            patch.object(self.engine, "_request_approval", return_value=True),
            patch.object(
                self.engine,
                "_before_tool_dispatch",
                side_effect=_CrashBeforeDispatch("simulated process death"),
            ),
        ):
            with self.assertRaises(_CrashBeforeDispatch):
                self.engine.execute(
                    action,
                    action_context=original_context,
                    operation_context=operation,
                )

        record = self.engine.idempotency_store.load(operation)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(IdempotencyState.RESERVED, record.state)
        checkpoint = self.engine.task_checkpoint_store.load(record.task_id or "")
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskState.RUNNING, checkpoint.state)
        self.assertEqual(TaskPhase.IDEMPOTENCY_RESERVED, checkpoint.phase)
        self.assertEqual(IdempotencyState.RESERVED.value, checkpoint.current_idempotency_state)
        handler.assert_not_called()
        return operation, record, checkpoint, handler

    def _resume(self, checkpoint, action, *, approval: bool | None = None):
        service = self.engine._get_task_recovery_service()
        approval_patch = (
            patch.object(self.engine, "_request_approval", return_value=approval)
            if approval is not None
            else patch.object(
                self.engine,
                "_request_approval",
                side_effect=AssertionError("unexpected approval request"),
            )
        )
        with service.execution_guard(
            checkpoint.task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with approval_patch as approval_mock:
                result = self.engine.resume_reserved_action(
                    action, recovery_token=token
                )
            recovery_identity = (
                token.request_id,
                token.trace_id,
                token.recovery_attempt_id,
            )
        return result, approval_mock, recovery_identity

    def _pre_p07_then_crash(
        self,
        action: dict[str, object],
        *,
        after_old_grant: bool = False,
    ):
        context = TraceContext.new_request().new_action()
        handler = Mock(return_value={"success": True})
        name = str(action["action"])
        self.engine.tools[name] = ToolSpec(name, handler, "pre-P0.7 test handler")
        approval_behavior = (
            patch.object(self.engine, "_request_approval", return_value=True)
            if after_old_grant
            else patch.object(
                self.engine,
                "_request_approval",
                side_effect=_CrashBeforeDispatch("crash while waiting for approval"),
            )
        )
        reserve_behavior = (
            patch.object(
                self.engine,
                "_reserve_operation",
                side_effect=_CrashBeforeDispatch("crash after old approval"),
            )
            if after_old_grant
            else nullcontext()
        )
        with approval_behavior as approval, reserve_behavior:
            with self.assertRaises(_CrashBeforeDispatch):
                self.engine.execute(action, action_context=context)

        checkpoint = self.engine.task_checkpoint_store.load(context.task_id)
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        expected_phase = (
            TaskPhase.BEFORE_DISPATCH
            if after_old_grant
            else TaskPhase.WAITING_FOR_APPROVAL
        )
        self.assertEqual(expected_phase, checkpoint.phase)
        operation = OperationContext(checkpoint.current_idempotency_key or "")
        self.assertIsNone(self.engine.idempotency_store.load(operation))
        handler.assert_not_called()
        return operation, checkpoint, handler, approval

    def _resume_pre_p07(self, checkpoint, action, *, approval: bool):
        service = self.engine._get_task_recovery_service()
        with service.execution_guard(
            checkpoint.task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with patch.object(
                self.engine, "_request_approval", return_value=approval
            ) as approval_mock:
                result = self.engine.resume_recoverable_action(
                    action, recovery_token=token
                )
            recovery_identity = (
                token.request_id,
                token.trace_id,
                token.recovery_attempt_id,
            )
        return result, approval_mock, recovery_identity

    def _reserve_before_checkpoint_then_crash(
        self,
        action: dict[str, object],
    ):
        context = TraceContext.new_request().new_action()
        handler = Mock(return_value={"success": True})
        name = str(action["action"])
        self.engine.tools[name] = ToolSpec(
            name, handler, "reservation checkpoint-gap test handler"
        )
        real_checkpoint = self.engine._checkpoint_task

        def crash_on_reserved_checkpoint(checkpoint, **kwargs):
            if kwargs.get("reason_code") == "TASK_IDEMPOTENCY_RESERVED":
                raise _CrashBeforeDispatch(
                    "crash after P0.7/P0.8 reservation before checkpoint CAS"
                )
            return real_checkpoint(checkpoint, **kwargs)

        with (
            patch.object(self.engine, "_request_approval", return_value=True),
            patch.object(
                self.engine,
                "_checkpoint_task",
                side_effect=crash_on_reserved_checkpoint,
            ),
        ):
            with self.assertRaises(_CrashBeforeDispatch):
                self.engine.execute(action, action_context=context)

        checkpoint = self.engine.task_checkpoint_store.load(context.task_id)
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskPhase.BEFORE_DISPATCH, checkpoint.phase)
        operation = OperationContext(checkpoint.current_idempotency_key or "")
        record = self.engine.idempotency_store.load(operation)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(IdempotencyState.RESERVED, record.state)
        handler.assert_not_called()
        return operation, record, checkpoint, handler

    def test_waiting_for_approval_grant_reserves_original_key_and_dispatches_once(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, checkpoint, handler, initial_approval = self._pre_p07_then_crash(
            action
        )
        initial_approval.assert_called_once()
        budget = (
            checkpoint.step_index,
            checkpoint.remaining_steps,
            checkpoint.provider_attempts_used,
            checkpoint.remaining_retry_budget,
        )

        result, fresh_approval, recovery_identity = self._resume_pre_p07(
            checkpoint, action, approval=True
        )

        fresh_approval.assert_called_once()
        handler.assert_called_once()
        self.assertTrue(result["dispatched"])
        self.assertEqual(operation.operation_key, result["operation_key"])
        self.assertEqual(checkpoint.task_id, result["task_id"])
        self.assertEqual(checkpoint.current_action_id, result["action_id"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.SUCCEEDED, record.state)
        self.assertEqual(checkpoint.latest_request_id, record.request_id)
        self.assertEqual(checkpoint.latest_trace_id, record.trace_id)
        self.assertEqual(checkpoint.current_action_id, record.action_id)
        self.assertEqual(checkpoint.task_id, record.task_id)
        final = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert final is not None
        self._assert_recovery_checkpoint_identity(
            final,
            recovery_identity,
            original_request_id=checkpoint.latest_request_id,
            original_trace_id=checkpoint.latest_trace_id,
        )
        self.assertEqual(
            budget,
            (
                final.step_index,
                final.remaining_steps,
                final.provider_attempts_used,
                final.remaining_retry_budget,
            ),
        )
        self.assertEqual(
            1,
            sum(
                item.get("event_type") == "IDEMPOTENCY_RESERVED"
                and item.get("operation_key") == operation.operation_key
                for item in self.engine.provenance_store.read_runtime_all()
            ),
        )

    def test_live_dispatch_does_not_mint_recovery_checkpoint_identity(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        context = TraceContext.new_request().new_action()
        operation = OperationContext.new_operation()
        handler = Mock(return_value={"success": True, "content": "bounded"})
        self.engine.tools["read_file"] = ToolSpec(
            "read_file", handler, "live identity control handler"
        )

        result = self.engine.execute(
            action,
            action_context=context,
            operation_context=operation,
        )

        handler.assert_called_once()
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        checkpoint = self.engine.task_checkpoint_store.load(record.task_id or "")
        assert checkpoint is not None
        self.assertEqual(context.request_id, checkpoint.latest_request_id)
        self.assertEqual(context.trace_id, checkpoint.latest_trace_id)
        self.assertIsNone(checkpoint.recovery_attempt_id)
        self.assertEqual(context.request_id, record.request_id)
        self.assertEqual(context.trace_id, record.trace_id)
        self.assertEqual(context.action_id, record.action_id)
        self.assertEqual(record.task_id, result["task_id"])

    def test_waiting_for_approval_denial_terminalizes_without_dispatch(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, checkpoint, handler, _ = self._pre_p07_then_crash(action)

        result, approval, _recovery_identity = self._resume_pre_p07(
            checkpoint, action, approval=False
        )

        approval.assert_called_once()
        handler.assert_not_called()
        self.assertTrue(result["cancelled"])
        self.assertFalse(result["dispatched"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.CANCELLED, record.state)
        self.assertFalse(any(
            item.get("event_type") == "ACTION_DISPATCH_STARTED"
            and item.get("operation_key") == operation.operation_key
            for item in self.engine.provenance_store.read_runtime_all()
        ))

    def test_pre_p07_current_policy_block_terminalizes_without_dispatch(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, checkpoint, handler, _ = self._pre_p07_then_crash(action)
        real_evaluator = evaluate_action_policy
        service = self.engine._get_task_recovery_service()
        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with (
                patch.object(
                    executor_module,
                    "evaluate_action_policy",
                    side_effect=lambda candidate, context=None: replace(
                        real_evaluator(candidate, context),
                        allowed=False,
                        requires_confirmation=False,
                        reason="Blocked by current recovery policy.",
                        runtime_requires_confirmation=False,
                    ),
                ),
                patch.object(
                    self.engine,
                    "_request_approval",
                    side_effect=AssertionError("blocked policy requested approval"),
                ),
            ):
                result = self.engine.resume_recoverable_action(
                    action, recovery_token=token
                )

        handler.assert_not_called()
        self.assertTrue(result["blocked"])
        self.assertFalse(result["dispatched"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.BLOCKED, record.state)
        self.assertFalse(any(
            item.get("event_type") == "ACTION_DISPATCH_STARTED"
            and item.get("operation_key") == operation.operation_key
            for item in self.engine.provenance_store.read_runtime_all()
        ))

    def test_crash_after_old_grant_requires_another_fresh_callback(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, checkpoint, handler, old_approval = self._pre_p07_then_crash(
            action, after_old_grant=True
        )
        old_approval.assert_called_once()
        self.assertEqual(ApprovalState.GRANTED_IN_PROCESS, checkpoint.approval_state)

        result, fresh_approval, _recovery_identity = self._resume_pre_p07(
            checkpoint, action, approval=True
        )

        fresh_approval.assert_called_once()
        handler.assert_called_once()
        self.assertTrue(result["dispatched"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.SUCCEEDED, record.state)

    def test_read_only_before_dispatch_is_classified_and_resumed_safely(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        operation, checkpoint, handler, initial_approval = (
            self._pre_p07_then_crash(action, after_old_grant=True)
        )
        initial_approval.assert_not_called()
        self.assertEqual(ApprovalState.NOT_REQUIRED, checkpoint.approval_state)
        decision = self.engine._get_task_recovery_service().classify(
            checkpoint.task_id
        )
        self.assertEqual(
            RecoveryClassification.SAFE_TO_RESUME,
            decision.classification,
        )
        self.assertEqual(
            RecoveryDirective.REVALIDATE_ACTION,
            decision.directive,
        )

        result, fresh_boundary, _recovery_identity = self._resume_pre_p07(
            checkpoint, action, approval=True
        )

        fresh_boundary.assert_called_once()
        handler.assert_called_once()
        self.assertTrue(result["dispatched"])
        self.assertEqual(operation.operation_key, result["operation_key"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.SUCCEEDED, record.state)

    def test_manual_review_checkpoint_cannot_bypass_service_resume_gate(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        policy = evaluate_action_policy(action)
        context = TraceContext.new_request().new_action()
        checkpoint = self.engine.task_checkpoint_store.ensure_for_action(context)
        reservation = self.engine.task_checkpoint_store.reserve_step(
            context.task_id
        )
        checkpoint = self.engine.task_checkpoint_store.consume_step_reservation(
            reservation,
            task_id=context.task_id,
        )
        operation = OperationContext.new_operation()
        fingerprint = executor_module.canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=policy.capability_class,
        )
        checkpoint = self.engine.task_checkpoint_store.transition(
            context.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            current_action_id=context.action_id,
            current_idempotency_key=operation.operation_key,
            current_action_name="read_file",
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        checkpoint = self.engine.task_checkpoint_store.transition(
            context.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_DISPATCH,
            reason_code="TASK_BEFORE_DISPATCH",
            current_action_fingerprint=fingerprint,
            current_capability_class=policy.capability_class.value,
            current_policy_reason_code=policy.reason_code,
            approval_state=ApprovalState.NOT_REQUIRED,
        )
        service = self.engine._get_task_recovery_service()
        decision = service.classify(context.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        handler = Mock(return_value={"success": True})
        self.engine.tools["read_file"] = ToolSpec(
            "read_file", handler, "manual-review bypass test handler"
        )

        with service.execution_guard(
            context.task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.resume_recoverable_action(
                    action,
                    recovery_token=token,
                )

        with self.assertRaises(RecoveryFencedError):
            self.engine.execute(
                action,
                action_context=context,
            )

        handler.assert_not_called()
        self.assertIsNone(self.engine.idempotency_store.load(operation))
        unchanged = self.engine.task_checkpoint_store.load(context.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(TaskPhase.BEFORE_DISPATCH, unchanged.phase)
        self.assertEqual(checkpoint.checkpoint_hash, unchanged.checkpoint_hash)

    def test_reserved_record_dominates_stale_before_dispatch_checkpoint(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, record, checkpoint, handler = (
            self._reserve_before_checkpoint_then_crash(action)
        )
        budget = (
            checkpoint.step_index,
            checkpoint.remaining_steps,
            checkpoint.provider_attempts_used,
            checkpoint.remaining_retry_budget,
        )
        service = self.engine._get_task_recovery_service()
        stale = service.classify(checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            stale.classification,
        )
        self.assertEqual(
            RecoveryDirective.RECONCILE_CHECKPOINT,
            stale.directive,
        )
        reconciled = service.reconcile(checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
            reconciled.classification,
        )
        checkpoint = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert checkpoint is not None
        self.assertEqual(TaskPhase.IDEMPOTENCY_RESERVED, checkpoint.phase)
        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with patch.object(
                self.engine, "_request_approval", return_value=True
            ) as approval:
                result = self.engine.resume_recoverable_action(
                    action, recovery_token=token
                )

        approval.assert_called_once()
        handler.assert_called_once()
        self.assertTrue(result["dispatched"])
        self.assertEqual(operation.operation_key, result["operation_key"])
        self.assertEqual(record.action_id, result["action_id"])
        self.assertEqual(record.task_id, result["task_id"])
        final_record = self.engine.idempotency_store.load(operation)
        assert final_record is not None
        self.assertEqual(IdempotencyState.SUCCEEDED, final_record.state)
        final = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert final is not None
        self.assertEqual(
            budget,
            (
                final.step_index,
                final.remaining_steps,
                final.provider_attempts_used,
                final.remaining_retry_budget,
            ),
        )
        self.assertEqual(
            1,
            sum(
                item.get("event_type") == "IDEMPOTENCY_RESERVED"
                and item.get("operation_key") == operation.operation_key
                for item in self.engine.provenance_store.read_runtime_all()
            ),
        )

    def test_explicit_cancel_handles_waiting_and_reserved_but_not_uncertain(self) -> None:
        waiting_action = {
            "action": "write_file",
            "path": "waiting.txt",
            "content": "bounded",
        }
        waiting_operation, waiting, waiting_handler, _ = self._pre_p07_then_crash(
            waiting_action
        )
        service = self.engine._get_task_recovery_service()
        with service.execution_guard(
            waiting.task_id,
            expected_checkpoint_hash=waiting.checkpoint_hash,
        ) as token:
            waiting_recovery_identity = (
                token.request_id,
                token.trace_id,
                token.recovery_attempt_id,
            )
            waiting_result = self.engine.cancel_recoverable_action(
                recovery_token=token
            )
        waiting_handler.assert_not_called()
        self.assertTrue(waiting_result["cancelled"])
        waiting_record = self.engine.idempotency_store.load(waiting_operation)
        assert waiting_record is not None
        self.assertEqual(IdempotencyState.CANCELLED, waiting_record.state)
        self.assertEqual(waiting.latest_request_id, waiting_record.request_id)
        self.assertEqual(waiting.latest_trace_id, waiting_record.trace_id)
        waiting_final = self.engine.task_checkpoint_store.load(waiting.task_id)
        assert waiting_final is not None
        self._assert_recovery_checkpoint_identity(
            waiting_final,
            waiting_recovery_identity,
            original_request_id=waiting.latest_request_id,
            original_trace_id=waiting.latest_trace_id,
        )

        reserved_action = {"action": "read_file", "path": "reserved.txt"}
        (
            reserved_operation,
            reserved_original_record,
            reserved,
            reserved_handler,
        ) = self._reserve_then_crash(reserved_action)
        with service.execution_guard(
            reserved.task_id,
            expected_checkpoint_hash=reserved.checkpoint_hash,
        ) as token:
            reserved_recovery_identity = (
                token.request_id,
                token.trace_id,
                token.recovery_attempt_id,
            )
            reserved_result = self.engine.cancel_recoverable_action(
                recovery_token=token
            )
        reserved_handler.assert_not_called()
        self.assertTrue(reserved_result["cancelled"])
        reserved_record = self.engine.idempotency_store.load(reserved_operation)
        assert reserved_record is not None
        self.assertEqual(IdempotencyState.CANCELLED, reserved_record.state)
        self.assertEqual(
            reserved_original_record.request_id,
            reserved_record.request_id,
        )
        self.assertEqual(
            reserved_original_record.trace_id,
            reserved_record.trace_id,
        )
        self.assertEqual(
            reserved_original_record.action_id,
            reserved_record.action_id,
        )
        reserved_final = self.engine.task_checkpoint_store.load(reserved.task_id)
        assert reserved_final is not None
        self._assert_recovery_checkpoint_identity(
            reserved_final,
            reserved_recovery_identity,
            original_request_id=reserved_original_record.request_id,
            original_trace_id=reserved_original_record.trace_id,
        )

        uncertain_action = {"action": "read_file", "path": "uncertain.txt"}
        uncertain_operation, uncertain_record, uncertain, uncertain_handler = (
            self._reserve_then_crash(uncertain_action)
        )
        uncertain_context = ActionContext(
            request_id=uncertain_record.request_id,
            trace_id=uncertain_record.trace_id,
            task_id=uncertain_record.task_id or "",
            action_id=uncertain_record.action_id,
            model_call_id=uncertain_record.model_call_id,
        )
        uncertain_policy = evaluate_action_policy(
            uncertain_action, uncertain_context
        )
        self.engine.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
                action_context=uncertain_context,
                operation_context=uncertain_operation,
                action_name=uncertain_policy.action_name,
                action_fingerprint=uncertain_record.action_fingerprint,
                capability_class=uncertain_policy.capability_class,
                idempotency_state=uncertain_record.state,
                replayed=False,
                dispatched=True,
                reason_code="ACTION_DISPATCH_STARTED",
            )
        )
        with service.execution_guard(
            uncertain.task_id,
            expected_checkpoint_hash=uncertain.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.cancel_recoverable_action(recovery_token=token)
        uncertain_handler.assert_not_called()
        current = self.engine.idempotency_store.load(uncertain_operation)
        assert current is not None
        self.assertEqual(IdempotencyState.RESERVED, current.state)

    def test_pre_dispatch_terminal_crash_windows_reconcile_directly(self) -> None:
        for after_old_grant in (False, True):
            for terminal_event_written in (False, True):
                with self.subTest(
                    after_old_grant=after_old_grant,
                    terminal_event_written=terminal_event_written,
                ):
                    action = {
                        "action": "write_file",
                        "path": (
                            f"terminal-{int(after_old_grant)}-"
                            f"{int(terminal_event_written)}.txt"
                        ),
                        "content": "must not dispatch",
                    }
                    operation, checkpoint, handler, _old_approval = (
                        self._pre_p07_then_crash(
                            action,
                            after_old_grant=after_old_grant,
                        )
                    )
                    original_budget = (
                        checkpoint.step_index,
                        checkpoint.remaining_steps,
                        checkpoint.provider_attempts_used,
                        checkpoint.remaining_retry_budget,
                    )
                    service = self.engine._get_task_recovery_service()
                    real_terminal_event = self.engine._after_idempotency_transition
                    real_checkpoint = self.engine._checkpoint_task

                    def crash_before_terminal_event(record, *args, **kwargs):
                        if record.state is IdempotencyState.CANCELLED:
                            raise _CrashBeforeDispatch(
                                "crash after P0.7 terminal before P0.8 terminal"
                            )
                        return real_terminal_event(record, *args, **kwargs)

                    def crash_before_terminal_checkpoint(current, **kwargs):
                        if (
                            kwargs.get("state") is TaskState.CANCELLED
                            and kwargs.get("phase") is TaskPhase.TERMINAL
                        ):
                            raise _CrashBeforeDispatch(
                                "crash after P0.8 terminal before checkpoint"
                            )
                        return real_checkpoint(current, **kwargs)

                    injected = (
                        patch.object(
                            self.engine,
                            "_checkpoint_task",
                            side_effect=crash_before_terminal_checkpoint,
                        )
                        if terminal_event_written
                        else patch.object(
                            self.engine,
                            "_after_idempotency_transition",
                            side_effect=crash_before_terminal_event,
                        )
                    )
                    with service.execution_guard(
                        checkpoint.task_id,
                        purpose=RecoveryPurpose.RECOVERY,
                        expected_checkpoint_hash=checkpoint.checkpoint_hash,
                    ) as token:
                        with (
                            patch.object(
                                self.engine,
                                "_request_approval",
                                return_value=False,
                            ),
                            injected,
                            self.assertRaises(_CrashBeforeDispatch),
                        ):
                            self.engine.resume_recoverable_action(
                                action,
                                recovery_token=token,
                            )

                    handler.assert_not_called()
                    record = self.engine.idempotency_store.load(operation)
                    self.assertIsNotNone(record)
                    assert record is not None
                    self.assertEqual(IdempotencyState.CANCELLED, record.state)
                    pending = service.show(checkpoint.task_id)
                    self.assertEqual(
                        RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                        pending.classification,
                    )
                    self.assertEqual(
                        (
                            RecoveryDirective.RECONCILE_CHECKPOINT
                            if terminal_event_written
                            else RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE
                        ),
                        pending.directive,
                    )

                    reconciled = service.reconcile(checkpoint.task_id)
                    self.assertEqual(
                        RecoveryClassification.TERMINAL_NO_RESUME,
                        reconciled.classification,
                    )
                    final = self.engine.task_checkpoint_store.load(
                        checkpoint.task_id
                    )
                    self.assertIsNotNone(final)
                    assert final is not None
                    self.assertEqual(TaskState.CANCELLED, final.state)
                    self.assertEqual(TaskPhase.TERMINAL, final.phase)
                    self.assertEqual(
                        original_budget,
                        (
                            final.step_index,
                            final.remaining_steps,
                            final.provider_attempts_used,
                            final.remaining_retry_budget,
                        ),
                    )
                    events = [
                        item
                        for item in self.engine.provenance_store.read_runtime_all()
                        if item.get("operation_key") == operation.operation_key
                    ]
                    self.assertFalse(
                        any(
                            item.get("event_type")
                            == "ACTION_DISPATCH_STARTED"
                            for item in events
                        )
                    )
                    terminal_truth = [
                        item
                        for item in events
                        if item.get("event_type")
                        in {
                            "ACTION_DISPATCH_CANCELLED",
                            "RECOVERY_TERMINAL_RECONCILED",
                        }
                    ]
                    self.assertEqual(1, len(terminal_truth))

    def test_pre_p07_changed_payload_policy_or_authoritative_ids_are_fenced(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "bounded",
        }
        operation, checkpoint, handler, _ = self._pre_p07_then_crash(action)
        service = self.engine._get_task_recovery_service()

        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.resume_pre_dispatch_action(
                    {**action, "content": "changed"}, recovery_token=token
                )

        real_evaluator = evaluate_action_policy
        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with patch.object(
                executor_module,
                "evaluate_action_policy",
                side_effect=lambda candidate, context=None: replace(
                    real_evaluator(candidate, context),
                    capability_class=CapabilityClass.LOCAL_STATE_CHANGE,
                ),
            ):
                with self.assertRaises(RecoveryFencedError):
                    self.engine.resume_pre_dispatch_action(
                        action, recovery_token=token
                    )

        forged = replace(
            checkpoint,
            current_action_id="action_" + "f" * 32,
        )
        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with patch.object(
                self.engine.task_checkpoint_store,
                "load",
                return_value=forged,
            ):
                with self.assertRaises(RecoveryFencedError):
                    self.engine.resume_pre_dispatch_action(
                        action, recovery_token=token
                    )

        handler.assert_not_called()
        self.assertIsNone(self.engine.idempotency_store.load(operation))

    def test_safe_reserved_resume_keeps_identity_budget_key_and_dispatch_order(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        observations: list[tuple[IdempotencyState, bool]] = []
        operation = OperationContext.new_operation()

        def handler(_action):
            current = self.engine.idempotency_store.load(operation)
            assert current is not None
            matching_start = any(
                item.get("event_type") == "ACTION_DISPATCH_STARTED"
                and item.get("operation_key") == operation.operation_key
                for item in self.engine.provenance_store.read_runtime_all()
            )
            observations.append((current.state, matching_start))
            return {"success": True, "content": "bounded"}

        handler_mock = Mock(side_effect=handler)
        operation, record, checkpoint, _ = self._reserve_then_crash(
            action, handler=handler_mock, operation=operation
        )
        budget_before = (
            checkpoint.step_index,
            checkpoint.remaining_steps,
            checkpoint.provider_attempts_used,
            checkpoint.remaining_retry_budget,
        )
        candidate = {
            **action,
            "task_id": "task_" + "0" * 32,
            "action_id": "action_" + "0" * 32,
            "operation_key": "operation_" + "0" * 32,
            "checkpoint_version": 999,
        }

        result, approval, recovery_identity = self._resume(checkpoint, candidate)

        self.assertTrue(result["success"])
        self.assertTrue(result["dispatched"])
        self.assertFalse(result["replayed"])
        self.assertEqual(operation.operation_key, result["operation_key"])
        self.assertEqual(record.task_id, result["task_id"])
        self.assertEqual(record.action_id, result["action_id"])
        self.assertEqual([(IdempotencyState.DISPATCH_STARTED, True)], observations)
        handler_mock.assert_called_once()
        approval.assert_not_called()
        final = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert final is not None
        self._assert_recovery_checkpoint_identity(
            final,
            recovery_identity,
            original_request_id=record.request_id,
            original_trace_id=record.trace_id,
        )
        final_record = self.engine.idempotency_store.load(operation)
        assert final_record is not None
        self.assertEqual(record.request_id, final_record.request_id)
        self.assertEqual(record.trace_id, final_record.trace_id)
        self.assertEqual(record.action_id, final_record.action_id)
        self.assertEqual(record.task_id, final_record.task_id)
        budget_after = (
            final.step_index,
            final.remaining_steps,
            final.provider_attempts_used,
            final.remaining_retry_budget,
        )
        self.assertEqual(budget_before, budget_after)
        events = self.engine.provenance_store.read_runtime_all()
        self.assertEqual(
            1,
            sum(
                item.get("event_type") == "IDEMPOTENCY_RESERVED"
                and item.get("operation_key") == operation.operation_key
                for item in events
            ),
        )
        self.assertEqual(IdempotencyState.SUCCEEDED, self.engine.idempotency_store.load(operation).state)

    def test_durable_approval_requirement_cannot_be_downgraded_on_resume(self) -> None:
        original = {
            "action": "read_file",
            "path": "input.txt",
            "requires_confirmation": True,
        }
        operation, _, checkpoint, handler = self._reserve_then_crash(original)
        self.assertEqual(
            ApprovalState.FRESH_APPROVAL_REQUIRED, checkpoint.approval_state
        )

        resumed, approval, _recovery_identity = self._resume(
            checkpoint,
            {
                "action": "read_file",
                "path": "input.txt",
                "requires_confirmation": False,
            },
            approval=False,
        )

        approval.assert_called_once()
        handler.assert_not_called()
        self.assertTrue(resumed["cancelled"])
        self.assertFalse(resumed["dispatched"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.CANCELLED, record.state)
        final = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert final is not None
        self.assertEqual(TaskState.CANCELLED, final.state)

    def test_side_effecting_resume_requires_fresh_approval_and_dispatches_once(self) -> None:
        action = {
            "action": "write_file",
            "path": "result.txt",
            "content": "safe-test-content",
            "requires_confirmation": False,
        }
        operation, record, checkpoint, handler = self._reserve_then_crash(action)

        result, approval, _recovery_identity = self._resume(
            checkpoint, action, approval=True
        )

        approval.assert_called_once()
        handler.assert_called_once()
        self.assertTrue(result["dispatched"])
        self.assertEqual(record.action_id, result["action_id"])
        self.assertEqual(operation.operation_key, result["operation_key"])
        final_record = self.engine.idempotency_store.load(operation)
        assert final_record is not None
        self.assertEqual(IdempotencyState.SUCCEEDED, final_record.state)

    def test_mismatched_action_is_fenced_without_redispatch(self) -> None:
        action = {"action": "read_file", "path": "first.txt"}
        operation, _, checkpoint, handler = self._reserve_then_crash(action)
        service = self.engine._get_task_recovery_service()

        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.resume_reserved_action(
                    {"action": "read_file", "path": "different.txt"},
                    recovery_token=token,
                )

        handler.assert_not_called()
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.RESERVED, record.state)

    def test_p08_dispatch_start_blocks_resume_even_when_p07_is_reserved(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        operation, record, checkpoint, handler = self._reserve_then_crash(action)
        context = ActionContext(
            request_id=record.request_id,
            trace_id=record.trace_id,
            task_id=record.task_id or "",
            action_id=record.action_id,
            model_call_id=record.model_call_id,
        )
        policy = evaluate_action_policy(action, context)
        self.engine.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
                action_context=context,
                operation_context=operation,
                action_name=policy.action_name,
                action_fingerprint=record.action_fingerprint,
                capability_class=policy.capability_class,
                idempotency_state=record.state,
                replayed=False,
                dispatched=True,
                reason_code="ACTION_DISPATCH_STARTED",
            )
        )
        service = self.engine._get_task_recovery_service()

        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.resume_reserved_action(action, recovery_token=token)

        handler.assert_not_called()
        current = self.engine.idempotency_store.load(operation)
        assert current is not None
        self.assertEqual(IdempotencyState.RESERVED, current.state)

    def test_p07_dispatch_started_blocks_resume_without_new_key(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        operation, record, checkpoint, handler = self._reserve_then_crash(action)
        self.engine.idempotency_store.transition(
            operation,
            owner_action_id=record.action_id,
            action_fingerprint=record.action_fingerprint,
            to_state=IdempotencyState.DISPATCH_STARTED,
            reason_code="IDEMPOTENCY_DISPATCH_STARTED",
        )
        service = self.engine._get_task_recovery_service()

        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                self.engine.resume_reserved_action(action, recovery_token=token)

        handler.assert_not_called()
        records = list((self.memory.paths.state_dir / "idempotency").glob("*.json"))
        self.assertEqual(1, len(records))
        current = self.engine.idempotency_store.load(operation)
        assert current is not None
        self.assertEqual(IdempotencyState.DISPATCH_STARTED, current.state)

    def test_effect_before_terminal_p07_is_unknown_and_never_repeated(self) -> None:
        action = {"action": "read_file", "path": "effect-once.txt"}
        operation, record, checkpoint, handler = self._reserve_then_crash(action)
        context = ActionContext(
            request_id=record.request_id,
            trace_id=record.trace_id,
            task_id=record.task_id or "",
            action_id=record.action_id,
            model_call_id=record.model_call_id,
        )
        policy = evaluate_action_policy(action, context)
        self.engine.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
                action_context=context,
                operation_context=operation,
                action_name=policy.action_name,
                action_fingerprint=record.action_fingerprint,
                capability_class=policy.capability_class,
                idempotency_state=record.state,
                replayed=False,
                dispatched=True,
                reason_code="ACTION_DISPATCH_STARTED",
            )
        )
        self.engine.idempotency_store.transition(
            operation,
            owner_action_id=record.action_id,
            action_fingerprint=record.action_fingerprint,
            to_state=IdempotencyState.DISPATCH_STARTED,
            reason_code="IDEMPOTENCY_DISPATCH_STARTED",
        )
        # The external effect occurred, but the process died before P0.7 could
        # record any terminal receipt.
        handler(action)
        handler.assert_called_once()
        service = self.engine._get_task_recovery_service()
        decision = service.show(checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.UNKNOWN_OUTCOME,
            decision.classification,
        )
        capability = service.bind_trusted_input(
            checkpoint.task_id,
            action=action,
        )

        with self.assertRaises(RecoveryInputError):
            service.resume(checkpoint.task_id, capability)

        handler.assert_called_once()
        current = self.engine.idempotency_store.load(operation)
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(IdempotencyState.DISPATCH_STARTED, current.state)
        starts = [
            item
            for item in self.engine.provenance_store.read_runtime_all()
            if item.get("event_type") == "ACTION_DISPATCH_STARTED"
            and item.get("operation_key") == operation.operation_key
        ]
        self.assertEqual(1, len(starts))

    def test_current_policy_block_terminalizes_existing_reserved_record(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        operation, _, checkpoint, handler = self._reserve_then_crash(action)
        real_evaluator = evaluate_action_policy

        def block(candidate, context=None):
            return replace(
                real_evaluator(candidate, context),
                allowed=False,
                reason="Blocked by current recovery policy.",
            )

        service = self.engine._get_task_recovery_service()
        with service.execution_guard(
            checkpoint.task_id,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with (
                patch.object(executor_module, "evaluate_action_policy", side_effect=block),
                patch.object(
                    self.engine,
                    "_request_approval",
                    side_effect=AssertionError("blocked policy requested approval"),
                ),
            ):
                result = self.engine.resume_reserved_action(
                    action, recovery_token=token
                )

        handler.assert_not_called()
        self.assertTrue(result["blocked"])
        self.assertFalse(result["dispatched"])
        record = self.engine.idempotency_store.load(operation)
        assert record is not None
        self.assertEqual(IdempotencyState.BLOCKED, record.state)
        final = self.engine.task_checkpoint_store.load(checkpoint.task_id)
        assert final is not None
        self.assertEqual(TaskState.BLOCKED, final.state)

    def test_terminalization_between_ensure_and_guard_cannot_mint_p07(self) -> None:
        action = {"action": "read_file", "path": "input.txt"}
        operation = OperationContext.new_operation()
        context = TraceContext.new_request().new_action()
        handler = Mock(side_effect=AssertionError("terminal task dispatched"))
        self.engine.tools["read_file"] = ToolSpec(
            "read_file", handler, "race test handler"
        )
        service = self.engine._get_task_recovery_service()
        original_guard = service.execution_guard
        raced = False

        @contextmanager
        def terminalizing_guard(task_id, **kwargs):
            nonlocal raced
            checkpoint = self.engine.task_checkpoint_store.load(task_id)
            assert checkpoint is not None
            if not raced:
                raced = True
                self.engine.task_checkpoint_store.transition(
                    task_id,
                    expected_version=checkpoint.checkpoint_version,
                    state=TaskState.CANCELLED,
                    phase=TaskPhase.TERMINAL,
                    reason_code="TASK_CANCELLED",
                )
            with original_guard(task_id, **kwargs) as token:
                yield token

        with patch.object(service, "execution_guard", terminalizing_guard):
            with self.assertRaises(RecoveryClaimConflictError):
                self.engine.execute(
                    action,
                    action_context=context,
                    operation_context=operation,
                )

        handler.assert_not_called()
        self.assertIsNone(self.engine.idempotency_store.load(operation))
        final = self.engine.task_checkpoint_store.load(operation.runtime_task_id())
        assert final is not None
        self.assertEqual(TaskState.CANCELLED, final.state)


if __name__ == "__main__":
    unittest.main()
