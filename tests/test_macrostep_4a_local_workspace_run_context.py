from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety import dry_run_artifact_integration
from runtime.safety.local_agent_entrypoint import run_durable_local_agent_entrypoint
from runtime.safety.local_workspace_run_context import (
    LocalWorkspaceRunContext,
    local_workspace_run_context_to_dict,
    prepare_local_workspace_run_context,
    run_durable_local_agent_in_workspace,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_CONTEXT_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_workspace_run_context.py",
)


class Macrostep4ALocalWorkspaceRunContextTests(unittest.TestCase):
    def test_workspace_context_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(prepare_local_workspace_run_context))
        self.assertTrue(callable(run_durable_local_agent_in_workspace))

    def test_workspace_context_requires_absolute_base_workspace_root(self) -> None:
        with self.assertRaises(ValueError):
            prepare_local_workspace_run_context(base_workspace_root="relative-workspace")
        with self.assertRaises(ValueError):
            prepare_local_workspace_run_context(base_workspace_root="")

    def test_workspace_context_creates_fixed_layout(self) -> None:
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base, run_id="run_001")

            self.assertIsInstance(context, LocalWorkspaceRunContext)
            self.assertTrue(context.prepared)
            self.assertEqual(Path(context.run_root), Path(base) / "runs" / "run_001")
            self.assertEqual(Path(context.artifact_workspace_root), Path(context.run_root) / "artifacts")
            self.assertEqual(Path(context.audit_dir), Path(context.run_root) / "audit")
            self.assertTrue(Path(context.artifact_workspace_root).is_dir())
            self.assertTrue(Path(context.audit_dir).is_dir())

    def test_workspace_context_generates_safe_run_id_when_missing(self) -> None:
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base)

        self.assertRegex(context.run_id, r"^[a-z0-9_-]{1,64}$")
        self.assertEqual(len(context.run_id), 32)

    def test_workspace_context_accepts_valid_caller_run_id(self) -> None:
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base, run_id="run_abc-123")

        self.assertEqual(context.run_id, "run_abc-123")

    def test_workspace_context_rejects_existing_run_directory_by_default(self) -> None:
        with TemporaryDirectory() as base:
            prepare_local_workspace_run_context(base_workspace_root=base, run_id="duplicate_run")
            with self.assertRaises(FileExistsError):
                prepare_local_workspace_run_context(base_workspace_root=base, run_id="duplicate_run")

    def test_workspace_context_result_serializes_to_dict(self) -> None:
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base, run_id="serializable_run")

        serialized = local_workspace_run_context_to_dict(context)
        self.assertIsInstance(serialized, dict)
        self.assertTrue(serialized["prepared"])
        self.assertEqual(serialized["run_id"], "serializable_run")
        self.assertEqual(serialized["default_relative_output_path"], "aoia_agent_v0_result.md")

    def test_workspace_context_runs_macrostep_3a_durable_entrypoint(self) -> None:
        with TemporaryDirectory() as base:
            result = run_durable_local_agent_in_workspace(
                goal="Create a workspace-context durable artifact.",
                base_workspace_root=base,
                run_id="entrypoint_run",
            )

            artifact_path = Path(result.artifact_path or "")
            audit_log_path = Path(result.audit_log_path or "")

            self.assertTrue(result.completed)
            self.assertTrue(result.durable_audit_completed)
            self.assertTrue(result.artifact_write_completed)
            self.assertTrue(audit_log_path.is_file())
            self.assertEqual(audit_log_path, Path(base) / "runs" / "entrypoint_run" / "audit" / "events.jsonl")
            self.assertTrue(artifact_path.is_file())
            self.assertTrue(str(artifact_path).startswith(str(Path(base) / "runs" / "entrypoint_run" / "artifacts")))

    def test_workspace_context_preserves_macrostep_3a_entrypoint_behavior(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = run_durable_local_agent_entrypoint(
                goal="Create a direct 3A artifact.",
                workspace_root=workspace,
                audit_dir=audit_dir,
            )

        self.assertTrue(result.completed)

    def test_workspace_context_does_not_call_old_non_durable_path(self) -> None:
        with TemporaryDirectory() as base:
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("old non-durable path must not be called"),
            ):
                result = run_durable_local_agent_in_workspace(
                    goal="Create a durable workspace artifact.",
                    base_workspace_root=base,
                    run_id="durable_only_run",
                )

        self.assertTrue(result.completed)

    def test_workspace_context_runtime_does_not_call_forbidden_capabilities(self) -> None:
        forbidden_modules = {
            "subprocess",
            "pty",
            "pexpect",
            "requests",
            "urllib",
            "http.client",
            "socket",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "google.cloud",
            "google.generativeai",
            "dotenv",
            "sqlite3",
            "shutil",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "safe_file_writer",
            "workspace_registry",
            "run_dry_run_agent_and_write_artifact(",
        )
        for source_file in WORKSPACE_CONTEXT_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            self.assertNotRegex(source, re.compile(r"\brun_dry_run_agent_and_write_artifact\s*\("))
            for term in forbidden_text:
                self.assertNotIn(term, source)
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            for module_name in imports:
                self.assertNotIn(module_name, forbidden_modules)
                self.assertFalse(any(module_name == item or module_name.startswith(item + ".") for item in forbidden_modules))


if __name__ == "__main__":
    unittest.main()
