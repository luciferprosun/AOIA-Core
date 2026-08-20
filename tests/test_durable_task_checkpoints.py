from __future__ import annotations

import dataclasses
import json
import multiprocessing
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from queue import Empty
from unittest.mock import Mock
from unittest.mock import patch

import runtime.task_checkpoints as checkpoint_module
from runtime.safety.atomic_persistence import AtomicWriteError
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    ModelContinuation,
    SafeResumeClassification,
    TaskBudgetError,
    TaskCheckpointError,
    TaskCheckpointCorruptionError,
    TaskCheckpointSchemaError,
    TaskPhase,
    TaskState,
    TaskStepReservationError,
    TaskTransitionError,
    TASK_CHECKPOINT_FIELDS,
    TASK_TRANSITION_FIELDS,
    SAFE_CONTEXT_FIELDS,
    safe_context_metadata,
)
from tools.executor import ExecutionEngine, ToolSpec
from tools.idempotency import (
    DurableIdempotencyStore,
    IdempotencyStoreCorruptionError,
    OperationContext,
)
from tools.provenance import AppendOnlyProvenanceStore, verify_provenance_chain
from tools.memory import MemoryStore
from trace_context import TraceContext, UNTRUSTED_IDENTITY_FIELDS


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _concurrent_create_worker(
    state_dir: str,
    project_dir: str,
    trace_fields: dict[str, str],
    start_event: multiprocessing.synchronize.Event,
    result_queue: multiprocessing.queues.Queue,
) -> None:
    try:
        store = DurableTaskCheckpointStore(
            Path(state_dir),
            project_dir=Path(project_dir),
            provenance_store=AppendOnlyProvenanceStore(Path(state_dir)),
        )
        if not start_event.wait(timeout=10):
            raise RuntimeError("concurrent checkpoint start timed out")
        checkpoint = store.create_task(
            TraceContext(**trace_fields),
            max_steps=3,
            retry_budget=2,
            safe_context=safe_context_metadata("concurrent request"),
        )
        result_queue.put(
            {
                "ok": True,
                "version": checkpoint.checkpoint_version,
                "hash": checkpoint.checkpoint_hash,
                "remaining_steps": checkpoint.remaining_steps,
            }
        )
    except BaseException as exc:  # pragma: no cover - returned to parent
        result_queue.put(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )


class DurableTaskCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.state = self.root / "state"
        self.project.mkdir()
        self.state.mkdir()
        self.provenance = AppendOnlyProvenanceStore(self.state)
        self.store = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=self.provenance,
        )
        self.trace = TraceContext.new_request()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create(self, *, max_steps: int = 3, retry_budget: int = 3):
        return self.store.create_task(
            self.trace,
            max_steps=max_steps,
            retry_budget=retry_budget,
            safe_context=safe_context_metadata("bounded request"),
        )

    def action_metadata(self) -> dict[str, object]:
        return {
            "current_action_id": _new_id("action"),
            "current_idempotency_key": _new_id("operation"),
            "current_action_name": "write_file",
        }

    def before_policy(self, checkpoint):
        return self.store.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            **self.action_metadata(),
        )

    def new_engine(self) -> ExecutionEngine:
        environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.root / "engine-home"),
                "AOIA_LEGACY_FILESYSTEM_ENABLED": "1",
            },
            clear=False,
        )
        environment.start()
        self.addCleanup(environment.stop)
        memory = MemoryStore(
            self.project,
            self.project,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        return ExecutionEngine(
            self.project,
            memory,
            provenance_store=self.provenance,
            task_checkpoint_store=self.store,
        )

    def complete_non_standalone_action(self):
        engine = self.new_engine()
        created = self.create(max_steps=2)
        reservation = self.store.reserve_step(created.task_id)
        result = engine.execute(
            {"action": "respond", "message": "checkpoint action"},
            action_context=self.trace.new_action(),
            step_reservation=reservation,
        )
        self.assertTrue(result["success"])
        checkpoint = self.store.load(created.task_id)
        self.assertEqual(TaskPhase.AFTER_ACTION, checkpoint.phase)
        return engine, checkpoint

    def test_new_tasks_have_unique_runtime_owned_ids(self) -> None:
        other = TraceContext.new_request()
        first = self.create()
        second = self.store.create_task(other, max_steps=1, retry_budget=1)
        self.assertNotEqual(first.task_id, second.task_id)
        self.assertEqual(self.trace.task_id, first.task_id)

    def test_checkpoint_versions_and_embedded_journal_are_monotonic(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        reserved = self.store.validate_step_reservation(
            token, task_id=created.task_id
        )
        self.assertEqual(created.checkpoint_version + 1, reserved.checkpoint_version)
        self.assertEqual([1, 2], [item.sequence for item in reserved.transitions])
        self.assertEqual(
            reserved.transitions[0].transition_hash,
            reserved.transitions[1].prev_hash,
        )
        self.assertEqual(1, reserved.step_index)
        self.assertEqual(created.remaining_steps - 1, reserved.remaining_steps)

    def test_two_processes_create_one_atomic_checkpoint(self) -> None:
        context = multiprocessing.get_context("spawn")
        start_event = context.Event()
        result_queue = context.Queue()
        arguments = (
            str(self.state),
            str(self.project),
            self.trace.identity_fields(),
            start_event,
            result_queue,
        )
        processes = [
            context.Process(target=_concurrent_create_worker, args=arguments)
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        start_event.set()
        try:
            results = [result_queue.get(timeout=20) for _ in processes]
        except Empty:
            self.fail("concurrent checkpoint worker produced no result")
        for process in processes:
            process.join(timeout=20)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
                self.fail("concurrent checkpoint worker did not terminate")
            self.assertEqual(0, process.exitcode)
        self.assertTrue(all(item["ok"] for item in results), results)
        self.assertEqual({1}, {item["version"] for item in results})
        self.assertEqual(1, len({item["hash"] for item in results}))
        checkpoint = self.store.load(self.trace.task_id)
        self.assertEqual(1, checkpoint.checkpoint_version)
        self.assertEqual(3, checkpoint.remaining_steps)

    def test_reserving_next_step_clears_all_action_metadata(self) -> None:
        _engine, completed = self.complete_non_standalone_action()
        token = self.store.reserve_step(completed.task_id)
        next_step = self.store.validate_step_reservation(
            token,
            task_id=completed.task_id,
        )
        for field in (
            "current_model_call_id",
            "current_action_id",
            "current_idempotency_key",
            "current_action_fingerprint",
            "current_idempotency_state",
            "causal_provenance_event_id",
            "current_action_name",
            "current_capability_class",
            "current_policy_reason_code",
        ):
            self.assertIsNone(getattr(next_step, field), field)
        self.assertEqual(ApprovalState.NOT_APPLICABLE, next_step.approval_state)

    def test_illegal_transition_and_budget_reset_fail_closed(self) -> None:
        created = self.create()
        with self.assertRaises(TaskTransitionError):
            self.store.transition(
                created.task_id,
                expected_version=created.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.DISPATCH_IN_FLIGHT,
                reason_code="TASK_DISPATCH_IN_FLIGHT",
            )
        with self.assertRaises((TaskTransitionError, TaskBudgetError)):
            self.store.transition(
                created.task_id,
                expected_version=created.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_MODEL_CALL,
                reason_code="TASK_STEP_RESERVED",
                step_index=1,
                remaining_steps=created.remaining_steps,
            )

    def test_failed_later_model_attempt_can_terminalize_partial_only(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        before_model = self.store.consume_step_reservation(
            token,
            task_id=created.task_id,
        )
        with self.assertRaises(TaskTransitionError):
            self.store.transition(
                created.task_id,
                expected_version=before_model.checkpoint_version,
                state=TaskState.COMPLETED,
                phase=TaskPhase.TERMINAL,
                reason_code="TASK_COMPLETED",
            )
        partial = self.store.transition(
            created.task_id,
            expected_version=before_model.checkpoint_version,
            state=TaskState.PARTIAL,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_PARTIAL",
        )
        self.assertEqual(TaskState.PARTIAL, partial.state)

    def test_step_token_is_bound_and_registry_is_bounded(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        forged = dataclasses.replace(token, checkpoint_hash="f" * 64)
        with self.assertRaises(TaskStepReservationError):
            self.store.consume_step_reservation(forged, task_id=created.task_id)
        self.store.consume_step_reservation(token, task_id=created.task_id)
        self.assertEqual({}, self.store._active_step_reservations)

    def test_provider_budget_is_debited_before_attempt_and_survives_reload(self) -> None:
        created = self.create(retry_budget=2)
        token = self.store.reserve_step(created.task_id)
        model_call = self.trace.new_model_call()
        debited = self.store.consume_provider_attempt(
            model_call, step_reservation=token
        )
        self.assertEqual(1, debited.provider_attempts_used)
        self.assertEqual(1, debited.remaining_retry_budget)
        reloaded = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=AppendOnlyProvenanceStore(self.state),
        ).load(created.task_id)
        self.assertEqual(1, reloaded.provider_attempts_used)
        self.assertEqual(1, reloaded.remaining_retry_budget)

    def test_second_model_call_requires_live_continuation_proof(self) -> None:
        created = self.create(retry_budget=3)
        token = self.store.reserve_step(created.task_id)
        planner = self.trace.new_model_call()
        started = self.store.consume_provider_attempt(planner, step_reservation=token)
        completed = self.store.transition(
            created.task_id,
            expected_version=started.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.AFTER_MODEL_CALL,
            reason_code="TASK_MODEL_CALL_COMPLETED",
            current_model_call_id=planner.model_call_id,
        )
        worker = self.trace.new_model_call()
        with self.assertRaises(TaskStepReservationError):
            self.store.consume_provider_attempt(worker, step_reservation=token)
        proof = self.store.authorize_model_continuation(
            token, completed_model_call=planner
        )
        continued = self.store.consume_provider_attempt(
            worker,
            step_reservation=token,
            model_continuation=proof,
        )
        self.assertEqual(TaskPhase.BEFORE_MODEL_CALL, continued.phase)
        self.assertEqual(2, continued.provider_attempts_used)
        with self.assertRaises(TaskStepReservationError):
            self.store.consume_provider_attempt(
                self.trace.new_model_call(),
                step_reservation=token,
                model_continuation=proof,
            )

    def test_unused_model_continuation_can_be_closed_exactly_once(self) -> None:
        created = self.create(retry_budget=2)
        token = self.store.reserve_step(created.task_id)
        planner = self.trace.new_model_call()
        started = self.store.consume_provider_attempt(
            planner,
            step_reservation=token,
        )
        completed = self.store.transition(
            created.task_id,
            expected_version=started.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.AFTER_MODEL_CALL,
            reason_code="TASK_MODEL_CALL_COMPLETED",
            current_model_call_id=planner.model_call_id,
        )
        self.assertEqual(TaskPhase.AFTER_MODEL_CALL, completed.phase)
        proof = self.store.authorize_model_continuation(
            token,
            completed_model_call=planner,
        )
        forged = dataclasses.replace(proof, checkpoint_hash="f" * 64)
        with self.assertRaises(TaskStepReservationError):
            self.store.close_model_continuation(forged)
        self.assertEqual(1, len(self.store._active_model_continuations))
        self.store.close_model_continuation(proof)
        self.assertEqual({}, self.store._active_model_continuations)
        with self.assertRaises(TaskStepReservationError):
            self.store.close_model_continuation(proof)

    def test_waiting_approval_requires_fresh_approval_after_restart(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        reserved = self.store.consume_step_reservation(
            token, task_id=created.task_id
        )
        before = self.before_policy(reserved)
        waiting = self.store.transition(
            created.task_id,
            expected_version=before.checkpoint_version,
            state=TaskState.WAITING_FOR_APPROVAL,
            phase=TaskPhase.WAITING_FOR_APPROVAL,
            reason_code="TASK_WAITING_FOR_APPROVAL",
            current_action_fingerprint="a" * 64,
            current_capability_class="FILESYSTEM_MUTATION",
            current_policy_reason_code="FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
            approval_state=ApprovalState.WAITING,
        )
        self.assertEqual(
            SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            waiting.safe_resume_classification,
        )
        reloaded = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=AppendOnlyProvenanceStore(self.state),
        ).load(created.task_id)
        self.assertNotEqual(ApprovalState.GRANTED_IN_PROCESS, reloaded.approval_state)
        self.assertEqual(
            SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            reloaded.safe_resume_classification,
        )

    def test_in_process_approval_is_classified_fresh_after_reload(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        reserved = self.store.consume_step_reservation(
            token,
            task_id=created.task_id,
        )
        before = self.before_policy(reserved)
        waiting = self.store.transition(
            created.task_id,
            expected_version=before.checkpoint_version,
            state=TaskState.WAITING_FOR_APPROVAL,
            phase=TaskPhase.WAITING_FOR_APPROVAL,
            reason_code="TASK_WAITING_FOR_APPROVAL",
            current_action_fingerprint="a" * 64,
            current_capability_class="FILESYSTEM_MUTATION",
            current_policy_reason_code=(
                "FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION"
            ),
            approval_state=ApprovalState.WAITING,
        )
        granted = self.store.transition(
            created.task_id,
            expected_version=waiting.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_DISPATCH,
            reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
            approval_state=ApprovalState.GRANTED_IN_PROCESS,
        )
        self.assertEqual(
            SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            granted.safe_resume_classification,
        )
        reloaded = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=AppendOnlyProvenanceStore(self.state),
        ).load(created.task_id)
        self.assertEqual(
            SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            reloaded.safe_resume_classification,
        )

    def test_terminal_task_cannot_resume(self) -> None:
        created = self.create()
        done = self.store.transition(
            created.task_id,
            expected_version=created.checkpoint_version,
            state=TaskState.COMPLETED,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_COMPLETED",
        )
        with self.assertRaises(TaskTransitionError):
            self.store.transition(
                done.task_id,
                expected_version=done.checkpoint_version,
                state=TaskState.RUNNING,
                phase=TaskPhase.BETWEEN_STEPS,
                reason_code="TASK_STARTED",
            )

    def test_terminal_task_state_must_match_persisted_action_outcome(self) -> None:
        _engine, completed_action = self.complete_non_standalone_action()
        self.assertEqual("SUCCEEDED", completed_action.current_idempotency_state)
        with self.assertRaises(TaskTransitionError):
            self.store.transition(
                completed_action.task_id,
                expected_version=completed_action.checkpoint_version,
                state=TaskState.CANCELLED,
                phase=TaskPhase.TERMINAL,
                reason_code="TASK_CANCELLED",
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
        unchanged = self.store.load(completed_action.task_id)
        self.assertEqual(TaskState.RUNNING, unchanged.state)
        self.assertEqual(TaskPhase.AFTER_ACTION, unchanged.phase)

    def test_aggregate_partial_atomically_closes_failed_action_context(self) -> None:
        engine = self.new_engine()
        handler = Mock(
            return_value={
                "success": False,
                "error": "synthetic reported action failure",
            }
        )
        engine.tools["respond"] = ToolSpec("respond", handler, "test handler")
        created = self.create(max_steps=2)
        reservation = self.store.reserve_step(created.task_id)
        result = engine.execute(
            {"action": "respond", "message": "reported failure"},
            action_context=self.trace.new_action(),
            step_reservation=reservation,
        )
        self.assertFalse(result["success"])
        failed_action = self.store.load(created.task_id)
        self.assertEqual(TaskPhase.AFTER_ACTION, failed_action.phase)
        self.assertEqual(
            "FAILED_REPORTED",
            failed_action.current_idempotency_state,
        )
        action_event_id = failed_action.causal_provenance_event_id
        action_id = failed_action.current_action_id

        partial = self.store.transition(
            created.task_id,
            expected_version=failed_action.checkpoint_version,
            state=TaskState.PARTIAL,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_PARTIAL",
        )

        self.assertEqual(failed_action.checkpoint_version + 1, partial.checkpoint_version)
        self.assertEqual(TaskState.PARTIAL, partial.state)
        self.assertEqual(TaskPhase.TERMINAL, partial.phase)
        self.assertEqual(
            TaskPhase.AFTER_ACTION.value,
            partial.transitions[-1].from_phase,
        )
        self.assertFalse(
            any(
                transition.to_phase == TaskPhase.BETWEEN_STEPS.value
                for transition in partial.transitions[failed_action.checkpoint_version :]
            )
        )
        for field in (
            "current_model_call_id",
            "current_action_id",
            "current_idempotency_key",
            "current_action_fingerprint",
            "current_idempotency_state",
            "causal_provenance_event_id",
            "current_action_name",
            "current_capability_class",
            "current_policy_reason_code",
        ):
            self.assertIsNone(getattr(partial, field), field)
        self.assertEqual(ApprovalState.NOT_APPLICABLE, partial.approval_state)
        terminal_action_event = next(
            event
            for event in self.provenance.read_runtime_all()
            if event.get("event_id") == action_event_id
        )
        self.assertEqual("ACTION_DISPATCH_FAILED", terminal_action_event["event_type"])
        self.assertEqual(action_id, terminal_action_event["action_id"])
        self.assertEqual("FAILED_REPORTED", terminal_action_event["idempotency_state"])
        self.assertEqual(TaskState.PARTIAL, self.store.load(created.task_id).state)

    def test_corrupt_duplicate_key_and_unsupported_schema_are_explicit(self) -> None:
        created = self.create()
        path = self.store.checkpoint_path(created.task_id)
        path.write_text('{"schema_version":"AOIA_TASK_CHECKPOINT_1A","schema_version":"X"}')
        with self.assertRaises(TaskCheckpointCorruptionError):
            self.store.load(created.task_id)

        payload = created.to_payload()
        payload["schema_version"] = "AOIA_TASK_CHECKPOINT_99Z"
        path.write_text(json.dumps(payload))
        with self.assertRaises(TaskCheckpointSchemaError):
            self.store.load(created.task_id)

    def test_safe_context_is_exact_bounded_and_secret_free(self) -> None:
        secret = "NZ_RECOVERY_SECRET_001"
        created = self.store.create_task(
            self.trace,
            max_steps=1,
            retry_budget=1,
            safe_context=safe_context_metadata(secret),
        )
        raw = self.store.checkpoint_path(created.task_id).read_text()
        self.assertNotIn(secret, raw)
        self.assertEqual(len(secret), created.safe_context["request_length"])
        with self.assertRaises(TaskCheckpointCorruptionError):
            self.store.create_task(
                TraceContext.new_request(),
                max_steps=1,
                retry_budget=1,
                safe_context={"request_hash": "a" * 64, "request_length": 1,
                              "context_hashes": [], "raw_prompt": secret},
            )

    def test_rehashed_budget_forgery_cannot_self_authorize(self) -> None:
        created = self.create(max_steps=2)
        path = self.store.checkpoint_path(created.task_id)
        payload = json.loads(path.read_text())
        forged_event = _new_id("provenance_event")
        payload["max_steps"] = 999
        payload["remaining_steps"] = 999
        payload["latest_provenance_event_id"] = forged_event
        payload["transitions"][0]["remaining_steps"] = 999
        payload["transitions"][0]["provenance_event_id"] = forged_event
        transition_doc = dict(payload["transitions"][0])
        transition_doc.pop("transition_hash")
        payload["transitions"][0]["transition_hash"] = (
            checkpoint_module._hash_document(transition_doc)
        )
        payload_without_hash = dict(payload)
        payload_without_hash.pop("checkpoint_hash")
        payload["checkpoint_hash"] = checkpoint_module._hash_document(
            payload_without_hash
        )
        before_events = len(self.provenance.read_runtime_all())
        path.write_text(json.dumps(payload))
        with self.assertRaises(TaskCheckpointCorruptionError):
            self.store.load(created.task_id)
        self.assertEqual(before_events, len(self.provenance.read_runtime_all()))

    def test_prepared_cas_failure_is_aborted_without_snapshot(self) -> None:
        trace = TraceContext.new_request()

        def fail_after_prepare(_path, update, **_kwargs):
            update(None)
            raise AtomicWriteError("synthetic CAS failure")

        with patch.object(checkpoint_module, "locked_update_json", fail_after_prepare):
            with self.assertRaises(AtomicWriteError):
                self.store.create_task(trace, max_steps=1, retry_budget=1)
        events = self.provenance.read_runtime_all()
        self.assertEqual(
            ["TASK_CHECKPOINT_PREPARED", "TASK_CHECKPOINT_ABORTED"],
            [event["event_type"] for event in events[-2:]],
        )
        self.assertTrue(verify_provenance_chain(self.provenance.runtime_log_path).ok)

    def test_checkpoint_persistence_errors_keep_existing_identity(self) -> None:
        action_context = self.trace.new_action()
        failure = AtomicWriteError("synthetic checkpoint persistence failure")
        with patch.object(
            checkpoint_module,
            "locked_update_json",
            side_effect=failure,
        ):
            with self.assertRaises(AtomicWriteError) as raised:
                self.store.create_task(
                    action_context,
                    max_steps=1,
                    retry_budget=1,
                )
        self.assertEqual(
            action_context.identity_fields(),
            raised.exception.correlation,
        )

    def test_task_directory_is_fsynced_before_checkpoint_publication(self) -> None:
        digest = checkpoint_module.hashlib.sha256(
            self.trace.task_id.encode("utf-8")
        ).hexdigest()
        with (
            patch.object(
                checkpoint_module.os,
                "fsync",
                side_effect=OSError("synthetic tasks-root fsync failure"),
            ),
            patch.object(checkpoint_module, "locked_update_json") as update,
            self.assertRaises(TaskCheckpointError),
        ):
            self.create()
        update.assert_not_called()
        self.assertFalse((self.store.root_dir / digest / "checkpoint.json").exists())
        self.assertEqual([], self.provenance.read_runtime_all())

    def test_crash_gap_after_cas_recovers_only_from_prepared_anchor(self) -> None:
        original = self.provenance.append_terminal
        with patch.object(
            self.provenance,
            "append_terminal",
            side_effect=AtomicWriteError("synthetic terminal append failure"),
        ):
            with self.assertRaises(AtomicWriteError):
                self.create()
        task_id = self.trace.task_id
        self.provenance.append_terminal = original
        recovered = self.store.load(task_id)
        self.assertIsNotNone(recovered)
        matching = [
            event for event in self.provenance.read_runtime_all()
            if event.get("event_id") == recovered.latest_provenance_event_id
        ]
        self.assertEqual(1, len(matching))

    def test_tasks_root_symlink_swap_fails_before_external_write(self) -> None:
        old_root = self.root / "tasks-old"
        outside = self.root / "outside"
        outside.mkdir()
        self.store.root_dir.rename(old_root)
        self.store.root_dir.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(TaskCheckpointCorruptionError):
            self.create()
        self.assertEqual([], list(outside.iterdir()))

    def test_root_and_task_descriptors_reject_ancestor_identity_swap(self) -> None:
        task_leaf = self.store.task_dir(self.trace.task_id)
        digest = task_leaf.name
        old_root = self.root / "tasks-old"
        outside = self.root / "outside-race"
        outside.mkdir()
        original = checkpoint_module.locked_update_json
        swapped = False

        def swap_after_descriptors_open(*args, **kwargs):
            nonlocal swapped
            if not swapped:
                swapped = True
                self.store.root_dir.rename(old_root)
                (old_root / digest).rename(outside / digest)
                self.store.root_dir.symlink_to(outside, target_is_directory=True)
            return original(*args, **kwargs)

        with patch.object(
            checkpoint_module,
            "locked_update_json",
            swap_after_descriptors_open,
        ):
            with self.assertRaises(TaskCheckpointCorruptionError) as raised:
                self.create()
        self.assertEqual(self.trace.task_id, raised.exception.correlation["task_id"])
        self.assertFalse((outside / digest / "checkpoint.json").exists())

    def test_idempotency_duplicate_security_key_is_rejected(self) -> None:
        idem = DurableIdempotencyStore(self.state)
        operation = OperationContext.new_operation()
        path = idem.record_path(operation.operation_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"task_id":"task_' + uuid.uuid4().hex + '","task_id":null}')
        with self.assertRaises(IdempotencyStoreCorruptionError):
            idem.load(operation)

    def test_prior_p07_replay_dispatches_handler_only_once(self) -> None:
        engine = self.new_engine()
        handler = Mock(return_value={"success": True})
        engine.tools["respond"] = ToolSpec("respond", handler, "test handler")
        operation = OperationContext.new_operation()
        action = {"action": "respond", "message": "stable replay"}
        first = engine.execute(
            action,
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        replay = engine.execute(
            action,
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        self.assertEqual(1, handler.call_count)
        self.assertTrue(first["dispatched"])
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["dispatched"])
        checkpoint = self.store.load(operation.runtime_task_id())
        self.assertEqual(TaskState.COMPLETED, checkpoint.state)

    def test_p07_conflict_has_consistent_blocked_task_truth(self) -> None:
        engine = self.new_engine()
        handler = Mock(return_value={"success": True})
        engine.tools["respond"] = ToolSpec("respond", handler, "test handler")
        created = self.create(max_steps=2)
        operation = OperationContext.new_operation()
        first_token = self.store.reserve_step(created.task_id)
        engine.execute(
            {"action": "respond", "message": "first semantics"},
            action_context=self.trace.new_action(),
            operation_context=operation,
            step_reservation=first_token,
        )
        after_first = self.store.load(created.task_id)
        between = self.store.transition(
            created.task_id,
            expected_version=after_first.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_BETWEEN_STEPS",
        )
        second_token = self.store.reserve_step(between.task_id)
        conflict = engine.execute(
            {"action": "respond", "message": "different semantics"},
            action_context=self.trace.new_action(),
            operation_context=operation,
            step_reservation=second_token,
        )
        self.assertTrue(conflict["idempotency_conflict"])
        self.assertEqual(1, handler.call_count)
        checkpoint = self.store.load(created.task_id)
        self.assertEqual(TaskState.BLOCKED, checkpoint.state)
        self.assertEqual("TASK_IDEMPOTENCY_CONFLICT", checkpoint.reason_code)
        self.assertEqual("CONFLICT", checkpoint.current_idempotency_state)

    def test_checkpoint_schema_owned_fields_are_untrusted_model_fields(self) -> None:
        future_claim_fields = {
            "claim_generation", "claim_owner", "claim_owner_id",
            "claim_expires_at", "lease_expires_at", "recovery_claim_id",
        }
        schema_owned = (
            set(TASK_CHECKPOINT_FIELDS)
            | set(TASK_TRANSITION_FIELDS)
            | set(SAFE_CONTEXT_FIELDS)
            | future_claim_fields
        )
        self.assertEqual(set(), schema_owned - set(UNTRUSTED_IDENTITY_FIELDS))

    def test_inflight_checkpoint_cannot_rewind_or_claim_completion(self) -> None:
        created = self.create()
        token = self.store.reserve_step(created.task_id)
        current = self.store.consume_step_reservation(token, task_id=created.task_id)
        current = self.before_policy(current)
        meta = {
            "current_action_fingerprint": "a" * 64,
            "current_capability_class": "FILESYSTEM_MUTATION",
            "current_policy_reason_code": "FILESYSTEM_MUTATION_REQUIRES_CONFIRMATION",
            "approval_state": ApprovalState.FRESH_APPROVAL_REQUIRED,
        }
        current = self.store.transition(
            created.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_DISPATCH,
            reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
            **meta,
        )
        current = self.store.transition(
            created.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.IDEMPOTENCY_RESERVED,
            reason_code="TASK_IDEMPOTENCY_RESERVED",
            current_idempotency_state="RESERVED",
            **meta,
        )
        current = self.store.transition(
            created.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            reason_code="TASK_PROVENANCE_DISPATCH_RECORDED",
            current_idempotency_state="RESERVED",
            **meta,
        )
        current = self.store.transition(
            created.task_id,
            expected_version=current.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.DISPATCH_IN_FLIGHT,
            reason_code="TASK_DISPATCH_IN_FLIGHT",
            current_idempotency_state="DISPATCH_STARTED",
            **meta,
        )
        with self.assertRaises(TaskTransitionError):
            self.store.reserve_step(created.task_id)
        with self.assertRaises((TaskTransitionError, TaskCheckpointCorruptionError)):
            self.store.transition(
                created.task_id,
                expected_version=current.checkpoint_version,
                state=TaskState.COMPLETED,
                phase=TaskPhase.TERMINAL,
                reason_code="TASK_COMPLETED",
                current_idempotency_state="SUCCEEDED",
                **meta,
            )


if __name__ == "__main__":
    unittest.main()
