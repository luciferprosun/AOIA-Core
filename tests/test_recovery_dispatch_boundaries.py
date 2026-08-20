from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import main
from runtime.task_checkpoints import TaskPhase, safe_context_metadata
from runtime.task_recovery import (
    RecoveryClassification,
    RecoveryDirective,
    RecoveryFencedError,
    RecoveryOperationStatus,
    RecoveryPurpose,
)
from tools.executor import ToolSpec
from runtime.tools.provenance import (
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import TraceContext


class _CanaryProvider:
    def __init__(self, request_canary: str, output_canary: str) -> None:
        self.request_canary = request_canary
        self.output_canary = output_canary
        self.calls = 0
        self.saw_raw_request = False
        self.runtime: main.AgentRuntime | None = None
        self.authorization_directive: RecoveryDirective | None = None
        self.wrong_directive_fenced = False
        self.other_thread_fenced = False

    def generate(self, prompt: str) -> str:
        self.calls += 1
        self.saw_raw_request = self.request_canary in prompt
        if self.runtime is not None:
            token = self.runtime._task_execution_token.get()
            if token is None:
                raise AssertionError("provider dispatch lacks its task token")
            service = self.runtime.task_recovery_service
            self.authorization_directive = (
                service.validate_dispatch_authorization(
                    token,
                    frozenset({RecoveryDirective.RESUME_MODEL}),
                )
            )
            try:
                service.validate_dispatch_authorization(
                    token,
                    frozenset({RecoveryDirective.CANCEL_TASK}),
                )
            except RecoveryFencedError:
                self.wrong_directive_fenced = True
            thread_errors: list[BaseException] = []

            def validate_from_other_thread() -> None:
                try:
                    service.validate_dispatch_authorization(
                        token,
                        frozenset({RecoveryDirective.RESUME_MODEL}),
                    )
                except BaseException as error:
                    thread_errors.append(error)

            contender = threading.Thread(target=validate_from_other_thread)
            contender.start()
            contender.join(timeout=5)
            self.other_thread_fenced = (
                len(thread_errors) == 1
                and isinstance(thread_errors[0], RecoveryFencedError)
            )
        return json.dumps(
            {
                "plan": [
                    {
                        "action": "respond",
                        "message": f"recovered {self.output_canary}",
                        "reason": f"provider result {self.output_canary}",
                    }
                ]
            }
        )

    def describe(self) -> str:
        return "synthetic/recovery-canary"

    def active_fallback_chain(self) -> list[str]:
        return ["synthetic/recovery-canary"]

    def provider_status(self) -> list[dict[str, object]]:
        return []

    def available_models(self) -> list[str]:
        return ["synthetic/recovery-canary"]


class RecoveryDispatchBoundaryTests(unittest.TestCase):
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
                "OPENAI_API_KEY": "NZ_RECOVERY_" + "SECRET_001",
                "SOME_PRIVATE_TOKEN": "NZ_RECOVERY_" + "SECRET_002",
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def _manual_between_checkpoint(
        self,
        runtime: main.AgentRuntime,
        request_text: str,
    ):
        trace = TraceContext.new_request()
        runtime.task_checkpoint_store.create_task(
            trace,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )
        checkpoint = runtime._start_task(trace, request_text)
        self.assertIs(TaskPhase.BETWEEN_STEPS, checkpoint.phase)
        runtime.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_STARTED,
                trace_context=trace,
                ingress="RUNTIME",
                request_length=len(request_text),
                slash_command=False,
            )
        )
        decision = runtime.task_recovery_service.show(trace.task_id)
        self.assertIs(
            RecoveryClassification.MANUAL_REVIEW_REQUIRED,
            decision.classification,
        )
        checkpoint = runtime.task_checkpoint_store.load(trace.task_id)
        self.assertIsNotNone(checkpoint)
        return trace, checkpoint

    @staticmethod
    def _trace_for_token(token) -> TraceContext:
        return TraceContext(
            request_id=token.request_id,
            trace_id=token.trace_id,
            task_id=token.task_id,
        )

    def test_public_runtime_dispatchers_reject_a_bare_recovery_guard_token(
        self,
    ) -> None:
        provider = _CanaryProvider("not-present", "not-persisted")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        request_text = "manual between-step task"
        _, checkpoint = self._manual_between_checkpoint(runtime, request_text)
        assert checkpoint is not None
        service = runtime.task_recovery_service

        with service.execution_guard(
            checkpoint.task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            recovery_trace = self._trace_for_token(token)
            with self.assertRaises(RecoveryFencedError):
                runtime.resume_model(
                    request_text,
                    trace_context=recovery_trace,
                    step_reservation=None,
                    recovery_token=token,
                )
            for dispatch in (
                lambda: runtime.resume_reserved_action(
                    {"action": "respond", "message": "must not run"},
                    trace_context=recovery_trace,
                    recovery_token=token,
                ),
                lambda: runtime.resume_waiting_action(
                    {"action": "respond", "message": "must not run"},
                    trace_context=recovery_trace,
                    recovery_token=token,
                ),
                lambda: runtime.cancel_recoverable_action(
                    trace_context=recovery_trace,
                    recovery_token=token,
                ),
            ):
                with self.assertRaises(RecoveryFencedError):
                    dispatch()

        self.assertEqual(0, provider.calls)
        unchanged = runtime.task_checkpoint_store.load(checkpoint.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(checkpoint.checkpoint_hash, unchanged.checkpoint_hash)

    def test_generic_executor_rejects_bare_recovery_token_before_p07(
        self,
    ) -> None:
        provider = _CanaryProvider("not-present", "not-persisted")
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        _, checkpoint = self._manual_between_checkpoint(
            runtime,
            "manual generic-executor task",
        )
        assert checkpoint is not None
        handler = Mock(return_value={"success": True})
        runtime.executor.tools["respond"] = ToolSpec(
            "respond",
            handler,
            "dispatch authorization test handler",
        )
        before_records = tuple(
            sorted(runtime.executor.idempotency_store.root_dir.glob("*.json"))
        )

        with runtime.task_recovery_service.execution_guard(
            checkpoint.task_id,
            purpose=RecoveryPurpose.RECOVERY,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            with self.assertRaises(RecoveryFencedError):
                runtime.executor.execute(
                    {"action": "respond", "message": "must not run"},
                    action_context=self._trace_for_token(token).new_action(),
                    recovery_token=token,
                )

        handler.assert_not_called()
        after_records = tuple(
            sorted(runtime.executor.idempotency_store.root_dir.glob("*.json"))
        )
        self.assertEqual(before_records, after_records)
        unchanged = runtime.task_checkpoint_store.load(checkpoint.task_id)
        self.assertIsNotNone(unchanged)
        assert unchanged is not None
        self.assertEqual(checkpoint.checkpoint_hash, unchanged.checkpoint_hash)

    def test_true_runtime_recovery_never_persists_request_or_output_canaries(
        self,
    ) -> None:
        request_canary = "NZ_RECOVERY_" + "SECRET_001"
        output_canary = "NZ_RECOVERY_" + "SECRET_002"
        self.assertEqual(request_canary, os.environ["OPENAI_API_KEY"])
        self.assertEqual(output_canary, os.environ["SOME_PRIVATE_TOKEN"])
        request_text = f"continue exact request containing {request_canary}"
        provider = _CanaryProvider(request_canary, output_canary)
        runtime = main.AgentRuntime(provider, "test prompt", self.project)
        provider.runtime = runtime
        original = TraceContext.new_request()
        runtime.task_checkpoint_store.create_task(
            original,
            max_steps=3,
            retry_budget=3,
            safe_context=safe_context_metadata(request_text),
        )

        with redirect_stdout(StringIO()):
            recovered = runtime.resume_recovery_task(
                original.task_id,
                request_text=request_text,
            )

        self.assertIs(RecoveryOperationStatus.COMPLETED, recovered.status)
        self.assertEqual(1, provider.calls)
        self.assertTrue(provider.saw_raw_request)
        self.assertIs(
            RecoveryDirective.RESUME_MODEL,
            provider.authorization_directive,
        )
        self.assertTrue(provider.wrong_directive_fenced)
        self.assertTrue(provider.other_thread_fenced)
        self.assertIsNone(
            runtime.task_recovery_service._dispatch_authorization.get()
        )
        forbidden = (request_canary.encode(), output_canary.encode())
        inspected = 0
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            inspected += 1
            payload = path.read_bytes()
            for canary in forbidden:
                self.assertNotIn(canary, payload, str(path))
        self.assertGreater(inspected, 0)


if __name__ == "__main__":
    unittest.main()
