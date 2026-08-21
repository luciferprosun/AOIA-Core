from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

from runtime.sensitive_redaction import (
    REDACTION_MARKER,
    SensitiveValueRedactor,
    build_runtime_redactor,
)


STDOUT_SECRET = "NZ_OVERNIGHT_SECRET_001"
PRIVATE_TOKEN = "NZ_OVERNIGHT_SECRET_002"


def _run_isolated(script: str) -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    python_path = [str(repo_root / "runtime"), str(repo_root)]
    if environment.get("PYTHONPATH"):
        python_path.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=repo_root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "isolated redaction integration failed:\n"
            + completed.stdout
            + completed.stderr
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


class SensitiveValueRedactorTests(unittest.TestCase):
    def test_registered_values_are_removed_exactly_without_leaking_length(self) -> None:
        redactor = SensitiveValueRedactor((STDOUT_SECRET, PRIVATE_TOKEN))
        rendered = redactor.redact_text(
            f"stdout={STDOUT_SECRET}; stderr={PRIVATE_TOKEN}; again={STDOUT_SECRET}"
        )

        self.assertNotIn(STDOUT_SECRET, rendered)
        self.assertNotIn(PRIVATE_TOKEN, rendered)
        self.assertEqual(3, rendered.count(REDACTION_MARKER))
        self.assertNotIn(str(len(STDOUT_SECRET)), rendered)
        self.assertNotIn(STDOUT_SECRET, repr(redactor))

    def test_empty_and_short_values_are_not_registered(self) -> None:
        redactor = SensitiveValueRedactor(("", "a", "safe"))

        self.assertEqual("a safe normal", redactor.redact_text("a safe normal"))

    def test_registration_is_immutable_and_runtime_local(self) -> None:
        original = SensitiveValueRedactor((STDOUT_SECRET,))
        extended = original.registering(PRIVATE_TOKEN)

        self.assertIn(PRIVATE_TOKEN, original.redact_text(PRIVATE_TOKEN))
        self.assertEqual(REDACTION_MARKER, extended.redact_text(PRIVATE_TOKEN))
        combined = original.combining(SensitiveValueRedactor((PRIVATE_TOKEN,)))
        self.assertEqual(REDACTION_MARKER, combined.redact_text(PRIVATE_TOKEN))
        with self.assertRaises(AttributeError):
            original._known_values = ()  # type: ignore[misc]

    def test_environment_lifecycle_reads_only_named_values(self) -> None:
        environ = {
            "OPENAI_API_KEY": STDOUT_SECRET,
            "SOME_PRIVATE_TOKEN": PRIVATE_TOKEN,
            "UNRELATED": "NZ_DO_NOT_REGISTER_003",
        }
        redactor = SensitiveValueRedactor.from_environment(
            environ,
            names=("OPENAI_API_KEY", "SOME_PRIVATE_TOKEN"),
        )

        rendered = redactor.redact_text(" ".join(environ.values()))
        self.assertNotIn(STDOUT_SECRET, rendered)
        self.assertNotIn(PRIVATE_TOKEN, rendered)
        self.assertIn("NZ_DO_NOT_REGISTER_003", rendered)
        self.assertEqual(
            environ,
            {
                "OPENAI_API_KEY": STDOUT_SECRET,
                "SOME_PRIVATE_TOKEN": PRIVATE_TOKEN,
                "UNRELATED": "NZ_DO_NOT_REGISTER_003",
            },
        )

    def test_structured_sensitive_fields_and_nested_values_are_redacted(self) -> None:
        redactor = SensitiveValueRedactor((STDOUT_SECRET, PRIVATE_TOKEN))
        payload = {
            "request_id": "req_visible",
            "trace_id": "trace_visible",
            "exit_code": 0,
            "max_tokens": 0,
            "api_key": "even-short",
            "accessToken": "even-short-too",
            "clientSecret": "client-secret-value",
            "privateKey": "private-key-value",
            "nested": {
                "some_private_token": PRIVATE_TOKEN,
                "stdout": f"value={STDOUT_SECRET}",
            },
        }

        redacted = redactor.redact(payload)
        rendered = json.dumps(redacted, sort_keys=True)
        self.assertNotIn(STDOUT_SECRET, rendered)
        self.assertNotIn(PRIVATE_TOKEN, rendered)
        self.assertEqual("req_visible", redacted["request_id"])
        self.assertEqual("trace_visible", redacted["trace_id"])
        self.assertEqual(0, redacted["exit_code"])
        self.assertEqual(0, redacted["max_tokens"])
        self.assertEqual(REDACTION_MARKER, redacted["api_key"])
        self.assertEqual(REDACTION_MARKER, redacted["accessToken"])
        self.assertEqual(REDACTION_MARKER, redacted["clientSecret"])
        self.assertEqual(REDACTION_MARKER, redacted["privateKey"])
        self.assertEqual(REDACTION_MARKER, redacted["nested"]["some_private_token"])

    def test_structured_redaction_is_bounded_and_fails_closed(self) -> None:
        redactor = SensitiveValueRedactor(
            (STDOUT_SECRET,),
            max_depth=2,
            max_items=2,
        )

        redacted = redactor.redact(
            {
                "first": {"deeper": {"secret_value": STDOUT_SECRET}},
                "second": ["safe", STDOUT_SECRET, "omitted"],
                "third": STDOUT_SECRET,
            }
        )
        rendered = json.dumps(redacted, sort_keys=True)
        self.assertNotIn(STDOUT_SECRET, rendered)
        self.assertEqual(REDACTION_MARKER, redacted["first"]["deeper"])
        self.assertEqual(REDACTION_MARKER, redacted["second"][1])
        self.assertEqual(REDACTION_MARKER, redacted["redaction_limit"])

    def test_cycles_and_non_json_mapping_keys_fail_closed(self) -> None:
        redactor = SensitiveValueRedactor((STDOUT_SECRET,), max_depth=3)
        cyclic: dict[object, object] = {}
        cyclic[("unsafe", "key")] = STDOUT_SECRET
        cyclic["cycle"] = cyclic

        redacted = redactor.redact(cyclic)
        rendered = json.dumps(redacted, sort_keys=True)
        self.assertNotIn(STDOUT_SECRET, rendered)
        self.assertIn(REDACTION_MARKER, rendered)
        self.assertEqual(REDACTION_MARKER, redacted["cycle"]["cycle"]["cycle"])
        self.assertEqual([REDACTION_MARKER], redactor.redact({STDOUT_SECRET}))

    def test_build_runtime_redactor_registers_known_provider_environment(self) -> None:
        redactor = build_runtime_redactor(
            environ={
                "OPENAI_API_KEY": STDOUT_SECRET,
                "SOME_PRIVATE_TOKEN": PRIVATE_TOKEN,
            },
        )

        self.assertEqual(
            f"{REDACTION_MARKER}/{REDACTION_MARKER}",
            redactor.redact_text(f"{STDOUT_SECRET}/{PRIVATE_TOKEN}"),
        )


