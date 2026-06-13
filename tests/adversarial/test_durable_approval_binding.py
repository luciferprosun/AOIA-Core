from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety import dry_run_artifact_integration as integration
from runtime.safety.audit_event_logger import AuditLogPathBlockedError, AuditLogWriteBlockedError
from runtime.safety.controlled_agent_demo import run_controlled_agent_demo
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.schemas.action_proposal import ActionProposalType
from runtime.schemas.dry_run_agent import create_dry_run_agent_request, create_dry_run_plan_step
from runtime.schemas.sandbox_artifact import SandboxArtifactState


REPO_ROOT = Path(__file__).resolve().parents[2]
DURABLE_BINDING_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "safety" / "dry_run_artifact_integration.py",
    REPO_ROOT / "runtime" / "safety" / "audit_event_logger.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
    REPO_ROOT / "runtime" / "schemas" / "sandbox_artifact.py",
)


class DurableApprovalBindingAdversarialTests(unittest.TestCase):
    def test_controlled_artifact_integration_runs_with_explicit_durable_audit_directory(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                self.make_request(),
                workspace,
                audit_dir,
            )
            durable_result, _trace, events, *_middle, artifact_result, durable_writes = result

            self.assertTrue(durable_result.durable_audit_write_completed)
            self.assertEqual(len(durable_writes), len(events))
            self.assertEqual(artifact_result.state, SandboxArtifactState.WRITTEN)
            self.assertTrue((Path(audit_dir) / "events.jsonl").is_file())

    def test_durable_audit_log_is_written_before_artifact_file_appears(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            output_path = Path(workspace) / "ordered.md"
            audit_log_path = Path(audit_dir) / "events.jsonl"
            original_writer = integration.write_sandbox_artifact

            def assert_audit_exists_before_artifact_write(request, workspace_root):
                self.assertTrue(audit_log_path.is_file())
                self.assertTrue(audit_log_path.read_text(encoding="utf-8").strip())
                self.assertFalse(output_path.exists())
                return original_writer(request, workspace_root)

            with patch.object(integration, "write_sandbox_artifact", side_effect=assert_audit_exists_before_artifact_write):
                result = integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                    self.make_request(),
                    workspace,
                    audit_dir,
                    relative_output_path="ordered.md",
                )

            self.assertTrue(result[0].write_completed)
            self.assertTrue(output_path.is_file())

    def test_durable_audit_append_failure_blocks_artifact_write(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            output_path = Path(workspace) / "should-not-exist.md"

            with patch.object(
                integration,
                "append_audit_event_jsonl",
                side_effect=AuditLogWriteBlockedError("simulated durable audit failure"),
            ):
                with self.assertRaises(AuditLogWriteBlockedError):
                    integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                        self.make_request(),
                        workspace,
                        audit_dir,
                        relative_output_path=output_path.name,
                    )

            self.assertFalse(output_path.exists())
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_symlink_audit_directory_blocks_artifact_write(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as parent, TemporaryDirectory() as outside:
            audit_dir = Path(parent) / "audit-link"
            try:
                audit_dir.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation not supported here: {exc}")

            with self.assertRaises(AuditLogPathBlockedError):
                integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                    self.make_request(),
                    workspace,
                    str(audit_dir),
                    relative_output_path="blocked.md",
                )

            self.assertFalse((Path(workspace) / "blocked.md").exists())
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_invalid_existing_audit_hash_chain_blocks_artifact_write(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            (Path(audit_dir) / "events.jsonl").write_text('{"event_hash":"not-current-chain"}\n', encoding="utf-8")

            with self.assertRaises(Exception):
                integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                    self.make_request(),
                    workspace,
                    audit_dir,
                    relative_output_path="blocked.md",
                )

            self.assertFalse((Path(workspace) / "blocked.md").exists())
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_expected_previous_hash_mismatch_blocks_artifact_write(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with self.assertRaises(Exception):
                integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                    self.make_request(),
                    workspace,
                    audit_dir,
                    relative_output_path="blocked.md",
                    expected_first_previous_hash="wrong-previous-hash",
                )

            self.assertFalse((Path(workspace) / "blocked.md").exists())
            self.assertFalse(any(Path(workspace).iterdir()))

    def test_durable_audit_event_binding_matches_artifact_contract(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                self.make_request(),
                workspace,
                audit_dir,
            )
            _durable_result, _trace, events, _sandbox_request, _sandbox_decision, _sandbox_result, artifact_request, _artifact_result, durable_writes = result

            self.assertEqual(artifact_request.audit_event_id, events[-1].event_id)
            self.assertEqual(artifact_request.contract_audit_event_id, durable_writes[-1].event_id)
            self.assertEqual(durable_writes[-1].event_hash, events[-1].event_hash)

    def test_artifact_contract_still_rejects_malformed_state_after_durable_flow(self) -> None:
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = integration.run_dry_run_agent_and_write_artifact_with_durable_audit(
                self.make_request(),
                workspace,
                audit_dir,
            )
            artifact_request = result[-3]

        malformed_requests = (
            replace(artifact_request, artifact_contract_version=""),
            replace(artifact_request, artifact_write_allowed=False),
            replace(artifact_request, contract_payload_hash="0" * 64),
            replace(artifact_request, audit_event_id="different-audit-id"),
        )
        for malformed in malformed_requests:
            with self.subTest(reason=malformed):
                with TemporaryDirectory() as workspace:
                    artifact_result = write_sandbox_artifact(malformed, workspace)
                    self.assertEqual(artifact_result.state, SandboxArtifactState.BLOCKED)
                    self.assertFalse(artifact_result.write_attempted)
                    self.assertFalse(any(Path(workspace).iterdir()))

    def test_existing_m9_non_durable_path_remains_explicitly_unchanged(self) -> None:
        with TemporaryDirectory() as workspace:
            result = integration.run_dry_run_agent_and_write_artifact(
                self.make_request(),
                workspace,
                relative_output_path="non-durable.md",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.WRITTEN)
            self.assertTrue((Path(workspace) / "non-durable.md").is_file())

    def test_existing_m10_controlled_demo_still_passes(self) -> None:
        with TemporaryDirectory() as workspace:
            result = run_controlled_agent_demo(
                "Create a controlled local summary artifact.",
                workspace,
                requested_by="unit-test",
            )
            artifact_result = result[-1]

            self.assertEqual(artifact_result.state, SandboxArtifactState.WRITTEN)
            self.assertTrue(Path(artifact_result.resolved_output_path).is_file())

    def test_no_forbidden_capabilities_are_introduced(self) -> None:
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

        for source_file in DURABLE_BINDING_RUNTIME_FILES:
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
            title="Durable approval-bound artifact",
            description="Create one inert durable-audited dry-run summary artifact.",
            proposed_action_type=ActionProposalType.HUMAN_REVIEW_ONLY.value,
            payload_summary="durable binding summary",
            exact_payload="durable_binding_payload=summary_only",
            step_index=0,
            step_id="durable-binding-step",
        )
        return create_dry_run_agent_request(
            goal_text="Create a durable approval-bound artifact.",
            requested_by="unit-test",
            plan_steps=(step,),
            run_id="durable-binding-run",
        )


if __name__ == "__main__":
    unittest.main()
