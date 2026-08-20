from __future__ import annotations

import importlib
import json
import multiprocessing
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from runtime.safety.atomic_persistence import StateLockTimeoutError
from tools.capability_policy import evaluate_action_policy
from tools.executor import ExecutionEngine, ToolSpec
from tools.idempotency import (
    ACTION_SEMANTIC_FIELDS,
    IDEMPOTENCY_KEY_CONFLICT_REASON_CODE,
    IDEMPOTENCY_RECEIPT_FIELDS,
    IDEMPOTENCY_RECORD_FIELDS,
    IDEMPOTENCY_STATE_REASON_CODES,
    IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
    DurableIdempotencyStore,
    IdempotencyState,
    IdempotencyStoreCorruptionError,
    OperationContext,
    canonical_action_fingerprint,
    project_scope_fingerprint,
)
from tools.memory import MemoryStore
from tools.validator import ALLOWED_ACTIONS
from trace_context import TraceContext, UNTRUSTED_IDENTITY_FIELDS


EXPECTED_EXECUTOR_OWNED_ACTION_FIELDS = frozenset(
    {
        "action_fingerprint",
        "idempotency_state",
        "idempotency_reason_code",
        "idempotency_conflict",
        "replayed",
        "dispatched",
        "manual_review_required",
        "unknown_outcome",
        "original_request_id",
        "original_trace_id",
        "original_model_call_id",
        "original_action_id",
        "runtime_requires_confirmation",
        "model_requests_confirmation",
        "policy_reason_code",
        "result_reason_code",
        "policy_allowed",
        "allowed",
    }
)
EXPECTED_PROVENANCE_OWNED_ACTION_FIELDS = frozenset(
    {
        "provenance_event_id",
        "event_id",
        "event_type",
        "timestamp_utc",
        "timestamp",
        "status",
        "outcome",
        "actor",
        "actor_type",
        "safe_payload_metadata",
        "payload",
        "prev_hash",
        "previous_hash",
        "payload_hash",
        "entry_hash",
        "event_hash",
        "chain_hash",
        "authority",
        "classification",
        "retention",
        "non_authoritative",
        "canonical_evidence",
    }
)


