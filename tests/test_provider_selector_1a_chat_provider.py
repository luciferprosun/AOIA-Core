from __future__ import annotations

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from runtime.provider_selector import (
    KNOWN_CHAT_PROVIDER_IDS,
    ChatProviderSelection,
    chat_provider_selection_to_dict,
    normalize_chat_provider_id,
    select_chat_provider,
)


RUNTIME_FILE = Path(__file__).parents[1] / "runtime" / "provider_selector.py"


class ChatProviderSelectorTests(unittest.TestCase):
    def test_known_provider_ids_are_accepted_as_inert_metadata(self) -> None:
        for provider_id in KNOWN_CHAT_PROVIDER_IDS:
            with self.subTest(provider_id=provider_id):
                selection = select_chat_provider(provider_id)
                self.assertEqual(provider_id, selection.selected_provider_id)
                self.assertTrue(selection.is_metadata_only)
                self.assertFalse(selection.provider_enabled)
                self.assertFalse(selection.provider_call_allowed)

    def test_unknown_missing_and_non_string_ids_are_rejected(self) -> None:
        for provider_id in (None, "", "unknown_chat", 1, object()):
            with self.subTest(provider_id=provider_id):
                with self.assertRaises(ValueError):
                    select_chat_provider(provider_id)

    def test_normalization_is_deterministic_and_bounded(self) -> None:
        self.assertEqual("openai_chat", normalize_chat_provider_id("  OPENAI_CHAT  "))
        self.assertEqual(
            select_chat_provider(" MOCK_CHAT "),
            select_chat_provider("mock_chat"),
        )

    def test_selection_is_frozen(self) -> None:
        selection = select_chat_provider("mock_chat")
        with self.assertRaises(FrozenInstanceError):
            selection.selected_provider_id = "openai_chat"  # type: ignore[misc]

    def test_constructor_cannot_enable_provider_or_authority(self) -> None:
        selection = ChatProviderSelection(
            selected_provider_id="mock_chat",
            provider_enabled=True,
            provider_call_allowed=True,
            network_allowed=True,
            authority_granted=True,
            approval_granted=True,
            gate_satisfied=True,
            artifact_write_allowed=True,
            execution_allowed=True,
        )
        for name in (
            "provider_enabled",
            "provider_call_allowed",
            "network_allowed",
            "authority_granted",
            "approval_granted",
            "gate_satisfied",
            "artifact_write_allowed",
            "execution_allowed",
        ):
            self.assertFalse(getattr(selection, name), name)

    def test_serialization_is_canonical_and_deterministic(self) -> None:
        selection = select_chat_provider("google_gemini_chat")
        first = chat_provider_selection_to_dict(selection)
        second = chat_provider_selection_to_dict(selection)
        self.assertEqual(first, second)
        self.assertEqual("google_gemini_chat", first["selected_provider_id"])
        self.assertEqual("chat_provider_metadata", first["selection_kind"])
        self.assertFalse(first["provider_call_allowed"])

    def test_serializer_rejects_unknown_input(self) -> None:
        with self.assertRaises(ValueError):
            chat_provider_selection_to_dict({"selected_provider_id": "mock_chat"})

    def test_module_has_no_provider_network_browser_shell_or_secret_capability(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        called_names: set[str] = set()
        called_attrs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_names.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_attrs.add(node.func.attr)

        forbidden_modules = (
            "os", "subprocess", "socket", "requests", "urllib", "httpx", "aiohttp",
            "selenium", "playwright", "openai", "anthropic", "google", "ollama",
            "runtime.providers", "runtime.provider_clients", "runtime.provider_live_adapter",
            "runtime.dispatch", "runtime.execution",
        )
        for module in imports:
            self.assertFalse(
                any(module == item or module.startswith(item + ".") for item in forbidden_modules)
            )
        for name in ("open", "print", "eval", "exec"):
            self.assertNotIn(name, called_names)
        for name in (
            "getenv", "send", "post", "request", "execute", "dispatch", "write",
            "write_text", "write_bytes",
        ):
            self.assertNotIn(name, called_attrs)

    def test_module_does_not_read_keys_environment_or_change_gates(self) -> None:
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        for term in (
            "api_key", "api key", "os.environ", "os.getenv", "dotenv", "keyring",
            "approval_artifact_gate", "provider_live_call_allowed", "call_selected_provider",
        ):
            self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
