from __future__ import annotations

import ast
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
FILESYSTEM_TOOLS_PATH = RUNTIME_DIR / "tools" / "filesystem_tools.py"
EXECUTOR_PATH = RUNTIME_DIR / "tools" / "executor.py"
CONTROLLED_GIT_COMMIT_PATH = RUNTIME_DIR / "git_ops" / "controlled_git_commit.py"

FILESYSTEM_ACTIONS = {
    "write_file",
    "append_file",
    "create_file",
    "create_folder",
    "move_file",
    "delete_file",
}
GIT_ACTION_TOKENS = {"git", "git_commit", "git_push", "git_reset", "git_checkout"}


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


def live_runtime_code_files() -> list[Path]:
    excluded_parts = {".venv", "__pycache__", "knowledge", "reports"}
    files: list[Path] = []
    for path in RUNTIME_DIR.rglob("*.py"):
        if any(part in excluded_parts for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


class Red1FilesystemGitSurfaceFreezeTests(unittest.TestCase):
    def test_filesystem_module_is_marked_legacy_frozen_and_not_approved(self) -> None:
        values = literal_assignments(FILESYSTEM_TOOLS_PATH)

        self.assertIs(values["LEGACY_FILESYSTEM_SURFACE"], True)
        self.assertIs(values["APPROVED_RUNTIME_FILESYSTEM_FLOW"], False)
        self.assertIs(values["FILESYSTEM_MUTATION_FROZEN"], True)

    def test_filesystem_mutation_functions_are_guarded_by_default(self) -> None:
        with patch.dict(os.environ, {"AOIA_LEGACY_FILESYSTEM_ENABLED": ""}, clear=False):
            filesystem_tools = import_or_reload("runtime.tools.filesystem_tools")

            with tempfile.TemporaryDirectory() as raw_tmp:
                root = Path(raw_tmp)
                target = root / "blocked.txt"
                folder = root / "blocked-folder"

                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.create_file(str(target), root, "blocked")
                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.write_file(str(target), "blocked", root)
                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.append_file(str(target), "blocked", root)
                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.create_folder(str(folder), root)
                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.move_file(str(target), str(root / "moved.txt"), root)
                with self.assertRaisesRegex(RuntimeError, "Legacy filesystem mutation surface is frozen"):
                    filesystem_tools.delete_file(str(target), root)

                self.assertFalse(target.exists())
                self.assertFalse(folder.exists())

    def test_executor_registry_marks_filesystem_tools_frozen(self) -> None:
        executor = import_or_reload("runtime.tools.executor")
        engine = object.__new__(executor.ExecutionEngine)
        tools = engine._build_tool_registry()

        for action in FILESYSTEM_ACTIONS:
            with self.subTest(action=action):
                self.assertIn(action, tools)
                self.assertIn("Frozen legacy filesystem surface", tools[action].description)

    def test_no_direct_git_runtime_action_is_registered(self) -> None:
        executor = import_or_reload("runtime.tools.executor")
        engine = object.__new__(executor.ExecutionEngine)
        tool_names = set(engine._build_tool_registry())

        self.assertTrue(GIT_ACTION_TOKENS.isdisjoint(tool_names))

    def test_no_live_runtime_file_or_git_surface_is_approved_by_default(self) -> None:
        forbidden_fragments = (
            "APPROVED_RUNTIME_FILESYSTEM_FLOW = True",
            "FILESYSTEM_MUTATION_FROZEN = False",
            "APPROVED_RUNTIME_GIT_FLOW = True",
            "GIT_OPERATION_FROZEN = False",
            "AOIA_LEGACY_FILESYSTEM_ENABLED = True",
            "AOIA_LEGACY_GIT_ENABLED = True",
            "git push",
            "git commit",
            "git reset",
            "git checkout",
        )
        findings: list[tuple[str, str]] = []
        for path in live_runtime_code_files():
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if path == CONTROLLED_GIT_COMMIT_PATH and fragment == "git commit":
                    continue
                if fragment in text:
                    findings.append((str(path), fragment))

        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
