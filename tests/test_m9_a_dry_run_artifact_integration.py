from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.audit_event_policy import assert_append_only_chain
from runtime.safety.dry_run_artifact_integration import (
    DryRunArtifactIntegrationResult,
    build_agent_demo_artifact_content,
    create_artifact_request_from_dry_run,
    dry_run_artifact_integration_result_to_dict,
    run_dry_run_agent_and_write_artifact,
)
from runtime.safety.proposal_decision_audit_bridge import record_proposal_with_audit
from runtime.schemas.action_proposal import ActionProposalType, create_human_review_only_proposal
from runtime.schemas.dry_run_agent import (
    DryRunAgentRequest,
    DryRunAgentTrace,
    create_dry_run_agent_request,
    create_dry_run_plan_step,
)
from runtime.schemas.sandbox_artifact import SandboxArtifactRequest, SandboxArtifactState
from runtime.schemas.sandbox_contract import SandboxPolicyDecision, SandboxRequest, SandboxResult


REPO_ROOT = Path(__file__).resolve().parents[1]
M9_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "dry_run_artifact_integration.py",
)


class M9ADryRunArtifactIntegrationTests(unittest.TestCase):
    def make_request(self) -> DryRunAgentRequest:
        step = create_dry_run_plan_step(
            title="Create workspace-bound demo artifact",
            description="Represent and summarize the dry-run flow.",
            proposed_action_type=ActionProposalType.SHELL_COMMAND.value,
            payload_summary="demo payload summary only",
            exact_payload='{"command":"printf should-not-run","purpose":"m9-a"}',
            step_index=0,
            step_id="dry-run-step-m9-a",
        )
        return create_dry_run_agent_request(
            goal_text="Produce one controlled local artifact from a dry-run trace.",
            requested_by="unit-test",
            plan_steps=(step,),
            run_id="dry-run-agent-m9-a",
        )

    def run_integration(self, relative_output_path: str = "aoia_agent_v0_result.md"):
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                relative_output_path=relative_output_path,
            )
            output_path = Path(result[-1].resolved_output_path) if result[-1].resolved_output_path else None
            output_text = output_path.read_text(encoding="utf-8") if output_path and output_path.exists() else ""
            return result, output_text, workspace

    def test_integration_can_run_from_dry_run_agent_request(self) -> None:
        (integration_result, _trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, _artifact_result), _text, _workspace = self.run_integration()

        self.assertEqual(integration_result.run_id, "dry-run-agent-m9-a")

    def test_integration_returns_result_object(self) -> None:
        (integration_result, *_rest), _text, _workspace = self.run_integration()

        self.assertIsInstance(integration_result, DryRunArtifactIntegrationResult)
        self.assertIsInstance(dry_run_artifact_integration_result_to_dict(integration_result), dict)

    def test_integration_creates_dry_run_trace(self) -> None:
        (_integration_result, trace, *_rest), _text, _workspace = self.run_integration()

        self.assertIsInstance(trace, DryRunAgentTrace)
        self.assertFalse(trace.execution_triggered)

    def test_integration_creates_sandbox_request_decision_and_result(self) -> None:
        (_integration_result, _trace, _events, sandbox_request, sandbox_decision, sandbox_result, *_rest), _text, _workspace = self.run_integration()

        self.assertIsInstance(sandbox_request, SandboxRequest)
        self.assertIsInstance(sandbox_decision, SandboxPolicyDecision)
        self.assertIsInstance(sandbox_result, SandboxResult)

    def test_integration_creates_sandbox_artifact_request(self) -> None:
        (_integration_result, _trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, artifact_request, _artifact_result), _text, _workspace = self.run_integration()

        self.assertIsInstance(artifact_request, SandboxArtifactRequest)
        self.assertTrue(artifact_request.human_approved)

    def test_integration_writes_one_artifact_inside_temp_workspace(self) -> None:
        (_integration_result, _trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, artifact_result), output_text, workspace = self.run_integration()

        self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
        self.assertEqual(artifact_result.resolved_output_path, "")
        self.assertFalse(artifact_result.write_attempted)
        self.assertEqual("", output_text)

    def test_artifact_content_includes_safe_trace_summary(self) -> None:
        (_integration_result, trace, _events, _sandbox_request, _sandbox_decision, _sandbox_result, _artifact_request, _artifact_result), output_text, _workspace = self.run_integration()

        self.assertEqual("", output_text)
        self.assertNotIn("printf should-not-run", output_text)

    def test_artifact_write_completed_true_for_safe_path(self) -> None:
        (integration_result, *_rest), _text, _workspace = self.run_integration("reports/result.md")

        self.assertFalse(integration_result.write_attempted)
        self.assertFalse(integration_result.write_completed)

    def test_execution_permitted_remains_false(self) -> None:
        (integration_result, trace, *_rest), _text, _workspace = self.run_integration()

        self.assertFalse(integration_result.execution_permitted)
        self.assertFalse(trace.execution_permitted)

    def test_execution_triggered_remains_false(self) -> None:
        (integration_result, trace, *_rest), _text, _workspace = self.run_integration()

        self.assertFalse(integration_result.execution_triggered)
        self.assertFalse(trace.execution_triggered)

    def test_provider_call_permitted_remains_false(self) -> None:
        (integration_result, trace, *_rest), _text, _workspace = self.run_integration()

        self.assertFalse(integration_result.provider_call_permitted)
        self.assertFalse(trace.provider_call_permitted)

    def test_existing_audit_chain_is_not_mutated(self) -> None:
        proposal = create_human_review_only_proposal(
            title="existing",
            description="existing audit event",
            proposed_by="unit-test",
            payload_summary="summary",
            exact_payload="payload",
        )
        _bridge_result, existing_events = record_proposal_with_audit(proposal)
        original_events = existing_events
        with TemporaryDirectory() as workspace:
            _result = run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                existing_audit_events=existing_events,
            )

        self.assertEqual(existing_events, original_events)
        self.assertEqual(len(existing_events), 1)

    def test_previous_hash_chain_remains_valid(self) -> None:
        (_integration_result, _trace, events, *_rest), _text, _workspace = self.run_integration()

        self.assertEqual(len(events), 2)
        assert_append_only_chain(events[0], events[1])

    def test_absolute_artifact_path_is_blocked(self) -> None:
        self.assert_integration_blocks_path("/tmp/outside.md", "absolute artifact paths are blocked")

    def test_path_traversal_artifact_path_is_blocked(self) -> None:
        self.assert_integration_blocks_path("../outside.md", "artifact path traversal is blocked")

    def test_git_artifact_path_is_blocked(self) -> None:
        self.assert_integration_blocks_path(".git/config.md", "artifact writes into .git are blocked")

    def test_unsafe_extension_is_blocked(self) -> None:
        self.assert_integration_blocks_path("scripts/result.sh", "artifact extension is not allowed")

    def test_symlink_escape_remains_blocked_when_supported(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as outside:
            link_path = Path(workspace) / "escape"
            try:
                link_path.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            result = run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                relative_output_path="escape/result.md",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(artifact_result.write_attempted)
            self.assertFalse((Path(outside) / "result.md").exists())

    def test_create_artifact_request_from_existing_dry_run_objects(self) -> None:
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(self.make_request(), workspace)
            _integration_result, trace, _events, sandbox_request, _sandbox_decision, sandbox_result, _artifact_request, _artifact_result = result

            request = create_artifact_request_from_dry_run(
                trace,
                sandbox_request,
                sandbox_result,
                "summary.md",
            )

        self.assertIsInstance(request, SandboxArtifactRequest)
        self.assertEqual(request.run_id, trace.run_id)

    def test_build_agent_demo_artifact_content_is_local_summary_only(self) -> None:
        (_integration_result, trace, _events, sandbox_request, sandbox_decision, sandbox_result, _artifact_request, _artifact_result), _text, _workspace = self.run_integration()

        content = build_agent_demo_artifact_content(trace, sandbox_request, sandbox_decision, sandbox_result)

        self.assertIn(trace.goal_hash, content)
        self.assertNotIn("printf should-not-run", content)

    def test_integration_does_not_write_outside_temp_workspace(self) -> None:
        repo_marker = REPO_ROOT / "__aoia_m9_a_repo_guard_should_not_exist__.md"
        self.assertFalse(repo_marker.exists())
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                relative_output_path=repo_marker.name,
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(repo_marker.exists())
            self.assertFalse((Path(workspace) / repo_marker.name).exists())

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
        }
        forbidden_text = (
            "os.system",
            "Popen",
            "eval(",
            "exec(",
            "os.environ",
            "shutil.rmtree",
        )

        for source_file in M9_RUNTIME_FILES:
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

    def assert_integration_blocks_path(self, relative_output_path: str, expected_reason: str) -> None:
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                relative_output_path=relative_output_path,
            )
            integration_result = result[0]
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
            self.assertFalse(integration_result.write_attempted)
            self.assertFalse(integration_result.write_completed)
            self.assertIn(expected_reason, artifact_result.blocked_reason)

    def assert_forbidden_runtime_terms_absent(self, forbidden_text: tuple[str, ...]) -> None:
        for source_file in M9_RUNTIME_FILES:
            source = source_file.read_text(encoding="utf-8")
            for term in forbidden_text:
                self.assertNotIn(term, source)

    def assert_forbidden_runtime_imports_absent(self, forbidden_modules: set[str]) -> None:
        for source_file in M9_RUNTIME_FILES:
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
