from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.local_workspace_run_context import (
    MAX_LOCAL_RUN_ID_CHARS,
    prepare_local_workspace_run_context,
    run_durable_local_agent_in_workspace,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_CONTEXT_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_workspace_run_context.py",
)


class LocalWorkspaceRunContextPolicyTests(unittest.TestCase):
    def test_relative_base_workspace_root_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            prepare_local_workspace_run_context(base_workspace_root="relative-base")

    def test_base_workspace_root_control_or_null_character_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            prepare_local_workspace_run_context(base_workspace_root="/tmp/aoia\x00workspace")
        with self.assertRaises(ValueError):
            prepare_local_workspace_run_context(base_workspace_root="/tmp/aoia\x1fworkspace")

    def test_unsafe_run_ids_are_rejected(self) -> None:
        unsafe_run_ids = (
            "nested/run",
            "nested\\run",
            "..",
            "run..id",
            "run id",
            "run\nid",
            "run;id",
            "run$id",
            "run*id",
            "RunUppercase",
        )
        with TemporaryDirectory() as base:
            for run_id in unsafe_run_ids:
                with self.subTest(run_id=run_id):
                    with self.assertRaises(ValueError):
                        prepare_local_workspace_run_context(base_workspace_root=base, run_id=run_id)

    def test_run_id_over_maximum_length_is_rejected(self) -> None:
        with TemporaryDirectory() as base:
            with self.assertRaises(ValueError):
                prepare_local_workspace_run_context(
                    base_workspace_root=base,
                    run_id="a" * (MAX_LOCAL_RUN_ID_CHARS + 1),
                )

    def test_symlink_base_workspace_root_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as parent:
            real_base = Path(parent) / "real"
            symlink_base = Path(parent) / "linked"
            real_base.mkdir()
            try:
                symlink_base.symlink_to(real_base, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this platform: {exc}")

            with self.assertRaises(ValueError):
                prepare_local_workspace_run_context(base_workspace_root=symlink_base)

    def test_symlink_runs_directory_escape_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as parent, TemporaryDirectory() as outside:
            base = Path(parent) / "base"
            base.mkdir()
            try:
                (base / "runs").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this platform: {exc}")

            with self.assertRaises(ValueError):
                prepare_local_workspace_run_context(base_workspace_root=base, run_id="blocked_symlink_run")

    def test_created_audit_and_artifact_directories_stay_inside_run_root(self) -> None:
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base, run_id="contained_run")

            run_root = Path(context.run_root).resolve()
            artifact_root = Path(context.artifact_workspace_root).resolve()
            audit_dir = Path(context.audit_dir).resolve()

            self.assertTrue(str(artifact_root).startswith(str(run_root)))
            self.assertTrue(str(audit_dir).startswith(str(run_root)))
            self.assertEqual(artifact_root.parent, run_root)
            self.assertEqual(audit_dir.parent, run_root)

    def test_artifact_output_cannot_escape_run_artifacts_directory(self) -> None:
        with TemporaryDirectory() as base:
            with self.assertRaises(ValueError):
                prepare_local_workspace_run_context(
                    base_workspace_root=base,
                    run_id="escape_output_run",
                    default_relative_output_path="../escape.md",
                )

            result = run_durable_local_agent_in_workspace(
                goal="Create a contained artifact.",
                base_workspace_root=base,
                run_id="contained_artifact_run",
            )

            artifact_path = Path(result.artifact_path or "").resolve()
            expected_root = (Path(base) / "runs" / "contained_artifact_run" / "artifacts").resolve()
            self.assertTrue(str(artifact_path).startswith(str(expected_root)))

    def test_duplicate_run_id_is_rejected_by_default(self) -> None:
        with TemporaryDirectory() as base:
            prepare_local_workspace_run_context(base_workspace_root=base, run_id="duplicate_policy_run")
            with self.assertRaises(FileExistsError):
                prepare_local_workspace_run_context(base_workspace_root=base, run_id="duplicate_policy_run")

    def test_no_registry_database_file_is_created(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a durable artifact without registry files.",
                base_workspace_root=base,
                run_id="no_registry_run",
            )

            created_files = {path.name for path in Path(base).rglob("*") if path.is_file()}

        forbidden_file_names = {
            "workspace_registry.json",
            "registry.json",
            "index.json",
            "workspace.db",
            "workspace.sqlite",
            "workspace.sqlite3",
        }
        self.assertTrue(created_files)
        self.assertTrue(forbidden_file_names.isdisjoint(created_files))

    def test_no_safe_file_writer_or_workspace_registry_is_introduced(self) -> None:
        source = (REPO_ROOT / "runtime" / "safety" / "local_workspace_run_context.py").read_text(encoding="utf-8")

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
            "safe_file_writer",
            "workspace_registry",
        )
        for source_file in WORKSPACE_CONTEXT_RUNTIME_FILES:
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
