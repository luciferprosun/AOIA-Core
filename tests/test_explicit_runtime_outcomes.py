from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from commands.base import CommandResult

from runtime.outcomes import (
    NZ_OUTCOME_SCHEMA_VERSION,
    NZOutcome,
    NZOutcomeStatus,
    NZReasonCode,
    attach_outcome,
    outcome_from_exception,
    outcome_from_tool_result,
)
from runtime.orchestrator.gemini_gemma import GeminiGemmaOrchestrator
from runtime.providers.config import ProviderManager
from runtime.providers.contracts import (
    ERROR,
    LIVE_SUCCESS,
    ProviderRuntimeResult,
)
from runtime.providers.errors import (
    ModelResponseMalformedError,
    provider_reason_code,
)
from runtime.providers.gateway import run_provider_request
from runtime.providers.payloads import build_provider_envelope
from runtime.task_recovery import (
    RecoveryClassification,
    RecoveryDirective,
    RecoveryOperationResult,
    RecoveryOperationStatus,
)
from runtime.safety.bounded_subprocess import (
    SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
    SubprocessResourceProfileName,
    run_bounded_subprocess,
)
from runtime.safety.subprocess_env import build_subprocess_env
from runtime.tools.idempotency import OperationContext
from runtime.tools.memory import MemoryStore
from runtime.trace_context import (
    TraceContext,
    TracedModelOutput,
    strip_untrusted_identity_fields,
)


TEST_TMP_ROOT = Path(
    "/media/l/LSC_DATA2/AIOA_WORKSPACE/runtime-storage/tmp"
)


class SequenceProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        response = self.responses[self.calls]
        self.calls += 1
        return response

    @staticmethod
    def describe() -> str:
        return "synthetic/model"

    @staticmethod
    def active_fallback_chain() -> list[str]:
        return ["synthetic/model"]

    @staticmethod
    def provider_status() -> list[dict[str, object]]:
        return []


class InvalidTracedProvider(SequenceProvider):
    def __init__(self, output: object) -> None:
        super().__init__([])
        self.output = output

    def generate_traced(self, *_args, **_kwargs):
        return self.output


class EmptyOrchestratorPlanProvider(SequenceProvider):
    def __init__(self) -> None:
        super().__init__([])

    def generate_traced(self, _prompt, trace_context, on_attempt=None):
        model_call = trace_context.new_model_call()
        if on_attempt is not None:
            on_attempt("started", model_call, "synthetic", "synthetic/model", 1)
            on_attempt("succeeded", model_call, "synthetic", "synthetic/model", 1)
        return TracedModelOutput(
            text='{"steps":[]}',
            model_call=model_call,
            provider="synthetic",
            model="synthetic/model",
        )


