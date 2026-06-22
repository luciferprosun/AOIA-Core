from __future__ import annotations

import ast
import json
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.providers.contracts import (
    BLOCKED,
    DRY_RUN_PREVIEW,
    LIVE_SUCCESS,
    UNTRUSTED,
    KNOWN_RUNTIME_PROVIDER_IDS,
    ProviderActivationStatus,
)
from runtime.providers.gateway import run_provider_request
from runtime.providers.payloads import build_provider_envelope, build_provider_payload
from runtime.providers.redaction import REDACTED, redact_provider_data, redact_provider_text
from runtime.providers.registry import list_runtime_providers


REPO_ROOT = Path(__file__).parents[1]
PROVIDER_RUNTIME_FILES = (
    REPO_ROOT / "runtime/providers/contracts.py",
    REPO_ROOT / "runtime/providers/registry.py",
    REPO_ROOT / "runtime/providers/payloads.py",
    REPO_ROOT / "runtime/providers/redaction.py",
    REPO_ROOT / "runtime/providers/runtime_policy.py",
    REPO_ROOT / "runtime/providers/gateway.py",
)
GATEWAY_FILE = REPO_ROOT / "runtime/providers/gateway.py"


class ProviderRuntime1ATests(unittest.TestCase):
    def test_registry_lists_known_providers_deterministically(self) -> None:
        first = list_runtime_providers()
        second = list_runtime_providers()
        self.assertEqual(first, second)
        self.assertEqual(KNOWN_RUNTIME_PROVIDER_IDS, tuple(item.provider_id for item in first))
        self.assertTrue(all(item.supports_streaming is False for item in first))

    def test_unknown_provider_rejects_deterministically(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown provider_id"):
            self.make_envelope(provider_id="unknown_chat")

    def test_openrouter_dry_run_builds_payload_without_network(self) -> None:
        envelope = self.make_envelope(provider_id="openrouter_chat")
        with patch("runtime.providers.gateway.urlopen") as network:
            result = run_provider_request(envelope)
        self.assertEqual(DRY_RUN_PREVIEW, result.status)
        self.assertIsNone(result.response_text)
        network.assert_not_called()
        self.assertEqual("future-model", build_provider_payload(envelope)["model"])

    def test_gemini_dry_run_builds_payload_without_network(self) -> None:
        envelope = self.make_envelope(provider_id="gemini_chat")
        with patch("runtime.providers.gateway.urlopen") as network:
            result = run_provider_request(envelope)
        self.assertEqual(DRY_RUN_PREVIEW, result.status)
        network.assert_not_called()
        self.assertIn("contents", build_provider_payload(envelope))

    def test_mock_chat_is_deterministic_and_never_uses_network(self) -> None:
        envelope = self.make_envelope(provider_id="mock_chat")
        with patch("runtime.providers.gateway.urlopen") as network:
            first = run_provider_request(envelope)
            second = run_provider_request(envelope)
        self.assertEqual(first, second)
        self.assertEqual(DRY_RUN_PREVIEW, first.status)
        self.assertIn("mock_chat deterministic response", first.response_text or "")
        network.assert_not_called()

    def test_live_without_acknowledgement_blocks_before_key_or_network(self) -> None:
        envelope = self.make_envelope(provider_id="openrouter_chat", dry_run=False)
        with (
            patch("runtime.providers.gateway._read_api_key") as key_read,
            patch("runtime.providers.gateway.urlopen") as network,
        ):
            result = run_provider_request(
                envelope,
                live=True,
                activation_status=ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST,
            )
        self.assertEqual(BLOCKED, result.status)
        key_read.assert_not_called()
        network.assert_not_called()

    def test_live_without_api_key_blocks_before_network(self) -> None:
        envelope = self.make_envelope(provider_id="gemini_chat", dry_run=False)
        with (
            patch("runtime.providers.gateway._read_api_key", return_value="") as key_read,
            patch("runtime.providers.gateway.urlopen") as network,
        ):
            result = self.run_live(envelope)
        self.assertEqual(BLOCKED, result.status)
        self.assertIn("API key", result.error_message or "")
        key_read.assert_called_once()
        network.assert_not_called()

    def test_live_requires_model_prompt_cap_and_manual_activation(self) -> None:
        cases = (
            self.make_envelope(provider_id="openrouter_chat", model_id="", dry_run=False),
            self.make_envelope(provider_id="openrouter_chat", prompt="", dry_run=False),
            self.make_envelope(provider_id="openrouter_chat", params={}, dry_run=False),
        )
        for envelope in cases:
            with self.subTest(preview=envelope.payload_preview):
                with patch("runtime.providers.gateway._read_api_key") as key_read:
                    result = self.run_live(envelope)
                self.assertEqual(BLOCKED, result.status)
                key_read.assert_not_called()
        envelope = self.make_envelope(provider_id="openrouter_chat", dry_run=False)
        with patch("runtime.providers.gateway._read_api_key") as key_read:
            result = run_provider_request(
                envelope,
                live=True,
                acknowledge_live_provider_test=True,
            )
        self.assertEqual(BLOCKED, result.status)
        key_read.assert_not_called()

    def test_fallback_and_unknown_payload_parameters_are_rejected(self) -> None:
        for params in ({"fallback": "other"}, {"fallback_provider": "other"}):
            with self.subTest(params=params):
                with self.assertRaisesRegex(ValueError, "fallback is not available"):
                    self.make_envelope(provider_id="openrouter_chat", params=params)

    def test_metadata_only_provider_cannot_enter_live_gateway(self) -> None:
        for provider_id in ("openai_chat", "anthropic_chat"):
            with self.subTest(provider_id=provider_id):
                envelope = self.make_envelope(provider_id=provider_id, dry_run=False)
                preview = json.loads(envelope.payload_preview)
                self.assertTrue(preview["metadata_only"])
                self.assertFalse(preview["runtime_payload_supported"])
                with (
                    patch("runtime.providers.gateway._read_api_key") as key_read,
                    patch("runtime.providers.gateway.urlopen") as network,
                ):
                    result = self.run_live(envelope)
                self.assertEqual(BLOCKED, result.status)
                self.assertIn("metadata-only", result.error_message or "")
                key_read.assert_not_called()
                network.assert_not_called()

    def test_metadata_only_dry_run_is_policy_blocked_without_key_or_network(self) -> None:
        for provider_id in (
            "openai_chat",
            "anthropic_chat",
            "google_gemini_chat",
            "local_ollama_chat",
        ):
            with self.subTest(provider_id=provider_id):
                envelope = self.make_envelope(provider_id=provider_id)
                with (
                    patch("runtime.providers.gateway._read_api_key") as key_read,
                    patch("runtime.providers.gateway.urlopen") as network,
                ):
                    result = run_provider_request(envelope)
                self.assertEqual(BLOCKED, result.status)
                self.assertIn("metadata-only", result.error_message or "")
                key_read.assert_not_called()
                network.assert_not_called()

    def test_mocked_openrouter_live_call_uses_single_gateway_call(self) -> None:
        envelope = self.make_envelope(provider_id="openrouter_chat", dry_run=False)
        response = self.fake_response(
            {"choices": [{"message": {"content": "mocked remote text"}}]}
        )
        with (
            patch("runtime.providers.gateway._read_api_key", return_value="placeholder"),
            patch("runtime.providers.gateway.urlopen", return_value=response) as network,
        ):
            result = self.run_live(envelope)
        self.assertEqual(LIVE_SUCCESS, result.status)
        self.assertEqual("mocked remote text", result.response_text)
        network.assert_called_once()

    def test_mocked_gemini_live_call_uses_single_gateway_call(self) -> None:
        envelope = self.make_envelope(provider_id="gemini_chat", dry_run=False)
        response = self.fake_response(
            {"candidates": [{"content": {"parts": [{"text": "mocked gemini text"}]}}]}
        )
        with (
            patch("runtime.providers.gateway._read_api_key", return_value="placeholder"),
            patch("runtime.providers.gateway.urlopen", return_value=response) as network,
        ):
            result = self.run_live(envelope)
        self.assertEqual(LIVE_SUCCESS, result.status)
        self.assertEqual("mocked gemini text", result.response_text)
        network.assert_called_once()

    def test_live_response_cannot_echo_gateway_secret(self) -> None:
        envelope = self.make_envelope(provider_id="openrouter_chat", dry_run=False)
        response = self.fake_response(
            {"choices": [{"message": {"content": "echo placeholder"}}]}
        )
        with (
            patch("runtime.providers.gateway._read_api_key", return_value="placeholder"),
            patch("runtime.providers.gateway.urlopen", return_value=response),
        ):
            result = self.run_live(envelope)
        self.assertEqual(LIVE_SUCCESS, result.status)
        self.assertNotIn("placeholder", result.response_text or "")
        self.assertIn(REDACTED, result.response_text or "")

    def test_output_is_untrusted_and_contains_no_authority_fields(self) -> None:
        result = run_provider_request(self.make_envelope(provider_id="mock_chat"))
        self.assertEqual(UNTRUSTED, result.trust_status)
        field_names = {item.name for item in fields(result)}
        for name in (
            "approved", "authority_granted", "can_approve", "can_write",
            "gate_satisfied", "execution_allowed", "artifact_write_allowed",
        ):
            self.assertNotIn(name, field_names)

    def test_envelope_is_frozen_and_has_no_runtime_methods_or_secrets(self) -> None:
        envelope = self.make_envelope(provider_id="openrouter_chat")
        for name in ("send", "call", "execute", "dispatch"):
            self.assertFalse(hasattr(envelope, name))
        self.assertNotIn("api_key", envelope.to_dict())
        with self.assertRaises(FrozenInstanceError):
            envelope.provider_id = "mock_chat"  # type: ignore[misc]

    def test_redaction_removes_headers_bearer_and_key_patterns(self) -> None:
        secret = "sk-" + "A" * 20
        gemini = "AIza" + "B" * 28
        redacted = redact_provider_data(
            {
                "Authorization": f"Bearer {secret}",
                "nested": [f"value={secret}", gemini],
            },
            known_secrets=(secret, gemini),
        )
        rendered = json.dumps(redacted)
        self.assertNotIn(secret, rendered)
        self.assertNotIn(gemini, rendered)
        self.assertIn(REDACTED, rendered)
        self.assertNotIn(secret, redact_provider_text(f"Bearer {secret}"))

    def test_network_and_environment_imports_exist_only_in_gateway(self) -> None:
        for path in PROVIDER_RUNTIME_FILES:
            imports = self.imported_modules(path)
            if path == GATEWAY_FILE:
                self.assertIn("os", imports)
                self.assertIn("urllib.request", imports)
            else:
                self.assertFalse(any(name == "os" or name.startswith("urllib") for name in imports))

    def test_no_provider_sdk_shell_browser_executor_or_gate_imports(self) -> None:
        forbidden = (
            "openai", "anthropic", "google", "litellm", "langchain", "autogen",
            "subprocess", "selenium", "playwright", "runtime.tools", "runtime.execution",
            "runtime.safety.approval", "runtime.safety.gated", "runtime.webapp",
        )
        for path in PROVIDER_RUNTIME_FILES:
            for module in self.imported_modules(path):
                self.assertFalse(any(module == item or module.startswith(item + ".") for item in forbidden))

    def test_no_environment_read_outside_gateway_and_no_import_time_read(self) -> None:
        for path in PROVIDER_RUNTIME_FILES:
            source = path.read_text(encoding="utf-8")
            if path != GATEWAY_FILE:
                self.assertNotIn("os.environ", source)
                self.assertNotIn("getenv", source)
        gateway_source = GATEWAY_FILE.read_text(encoding="utf-8")
        tree = ast.parse(gateway_source)
        module_level_calls = [
            node for node in tree.body if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign))
            and any(isinstance(child, ast.Call) for child in ast.walk(node))
        ]
        self.assertEqual([], module_level_calls)

    def run_live(self, envelope):
        return run_provider_request(
            envelope,
            live=True,
            acknowledge_live_provider_test=True,
            activation_status=ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST,
        )

    def make_envelope(
        self,
        *,
        provider_id: str,
        model_id: str = "future-model",
        prompt: str = "Explicit test prompt.",
        params: dict[str, object] | None = None,
        dry_run: bool = True,
    ):
        return build_provider_envelope(
            provider_id=provider_id,
            model_id=model_id,
            prompt=prompt,
            params={"max_tokens": 64} if params is None else params,
            dry_run=dry_run,
            created_at="2026-06-22T08:00:00+02:00",
        )

    @staticmethod
    def fake_response(payload: object) -> MagicMock:
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps(payload).encode("utf-8")
        return response

    @staticmethod
    def imported_modules(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules


if __name__ == "__main__":
    unittest.main()
