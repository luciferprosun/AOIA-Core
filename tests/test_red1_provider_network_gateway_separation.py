from __future__ import annotations

import ast
import importlib
import os
import socket
import sys
import tempfile
import unittest
import urllib.request
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
PROVIDER_CLIENTS_PATH = RUNTIME_DIR / "provider_clients.py"
PROVIDERS_CONFIG_PATH = RUNTIME_DIR / "providers" / "config.py"
OPENAI_COMPATIBLE_PATH = RUNTIME_DIR / "providers" / "openai_compatible.py"
GEMINI_PROVIDER_PATH = RUNTIME_DIR / "providers" / "gemini_provider.py"
GEMMA_PROVIDER_PATH = RUNTIME_DIR / "providers" / "gemma_provider.py"

PROVIDER_SURFACE_PATHS = (
    PROVIDER_CLIENTS_PATH,
    PROVIDERS_CONFIG_PATH,
    OPENAI_COMPATIBLE_PATH,
    GEMINI_PROVIDER_PATH,
    GEMMA_PROVIDER_PATH,
)


def import_or_reload(module_name: str):
    runtime_path = str(RUNTIME_DIR)
    inserted = False
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)
        inserted = True
    try:
        if module_name in sys.modules:
            return importlib.reload(sys.modules[module_name])
        return importlib.import_module(module_name)
    finally:
        if inserted:
            try:
                sys.path.remove(runtime_path)
            except ValueError:
                pass


def literal_assignments(path: Path) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            try:
                values[target.id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError):
                continue
    return values


@contextmanager
def patched_network_primitives():
    stack = ExitStack()
    mocks = {
        "urllib_urlopen": stack.enter_context(
            patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("urllib.request.urlopen called"),
            )
        ),
        "socket_create_connection": stack.enter_context(
            patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("socket.create_connection called"),
            )
        ),
    }

    try:
        requests = importlib.import_module("requests")
    except ModuleNotFoundError:
        requests = None
    if requests is not None:
        mocks["requests_request"] = stack.enter_context(
            patch.object(requests, "request", side_effect=AssertionError("requests.request called"))
        )

    try:
        httpx = importlib.import_module("httpx")
    except ModuleNotFoundError:
        httpx = None
    if httpx is not None:
        mocks["httpx_request"] = stack.enter_context(
            patch.object(httpx, "request", side_effect=AssertionError("httpx.request called"))
        )

    try:
        yield mocks
    finally:
        stack.close()


def live_runtime_code_files() -> list[Path]:
    excluded_parts = {".venv", "__pycache__", "knowledge", "reports"}
    files: list[Path] = []
    for path in RUNTIME_DIR.rglob("*.py"):
        if any(part in excluded_parts for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


class Red1ProviderNetworkGatewaySeparationTests(unittest.TestCase):
    def test_provider_network_modules_are_marked_frozen_and_not_approved(self) -> None:
        for path in PROVIDER_SURFACE_PATHS:
            with self.subTest(path=path.name):
                values = literal_assignments(path)
                self.assertIs(values["PROVIDER_NETWORK_SURFACE"], True)
                self.assertIs(values["APPROVED_RUNTIME_PROVIDER_FLOW"], False)
                self.assertIs(values["PROVIDER_CALLS_FROZEN"], True)

    def test_provider_call_entrypoints_are_guarded_before_network(self) -> None:
        with patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": ""}, clear=False):
            provider_clients = import_or_reload("runtime.provider_clients")

            with patched_network_primitives() as mocks:
                result = provider_clients.call_selected_provider_once(
                    provider_id="gemini",
                    model_id="gemini/gemini-2.5-flash",
                    user_prompt="public diagnostic prompt",
                    human_approved=True,
                    provider_call_permitted=True,
                    policy_rejected=False,
                )

                with self.assertRaisesRegex(RuntimeError, "Provider/network calls are frozen"):
                    provider_clients._call_gemini_once(
                        model_id="gemini/gemini-2.5-flash",
                        user_prompt="public diagnostic prompt",
                    )

        self.assertFalse(result.call_made)
        self.assertIn("frozen by default", result.error)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_provider_manager_fallback_is_guarded_before_provider_build_or_network(self) -> None:
        with patch.dict(os.environ, {"AOIA_PROVIDER_CALLS_ENABLED": ""}, clear=False):
            provider_config = import_or_reload("runtime.providers.config")

            with tempfile.TemporaryDirectory() as raw_tmp:
                manager = provider_config.ProviderManager(Path(raw_tmp))
                with patched_network_primitives() as mocks:
                    with self.assertRaisesRegex(RuntimeError, "Provider/network calls are frozen"):
                        manager.generate_with_fallback("public diagnostic prompt")

        for mock in mocks.values():
            mock.assert_not_called()

    def test_config_catalog_and_cpt_paths_remain_local_and_network_free(self) -> None:
        provider_config = import_or_reload("runtime.provider_config")
        model_catalog = import_or_reload("runtime.model_catalog")
        webapp = import_or_reload("runtime.webapp")

        with patched_network_primitives() as mocks:
            config_status = provider_config.get_provider_config_status()
            catalog = model_catalog.get_static_model_catalog_payload()
            transform = webapp.build_cpt_transform_payload(
                "Review the provider gateway separation critically.",
                mode="balanced_critic",
            )

        self.assertIn("gemini_configured", config_status)
        self.assertFalse(catalog["provider_call_permitted"])
        self.assertTrue(transform["ok"])
        self.assertFalse(transform["record"]["provider_call_permitted"])
        for mock in mocks.values():
            mock.assert_not_called()

    def test_no_live_runtime_file_enables_provider_calls_by_default(self) -> None:
        forbidden_fragments = (
            "APPROVED_RUNTIME_PROVIDER_FLOW = True",
            "PROVIDER_CALLS_FROZEN = False",
            "AOIA_PROVIDER_CALLS_ENABLED = True",
            "health_check_permitted\": True",
            "automatic_fallback_permitted\": True",
        )
        findings: list[tuple[str, str]] = []
        for path in live_runtime_code_files():
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    findings.append((str(path), fragment))

        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
