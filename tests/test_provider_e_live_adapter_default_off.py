from __future__ import annotations

import ast
import os
import socket
import unittest
import urllib.request
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from runtime import provider_clients
from runtime.provider_live_adapter import (
    BUDGET_LIMIT_REQUIRED,
    FUTURE_LIVE_SMOKE_TEST,
    LIVE_PROVIDER_ADAPTER_BLOCKED,
    MANUAL_SMOKE_TEST_REQUIRED,
    REGISTRY_ALLOW_REQUIRED,
    DefaultOffProviderAdapter,
    LiveProviderAdapterRequest,
    ProviderLiveCallBlockedError,
)
from runtime.provider_request_flow import (
    UNTRUSTED_PROVIDER_OUTPUT,
    ProviderRequest,
    decide_mock_provider_request,
)
from runtime.safety.provider_call_limits import ProviderCallBudgetConfig


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "provider_live_adapter.py"


class ProviderELiveAdapterDefaultOffTests(unittest.TestCase):
    def test_adapter_is_default_off_and_returns_deterministic_blocked_metadata(self):
        request, decision = self.make_request_and_decision()
        adapter_request = self.make_adapter_request(request=request)
        adapter = DefaultOffProviderAdapter()

        first = adapter.evaluate(
            adapter_request=adapter_request,
            registry_decision=decision,
            budget_limit=None,
        )
        second = adapter.evaluate(
            adapter_request=adapter_request,
            registry_decision=decision,
            budget_limit=None,
        )

        self.assertEqual(LIVE_PROVIDER_ADAPTER_BLOCKED, first.status)
        self.assertTrue(first.live_call_blocked)
        self.assertFalse(first.live_call_attempted)
        self.assertEqual(first.decision_hash, second.decision_hash)
        self.assertEqual(first.decision_id, second.decision_id)
        self.assertEqual(UNTRUSTED_PROVIDER_OUTPUT, first.trust_label)
        self.assertIsNone(first.real_provider_response_text)
        self.assertEqual(FUTURE_LIVE_SMOKE_TEST, first.future_smoke_test_seam)
        self.assertTrue(first.manual_smoke_test_required)
        self.assertTrue(first.registry_allow_required)
        self.assertTrue(first.budget_limit_required)

    def test_missing_registry_decision_fails_closed(self):
        request = self.make_request()
        result = self.evaluate(request=request, registry_decision=None)

        self.assertIn(REGISTRY_ALLOW_REQUIRED.replace("_", " "), result.blocked_reason)
        self.assertFalse(result.live_call_attempted)
        self.assertTrue(result.live_call_blocked)

    def test_mismatched_registry_decision_fails_closed(self):
        request = self.make_request()
        other = self.make_request(task_text="different request")
        other_decision = decide_mock_provider_request(other)
        result = self.evaluate(
            request=request,
            registry_decision=other_decision,
        )

        self.assertIn("matching registry decision", result.blocked_reason)
        self.assertFalse(result.live_call_attempted)

    def test_manual_flag_alone_is_not_enough(self):
        request = self.make_request()
        result = self.evaluate(
            request=request,
            registry_decision=None,
            manual_live_call_requested=True,
            budget_limit=self.permissive_budget(),
        )

        self.assertIn("registry allow required", result.blocked_reason)
        self.assertFalse(result.live_call_attempted)

    def test_registry_decision_without_manual_flag_is_not_enough(self):
        request, decision = self.make_request_and_decision()
        result = self.evaluate(
            request=request,
            registry_decision=decision,
            manual_live_call_requested=False,
            budget_limit=self.permissive_budget(),
        )

        self.assertIn(MANUAL_SMOKE_TEST_REQUIRED.replace("_", " "), result.blocked_reason)
        self.assertFalse(result.live_call_attempted)

    def test_registry_and_manual_flag_without_budget_are_not_enough(self):
        request, decision = self.make_request_and_decision()
        result = self.evaluate(
            request=request,
            registry_decision=decision,
            manual_live_call_requested=True,
            budget_limit=None,
        )

        self.assertIn(BUDGET_LIMIT_REQUIRED.replace("_", " "), result.blocked_reason)
        self.assertFalse(result.budget_limit_present)
        self.assertFalse(result.live_call_attempted)

    def test_disabled_offline_profile_fails_closed_with_all_other_seams_present(self):
        request, decision = self.make_request_and_decision()
        result = self.evaluate(
            request=request,
            registry_decision=decision,
            manual_live_call_requested=True,
            budget_limit=self.permissive_budget(),
        )

        self.assertTrue(result.profile_registered)
        self.assertFalse(result.profile_enabled)
        self.assertFalse(result.network_allowed)
        self.assertIn("disabled", result.blocked_reason)
        self.assertFalse(result.live_call_attempted)

    def test_calls_enabled_environment_flag_does_not_change_blocked_result(self):
        request, decision = self.make_request_and_decision()
        with patch.dict(
            os.environ,
            {
                "AOIA_PROVIDER_CALLS_ENABLED": "1",
                "OPENROUTER_API_KEY": "fake-never-read",
            },
            clear=False,
        ):
            result = self.evaluate(
                request=request,
                registry_decision=decision,
                manual_live_call_requested=True,
                budget_limit=self.permissive_budget(),
            )

        self.assertTrue(result.live_call_blocked)
        self.assertFalse(result.live_call_attempted)
        self.assertEqual(UNTRUSTED_PROVIDER_OUTPUT, result.trust_label)
        self.assertIsNone(result.real_provider_response_text)

    def test_adapter_reads_no_environment_keys_and_calls_no_network_or_provider_client(self):
        request, decision = self.make_request_and_decision()
        with patch.object(
            os.environ,
            "get",
            side_effect=AssertionError("environment key read"),
        ) as env_get, patch.object(
            urllib.request,
            "urlopen",
            side_effect=AssertionError("network called"),
        ) as urlopen_mock, patch.object(
            socket,
            "create_connection",
            side_effect=AssertionError("network called"),
        ) as socket_mock, patch.object(
            provider_clients,
            "call_selected_provider_once",
            side_effect=AssertionError("provider client called"),
        ) as provider_call:
            result = self.evaluate(
                request=request,
                registry_decision=decision,
                manual_live_call_requested=True,
                budget_limit=self.permissive_budget(),
            )

        self.assertTrue(result.live_call_blocked)
        env_get.assert_not_called()
        urlopen_mock.assert_not_called()
        socket_mock.assert_not_called()
        provider_call.assert_not_called()

    def test_live_allowed_shaped_decision_still_cannot_activate_skeleton(self):
        request, decision = self.make_request_and_decision()
        future_shaped = replace(
            decision,
            live_call_allowed=False,
            status="FUTURE_LIVE_SMOKE_TEST_PENDING",
            reason="future seam only",
        )
        result = self.evaluate(
            request=request,
            registry_decision=future_shaped,
            manual_live_call_requested=True,
            budget_limit=self.permissive_budget(),
        )

        self.assertTrue(result.live_call_blocked)
        self.assertFalse(result.live_call_attempted)
        self.assertIsNone(result.real_provider_response_text)

    def test_exception_style_api_raises_controlled_block_error(self):
        request, decision = self.make_request_and_decision()
        with self.assertRaisesRegex(ProviderLiveCallBlockedError, "disabled"):
            DefaultOffProviderAdapter().require_blocked(
                adapter_request=self.make_adapter_request(
                    request=request,
                    manual_live_call_requested=True,
                ),
                registry_decision=decision,
                budget_limit=self.permissive_budget(),
            )

    def test_runtime_module_has_no_env_network_transport_or_authority_capability(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        lowered = source.lower()
        forbidden_terms = (
            "subprocess",
            "os.system",
            "popen",
            "socket",
            "urllib",
            "httpx",
            "playwright",
            "selenium",
            "eval(",
            "exec(",
            "webbrowser",
            "getenv",
            "environ",
            "api_key",
            "provider_clients",
            "openai_compatible",
            "gemini_provider",
            "gemma_provider",
            "approval_gate",
            "artifact_write",
            "human_decision",
        )
        for term in forbidden_terms:
            self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        forbidden_import_roots = {
            "httpx",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.isdisjoint(forbidden_import_roots))

    def evaluate(
        self,
        *,
        request: ProviderRequest,
        registry_decision,
        manual_live_call_requested: bool = False,
        budget_limit=None,
    ):
        return DefaultOffProviderAdapter().evaluate(
            adapter_request=self.make_adapter_request(
                request=request,
                manual_live_call_requested=manual_live_call_requested,
            ),
            registry_decision=registry_decision,
            budget_limit=budget_limit,
        )

    def make_request(self, **overrides):
        values = {
            "provider_id": "openrouter",
            "task_text": "Future provider smoke-test request metadata only.",
            "purpose": "Provider-E default-off adapter",
            "caller_label": "provider-e-test",
            "live_call_requested": True,
            "metadata": {"trace": "provider-e"},
        }
        values.update(overrides)
        return ProviderRequest(**values)

    def make_request_and_decision(self):
        request = self.make_request(live_call_requested=False)
        return request, decide_mock_provider_request(request)

    def make_adapter_request(
        self,
        *,
        request: ProviderRequest,
        manual_live_call_requested: bool = False,
    ):
        return LiveProviderAdapterRequest(
            request=request,
            model_label="future-openrouter-model",
            manual_live_call_requested=manual_live_call_requested,
            adapter_metadata={"mode": FUTURE_LIVE_SMOKE_TEST},
        )

    def permissive_budget(self):
        return ProviderCallBudgetConfig(
            max_calls_per_session=1,
            max_calls_per_day=1,
            max_input_chars_per_request=1000,
            max_estimated_tokens_per_request=500,
            max_estimated_cost_per_session="1.00",
            max_estimated_cost_per_day="1.00",
        )


if __name__ == "__main__":
    unittest.main()
