from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
import time
import unittest
from pathlib import Path
from queue import Empty
from unittest.mock import patch

import runtime.safety.atomic_persistence as atomic_persistence
import tools.memory as memory_module
from runtime.safety.atomic_persistence import (
    STATE_ATOMIC_WRITE_FAILED_REASON_CODE,
    STATE_CORRUPT_REASON_CODE,
    STATE_LOCK_TIMEOUT_REASON_CODE,
    AtomicWriteError,
    InterProcessFileLock,
    StateCorruptionError,
    StateLockTimeoutError,
    atomic_write_json,
    state_resource_lock_path,
)
from runtime_paths import runtime_state_dir
from tools.executor import ExecutionEngine
from tools.memory import AgentMemory, MemoryStore
from trace_context import TraceContext


def _snapshot_writer(
    project_dir: str,
    aoia_home: str,
    writer: str,
    result_queue: multiprocessing.Queue,
    start_event: multiprocessing.Event | None = None,
    delay_inside_lock: float = 0.0,
    lock_timeout: float = 2.0,
) -> None:
    os.environ["AOIA_HOME"] = aoia_home
    try:
        store = MemoryStore(
            Path(project_dir),
            Path(project_dir),
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
            state_lock_timeout_seconds=lock_timeout,
        )
        store.memory.current_task = writer
        store.memory.recent_outputs = [
            {
                "writer": writer,
                "payload": writer * 10_000,
            }
        ]
        if delay_inside_lock:
            original_replace = atomic_persistence._atomic_replace_bytes_unlocked

            def delayed_replace(target: Path, payload: bytes, *, mode: int) -> None:
                if start_event is not None:
                    start_event.set()
                time.sleep(delay_inside_lock)
                original_replace(target, payload, mode=mode)

            atomic_persistence._atomic_replace_bytes_unlocked = delayed_replace
        elif start_event is not None:
            if not start_event.wait(timeout=3.0):
                raise RuntimeError("concurrent snapshot start signal timed out")

        started = time.monotonic()
        store.save()
        result_queue.put(
            {
                "ok": True,
                "writer": writer,
                "elapsed": time.monotonic() - started,
            }
        )
    except Exception as exc:
        result_queue.put(
            {
                "ok": False,
                "writer": writer,
                "error_type": type(exc).__name__,
                "reason_code": getattr(exc, "reason_code", ""),
                "message": str(exc),
            }
        )


