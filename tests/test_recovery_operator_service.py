from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    TaskPhase,
    TaskState,
    safe_context_metadata,
)
from runtime.task_recovery import (
    RecoveryClassification,
    RecoveryCorruptionError,
    RecoveryDirective,
    RecoveryFencedError,
    RecoveryInputError,
    RecoveryOperationStatus,
    TaskRecoveryService,
)
from runtime.tools.capability_policy import evaluate_action_policy
from runtime.tools.idempotency import (
    IDEMPOTENCY_STATE_REASON_CODES,
    DurableIdempotencyStore,
    IdempotencyState,
    OperationContext,
    build_safe_result_receipt,
    canonical_action_fingerprint,
)
from runtime.tools.provenance import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import TraceContext


class _TrustedDispatcher:
    def __init__(self, checkpoints: DurableTaskCheckpointStore) -> None:
        self.checkpoints = checkpoints
        self.calls: list[tuple[str, str, str, str]] = []
        self.reminted_attempts: list[str | None] = []

    def resume_model(
        self,
        request_text,
        *,
        trace_context,
        step_reservation,
        recovery_token,
    ):
        self.calls.append(
            (
                "model",
                trace_context.task_id,
                trace_context.request_id,
                recovery_token.recovery_attempt_id,
            )
        )
        self.reminted_attempts.append(
            None
            if step_reservation is None
            else step_reservation.recovery_attempt_id
        )
        checkpoint = self.checkpoints.load(trace_context.task_id)
        assert checkpoint is not None
        if checkpoint.state is TaskState.CREATED:
            checkpoint = self.checkpoints.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BETWEEN_STEPS,
                reason_code="TASK_STARTED",
                latest_request_id=trace_context.request_id,
                latest_trace_id=trace_context.trace_id,
                recovery_attempt_id=recovery_token.recovery_attempt_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
        reservation = step_reservation or self.checkpoints.reserve_step(
            checkpoint.task_id
        )
        model_call = trace_context.new_model_call()
        self.checkpoints.consume_provider_attempt(
            model_call,
            step_reservation=reservation,
        )
        checkpoint = self.checkpoints.load(checkpoint.task_id)
        assert checkpoint is not None
        checkpoint = self.checkpoints.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.AFTER_MODEL_CALL,
            reason_code="TASK_MODEL_CALL_COMPLETED",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            recovery_attempt_id=recovery_token.recovery_attempt_id,
            current_model_call_id=model_call.model_call_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        self.checkpoints.close_step_reservation(reservation)
        self.checkpoints.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.COMPLETED,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_COMPLETED",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            recovery_attempt_id=recovery_token.recovery_attempt_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        return {"success": True, "unexposed": request_text}

    def resume_reserved_action(
        self, action, *, trace_context, recovery_token
    ):
        self.calls.append(
            (
                "reserved",
                trace_context.task_id,
                trace_context.request_id,
                recovery_token.recovery_attempt_id,
            )
        )
        return {"success": False, "unexposed": dict(action)}

    def resume_waiting_action(
        self, action, *, trace_context, recovery_token
    ):
        self.calls.append(
            (
                "waiting",
                trace_context.task_id,
                trace_context.request_id,
                recovery_token.recovery_attempt_id,
            )
        )
        return {"success": False, "unexposed": dict(action)}

    def cancel_recoverable_action(
        self, *, trace_context, recovery_token
    ):
        self.calls.append(
            (
                "cancel",
                trace_context.task_id,
                trace_context.request_id,
                recovery_token.recovery_attempt_id,
            )
        )
        return {"success": False}


class RecoveryOperatorServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        )
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.state = self.root / "state"
        self.state.mkdir()
        self.provenance = AppendOnlyProvenanceStore(self.state)
        self.checkpoints = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=self.provenance,
        )
        self.idempotency = DurableIdempotencyStore(self.state)
        self.dispatcher = _TrustedDispatcher(self.checkpoints)
        self.service = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            idempotency_store=self.idempotency,
            provenance_store=self.provenance,
            dispatcher=self.dispatcher,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_task(
        self,
        request: str = "trusted request",
        *,
        max_steps: int = 2,
        retry_budget: int = 3,
    ):
        trace = TraceContext.new_request()
        checkpoint = self.checkpoints.create_task(
            trace,
            max_steps=max_steps,
            retry_budget=retry_budget,
            safe_context=safe_context_metadata(request),
        )
        return trace, checkpoint

    def prepare_pristine_read_only_action(
        self, *, record_policy: bool = True
    ):
        action = {"action": "read_file", "path": "README.md"}
        trace, created = self.create_task()
        step = self.checkpoints.reserve_step(trace.task_id)
        current = self.checkpoints.consume_step_reservation(
            step, task_id=trace.task_id
        )
        operation = OperationContext.new_operation()
        action_context = trace.new_action()
        policy = evaluate_action_policy(action)
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=policy.capability_class,
        )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            current_action_id=action_context.action_id,
            current_idempotency_key=operation.operation_key,
            current_action_name=policy.action_name,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        if record_policy:
            self.provenance.append_runtime_event(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.CAPABILITY_DECISION,
                    action_context=action_context,
                    operation_context=operation,
                    action_name=policy.action_name,
                    capability_class=policy.capability_class,
                    policy_allowed=True,
                    approval_required=False,
                    reason_code=policy.reason_code,
                )
            )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_DISPATCH,
            reason_code="TASK_BEFORE_DISPATCH",
            current_action_fingerprint=fingerprint,
            current_capability_class=policy.capability_class.value,
            current_policy_reason_code=policy.reason_code,
            approval_state=ApprovalState.NOT_REQUIRED,
        )
        return trace, current, action, operation

    def prepare_action(
        self,
        action: dict[str, object],
        *,
        stop_before_checkpoint: bool = False,
        dispatch_started: bool = False,
    ):
        trace, created = self.create_task()
        step = self.checkpoints.reserve_step(trace.task_id)
        current = self.checkpoints.consume_step_reservation(
            step, task_id=trace.task_id
        )
        operation = OperationContext.new_operation()
        action_context = trace.new_action()
        policy = evaluate_action_policy(action)
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=policy.capability_class,
        )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            current_action_id=action_context.action_id,
            current_idempotency_key=operation.operation_key,
            current_action_name=str(action["action"]),
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        if policy.requires_confirmation:
            current = self.checkpoints.transition(
                trace.task_id,
                expected_version=current.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
                current_action_fingerprint=fingerprint,
                current_capability_class=policy.capability_class.value,
                current_policy_reason_code=policy.reason_code,
                approval_state=ApprovalState.GRANTED_IN_PROCESS,
            )
        else:
            current = self.checkpoints.transition(
                trace.task_id,
                expected_version=current.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_BEFORE_DISPATCH",
                current_action_fingerprint=fingerprint,
                current_capability_class=policy.capability_class.value,
                current_policy_reason_code=policy.reason_code,
                approval_state=ApprovalState.NOT_REQUIRED,
            )
        resolution = self.idempotency.reserve(
            operation,
            action_context=action_context,
            action_fingerprint=fingerprint,
            capability_class=policy.capability_class,
            project_scope=current.project_scope,
        )
        reservation_event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED,
            action_context=action_context,
            operation_context=operation,
            action_name=policy.action_name,
            action_fingerprint=fingerprint,
            capability_class=policy.capability_class,
            idempotency_state=IdempotencyState.RESERVED,
            replayed=False,
            dispatched=False,
            reason_code=resolution.reason_code,
        )
        self.provenance.append_runtime_event(reservation_event)
        if stop_before_checkpoint:
            return (
                trace,
                current,
                action,
                action_context,
                operation,
                fingerprint,
                policy,
                reservation_event,
            )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.IDEMPOTENCY_RESERVED,
            reason_code="TASK_IDEMPOTENCY_RESERVED",
            current_idempotency_state="RESERVED",
            causal_provenance_event_id=reservation_event.event_id,
            approval_state=(
                ApprovalState.FRESH_APPROVAL_REQUIRED
                if policy.requires_confirmation
                else ApprovalState.NOT_REQUIRED
            ),
        )
        if dispatch_started:
            start = new_runtime_provenance_event(
                RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
                action_context=action_context,
                operation_context=operation,
                action_name=policy.action_name,
                action_fingerprint=fingerprint,
                capability_class=policy.capability_class,
                idempotency_state=IdempotencyState.RESERVED,
                replayed=False,
                dispatched=True,
            )
            self.provenance.append_runtime_event(start)
        return (
            trace,
            current,
            action,
            action_context,
            operation,
            fingerprint,
            policy,
            reservation_event,
        )

    def complete_action_between_steps(self, action: dict[str, object]):
        (
            trace,
            current,
            _action,
            action_context,
            operation,
            fingerprint,
            policy,
            _reservation,
        ) = self.prepare_action(action)
        start = new_runtime_provenance_event(
            RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
            action_context=action_context,
            operation_context=operation,
            action_name=policy.action_name,
            action_fingerprint=fingerprint,
            capability_class=policy.capability_class,
            idempotency_state=IdempotencyState.RESERVED,
            replayed=False,
            dispatched=True,
        )
        self.provenance.append_runtime_event(start)
        self.idempotency.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.DISPATCH_STARTED,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[
                IdempotencyState.DISPATCH_STARTED
            ],
        )
        terminal_record = self.idempotency.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.SUCCEEDED,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[
                IdempotencyState.SUCCEEDED
            ],
            terminal_receipt=build_safe_result_receipt({"success": True}),
        )
        terminal = new_runtime_provenance_event(
            RuntimeProvenanceEventType.ACTION_DISPATCH_SUCCEEDED,
            action_context=action_context,
            operation_context=operation,
            action_name=policy.action_name,
            action_fingerprint=fingerprint,
            capability_class=policy.capability_class,
            idempotency_state=terminal_record.state,
            replayed=False,
            dispatched=True,
            success=True,
            reason_code=terminal_record.reason_code,
        )
        self.provenance.append_terminal_event(terminal)
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.AFTER_ACTION,
            reason_code="TASK_ACTION_COMPLETED",
            current_idempotency_state="SUCCEEDED",
            causal_provenance_event_id=terminal.event_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        return self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_BETWEEN_STEPS",
            approval_state=ApprovalState.NOT_APPLICABLE,
        )

    def test_resume_keeps_task_and_mints_new_recovery_request_identities(self) -> None:
        secret = "NZ_OPERATOR_SECRET_001"
        trace, before = self.create_task(secret)
        capability = self.service.bind_trusted_input(
            trace.task_id, request_text=secret
        )

        result = self.service.resume(trace.task_id, capability)

        self.assertEqual(RecoveryOperationStatus.COMPLETED, result.status)
        self.assertEqual(trace.task_id, result.task_id)
        self.assertNotEqual(trace.request_id, result.request_id)
        self.assertNotEqual(trace.trace_id, result.trace_id)
        self.assertTrue(result.recovery_attempt_id.startswith("recovery_attempt_"))
        final = self.checkpoints.load(trace.task_id)
        assert final is not None
        self.assertEqual(result.request_id, final.latest_request_id)
        self.assertEqual(result.trace_id, final.latest_trace_id)
        self.assertEqual(result.recovery_attempt_id, final.recovery_attempt_id)
        self.assertEqual(before.remaining_steps - 1, final.remaining_steps)
        self.assertEqual(
            before.remaining_retry_budget - 1,
            final.remaining_retry_budget,
        )
        self.assertNotIn(secret, repr(result))
        with self.assertRaises(RecoveryInputError):
            self.service.resume(trace.task_id, capability)

        records = self.provenance.read_runtime_all()
        event_types = [
            item["event_type"]
            for item in records
            if item.get("recovery_attempt_id") == result.recovery_attempt_id
        ]
        self.assertLess(
            event_types.index("RECOVERY_DECISION"),
            event_types.index("RECOVERY_RESUME_STARTED"),
        )
        self.assertLess(
            event_types.index("RECOVERY_RESUME_STARTED"),
            event_types.index("RECOVERY_COMPLETED"),
        )

    def test_before_model_remint_does_not_redebit_step_budget(self) -> None:
        trace, _created = self.create_task("remint")
        lost = self.checkpoints.reserve_step(trace.task_id)
        before = self.checkpoints.load(trace.task_id)
        assert before is not None
        self.checkpoints.close_step_reservation(lost)
        capability = self.service.bind_trusted_input(
            trace.task_id, request_text="remint"
        )

        result = self.service.resume(trace.task_id, capability)

        final = self.checkpoints.load(trace.task_id)
        assert final is not None
        self.assertEqual(before.step_index, final.step_index)
        self.assertEqual(before.remaining_steps, final.remaining_steps)
        self.assertLess(final.remaining_retry_budget, before.remaining_retry_budget)
        self.assertEqual(
            result.recovery_attempt_id,
            self.dispatcher.reminted_attempts[-1],
        )
        self.assertIn(
            "TASK_RECOVERY_STEP_REMINTED",
            [item.reason_code for item in final.transitions],
        )

    def test_recovery_step_remint_rejects_released_owner_token(self) -> None:
        trace, _created = self.create_task()
        reservation = self.checkpoints.reserve_step(trace.task_id)
        self.checkpoints.close_step_reservation(reservation)
        before = self.checkpoints.load(trace.task_id)
        assert before is not None
        with self.service.execution_guard(
            trace.task_id,
            expected_checkpoint_hash=before.checkpoint_hash,
        ) as token:
            released_token = token
        with self.assertRaises(RecoveryFencedError):
            self.checkpoints.remint_step_reservation_for_recovery(
                trace.task_id,
                recovery_token=released_token,
            )
        unchanged = self.checkpoints.load(trace.task_id)
        assert unchanged is not None
        self.assertEqual(before.checkpoint_hash, unchanged.checkpoint_hash)

    def test_between_steps_is_safe_only_with_exact_read_only_terminal_proof(self) -> None:
        read_checkpoint = self.complete_action_between_steps(
            {"action": "read_file", "path": "README.md"}
        )
        read_decision = self.service.show(read_checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.SAFE_TO_RESUME,
            read_decision.classification,
        )

        mutation_checkpoint = self.complete_action_between_steps(
            {"action": "write_file", "path": "x", "content": "y"}
        )
        mutation_decision = self.service.show(mutation_checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            mutation_decision.classification,
        )

    def test_next_model_step_after_mutation_never_replans_from_root_request(self) -> None:
        between = self.complete_action_between_steps(
            {"action": "write_file", "path": "x", "content": "y"}
        )
        self.assertEqual(1, between.step_index)
        lost = self.checkpoints.reserve_step(between.task_id)
        self.checkpoints.close_step_reservation(lost)
        before_model = self.checkpoints.load(between.task_id)
        assert before_model is not None
        self.assertEqual(2, before_model.step_index)
        decision = self.service.show(between.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(
            "RECOVERY_CONTINUATION_PAYLOAD_NOT_DURABLE",
            decision.reason_code,
        )
        capability = self.service.bind_trusted_input(
            between.task_id, request_text="trusted request"
        )
        calls_before = tuple(self.dispatcher.calls)
        with self.assertRaises(RecoveryInputError):
            self.service.resume(between.task_id, capability)
        self.assertEqual(calls_before, tuple(self.dispatcher.calls))

    def test_model_failure_requires_exact_started_then_failed_provenance(self) -> None:
        trace, _created = self.create_task("retry")
        reservation = self.checkpoints.reserve_step(trace.task_id)
        model_call = trace.new_model_call()
        self.checkpoints.consume_provider_attempt(
            model_call, step_reservation=reservation
        )
        self.provenance.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.MODEL_CALL_STARTED,
                model_call=model_call,
                requested_provider="test",
                requested_model="test/model",
                retry_attempt=1,
                provider_attempt=1,
            )
        )
        self.provenance.append_terminal_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.MODEL_CALL_FAILED,
                model_call=model_call,
                requested_provider="test",
                requested_model="test/model",
                retry_attempt=1,
                provider_attempt=1,
                success=False,
            )
        )
        checkpoint = self.checkpoints.load(trace.task_id)
        assert checkpoint is not None
        self.assertEqual("TASK_MODEL_ATTEMPT_STARTED", checkpoint.reason_code)
        attempts_before = checkpoint.provider_attempts_used
        retry_budget_before = checkpoint.remaining_retry_budget
        self.checkpoints.close_step_reservation(reservation)
        self.assertEqual(
            RecoveryClassification.SAFE_TO_RESUME,
            self.service.show(trace.task_id).classification,
        )
        trusted = self.service.bind_trusted_input(
            trace.task_id,
            request_text="retry",
        )
        result = self.service.resume(trace.task_id, trusted)
        self.assertEqual(RecoveryOperationStatus.COMPLETED, result.status)
        final = self.checkpoints.load(trace.task_id)
        assert final is not None
        self.assertEqual(TaskState.COMPLETED, final.state)
        self.assertEqual(attempts_before + 1, final.provider_attempts_used)
        self.assertEqual(retry_budget_before - 1, final.remaining_retry_budget)
        self.assertIn(
            "TASK_RECOVERY_STEP_REMINTED",
            [item.reason_code for item in final.transitions],
        )

        other_trace, _ = self.create_task("missing failure")
        other_reservation = self.checkpoints.reserve_step(other_trace.task_id)
        other_call = other_trace.new_model_call()
        self.checkpoints.consume_provider_attempt(
            other_call, step_reservation=other_reservation
        )
        other = self.checkpoints.load(other_trace.task_id)
        assert other is not None
        self.checkpoints.transition(
            other_trace.task_id,
            expected_version=other.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_MODEL_CALL,
            reason_code="TASK_MODEL_CALL_FAILED",
            current_model_call_id=other_call.model_call_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        self.checkpoints.close_step_reservation(other_reservation)
        self.assertEqual(
            RecoveryClassification.UNKNOWN_OUTCOME,
            self.service.show(other_trace.task_id).classification,
        )

    def test_after_model_result_before_policy_is_manual_and_never_reinvokes(self) -> None:
        trace, _created = self.create_task("after model")
        reservation = self.checkpoints.reserve_step(trace.task_id)
        model_call = trace.new_model_call()
        self.checkpoints.consume_provider_attempt(
            model_call,
            step_reservation=reservation,
        )
        self.provenance.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.MODEL_CALL_STARTED,
                model_call=model_call,
                requested_provider="test",
                requested_model="test/model",
                retry_attempt=1,
                provider_attempt=1,
            )
        )
        self.provenance.append_terminal_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.MODEL_CALL_COMPLETED,
                model_call=model_call,
                requested_provider="test",
                requested_model="test/model",
                retry_attempt=1,
                provider_attempt=1,
                success=True,
            )
        )
        checkpoint = self.checkpoints.load(trace.task_id)
        assert checkpoint is not None
        self.checkpoints.transition(
            trace.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.AFTER_MODEL_CALL,
            reason_code="TASK_MODEL_CALL_COMPLETED",
            current_model_call_id=model_call.model_call_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        self.checkpoints.close_step_reservation(reservation)
        decision = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(
            RecoveryDirective.REQUIRE_OPERATOR_ACK,
            decision.directive,
        )
        before_calls = tuple(self.dispatcher.calls)
        capability = self.service.bind_trusted_input(
            trace.task_id,
            request_text="after model",
        )
        with self.assertRaises(RecoveryInputError):
            self.service.resume(trace.task_id, capability)
        self.assertEqual(before_calls, tuple(self.dispatcher.calls))

    def test_exact_recovery_secret_canaries_never_enter_durable_artifacts(self) -> None:
        first = "NZ_RECOVERY_SECRET_001"
        second = "NZ_RECOVERY_SECRET_002"
        request_text = f"inspect {first} and {second} without persistence"
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": first,
                "SOME_PRIVATE_TOKEN": second,
            },
            clear=False,
        ):
            trace, _created = self.create_task(request_text)
            capability = self.service.bind_trusted_input(
                trace.task_id,
                request_text=request_text,
            )
            result = self.service.resume(trace.task_id, capability)
            metadata = (
                repr(result)
                + repr(self.service.show(trace.task_id))
                + repr(self.service.list_incomplete_tasks())
            ).encode("utf-8")
            self.assertNotIn(first.encode("utf-8"), metadata)
            self.assertNotIn(second.encode("utf-8"), metadata)
            for path in self.root.rglob("*"):
                if path.is_symlink() or not path.is_file():
                    continue
                payload = path.read_bytes()
                self.assertNotIn(first.encode("utf-8"), payload, str(path))
                self.assertNotIn(second.encode("utf-8"), payload, str(path))

    def test_waiting_action_uses_fresh_approval_dispatcher_path(self) -> None:
        trace, created = self.create_task()
        step = self.checkpoints.reserve_step(trace.task_id)
        current = self.checkpoints.consume_step_reservation(
            step, task_id=trace.task_id
        )
        action = {"action": "write_file", "path": "x", "content": "y"}
        policy = evaluate_action_policy(action)
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=policy.capability_class,
        )
        action_context = trace.new_action()
        operation = OperationContext.new_operation()
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            current_action_id=action_context.action_id,
            current_idempotency_key=operation.operation_key,
            current_action_name="write_file",
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.WAITING_FOR_APPROVAL,
            phase=TaskPhase.WAITING_FOR_APPROVAL,
            reason_code="TASK_WAITING_FOR_APPROVAL",
            current_action_fingerprint=fingerprint,
            current_capability_class=policy.capability_class.value,
            current_policy_reason_code=policy.reason_code,
            approval_state=ApprovalState.WAITING,
        )
        decision = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryDirective.REQUIRE_FRESH_APPROVAL, decision.directive
        )
        capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )

        result = self.service.resume(trace.task_id, capability)

        self.assertEqual(RecoveryOperationStatus.FAILED, result.status)
        self.assertEqual("waiting", self.dispatcher.calls[-1][0])

    def test_stale_reserved_checkpoint_reconciles_before_reserved_route(self) -> None:
        (
            trace,
            before_dispatch,
            action,
            *_rest,
        ) = self.prepare_action(
            {"action": "read_file", "path": "README.md"},
            stop_before_checkpoint=True,
        )
        pending = self.service.show(trace.task_id)
        self.assertEqual(
            "RECOVERY_RESERVED_CHECKPOINT_PENDING", pending.reason_code
        )
        self.assertEqual(
            RecoveryDirective.RECONCILE_CHECKPOINT, pending.directive
        )

        reconciled = self.service.reconcile(trace.task_id)

        checkpoint = self.checkpoints.load(trace.task_id)
        assert checkpoint is not None
        self.assertGreater(
            checkpoint.checkpoint_version, before_dispatch.checkpoint_version
        )
        self.assertEqual(TaskPhase.IDEMPOTENCY_RESERVED, checkpoint.phase)
        self.assertIn(
            reconciled.classification,
            {
                RecoveryClassification.SAFE_TO_RESUME,
                RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
            },
        )
        capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )
        self.service.resume(trace.task_id, capability)
        self.assertEqual("reserved", self.dispatcher.calls[-1][0])

    def test_current_policy_denial_does_not_prevent_identity_binding(self) -> None:
        trace, _checkpoint, action, *_rest = self.prepare_action(
            {"action": "read_file", "path": "README.md"}
        )
        allowed = evaluate_action_policy(action)
        denied = replace(allowed, allowed=False)
        with patch(
            "runtime.tools.capability_policy.evaluate_action_policy",
            return_value=denied,
        ):
            capability = self.service.bind_trusted_input(
                trace.task_id, action=action
            )
        self.assertEqual(trace.task_id, capability.task_id)

    def test_pristine_read_only_pre_p07_requires_exact_policy_proof(self) -> None:
        trace, _checkpoint, action, operation = (
            self.prepare_pristine_read_only_action()
        )
        decision = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.SAFE_TO_RESUME,
            decision.classification,
        )
        self.assertEqual(RecoveryDirective.REVALIDATE_ACTION, decision.directive)
        self.assertIsNone(self.idempotency.load(operation))
        capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )
        result = self.service.resume(trace.task_id, capability)
        self.assertEqual(RecoveryOperationStatus.FAILED, result.status)
        self.assertEqual("waiting", self.dispatcher.calls[-1][0])
        self.assertIsNone(self.idempotency.load(operation))

        missing_trace, _checkpoint, _action, _operation = (
            self.prepare_pristine_read_only_action(record_policy=False)
        )
        missing = self.service.show(missing_trace.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            missing.classification,
        )
        self.assertEqual(
            RecoveryDirective.REQUIRE_OPERATOR_ACK, missing.directive
        )

    def test_dispatcher_cannot_claim_completion_without_terminal_truth(self) -> None:
        trace, _checkpoint, action, _operation = (
            self.prepare_pristine_read_only_action()
        )
        capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )
        with patch.object(
            self.dispatcher,
            "resume_waiting_action",
            return_value={"success": True},
        ):
            with self.assertRaises(RecoveryCorruptionError):
                self.service.resume(trace.task_id, capability)
        events = [
            item["event_type"]
            for item in self.provenance.read_runtime_all()
            if item.get("task_id") == trace.task_id
        ]
        self.assertIn("RECOVERY_FAILED", events)
        self.assertNotIn("RECOVERY_COMPLETED", events)

    def test_cancel_safe_task_and_unknown_only_acknowledges(self) -> None:
        trace, _created = self.create_task("cancel")
        cancelled = self.service.cancel(trace.task_id)
        self.assertEqual(RecoveryOperationStatus.CANCELLED, cancelled.status)
        final = self.checkpoints.load(trace.task_id)
        assert final is not None
        self.assertEqual(TaskState.CANCELLED, final.state)

        (
            uncertain_trace,
            uncertain_before,
            _action,
            *_rest,
        ) = self.prepare_action(
            {"action": "read_file", "path": "README.md"},
            dispatch_started=True,
        )
        self.assertEqual(
            RecoveryClassification.UNKNOWN_OUTCOME,
            self.service.show(uncertain_trace.task_id).classification,
        )
        with self.assertRaises(RecoveryInputError):
            self.service.cancel(uncertain_trace.task_id)
        acknowledged = self.service.acknowledge_manual_review(
            uncertain_trace.task_id
        )
        self.assertEqual(
            RecoveryOperationStatus.ACKNOWLEDGED, acknowledged.status
        )
        unchanged = self.checkpoints.load(uncertain_trace.task_id)
        assert unchanged is not None
        self.assertEqual(uncertain_before.state, unchanged.state)
        self.assertEqual(uncertain_before.phase, unchanged.phase)
        self.assertEqual(
            RecoveryClassification.UNKNOWN_OUTCOME,
            self.service.show(uncertain_trace.task_id).classification,
        )

    def test_terminal_task_cannot_resume_and_list_show_are_metadata_only(self) -> None:
        live_trace, _ = self.create_task("live")
        done_trace, done = self.create_task("done")
        self.checkpoints.transition(
            done_trace.task_id,
            expected_version=done.checkpoint_version,
            state=TaskState.COMPLETED,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_COMPLETED",
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        capability = self.service.bind_trusted_input(
            done_trace.task_id, request_text="done"
        )
        with self.assertRaises(RecoveryInputError):
            self.service.resume(done_trace.task_id, capability)
        with self.assertRaises(RecoveryInputError):
            self.service.consume_trusted_input(done_trace.task_id, capability)
        listed = self.service.list_incomplete_tasks()
        self.assertIn(live_trace.task_id, {item.task_id for item in listed})
        self.assertNotIn(done_trace.task_id, {item.task_id for item in listed})
        self.assertEqual(
            RecoveryClassification.SAFE_TO_RESUME,
            self.service.show(live_trace.task_id).classification,
        )


if __name__ == "__main__":
    unittest.main()
