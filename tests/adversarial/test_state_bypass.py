from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.safety.controlled_agent_demo import run_controlled_agent_demo
from runtime.safety.dry_run_agent_loop import run_dry_run_agent_loop
from runtime.safety.dry_run_artifact_integration import (
    create_artifact_request_from_dry_run,
    run_dry_run_agent_and_write_artifact,
)
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.dry_run_agent import create_dry_run_agent_request, create_dry_run_plan_step
from runtime.schemas.sandbox_artifact import SandboxArtifactRequest, SandboxArtifactState


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_GUARD_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "sandbox_artifact.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
    REPO_ROOT / "runtime" / "safety" / "dry_run_artifact_integration.py",
)


class ArtifactStateBypassAdversarialTests(unittest.TestCase):
    def test_direct_runner_call_with_missing_contract_marker_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), artifact_contract_version="")

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact contract version is invalid", result.blocked_reason)

    def test_direct_runner_call_with_malformed_contract_marker_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), artifact_contract_version="not-aoia-contract")

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact contract version is invalid", result.blocked_reason)

    def test_direct_runner_call_with_policy_rejected_contract_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), artifact_write_allowed=False)

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact contract does not allow workspace write", result.blocked_reason)

    def test_direct_runner_call_with_invalid_sandbox_result_state_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), sandbox_result_state="INVALID")

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("sandbox result state is not eligible", result.blocked_reason)

    def test_direct_runner_call_with_wrong_audit_relationship_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), audit_event_id="different-audit-event")

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact audit event must match contract audit event", result.blocked_reason)

    def test_direct_runner_call_with_content_hash_mismatch_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), contract_payload_hash="0" * 64)

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact content hash must match contract payload hash", result.blocked_reason)

    def test_direct_runner_call_with_missing_trace_relationship_is_rejected(self) -> None:
        request = replace(self.make_valid_artifact_request(), dry_run_trace_id="")

        result = self.run_direct(request)

        self.assertEqual(result.state, SandboxArtifactState.BLOCKED)
        self.assertIn("artifact contract requires dry-run identifiers", result.blocked_reason)

    def test_existing_m9_dry_run_artifact_integration_still_succeeds(self) -> None:
        with TemporaryDirectory() as workspace:
            result = run_dry_run_agent_and_write_artifact(self.make_dry_run_request(), workspace)
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.WRITTEN)
            self.assertTrue(Path(artifact_result.resolved_output_path).is_file())

    def test_existing_m10_controlled_agent_demo_still_succeeds(self) -> None:
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                "Create a controlled local summary artifact.",
                workspace,
                requested_by="unit-test",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.WRITTEN)
            self.assertTrue(Path(artifact_result.resolved_output_path).is_file())

    def test_runtime_does_not_add_forbidden_capabilities(self) -> None:
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
            "audit_log",
            "workspace_registry",
        )

        for source_file in STATE_GUARD_RUNTIME_FILES:
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

    def make_valid_artifact_request(self) -> SandboxArtifactRequest:
        trace, _events, sandbox_request, _sandbox_decision, sandbox_result = run_dry_run_agent_loop(
            self.make_dry_run_request()
        )
        return create_artifact_request_from_dry_run(
            trace,
            sandbox_request,
            sandbox_result,
            "state-guard-result.md",
        )

    def make_dry_run_request(self):
        step = create_dry_run_plan_step(
            title="State guard artifact",
            description="Create one inert dry-run summary artifact.",
            proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
            payload_summary="state guard summary",
            exact_payload="state_guard_payload=summary_only",
            step_index=0,
            step_id="state-guard-step",
        )
        return create_dry_run_agent_request(
            goal_text="Create a state guard artifact.",
            requested_by="unit-test",
            plan_steps=(step,),
            run_id="state-guard-run",
        )

    def run_direct(self, request: SandboxArtifactRequest):
        with TemporaryDirectory() as workspace:
            result = write_sandbox_artifact(request, workspace)
            self.assertFalse(result.write_attempted)
            self.assertFalse(result.write_completed)
            self.assertFalse(any(Path(workspace).iterdir()))
            return result


if __name__ == "__main__":
    unittest.main()