def _append_history_worker(
    project_dir: str,
    aoia_home: str,
    writer: str,
    count: int,
    start_event: multiprocessing.Event,
    result_queue: multiprocessing.Queue,
) -> None:
    os.environ["AOIA_HOME"] = aoia_home
    try:
        store = MemoryStore(
            Path(project_dir),
            Path(project_dir),
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        if not start_event.wait(timeout=3.0):
            raise RuntimeError("append start signal timed out")
        for index in range(count):
            store.append_history(
                "concurrent_append_test",
                {"writer": writer, "index": index},
            )
        result_queue.put({"ok": True, "writer": writer})
    except Exception as exc:
        result_queue.put(
            {
                "ok": False,
                "writer": writer,
                "error_type": type(exc).__name__,
                "reason_code": getattr(exc, "reason_code", ""),
                "message": str(exc),
            }
        )


class AtomicStatePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temporary_directory.name)
        self.aoia_home = self.temp_root / "aoia-state"
        self.project_root = self.temp_root / "project"
        self.project_root.mkdir()
        self.environment = patch.dict(
            os.environ,
            {"AOIA_HOME": str(self.aoia_home)},
            clear=False,
        )
        self.environment.start()
        self.state_dir = runtime_state_dir(self.project_root) / "state"
        self.target = self.state_dir / "atomic-test.json"
        self.lock_path = state_resource_lock_path(self.state_dir, self.target)
        self.process_context = multiprocessing.get_context("spawn")

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def _queue_result(
        self,
        process: multiprocessing.Process,
        result_queue: multiprocessing.Queue,
    ) -> dict:
        process.join(timeout=8.0)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2.0)
            self.fail("child persistence test process did not terminate")
        self.assertEqual(0, process.exitcode)
        try:
            return result_queue.get(timeout=2.0)
        except Empty:
            self.fail("child persistence test process produced no result")

    def test_atomic_replacement_produces_complete_json_and_removes_temp_file(self) -> None:
        self.state_dir.mkdir(parents=True)
        self.target.write_text('{"version":"old"}', encoding="utf-8")

        atomic_write_json(
            self.target,
            {"version": "new", "items": list(range(100))},
            lock_path=self.lock_path,
        )

        payload = json.loads(self.target.read_text(encoding="utf-8"))
        self.assertEqual("new", payload["version"])
        self.assertEqual(list(range(100)), payload["items"])
        self.assertEqual([], list(self.state_dir.glob(f".{self.target.name}.*.tmp")))

    def test_failure_before_replace_preserves_previous_valid_snapshot(self) -> None:
        self.state_dir.mkdir(parents=True)
        old_text = '{"version":"old"}'
        self.target.write_text(old_text, encoding="utf-8")

        with patch.object(
            atomic_persistence.os,
            "fsync",
            side_effect=OSError("synthetic pre-replace failure"),
        ):
            with self.assertRaises(AtomicWriteError) as raised:
                atomic_write_json(
                    self.target,
                    {"version": "new"},
                    lock_path=self.lock_path,
                )

        self.assertEqual(STATE_ATOMIC_WRITE_FAILED_REASON_CODE, raised.exception.reason_code)
        self.assertEqual(old_text, self.target.read_text(encoding="utf-8"))
        self.assertEqual({"version": "old"}, json.loads(old_text))
        self.assertEqual([], list(self.state_dir.glob(f".{self.target.name}.*.tmp")))

    def test_replace_failure_preserves_previous_valid_snapshot(self) -> None:
        self.state_dir.mkdir(parents=True)
        old_text = '{"version":"old"}'
        self.target.write_text(old_text, encoding="utf-8")

        with patch.object(
            atomic_persistence.os,
            "replace",
            side_effect=OSError("synthetic replace failure"),
        ):
            with self.assertRaises(AtomicWriteError):
                atomic_write_json(
                    self.target,
                    {"version": "new"},
                    lock_path=self.lock_path,
                )

        self.assertEqual(old_text, self.target.read_text(encoding="utf-8"))
        self.assertEqual({"version": "old"}, json.loads(old_text))
        self.assertEqual([], list(self.state_dir.glob(f".{self.target.name}.*.tmp")))

    def test_two_real_process_writes_are_serialized_and_leave_valid_snapshot(self) -> None:
        initial = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            record_session_start=False,
        )
        result_queue = self.process_context.Queue()
        first_inside_lock = self.process_context.Event()
        first = self.process_context.Process(
            target=_snapshot_writer,
            args=(
                str(self.project_root),
                str(self.aoia_home),
                "first",
                result_queue,
                first_inside_lock,
                0.35,
                2.0,
            ),
        )
        second = self.process_context.Process(
            target=_snapshot_writer,
            args=(
                str(self.project_root),
                str(self.aoia_home),
                "second",
                result_queue,
                first_inside_lock,
                0.0,
                2.0,
            ),
        )

        first.start()
        second.start()
        first_result = self._queue_result(first, result_queue)
        second_result = self._queue_result(second, result_queue)
        by_writer = {
            first_result["writer"]: first_result,
            second_result["writer"]: second_result,
        }
        self.assertTrue(by_writer["first"]["ok"], by_writer["first"])
        self.assertTrue(by_writer["second"]["ok"], by_writer["second"])
        self.assertGreaterEqual(by_writer["second"]["elapsed"], 0.20)

        final_payload = json.loads(initial.state_file.read_text(encoding="utf-8"))
        self.assertEqual("second", final_payload["current_task"])
        self.assertEqual("second", final_payload["recent_outputs"][0]["writer"])
        self.assertEqual([], list(initial.state_file.parent.glob(f".{initial.state_file.name}.*.tmp")))

    def test_lock_timeout_is_explicit_and_bounded(self) -> None:
        store = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            record_session_start=False,
        )
        result_queue = self.process_context.Queue()
        process = self.process_context.Process(
            target=_snapshot_writer,
            args=(
                str(self.project_root),
                str(self.aoia_home),
                "blocked",
                result_queue,
                None,
                0.0,
                0.10,
            ),
        )

        with InterProcessFileLock(store._lock_for(store.state_file), timeout_seconds=1.0):
            process.start()
            result = self._queue_result(process, result_queue)

        self.assertFalse(result["ok"], result)
        self.assertEqual("StateLockTimeoutError", result["error_type"])
        self.assertEqual(STATE_LOCK_TIMEOUT_REASON_CODE, result["reason_code"])

    def test_different_project_state_locks_do_not_block_each_other(self) -> None:
        first_store = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            record_session_start=False,
        )
        second_project = self.temp_root / "second-project"
        second_project.mkdir()
        result_queue = self.process_context.Queue()
        process = self.process_context.Process(
            target=_snapshot_writer,
            args=(
                str(second_project),
                str(self.aoia_home),
                "independent",
                result_queue,
                None,
                0.0,
                0.10,
            ),
        )

        with InterProcessFileLock(
            first_store._lock_for(first_store.state_file),
            timeout_seconds=1.0,
        ):
            process.start()
            result = self._queue_result(process, result_queue)

        self.assertTrue(result["ok"], result)
        second_state = runtime_state_dir(second_project) / "state" / "agent_state.json"
        self.assertEqual("independent", json.loads(second_state.read_text())["current_task"])

    def test_malformed_missing_and_valid_empty_state_are_distinguishable(self) -> None:
        missing = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        self.assertIsNone(missing.load())

        missing.memory = AgentMemory(session_id="", cwd="")
        missing.save()
        valid_empty = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        ).load()
        self.assertIsNotNone(valid_empty)
        assert valid_empty is not None
        self.assertEqual("", valid_empty.session_id)
        self.assertEqual([], valid_empty.recent_outputs)

        missing.state_file.write_text('{"session_id":', encoding="utf-8")
        with self.assertRaises(StateCorruptionError) as raised:
            MemoryStore(
                self.project_root,
                self.project_root,
                initialize_vault=False,
                persist_on_init=False,
                record_session_start=False,
            )
        self.assertEqual(STATE_CORRUPT_REASON_CODE, raised.exception.reason_code)

    def test_concurrent_append_logs_keep_every_record_parseable(self) -> None:
        initial = MemoryStore(
            self.project_root,
            self.project_root,
            record_session_start=False,
        )
        writer_count = 2
        records_per_writer = 20
        start_event = self.process_context.Event()
        result_queue = self.process_context.Queue()
        processes = [
            self.process_context.Process(
                target=_append_history_worker,
                args=(
                    str(self.project_root),
                    str(self.aoia_home),
                    f"writer-{index}",
                    records_per_writer,
                    start_event,
                    result_queue,
                ),
            )
            for index in range(writer_count)
        ]
        for process in processes:
            process.start()
        start_event.set()
        results = [self._queue_result(process, result_queue) for process in processes]
        self.assertTrue(all(result["ok"] for result in results), results)

        lines = initial.history_file.read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines]
        self.assertEqual(writer_count * records_per_writer, len(records))
        observed = {
            (record["payload"]["writer"], record["payload"]["index"])
            for record in records
        }
        expected = {
            (f"writer-{writer}", index)
            for writer in range(writer_count)
            for index in range(records_per_writer)
        }
        self.assertEqual(expected, observed)

    def test_traced_execution_retains_identity_through_atomic_persistence(self) -> None:
        memory = MemoryStore(
            self.project_root,
            self.project_root,
            record_session_start=False,
        )
        engine = ExecutionEngine(self.project_root, memory)
        trace = TraceContext.new_request()
        model_call = trace.new_model_call()
        action_context = trace.new_action(model_call)

        result = engine.execute(
            {"action": "respond", "message": "atomic trace"},
            action_context=action_context,
        )

        self.assertEqual(action_context.identity_fields(), {
            field: result[field]
            for field in action_context.identity_fields()
        })
        command_logs = list(memory.paths.command_logs_dir.glob("*.json"))
        self.assertEqual(1, len(command_logs))
        operational = json.loads(command_logs[0].read_text(encoding="utf-8"))
        history = json.loads(memory.history_file.read_text(encoding="utf-8").splitlines()[0])
        for field, expected in action_context.identity_fields().items():
            self.assertEqual(expected, operational[field])
            self.assertEqual(expected, history["payload"][field])
        self.assertFalse(operational["authority"]["canonical_evidence"])

    def test_persistence_failure_retains_existing_trace_identity(self) -> None:
        memory = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        engine = ExecutionEngine(self.project_root, memory)
        action_context = TraceContext.new_request().new_action()
        failure = StateLockTimeoutError(
            "synthetic traced state lock timeout",
            target_path=memory.state_file,
        )

        with patch.object(memory_module, "atomic_write_json", side_effect=failure):
            with self.assertRaises(StateLockTimeoutError) as raised:
                engine.execute(
                    {"action": "respond", "message": "persistence failure"},
                    action_context=action_context,
                )

        self.assertEqual(STATE_LOCK_TIMEOUT_REASON_CODE, raised.exception.reason_code)
        self.assertEqual(
            action_context.identity_fields(),
            raised.exception.correlation,
        )

    def test_memory_store_save_cannot_bypass_atomic_locked_boundary(self) -> None:
        store = MemoryStore(
            self.project_root,
            self.project_root,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        with patch.object(memory_module, "atomic_write_json") as atomic_write:
            store.save()

        atomic_write.assert_called_once()
        call = atomic_write.call_args
        self.assertEqual(store.state_file, call.args[0])
        self.assertEqual(store._lock_for(store.state_file), call.kwargs["lock_path"])
        source = Path(memory_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("self.state_file.write_text(", source)
        self.assertNotIn("open(self.state_file, \"w\"", source)


if __name__ == "__main__":
    unittest.main()
