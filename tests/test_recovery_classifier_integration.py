from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import runtime.task_recovery as task_recovery_module
from runtime.task_checkpoints import (
    DurableTaskCheckpointStore,
    TaskPhase,
    TaskState,
    safe_context_metadata,
)
from runtime.task_recovery import (
    RecoveryClassification,
    RecoveryDirective,
    TaskRecoveryService,
)
from tools.capability_policy import evaluate_action_policy
from tools.executor import ExecutionEngine, ToolSpec
from tools.idempotency import (
    canonical_action_fingerprint,
    IdempotencyState,
    OperationContext,
    project_scope_fingerprint,
)
from tools.memory import MemoryStore
from runtime.tools.provenance import AppendOnlyProvenanceStore
from runtime.trace_context import TraceContext


class _SimulatedProcessDeath(BaseException):
    pass


class RecoveryClassifierIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=os.environ.get("TMPDIR") or None
        )
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.root / "aoia-home"),
                "AOIA_LEGACY_FILESYSTEM_ENABLED": "1",
            },
            clear=False,
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.memory = MemoryStore(
            self.project,
            self.project,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
        )
        self.state = self.memory.paths.state_dir
        self.provenance = AppendOnlyProvenanceStore(self.state)
        self.checkpoints = DurableTaskCheckpointStore(
            self.state,
            project_dir=self.project,
            provenance_store=self.provenance,
        )
        self.engine = ExecutionEngine(
            self.project,
            self.memory,
            provenance_store=self.provenance,
            task_checkpoint_store=self.checkpoints,
        )
        self.service = TaskRecoveryService(
            self.state,
            project_dir=self.project,
            checkpoint_store=self.checkpoints,
            idempotency_store=self.engine.idempotency_store,
            provenance_store=self.provenance,
            lock_timeout_seconds=0.3,
            lease_seconds=1.0,
        )
        self.engine.task_recovery_service = self.service

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_legal_pre_p07_policy_block_remains_terminal_blocked(self) -> None:
        result = self.engine.execute(
            {"action": "definitely_not_an_action"}
        )
        checkpoint = self.checkpoints.load(result["task_id"])
        self.assertIsNotNone(checkpoint)
        assert checkpoint is not None
        self.assertEqual(TaskState.BLOCKED, checkpoint.state)
        self.assertIsNone(checkpoint.current_idempotency_state)

        decision = self.service.show(checkpoint.task_id)
        self.assertEqual(RecoveryClassification.BLOCKED, decision.classification)
        self.assertEqual(RecoveryDirective.NO_ACTION, decision.directive)
        self.assertEqual("RECOVERY_TASK_BLOCKED", decision.reason_code)

    def test_legal_idempotency_conflict_is_terminal_and_not_pending(self) -> None:
        handler = Mock(return_value={"success": True, "message": "ok"})
        self.engine.tools["respond"] = ToolSpec(
            "respond", handler, "synthetic response"
        )
        trace = TraceContext.new_request()
        created = self.checkpoints.create_task(
            trace,
            max_steps=2,
            retry_budget=0,
            safe_context=safe_context_metadata("conflict"),
        )
        operation = OperationContext.new_operation()
        first = self.checkpoints.reserve_step(trace.task_id)
        self.engine.execute(
            {"action": "respond", "message": "first"},
            action_context=trace.new_action(),
            operation_context=operation,
            step_reservation=first,
        )
        after_first = self.checkpoints.load(created.task_id)
        assert after_first is not None
        between = self.checkpoints.transition(
            trace.task_id,
            expected_version=after_first.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_BETWEEN_STEPS",
        )
        second = self.checkpoints.reserve_step(between.task_id)
        result = self.engine.execute(
            {"action": "respond", "message": "different"},
            action_context=trace.new_action(),
            operation_context=operation,
            step_reservation=second,
        )
        self.assertTrue(result["idempotency_conflict"])
        self.assertEqual(1, handler.call_count)

        decision = self.service.show(trace.task_id)
        self.assertEqual(RecoveryClassification.CONFLICT, decision.classification)
        self.assertEqual(RecoveryDirective.NO_ACTION, decision.directive)
        discovery = self.service.discover(limit=8)
        self.assertEqual(0, discovery.pending_count)
        self.assertNotIn(
            trace.task_id,
            {item.task_id for item in self.service.list_incomplete_tasks(limit=8)},
        )

    def test_pristine_standalone_action_checkpoint_never_becomes_model_work(self) -> None:
        context = TraceContext.new_request().new_action()
        checkpoint = self.checkpoints.ensure_for_action(context)
        decision = self.service.show(checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(RecoveryDirective.REQUIRE_OPERATOR_ACK, decision.directive)

    def test_orphan_approval_or_reservation_evidence_never_resumes_model(self) -> None:
        write_handler = Mock(return_value={"success": True})
        self.engine.tools["write_file"] = ToolSpec(
            "write_file", write_handler, "synthetic write"
        )
        approval_operation = OperationContext.new_operation()
        with (
            patch.object(
                self.engine,
                "_request_approval",
                side_effect=_SimulatedProcessDeath("approval wait crash"),
            ),
            self.assertRaises(_SimulatedProcessDeath),
        ):
            self.engine.execute(
                {"action": "write_file", "path": "safe.txt", "content": "x"},
                action_context=TraceContext.new_request().new_action(),
                operation_context=approval_operation,
            )
        approval_checkpoint = self.checkpoints.load(
            approval_operation.runtime_task_id()
        )
        self.assertIsNotNone(approval_checkpoint)
        assert approval_checkpoint is not None
        approval_decision = self.service.show(approval_checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            approval_decision.classification,
        )
        self.assertEqual(0, write_handler.call_count)

        read_handler = Mock(return_value={"success": True})
        self.engine.tools["read_file"] = ToolSpec(
            "read_file", read_handler, "synthetic read"
        )
        reserve_operation = OperationContext.new_operation()
        original_after = self.engine._after_idempotency_resolution

        def crash_after_reservation(*args, **kwargs):
            original_after(*args, **kwargs)
            raise _SimulatedProcessDeath("reservation receipt crash")

        with (
            patch.object(
                self.engine,
                "_after_idempotency_resolution",
                side_effect=crash_after_reservation,
            ),
            self.assertRaises(_SimulatedProcessDeath),
        ):
            self.engine.execute(
                {"action": "read_file", "path": "README.md"},
                action_context=TraceContext.new_request().new_action(),
                operation_context=reserve_operation,
            )
        reserved_checkpoint = self.checkpoints.load(
            reserve_operation.runtime_task_id()
        )
        self.assertIsNotNone(reserved_checkpoint)
        assert reserved_checkpoint is not None
        record = self.engine.idempotency_store.load(reserve_operation)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(IdempotencyState.RESERVED, record.state)
        reserved_decision = self.service.show(reserved_checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            reserved_decision.classification,
        )
        self.assertEqual(0, read_handler.call_count)

    def test_p07_only_orphan_reservation_never_resumes_model(self) -> None:
        trace = TraceContext.new_request()
        checkpoint = self.checkpoints.create_task(
            trace,
            max_steps=2,
            retry_budget=2,
            safe_context=safe_context_metadata("p07 orphan"),
        )
        action = {"action": "read_file", "path": "README.md"}
        policy = evaluate_action_policy(action)
        operation = OperationContext.new_operation()
        self.engine.idempotency_store.reserve(
            operation,
            action_context=trace.new_action(),
            action_fingerprint=canonical_action_fingerprint(
                action,
                project_dir=self.project,
                capability_class=policy.capability_class,
            ),
            capability_class=policy.capability_class,
            project_scope=project_scope_fingerprint(self.project),
        )

        decision = self.service.show(checkpoint.task_id)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(
            RecoveryDirective.REQUIRE_OPERATOR_ACK,
            decision.directive,
        )
        self.assertEqual(
            "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            decision.reason_code,
        )

    def test_p07_orphan_scan_fails_closed_on_root_replacement(self) -> None:
        trace = TraceContext.new_request()
        checkpoint = self.checkpoints.create_task(
            trace,
            max_steps=2,
            retry_budget=2,
            safe_context=safe_context_metadata("p07 root replacement"),
        )
        action = {"action": "read_file", "path": "README.md"}
        policy = evaluate_action_policy(action)
        operation = OperationContext.new_operation()
        self.engine.idempotency_store.reserve(
            operation,
            action_context=trace.new_action(),
            action_fingerprint=canonical_action_fingerprint(
                action,
                project_dir=self.project,
                capability_class=policy.capability_class,
            ),
            capability_class=policy.capability_class,
            project_scope=project_scope_fingerprint(self.project),
        )
        idempotency_root = self.engine.idempotency_store.root_dir
        moved_root = idempotency_root.with_name("idempotency.moved")
        original_read = task_recovery_module.read_json_snapshot
        swapped = False

        def swap_before_read(path, *args, **kwargs):
            nonlocal swapped
            if not swapped and Path(path).parent == idempotency_root:
                idempotency_root.rename(moved_root)
                idempotency_root.mkdir()
                swapped = True
            return original_read(path, *args, **kwargs)

        with patch.object(
            task_recovery_module,
            "read_json_snapshot",
            side_effect=swap_before_read,
        ):
            decision = self.service.show(checkpoint.task_id)

        self.assertTrue(swapped)
        self.assertEqual(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        self.assertEqual(
            "RECOVERY_REQUEST_EXECUTION_UNCERTAIN",
            decision.reason_code,
        )


if __name__ == "__main__":
    unittest.main()