class ExplicitRuntimeOutcomeTests(unittest.TestCase):
    def test_status_vocabulary_is_exact_and_contract_is_bounded(self) -> None:
        self.assertEqual(
            {
                "SUCCESS",
                "PARTIAL",
                "DEGRADED",
                "BLOCKED",
                "CANCELLED",
                "FAILED",
                "TIMEOUT",
                "CONFLICT",
                "UNKNOWN_OUTCOME",
                "MANUAL_REVIEW_REQUIRED",
            },
            {item.value for item in NZOutcomeStatus},
        )
        outcome = NZOutcome.build(
            NZOutcomeStatus.PARTIAL,
            NZReasonCode.STEP_BUDGET_EXHAUSTED,
            data={"zero_is_valid": 0},
        )
        self.assertEqual(NZ_OUTCOME_SCHEMA_VERSION, outcome.to_dict()["schema_version"])
        self.assertEqual(0, outcome.to_dict()["data"]["zero_is_valid"])
        with self.assertRaisesRegex(ValueError, "message_safe"):
            NZOutcome.build("FAILED", "ACTION_FAILED", message_safe="")
        with self.assertRaisesRegex(ValueError, "reason_code"):
            NZOutcome.build("FAILED", "")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            NZOutcome.build("MODEL_SAYS_SUCCESS", None)
        with self.assertRaisesRegex(ValueError, "byte bound"):
            NZOutcome.build(
                "FAILED",
                "ACTION_FAILED",
                data={"large": ["x" * 4096 for _ in range(9)]},
            )

    def test_from_dict_is_strict_and_dual_import_identity_is_preserved(self) -> None:
        import outcomes
        import runtime.outcomes as runtime_outcomes

        self.assertIs(outcomes.NZOutcome, runtime_outcomes.NZOutcome)
        payload = NZOutcome.build("SUCCESS").to_dict()
        self.assertEqual(NZOutcomeStatus.SUCCESS, NZOutcome.from_dict(payload).status)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            NZOutcome.from_dict({**payload, "invented": True})
        with self.assertRaisesRegex(ValueError, "schema"):
            NZOutcome.from_dict({**payload, "schema_version": "EVIL"})

    def test_outcome_module_defaults_are_immutable(self) -> None:
        import runtime.outcomes as runtime_outcomes

        default_message = NZOutcome.build("FAILED", "ACTION_FAILED").message_safe
        with self.assertRaises(TypeError):
            runtime_outcomes._SAFE_MESSAGES[NZOutcomeStatus.FAILED] = "unsafe"  # type: ignore[index]
        with self.assertRaises(TypeError):
            runtime_outcomes._RUNTIME_ID_PREFIXES["request_id"] = "unsafe"  # type: ignore[index]
        self.assertEqual(
            default_message,
            NZOutcome.build("FAILED", "ACTION_FAILED").message_safe,
        )

    def test_untrusted_syntactically_valid_ids_never_enter_projection(self) -> None:
        spoof = TraceContext.new_request().new_action()
        raw = {
            "success": True,
            **spoof.identity_fields(),
            "outcome": {"status": "BLOCKED"},
        }
        projected = attach_outcome(raw)
        nested = projected["outcome"]
        for field in ("request_id", "trace_id", "task_id", "model_call_id", "action_id"):
            self.assertNotIn(field, nested)
        authoritative = TraceContext.new_request().new_action()
        trusted = attach_outcome(
            raw,
            request_id=authoritative.request_id,
            trace_id=authoritative.trace_id,
            task_id=authoritative.task_id,
            action_id=authoritative.action_id,
        )["outcome"]
        self.assertEqual(authoritative.action_id, trusted["action_id"])
        self.assertNotEqual(spoof.action_id, trusted["action_id"])

    def test_model_authority_aliases_are_stripped(self) -> None:
        action = {
            "action": "respond",
            "message": "safe",
            "status": "SUCCESS",
            "outcome_status": "SUCCESS",
            "reason_code": "REQUEST_COMPLETED",
            "message_safe": "model controls truth",
            "degraded": False,
            "data": {"authority": True},
            "metadata": {"authority": True},
            "outcome": {"status": "SUCCESS"},
        }
        stripped = strip_untrusted_identity_fields(action)
        self.assertEqual({"action", "message"}, set(stripped))

    def test_browser_fallback_is_degraded_and_not_success(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            child_code = """
import json
import sys
from pathlib import Path
import runtime.tools.browser_tools as browser_tools

browser_tools.AOIA_LEGACY_BROWSER_ENABLED = True
root = Path(sys.argv[1])
bridge = browser_tools.BrowserBridge(root / "profile", root / "shots")
bridge.fallback_active = True
result = bridge.browser_open("about:blank")
closed = bridge.browser_close()
print(json.dumps({"result": result, "closed": closed}, sort_keys=True))
"""
            child = subprocess.run(
                [sys.executable, "-c", child_code, tmp],
                cwd=Path(__file__).resolve().parents[1],
                env=build_subprocess_env(
                    fixed={
                        "PYTHONDONTWRITEBYTECODE": "1",
                        "PYTHONPYCACHEPREFIX": str(Path(tmp) / "pycache"),
                    }
                ),
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            child_payload = json.loads(child.stdout)
            result = child_payload["result"]
            closed = child_payload["closed"]
        self.assertFalse(result["success"])
        self.assertTrue(result["degraded"])
        self.assertEqual("fallback", result["browser_mode"])
        self.assertEqual("DEGRADED", result["outcome"]["status"])
        self.assertEqual(
            "BROWSER_FALLBACK_UNVERIFIED",
            result["outcome"]["reason_code"],
        )
        self.assertFalse(closed["success"])
        self.assertEqual("DEGRADED", closed["outcome"]["status"])

    def test_tool_result_maps_timeout_conflict_unknown_and_approval_denial(self) -> None:
        cases = (
            (
                {"success": False, "timed_out": True, "idempotency_state": "TIMED_OUT_OR_UNKNOWN", "replayed": False},
                ("TIMEOUT", "PROCESS_TIMEOUT"),
            ),
            (
                {"success": False, "timed_out": True, "unknown_outcome": True, "replayed": True},
                ("UNKNOWN_OUTCOME", "UNKNOWN_OUTCOME"),
            ),
            (
                {"success": False, "idempotency_conflict": True},
                ("CONFLICT", "IDEMPOTENCY_CONFLICT"),
            ),
            (
                {"success": False, "cancelled": True, "result_reason_code": "HUMAN_APPROVAL_DECLINED"},
                ("CANCELLED", "HUMAN_APPROVAL_DECLINED"),
            ),
            (
                {"success": False, "blocked": True, "policy_reason_code": "CAPABILITY_DENIED"},
                ("BLOCKED", "CAPABILITY_DENIED"),
            ),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                projected = outcome_from_tool_result(raw)
                self.assertEqual(expected, (projected.status.value, projected.reason_code))

    def test_malformed_gateway_payload_has_explicit_reason(self) -> None:
        envelope = build_provider_envelope(
            provider_id="openrouter_chat",
            model_id="synthetic-model",
            prompt="synthetic prompt",
            params={"max_tokens": 8},
            dry_run=False,
            created_at="2026-08-21T00:00:00Z",
        )
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"{}"
        response.__exit__.return_value = False
        with (
            patch("runtime.providers.gateway._read_api_key", return_value="synthetic-key"),
            patch("runtime.providers.gateway.urlopen", return_value=response),
        ):
            result = run_provider_request(
                envelope,
                live=True,
                acknowledge_live_provider_test=True,
                activation_status="live_allowed_for_manual_test",
            )
        self.assertEqual(ERROR, result.status)
        self.assertEqual("MODEL_RESPONSE_MALFORMED", result.reason_code)
        self.assertEqual("FAILED", result.outcome.status.value)
        self.assertNotIn("synthetic-key", json.dumps(result.to_dict()))

    def test_provider_success_requires_text_and_timeout_projects_timeout(self) -> None:
        with self.assertRaisesRegex(ValueError, "response_text"):
            ProviderRuntimeResult(
                provider_id="mock_chat",
                model_id="synthetic",
                mode="live",
                status=LIVE_SUCCESS,
                redacted_request_preview="{}",
                response_text=" ",
            )
        timed_out = ProviderRuntimeResult(
            provider_id="mock_chat",
            model_id="synthetic",
            mode="live",
            status=ERROR,
            redacted_request_preview="{}",
            error_message="safe",
            reason_code="MODEL_TIMEOUT",
        )
        self.assertEqual("TIMEOUT", timed_out.outcome.status.value)
        with self.assertRaisesRegex(ValueError, "reason_code"):
            ProviderRuntimeResult(
                provider_id="mock_chat",
                model_id="synthetic",
                mode="live",
                status=ERROR,
                redacted_request_preview="{}",
                reason_code="",
            )

    def test_provider_manager_rejects_empty_before_success_observer(self) -> None:
        class EmptyProvider:
            full_name = "synthetic/model"

            @staticmethod
            def generate(_prompt: str) -> str:
                return "   "

        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            manager = ProviderManager(Path(tmp))
            observed: list[str] = []
            trace = TraceContext.new_request()
            with (
                patch.object(manager, "_fallback_candidates", return_value=["openrouter/model"]),
                patch.object(manager, "_build_provider", return_value=EmptyProvider()),
                patch("runtime.providers.config.require_provider_calls_enabled"),
            ):
                with self.assertRaises(ModelResponseMalformedError):
                    manager.generate_traced(
                        "prompt",
                        trace,
                        on_attempt=lambda status, *_args: observed.append(status),
                    )
        self.assertEqual(["started", "failed"], observed)

    def test_agent_rejects_invalid_nested_traced_response_as_malformed(self) -> None:
        import main

        malformed_values = (
            None,
            object(),
            TracedModelOutput(text="{}", model_call=None),  # type: ignore[arg-type]
            TracedModelOutput(
                text="{}",
                model_call=TraceContext.new_request().new_model_call(),
            ),
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            for index, malformed in enumerate(malformed_values):
                with self.subTest(index=index):
                    project = root / f"project-{index}"
                    project.mkdir()
                    with (
                        patch.dict(
                            os.environ,
                            {"AOIA_HOME": str(root / f"aoia-home-{index}")},
                        ),
                        patch.object(main, "MODEL_RETRY_DELAYS", (0.0,)),
                    ):
                        runtime = main.AgentRuntime(
                            InvalidTracedProvider(malformed),
                            "synthetic prompt",
                            project,
                        )
                        with self.assertRaises(ModelResponseMalformedError) as caught:
                            runtime.ask_model("prompt", TraceContext.new_request())
                    self.assertEqual(
                        "MODEL_RESPONSE_MALFORMED",
                        caught.exception.reason_code,
                    )

    def test_urlerror_wrapped_timeout_is_not_network_failure(self) -> None:
        wrapped = URLError(socket.timeout("synthetic timeout"))
        self.assertEqual("MODEL_TIMEOUT", provider_reason_code(wrapped))

    def test_recovery_controller_success_does_not_flatten_task_truth(self) -> None:
        trace = TraceContext.new_request()
        result = RecoveryOperationResult(
            task_id=trace.task_id,
            recovery_attempt_id="recovery_attempt_" + "1" * 32,
            request_id=trace.request_id,
            trace_id=trace.trace_id,
            classification=RecoveryClassification.BLOCKED,
            directive=RecoveryDirective.NO_ACTION,
            status=RecoveryOperationStatus.COMPLETED,
            success=True,
            task_state="BLOCKED",
            task_phase="TERMINAL",
            checkpoint_version=1,
            checkpoint_hash="a" * 64,
        )
        self.assertTrue(result.success)
        self.assertEqual("BLOCKED", result.outcome.status.value)
        self.assertEqual("BLOCKED", result.to_dict()["outcome"]["status"])

    def test_exception_adapter_preserves_typed_reason_without_raw_message(self) -> None:
        class TypedFailure(RuntimeError):
            def __init__(self, reason_code: str) -> None:
                super().__init__("SENSITIVE_INTERNAL_DETAIL")
                self.reason_code = reason_code

        cases = {
            "STATE_LOCK_TIMEOUT": "TIMEOUT",
            "TASK_CHECKPOINT_CORRUPT": "MANUAL_REVIEW_REQUIRED",
            "UNSUPPORTED_SCHEMA": "MANUAL_REVIEW_REQUIRED",
            "RECOVERY_IN_PROGRESS": "MANUAL_REVIEW_REQUIRED",
            "IDEMPOTENCY_IN_PROGRESS": "MANUAL_REVIEW_REQUIRED",
            "RECOVERY_GENERATION_FENCED": "CONFLICT",
            "ACTION_UNKNOWN_OUTCOME": "UNKNOWN_OUTCOME",
            "TASK_BUDGET_EXHAUSTED": "PARTIAL",
            "MODEL_PROVIDER_ERROR": "FAILED",
        }
        for reason, expected in cases.items():
            with self.subTest(reason=reason):
                outcome = outcome_from_exception(TypedFailure(reason))
                self.assertEqual(expected, outcome.status.value)
                self.assertEqual(reason, outcome.reason_code)
                self.assertNotIn("SENSITIVE_INTERNAL_DETAIL", json.dumps(outcome.to_dict()))

    def test_executor_projects_policy_and_approval_truth(self) -> None:
        from tools.executor import ExecutionEngine

        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home")}):
                engine = ExecutionEngine(project, MemoryStore(project, project))
                blocked = engine.execute({"action": "model_invented_tool"})
                with patch("builtins.input", return_value="n"):
                    denied = engine.execute(
                        {
                            "action": "create_folder",
                            "path": str(project / "not-created"),
                            "reason": "synthetic approval test",
                        }
                    )
        self.assertEqual("BLOCKED", blocked["outcome"]["status"])
        self.assertFalse(blocked["success"])
        self.assertEqual("CANCELLED", denied["outcome"]["status"])
        self.assertEqual("HUMAN_APPROVAL_DECLINED", denied["outcome"]["reason_code"])

    def test_real_hard_timeout_is_timeout_then_replay_is_unknown(self) -> None:
        from tools.executor import ExecutionEngine, ToolSpec

        calls = 0

        def timed_handler(_action: dict[str, object]) -> dict[str, object]:
            nonlocal calls
            calls += 1
            try:
                run_bounded_subprocess(
                    [sys.executable, "-c", "import time; time.sleep(2)"],
                    env=build_subprocess_env(),
                    timeout=0.1,
                    resource_profile=SubprocessResourceProfileName.CONTROLLED_TEST,
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=False,
                )
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "timed_out": True,
                    "result_reason_code": SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
                }
            raise AssertionError("synthetic child unexpectedly completed")

        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home")}):
                engine = ExecutionEngine(project, MemoryStore(project, project))
                engine.tools["respond"] = ToolSpec(
                    "respond",
                    timed_handler,
                    "Synthetic bounded timeout handler.",
                )
                operation = OperationContext.new_operation()
                action = {"action": "respond", "message": "synthetic"}
                first = engine.execute(action, operation_context=operation)
                replay = engine.execute(action, operation_context=operation)
        self.assertEqual(1, calls)
        self.assertEqual("TIMEOUT", first["outcome"]["status"])
        self.assertEqual(
            SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
            first["outcome"]["reason_code"],
        )
        self.assertEqual("UNKNOWN_OUTCOME", replay["outcome"]["status"])
        self.assertFalse(replay["dispatched"])

    def test_main_success_malformed_degraded_and_hint_reset(self) -> None:
        import main

        responses = [
            "{}",
            '{"action":"respond","message":"fallback completed"}',
        ]
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home")}):
                runtime = main.AgentRuntime(
                    SequenceProvider(responses),
                    "synthetic prompt",
                    project,
                    max_steps=2,
                )
                degraded = runtime.run_text_request("synthetic model request")
                ordinary = runtime.run_text_request("/status")
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home-explicit")}):
                explicit_empty_runtime = main.AgentRuntime(
                    SequenceProvider(
                        [
                            '{"plan":[]}',
                            '{"action":"respond","message":"explicit empty plan is valid"}',
                        ]
                    ),
                    "synthetic prompt",
                    project,
                    max_steps=2,
                )
                explicit_empty = explicit_empty_runtime.run_text_request(
                    "synthetic explicit empty plan"
                )
        self.assertEqual("DEGRADED", degraded["outcome"]["status"])
        self.assertEqual(
            "MODEL_RESPONSE_MALFORMED",
            degraded["outcome"]["reason_code"],
        )
        self.assertEqual("SUCCESS", ordinary["outcome"]["status"])
        self.assertEqual("SUCCESS", explicit_empty["outcome"]["status"])

    def test_main_step_budget_and_early_terminal_are_truthful(self) -> None:
        import main

        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            fixture = project / "fixture.txt"
            fixture.write_text("read only", encoding="utf-8")
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home-a")}):
                exhausted_runtime = main.AgentRuntime(
                    SequenceProvider(
                        [
                            json.dumps(
                                {
                                    "plan": [
                                        {
                                            "action": "read_file",
                                            "path": str(fixture),
                                        }
                                    ]
                                }
                            )
                        ]
                    ),
                    "synthetic prompt",
                    project,
                    max_steps=1,
                )
                exhausted = exhausted_runtime.run_text_request("read one file")
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home-b")}):
                early_runtime = main.AgentRuntime(
                    SequenceProvider(
                        [
                            json.dumps(
                                {
                                    "plan": [
                                        {"action": "respond", "message": "done"},
                                        {"action": "read_file", "path": str(fixture)},
                                    ]
                                }
                            )
                        ]
                    ),
                    "synthetic prompt",
                    project,
                    max_steps=1,
                )
                early = early_runtime.run_text_request("respond early")
        self.assertEqual("PARTIAL", exhausted["outcome"]["status"])
        self.assertEqual(
            "STEP_BUDGET_EXHAUSTED",
            exhausted["outcome"]["reason_code"],
        )
        self.assertEqual("SUCCESS", early["outcome"]["status"])

    def test_orchestrator_empty_plan_cannot_finish_as_success(self) -> None:
        import main

        parser = object.__new__(GeminiGemmaOrchestrator)
        parser.max_steps = 4
        with self.assertRaises(ModelResponseMalformedError):
            parser._parse_plan('{"steps":[]}')

        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home")}):
                runtime = main.AgentRuntime(
                    EmptyOrchestratorPlanProvider(),
                    "synthetic prompt",
                    project,
                )
                runtime.use_orchestrator = True
                with (
                    patch.object(runtime, "handle_external_review_route", return_value=False),
                    patch.object(runtime, "handle_local_route", return_value=False),
                    patch.object(runtime, "handle_knowledge_route", return_value=False),
                ):
                    result = runtime.run_text_request("synthetic orchestrated request")
        self.assertEqual("FAILED", result["outcome"]["status"])
        self.assertEqual(
            "MODEL_RESPONSE_MALFORMED",
            result["outcome"]["reason_code"],
        )

    def test_browser_degraded_hint_reaches_run_text_request(self) -> None:
        import main

        fallback = {
            "success": False,
            "degraded": True,
            "browser_mode": "fallback",
            "result_reason_code": "BROWSER_FALLBACK_UNVERIFIED",
            "outcome": NZOutcome.build(
                "DEGRADED",
                "BROWSER_FALLBACK_UNVERIFIED",
                degraded=True,
            ).to_dict(),
        }
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            with patch.dict(os.environ, {"AOIA_HOME": str(root / "aoia-home")}):
                runtime = main.AgentRuntime(
                    SequenceProvider([]),
                    "synthetic prompt",
                    project,
                )

                def command_side_effect(*_args, **_kwargs):
                    runtime.print_result(fallback)
                    return CommandResult(True, "")

                with patch.object(
                    runtime.command_registry,
                    "execute",
                    side_effect=command_side_effect,
                ):
                    result = runtime.run_text_request("/synthetic-browser")
        self.assertEqual("DEGRADED", result["outcome"]["status"])
        self.assertFalse(result["outcome"]["status"] == "SUCCESS")


if __name__ == "__main__":
    unittest.main()
