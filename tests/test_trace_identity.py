from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import providers.config as provider_config
import runtime.webapp as webapp
from runtime.safety.bounded_subprocess import (
    SUBPROCESS_HARD_TIMEOUT_REASON_CODE,
    SubprocessResourceProfileName,
    run_bounded_subprocess,
)
from runtime.safety.subprocess_env import build_subprocess_env
from tools.executor import ExecutionEngine, ToolSpec
from tools.memory import MemoryStore
from trace_context import TraceContext, TraceIdentityError


PROMPT_TEMPLATE = "AOIA trace test prompt"


class FakeProviderManager:
    def __init__(self, outputs: list[str | Exception]) -> None:
        self.outputs = list(outputs)
        self.calls = 0

    def generate(self, _prompt: str) -> str:
        output = self.outputs[self.calls]
        self.calls += 1
        if isinstance(output, Exception):
            raise output
        return output

    def describe(self) -> str:
        return "fake/test-model"

    def active_fallback_chain(self) -> list[str]:
        return ["fake/test-model"]

    def provider_status(self) -> list[dict[str, object]]:
        return []

    def available_models(self) -> list[str]:
        return ["fake/test-model"]


class FakeFallbackProvider:
    def __init__(self, full_name: str, output: str | Exception) -> None:
        self.full_name = full_name
        self.output = output

    def generate(self, _prompt: str) -> str:
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


class TraceIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temporary_directory.name)
        self.project_root = self.temp_root / "project"
        self.project_root.mkdir()
        self.environment = patch.dict(
            os.environ,
            {
                "AOIA_HOME": str(self.temp_root / "aoia-state"),
                "AOIA_LEGACY_FILESYSTEM_ENABLED": "1",
            },
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def build_runtime(self, outputs: list[str | Exception]) -> main.AgentRuntime:
        return main.AgentRuntime(
            FakeProviderManager(outputs),
            PROMPT_TEMPLATE,
            self.project_root,
        )

    @staticmethod
    def plan(*actions: dict[str, object]) -> str:
        return json.dumps({"plan": list(actions)})

    def force_model_path(self, runtime: main.AgentRuntime):
        return (
            patch.object(runtime, "handle_external_review_route", return_value=False),
            patch.object(runtime, "handle_local_route", return_value=False),
            patch.object(runtime, "handle_knowledge_route", return_value=False),
        )

    def command_log_payloads(self, memory: MemoryStore) -> list[dict]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(memory.paths.command_logs_dir.glob("*.json"))
        ]

    def test_two_top_level_requests_receive_unique_server_identities(self) -> None:
        runtime = self.build_runtime([])

        first = runtime.run_text_request("/status")
        second = runtime.run_text_request("/status")

        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertNotEqual(first["trace_id"], second["trace_id"])

    def test_one_multiaction_request_keeps_trace_and_assigns_unique_actions(self) -> None:
        first_file = self.project_root / "first.txt"
        first_file.write_text("one\n", encoding="utf-8")
        runtime = self.build_runtime(
            [
                json.dumps({"plan": []}),
                json.dumps({"action": "read_file", "path": "first.txt"}),
                json.dumps({"action": "respond", "message": "trace complete"}),
            ]
        )

        route_patches = self.force_model_path(runtime)
        with route_patches[0], route_patches[1], route_patches[2]:
            response = runtime.run_text_request("read two trace fixtures")

        records = self.command_log_payloads(runtime.memory_store)
        self.assertEqual(2, len(records))
        self.assertEqual(
            {response["request_id"]},
            {record["request_id"] for record in records},
        )
        self.assertEqual(
            {response["trace_id"]},
            {record["trace_id"] for record in records},
        )
        self.assertEqual(2, len({record["action_id"] for record in records}))
        self.assertEqual(2, len({record["model_call_id"] for record in records}))
        session_records = [
            json.loads(line)
            for line in runtime.session_log.read_text(encoding="utf-8").splitlines()
        ]
        started_calls = [
            record
            for record in session_records
            if record["kind"] == "model_call_attempt"
            and record["payload"]["status"] == "started"
        ]
        self.assertEqual(3, len(started_calls))
        self.assertEqual(3, len({record["model_call_id"] for record in started_calls}))
        self.assertEqual(
            {response["trace_id"]},
            {record["trace_id"] for record in started_calls},
        )

    def test_each_actual_provider_fallback_attempt_has_a_unique_model_call_id(self) -> None:
        manager = provider_config.ProviderManager(self.project_root)
        trace_context = TraceContext.new_request()
        observed: list[tuple[str, str, str]] = []
        providers = (
            FakeFallbackProvider("first/model-a", RuntimeError("synthetic failure")),
            FakeFallbackProvider("second/model-b", "synthetic success"),
        )

        with (
            patch.object(manager, "_fallback_candidates", return_value=["first/model-a", "second/model-b"]),
            patch.object(manager, "_build_provider", side_effect=providers),
            patch.object(provider_config, "require_provider_calls_enabled"),
            patch.object(provider_config, "load_api_environment"),
        ):
            result = manager.generate_traced(
                "trace provider attempts",
                trace_context,
                on_attempt=lambda status, call, provider, _model, _attempt: observed.append(
                    (status, call.model_call_id, provider)
                ),
            )

        started_ids = [model_call_id for status, model_call_id, _ in observed if status == "started"]
        self.assertEqual(2, len(started_ids))
        self.assertEqual(2, len(set(started_ids)))
        self.assertEqual(trace_context.request_id, result.model_call.request_id)
        self.assertEqual(trace_context.trace_id, result.model_call.trace_id)
        self.assertEqual(started_ids[-1], result.model_call.model_call_id)

    def test_model_supplied_identity_fields_cannot_spoof_runtime_ids(self) -> None:
        runtime = self.build_runtime(
            [
                self.plan(
                    {
                        "action": "respond",
                        "message": "done",
                        "request_id": "MODEL_CONTROLLED",
                        "trace_id": "MODEL_CONTROLLED",
                        "model_call_id": "MODEL_CONTROLLED",
                        "action_id": "MODEL_CONTROLLED",
                    }
                )
            ]
        )

        route_patches = self.force_model_path(runtime)
        with route_patches[0], route_patches[1], route_patches[2]:
            response = runtime.run_text_request("attempt identity spoof")

        record = self.command_log_payloads(runtime.memory_store)[0]
        self.assertEqual(response["request_id"], record["request_id"])
        self.assertEqual(response["trace_id"], record["trace_id"])
        self.assertNotEqual("MODEL_CONTROLLED", record["action_id"])
        self.assertNotEqual("MODEL_CONTROLLED", record["model_call_id"])
        for field in ("request_id", "trace_id", "model_call_id", "action_id"):
            self.assertNotIn(field, record["action"])

    def test_operational_log_contains_authoritative_execution_correlation(self) -> None:
        target = self.project_root / "readme.txt"
        target.write_text("traceable\n", encoding="utf-8")
        memory = MemoryStore(self.project_root, self.project_root)
        engine = ExecutionEngine(self.project_root, memory)
        trace_context = TraceContext.new_request()
        model_call = trace_context.new_model_call()
        action_context = trace_context.new_action(model_call)

        result = engine.execute(
            {"action": "read_file", "path": "readme.txt"},
            action_context=action_context,
        )

        record = self.command_log_payloads(memory)[0]
        self.assertEqual(action_context.identity_fields(), {
            key: record[key] for key in action_context.identity_fields()
        })
        self.assertEqual(action_context.identity_fields(), {
            key: result[key] for key in action_context.identity_fields()
        })
        self.assertEqual("operational_event", record["authority"]["classification"])
        self.assertEqual("replay_only", record["authority"]["retention"])
        self.assertTrue(record["authority"]["non_authoritative"])
        self.assertFalse(record["authority"]["canonical_evidence"])

    def test_declined_action_is_correlated_without_side_effect_or_execution_log(self) -> None:
        target = self.project_root / "target.txt"
        target.write_text("original\n", encoding="utf-8")
        memory = MemoryStore(self.project_root, self.project_root)
        engine = ExecutionEngine(self.project_root, memory)
        trace_context = TraceContext.new_request()
        model_call = trace_context.new_model_call()
        action_context = trace_context.new_action(model_call)

        def decline(_action, decision, approval_context) -> bool:
            self.assertEqual(action_context, approval_context)
            self.assertEqual(action_context.request_id, decision.request_id)
            self.assertEqual(action_context.trace_id, decision.trace_id)
            self.assertEqual(action_context.action_id, decision.action_id)
            return False

        with patch.object(engine, "_request_approval", side_effect=decline):
            result = engine.execute(
                {
                    "action": "write_file",
                    "path": "target.txt",
                    "content": "changed\n",
                    "requires_confirmation": False,
                },
                action_context=action_context,
            )

        self.assertTrue(result["cancelled"])
        self.assertFalse(result["success"])
        self.assertEqual(action_context.identity_fields(), {
            key: result[key] for key in action_context.identity_fields()
        })
        self.assertEqual("original\n", target.read_text(encoding="utf-8"))
        self.assertEqual([], self.command_log_payloads(memory))

    def test_real_timeout_and_sanitized_child_environment_remain_correlated(self) -> None:
        evidence_path = self.temp_root / "timed-child.json"
        child_code = (
            "import json, os, pathlib, sys, time; "
            "pathlib.Path(sys.argv[1]).write_text(json.dumps({"
            "'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY')}), encoding='utf-8'); "
            "time.sleep(30)"
        )
        memory = MemoryStore(self.project_root, self.project_root)
        engine = ExecutionEngine(self.project_root, memory)
        trace_context = TraceContext.new_request()
        action_context = trace_context.new_action()

        def timed_handler(_action: dict) -> dict:
            try:
                run_bounded_subprocess(
                    [sys.executable, "-c", child_code, str(evidence_path)],
                    env=build_subprocess_env(),
                    timeout=0.25,
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
            raise AssertionError("Synthetic timeout process unexpectedly completed")

        engine.tools["respond"] = ToolSpec(
            "respond",
            timed_handler,
            "P0.5 correlation probe around the P0.4 process boundary.",
        )
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "NZ_TRACE_SECRET_MUST_NOT_INHERIT"},
            clear=False,
        ):
            result = engine.execute(
                {"action": "respond", "message": "timeout probe"},
                action_context=action_context,
            )

        self.assertTrue(result["timed_out"])
        self.assertFalse(result["success"])
        self.assertEqual(SUBPROCESS_HARD_TIMEOUT_REASON_CODE, result["result_reason_code"])
        self.assertEqual(action_context.identity_fields(), {
            key: result[key] for key in action_context.identity_fields()
        })
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertIsNone(evidence["OPENAI_API_KEY"])
        record = self.command_log_payloads(memory)[0]
        self.assertEqual(action_context.action_id, record["action_id"])
        self.assertEqual(trace_context.trace_id, record["trace_id"])

    def test_api_chat_returns_server_generated_request_and_trace_ids(self) -> None:
        runtime = self.build_runtime([])
        service = webapp.WebRuntimeService.__new__(webapp.WebRuntimeService)
        service.runtime = runtime
        service.lock = threading.Lock()

        with patch.object(webapp, "SERVICE", service):
            status, response = webapp.route_post_payload(
                "/api/chat",
                {
                    "prompt": "/status",
                    "request_id": "CLIENT_CONTROLLED",
                    "trace_id": "CLIENT_CONTROLLED",
                },
            )

        self.assertEqual(200, status)
        self.assertTrue(response["ok"])
        self.assertTrue(str(response["task_id"]).startswith("task_"))
        self.assertNotEqual("CLIENT_CONTROLLED", response["request_id"])
        self.assertNotEqual("CLIENT_CONTROLLED", response["trace_id"])
        self.assertTrue(str(response["request_id"]).startswith("request_"))
        self.assertTrue(str(response["trace_id"]).startswith("trace_"))

    def test_operational_record_invariant_rejects_missing_identity(self) -> None:
        memory = MemoryStore(self.project_root, self.project_root)
        engine = ExecutionEngine(self.project_root, memory)
        action_context = TraceContext.new_request().new_action()

        with self.assertRaises(TraceIdentityError):
            engine._record_execution(
                {"action": "respond", "message": "invalid"},
                {"success": True},
                action_context,
            )

        self.assertEqual([], self.command_log_payloads(memory))


if __name__ == "__main__":
    unittest.main()