def _race_same_operation_worker(
    project_dir: str,
    state_home: str,
    operation_key: str,
    marker_path: str,
    start_event,
    result_queue,
) -> None:
    os.environ["AOIA_HOME"] = state_home
    project = Path(project_dir)
    memory = MemoryStore(
        project,
        project,
        initialize_vault=False,
        persist_on_init=False,
        record_session_start=False,
    )
    engine = ExecutionEngine(project, memory)

    def handler(_action: dict) -> dict:
        descriptor = os.open(
            marker_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.write(descriptor, f"{os.getpid()}\n".encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        time.sleep(0.2)
        return {"success": True, "bytes_written": 1}

    engine.tools["write_file"] = ToolSpec("write_file", handler, "race probe")
    engine._request_approval = lambda *_args, **_kwargs: True
    start_event.wait(timeout=10)
    try:
        result = engine.execute(
            {"action": "write_file", "path": "same.txt", "content": "same"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=OperationContext(operation_key),
        )
        result_queue.put(
            {
                "dispatched": result.get("dispatched"),
                "replayed": result.get("replayed"),
                "state": result.get("idempotency_state"),
                "reason": result.get("result_reason_code"),
            }
        )
    except BaseException as exc:  # pragma: no cover - returned for parent assertion
        result_queue.put({"error": f"{type(exc).__name__}:{exc}"})


class DurableActionIdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.state_home = self.root / "state-home"
        self.environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.state_home),
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
        self.temporary_directory.cleanup()

    @staticmethod
    def write_action(content: str = "same") -> dict[str, object]:
        return {
            "action": "write_file",
            "path": "target.txt",
            "content": content,
            "requires_confirmation": False,
        }

    def install_handler(self, handler) -> None:
        self.engine.tools["write_file"] = ToolSpec(
            "write_file", handler, "idempotency test handler"
        )

    def execute_approved(
        self,
        action: dict[str, object],
        operation: OperationContext,
    ) -> dict[str, object]:
        with patch.object(self.engine, "_request_approval", return_value=True):
            return self.engine.execute(
                action,
                action_context=TraceContext.new_request().new_action(),
                operation_context=operation,
            )

    def record_for(self, operation: OperationContext):
        record = self.engine.idempotency_store.load(operation)
        self.assertIsNotNone(record)
        return record

    def test_same_key_and_fingerprint_dispatches_once_then_replays(self) -> None:
        calls: list[str] = []
        self.install_handler(
            lambda action: calls.append(str(action["content"])) or {"success": True}
        )
        operation = OperationContext.new_operation()

        first = self.execute_approved(self.write_action(), operation)
        second = self.execute_approved(self.write_action(), operation)

        self.assertEqual(["same"], calls)
        self.assertTrue(first["dispatched"])
        self.assertFalse(first["replayed"])
        self.assertFalse(second["dispatched"])
        self.assertTrue(second["replayed"])
        self.assertTrue(second["success"])
        self.assertEqual(first["action_id"], second["original_action_id"])
        self.assertNotEqual(first["action_id"], second["action_id"])
        self.assertEqual(IdempotencyState.SUCCEEDED, self.record_for(operation).state)

    def test_same_key_with_different_semantic_payload_conflicts(self) -> None:
        handler = Mock(return_value={"success": True})
        self.install_handler(handler)
        operation = OperationContext.new_operation()

        self.execute_approved(self.write_action("first"), operation)
        conflict = self.execute_approved(self.write_action("different"), operation)

        self.assertEqual(1, handler.call_count)
        self.assertTrue(conflict["idempotency_conflict"])
        self.assertEqual("CONFLICT", conflict["idempotency_state"])
        self.assertEqual(
            IDEMPOTENCY_KEY_CONFLICT_REASON_CODE,
            conflict["result_reason_code"],
        )
        self.assertEqual(IdempotencyState.SUCCEEDED, self.record_for(operation).state)

    def test_model_supplied_internal_keys_are_ignored_and_not_fingerprinted(self) -> None:
        handler = Mock(return_value={"success": True})
        self.install_handler(handler)
        action = {
            **{
                field: "MODEL_CONTROLLED"
                for field in UNTRUSTED_IDENTITY_FIELDS
            },
            **self.write_action(),
        }

        with patch.object(self.engine, "_request_approval", return_value=True):
            result = self.engine.execute(action)

        self.assertTrue(str(result["operation_key"]).startswith("operation_"))
        self.assertNotEqual("MODEL_CONTROLLED", result["operation_key"])
        dispatched_action = handler.call_args.args[0]
        command_logs = list(self.memory.paths.command_logs_dir.glob("*.json"))
        self.assertEqual(1, len(command_logs))
        operational_action = json.loads(
            command_logs[0].read_text(encoding="utf-8")
        )["action"]
        for field in UNTRUSTED_IDENTITY_FIELDS:
            self.assertNotIn(field, dispatched_action)
            self.assertNotIn(field, operational_action)

    def test_two_real_processes_racing_one_key_dispatch_only_once(self) -> None:
        operation = OperationContext.new_operation()
        marker = self.root / "dispatches.txt"
        context = multiprocessing.get_context("spawn")
        start_event = context.Event()
        result_queue = context.Queue()
        arguments = (
            str(self.project),
            str(self.state_home),
            operation.operation_key,
            str(marker),
            start_event,
            result_queue,
        )
        processes = [
            context.Process(target=_race_same_operation_worker, args=arguments)
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        start_event.set()
        results = [result_queue.get(timeout=20) for _ in processes]
        for process in processes:
            process.join(timeout=20)
            self.assertEqual(0, process.exitcode)

        self.assertFalse(any("error" in result for result in results), results)
        self.assertEqual(1, sum(result["dispatched"] is True for result in results))
        lines = marker.read_text(encoding="ascii").splitlines()
        self.assertEqual(1, len(lines))
        self.assertEqual(IdempotencyState.SUCCEEDED, self.record_for(operation).state)

    def test_distinct_runtime_keys_execute_independently(self) -> None:
        handler = Mock(return_value={"success": True})
        self.install_handler(handler)

        first = self.execute_approved(
            self.write_action(), OperationContext.new_operation()
        )
        second = self.execute_approved(
            self.write_action(), OperationContext.new_operation()
        )

        self.assertEqual(2, handler.call_count)
        self.assertTrue(first["dispatched"])
        self.assertTrue(second["dispatched"])
        self.assertNotEqual(first["operation_key"], second["operation_key"])

    def test_declined_action_is_terminal_without_dispatch_started(self) -> None:
        handler = Mock(side_effect=AssertionError("declined action dispatched"))
        self.install_handler(handler)
        operation = OperationContext.new_operation()

        with patch.object(self.engine, "_request_approval", return_value=False):
            declined = self.engine.execute(
                self.write_action(),
                action_context=TraceContext.new_request().new_action(),
                operation_context=operation,
            )
        with patch.object(self.engine, "_request_approval", return_value=True):
            duplicate = self.engine.execute(
                self.write_action(),
                action_context=TraceContext.new_request().new_action(),
                operation_context=operation,
            )

        handler.assert_not_called()
        self.assertTrue(declined["cancelled"])
        self.assertFalse(declined["dispatched"])
        self.assertEqual(IdempotencyState.CANCELLED, self.record_for(operation).state)
        self.assertTrue(duplicate["replayed"])
        self.assertTrue(duplicate["cancelled"])

    def test_dispatch_started_duplicate_is_explicit_unknown_and_never_reclaimed(self) -> None:
        handler = Mock(side_effect=AssertionError("uncertain action redispatched"))
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        original_context = TraceContext.new_request().new_action()
        action = self.write_action()
        decision = evaluate_action_policy(action, original_context)
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=decision.capability_class,
        )
        resolution = self.engine.idempotency_store.reserve(
            operation,
            action_context=original_context,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class,
            project_scope=project_scope_fingerprint(self.project),
        )
        self.assertTrue(resolution.dispatch_allowed)
        self.engine.idempotency_store.transition(
            operation,
            owner_action_id=original_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.DISPATCH_STARTED,
            reason_code="IDEMPOTENCY_DISPATCH_STARTED",
        )

        duplicate = self.execute_approved(action, operation)

        handler.assert_not_called()
        self.assertTrue(duplicate["unknown_outcome"])
        self.assertTrue(duplicate["manual_review_required"])
        self.assertEqual(
            IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
            duplicate["result_reason_code"],
        )
        self.assertEqual(
            IdempotencyState.DISPATCH_STARTED,
            self.record_for(operation).state,
        )

    def test_timeout_is_durable_uncertainty_and_is_not_retried(self) -> None:
        handler = Mock(
            return_value={
                "success": False,
                "timed_out": True,
                "result_reason_code": "SUBPROCESS_HARD_TIMEOUT",
            }
        )
        self.install_handler(handler)
        operation = OperationContext.new_operation()

        first = self.execute_approved(self.write_action(), operation)
        second = self.execute_approved(self.write_action(), operation)

        self.assertEqual(1, handler.call_count)
        self.assertEqual("TIMED_OUT_OR_UNKNOWN", first["idempotency_state"])
        self.assertTrue(second["unknown_outcome"])
        self.assertFalse(second["dispatched"])
        self.assertEqual(
            IdempotencyState.TIMED_OUT_OR_UNKNOWN,
            self.record_for(operation).state,
        )

    def test_failed_before_dispatch_is_explicit_and_not_automatically_retried(self) -> None:
        handler = Mock(side_effect=AssertionError("failed-before-dispatch retried"))
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        original_context = TraceContext.new_request().new_action()
        action = self.write_action()
        decision = evaluate_action_policy(action, original_context)
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=decision.capability_class,
        )
        self.engine.idempotency_store.reserve(
            operation,
            action_context=original_context,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class,
            project_scope=project_scope_fingerprint(self.project),
        )
        self.engine.idempotency_store.transition(
            operation,
            owner_action_id=original_context.action_id,
            action_fingerprint=fingerprint,
            to_state=IdempotencyState.FAILED_BEFORE_DISPATCH,
            reason_code=IDEMPOTENCY_STATE_REASON_CODES[
                IdempotencyState.FAILED_BEFORE_DISPATCH
            ],
            terminal_receipt={
                "receipt_schema_version": "AOIA_IDEMPOTENCY_RECEIPT_1A",
                "success": False,
            },
        )

        duplicate = self.execute_approved(action, operation)

        handler.assert_not_called()
        self.assertTrue(duplicate["replayed"])
        self.assertFalse(duplicate["success"])
        self.assertEqual("FAILED_BEFORE_DISPATCH", duplicate["idempotency_state"])

    def test_terminal_persistence_failure_after_handler_leaves_unknown_record(self) -> None:
        handler = Mock(return_value={"success": True})
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        original_transition = self.engine.idempotency_store.transition

        def fail_terminal(*args, **kwargs):
            if kwargs.get("to_state") is IdempotencyState.SUCCEEDED:
                raise StateLockTimeoutError("synthetic terminal persistence failure")
            return original_transition(*args, **kwargs)

        with (
            patch.object(self.engine, "_request_approval", return_value=True),
            patch.object(
                self.engine.idempotency_store,
                "transition",
                side_effect=fail_terminal,
            ),
            self.assertRaises(StateLockTimeoutError),
        ):
            self.engine.execute(
                self.write_action(),
                action_context=TraceContext.new_request().new_action(),
                operation_context=operation,
            )

        self.assertEqual(1, handler.call_count)
        self.assertEqual(
            IdempotencyState.DISPATCH_STARTED,
            self.record_for(operation).state,
        )
        duplicate = self.execute_approved(self.write_action(), operation)
        self.assertEqual(1, handler.call_count)
        self.assertTrue(duplicate["unknown_outcome"])

    def test_reservation_persistence_failure_prevents_handler_dispatch(self) -> None:
        handler = Mock(side_effect=AssertionError("handler ran without reservation"))
        self.install_handler(handler)
        failure = StateLockTimeoutError("synthetic reservation lock failure")

        with (
            patch.object(self.engine, "_request_approval", return_value=True),
            patch.object(
                self.engine.idempotency_store,
                "reserve",
                side_effect=failure,
            ),
            self.assertRaises(StateLockTimeoutError) as raised,
        ):
            self.engine.execute(
                self.write_action(),
                action_context=TraceContext.new_request().new_action(),
                operation_context=OperationContext.new_operation(),
            )

        handler.assert_not_called()
        self.assertTrue(raised.exception.correlation["request_id"].startswith("request_"))

    def test_receipt_is_bounded_secret_free_and_preserves_traceability(self) -> None:
        synthetic_strings = {
            "message": "NZ_ULTRA_SECRET_001",
            "stdout": "NZ_ULTRA_SECRET_002",
            "result_reason_code": "SECRET_TOKEN",
            "policy_reason_code": "PRIVATE_PASSWORD",
            "permission_mode": "AWS_SECRET_ACCESS_KEY",
            "confidence_label": "CREDENTIAL_VALUE",
        }
        handler = Mock(
            return_value={
                "success": True,
                "bytes_written": 7,
                **synthetic_strings,
            }
        )
        self.install_handler(handler)
        operation = OperationContext.new_operation()

        first = self.execute_approved(self.write_action(), operation)
        record_path = self.engine.idempotency_store.record_path(
            operation.operation_key
        )
        raw_record = record_path.read_text(encoding="utf-8")
        replay = self.execute_approved(self.write_action(), operation)

        for synthetic_value in synthetic_strings.values():
            self.assertNotIn(synthetic_value, raw_record)
        self.assertNotIn("stdout", raw_record)
        self.assertEqual(7, replay["bytes_written"])
        self.assertEqual(first["action_id"], replay["original_action_id"])
        self.assertEqual(first["trace_id"], replay["original_trace_id"])

    def test_tampered_record_schema_and_state_metadata_fail_closed(self) -> None:
        self.install_handler(Mock(return_value={"success": True}))
        operation = OperationContext.new_operation()
        self.execute_approved(self.write_action(), operation)
        record_path = self.engine.idempotency_store.record_path(
            operation.operation_key
        )
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        payload["unexpected_model_metadata"] = "MODEL_CONTROLLED"
        record_path.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(IdempotencyStoreCorruptionError):
            self.engine.idempotency_store.load(operation)

        payload.pop("unexpected_model_metadata")
        payload["state"] = "INVENTED_RETRYABLE_STATE"
        record_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(IdempotencyStoreCorruptionError):
            self.engine.idempotency_store.load(operation)

    def test_tampered_state_receipt_and_reason_invariants_fail_closed(self) -> None:
        self.install_handler(Mock(return_value={"success": True}))
        operation = OperationContext.new_operation()
        self.execute_approved(self.write_action(), operation)
        record_path = self.engine.idempotency_store.record_path(
            operation.operation_key
        )
        original = json.loads(record_path.read_text(encoding="utf-8"))

        tampered_payloads: list[dict[str, object]] = []
        wrong_reason = dict(original)
        wrong_reason["reason_code"] = "SECRET_TOKEN"
        tampered_payloads.append(wrong_reason)

        failed_with_success = json.loads(json.dumps(original))
        failed_with_success["state"] = "FAILED_REPORTED"
        failed_with_success["reason_code"] = "ACTION_FAILED_REPORTED"
        tampered_payloads.append(failed_with_success)

        cancelled_without_flag = json.loads(json.dumps(original))
        cancelled_without_flag["state"] = "CANCELLED"
        cancelled_without_flag["reason_code"] = "HUMAN_APPROVAL_DECLINED"
        cancelled_without_flag["terminal_receipt"]["success"] = False
        tampered_payloads.append(cancelled_without_flag)

        timeout_without_uncertainty = json.loads(json.dumps(original))
        timeout_without_uncertainty["state"] = "TIMED_OUT_OR_UNKNOWN"
        timeout_without_uncertainty["reason_code"] = "ACTION_TIMED_OUT_OR_UNKNOWN"
        timeout_without_uncertainty["terminal_receipt"]["success"] = False
        tampered_payloads.append(timeout_without_uncertainty)

        succeeded_with_timeout = json.loads(json.dumps(original))
        succeeded_with_timeout["terminal_receipt"]["timed_out"] = True
        tampered_payloads.append(succeeded_with_timeout)

        blocked_with_uncertainty = json.loads(json.dumps(original))
        blocked_with_uncertainty["state"] = "BLOCKED"
        blocked_with_uncertainty["reason_code"] = "ACTION_BLOCKED_BY_POLICY"
        blocked_with_uncertainty["terminal_receipt"]["success"] = False
        blocked_with_uncertainty["terminal_receipt"]["blocked"] = True
        blocked_with_uncertainty["terminal_receipt"]["timed_out"] = True
        tampered_payloads.append(blocked_with_uncertainty)

        cancelled_with_unknown = json.loads(json.dumps(original))
        cancelled_with_unknown["state"] = "CANCELLED"
        cancelled_with_unknown["reason_code"] = "HUMAN_APPROVAL_DECLINED"
        cancelled_with_unknown["terminal_receipt"]["success"] = False
        cancelled_with_unknown["terminal_receipt"]["cancelled"] = True
        cancelled_with_unknown["terminal_receipt"]["unknown_outcome"] = True
        tampered_payloads.append(cancelled_with_unknown)

        failed_with_cancelled = json.loads(json.dumps(original))
        failed_with_cancelled["state"] = "FAILED_REPORTED"
        failed_with_cancelled["reason_code"] = "ACTION_FAILED_REPORTED"
        failed_with_cancelled["terminal_receipt"]["success"] = False
        failed_with_cancelled["terminal_receipt"]["cancelled"] = True
        tampered_payloads.append(failed_with_cancelled)

        for payload in tampered_payloads:
            with self.subTest(state=payload["state"], reason=payload["reason_code"]):
                record_path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(IdempotencyStoreCorruptionError):
                    self.engine.idempotency_store.load(operation)

    def test_registry_and_state_machine_structural_invariants(self) -> None:
        self.assertEqual(set(ALLOWED_ACTIONS), set(ACTION_SEMANTIC_FIELDS))
        expected_runtime_owned_fields = (
            IDEMPOTENCY_RECORD_FIELDS
            | IDEMPOTENCY_RECEIPT_FIELDS
            | EXPECTED_EXECUTOR_OWNED_ACTION_FIELDS
            | EXPECTED_PROVENANCE_OWNED_ACTION_FIELDS
        )
        self.assertLessEqual(
            expected_runtime_owned_fields,
            UNTRUSTED_IDENTITY_FIELDS,
        )
        self.assertEqual(
            {
                "RESERVED",
                "DISPATCH_STARTED",
                "SUCCEEDED",
                "BLOCKED",
                "CANCELLED",
                "FAILED_BEFORE_DISPATCH",
                "FAILED_REPORTED",
                "TIMED_OUT_OR_UNKNOWN",
                "UNKNOWN_OUTCOME",
                "CONFLICT",
            },
            {state.value for state in IdempotencyState},
        )

    def test_dual_package_namespace_enum_values_are_canonicalized(self) -> None:
        runtime_idempotency = importlib.import_module("runtime.tools.idempotency")
        runtime_policy = importlib.import_module("runtime.tools.capability_policy")
        operation = runtime_idempotency.OperationContext.new_operation()
        action_context = TraceContext.new_request().new_action()
        action = self.write_action()
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project,
            capability_class=runtime_policy.CapabilityClass.FILESYSTEM_MUTATION,
        )

        reservation = self.engine.idempotency_store.reserve(
            operation,
            action_context=action_context,
            action_fingerprint=fingerprint,
            capability_class=runtime_policy.CapabilityClass.FILESYSTEM_MUTATION,
            project_scope=project_scope_fingerprint(self.project),
        )
        transitioned = self.engine.idempotency_store.transition(
            operation,
            owner_action_id=action_context.action_id,
            action_fingerprint=fingerprint,
            to_state=runtime_idempotency.IdempotencyState.DISPATCH_STARTED,
            reason_code="IDEMPOTENCY_DISPATCH_STARTED",
        )

        self.assertTrue(reservation.dispatch_allowed)
        self.assertEqual(IdempotencyState.DISPATCH_STARTED, transitioned.state)


if __name__ == "__main__":
    unittest.main()
