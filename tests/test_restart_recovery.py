from __future__ import annotations

import datetime as dt
import json
import multiprocessing
import os
import pickle
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.safety.atomic_persistence import StateLockTimeoutError
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    TaskCheckpointError,
    TaskPhase,
    TaskState,
    safe_context_metadata,
)
from runtime.task_recovery import (
    RECOVERY_CLAIM_FIELDS,
    RECOVERY_DECISION_FIELDS,
    RecoveryClassification,
    RecoveryCorruptionError,
    RecoveryDecision,
    RecoveryDirective,
    RecoveryFencedError,
    RecoveryInProgressError,
    RecoveryInputError,
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
    CHECKPOINT_RUNTIME_PROVENANCE_SCHEMA_VERSION,
    AppendOnlyProvenanceStore,
    ProvenanceSchemaError,
    RuntimeProvenanceEvent,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import TraceContext, UNTRUSTED_IDENTITY_FIELDS


def _hold_claim_worker(
    state: str,
    project: str,
    task_id: str,
    entered: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
) -> None:
    service = TaskRecoveryService(
        Path(state),
        project_dir=Path(project),
        lock_timeout_seconds=0.2,
        lease_seconds=1.0,
    )
    with service.execution_guard(task_id):
        entered.set()
        release.wait(10)


def _reuse_inherited_guard_worker(service, task_id, token, outcome) -> None:
    try:
        with service.execution_guard(task_id, existing_token=token):
            outcome.put("entered")
    except RecoveryFencedError:
        outcome.put("fenced")
    except BaseException as exc:  # pragma: no cover - returned to parent
        outcome.put(f"{type(exc).__name__}:{exc}")


class RestartRecoveryTests(unittest.TestCase):
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
        self.service = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            idempotency_store=self.idempotency,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_task(
        self,
        request: str = "safe request",
        *,
        max_steps: int = 1,
        retry_budget: int = 2,
    ):
        trace = TraceContext.new_request()
        checkpoint = self.checkpoints.create_task(
            trace,
            max_steps=max_steps,
            retry_budget=retry_budget,
            safe_context=safe_context_metadata(request),
        )
        return trace, checkpoint

    def reserve_read_action(
        self,
        *,
        max_steps: int = 1,
        action: dict[str, object] | None = None,
    ):
        trace, created = self.create_task(max_steps=max_steps)
        step = self.checkpoints.reserve_step(created.task_id)
        current = self.checkpoints.consume_step_reservation(
            step, task_id=created.task_id
        )
        action = action or {"action": "read_file", "path": "README.md"}
        decision = evaluate_action_policy(action)
        operation = OperationContext.new_operation()
        action_context = trace.new_action()
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=decision.capability_class,
        )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            current_action_id=action_context.action_id,
            current_idempotency_key=operation.operation_key,
            current_action_name=decision.action_name,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_DISPATCH,
            reason_code=(
                "TASK_APPROVAL_GRANTED_IN_PROCESS"
                if decision.requires_confirmation
                else "TASK_BEFORE_DISPATCH"
            ),
            current_action_fingerprint=fingerprint,
            current_capability_class=decision.capability_class.value,
            current_policy_reason_code=decision.reason_code,
            approval_state=(
                ApprovalState.GRANTED_IN_PROCESS
                if decision.requires_confirmation
                else ApprovalState.NOT_REQUIRED
            ),
        )
        resolution = self.idempotency.reserve(
            operation,
            action_context=action_context,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class,
            project_scope=current.project_scope,
        )
        reservation_event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED,
            action_context=action_context,
            operation_context=operation,
            action_name=decision.action_name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class,
            idempotency_state=resolution.record.state,
            replayed=False,
            dispatched=False,
            reason_code=resolution.reason_code,
        )
        self.provenance.append_runtime_event(reservation_event)
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.IDEMPOTENCY_RESERVED,
            reason_code="TASK_IDEMPOTENCY_RESERVED",
            current_idempotency_state=resolution.record.state.value,
            causal_provenance_event_id=reservation_event.event_id,
            approval_state=(
                ApprovalState.FRESH_APPROVAL_REQUIRED
                if decision.requires_confirmation
                else ApprovalState.NOT_REQUIRED
            ),
        )
        return trace, current, action, action_context, operation, fingerprint, decision

    def append_dispatch_start(
        self, action_context, operation, fingerprint, decision
    ) -> RuntimeProvenanceEvent:
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
            action_context=action_context,
            operation_context=operation,
            action_name=decision.action_name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class,
            idempotency_state=IdempotencyState.RESERVED,
            replayed=False,
            dispatched=True,
        )
        self.provenance.append_runtime_event(event)
        return event

    def terminalize_idempotency(
        self, operation, action_context, fingerprint
    ):
        self.idempotency.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.DISPATCH_STARTED,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[
                IdempotencyState.DISPATCH_STARTED
            ],
        )
        return self.idempotency.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.SUCCEEDED,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[IdempotencyState.SUCCEEDED],
            terminal_receipt=build_safe_result_receipt({"success": True}),
        )

    def terminalize_idempotency_as(
        self,
        operation,
        action_context,
        fingerprint,
        state: IdempotencyState,
    ):
        if state in {IdempotencyState.SUCCEEDED, IdempotencyState.FAILED_REPORTED}:
            self.idempotency.transition(
                operation,
                owner_action_id=action_context.action_id,
                action_fingerprint=fingerprint,
                to_state=IdempotencyState.DISPATCH_STARTED,
                reason_code=IDEMPOTENCY_STATE_REASON_CODES[
                    IdempotencyState.DISPATCH_STARTED
                ],
            )
        result = {"success": state is IdempotencyState.SUCCEEDED}
        if state is IdempotencyState.BLOCKED:
            result["blocked"] = True
        if state is IdempotencyState.CANCELLED:
            result["cancelled"] = True
        return self.idempotency.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=state,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[state],
            terminal_receipt=build_safe_result_receipt(result),
        )

    def test_exact_enums_decision_schema_and_cross_field_matrix(self) -> None:
        self.assertEqual(
            {
                "SAFE_TO_RESUME", "WAITING_FOR_FRESH_APPROVAL", "ALREADY_COMPLETED",
                "TERMINAL_NO_RESUME", "BLOCKED", "CONFLICT", "CORRUPT_CHECKPOINT",
                "UNSUPPORTED_SCHEMA", "UNKNOWN_OUTCOME", "MANUAL_REVIEW_REQUIRED",
                "RECOVERY_IN_PROGRESS",
            },
            {item.value for item in RecoveryClassification},
        )
        trace, checkpoint = self.create_task()
        decision = self.service.classify(trace.task_id)
        self.assertEqual(RECOVERY_DECISION_FIELDS, frozenset(decision.to_payload()))
        self.assertFalse(decision.provider_dispatch_allowed)
        self.assertFalse(decision.handler_dispatch_allowed)
        self.assertEqual(
            set(),
            (RECOVERY_CLAIM_FIELDS | RECOVERY_DECISION_FIELDS)
            - UNTRUSTED_IDENTITY_FIELDS,
        )
        with self.assertRaises(RecoveryCorruptionError):
            RecoveryDecision(
                **{
                    **decision.__dict__,
                    "directive": RecoveryDirective.CANCEL_TASK,
                }
            )

    def test_created_requires_exact_digest_bound_one_shot_input(self) -> None:
        secret = "SYNTHETIC_RECOVERY_SECRET_001"
        trace, _checkpoint = self.create_task(secret)
        decision = self.service.classify(trace.task_id)
        self.assertEqual(RecoveryClassification.SAFE_TO_RESUME, decision.classification)
        self.assertTrue(decision.requires_trusted_input)
        with self.assertRaises(RecoveryInputError):
            self.service.bind_trusted_input(trace.task_id, request_text="wrong")
        capability = self.service.bind_trusted_input(
            trace.task_id, request_text=secret
        )
        self.assertNotIn(secret, repr(capability))
        with self.assertRaises(TypeError):
            pickle.dumps(capability)
        self.service.consume_trusted_input(trace.task_id, capability)
        with self.assertRaises(RecoveryInputError):
            self.service.consume_trusted_input(trace.task_id, capability)
        durable = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.state.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
        self.assertNotIn(secret, durable)

    def test_trusted_input_is_immutable_and_revalidated_on_consume(self) -> None:
        trace, _checkpoint = self.create_task("trusted original")
        request_capability = self.service.bind_trusted_input(
            trace.task_id, request_text="trusted original"
        )
        with self.assertRaises(AttributeError):
            request_capability._request_text = "changed"
        with self.assertRaises(AttributeError):
            del request_capability._request_text
        object.__setattr__(
            request_capability, "_request_text", "forced mutation"
        )
        with self.assertRaises(RecoveryInputError):
            self.service.consume_trusted_input(
                trace.task_id, request_capability
            )

        trace, _checkpoint, action, *_rest = self.reserve_read_action()
        action_capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )
        with self.assertRaises(AttributeError):
            action_capability.action_fingerprint = "0" * 64
        object.__setattr__(
            action_capability,
            "_action_json",
            '{"action":"read_file","path":"different"}',
        )
        with self.assertRaises(RecoveryInputError):
            self.service.consume_trusted_input(
                trace.task_id, action_capability
            )

    def test_between_steps_after_prior_step_is_manual_not_model_resume(self) -> None:
        trace, created = self.create_task(max_steps=2)
        reserved = self.checkpoints.reserve_step(trace.task_id)
        current = self.checkpoints.load(trace.task_id)
        self.assertIsNotNone(current)
        # A persisted boundary without a durable continuation payload cannot
        # authorize a new provider call merely from the root request digest.
        current = self.checkpoints.transition(
            trace.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.PARTIAL,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_PARTIAL",
        )
        self.checkpoints.close_step_reservation(reserved)
        decision = self.service.classify(trace.task_id)
        self.assertEqual(
            RecoveryClassification.TERMINAL_NO_RESUME,
            decision.classification,
        )

    def test_reserved_action_requires_matching_candidate_and_current_policy(self) -> None:
        trace, _cp, action, *_rest = self.reserve_read_action()
        decision = self.service.classify(trace.task_id)
        self.assertEqual(RecoveryDirective.REVALIDATE_ACTION, decision.directive)
        self.assertFalse(decision.handler_dispatch_allowed)
        with self.assertRaises(RecoveryInputError):
            self.service.bind_trusted_input(
                trace.task_id,
                action={"action": "read_file", "path": "different"},
            )
        capability = self.service.bind_trusted_input(
            trace.task_id, action=action
        )
        self.service.consume_trusted_input(trace.task_id, capability)

    def test_dispatch_start_or_unknown_never_authorizes_redispatch(self) -> None:
        (
            trace, _cp, _action, action_context, operation, fingerprint, decision,
        ) = self.reserve_read_action()
        self.append_dispatch_start(action_context, operation, fingerprint, decision)
        classified = self.service.classify(trace.task_id)
        self.assertEqual(RecoveryClassification.UNKNOWN_OUTCOME, classified.classification)
        self.assertFalse(classified.handler_dispatch_allowed)

    def test_terminal_p07_reconciles_distinct_receipt_and_converges(self) -> None:
        (
            trace, _cp, _action, action_context, operation, fingerprint, decision,
        ) = self.reserve_read_action()
        self.append_dispatch_start(action_context, operation, fingerprint, decision)
        self.terminalize_idempotency(operation, action_context, fingerprint)
        before = self.service.classify(trace.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            before.classification,
        )
        self.assertEqual(
            RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
            before.directive,
        )
        after = self.service.reconcile(trace.task_id)
        self.assertEqual(RecoveryClassification.ALREADY_COMPLETED, after.classification)
        again = self.service.reconcile(trace.task_id)
        self.assertEqual(RecoveryDirective.NO_ACTION, again.directive)
        records = self.provenance.read_runtime_all()
        self.assertEqual(
            1,
            sum(
                item["event_type"] == "RECOVERY_TERMINAL_RECONCILED"
                for item in records
            ),
        )
        self.assertEqual(
            0,
            sum(
                item["event_type"] == "ACTION_DISPATCH_SUCCEEDED"
                for item in records
            ),
        )
        receipt = next(
            item for item in records
            if item["event_type"] == "RECOVERY_TERMINAL_RECONCILED"
        )
        self.assertEqual("SUCCEEDED", receipt["idempotency_state"])
        self.assertRegex(receipt["terminal_receipt_hash"], r"^[0-9a-f]{64}$")

    def test_terminal_checkpoint_rejects_rolled_back_idempotency_record(self) -> None:
        (
            trace, _cp, _action, action_context, operation, fingerprint, decision,
        ) = self.reserve_read_action()
        record_path = self.idempotency.record_path(operation.operation_key)
        reserved_snapshot = record_path.read_bytes()
        self.append_dispatch_start(
            action_context, operation, fingerprint, decision
        )
        self.terminalize_idempotency(operation, action_context, fingerprint)
        reconciled = self.service.reconcile(trace.task_id)
        self.assertEqual(
            RecoveryClassification.ALREADY_COMPLETED,
            reconciled.classification,
        )

        record_path.write_bytes(reserved_snapshot)
        corrupted = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.CORRUPT_CHECKPOINT,
            corrupted.classification,
        )
        self.assertEqual("RECOVERY_IDEMPOTENCY_CORRUPT", corrupted.reason_code)

    def test_post_dispatch_terminal_truth_requires_dispatch_start(self) -> None:
        for terminal_state in (
            IdempotencyState.SUCCEEDED,
            IdempotencyState.FAILED_REPORTED,
        ):
            with self.subTest(state=terminal_state.value):
                (
                    trace,
                    _checkpoint,
                    _action,
                    action_context,
                    operation,
                    fingerprint,
                    _decision,
                ) = self.reserve_read_action()
                self.terminalize_idempotency_as(
                    operation,
                    action_context,
                    fingerprint,
                    terminal_state,
                )
                classified = self.service.classify(trace.task_id)
                self.assertEqual(
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    classified.classification,
                )
                self.assertEqual(
                    "RECOVERY_TERMINAL_WITHOUT_DISPATCH_START",
                    classified.reason_code,
                )
                self.assertEqual(classified, self.service.reconcile(trace.task_id))
        self.assertFalse(
            any(
                item["event_type"] == "RECOVERY_TERMINAL_RECONCILED"
                for item in self.provenance.read_runtime_all()
            )
        )

    def test_pre_dispatch_terminal_truth_rejects_dispatch_start(self) -> None:
        for terminal_state in (
            IdempotencyState.BLOCKED,
            IdempotencyState.CANCELLED,
            IdempotencyState.FAILED_BEFORE_DISPATCH,
        ):
            with self.subTest(state=terminal_state.value):
                (
                    trace,
                    _checkpoint,
                    _action,
                    action_context,
                    operation,
                    fingerprint,
                    decision,
                ) = self.reserve_read_action()
                self.append_dispatch_start(
                    action_context, operation, fingerprint, decision
                )
                self.terminalize_idempotency_as(
                    operation,
                    action_context,
                    fingerprint,
                    terminal_state,
                )
                classified = self.service.classify(trace.task_id)
                self.assertEqual(
                    RecoveryClassification.CORRUPT_CHECKPOINT,
                    classified.classification,
                )
                self.assertEqual(
                    "RECOVERY_CHECKPOINT_ANCHOR_CONFLICT",
                    classified.reason_code,
                )

    def test_pre_dispatch_terminal_truth_reconciles_without_action_event(self) -> None:
        for terminal_state in (
            IdempotencyState.BLOCKED,
            IdempotencyState.CANCELLED,
            IdempotencyState.FAILED_BEFORE_DISPATCH,
        ):
            with self.subTest(state=terminal_state.value):
                (
                    trace,
                    _checkpoint,
                    _action,
                    action_context,
                    operation,
                    fingerprint,
                    _decision,
                ) = self.reserve_read_action()
                self.terminalize_idempotency_as(
                    operation,
                    action_context,
                    fingerprint,
                    terminal_state,
                )
                classified = self.service.classify(trace.task_id)
                self.assertEqual(
                    RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
                    classified.directive,
                )
                recovered = self.service.reconcile(trace.task_id)
                self.assertIn(
                    recovered.classification,
                    {
                        RecoveryClassification.BLOCKED,
                        RecoveryClassification.TERMINAL_NO_RESUME,
                    },
                )
        records = self.provenance.read_runtime_all()
        self.assertFalse(
            any(item["event_type"].startswith("ACTION_DISPATCH_") for item in records)
        )
        self.assertEqual(
            3,
            sum(
                item["event_type"] == "RECOVERY_TERMINAL_RECONCILED"
                for item in records
            ),
        )

    def test_terminal_reconciliation_never_aggregates_failure_as_partial(self) -> None:
        expected = {
            IdempotencyState.SUCCEEDED: TaskState.PARTIAL,
            IdempotencyState.BLOCKED: TaskState.BLOCKED,
            IdempotencyState.CANCELLED: TaskState.CANCELLED,
            IdempotencyState.FAILED_BEFORE_DISPATCH: TaskState.FAILED,
            IdempotencyState.FAILED_REPORTED: TaskState.FAILED,
        }
        for terminal_state, expected_task_state in expected.items():
            with self.subTest(state=terminal_state.value):
                (
                    trace,
                    checkpoint,
                    _action,
                    action_context,
                    operation,
                    fingerprint,
                    decision,
                ) = self.reserve_read_action(
                    max_steps=3,
                    action={
                        "action": "write_file",
                        "path": "result.txt",
                        "content": "bounded",
                    },
                )
                self.assertGreater(checkpoint.remaining_steps, 0)
                if terminal_state in {
                    IdempotencyState.SUCCEEDED,
                    IdempotencyState.FAILED_REPORTED,
                }:
                    self.append_dispatch_start(
                        action_context, operation, fingerprint, decision
                    )
                self.terminalize_idempotency_as(
                    operation,
                    action_context,
                    fingerprint,
                    terminal_state,
                )
                classified = self.service.classify(trace.task_id)
                self.assertEqual(
                    RecoveryDirective.RECONCILE_TERMINAL_PROVENANCE,
                    classified.directive,
                )
                self.service.reconcile(trace.task_id)
                final = self.checkpoints.load(trace.task_id)
                assert final is not None
                self.assertEqual(expected_task_state, final.state)
                self.assertEqual(TaskPhase.TERMINAL, final.phase)
                self.assertEqual(
                    ApprovalState.DENIED
                    if terminal_state is IdempotencyState.CANCELLED
                    else ApprovalState.NOT_APPLICABLE,
                    final.approval_state,
                )
                if terminal_state is not IdempotencyState.SUCCEEDED:
                    self.assertIsNot(TaskState.PARTIAL, final.state)

    def test_snapshot_prepare_gap_reconciles_without_execution(self) -> None:
        trace, checkpoint = self.create_task(max_steps=2)
        original_ensure = self.checkpoints.ensure_checkpoint_event

        def fail_candidate_anchor(candidate):
            if candidate.checkpoint_version == checkpoint.checkpoint_version + 1:
                raise TaskCheckpointError("forced snapshot-to-anchor gap")
            return original_ensure(candidate)

        with patch.object(
            self.checkpoints,
            "ensure_checkpoint_event",
            side_effect=fail_candidate_anchor,
        ):
            with self.assertRaises(TaskCheckpointError):
                self.checkpoints.transition(
                    trace.task_id,
                    expected_version=checkpoint.checkpoint_version,
                    state=TaskState.RUNNING,
                    phase=TaskPhase.BETWEEN_STEPS,
                    reason_code="TASK_STARTED",
                )
        decision = self.service.classify(trace.task_id)
        self.assertEqual(RecoveryDirective.RECONCILE_CHECKPOINT, decision.directive)
        recovered = self.service.reconcile(trace.task_id)
        self.assertEqual(RecoveryClassification.SAFE_TO_RESUME, recovered.classification)
        self.assertEqual(RecoveryDirective.RESUME_MODEL, recovered.directive)

    def test_claim_exact_release_generation_and_no_secret_fields(self) -> None:
        trace, checkpoint = self.create_task()
        with self.service.execution_guard(
            trace.task_id, expected_checkpoint_hash=checkpoint.checkpoint_hash
        ) as token:
            active = self.service._read_claim(trace.task_id)
            self.assertEqual(RECOVERY_CLAIM_FIELDS, frozenset(active.to_payload()))
            self.assertEqual(1, active.generation)
            with self.service.execution_guard(
                trace.task_id, existing_token=token
            ) as nested:
                self.assertIs(token, nested)
            with self.assertRaises(RecoveryInProgressError):
                with self.service.execution_guard(trace.task_id):
                    pass
        released = self.service._read_claim(trace.task_id)
        self.assertEqual("RELEASED", released.status.value)
        with self.service.execution_guard(trace.task_id) as second:
            self.assertEqual(2, second.generation)
        raw = self.service.claim_path(trace.task_id).read_text(encoding="utf-8")
        for forbidden in ("prompt", "output", "command", "content", "error"):
            self.assertNotIn(forbidden, raw.lower())

    def test_execution_token_is_immutable_and_stale_release_is_fenced(self) -> None:
        trace, _checkpoint = self.create_task()
        with self.service.execution_guard(trace.task_id) as stale:
            with self.assertRaises(AttributeError):
                stale.generation = stale.generation + 1
            with self.assertRaises(AttributeError):
                del stale.generation
        with self.service.execution_guard(trace.task_id) as current:
            self.assertGreater(current.generation, stale.generation)
            with self.assertRaises(RecoveryFencedError):
                self.service._release_claim(stale)

    def test_forked_process_cannot_reuse_inherited_guard_token(self) -> None:
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("fork start method is unavailable")
        trace, _checkpoint = self.create_task()
        context = multiprocessing.get_context("fork")
        outcome = context.Queue()
        with self.service.execution_guard(trace.task_id) as token:
            process = context.Process(
                target=_reuse_inherited_guard_worker,
                args=(self.service, trace.task_id, token, outcome),
            )
            process.start()
            process.join(5)
            self.assertEqual(0, process.exitcode)
            self.assertEqual("fenced", outcome.get(timeout=2))

    def test_release_failure_preserves_primary_body_exception(self) -> None:
        trace, _checkpoint = self.create_task()
        with patch.object(
            self.service,
            "_release_claim",
            side_effect=RuntimeError("forced release failure"),
        ):
            with self.assertRaisesRegex(ValueError, "primary body failure") as raised:
                with self.service.execution_guard(trace.task_id):
                    raise ValueError("primary body failure")
        self.assertTrue(
            any("release also failed" in note for note in raised.exception.__notes__)
        )

    def test_release_timestamp_cannot_precede_claim_timestamp(self) -> None:
        trace, _checkpoint = self.create_task()
        claimed = dt.datetime(2026, 8, 20, 12, tzinfo=dt.UTC)
        timestamps = iter(
            [claimed, claimed, claimed - dt.timedelta(seconds=1)]
        )
        self.service._clock = lambda: next(timestamps)
        with self.assertRaisesRegex(
            RecoveryCorruptionError, "release precedes"
        ):
            with self.service.execution_guard(trace.task_id):
                pass
        claim = self.service._read_claim(trace.task_id)
        self.assertEqual("ACTIVE", claim.status.value)

    def test_recovery_ancestor_symlink_is_rejected_before_external_write(self) -> None:
        state = self.root / "symlink-state"
        recovery = state / "recovery"
        recovery.mkdir(parents=True)
        external = self.root / "external-claims"
        external.mkdir()
        os.symlink(external, recovery / "claims", target_is_directory=True)
        with self.assertRaises(RecoveryCorruptionError):
            TaskRecoveryService(state, project_dir=self.project)
        self.assertEqual([], list(external.iterdir()))

    def test_recovery_root_swap_cannot_write_claim_outside_state(self) -> None:
        trace, _checkpoint = self.create_task()
        moved = self.state / "recovery.old"
        external = self.root / "external-recovery"
        (external / "claims" / self.service.project_scope).mkdir(parents=True)
        (external / "execution" / self.service.project_scope).mkdir(parents=True)
        original_acquire = self.service._acquire_claim

        def swap_then_acquire(*args, **kwargs):
            os.rename(self.state / "recovery", moved)
            os.symlink(
                external,
                self.state / "recovery",
                target_is_directory=True,
            )
            return original_acquire(*args, **kwargs)

        with patch.object(
            self.service,
            "_acquire_claim",
            side_effect=swap_then_acquire,
        ):
            with self.assertRaises(RecoveryCorruptionError):
                with self.service.execution_guard(trace.task_id):
                    pass
        self.assertEqual(
            [], [path for path in external.rglob("*") if path.is_file()]
        )

    def test_invalid_expected_hash_does_not_create_active_claim(self) -> None:
        trace, _checkpoint = self.create_task()
        with self.assertRaises(Exception):
            with self.service.execution_guard(
                trace.task_id, expected_checkpoint_hash="not-a-hash"
            ):
                pass
        self.assertFalse(self.service.claim_path(trace.task_id).exists())

    def test_two_threads_cannot_implicitly_share_guard(self) -> None:
        trace, _checkpoint = self.create_task()
        outcome: list[str] = []
        with self.service.execution_guard(trace.task_id):
            thread = threading.Thread(
                target=lambda: self._thread_guard_attempt(trace.task_id, outcome)
            )
            thread.start()
            thread.join(2)
        self.assertEqual(["blocked"], outcome)

    def _thread_guard_attempt(self, task_id: str, outcome: list[str]) -> None:
        try:
            with self.service.execution_guard(task_id):
                outcome.append("entered")
        except RecoveryInProgressError:
            outcome.append("blocked")

    def test_real_process_execution_flock_blocks_second_owner(self) -> None:
        trace, _checkpoint = self.create_task()
        context = multiprocessing.get_context("spawn")
        entered = context.Event()
        release = context.Event()
        process = context.Process(
            target=_hold_claim_worker,
            args=(str(self.state), str(self.project), trace.task_id, entered, release),
        )
        process.start()
        self.assertTrue(entered.wait(10))
        contender = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            lock_timeout_seconds=0.05,
            lease_seconds=1.0,
        )
        with self.assertRaises(RecoveryInProgressError) as raised:
            with contender.execution_guard(trace.task_id):
                pass
        self.assertEqual("RECOVERY_IN_PROGRESS", raised.exception.reason_code)
        self.assertEqual(
            trace.task_id,
            raised.exception.correlation.get("task_id"),
        )
        self.assertIsInstance(
            raised.exception.__cause__, StateLockTimeoutError
        )
        release.set()
        process.join(10)
        self.assertEqual(0, process.exitcode)

    def test_replaced_execution_lock_cannot_take_over_expired_active_claim(self) -> None:
        trace, _checkpoint = self.create_task()
        claimed = dt.datetime(2026, 8, 20, 12, tzinfo=dt.UTC)
        self.service._clock = lambda: claimed
        contender = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
            clock=lambda: claimed + dt.timedelta(seconds=2),
        )
        contender_entered = False
        with self.assertRaises(RecoveryFencedError):
            with self.service.execution_guard(trace.task_id) as token:
                lock_path = self.service.execution_lock_path(trace.task_id)
                lock_path.unlink()
                descriptor = os.open(
                    lock_path,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                os.close(descriptor)
                with self.assertRaisesRegex(
                    RecoveryCorruptionError, "lock binding changed"
                ):
                    with contender.execution_guard(trace.task_id):
                        contender_entered = True
                claim = contender._read_claim(trace.task_id)
                self.assertEqual(1, claim.generation)
                self.assertEqual("ACTIVE", claim.status.value)
                with self.assertRaises(RecoveryFencedError):
                    self.service.classify_under_claim(trace.task_id, token)
        self.assertFalse(contender_entered)

    def test_discovery_is_bounded_deterministic_and_explicit_on_overflow(self) -> None:
        task_ids = [self.create_task()[0].task_id for _ in range(3)]
        overflow = self.service.discover(limit=2)
        self.assertTrue(overflow.truncated)
        self.assertTrue(overflow.degraded)
        self.assertEqual((), overflow.decisions)
        complete = self.service.discover(limit=3)
        self.assertFalse(complete.degraded)
        self.assertEqual(
            sorted(self.service._resource_id(item) for item in task_ids),
            [item.resource_id for item in complete.decisions],
        )

    def test_referenced_idempotency_corruption_and_absence_are_explicit(self) -> None:
        trace, checkpoint, _action, _ctx, operation, *_rest = (
            self.reserve_read_action()
        )
        self.idempotency.record_path(operation.operation_key).write_text(
            "{", encoding="utf-8"
        )
        corrupt = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.CORRUPT_CHECKPOINT,
            corrupt.classification,
        )
        self.assertEqual("RECOVERY_IDEMPOTENCY_CORRUPT", corrupt.reason_code)

        trace, checkpoint, _action, _ctx, operation, *_rest = (
            self.reserve_read_action()
        )
        self.idempotency.record_path(operation.operation_key).unlink()
        missing = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.CORRUPT_CHECKPOINT,
            missing.classification,
        )
        self.assertEqual(
            "RECOVERY_IDEMPOTENCY_STATE_MISSING",
            missing.reason_code,
        )

    def test_unsupported_checkpoint_is_explicit_in_show_and_discovery(self) -> None:
        trace, _checkpoint = self.create_task()
        path = self.checkpoints.checkpoint_path(trace.task_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["schema_version"] = "AOIA_TASK_CHECKPOINT_FUTURE"
        path.write_text(json.dumps(payload), encoding="utf-8")

        direct = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.UNSUPPORTED_SCHEMA,
            direct.classification,
        )
        self.assertEqual(
            "RECOVERY_CHECKPOINT_SCHEMA_UNSUPPORTED",
            direct.reason_code,
        )
        discovered = self.service.discover(limit=4)
        self.assertEqual(1, discovered.malformed_count)
        self.assertEqual(1, len(discovered.decisions))
        self.assertEqual(
            RecoveryClassification.UNSUPPORTED_SCHEMA,
            discovered.decisions[0].classification,
        )

    def test_older_valid_checkpoint_snapshot_cannot_remint_budget(self) -> None:
        trace, created = self.create_task(max_steps=3)
        path = self.checkpoints.checkpoint_path(trace.task_id)
        original_snapshot = path.read_bytes()
        started = self.checkpoints.transition(
            trace.task_id,
            expected_version=created.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_STARTED",
        )
        reservation = self.checkpoints.reserve_step(trace.task_id)
        latest = self.checkpoints.load(trace.task_id)
        assert latest is not None
        self.assertEqual(started.remaining_steps - 1, latest.remaining_steps)

        # Fault injection: restore a once-valid, internally consistent snapshot.
        path.write_bytes(original_snapshot)
        rolled_back = self.service.show(trace.task_id)
        self.assertEqual(
            RecoveryClassification.CORRUPT_CHECKPOINT,
            rolled_back.classification,
        )
        self.assertEqual(
            "RECOVERY_CHECKPOINT_ROLLBACK_DETECTED",
            rolled_back.reason_code,
        )
        self.checkpoints.close_step_reservation(reservation)

    def test_model_terminal_event_before_checkpoint_is_classified_truthfully(self) -> None:
        for event_type, expected_classification, expected_reason in (
            (
                RuntimeProvenanceEventType.MODEL_CALL_FAILED,
                RecoveryClassification.SAFE_TO_RESUME,
                "RECOVERY_TRUSTED_REQUEST_REQUIRED",
            ),
            (
                RuntimeProvenanceEventType.MODEL_CALL_COMPLETED,
                RecoveryClassification.MANUAL_REVIEW_REQUIRED,
                "RECOVERY_MODEL_OUTPUT_NOT_DURABLE",
            ),
        ):
            with self.subTest(event_type=event_type.value):
                trace, _created = self.create_task(retry_budget=2)
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
                        requested_provider="synthetic",
                        requested_model="synthetic-model",
                        retry_attempt=1,
                        provider_attempt=1,
                    )
                )
                self.provenance.append_terminal(
                    new_runtime_provenance_event(
                        event_type,
                        model_call=model_call,
                        requested_provider="synthetic",
                        requested_model="synthetic-model",
                        retry_attempt=1,
                        provider_attempt=1,
                        success=(
                            event_type
                            is RuntimeProvenanceEventType.MODEL_CALL_COMPLETED
                        ),
                    )
                )

                decision = self.service.show(trace.task_id)
                self.assertEqual(expected_classification, decision.classification)
                self.assertEqual(expected_reason, decision.reason_code)
                self.checkpoints.close_step_reservation(reservation)

    def test_provenance_1c_exact_values_and_monotonic_1b_upgrade(self) -> None:
        trace, checkpoint = self.create_task()
        legacy_trace = TraceContext.new_request()
        one_b = RuntimeProvenanceEvent(
            event_id=f"provenance_event_{'1' * 32}",
            timestamp_utc="2026-08-20T00:00:00Z",
            event_type="REQUEST_STARTED",
            task_id=legacy_trace.task_id,
            request_id=legacy_trace.request_id,
            trace_id=legacy_trace.trace_id,
            ingress="RUNTIME",
            request_length=1,
            slash_command=False,
            reason_code="REQUEST_STARTED",
            schema_version=CHECKPOINT_RUNTIME_PROVENANCE_SCHEMA_VERSION,
        )
        # A separate ledger demonstrates the allowed 1B prefix then 1C suffix.
        upgrade_state = self.root / "upgrade"
        upgrade = AppendOnlyProvenanceStore(upgrade_state)
        upgrade.append_runtime_event(one_b)
        upgrade.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_STARTED,
                trace_context=TraceContext.new_request(),
                ingress="RUNTIME",
                request_length=1,
                slash_command=False,
            )
        )
        self.assertEqual(
            ["AOIA_RUNTIME_PROVENANCE_1B", "AOIA_RUNTIME_PROVENANCE_1C"],
            [item["schema_version"] for item in upgrade.read_runtime_all()],
        )
        base = dict(
            event_id=f"provenance_event_{'2' * 32}",
            timestamp_utc="2026-08-20T00:00:00Z",
            event_type="RECOVERY_DECISION",
            task_id=trace.task_id,
            request_id=trace.request_id,
            trace_id=trace.trace_id,
            project_scope=checkpoint.project_scope,
            recovery_attempt_id=f"recovery_attempt_{'3' * 32}",
            recovery_generation=1,
            recovery_directive="RESUME_MODEL",
            checkpoint_version=checkpoint.checkpoint_version,
            checkpoint_hash=checkpoint.checkpoint_hash,
            task_state=checkpoint.state.value,
            task_phase=checkpoint.phase.value,
            reason_code="RECOVERY_DECISION_RECORDED",
        )
        with self.assertRaises(ProvenanceSchemaError):
            RuntimeProvenanceEvent(
                **base,
                recovery_classification="EVIL_AUTO_RESUME",
            )
        with self.assertRaises(ProvenanceSchemaError):
            RuntimeProvenanceEvent(
                **{
                    **base,
                    "task_state": "BOGUS_STATE",
                },
                recovery_classification="SAFE_TO_RESUME",
            )


if __name__ == "__main__":
    unittest.main()
