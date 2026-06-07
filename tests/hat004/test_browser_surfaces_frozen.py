from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BROWSER_TOOLS = PROJECT_ROOT / "runtime" / "tools" / "browser_tools.py"
EXECUTOR = PROJECT_ROOT / "runtime" / "tools" / "executor.py"
FREEZE_REPORT = PROJECT_ROOT / "docs" / "audit" / "HAT_004_BROWSER_SURFACE_FREEZE_REPORT.md"
GOVERNANCE_POLICY = PROJECT_ROOT / "docs" / "audit" / "HAT_004_BROWSER_GOVERNANCE_POLICY.md"

EXPECTED_BROWSER_ACTIONS = {
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


class Hat004BrowserSurfaceFreezeTests(unittest.TestCase):
    def test_freeze_documents_exist_and_mark_legacy_surfaces_not_approved(self) -> None:
        report = FREEZE_REPORT.read_text(encoding="utf-8")
        policy = GOVERNANCE_POLICY.read_text(encoding="utf-8")

        self.assertIn("NOT_APPROVED_H4", report)
        self.assertIn("NOT_APPROVED_H4", policy)
        self.assertIn("Existing browser-adjacent code is `NOT_APPROVED_H4`", report)
        self.assertIn("Current browser-adjacent runtime surfaces are `NOT_APPROVED_H4`", policy)

    def test_existing_browser_actions_are_documented_as_frozen(self) -> None:
        executor_text = EXECUTOR.read_text(encoding="utf-8")
        report = FREEZE_REPORT.read_text(encoding="utf-8")

        for action in EXPECTED_BROWSER_ACTIONS:
            with self.subTest(action=action):
                self.assertIn(f'"{action}"', executor_text)
                self.assertIn(f"`{action}`", report)

    def test_policy_contains_required_forbidden_boundaries(self) -> None:
        policy = GOVERNANCE_POLICY.read_text(encoding="utf-8")
        required_phrases = {
            "website login",
            "password entry",
            "credential handling",
            "cookie theft",
            "session theft",
            "cookie reuse",
            "session reuse",
            "autonomous navigation",
            "autonomous online actions",
            "CAPTCHA bypass",
            "stealth automation",
        }

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

    def test_h4c_does_not_import_or_execute_browser_runtime_code(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        forbidden_modules = {
            "runtime.tools.browser_tools",
            "runtime.tools.executor",
            "playwright",
            "selenium",
            "requests",
        }
        forbidden_calls = {"eval", "exec", "compile", "__import__"}

        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, forbidden_calls)

        self.assertTrue(forbidden_modules.isdisjoint(imported_modules))

    def test_browser_tools_remain_legacy_surface_not_policy(self) -> None:
        browser_source = BROWSER_TOOLS.read_text(encoding="utf-8")
        report = FREEZE_REPORT.read_text(encoding="utf-8")
        policy = GOVERNANCE_POLICY.read_text(encoding="utf-8")

        self.assertIn("class BrowserBridge", browser_source)
        self.assertIn("playwright.sync_api", browser_source)
        self.assertIn("this surface is `NOT_APPROVED_H4`", report)
        self.assertIn("runtime/tools/browser_tools.py`: `NOT_APPROVED_H4`", policy)


if __name__ == "__main__":
    unittest.main()
