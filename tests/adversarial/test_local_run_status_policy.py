from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety import audit_event_logger, sandbox_artifact_runner
from runtime.safety.local_run_status import MAX_LOCAL_RUN_STATUS_AUDIT_LOG_BYTES, read_local_run_status
from runtime.safety.local_workspace_run_context import run_durable_local_agent_in_workspace


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_STATUS_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_run_status.py",
)


class LocalRunStatusPolicyTests(unittest.TestCase):
    def test_relative_base_workspace_root_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            read_local_run_status(base_workspace_root="relative-base", run_id="run_1")

    def test_unsafe_run_ids_are_rejected(self) -> None:
        unsafe_run_ids = (
            "nested/run",
            "nested\\run",
            "..",
            "run.id",
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
                        read_local_run_status(base_workspace_root=base, run_id=run_id)

    def test_symlink_run_root_escape_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as base, TemporaryDirectory() as outside:
            runs = Path(base) / "runs"
            runs.mkdir()
            try:
                (runs / "linked_run").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this platform: {exc}")

            with self.assertRaises(ValueError):
                read_local_run_status(base_workspace_root=base, run_id="linked_run")

    def test_symlink_audit_log_escape_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as base, TemporaryDirectory() as outside:
            audit = Path(base) / "runs" / "audit_link_run" / "audit"
            artifacts = Path(base) / "runs" / "audit_link_run" / "artifacts"
            audit.mkdir(parents=True)
            artifacts.mkdir()
            outside_log = Path(outside) / "events.jsonl"
            try:
                (audit / "events.jsonl").symlink_to(outside_log)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this platform: {exc}")

            with self.assertRaises(ValueError):
                read_local_run_status(base_workspace_root=base, run_id="audit_link_run")

    def test_symlink_artifact_dir_escape_is_rejected_when_supported(self) -> None:
        with TemporaryDirectory() as base, TemporaryDirectory() as outside:
            run_root = Path(base) / "runs" / "artifact_link_run"
            audit = run_root / "audit"
            audit.mkdir(parents=True)
            (audit / "events.jsonl").write_text("", encoding="utf-8")
            try:
                (run_root / "artifacts").symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this platform: {exc}")

            with self.assertRaises(ValueError):
                read_local_run_status(base_workspace_root=base, run_id="artifact_link_run")

    def test_malformed_jsonl_is_reported_invalid_without_repair(self) -> None:
        with TemporaryDirectory() as base:
            audit = Path(base) / "runs" / "malformed_run" / "audit"
            artifacts = Path(base) / "runs" / "malformed_run" / "artifacts"
            audit.mkdir(parents=True)
            artifacts.mkdir()
            log_path = audit / "events.jsonl"
            log_path.write_text("{not-json}\n", encoding="utf-8")

            before = log_path.read_text(encoding="utf-8")
            status = read_local_run_status(base_workspace_root=base, run_id="malformed_run")
            after = log_path.read_text(encoding="utf-8")

        self.assertFalse(status.read_successful)
        self.assertFalse(status.hash_chain_valid)
        self.assertFalse(status.run_complete)
        self.assertEqual(before, after)

    def test_oversized_audit_log_is_reported_too_large_without_read_repair(self) -> None:
        with TemporaryDirectory() as base:
            audit = Path(base) / "runs" / "oversized_run" / "audit"
            artifacts = Path(base) / "runs" / "oversized_run" / "artifacts"
            audit.mkdir(parents=True)
            artifacts.mkdir()
            log_path = audit / "events.jsonl"
            log_path.write_text("x" * (MAX_LOCAL_RUN_STATUS_AUDIT_LOG_BYTES + 1), encoding="utf-8")

            before_size = log_path.stat().st_size
            status = read_local_run_status(base_workspace_root=base, run_id="oversized_run")
            after_size = log_path.stat().st_size

        self.assertFalse(status.read_successful)
        self.assertIn("too large", status.reason)
        self.assertEqual(before_size, after_size)

    def test_read_only_status_does_not_create_missing_directories_or_files(self) -> None:
        with TemporaryDirectory() as base:
            read_local_run_status(base_workspace_root=base, run_id="missing_policy_run")

            self.assertFalse((Path(base) / "runs").exists())

    def test_write_functions_are_not_called_by_status_reader(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a status reader artifact.",
                base_workspace_root=base,
                run_id="no_write_calls_run",
            )
            with patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("status reader must not append audit events"),
            ), patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("status reader must not write artifacts"),
            ):
                status = read_local_run_status(base_workspace_root=base, run_id="no_write_calls_run")

        self.assertTrue(status.read_successful)
        self.assertTrue(status.run_complete)

    def test_hash_chain_missing_event_hash_is_invalid(self) -> None:
        with TemporaryDirectory() as base:
            audit = Path(base) / "runs" / "missing_hash_run" / "audit"
            artifacts = Path(base) / "runs" / "missing_hash_run" / "artifacts"
            audit.mkdir(parents=True)
            artifacts.mkdir()
            (audit / "events.jsonl").write_text(json.dumps({"previous_event_hash": ""}) + "\n", encoding="utf-8")

            status = read_local_run_status(base_workspace_root=base, run_id="missing_hash_run")

        self.assertFalse(status.hash_chain_valid)
        self.assertFalse(status.run_complete)

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
            "append_audit_event_jsonl(",
            "write_sandbox_artifact(",
            "mkdir(",
            "write_text(",
            "open(",
        )
        for source_file in RUN_STATUS_RUNTIME_FILES:
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
