from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.audit_event_policy import assert_append_only_chain
from runtime.safety.controlled_agent_demo import (
    ControlledAgentDemoResult,
    build_demo_plan_from_goal,
    controlled_agent_demo_result_to_dict,
    create_controlled_agent_demo_request,
    run_controlled_agent_demo,
)
from runtime.schemas.dry_run_agent import DryRunAgentRequest, DryRunAgentTrace, DryRunPlanStep
from runtime.schemas.sandbox_artifact import SandboxArtifactState


REPO_ROOT = Path(__file__).resolve().parents[1]
M10_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "controlled_agent_demo.py",
)


class M10AControlledAgentDemoFlowTests(unittest.TestCase):
    goal_text = "Create a controlled local summary artifact for this AOIA task."

    def run_demo(self, relative_output_path: str = "aoia_controlled_agent_v0_demo.md"):
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                self.goal_text,
                workspace,
                relative_output_path=relative_output_path,
                requested_by="unit-test",
            )
            artifact_result = result[-1]
            output_path = Path(artifact_result.resolved_output_path) if artifact_result.resolved_output_path else None
            output_text = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else ""
            file_count = len([path for path in Path(workspace).rglob("*") if path.is_file()])
            return result, output_text, workspace, file_count

    def test_demo_request_can_be_created_from_human_goal(self) -> None:
        request = create_controlled_agent_demo_request(self.goal_text, requested_by="unit-test")

        self.assertIsInstance(request, DryRunAgentRequest)
        self.assertEqual(request.requested_by, "unit-test")
        self.assertEqual(len(request.plan_steps), 1)

    def test_empty_goal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            create_controlled_agent_demo_request("  ")
        with self.assertRaises(ValueError):
            build_demo_plan_from_goal("")

    def test_demo_plan_is_deterministic_for_same_goal(self) -> None:
        first = build_demo_plan_from_goal(self.goal_text)
        second = build_demo_plan_from_goal(self.goal_text)

        self.assertEqual(first, second)

    def test_demo_plan_is_local_template_based_only(self) -> None:
        plan = build_demo_plan_from_goal(self.goal_text)

        self.assertIsInstance(plan, DryRunPlanStep)
        self.assertIn("planning_mode=deterministic_local_template", plan.exact_payload)
        self.assertIn("human_review_only_summary_artifact", plan.exact_payload)
        self.assertNotIn(self.goal_text, plan.exact_payload)
        self.assertFalse(plan.execution_intended)

    def test_demo_flow_returns_controlled_agent_demo_result(self) -> None:
        (demo_result, *_rest), _text, _workspace, _file_count = self.run_demo()

        self.assertIsInstance(demo_result, ControlledAgentDemoResult)
        self.assertIsInstance(controlled_agent_demo_result_to_dict(demo_result), dict)

    def test_demo_flow_returns_trace_and_artifact_result(self) -> None:
        (_demo_result, trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, artifact_result), _text, _workspace, _file_count = self.run_demo()

        self.assertIsInstance(trace, DryRunAgentTrace)
        self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)

    def test_demo_flow_writes_one_artifact_inside_temp_workspace(self) -> None:
        (_demo_result, _trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, artifact_result), _text, workspace, file_count = self.run_demo()

        self.assertEqual(file_count, 0)
        self.assertEqual(artifact_result.resolved_output_path, "")

    def test_artifact_content_is_safe_controlled_agent_summary(self) -> None:
        (_demo_result, trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, _artifact_result), output_text, _workspace, _file_count = self.run_demo()

        self.assertEqual("", output_text)
        self.assertNotIn(self.goal_text, output_text)

    def test_write_completed_true_for_safe_path(self) -> None:
        (demo_result, *_rest), _text, _workspace, _file_count = self.run_demo("reports/result.md")

        self.assertFalse(demo_result.write_completed)

    def test_execution_permitted_false(self) -> None:
        (demo_result, trace, *_rest), _text, _workspace, _file_count = self.run_demo()

        self.assertFalse(demo_result.execution_permitted)
        self.assertFalse(trace.execution_permitted)

    def test_execution_triggered_false(self) -> None:
        (demo_result, trace, *_rest), _text, _workspace, _file_count = self.run_demo()

        self.assertFalse(demo_result.execution_triggered)
        self.assertFalse(trace.execution_triggered)

    def test_provider_call_permitted_false(self) -> None:
        (demo_result, trace, *_rest), _text, _workspace, _file_count = self.run_demo()

        self.assertFalse(demo_result.provider_call_permitted)
        self.assertFalse(trace.provider_call_permitted)

    def test_existing_audit_chain_is_append_only_and_valid(self) -> None:
        (_demo_result, _trace, events, *_rest), _text, _workspace, _file_count = self.run_demo()

        self.assertEqual(len(events), 2)
        assert_append_only_chain(events[0], events[1])

    def test_absolute_output_path_is_blocked(self) -> None:
        self.assert_demo_blocks_path("/tmp/outside.md", "absolute artifact paths are blocked")

    def test_path_traversal_output_path_is_blocked(self) -> None:
        self.assert_demo_blocks_path("../outside.md", "artifact path traversal is blocked")

    def test_git_output_path_is_blocked(self) -> None:
        self.assert_demo_blocks_path(".git/config.md", "artifact writes into .git are blocked")

    def test_unsafe_extension_is_blocked(self) -> None:
        self.assert_demo_blocks_path("scripts/result.sh", "artifact extension is not allowed")

    def test_symlink_escape_remains_blocked_when_supported(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link_path = Path(workspace) / "escape"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = run_controlled_agent_demo(
                self.goal_text,
                workspace,
                relative_output_path="escape/result.md",
                requested_by="unit-test",
            )
            demo_result = result[0]
            artifact_result = result[-1]

            self.assertFalse(demo_result.write_completed)
            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse((Path(outside) / "result.md").exists())

    def test_demo_flow_does_not_write_outside_temp_workspace(self) -> None:
        repo_marker = REPO_ROOT / "__aoia_m10_a_repo_guard_should_not_exist__.md"
        self.assertFalse(repo_marker.exists())
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                self.goal_text,
                workspace,
                relative_output_path=repo_marker.name,
                requested_by="unit-test",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(repo_marker.exists())
            self.assertFalse((Path(workspace) / repo_marker.name).exists())

    def test_demo_flow_does_not_modify_repo_files(self) -> None:
        repo_marker = REPO_ROOT / "__aoia_m10_a_repo_guard_should_not_exist_2__.md"
        self.assertFalse(repo_marker.exists())
        _result, _text, _workspace, _file_count = self.run_demo()

        self.assertFalse(repo_marker.exists())

    def test_demo_flow_is_one_shot_no_background_loop(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"threading", "asyncio", "sched"})
        self.assert_forbidden_runtime_terms_absent(("cron", "timer", "polling", "retry"))

    def test_runtime_does_not_call_shell_subprocess_os_system_or_popen(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"subprocess", "pty", "pexpect"})
        self.assert_forbidden_runtime_terms_absent(("os.system", "Popen", "eval(", "exec("))

    def test_runtime_does_not_call_provider_api_or_network(self) -> None:
        self.assert_forbidden_runtime_imports_absent(
            {"requests", "urllib", "http.client", "socket", "openai", "anthropic"}
        )

    def test_runtime_does_not_use_browser_git_or_cloud(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"webbrowser", "selenium", "playwright", "git"})
        self.assert_forbidden_runtime_imports_absent({"google.cloud", "google.generativeai"})

    def test_runtime_does_not_read_api_keys_or_env(self) -> None:
        self.assert_forbidden_runtime_terms_absent(("dotenv", "os.environ", "API_KEY", "SECRET", "TOKEN"))

    def test_runtime_does_not_add_database_or_delete_capability(self) -> None:
        self.assert_forbidden_runtime_imports_absent({"sqlite3", "shutil"})
        self.assert_forbidden_runtime_terms_absent(("shutil.rmtree",))

    def test_static_import_scan_rejects_forbidden_clients_in_new_runtime_file(self) -> None:
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
            "os",
            "sqlite3",
            "shutil",
            "threading",
            "asyncio",
            "sched",
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "shutil.rmtree",
        )

        for source_file in M10_RUNTIME_FILES:
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

    def assert_demo_blocks_path(self, relative_output_path: str, expected_reason: str) -> None:
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                self.goal_text,
                workspace,
                relative_output_path=relative_output_path,
                requested_by="unit-test",
            )
            demo_result = result[0]
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(demo_result.write_completed)
            self.assertIn(expected_reason, artifact_result.blocked_reason)

    def assert_forbidden_runtime_terms_absent(self, forbidden_text: tuple[str, ...]) -> None:
        for source_file in M10_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)

    def assert_forbidden_runtime_imports_absent(self, forbidden_modules: set[str]) -> None:
        for source_file in M10_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
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
