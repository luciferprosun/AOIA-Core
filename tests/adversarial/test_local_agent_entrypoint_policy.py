from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety import dry_run_artifact_integration
from runtime.safety import local_agent_entrypoint
from runtime.safety.audit_event_logger import AuditLogWriteBlockedError


REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_agent_entrypoint.py",
)


class LocalAgentEntrypointPolicyTests(unittest.TestCase):
    def test_empty_goal_is_rejected(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="  ",
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                )

    def test_goal_over_maximum_length_is_rejected(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="x" * (local_agent_entrypoint.MAX_LOCAL_AGENT_GOAL_CHARS + 1),
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                )

    def test_goal_control_characters_are_rejected_except_tab_and_newline(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="create\x00artifact",
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                )
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="create\x1fartifact",
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                )

            result = local_agent_entrypoint.run_durable_local_agent_entrypoint(
                goal="create\tartifact\nsummary",
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path="allowed-control.md",
            )

        self.assertTrue(result.completed)

    def test_relative_workspace_path_is_rejected(self) -> None:
        with TemporaryDirectory() as audit_dir:
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="Create an artifact.",
                    workspace_root="relative-workspace",
                    audit_dir=audit_dir,
                )

    def test_relative_audit_dir_is_rejected(self) -> None:
        with TemporaryDirectory() as workspace:
            with self.assertRaises(ValueError):
                local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="Create an artifact.",
                    workspace_root=workspace,
                    audit_dir="relative-audit",
                )

    def test_audit_failure_blocks_artifact_creation(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            artifact_path = Path(workspace) / "blocked.md"
            with patch.object(
                dry_run_artifact_integration,
                "append_audit_event_jsonl",
                side_effect=AuditLogWriteBlockedError("simulated durable append failure"),
            ):
                with self.assertRaises(AuditLogWriteBlockedError):
                    local_agent_entrypoint.run_durable_local_agent_entrypoint(
                        goal="Create an artifact.",
                        workspace_root=workspace,
                        audit_dir=audit_dir,
                        relative_output_path=artifact_path.name,
                    )

            self.assertFalse(artifact_path.exists())
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_entrypoint_does_not_call_old_non_durable_function(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("old non-durable path must not be called"),
            ):
                result = local_agent_entrypoint.run_durable_local_agent_entrypoint(
                    goal="Create a durable artifact.",
                    workspace_root=workspace,
                    audit_dir=audit_dir,
                )

        self.assertTrue(result.completed)

    def test_old_non_durable_function_still_exists_but_is_not_imported_by_entrypoint(self) -> None:
        self.assertTrue(hasattr(dry_run_artifact_integration, "run_dry_run_agent_and_write_artifact"))
        source = (REPO_ROOT / "runtime" / "safety" / "local_agent_entrypoint.py").read_text(encoding="utf-8")
        self.assertNotIn("run_dry_run_agent_and_write_artifact(", source)
        self.assertIn("run_dry_run_agent_and_write_artifact_with_durable_audit", source)

    def test_no_safe_file_writer_or_workspace_registry_is_introduced(self) -> None:
        source = (REPO_ROOT / "runtime" / "safety" / "local_agent_entrypoint.py").read_text(encoding="utf-8")

        self.assertNotIn("safe_file_writer", source)
        self.assertNotIn("workspace_registry", source)

    def test_no_forbidden_runtime_capability_is_introduced(self) -> None:
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
        )
        for source_file in ENTRYPOINT_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
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
