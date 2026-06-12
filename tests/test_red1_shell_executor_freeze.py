from __future__ import annotations

import ast
import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
SHELL_TOOLS_PATH = RUNTIME_DIR / "tools" / "shell_tools.py"
EXECUTOR_PATH = RUNTIME_DIR / "tools" / "executor.py"
LOCAL_COMMANDS_PATH = RUNTIME_DIR / "commands" / "local_commands.py"


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


class Red1ShellExecutorFreezeTests(unittest.TestCase):
    def test_shell_module_is_marked_legacy_frozen_and_not_approved(self) -> None:
        values = literal_assignments(SHELL_TOOLS_PATH)

        self.assertIs(values["LEGACY_SHELL_EXECUTOR_SURFACE"], True)
        self.assertIs(values["APPROVED_RUNTIME_SHELL_EXECUTION_FLOW"], False)
        self.assertIs(values["SHELL_EXECUTION_FROZEN"], True)

    def test_shell_execution_guard_blocks_by_default(self) -> None:
        with patch.dict(os.environ, {"AOIA_SHELL_EXECUTION_ENABLED": ""}, clear=False):
            shell_tools = import_or_reload("runtime.tools.shell_tools")

        self.assertFalse(shell_tools.AOIA_SHELL_EXECUTION_ENABLED)
        with self.assertRaisesRegex(RuntimeError, "Legacy shell/executor surface is frozen"):
            shell_tools._require_legacy_shell_execution_enabled()

    def test_shell_execute_blocks_before_execution_primitives_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            with patch.dict(os.environ, {"AOIA_SHELL_EXECUTION_ENABLED": ""}, clear=False):
                shell_tools = import_or_reload("runtime.tools.shell_tools")
                with patch.object(subprocess, "run") as subprocess_run:
                    with patch.object(subprocess, "Popen") as subprocess_popen:
                        with patch.object(os, "system") as os_system:
                            result = shell_tools.shell_execute("pwd", Path(raw_tmp))

        self.assertFalse(result["success"])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["frozen"])
        self.assertFalse(result["approved_runtime_shell_execution"])
        self.assertEqual(result["mode"], "reviewer_safe_blocked")
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["stderr"], "")
        self.assertIsNone(result["exit_code"])
        self.assertIn("allowed=True", result["message"])
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        os_system.assert_not_called()

    def test_executor_shell_path_blocks_before_shell_backend_by_default(self) -> None:
        executor = import_or_reload("runtime.tools.executor")
        memory_module = import_or_reload("runtime.tools.memory")

        with tempfile.TemporaryDirectory() as raw_tmp:
            project_dir = Path(raw_tmp) / "project"
            project_dir.mkdir()
            memory = memory_module.MemoryStore(project_dir, project_dir)
            engine = executor.ExecutionEngine(project_dir, memory)

            with patch.dict(os.environ, {"AOIA_SHELL_EXECUTION_ENABLED": ""}, clear=False):
                with patch.object(executor, "shell_execute", side_effect=AssertionError("shell_execute called")):
                    result = engine.execute(
                        {
                            "action": "shell_execute",
                            "command": "date -Iseconds",
                            "reason": "RED-1-E frozen shell regression.",
                            "requires_confirmation": False,
                        },
                        require_approval=False,
                    )

        self.assertFalse(result["success"])
        self.assertTrue(result["blocked"])
        self.assertTrue(result["frozen"])
        self.assertEqual(result["mode"], "reviewer_safe_blocked")

    def test_executor_registry_marks_shell_tool_frozen(self) -> None:
        executor = import_or_reload("runtime.tools.executor")
        engine = object.__new__(executor.ExecutionEngine)
        tools = engine._build_tool_registry()

        self.assertIn("shell_execute", tools)
        self.assertIn("Frozen legacy shell/executor surface", tools["shell_execute"].description)

    def test_allowed_true_and_classification_do_not_execute(self) -> None:
        validator = import_or_reload("runtime.tools.validator")

        with patch.object(subprocess, "run") as subprocess_run:
            with patch.object(subprocess, "Popen") as subprocess_popen:
                with patch.object(os, "system") as os_system:
                    allowed, reason = validator.validate_shell_command("printf hello")
                    decision = validator.classify_shell_command("printf hello")

        self.assertTrue(allowed)
        self.assertEqual("OK", reason)
        self.assertEqual("safe", decision.mode)
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        os_system.assert_not_called()

    def test_scemda_legacy_subprocess_path_is_blocked_by_default(self) -> None:
        local_commands = import_or_reload("commands.local_commands")

        with tempfile.TemporaryDirectory() as raw_tmp:
            project_dir = Path(raw_tmp)
            addon_dir = project_dir / "addons" / "scemda"
            addon_dir.mkdir(parents=True)
            (addon_dir / "scemda_agent_v2.py").write_text("print('blocked')\n", encoding="utf-8")
            runtime = SimpleNamespace(project_dir=project_dir)

            with patch.dict(os.environ, {"AOIA_SHELL_EXECUTION_ENABLED": ""}, clear=False):
                with patch("builtins.input", return_value=""):
                    with patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called")):
                        result = local_commands.cmd_scemda("--start 2026-01-01", runtime)

        self.assertTrue(result.handled)
        self.assertIn("frozen legacy shell/subprocess surface", result.message)
        self.assertIn("not approved by default", result.message)

    def test_rhcsa_build_legacy_subprocess_path_is_blocked_before_prompt_by_default(self) -> None:
        local_commands = import_or_reload("commands.local_commands")
        runtime = SimpleNamespace(project_dir=PROJECT_ROOT)

        with patch.dict(os.environ, {"AOIA_SHELL_EXECUTION_ENABLED": ""}, clear=False):
            with patch("builtins.input", side_effect=AssertionError("input called")):
                with patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called")):
                    result = local_commands.cmd_rhcsa("build", runtime)

        self.assertTrue(result.handled)
        self.assertIn("frozen legacy shell/subprocess tooling surface", result.message)
        self.assertIn("not approved by default", result.message)

    def test_cpt_local_transform_does_not_reach_shell_primitives(self) -> None:
        webapp = import_or_reload("runtime.webapp")

        with patch.object(subprocess, "run") as subprocess_run:
            with patch.object(subprocess, "Popen") as subprocess_popen:
                with patch.object(os, "system") as os_system:
                    payload = webapp.build_cpt_transform_payload(
                        "Review the shell freeze boundary critically.",
                        mode="balanced_critic",
                    )

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["record"]["execution_permitted"])
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        os_system.assert_not_called()

    def test_no_live_runtime_shell_surface_is_approved_by_default(self) -> None:
        forbidden_fragments = (
            "APPROVED_RUNTIME_SHELL_EXECUTION_FLOW = True",
            "SHELL_EXECUTION_FROZEN = False",
            "AOIA_SHELL_EXECUTION_ENABLED = True",
        )
        findings: list[tuple[str, str]] = []
        for path in live_runtime_code_files():
            text = path.read_text(encoding="utf-8")
            for fragment in forbidden_fragments:
                if fragment in text:
                    findings.append((str(path), fragment))

        self.assertEqual([], findings)

    def test_runtime_prompt_marks_shell_execution_as_frozen_legacy(self) -> None:
        prompt = (RUNTIME_DIR / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")

        self.assertIn("Shell execution is a frozen legacy surface", prompt)
        self.assertIn("not authorize command execution", " ".join(prompt.split()))


if __name__ == "__main__":
    unittest.main()
