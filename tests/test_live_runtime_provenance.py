from __future__ import annotations

import dataclasses
import datetime as dt
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from contextlib import ExitStack
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import main
import tools.provenance as provenance_module
from runtime import webapp
from runtime.providers import cli as provider_cli
from runtime.providers.contracts import LIVE_SUCCESS, ProviderRuntimeResult
from runtime.runtime_paths import runtime_state_dir
from runtime.safety.atomic_persistence import PersistenceError
from tools.executor import ExecutionEngine, ToolSpec
from tools.idempotency import (
    IdempotencyState,
    OperationContext,
    canonical_action_fingerprint,
)
from tools.memory import MemoryStore
from tools.provenance import (
    RUNTIME_PROVENANCE_AUTHORITY,
    RUNTIME_PROVENANCE_EVENT_FIELDS,
    RUNTIME_PROVENANCE_EVENT_TYPES,
    RUNTIME_PROVENANCE_RECORD_FIELDS,
    AppendOnlyProvenanceStore,
    ProvenanceAppendError,
    ProvenanceAppendStatus,
    ProvenanceChainError,
    ProvenanceEventConflictError,
    ProvenanceOutboxError,
    ProvenanceSchemaError,
    RuntimeProvenanceEvent,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
    verify_provenance_chain,
)
from trace_context import TraceContext, UNTRUSTED_IDENTITY_FIELDS


EXPECTED_EVENT_TYPES = {
    "REQUEST_STARTED", "REQUEST_COMPLETED", "MODEL_CALL_STARTED",
    "MODEL_CALL_COMPLETED", "MODEL_CALL_FAILED", "CAPABILITY_DECISION",
    "APPROVAL_GRANTED", "APPROVAL_DENIED", "IDEMPOTENCY_RESERVED",
    "IDEMPOTENCY_REPLAYED", "IDEMPOTENCY_CONFLICT",
    "ACTION_DISPATCH_STARTED", "ACTION_DISPATCH_SUCCEEDED",
    "ACTION_DISPATCH_FAILED", "ACTION_DISPATCH_TIMED_OUT",
    "ACTION_DISPATCH_BLOCKED", "ACTION_DISPATCH_CANCELLED",
    "UNKNOWN_OUTCOME_DETECTED", "PERSISTENCE_FAILURE",
    "PROVENANCE_RECOVERY",
    "TASK_CHECKPOINT_PREPARED", "TASK_CHECKPOINTED",
    "TASK_CHECKPOINT_ABORTED",
}


def _multiprocess_append_worker(root: str, count: int, queue) -> None:
    try:
        store = AppendOnlyProvenanceStore(Path(root))
        for index in range(count):
            trace = TraceContext.new_request()
            store.append_runtime_event(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.REQUEST_STARTED,
                    trace_context=trace,
                    ingress="RUNTIME",
                    request_length=index,
                    slash_command=False,
                )
            )
        queue.put(None)
    except BaseException as exc:  # pragma: no cover - returned to parent
        queue.put(f"{type(exc).__name__}:{exc}")


class FakeProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        self.calls += 1
        return self.response

    def describe(self) -> str:
        return "fake/test-model"

    def active_fallback_chain(self) -> list[str]:
        return ["fake/test-model"]

    def provider_status(self) -> list[dict[str, object]]:
        return []

    def available_models(self) -> list[str]:
        return ["fake/test-model"]


class RuntimeProvenanceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def request_event(self):
        return new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_STARTED,
            trace_context=TraceContext.new_request(),
            ingress="RUNTIME",
            request_length=7,
            slash_command=False,
        )

    def test_event_category_and_exact_authority_contract(self) -> None:
        self.assertEqual(EXPECTED_EVENT_TYPES, RUNTIME_PROVENANCE_EVENT_TYPES)
        self.assertEqual(
            set(),
            RUNTIME_PROVENANCE_EVENT_FIELDS - UNTRUSTED_IDENTITY_FIELDS,
        )
        store = AppendOnlyProvenanceStore(self.root)
        store.append_runtime_event(self.request_event())
        record = store.read_runtime_all()[0]
        self.assertEqual(RUNTIME_PROVENANCE_RECORD_FIELDS, frozenset(record))
        self.assertEqual(RUNTIME_PROVENANCE_AUTHORITY, record["authority"])
        self.assertEqual("AOIA_RUNTIME", record["actor"])
        self.assertEqual("RUNTIME", record["actor_type"])

    def test_same_event_is_idempotent_but_changed_same_id_conflicts(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        event = self.request_event()
        first = store.append_runtime_event(event)
        second = store.append_runtime_event(event)
        self.assertEqual(ProvenanceAppendStatus.APPENDED, first.status)
        self.assertEqual(ProvenanceAppendStatus.ALREADY_PRESENT, second.status)
        changed = dataclasses.replace(
            event,
            timestamp_utc=(
                dt.datetime.fromisoformat(event.timestamp_utc.replace("Z", "+00:00"))
                + dt.timedelta(seconds=1)
            ).isoformat().replace("+00:00", "Z"),
        )
        with self.assertRaises(ProvenanceEventConflictError):
            store.append_runtime_event(changed)
        self.assertEqual(1, len(store.read_runtime_all()))

    def test_two_real_processes_produce_one_linear_chain(self) -> None:
        context = multiprocessing.get_context("fork")
        queue = context.Queue()
        workers = [
            context.Process(
                target=_multiprocess_append_worker,
                args=(str(self.root), 12, queue),
            )
            for _ in range(2)
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=20)
            self.assertEqual(0, worker.exitcode)
        self.assertEqual([None, None], sorted([queue.get(), queue.get()], key=str))
        store = AppendOnlyProvenanceStore(self.root)
        records = store.read_runtime_all()
        self.assertEqual(24, len(records))
        self.assertEqual(list(range(1, 25)), [item["sequence"] for item in records])
        self.assertTrue(verify_provenance_chain(store.runtime_log_path).ok)

    def test_one_store_concurrent_legacy_and_runtime_writes_do_not_mix(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        barrier = threading.Barrier(2)
        errors: list[BaseException] = []

        def legacy_writer() -> None:
            try:
                barrier.wait()
                for index in range(30):
                    store.append_event("source_ingested", {"index": index})
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        def runtime_writer() -> None:
            try:
                barrier.wait()
                for index in range(30):
                    trace = TraceContext.new_request()
                    store.append_runtime_event(
                        new_runtime_provenance_event(
                            RuntimeProvenanceEventType.REQUEST_STARTED,
                            trace_context=trace,
                            ingress="RUNTIME",
                            request_length=index,
                            slash_command=False,
                        )
                    )
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        threads = [
            threading.Thread(target=legacy_writer),
            threading.Thread(target=runtime_writer),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
            self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(30, len(store.read_legacy_all()))
        self.assertEqual(30, len(store.read_runtime_all()))
        self.assertTrue(verify_provenance_chain(store.legacy_log_path).ok)
        self.assertTrue(verify_provenance_chain(store.runtime_log_path).ok)

    def test_tamper_partial_and_symlink_fail_closed(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        store.append_runtime_event(self.request_event())
        original = store.runtime_log_path.read_text(encoding="utf-8")

        record = json.loads(original)
        record["request_length"] = 999
        store.runtime_log_path.write_text(
            json.dumps(record) + "\n", encoding="utf-8"
        )
        with self.assertRaises(ProvenanceChainError):
            store.append_runtime_event(self.request_event())

        store.runtime_log_path.write_text(original.rstrip("\n"), encoding="utf-8")
        with self.assertRaises(ProvenanceChainError):
            store.append_runtime_event(self.request_event())

        victim = self.root / "victim"
        victim.write_text("unchanged", encoding="utf-8")
        store.runtime_log_path.unlink()
        store.runtime_log_path.symlink_to(victim)
        with self.assertRaises(ProvenanceChainError):
            store.append_runtime_event(self.request_event())
        self.assertEqual("unchanged", victim.read_text(encoding="utf-8"))

    def test_path_swap_after_fsync_is_detected_before_success(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        detached = self.root / "detached-ledger"
        original_fsync = provenance_module.os.fsync
        swapped = False

        def fsync_then_swap(descriptor: int) -> None:
            nonlocal swapped
            original_fsync(descriptor)
            if not swapped and store.runtime_log_path.exists():
                swapped = True
                store.runtime_log_path.replace(detached)
                store.runtime_log_path.write_text(
                    "attacker-controlled replacement\n", encoding="utf-8"
                )

        with patch.object(
            provenance_module.os,
            "fsync",
            side_effect=fsync_then_swap,
        ):
            with self.assertRaises(ProvenanceChainError):
                store.append_runtime_event(self.request_event())
        self.assertTrue(swapped)
        self.assertEqual(
            "attacker-controlled replacement\n",
            store.runtime_log_path.read_text(encoding="utf-8"),
        )

    def test_legacy_and_runtime_ledgers_coexist_without_mixing(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        store.append_event("source_ingested", {"artifact": "knowledge/a.md"})
        store.append_runtime_event(self.request_event())
        self.assertNotEqual(store.legacy_log_path, store.runtime_log_path)
        self.assertTrue(verify_provenance_chain(store.legacy_log_path).ok)
        self.assertTrue(verify_provenance_chain(store.runtime_log_path).ok)
        self.assertEqual(1, len(store.read_legacy_all()))
        self.assertEqual(1, len(store.read_runtime_all()))

    def test_terminal_outbox_recovers_once_after_append_failure(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        trace = TraceContext.new_request()
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_COMPLETED,
            trace_context=trace,
            ingress="RUNTIME",
            success=False,
            reason_code="REQUEST_FAILED",
        )
        with patch.object(
            store,
            "_append_runtime_without_recovery",
            side_effect=ProvenanceAppendError("forced terminal append failure"),
        ):
            with self.assertRaises(ProvenanceAppendError):
                store.append_terminal(event)
        pending = store.outbox_dir / f"{event.event_id}.json"
        self.assertTrue(pending.exists())

        recovered = AppendOnlyProvenanceStore(self.root)
        records = recovered.read_runtime_all()
        self.assertEqual(
            1, sum(item["event_id"] == event.event_id for item in records)
        )
        self.assertEqual(
            1,
            sum(item["event_type"] == "PROVENANCE_RECOVERY" for item in records),
        )
        self.assertFalse(pending.exists())

        restarted = AppendOnlyProvenanceStore(self.root)
        records = restarted.read_runtime_all()
        self.assertEqual(
            1, sum(item["event_id"] == event.event_id for item in records)
        )
        self.assertEqual(
            1,
            sum(item["event_type"] == "PROVENANCE_RECOVERY" for item in records),
        )

    def test_append_then_delivery_marker_failure_dedupes_on_restart(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_COMPLETED,
            trace_context=TraceContext.new_request(),
            ingress="RUNTIME",
            success=True,
        )
        with patch(
            "tools.provenance.locked_unlink",
            side_effect=ProvenanceOutboxError("forced delivery-marker failure"),
        ):
            with self.assertRaises(ProvenanceOutboxError):
                store.append_terminal(event)
        self.assertEqual(
            1,
            sum(
                item["event_id"] == event.event_id
                for item in store.read_runtime_all()
            ),
        )
        self.assertTrue((store.outbox_dir / f"{event.event_id}.json").exists())

        restarted = AppendOnlyProvenanceStore(self.root)
        records = restarted.read_runtime_all()
        self.assertEqual(
            1, sum(item["event_id"] == event.event_id for item in records)
        )
        self.assertFalse((store.outbox_dir / f"{event.event_id}.json").exists())
        self.assertEqual(
            1,
            sum(item["event_type"] == "PROVENANCE_RECOVERY" for item in records),
        )

    def test_malformed_pending_and_filename_mismatch_are_explicit(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)
        malformed = store.outbox_dir / "malformed.json"
        malformed.write_text("{", encoding="utf-8")
        with self.assertRaises(ProvenanceOutboxError):
            store.recover_pending_events()
        self.assertTrue(malformed.exists())

        malformed.unlink()
        trace = TraceContext.new_request()
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.REQUEST_COMPLETED,
            trace_context=trace,
            ingress="RUNTIME",
            success=True,
        )
        mismatched = store.outbox_dir / f"provenance_event_{'a' * 32}.json"
        mismatched.write_text(
            json.dumps(event.outbox_document(), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ProvenanceOutboxError):
            store.recover_pending_events()

        mismatched.unlink()
        victim = self.root / "outbox-victim"
        victim.write_text("victim-data", encoding="utf-8")
        symlink = store.outbox_dir / f"provenance_event_{'b' * 32}.json"
        symlink.symlink_to(victim)
        with self.assertRaises(ProvenanceOutboxError):
            store.recover_pending_events()
        self.assertEqual("victim-data", victim.read_text(encoding="utf-8"))

    def test_outbox_scan_stops_at_bounded_overflow_marker(self) -> None:
        store = AppendOnlyProvenanceStore(self.root)

        class CountingScandir:
            def __init__(self) -> None:
                self.consumed = 0

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback) -> None:
                return None

            def __iter__(self):
                return self

            def __next__(self):
                if self.consumed >= 10:
                    raise StopIteration
                self.consumed += 1
                return Mock(
                    path=str(store.outbox_dir / f"pending-{self.consumed}.json")
                )

        scanner = CountingScandir()
        with (
            patch.object(provenance_module, "MAX_PROVENANCE_OUTBOX_ENTRIES", 3),
            patch.object(
                provenance_module.os,
                "scandir",
                return_value=scanner,
            ),
        ):
            with self.assertRaises(ProvenanceOutboxError):
                store.recover_pending_events()
        self.assertEqual(4, scanner.consumed)

    def test_contradictory_events_fail_construction_and_deserialization(self) -> None:
        trace = TraceContext.new_request()
        model_call = trace.new_model_call()
        valid = new_runtime_provenance_event(
            RuntimeProvenanceEventType.MODEL_CALL_COMPLETED,
            model_call=model_call,
            requested_provider="provider",
            requested_model="model",
            retry_attempt=1,
            provider_attempt=1,
            success=True,
        )
        contradictions = (
            {"success": False},
            {"reason_code": "MODEL_CALL_FAILED"},
        )
        for changes in contradictions:
            with self.subTest(changes=changes):
                with self.assertRaises(ProvenanceSchemaError):
                    dataclasses.replace(valid, **changes)

        action = trace.new_action(model_call)
        operation = OperationContext.new_operation()
        fingerprint = "a" * 64
        succeeded = new_runtime_provenance_event(
            RuntimeProvenanceEventType.ACTION_DISPATCH_SUCCEEDED,
            action_context=action,
            operation_context=operation,
            action_name="respond",
            action_fingerprint=fingerprint,
            capability_class="READ_ONLY",
            idempotency_state="SUCCEEDED",
            replayed=False,
            dispatched=True,
            success=True,
            reason_code="ACTION_SUCCEEDED",
        )
        with self.assertRaises(ProvenanceSchemaError):
            dataclasses.replace(
                succeeded,
                success=False,
                idempotency_state="BLOCKED",
                dispatched=False,
            )
        with self.assertRaises(ProvenanceSchemaError):
            dataclasses.replace(
                succeeded,
                reason_code="HUMAN_APPROVAL_DECLINED",
            )
        document = succeeded.event_document()
        document["success"] = False
        with self.assertRaises(ProvenanceSchemaError):
            RuntimeProvenanceEvent.from_event_document(document)

    def test_synthetic_secrets_never_enter_ledger_or_outbox(self) -> None:
        secret = "SYNTHETIC_SECRET_TOKEN_123"
        store = AppendOnlyProvenanceStore(self.root)
        trace = TraceContext.new_request()
        model_call = trace.new_model_call()
        started = new_runtime_provenance_event(
            RuntimeProvenanceEventType.MODEL_CALL_STARTED,
            model_call=model_call,
            requested_provider=f"provider-{secret}",
            requested_model=f"model-{secret}",
            retry_attempt=1,
            provider_attempt=1,
        )
        store.append_runtime_event(started)
        terminal = new_runtime_provenance_event(
            RuntimeProvenanceEventType.MODEL_CALL_FAILED,
            model_call=model_call,
            requested_provider=f"provider-{secret}",
            requested_model=f"model-{secret}",
            retry_attempt=1,
            provider_attempt=1,
            success=False,
        )
        with patch.object(
            store,
            "_append_runtime_without_recovery",
            side_effect=ProvenanceAppendError("forced"),
        ):
            with self.assertRaises(ProvenanceAppendError):
                store.append_terminal(terminal)
        combined = store.runtime_log_path.read_text(encoding="utf-8") + "".join(
            item.read_text(encoding="utf-8")
            for item in store.outbox_dir.glob("*.json")
        )
        self.assertNotIn(secret, combined)
        self.assertNotIn("prompt", combined.casefold())
        self.assertNotIn("response", combined.casefold())


class ExecutorProvenanceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
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
        self.temporary_directory.cleanup()

    def install_handler(self, handler) -> None:
        self.engine.tools["respond"] = ToolSpec("respond", handler, "test")

    def test_valid_start_terminal_chain_and_replay_no_dispatch(self) -> None:
        handler = Mock(return_value={"success": True, "message": "safe"})
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        first = self.engine.execute(
            {"action": "respond", "message": "synthetic secret output"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        second = self.engine.execute(
            {"action": "respond", "message": "synthetic secret output"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        self.assertEqual(1, handler.call_count)
        self.assertTrue(first["dispatched"])
        self.assertTrue(second["replayed"])
        records = self.engine.provenance_store.read_runtime_all()
        event_types = [item["event_type"] for item in records]
        self.assertEqual(1, event_types.count("ACTION_DISPATCH_STARTED"))
        self.assertEqual(1, event_types.count("ACTION_DISPATCH_SUCCEEDED"))
        self.assertEqual(1, event_types.count("IDEMPOTENCY_REPLAYED"))
        self.assertTrue(verify_provenance_chain(
            self.engine.provenance_store.runtime_log_path
        ).ok)
        self.assertEqual(len(records), len({item["event_id"] for item in records}))

    def test_conflict_receipt_binds_attempted_fingerprint_and_never_dispatches(self) -> None:
        handler = Mock(return_value={"success": True, "message": "safe"})
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        self.engine.execute(
            {"action": "respond", "message": "first"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        attempted = {"action": "respond", "message": "different"}
        result = self.engine.execute(
            attempted,
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        self.assertTrue(result["idempotency_conflict"])
        self.assertEqual(1, handler.call_count)
        conflict = [
            item
            for item in self.engine.provenance_store.read_runtime_all()
            if item["event_type"] == "IDEMPOTENCY_CONFLICT"
        ][0]
        expected = canonical_action_fingerprint(
            attempted,
            project_dir=self.project,
            capability_class="READ_ONLY",
        )
        self.assertEqual(expected, conflict["action_fingerprint"])

    def test_handler_observes_both_idempotency_and_provenance_start(self) -> None:
        operation = OperationContext.new_operation()
        action_context = TraceContext.new_request().new_action()
        expected_task_id = operation.runtime_task_id()
        observed: dict[str, int] = {}

        def handler(_action):
            record = self.engine.idempotency_store.load(operation)
            self.assertEqual(IdempotencyState.DISPATCH_STARTED, record.state)
            events = self.engine.provenance_store.read_runtime_all()
            starts = [
                (index, event)
                for index, event in enumerate(events)
                if event["event_type"] == "ACTION_DISPATCH_STARTED"
                and event["task_id"] == expected_task_id
                and event["action_id"] == action_context.action_id
                and event["operation_key"] == operation.operation_key
            ]
            dispatch_checkpoints = [
                (index, event)
                for index, event in enumerate(events)
                if event["event_type"] == "TASK_CHECKPOINTED"
                and event["task_id"] == expected_task_id
                and event["request_id"] == action_context.request_id
                and event["trace_id"] == action_context.trace_id
                and event["task_phase"] == "PROVENANCE_DISPATCH_RECORDED"
            ]
            self.assertEqual(1, len(starts))
            self.assertEqual(1, len(dispatch_checkpoints))
            start_index, _start = starts[0]
            checkpoint_index, checkpoint_event = dispatch_checkpoints[0]
            self.assertLess(start_index, checkpoint_index)

            checkpoint = self.engine.task_checkpoint_store.load(expected_task_id)
            self.assertIsNotNone(checkpoint)
            self.assertEqual(action_context.action_id, checkpoint.current_action_id)
            self.assertEqual(operation.operation_key, checkpoint.current_idempotency_key)
            matching_transition = next(
                transition
                for transition in checkpoint.transitions
                if transition.sequence == checkpoint_event["checkpoint_version"]
            )
            self.assertEqual(
                "PROVENANCE_DISPATCH_RECORDED",
                matching_transition.to_phase,
            )
            self.assertEqual(
                checkpoint_event["event_id"],
                matching_transition.provenance_event_id,
            )
            observed["start"] = start_index
            observed["checkpoint"] = checkpoint_index
            return {"success": True}

        self.install_handler(handler)
        self.engine.execute(
            {"action": "respond", "message": "safe"},
            action_context=action_context,
            operation_context=operation,
        )
        self.assertLess(observed["start"], observed["checkpoint"])

    def test_corrupt_chain_and_start_failure_block_handler(self) -> None:
        handler = Mock(return_value={"success": True})
        self.install_handler(handler)
        first_operation = OperationContext.new_operation()
        self.engine.execute(
            {"action": "respond", "message": "first"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=first_operation,
        )
        path = self.engine.provenance_store.runtime_log_path
        lines = path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["outcome"] = "SUCCEEDED"
        lines[0] = json.dumps(first)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(PersistenceError):
            self.engine.execute(
                {"action": "respond", "message": "second"},
                action_context=TraceContext.new_request().new_action(),
            )
        self.assertEqual(1, handler.call_count)

        fresh_root = self.root / "fresh-state"
        fresh_store = AppendOnlyProvenanceStore(fresh_root)
        fresh_engine = ExecutionEngine(
            self.project, self.memory, provenance_store=fresh_store
        )
        fresh_handler = Mock(return_value={"success": True})
        fresh_engine.tools["respond"] = ToolSpec("respond", fresh_handler, "test")
        original_append = fresh_store.append_runtime_event

        def fail_start(event):
            if event.event_type == "ACTION_DISPATCH_STARTED":
                raise ProvenanceAppendError("forced start failure")
            return original_append(event)

        start_operation = OperationContext.new_operation()
        with patch.object(fresh_store, "append_runtime_event", side_effect=fail_start):
            with self.assertRaises(ProvenanceAppendError):
                fresh_engine.execute(
                    {"action": "respond", "message": "safe"},
                    action_context=TraceContext.new_request().new_action(),
                    operation_context=start_operation,
                )
        fresh_handler.assert_not_called()
        self.assertEqual(
            IdempotencyState.FAILED_BEFORE_DISPATCH,
            fresh_engine.idempotency_store.load(start_operation).state,
        )
        self.assertFalse(any(
            item["event_type"] == "ACTION_DISPATCH_STARTED"
            for item in fresh_store.read_runtime_all()
        ))

    def test_terminal_provenance_fault_reconciles_then_replays_without_dispatch(self) -> None:
        handler = Mock(return_value={"success": True, "message": "safe"})
        self.install_handler(handler)
        operation = OperationContext.new_operation()
        store = self.engine.provenance_store
        original_append = store._append_runtime_without_recovery
        failed = False

        def fail_first_terminal(event):
            nonlocal failed
            if (
                not failed
                and event.event_type == "ACTION_DISPATCH_SUCCEEDED"
            ):
                failed = True
                raise ProvenanceAppendError("forced post-idempotency terminal fault")
            return original_append(event)

        with patch.object(
            store,
            "_append_runtime_without_recovery",
            side_effect=fail_first_terminal,
        ):
            with self.assertRaises(ProvenanceAppendError):
                self.engine.execute(
                    {"action": "respond", "message": "safe"},
                    action_context=TraceContext.new_request().new_action(),
                    operation_context=operation,
                )
        self.assertEqual(1, handler.call_count)
        self.assertEqual(
            IdempotencyState.SUCCEEDED,
            self.engine.idempotency_store.load(operation).state,
        )
        self.assertEqual(1, len(list(store.outbox_dir.glob("*.json"))))

        restarted = AppendOnlyProvenanceStore(self.memory.paths.state_dir)
        self.engine.provenance_store = restarted
        replay = self.engine.execute(
            {"action": "respond", "message": "safe"},
            action_context=TraceContext.new_request().new_action(),
            operation_context=operation,
        )
        self.assertEqual(1, handler.call_count)
        self.assertTrue(replay["replayed"])
        self.assertFalse(replay["dispatched"])
        records = restarted.read_runtime_all()
        self.assertEqual(
            1,
            sum(item["event_type"] == "ACTION_DISPATCH_SUCCEEDED" for item in records),
        )
        self.assertEqual(
            1,
            sum(item["event_type"] == "ACTION_DISPATCH_STARTED" for item in records),
        )
        self.assertEqual(
            1,
            sum(item["event_type"] == "IDEMPOTENCY_REPLAYED" for item in records),
        )

    def test_ledger_excludes_action_secret_and_operational_log_is_noncanonical(self) -> None:
        secret = "SYNTHETIC_ACTION_SECRET_456"
        self.install_handler(lambda _action: {"success": True, "message": secret})
        self.engine.execute(
            {"action": "respond", "message": secret},
            action_context=TraceContext.new_request().new_action(),
        )
        ledger = self.engine.provenance_store.runtime_log_path.read_text(
            encoding="utf-8"
        )
        self.assertNotIn(secret, ledger)
        command_log = next(self.memory.paths.command_logs_dir.glob("*.json"))
        operational = json.loads(command_log.read_text(encoding="utf-8"))
        self.assertTrue(operational["authority"]["non_authoritative"])
        self.assertFalse(operational["authority"]["canonical_evidence"])


class RuntimeLifecycleIntegrationTests(unittest.TestCase):
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

    def test_request_and_model_lifecycle_and_no_terminal_retry(self) -> None:
        provider = FakeProvider(
            '{"plan":[{"action":"respond","message":"done","reason":"safe"}]}'
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        runtime.run_text_request("/status", ingress="WEB")
        records = runtime.provenance_store.read_runtime_all()
        request_lifecycle = [
            record
            for record in records
            if record["event_type"] in {"REQUEST_STARTED", "REQUEST_COMPLETED"}
        ]
        self.assertEqual(
            ["REQUEST_STARTED", "REQUEST_COMPLETED"],
            [record["event_type"] for record in request_lifecycle],
        )
        self.assertEqual("WEB", request_lifecycle[0]["ingress"])
        self.assertEqual(
            request_lifecycle[0]["task_id"],
            request_lifecycle[1]["task_id"],
        )

        trace = TraceContext.new_request()
        original_append_terminal = runtime.provenance_store.append_terminal

        def fail_model_terminal(event):
            if event.event_type == "MODEL_CALL_COMPLETED":
                raise ProvenanceAppendError("forced terminal persistence")
            return original_append_terminal(event)

        with patch.object(
            runtime.provenance_store,
            "append_terminal",
            side_effect=fail_model_terminal,
        ):
            with self.assertRaises(RuntimeError):
                runtime.ask_model("synthetic prompt secret", trace)
        self.assertEqual(1, provider.calls)

    def test_full_request_model_terminal_fault_never_red_dispatches_provider(self) -> None:
        provider = FakeProvider(
            '{"plan":[{"action":"respond","message":"done","reason":"safe"}]}'
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        original_append = runtime.provenance_store._append_runtime_without_recovery
        failed = False

        def fail_model_terminal_once(event):
            nonlocal failed
            if not failed and event.event_type == "MODEL_CALL_COMPLETED":
                failed = True
                raise ProvenanceAppendError("forced model terminal fault")
            return original_append(event)

        with (
            patch.object(
                runtime.provenance_store,
                "_append_runtime_without_recovery",
                side_effect=fail_model_terminal_once,
            ),
            patch.object(runtime, "handle_external_review_route", return_value=False),
            patch.object(runtime, "handle_local_route", return_value=False),
            patch.object(runtime, "handle_knowledge_route", return_value=False),
        ):
            with self.assertRaises(ProvenanceAppendError):
                runtime.run_text_request("provider request", ingress="WEB")
        self.assertEqual(1, provider.calls)
        records = runtime.provenance_store.read_runtime_all()
        self.assertEqual(
            1,
            sum(item["event_type"] == "MODEL_CALL_COMPLETED" for item in records),
        )
        self.assertTrue(any(
            item["event_type"] == "PROVENANCE_RECOVERY" for item in records
        ))
        request_terminals = [
            item for item in records if item["event_type"] == "REQUEST_COMPLETED"
        ]
        self.assertEqual([False], [item["success"] for item in request_terminals])

    def test_action_terminal_fault_propagates_and_request_is_not_false_success(self) -> None:
        provider = FakeProvider(
            '{"plan":[{"action":"respond","message":"done","reason":"safe"}]}'
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        handler = Mock(return_value={"success": True, "message": "done"})
        runtime.executor.tools["respond"] = ToolSpec("respond", handler, "test")
        original_append = runtime.provenance_store._append_runtime_without_recovery
        failed = False

        def fail_action_terminal_once(event):
            nonlocal failed
            if not failed and event.event_type == "ACTION_DISPATCH_SUCCEEDED":
                failed = True
                raise ProvenanceAppendError("forced action terminal fault")
            return original_append(event)

        with (
            patch.object(
                runtime.provenance_store,
                "_append_runtime_without_recovery",
                side_effect=fail_action_terminal_once,
            ),
            patch.object(runtime, "handle_external_review_route", return_value=False),
            patch.object(runtime, "handle_local_route", return_value=False),
            patch.object(runtime, "handle_knowledge_route", return_value=False),
        ):
            with self.assertRaises(ProvenanceAppendError):
                runtime.run_text_request("execute one plan", ingress="TUI")
        self.assertEqual(1, provider.calls)
        self.assertEqual(1, handler.call_count)
        records = runtime.provenance_store.read_runtime_all()
        self.assertEqual(
            1,
            sum(
                item["event_type"] == "ACTION_DISPATCH_SUCCEEDED"
                for item in records
            ),
        )
        self.assertTrue(any(
            item["event_type"] == "PROVENANCE_RECOVERY" for item in records
        ))
        request_terminals = [
            item for item in records if item["event_type"] == "REQUEST_COMPLETED"
        ]
        self.assertEqual([False], [item["success"] for item in request_terminals])

    def test_full_model_request_records_model_lifecycle_without_prompt(self) -> None:
        secret = "SYNTHETIC_PROMPT_SECRET_789"
        provider = FakeProvider(
            '{"plan":[{"action":"respond","message":"done","reason":"safe"}]}'
        )
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(runtime, "handle_external_review_route", return_value=False)
            )
            stack.enter_context(
                patch.object(runtime, "handle_local_route", return_value=False)
            )
            stack.enter_context(
                patch.object(runtime, "handle_knowledge_route", return_value=False)
            )
            runtime.run_text_request(secret, ingress="TUI")
        records = runtime.provenance_store.read_runtime_all()
        lifecycle = [
            item
            for item in records
            if item["event_type"]
            in {
                "REQUEST_STARTED",
                "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED",
                "REQUEST_COMPLETED",
            }
        ]
        self.assertEqual(
            [
                "REQUEST_STARTED",
                "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED",
                "REQUEST_COMPLETED",
            ],
            [item["event_type"] for item in lifecycle],
        )
        self.assertEqual("TUI", lifecycle[0]["ingress"])
        self.assertEqual(
            {lifecycle[0]["task_id"]},
            {item["task_id"] for item in lifecycle},
        )
        ledger = runtime.provenance_store.runtime_log_path.read_text(encoding="utf-8")
        self.assertNotIn(secret, ledger)
        session = runtime.session_log.read_text(encoding="utf-8").splitlines()
        for line in session:
            record = json.loads(line)
            self.assertTrue(record["authority"]["non_authoritative"])
            self.assertFalse(record["authority"]["canonical_evidence"])

    def test_operator_api_and_live_cli_have_request_model_receipts(self) -> None:
        result = ProviderRuntimeResult(
            provider_id="kimi_chat",
            model_id="moonshot-test",
            mode="live",
            status=LIVE_SUCCESS,
            redacted_request_preview="redacted",
            response_text="synthetic provider output",
        )
        with patch(
            "runtime.providers.selector.run_selected_provider",
            return_value=result,
        ):
            payload = webapp.build_operator_chat_payload(
                {
                    "provider_id": "kimi_chat",
                    "model_id": "moonshot-test",
                    "prompt": "operator synthetic secret",
                }
            )
        self.assertTrue(payload["ok"])
        operator_store = AppendOnlyProvenanceStore(
            runtime_state_dir(webapp.PROJECT_DIR) / "state"
        )
        operator_records = operator_store.read_runtime_all()
        operator_request = next(
            item
            for item in operator_records
            if item["event_type"] == "REQUEST_STARTED"
            and item["ingress"] == "OPERATOR_API"
        )
        operator_lifecycle = [
            item
            for item in operator_records
            if item["task_id"] == operator_request["task_id"]
            and item["event_type"]
            in {
                "REQUEST_STARTED",
                "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED",
                "REQUEST_COMPLETED",
            }
        ]
        self.assertEqual(
            [
                "REQUEST_STARTED", "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED", "REQUEST_COMPLETED",
            ],
            [item["event_type"] for item in operator_lifecycle],
        )

        cli_result = dataclasses.replace(result, model_id="cli-test")
        with (
            patch.object(provider_cli, "run_selected_provider", return_value=cli_result),
            redirect_stdout(StringIO()),
        ):
            exit_code = provider_cli.main(
                [
                    "--provider", "kimi_chat",
                    "--model", "cli-test",
                    "--prompt", "cli synthetic secret",
                    "--max-tokens", "32",
                    "--live",
                    "--acknowledge-live-provider-test",
                    "--activate-manual-live-test",
                ]
            )
        self.assertEqual(0, exit_code)
        cli_store = AppendOnlyProvenanceStore(
            runtime_state_dir(Path(provider_cli.__file__).resolve().parents[1])
            / "state"
        )
        cli_records = cli_store.read_runtime_all()
        cli_request = next(
            item
            for item in cli_records
            if item["event_type"] == "REQUEST_STARTED"
            and item["ingress"] == "CLI"
        )
        cli_lifecycle = [
            item
            for item in cli_records
            if item["task_id"] == cli_request["task_id"]
            and item["event_type"]
            in {
                "REQUEST_STARTED",
                "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED",
                "REQUEST_COMPLETED",
            }
        ]
        self.assertEqual(
            [
                "REQUEST_STARTED", "MODEL_CALL_STARTED",
                "MODEL_CALL_COMPLETED", "REQUEST_COMPLETED",
            ],
            [item["event_type"] for item in cli_lifecycle],
        )


if __name__ == "__main__":
    unittest.main()
