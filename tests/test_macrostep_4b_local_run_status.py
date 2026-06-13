from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.local_run_status import (
    LocalRunStatus,
    local_run_status_to_dict,
    read_local_run_status,
)
from runtime.safety.local_workspace_run_context import run_durable_local_agent_in_workspace


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_STATUS_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_run_status.py",
)


class Macrostep4BLocalRunStatusTests(unittest.TestCase):
    def test_run_status_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(read_local_run_status))

    def test_run_status_accepts_absolute_base_and_run_id(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a run status artifact.",
                base_workspace_root=base,
                run_id="status_run",
            )

            status = read_local_run_status(base_workspace_root=base, run_id="status_run")

        self.assertIsInstance(status, LocalRunStatus)
        self.assertTrue(status.read_successful)
        self.assertEqual(status.run_id, "status_run")

    def test_run_status_rejects_missing_or_empty_run_id(self) -> None:
        with TemporaryDirectory() as base:
            with self.assertRaises(ValueError):
                read_local_run_status(base_workspace_root=base, run_id="")
            with self.assertRaises(TypeError):
                read_local_run_status(base_workspace_root=base, run_id=None)

    def test_run_status_reads_expected_layout(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a layout status artifact.",
                base_workspace_root=base,
                run_id="layout_run",
            )

            status = read_local_run_status(
                base_workspace_root=base,
                run_id="layout_run",
                expected_artifact_filename="aoia_agent_v0_result.md",
            )

            self.assertEqual(Path(status.run_root), Path(base) / "runs" / "layout_run")
            self.assertEqual(Path(status.artifacts_dir), Path(status.run_root) / "artifacts")
            self.assertEqual(Path(status.audit_dir), Path(status.run_root) / "audit")
            self.assertEqual(Path(status.audit_log_path), Path(status.audit_dir) / "events.jsonl")
            self.assertTrue(status.expected_artifact_exists)

    def test_missing_run_is_incomplete_without_creation(self) -> None:
        with TemporaryDirectory() as base:
            status = read_local_run_status(base_workspace_root=base, run_id="missing_run")

            self.assertFalse(status.run_complete)
            self.assertFalse(status.audit_log_exists)
            self.assertEqual(status.event_count, 0)
            self.assertFalse((Path(base) / "runs").exists())

    def test_missing_audit_log_is_incomplete_without_creation(self) -> None:
        with TemporaryDirectory() as base:
            run_root = Path(base) / "runs" / "partial_run"
            artifacts = run_root / "artifacts"
            audit = run_root / "audit"
            artifacts.mkdir(parents=True)
            audit.mkdir()

            before = self.snapshot(base)
            status = read_local_run_status(base_workspace_root=base, run_id="partial_run")
            after = self.snapshot(base)

            self.assertFalse(status.run_complete)
            self.assertFalse(status.audit_log_exists)
            self.assertEqual(status.event_count, 0)
            self.assertEqual(before, after)

    def test_missing_artifacts_dir_is_incomplete_without_creation(self) -> None:
        with TemporaryDirectory() as base:
            run_root = Path(base) / "runs" / "no_artifacts_run"
            audit = run_root / "audit"
            audit.mkdir(parents=True)
            (audit / "events.jsonl").write_text("", encoding="utf-8")

            before = self.snapshot(base)
            status = read_local_run_status(base_workspace_root=base, run_id="no_artifacts_run")
            after = self.snapshot(base)

            self.assertFalse(status.run_complete)
            self.assertEqual(status.artifact_count, 0)
            self.assertEqual(before, after)
            self.assertFalse((run_root / "artifacts").exists())

    def test_run_status_reports_event_count_and_artifact_count(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a countable run status artifact.",
                base_workspace_root=base,
                run_id="count_run",
            )

            status = read_local_run_status(base_workspace_root=base, run_id="count_run")

        self.assertGreaterEqual(status.event_count, 1)
        self.assertEqual(status.artifact_count, 1)

    def test_run_status_validates_audit_hash_chain(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a hash-chain status artifact.",
                base_workspace_root=base,
                run_id="hash_chain_run",
            )
            status = read_local_run_status(base_workspace_root=base, run_id="hash_chain_run")

            audit_log = Path(status.audit_log_path)
            lines = audit_log.read_text(encoding="utf-8").splitlines()
            decoded = [json.loads(line) for line in lines if line.strip()]
            if len(decoded) < 2:
                self.skipTest("durable flow produced fewer than two audit events")
            decoded[1]["previous_event_hash"] = "wrong"
            audit_log.write_text("\n".join(json.dumps(item, sort_keys=True) for item in decoded) + "\n", encoding="utf-8")

            broken_status = read_local_run_status(base_workspace_root=base, run_id="hash_chain_run")

        self.assertTrue(status.hash_chain_valid)
        self.assertFalse(broken_status.hash_chain_valid)
        self.assertFalse(broken_status.run_complete)

    def test_run_status_result_serializes_to_dict(self) -> None:
        with TemporaryDirectory() as base:
            status = read_local_run_status(base_workspace_root=base, run_id="missing_serializable_run")

        serialized = local_run_status_to_dict(status)
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["run_id"], "missing_serializable_run")
        self.assertFalse(serialized["run_complete"])

    def test_run_status_does_not_mutate_filesystem(self) -> None:
        with TemporaryDirectory() as base:
            run_durable_local_agent_in_workspace(
                goal="Create a read-only status artifact.",
                base_workspace_root=base,
                run_id="readonly_run",
            )
            before = self.snapshot(base)
            read_local_run_status(base_workspace_root=base, run_id="readonly_run")
            after = self.snapshot(base)

        self.assertEqual(before, after)

    def test_run_status_runtime_does_not_call_forbidden_capabilities(self) -> None:
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
            "write_sandbox_artifact(",
            "append_audit_event_jsonl(",
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

    def snapshot(self, base: str) -> dict[str, tuple[int, int]]:
        root = Path(base)
        return {
            str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
            for path in sorted(root.rglob("*"))
            if path.exists()
        }


if __name__ == "__main__":
    unittest.main()
