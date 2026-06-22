from __future__ import annotations

import ast
import json
import unittest
from contextlib import redirect_stdout
from dataclasses import fields
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from runtime.providers.cli import main as cli_main
from runtime.providers.contracts import BLOCKED, DRY_RUN_PREVIEW, UNTRUSTED, ProviderActivationStatus
from runtime.providers.selector import (
    get_provider_status,
    list_available_providers,
    run_configured_provider,
    run_selected_provider,
)
from runtime.providers.user_config import provider_selector_config_from_mapping


REPO_ROOT = Path(__file__).parents[1]
SELECTOR_FILES = (
    REPO_ROOT / "runtime/providers/selector.py",
    REPO_ROOT / "runtime/providers/user_config.py",
    REPO_ROOT / "runtime/providers/cli.py",
)


class ProviderSelector1AFinalTests(unittest.TestCase):
    def test_provider_list_is_deterministic_runtime_subset(self) -> None:
        first = list_available_providers()
        second = list_available_providers()
        self.assertEqual(first, second)
        self.assertEqual(
            ("mock_chat", "openrouter_chat", "gemini_chat"),
            tuple(item.provider_id for item in first),
        )
        self.assertTrue(all(item.runtime_supported for item in first))
        self.assertTrue(all(item.metadata_only is False for item in first))
        self.assertTrue(all(item.default_mode == "dry_run" for item in first))
        self.assertTrue(all(item.output_trust == UNTRUSTED for item in first))

    def test_provider_status_distinguishes_runtime_and_metadata_only(self) -> None:
        self.assertTrue(get_provider_status("openrouter_chat").live_available)
        metadata = get_provider_status("openai_chat")
        self.assertFalse(metadata.runtime_supported)
        self.assertTrue(metadata.metadata_only)
        self.assertFalse(metadata.live_available)
        self.assertEqual(UNTRUSTED, metadata.output_trust)

    def test_dry_run_selector_calls_are_network_and_key_free(self) -> None:
        for provider_id in ("mock_chat", "openrouter_chat", "gemini_chat"):
            with self.subTest(provider_id=provider_id):
                with (
                    patch("runtime.providers.gateway._read_api_key") as key_read,
                    patch("runtime.providers.gateway.urlopen") as network,
                ):
                    result = self._run_selector(provider_id=provider_id)
                self.assertEqual(DRY_RUN_PREVIEW, result.status)
                self.assertEqual(UNTRUSTED, result.trust_status)
                key_read.assert_not_called()
                network.assert_not_called()

    def test_live_without_ack_key_model_prompt_or_cap_blocks(self) -> None:
        with patch("runtime.providers.gateway._read_api_key") as key_read:
            without_ack = self._run_selector(provider_id="openrouter_chat", live=True)
        self.assertEqual(BLOCKED, without_ack.status)
        key_read.assert_not_called()

        with (
            patch("runtime.providers.gateway._read_api_key", return_value="") as key_read,
            patch("runtime.providers.gateway.urlopen") as network,
        ):
            without_key = self._run_selector(
                provider_id="openrouter_chat",
                live=True,
                acknowledge=True,
                activation=ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST,
            )
        self.assertEqual(BLOCKED, without_key.status)
        key_read.assert_called_once()
        network.assert_not_called()

        for values in (
            {"model_id": ""},
            {"prompt": ""},
            {"max_tokens": None},
        ):
            with self.subTest(values=values):
                with patch("runtime.providers.gateway._read_api_key") as key_read:
                    result = self._run_selector(
                        provider_id="openrouter_chat",
                        live=True,
                        acknowledge=True,
                        activation=ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST,
                        **values,
                    )
                self.assertEqual(BLOCKED, result.status)
                key_read.assert_not_called()

    def test_config_is_local_strict_dry_run_and_contains_no_secret_fields(self) -> None:
        config = provider_selector_config_from_mapping(
            {
                "selected_provider_id": "mock_chat",
                "selected_model_id": "mock-model",
            }
        )
        self.assertEqual("dry_run", config.default_mode)
        self.assertFalse(config.live_enabled)
        self.assertEqual(
            {
                "selected_provider_id",
                "selected_model_id",
                "default_max_tokens",
                "default_mode",
                "live_enabled",
            },
            set(config.to_dict()),
        )
        for field_name in ("api_key", "secret", "token", "credential"):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, "secret or credential"):
                    provider_selector_config_from_mapping(
                        {
                            "selected_provider_id": "mock_chat",
                            "selected_model_id": "mock-model",
                            field_name: "not-used",
                        }
                    )
        with self.assertRaisesRegex(ValueError, "cannot enable live"):
            provider_selector_config_from_mapping(
                {
                    "selected_provider_id": "mock_chat",
                    "selected_model_id": "mock-model",
                    "live_enabled": True,
                }
            )

    def test_metadata_only_config_is_blocked_by_policy_not_invalid(self) -> None:
        config = provider_selector_config_from_mapping(
            {
                "selected_provider_id": "openai_chat",
                "selected_model_id": "metadata-model",
            }
        )
        with (
            patch("runtime.providers.gateway._read_api_key") as key_read,
            patch("runtime.providers.gateway.urlopen") as network,
        ):
            result = run_configured_provider(
                config,
                prompt="Review-only prompt.",
                created_at="2026-06-22T09:00:00+02:00",
            )
        self.assertEqual(BLOCKED, result.status)
        self.assertIn("metadata-only", result.error_message or "")
        key_read.assert_not_called()
        network.assert_not_called()

    def test_unknown_provider_in_config_is_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown provider_id"):
            provider_selector_config_from_mapping(
                {
                    "selected_provider_id": "unknown_chat",
                    "selected_model_id": "unknown-model",
                }
            )

    def test_fallback_cannot_be_configured_or_called(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            provider_selector_config_from_mapping(
                {
                    "selected_provider_id": "mock_chat",
                    "selected_model_id": "mock-model",
                    "fallback": ["openrouter_chat"],
                }
            )
        self.assertNotIn("fallback", run_selected_provider.__code__.co_varnames)

    def test_provider_output_has_no_authority_gate_or_write_fields(self) -> None:
        result = self._run_selector(provider_id="mock_chat")
        result_fields = {item.name for item in fields(result)}
        for name in (
            "approved", "authority_granted", "can_approve", "can_write",
            "gate_satisfied", "execution_allowed", "artifact_write_allowed",
        ):
            self.assertNotIn(name, result_fields)

    def test_cli_list_and_default_dry_run_are_local(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, cli_main(["--list"]))
        listed = json.loads(output.getvalue())
        self.assertEqual(3, len(listed))

        output = StringIO()
        with (
            patch("runtime.providers.gateway._read_api_key") as key_read,
            patch("runtime.providers.gateway.urlopen") as network,
            redirect_stdout(output),
        ):
            code = cli_main(
                [
                    "--provider", "mock_chat",
                    "--model", "mock-model",
                    "--prompt", "hello",
                    "--max-tokens", "32",
                ]
            )
        self.assertEqual(0, code)
        self.assertEqual(DRY_RUN_PREVIEW, json.loads(output.getvalue())["status"])
        key_read.assert_not_called()
        network.assert_not_called()

    def test_selector_modules_add_no_network_env_sdk_or_execution_capability(self) -> None:
        forbidden_imports = (
            "os", "urllib", "requests", "httpx", "aiohttp", "socket", "openai",
            "anthropic", "google", "litellm", "langchain", "autogen", "subprocess",
            "selenium", "playwright", "runtime.tools", "runtime.execution",
            "runtime.webapp", "runtime.safety.approval", "runtime.safety.gated",
        )
        for path in SELECTOR_FILES:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
            self.assertFalse(
                any(
                    module == item or module.startswith(item + ".")
                    for module in imports
                    for item in forbidden_imports
                )
            )
            self.assertNotIn("os.environ", source)
            self.assertNotIn("getenv", source)

    def _run_selector(
        self,
        *,
        provider_id: str,
        model_id: str = "test-model",
        prompt: str = "Explicit test prompt.",
        max_tokens: int | None = 64,
        live: bool = False,
        acknowledge: bool = False,
        activation: ProviderActivationStatus = ProviderActivationStatus.DRY_RUN_ONLY,
    ):
        return run_selected_provider(
            provider_id=provider_id,
            model_id=model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            live=live,
            acknowledge_live_provider_test=acknowledge,
            activation_status=activation,
            selected_by="operator",
            created_at="2026-06-22T09:00:00+02:00",
        )


if __name__ == "__main__":
    unittest.main()
