from __future__ import annotations

import datetime as dt
import multiprocessing
import os
import tempfile
import threading
import unittest
from pathlib import Path

from runtime.task_checkpoints import (
    DurableTaskCheckpointStore,
    safe_context_metadata,
)
from runtime.task_recovery import TaskRecoveryService
from runtime.tools.provenance import AppendOnlyProvenanceStore
from runtime.trace_context import TaskContext, TraceContext


def _die_while_holding_recovery_claim(
    state_dir: str,
    project_dir: str,
    task_id: str,
    entered: multiprocessing.synchronize.Event,
) -> None:
    service = TaskRecoveryService(
        Path(state_dir),
        project_dir=Path(project_dir),
        lock_timeout_seconds=0.3,
        lease_seconds=1.0,
    )
    with service.execution_guard(task_id) as token:
        if token.generation != 1:
            os._exit(18)
        entered.set()
        os._exit(17)


class RecoveryIndependenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        )
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.project = self.root / "project"
        self.state.mkdir()
        self.project.mkdir()
        self.provenance = AppendOnlyProvenanceStore(self.state)
        self.checkpoints = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=self.provenance,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_task(
        self,
        *,
        task_id: str | None = None,
        checkpoints: DurableTaskCheckpointStore | None = None,
    ) -> str:
        store = checkpoints or self.checkpoints
        trace = (
            TraceContext.new_request()
            if task_id is None
            else TraceContext.new_request(TaskContext(task_id))
        )
        store.create_task(
            trace,
            max_steps=2,
            retry_budget=2,
            safe_context=safe_context_metadata("independence probe"),
        )
        return trace.task_id

    def test_different_tasks_can_hold_recovery_guards_concurrently(self) -> None:
        first_task = self._create_task()
        second_task = self._create_task()
        first_service = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )
        second_service = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )
        entered = threading.Event()
        release = threading.Event()
        errors: list[BaseException] = []

        def hold_first() -> None:
            try:
                with first_service.execution_guard(first_task):
                    entered.set()
                    release.wait(2)
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)
                entered.set()

        worker = threading.Thread(target=hold_first)
        worker.start()
        self.assertTrue(entered.wait(1))
        with second_service.execution_guard(second_task) as token:
            self.assertEqual(second_task, token.task_id)
        release.set()
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], errors)

    def test_same_task_id_in_different_project_roots_does_not_block(self) -> None:
        task_id = TraceContext.new_request().task_id
        other_state = self.root / "other-state"
        other_project = self.root / "other-project"
        other_state.mkdir()
        other_project.mkdir()
        self._create_task(task_id=task_id)
        other_provenance = AppendOnlyProvenanceStore(other_state)
        other_checkpoints = DurableTaskCheckpointStore(
            other_state,
            project_dir=other_project,
            provenance_store=other_provenance,
        )
        self._create_task(task_id=task_id, checkpoints=other_checkpoints)
        first = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )
        second = TaskRecoveryService(
            other_state,
            project_dir=other_project,
            checkpoint_store=other_checkpoints,
            provenance_store=other_provenance,
            lock_timeout_seconds=0.2,
            lease_seconds=1.0,
        )
        with first.execution_guard(task_id) as first_token:
            with second.execution_guard(task_id) as second_token:
                self.assertNotEqual(
                    first_token.project_scope,
                    second_token.project_scope,
                )

    def test_process_death_leaves_stale_claim_then_allows_next_generation(self) -> None:
        task_id = self._create_task()
        context = multiprocessing.get_context("spawn")
        entered = context.Event()
        worker = context.Process(
            target=_die_while_holding_recovery_claim,
            args=(str(self.state), str(self.project), task_id, entered),
        )
        worker.start()
        self.assertTrue(entered.wait(5))
        worker.join(5)
        self.assertEqual(17, worker.exitcode)

        observer = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.3,
            lease_seconds=1.0,
        )
        stale = observer._read_claim(task_id)
        self.assertIsNotNone(stale)
        assert stale is not None
        self.assertEqual("ACTIVE", stale.status.value)
        self.assertEqual(1, stale.generation)

        future = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=2)
        takeover = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.3,
            lease_seconds=1.0,
            clock=lambda: future,
        )
        with takeover.execution_guard(task_id) as token:
            self.assertEqual(2, token.generation)


if __name__ == "__main__":
    unittest.main()
