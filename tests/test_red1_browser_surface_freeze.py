from __future__ import annotations

import ast
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
BROWSER_TOOLS_PATH = RUNTIME_DIR / "tools" / "browser_tools.py"
WEB_READER_PATH = RUNTIME_DIR / "tools" / "web_reader.py"
EXECUTOR_PATH = RUNTIME_DIR / "tools" / "executor.py"

BROWSER_ACTIONS = {
    "browser_start",
    "browser_open",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_read_html",
    "browser_get_visible_text",
    "browser_screenshot",
    "browser_close",
    "browser_current_url",
}


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


class Red1BrowserSurfaceFreezeTests(unittest.TestCase):
    def test_browser_modules_are_marked_legacy_frozen_and_not_approved(self) -> None:
        for path in (BROWSER_TOOLS_PATH, WEB_READER_PATH):
            with self.subTest(path=path.name):
                values = literal_assignments(path)
                self.assertIs(values["LEGACY_BROWSER_SURFACE"], True)
                self.assertIs(values["APPROVED_RUNTIME_BROWSER_FLOW"], False)
                self.assertIs(values["H4_APPROVED_BROWSER_FLOW"], False)
                self.assertIs(values["BROWSER_EXECUTION_FROZEN"], True)

    def test_browser_execution_guard_blocks_by_default_before_launch(self) -> None:
        with patch.dict(os.environ, {"AOIA_LEGACY_BROWSER_ENABLED": ""}, clear=False):
            browser_tools = import_or_reload("runtime.tools.browser_tools")

        self.assertFalse(browser_tools.AOIA_LEGACY_BROWSER_ENABLED)
        with self.assertRaisesRegex(RuntimeError, "Legacy browser surface is frozen"):
            browser_tools._require_legacy_browser_enabled()
        with self.assertRaisesRegex(RuntimeError, "Legacy browser surface is frozen"):
            browser_tools.browser_start()

    def test_web_reader_fetch_is_guarded_by_default(self) -> None:
        text = WEB_READER_PATH.read_text(encoding="utf-8")
        self.assertIn("def fetch_page", text)
        self.assertIn("_require_legacy_browser_enabled()", text)
        self.assertLess(
            text.index("_require_legacy_browser_enabled()"),
            text.index("requests.get"),
        )

    def test_executor_registry_marks_browser_tools_frozen(self) -> None:
        executor = import_or_reload("runtime.tools.executor")
        engine = object.__new__(executor.ExecutionEngine)
        tools = engine._build_tool_registry()

        for action in BROWSER_ACTIONS:
            with self.subTest(action=action):
                self.assertIn(action, tools)
                self.assertIn("Frozen legacy browser surface", tools[action].description)

    def test_no_live_browser_surface_is_approved_by_default(self) -> None:
        checked_paths = (BROWSER_TOOLS_PATH, WEB_READER_PATH, EXECUTOR_PATH)
        forbidden_fragments = (
            "APPROVED_RUNTIME_BROWSER_FLOW = True",
            "H4_APPROVED_BROWSER_FLOW = True",
            "BROWSER_EXECUTION_FROZEN = False",
            "AOIA_LEGACY_BROWSER_ENABLED = True",
        )
        findings: list[tuple[str, str]] = []
        for path in checked_paths:
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    findings.append((str(path), fragment))

        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