class SensitiveOutputIntegrationTests(unittest.TestCase):
    def test_executor_model_console_worker_and_artifacts_are_secret_free(self) -> None:
        payload = _run_isolated(
            r'''
            import io
            import json
            import os
            import tempfile
            import types
            from contextlib import redirect_stdout
            from pathlib import Path

            from runtime.main import AgentRuntime
            from runtime.memory.gemma_worker_memory import GemmaWorkerMemory
            from runtime.orchestrator.gemini_gemma import GeminiGemmaOrchestrator
            from runtime.outcomes import NZOutcome, NZOutcomeStatus
            from runtime.sensitive_redaction import build_current_runtime_redactor
            from runtime.tools.executor import ExecutionEngine, ToolSpec
            from runtime.tools.idempotency import (
                OperationContext,
                build_safe_result_receipt,
            )
            from runtime.tools.memory import MemoryStore
            from runtime.tools.provenance import verify_provenance_chain
            from runtime.trace_context import TraceContext

            secret_one = "NZ_OVERNIGHT_SECRET_001"
            secret_two = "NZ_OVERNIGHT_SECRET_002"

            class ProviderManager:
                def __init__(self):
                    self.output_redactor = build_current_runtime_redactor(environ=os.environ)
                def describe(self):
                    return "synthetic/no-call"
                def active_fallback_chain(self):
                    return ["synthetic/no-call"]
                def provider_status(self):
                    return []

            class Hats:
                def prompt_block(self):
                    return {"name": "synthetic"}

            class WorkerProvider:
                full_name = "synthetic/gemma"
                def __init__(self):
                    self.prompts = []
                def generate(self, prompt):
                    self.prompts.append(prompt)
                    return json.dumps({
                        "action": "respond",
                        "message": "worker=" + secret_one,
                        "reason": "token=" + secret_two,
                    })

            with tempfile.TemporaryDirectory() as raw_root:
                root = Path(raw_root)
                project = root / "project"
                project.mkdir()
                os.environ["AOIA_HOME"] = str(root / "aoia-home")
                os.environ["OPENAI_API_KEY"] = secret_one
                os.environ["SOME_PRIVATE_TOKEN"] = secret_two
                os.environ.pop("EPISTEMIC_DISABLE_REASONING_TRACE", None)

                memory = MemoryStore(
                    project,
                    project,
                    initialize_vault=False,
                    persist_on_init=False,
                    record_session_start=False,
                )
                engine = ExecutionEngine(project, memory)
                raw_handler_result = {
                    "success": True,
                    "message": "message=" + secret_one,
                    "stdout": "stdout=" + secret_one,
                    "stderr": "stderr=" + secret_two,
                    "stdout_truncated": True,
                    "stderr_truncated": False,
                    "exit_code": 0,
                    "stop_loop": True,
                }
                engine.tools["respond"] = ToolSpec(
                    "respond",
                    lambda _action: dict(raw_handler_result),
                    "synthetic redaction handler",
                )
                captured_raw_correlated = {}
                correlate_result = engine._correlate_result

                def capture_raw_correlated(result, context):
                    correlated = correlate_result(result, context)
                    captured_raw_correlated.update(correlated)
                    return correlated

                engine._correlate_result = capture_raw_correlated
                operation = OperationContext.new_operation()
                action_context = TraceContext.new_request().new_action()
                executor_result = engine.execute(
                    {"action": "respond", "message": "safe"},
                    require_approval=False,
                    action_context=action_context,
                    operation_context=operation,
                )
                executor_rendered = json.dumps(executor_result, sort_keys=True)
                assert secret_one not in executor_rendered
                assert secret_two not in executor_rendered
                assert executor_result["stdout_truncated"] is True
                assert executor_result["stderr_truncated"] is False
                assert executor_result["exit_code"] == 0
                for field, prefix in (
                    ("request_id", "request_"),
                    ("trace_id", "trace_"),
                    ("task_id", "task_"),
                    ("action_id", "action_"),
                ):
                    assert executor_result[field].startswith(prefix)
                record = engine.idempotency_store.load(operation)
                assert record is not None
                receipt = dict(record.terminal_receipt or {})
                receipt_text = json.dumps(receipt, sort_keys=True)
                assert secret_one not in receipt_text
                assert secret_two not in receipt_text
                assert secret_one in json.dumps(captured_raw_correlated)
                assert secret_two in json.dumps(captured_raw_correlated)
                assert receipt["result_hash"] == build_safe_result_receipt(
                    captured_raw_correlated
                )["result_hash"]
                assert verify_provenance_chain(
                    engine.provenance_store.runtime_log_path
                ).ok

                runtime = AgentRuntime(
                    ProviderManager(),
                    "system prompt",
                    project,
                    max_steps=1,
                )
                trace = TraceContext.new_request()
                runtime.memory_store.set_current_task(
                    "task=" + secret_one + "/" + secret_two
                )
                runtime.memory_store.append_history(
                    "synthetic",
                    {"stdout": secret_one, "stderr": secret_two},
                )
                runtime.log_session_event(
                    "synthetic",
                    {"provider_error": secret_one, "token": secret_two},
                    trace_context=trace,
                )
                runtime.log_reasoning_trace(
                    "synthetic",
                    {"model_feedback": secret_one, "nested": {"password": secret_two}},
                    trace_context=trace,
                )
                runtime.log_error(
                    {"error": "failure=" + secret_one, "traceback": secret_two},
                    trace_context=trace,
                )
                model_projection = runtime.result_for_model(
                    {
                        "stdout": secret_one + ("x" * 3000),
                        "stderr": secret_two,
                        "stdout_truncated": True,
                        "exit_code": 0,
                    }
                )
                model_rendered = json.dumps(model_projection, sort_keys=True)
                assert secret_one not in model_rendered
                assert secret_two not in model_rendered
                assert "...[truncated]..." in model_projection["stdout"]
                assert model_projection["stdout_truncated"] is True
                assert model_projection["exit_code"] == 0

                console = io.StringIO()
                with redirect_stdout(console):
                    runtime.print_result(
                        {
                            "success": False,
                            "message": secret_one,
                            "stdout": secret_one,
                            "stderr": secret_two,
                        }
                    )
                assert secret_one not in console.getvalue()
                assert secret_two not in console.getvalue()

                model_prompt = runtime.build_model_request(
                    "request=" + secret_one,
                    [{"result": secret_two}],
                )
                assert secret_one not in model_prompt
                assert secret_two not in model_prompt

                def fake_dispatch(self, _user_input, current_trace, *, ingress):
                    print("transcript=" + secret_one + "/" + secret_two)
                    return NZOutcome.build(
                        NZOutcomeStatus.SUCCESS,
                        request_id=current_trace.request_id,
                        trace_id=current_trace.trace_id,
                        task_id=current_trace.task_id,
                    )

                runtime.dispatch_text_request = types.MethodType(fake_dispatch, runtime)
                response = runtime.run_text_request(secret_one, trace)
                response_rendered = json.dumps(response, sort_keys=True)
                assert secret_one not in response_rendered
                assert secret_two not in response_rendered
                assert response["request_id"] == trace.request_id
                assert response["trace_id"] == trace.trace_id
                assert response["task_id"] == trace.task_id

                worker_memory = GemmaWorkerMemory(
                    project,
                    redactor=runtime.redactor,
                )
                worker = WorkerProvider()
                orchestrator = GeminiGemmaOrchestrator(
                    ProviderManager(),
                    worker_memory,
                    Hats(),
                    project,
                    project,
                    redactor=runtime.redactor,
                )
                orchestrator.gemma_provider = worker
                worker_action = orchestrator.action_for_step(
                    "request=" + secret_one,
                    "step=" + secret_two,
                    runtime.snapshot_status(),
                    [],
                )
                orchestrator.record_result(
                    "step=" + secret_one,
                    worker_action,
                    {"stderr": secret_two},
                )
                worker_rendered = json.dumps(
                    worker_memory.summarize_worker_state(),
                    sort_keys=True,
                )
                assert secret_one not in worker_rendered
                assert secret_two not in worker_rendered
                assert secret_one not in worker.prompts[0]
                assert secret_two not in worker.prompts[0]

                snapshot_path = runtime.save_page_text_snapshot(
                    "https://user:" + secret_one + "@" + secret_two + ".example/page",
                    {"text": "snapshot=" + secret_one + "/" + secret_two},
                )
                assert snapshot_path is not None
                assert secret_one not in str(snapshot_path.relative_to(root))
                assert secret_two not in str(snapshot_path.relative_to(root))

                artifacts = []
                artifact_names = []
                for path in sorted(root.rglob("*")):
                    if path.is_file():
                        artifact_names.append(str(path.relative_to(root)))
                        artifacts.append(
                            path.read_bytes().decode("utf-8", errors="replace")
                        )
                artifact_text = "\n".join(artifacts)
                artifact_name_text = "\n".join(artifact_names)
                assert secret_one not in artifact_text
                assert secret_two not in artifact_text
                assert secret_one not in artifact_name_text
                assert secret_two not in artifact_name_text
                assert "[REDACTED]" in artifact_text

                print(json.dumps({
                    "executor": True,
                    "model_feedback": True,
                    "console": True,
                    "worker": True,
                    "artifacts": True,
                    "provenance": True,
                    "ids": True,
                }))
            '''
        )
        self.assertTrue(all(payload.values()))

    def test_provider_file_lifecycle_cli_and_error_surfaces_are_secret_free(self) -> None:
        payload = _run_isolated(
            r'''
            import io
            import json
            import os
            import tempfile
            from contextlib import redirect_stdout
            from pathlib import Path
            from unittest.mock import patch

            from runtime.main import AgentRuntime
            from runtime.model_router import execute_approved_model_call_once
            from runtime.provider_clients import ProviderCallResult
            from runtime.providers import cli as provider_cli
            from runtime.providers import config as provider_config
            from runtime.providers import gateway as provider_gateway
            from runtime.providers.contracts import ProviderActivationStatus
            from runtime.providers.payloads import build_provider_envelope

            secret_one = "NZ_OVERNIGHT_SECRET_001"
            secret_two = "NZ_OVERNIGHT_SECRET_002"

            with tempfile.TemporaryDirectory() as raw_root:
                root = Path(raw_root)
                project = root / "project"
                project.mkdir()
                secret_file = root / "provider.env"
                secret_file.write_text(
                    "OPENAI_API_KEY=" + secret_one + "\n"
                    "SOME_PRIVATE_TOKEN=" + secret_two + "\n",
                    encoding="utf-8",
                )
                os.environ["AOIA_HOME"] = str(root / "aoia-home")
                os.environ.pop("OPENAI_API_KEY", None)
                os.environ.pop("SOME_PRIVATE_TOKEN", None)
                provider_config.API_FILE_CANDIDATES = [secret_file]

                manager = provider_config.ProviderManager(project)
                assert "OPENAI_API_KEY" not in os.environ
                assert "SOME_PRIVATE_TOKEN" not in os.environ
                assert secret_one not in manager.output_redactor.redact_text(secret_one)
                assert secret_two not in manager.output_redactor.redact_text(secret_two)

                runtime = AgentRuntime(
                    manager,
                    "system prompt",
                    project,
                    max_steps=1,
                )
                runtime.memory_store.set_current_task(
                    "before-provider=" + secret_one + "/" + secret_two
                )
                state_text = "\n".join(
                    path.read_bytes().decode("utf-8", errors="replace")
                    for path in sorted((root / "aoia-home").rglob("*"))
                    if path.is_file()
                )
                assert secret_one not in state_text
                assert secret_two not in state_text

                os.environ["OPENAI_API_KEY"] = secret_one
                os.environ["SOME_PRIVATE_TOKEN"] = secret_two
                output = io.StringIO()
                with redirect_stdout(output):
                    code = provider_cli.main([
                        "--provider", "mock_chat",
                        "--model", "mock-model",
                        "--prompt", secret_one + "/" + secret_two,
                        "--max-tokens", "32",
                    ])
                cli_text = output.getvalue()
                assert code == 0
                assert secret_one not in cli_text
                assert secret_two not in cli_text
                assert "[REDACTED]" in cli_text

                output = io.StringIO()
                with patch.object(
                    provider_cli,
                    "run_selected_provider",
                    side_effect=ValueError("provider-error=" + secret_one + "/" + secret_two),
                ), redirect_stdout(output):
                    code = provider_cli.main([
                        "--provider", "mock_chat",
                        "--model", "mock-model",
                        "--prompt", "safe",
                    ])
                error_text = output.getvalue()
                assert code == 2
                assert secret_one not in error_text
                assert secret_two not in error_text
                assert json.loads(error_text)["status"] == "invalid"

                mock_envelope = build_provider_envelope(
                    provider_id="mock_chat",
                    model_id="mock-model",
                    prompt="dry-run=" + secret_one + "/" + secret_two,
                    params={"max_tokens": 32},
                    created_at="synthetic-p013",
                )
                mock_result = provider_gateway.run_provider_request(mock_envelope)
                mock_rendered = json.dumps(mock_result.to_dict(), sort_keys=True)
                assert secret_one not in mock_rendered
                assert secret_two not in mock_rendered
                assert "[REDACTED]" in mock_result.redacted_request_preview

                # A file-only gateway key is learned after the envelope was
                # constructed.  It must be removed from both the actual model
                # payload and the result preview once the gateway reads it.
                os.environ.pop("OPENAI_API_KEY", None)
                os.environ.pop("KIMI_API_KEY", None)
                os.environ.pop("MOONSHOT_API_KEY", None)
                os.environ["SOME_PRIVATE_TOKEN"] = secret_two
                gateway_key_file = root / "kimi.key"
                gateway_key_file.write_text(secret_one, encoding="utf-8")
                os.environ["KIMI_API_KEY_FILE"] = str(gateway_key_file)
                envelope = build_provider_envelope(
                    provider_id="kimi_chat",
                    model_id="moonshot-v1-8k",
                    prompt="gateway-prompt=" + secret_one + "/" + secret_two,
                    params={"max_tokens": 32},
                    dry_run=False,
                    created_at="synthetic-p013",
                )
                assert secret_one in envelope.payload_preview
                captured_request = {}

                class FakeResponse:
                    def __enter__(self):
                        return self
                    def __exit__(self, *_args):
                        return False
                    def read(self):
                        return json.dumps({
                            "choices": [{"message": {"content": "safe response"}}]
                        }).encode("utf-8")

                def fake_urlopen(request, *, timeout):
                    captured_request["body"] = request.data.decode("utf-8")
                    captured_request["timeout"] = timeout
                    return FakeResponse()

                with patch.object(
                    provider_gateway,
                    "urlopen",
                    side_effect=fake_urlopen,
                ):
                    gateway_result = provider_gateway.run_provider_request(
                        envelope,
                        live=True,
                        acknowledge_live_provider_test=True,
                        activation_status=(
                            ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST
                        ),
                    )
                gateway_rendered = json.dumps(
                    gateway_result.to_dict(),
                    sort_keys=True,
                )
                assert gateway_result.status == "live_success"
                assert secret_one not in captured_request["body"]
                assert secret_two not in captured_request["body"]
                assert "[REDACTED]" in captured_request["body"]
                assert secret_one not in gateway_rendered
                assert secret_two not in gateway_rendered
                assert "[REDACTED]" in gateway_result.redacted_request_preview

                os.environ["GEMINI_API_KEY"] = secret_two
                gemini_envelope = build_provider_envelope(
                    provider_id="gemini_chat",
                    model_id=secret_two,
                    prompt="gemini-prompt=" + secret_two,
                    params={"max_tokens": 32},
                    dry_run=False,
                    created_at="synthetic-p013",
                )
                captured_gemini = {}

                class FakeGeminiResponse:
                    def __enter__(self):
                        return self
                    def __exit__(self, *_args):
                        return False
                    def read(self):
                        return json.dumps({
                            "candidates": [{
                                "content": {"parts": [{"text": "safe response"}]}
                            }]
                        }).encode("utf-8")

                def fake_gemini_urlopen(request, *, timeout):
                    captured_gemini["url"] = request.full_url
                    captured_gemini["body"] = request.data.decode("utf-8")
                    return FakeGeminiResponse()

                with patch.object(
                    provider_gateway,
                    "urlopen",
                    side_effect=fake_gemini_urlopen,
                ):
                    gemini_result = provider_gateway.run_provider_request(
                        gemini_envelope,
                        live=True,
                        acknowledge_live_provider_test=True,
                        activation_status=(
                            ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST
                        ),
                    )
                gemini_rendered = json.dumps(gemini_result.to_dict(), sort_keys=True)
                assert gemini_result.status == "live_success"
                assert secret_two not in captured_gemini["url"]
                assert secret_two not in captured_gemini["body"]
                assert secret_two not in gemini_rendered
                assert gemini_result.model_id == "[REDACTED]"

                os.environ["OPENAI_API_KEY"] = secret_one
                os.environ["SOME_PRIVATE_TOKEN"] = secret_two
                routed_calls = []

                def fake_provider_call(**kwargs):
                    routed_calls.append(kwargs)
                    return ProviderCallResult(
                        provider_id=kwargs["provider_id"],
                        model_id=kwargs["model_id"],
                        call_made=True,
                        output_text="provider-output=" + secret_one + "/" + secret_two,
                    )

                routed_result = execute_approved_model_call_once(
                    provider_id="gemini",
                    model_id="gemini/gemini-2.5-flash",
                    task_sensitivity="PUBLIC_DEV",
                    user_prompt="provider-input=" + secret_one + "/" + secret_two,
                    human_approved=True,
                    provider_call_func=fake_provider_call,
                )
                assert len(routed_calls) == 1
                assert secret_one not in routed_calls[0]["user_prompt"]
                assert secret_two not in routed_calls[0]["user_prompt"]
                assert "[REDACTED]" in routed_calls[0]["user_prompt"]
                routed_rendered = json.dumps(routed_result, sort_keys=True)
                assert secret_one not in routed_rendered
                assert secret_two not in routed_rendered
                assert "[REDACTED]" in routed_result["output_text"]

                registered_model_id = "gemini/gemini-2.5-flash"
                os.environ["XAI_API_KEY"] = registered_model_id
                model_id_calls = []

                def model_id_provider_call(**kwargs):
                    model_id_calls.append(kwargs)
                    return ProviderCallResult(
                        provider_id=kwargs["provider_id"],
                        model_id=kwargs["model_id"],
                        call_made=True,
                        output_text="safe",
                    )

                model_id_result = execute_approved_model_call_once(
                    provider_id="gemini",
                    model_id=registered_model_id,
                    task_sensitivity="PUBLIC_DEV",
                    user_prompt="safe approved input",
                    human_approved=True,
                    provider_call_func=model_id_provider_call,
                )
                assert len(model_id_calls) == 1
                assert model_id_calls[0]["model_id"] == "[REDACTED]"
                assert registered_model_id not in json.dumps(
                    model_id_result,
                    sort_keys=True,
                )

                blocked_result = execute_approved_model_call_once(
                    provider_id="gemini",
                    model_id=secret_one,
                    task_sensitivity="PUBLIC_DEV",
                    user_prompt="safe blocked input",
                    human_approved=True,
                    provider_call_func=fake_provider_call,
                )
                blocked_rendered = json.dumps(blocked_result, sort_keys=True)
                assert blocked_result["call_made"] is False
                assert secret_one not in blocked_rendered
                assert blocked_result["proposal"]["proposal_id"].startswith("proposal-")

                print(json.dumps({
                    "pre_provider": True,
                    "env_unmodified": True,
                    "cli": True,
                    "provider_error": True,
                    "gateway_wire": True,
                    "gateway_model_id": True,
                    "model_router": True,
                }))
            '''
        )
        self.assertTrue(all(payload.values()))

    def test_http_success_error_and_late_secret_refresh_are_safe(self) -> None:
        payload = _run_isolated(
            r'''
            import json
            import os
            from http import HTTPStatus
            from io import BytesIO
            from types import SimpleNamespace

            from runtime import webapp
            from runtime.sensitive_redaction import SensitiveValueRedactor
            from runtime.trace_context import TraceContext

            secret_one = "NZ_OVERNIGHT_SECRET_001"
            secret_two = "NZ_OVERNIGHT_SECRET_002"
            operator_token = "NZ_P013_SYNTHETIC_OPERATOR_TOKEN_001"
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("SOME_PRIVATE_TOKEN", None)
            config = webapp.WebBoundaryConfig(
                operator_token=operator_token,
                allowed_origins=frozenset({"http://127.0.0.1:4311"}),
            )
            startup_redactor = SensitiveValueRedactor((operator_token,))
            server = SimpleNamespace(
                output_redactor=startup_redactor,
                web_boundary_config=config,
            )

            def write(payload, status=HTTPStatus.OK):
                handler = object.__new__(webapp.CodexStyleHandler)
                handler.server = server
                handler.web_boundary_config = config
                handler.wfile = BytesIO()
                handler.send_response = lambda _status: None
                handler.send_header = lambda *_args: None
                handler.end_headers = lambda: None
                webapp.CodexStyleHandler._write_json(handler, status, payload)
                return handler.wfile.getvalue().decode("utf-8")

            # These values appear only after server construction.  The response
            # boundary must refresh its immutable snapshot for every response.
            os.environ["OPENAI_API_KEY"] = secret_one
            os.environ["SOME_PRIVATE_TOKEN"] = secret_two
            trace = TraceContext.new_request()
            success_text = write({
                "ok": True,
                "stdout": secret_one,
                "nested": {"somePrivateToken": secret_two},
                "operator_echo": operator_token,
                **trace.identity_fields(),
            })
            assert secret_one not in success_text
            assert secret_two not in success_text
            assert operator_token not in success_text
            assert "[REDACTED]" in success_text
            success = json.loads(success_text)
            assert success["request_id"] == trace.request_id
            assert success["trace_id"] == trace.trace_id
            assert success["task_id"] == trace.task_id

            failure = webapp._safe_exception_payload(
                RuntimeError(
                    "Traceback /private/operator/path secret="
                    + secret_one
                    + "/"
                    + secret_two
                ),
                trace,
            )
            failure_text = write(failure, HTTPStatus.INTERNAL_SERVER_ERROR)
            assert secret_one not in failure_text
            assert secret_two not in failure_text
            assert "Traceback" not in failure_text
            assert "/private/operator/path" not in failure_text
            failure_payload = json.loads(failure_text)
            assert failure_payload["request_id"] == trace.request_id
            assert failure_payload["trace_id"] == trace.trace_id
            assert failure_payload["outcome"]["status"] == "FAILED"

            print(json.dumps({
                "http_success": True,
                "http_error": True,
                "late_refresh": True,
                "ids": True,
            }))
            '''
        )
        self.assertTrue(all(payload.values()))


if __name__ == "__main__":
    unittest.main()
