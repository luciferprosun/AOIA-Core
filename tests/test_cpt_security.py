from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CPT_DIR = PROJECT_ROOT / "runtime" / "cpt"

FORBIDDEN_IMPORTS = {
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "webbrowser",
    "openai",
    "anthropic",
    "google.generativeai",
    "playwright",
    "selenium",
    "shell_tools",
    "browser_tools",
    "executor",
    "runtime.provider_clients",
    "runtime.providers",
    "runtime.tools.shell_tools",
    "runtime.tools.browser_tools",
    "runtime.tools.executor",
}

FORBIDDEN_CALL_NAMES = {"eval", "exec"}
FORBIDDEN_ATTR_CALLS = {("os", "system")}


class CptSecurityTests(unittest.TestCase):
    def test_cpt_sources_have_no_forbidden_imports_or_calls(self) -> None:
        offenders: list[str] = []

        for path in sorted(CPT_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden_import(alias.name):
                            offenders.append(f"{path.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if _is_forbidden_import(module):
                        offenders.append(f"{path.name}: from {module}")
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                        offenders.append(f"{path.name}: call {node.func.id}")
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        pair = (node.func.value.id, node.func.attr)
                        if pair in FORBIDDEN_ATTR_CALLS:
                            offenders.append(f"{path.name}: call {pair[0]}.{pair[1]}")

        self.assertEqual([], offenders)

    def test_importing_cpt_does_not_import_forbidden_runtime_modules(self) -> None:
        before = set(sys.modules)
        importlib.import_module("runtime.cpt")
        importlib.import_module("runtime.cpt.transformer")
        importlib.import_module("runtime.cpt.audit")
        after = set(sys.modules)

        newly_loaded = after - before
        offenders = sorted(module for module in newly_loaded if _is_forbidden_import(module))

        self.assertEqual([], offenders)


def _is_forbidden_import(module_name: str) -> bool:
    return any(module_name == forbidden or module_name.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_IMPORTS)


if __name__ == "__main__":
    unittest.main()
