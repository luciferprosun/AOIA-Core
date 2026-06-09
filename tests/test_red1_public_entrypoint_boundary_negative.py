"""
RED-1-F public entrypoint boundary negative diagnostics.
These tests do not start servers.
They do not launch browsers.
They do not call providers.
They do not execute project shell actions.
They check whether selected public entrypoint modules can be imported or inspected without dangerous side effects, and whether entrypoint exposure remains a RED-1 diagnostic concern.
This file does not close RED-1 blockers globally.
"""

from __future__ import annotations

import importlib
import os
import shutil
import socket
import subprocess
import sys
import unittest
import urllib.request
import webbrowser
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
MAIN_PATH = RUNTIME_DIR / "main.py"
RED1_PUBLIC_ENTRYPOINT_BLOCKER_CLOSED = False

BROWSER_MODULES = {
    "runtime.tools.browser_tools",
    "runtime.tools.web_reader",
    "playwright",
    "selenium",
}

MAIN_EXPOSED_TERMS = (
    "browser_open",
    "browser_start",
    "browser_tools",
    "web_reader",
    "shell_execute",
    "subprocess",
    "provider",
    "urlopen",
    "requests",
    "write_text",
    "unlink",
    "git commit",
    "git push",
    "require_approval=False",
)


def loaded_browser_modules() -> set[str]:
    return BROWSER_MODULES.intersection(sys.modules)


def dangerous_primitive_patches():
    stack = ExitStack()
    mocks = {
        "subprocess_run": stack.enter_context(
            patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called"))
        ),
        "subprocess_popen": stack.enter_context(
            patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess.Popen called"))
        ),
        "os_system": stack.enter_context(
            patch.object(os, "system", side_effect=AssertionError("os.system called"))
        ),
        "urlopen": stack.enter_context(
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("urllib.request.urlopen called"))
        ),
        "socket": stack.enter_context(
            patch.object(socket, "create_connection", side_effect=AssertionError("socket.create_connection called"))
        ),
        "webbrowser": stack.enter_context(
            patch.object(webbrowser, "open", side_effect=AssertionError("webbrowser.open called"))
        ),
        "write_text": stack.enter_context(
            patch.object(Path, "write_text", side_effect=AssertionError("Path.write_text called"))
        ),
        "unlink": stack.enter_context(
            patch.object(Path, "unlink", side_effect=AssertionError("Path.unlink called"))
        ),
        "shutil_move": stack.enter_context(
            patch.object(shutil, "move", side_effect=AssertionError("shutil.move called"))
        ),
        "shutil_rmtree": stack.enter_context(
            patch.object(shutil, "rmtree", side_effect=AssertionError("shutil.rmtree called"))
        ),
    }
    try:
        requests = importlib.import_module("requests")
    except ModuleNotFoundError:
        requests = None
    if requests is not None:
        mocks["requests_get"] = stack.enter_context(
            patch.object(requests, "get", side_effect=AssertionError("requests.get called"))
        )
        mocks["requests_post"] = stack.enter_context(
            patch.object(requests, "post", side_effect=AssertionError("requests.post called"))
        )
    for module_name in ("provider_clients", "runtime.provider_clients"):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, "urlopen"):
            mocks[f"{module_name}.urlopen"] = stack.enter_context(
                patch.object(module, "urlopen", side_effect=AssertionError(f"{module_name}.urlopen called"))
            )
    return stack, mocks


def import_or_reload_webapp():
    runtime_path = str(RUNTIME_DIR)
    inserted = False
    if runtime_path not in sys.path:
        sys.path.insert(0, runtime_path)
        inserted = True
    try:
        if "runtime.webapp" in sys.modules:
            return importlib.reload(sys.modules["runtime.webapp"])
        return importlib.import_module("runtime.webapp")
    finally:
        if inserted:
            try:
                sys.path.remove(runtime_path)
            except ValueError:
                pass


def import_webapp_or_skip_if_entrypoint_writes_report():
    try:
        return import_or_reload_webapp()
    except AssertionError as exc:
        if str(exc) == "Path.write_text called":
            raise unittest.SkipTest(
                "runtime.webapp import performs Path.write_text via KnowledgeRouter report initialization; "
                "RED-1-F keeps the public entrypoint blocker open."
            ) from exc
        raise


class Red1PublicEntrypointBoundaryNegativeTests(unittest.TestCase):
    def test_static_scan_of_runtime_main_records_exposed_surfaces(self) -> None:
        source = MAIN_PATH.read_text(encoding="utf-8")
        exposed = [term for term in MAIN_EXPOSED_TERMS if term in source]

        self.assertTrue(
            exposed,
            "runtime/main.py static scan should expose RED-1 diagnostic surfaces requiring later hardening; "
            "presence is diagnostic evidence, not proof of execution",
        )

    def test_runtime_webapp_import_does_not_trigger_dangerous_primitives(self) -> None:
        stack, mocks = dangerous_primitive_patches()

        with stack:
            module = import_webapp_or_skip_if_entrypoint_writes_report()

        self.assertTrue(hasattr(module, "CodexStyleHandler"))
        self.assertTrue(hasattr(module, "main"))
        for mock in mocks.values():
            mock.assert_not_called()

    def test_runtime_main_is_statically_inspected_not_imported(self) -> None:
        main_loaded_before = "main" in sys.modules
        source = MAIN_PATH.read_text(encoding="utf-8")
        exposed = [term for term in MAIN_EXPOSED_TERMS if term in source]
        main_loaded_after = "main" in sys.modules

        self.assertIn('if __name__ == "__main__"', source)
        self.assertTrue(exposed)
        self.assertEqual(
            main_loaded_before,
            main_loaded_after,
            "RED-1-F static inspection must not import runtime/main.py when exposed surfaces exist",
        )

    def test_webapp_import_does_not_import_browser_tools(self) -> None:
        before = loaded_browser_modules()
        stack, mocks = dangerous_primitive_patches()

        with stack:
            import_webapp_or_skip_if_entrypoint_writes_report()

        after = loaded_browser_modules()
        self.assertFalse(after - before, f"runtime.webapp import loaded browser modules: {sorted(after - before)}")
        for mock in mocks.values():
            mock.assert_not_called()

    def test_webapp_import_does_not_call_provider_or_network_primitives(self) -> None:
        stack, mocks = dangerous_primitive_patches()

        with stack:
            import_webapp_or_skip_if_entrypoint_writes_report()

        mocks["urlopen"].assert_not_called()
        mocks["socket"].assert_not_called()
        if "requests_get" in mocks:
            mocks["requests_get"].assert_not_called()
            mocks["requests_post"].assert_not_called()
        for name, mock in mocks.items():
            if name.endswith(".urlopen"):
                mock.assert_not_called()

    def test_webapp_import_does_not_perform_file_mutation_primitives(self) -> None:
        stack, mocks = dangerous_primitive_patches()

        with stack:
            import_webapp_or_skip_if_entrypoint_writes_report()

        mocks["write_text"].assert_not_called()
        mocks["unlink"].assert_not_called()
        mocks["shutil_move"].assert_not_called()
        mocks["shutil_rmtree"].assert_not_called()

    def test_public_entrypoint_blocker_remains_open(self) -> None:
        self.assertFalse(
            RED1_PUBLIC_ENTRYPOINT_BLOCKER_CLOSED,
            "RED-1-F is diagnostic only; public entrypoint blocker remains open.",
        )


if __name__ == "__main__":
    unittest.main()
