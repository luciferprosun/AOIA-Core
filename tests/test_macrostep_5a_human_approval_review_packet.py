from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.action_proposal import create_human_review_only_proposal
from runtime.schemas.human_approval_review import (
    HUMAN_APPROVAL_REVIEW_PACKET_VERSION,
    HumanApprovalReviewPacket,
    create_human_approval_review_packet,
    human_approval_review_packet_to_dict,
    render_human_approval_review_packet_markdown,
)
from runtime.safety import audit_event_logger, dry_run_artifact_integration, sandbox_artifact_runner
from runtime.safety.human_approval_review_policy import validate_human_approval_review_packet
from runtime.safety.local_workspace_run_context import prepare_local_workspace_run_context


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "human_approval_review.py",
    REPO_ROOT / "runtime" / "safety" / "human_approval_review_policy.py",
)


class Macrostep5AHumanApprovalReviewPacketTests(unittest.TestCase):
    def test_review_packet_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(create_human_approval_review_packet))
        self.assertTrue(callable(render_human_approval_review_packet_markdown))

    def test_review_packet_can_be_created_from_existing_local_inputs(self) -> None:
        proposal = self.make_proposal()
        with TemporaryDirectory() as base:
            context = prepare_local_workspace_run_context(base_workspace_root=base, run_id="review_packet_run")
            packet = create_human_approval_review_packet(
                goal="Create a human-reviewable artifact.",
                proposal_id=proposal.proposal_id,
                proposed_action_summary=proposal.payload_summary,
                run_id=context.run_id,
                artifact_relative_path=context.default_relative_output_path,
                artifact_destination_summary=context.artifact_workspace_root,
                audit_context_summary=context.audit_dir,
            )

        self.assertIsInstance(packet, HumanApprovalReviewPacket)
        self.assertEqual(packet.proposal_id, proposal.proposal_id)
        self.assertEqual(packet.run_id, "review_packet_run")

    def test_review_packet_includes_version_and_stable_id(self) -> None:
        first = self.make_packet()
        second = self.make_packet()

        self.assertEqual(first.packet_version, HUMAN_APPROVAL_REVIEW_PACKET_VERSION)
        self.assertEqual(first.packet_id, second.packet_id)
        self.assertTrue(first.packet_id.startswith("human-approval-review-"))

    def test_review_packet_includes_goal_proposal_artifact_run_and_audit_context(self) -> None:
        packet = self.make_packet()

        self.assertEqual(packet.goal, "Create a safe review packet.")
        self.assertEqual(packet.proposal_id, "proposal-review-1")
        self.assertEqual(packet.proposed_action_summary, "workspace-bound markdown artifact")
        self.assertEqual(packet.artifact_relative_path, "review.md")
        self.assertEqual(packet.run_id, "review_run")
        self.assertIn("artifacts", packet.artifact_destination_summary)
        self.assertIn("audit", packet.audit_context_summary)

    def test_review_packet_includes_required_safety_boundaries(self) -> None:
        packet = self.make_packet()

        boundaries = set(packet.safety_boundaries)
        self.assertIn("no_shell_execution", boundaries)
        self.assertIn("no_provider_api_network", boundaries)
        self.assertIn("no_browser_git_cloud", boundaries)
        self.assertIn("no_db_sqlite_orm", boundaries)
        self.assertIn("artifact_write_only", boundaries)
        self.assertIn("durable_audit_required", boundaries)
        self.assertTrue(packet.durable_audit_required)

    def test_review_packet_includes_explicit_pending_decision_options(self) -> None:
        packet = self.make_packet()

        self.assertTrue(packet.decision_required)
        self.assertEqual(packet.decision_status, "pending")
        self.assertEqual(packet.allowed_decisions, ("approve", "deny"))

    def test_review_packet_renders_deterministic_markdown(self) -> None:
        packet = self.make_packet()

        first = render_human_approval_review_packet_markdown(packet)
        second = render_human_approval_review_packet_markdown(packet)

        self.assertEqual(first, second)
        self.assertIn("# Human Approval Review Packet", first)
        self.assertIn("Decision status: pending", first)
        self.assertIn("Allowed decisions: approve, deny", first)

    def test_review_packet_serializes_to_dict(self) -> None:
        packet = self.make_packet()
        serialized = human_approval_review_packet_to_dict(packet)

        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["decision_status"], "pending")
        self.assertEqual(serialized["allowed_decisions"], ("approve", "deny"))

    def test_review_packet_does_not_create_files_append_audit_or_write_artifacts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            before = self.snapshot(tmpdir)
            with patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("review packet must not append audit logs"),
            ), patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("review packet must not write artifacts"),
            ):
                packet = self.make_packet(destination=str(Path(tmpdir) / "artifacts"), audit=str(Path(tmpdir) / "audit"))
                render_human_approval_review_packet_markdown(packet)
                validate_human_approval_review_packet(packet)
            after = self.snapshot(tmpdir)

        self.assertEqual(before, after)

    def test_review_packet_does_not_call_old_non_durable_path(self) -> None:
        with patch.object(
            dry_run_artifact_integration,
            "run_dry_run_agent_and_write_artifact",
            side_effect=AssertionError("old non-durable path must not be called"),
        ):
            packet = self.make_packet()
            rendered = render_human_approval_review_packet_markdown(packet)

        self.assertIn(packet.packet_id, rendered)

    def test_review_packet_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_files_do_not_call_forbidden_capabilities()

    def make_packet(self, *, destination: str = "/tmp/aoia-run/artifacts", audit: str = "/tmp/aoia-run/audit"):
        return create_human_approval_review_packet(
            goal="Create a safe review packet.",
            proposal_id="proposal-review-1",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="review_run",
            artifact_relative_path="review.md",
            artifact_destination_summary=destination,
            audit_context_summary=audit,
            created_by="unit-test",
        )

    def make_proposal(self):
        return create_human_review_only_proposal(
            title="Review packet proposal",
            description="Create a non-UI review packet.",
            payload_summary="workspace-bound markdown artifact",
            exact_payload="review_packet=summary_only",
            proposal_id="proposal-review-existing",
        )

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))

    def assert_runtime_files_do_not_call_forbidden_capabilities(self) -> None:
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
            "run_dry_run_agent_and_write_artifact(",
            "create_human_approval_decision(",
            "create_rejection_decision(",
            "input(",
            "readline(",
            "mkdir(",
            "write_text(",
            "open(",
        )
        for source_file in REVIEW_RUNTIME_FILES:
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
