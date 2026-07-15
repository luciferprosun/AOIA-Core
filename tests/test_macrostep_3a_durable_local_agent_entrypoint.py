from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.local_agent_entrypoint import (
    LocalAgentEntrypointResult,
    local_agent_entrypoint_result_to_dict,
    run_durable_local_agent_entrypoint,
)
from runtime.safety.dry_run_artifact_integration import run_dry_run_agent_and_write_artifact
from runtime.safety.controlled_agent_demo import run_controlled_agent_demo
from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.dry_run_agent import create_dry_run_agent_request, create_dry_run_plan_step
from runtime.schemas.sandbox_artifact import SandboxArtifactState


REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "local_agent_entrypoint.py",
)


class Macrostep3ADurableLocalAgentEntrypointTests(unittest.TestCase):
    def test_entrypoint_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(run_durable_local_agent_entrypoint))

    def test_entrypoint_accepts_non_empty_human_goal(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = run_durable_local_agent_entrypoint(
                goal="Create a durable local controlled-agent artifact.",
                workspace_root=Path(workspace),
                audit_dir=Path(audit_dir),
            )

        self.assertIsInstance(result, LocalAgentEntrypointResult)
        self.assertFalse(result.completed)

    def test_entrypoint_requires_explicit_workspace_root(self) -> None:
        with TemporaryDirectory() as audit_dir:
            with self.assertRaises(ValueError):
                run_durable_local_agent_entrypoint(
                    goal="Create an artifact.",
                    workspace_root="",
                    audit_dir=audit_dir,
                )

    def test_entrypoint_requires_explicit_audit_directory(self) -> None:
        with TemporaryDirectory() as workspace:
            with self.assertRaises(ValueError):
                run_durable_local_agent_entrypoint(
                    goal="Create an artifact.",
                    workspace_root=workspace,
                    audit_dir="",
                )

    def test_entrypoint_requires_absolute_workspace_and_audit_paths(self) -> None:
        with self.assertRaises(ValueError):
            run_durable_local_agent_entrypoint(
                goal="Create an artifact.",
                workspace_root="relative-workspace",
                audit_dir="/tmp/aoia-audit-test",
            )
        with self.assertRaises(ValueError):
            run_durable_local_agent_entrypoint(
                goal="Create an artifact.",
                workspace_root="/tmp/aoia-workspace-test",
                audit_dir="relative-audit",
            )

    def test_entrypoint_creates_durable_audit_log_and_workspace_artifact(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = run_durable_local_agent_entrypoint(
                goal="Create a durable local summary artifact.",
                workspace_root=workspace,
                audit_dir=audit_dir,
                relative_output_path="entrypoint-result.md",
            )
            artifact_path = Path(result.artifact_path or "")
            audit_log_path = Path(result.audit_log_path or "")

            self.assertTrue(result.durable_audit_required)
            self.assertTrue(result.durable_audit_completed)
            self.assertFalse(result.artifact_write_completed)
            self.assertTrue(audit_log_path.is_file())
            self.assertEqual(audit_log_path.name, "events.jsonl")
            self.assertIsNone(result.artifact_path)

    def test_entrypoint_result_serializes_to_dict(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = run_durable_local_agent_entrypoint(
                goal="Create a serializable entrypoint result.",
                workspace_root=workspace,
                audit_dir=audit_dir,
            )

        serialized = local_agent_entrypoint_result_to_dict(result)
        self.assertIsInstance(serialized, dict)
        self.assertFalse(serialized["completed"])
        self.assertTrue(serialized["durable_audit_required"])

    def test_entrypoint_preserves_existing_m9_behavior(self) -> None:
        request = self.make_request()
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(request, workspace)
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)

    def test_entrypoint_preserves_existing_m10_behavior(self) -> None:
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                "Create a controlled local summary artifact.",
                workspace,
                requested_by="unit-test",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)

    def test_entrypoint_runtime_does_not_call_forbidden_capabilities(self) -> None:
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

    def make_request(self):
        step = create_dry_run_plan_step(
            title="M9 compatibility check",
            description="Create one inert dry-run summary artifact.",
            proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
            payload_summary="m9 compatibility summary",
            exact_payload="m9_compatibility_payload=summary_only",
            step_index=0,
            step_id="macrostep-3a-m9-compatibility-step",
        )
        return create_dry_run_agent_request(
            goal_text="Create an M9 compatibility artifact.",
            requested_by="unit-test",
            plan_steps=(step,),
            run_id="macrostep-3a-m9-compatibility-run",
        )


if __name__ == "__main__":
    unittest.main()
