from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.safety import audit_event_logger, sandbox_artifact_runner
from runtime.safety.human_approval_review_policy import (
    HumanApprovalReviewNotApprovalError,
    assert_review_packet_is_not_approval,
    validate_human_approval_review_packet,
)
from runtime.schemas.human_approval_review import (
    MAX_HUMAN_APPROVAL_REVIEW_GOAL_CHARS,
    create_human_approval_review_packet,
    render_human_approval_review_packet_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "human_approval_review.py",
    REPO_ROOT / "runtime" / "safety" / "human_approval_review_policy.py",
)


class HumanApprovalReviewPolicyTests(unittest.TestCase):
    def test_empty_goal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.make_packet(goal="  ")

    def test_overlong_goal_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.make_packet(goal="x" * (MAX_HUMAN_APPROVAL_REVIEW_GOAL_CHARS + 1))

    def test_goal_control_characters_are_rejected_except_tab_and_newline(self) -> None:
        with self.assertRaises(ValueError):
            self.make_packet(goal="create\x00artifact")
        with self.assertRaises(ValueError):
            self.make_packet(goal="create\x1fartifact")

        packet = self.make_packet(goal="create\tartifact\nsummary")
        self.assertIn("\t", packet.goal)
        self.assertIn("\n", packet.goal)

    def test_missing_artifact_destination_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.make_packet(destination="")
        with self.assertRaises(ValueError):
            self.make_packet(audit="")

    def test_unsafe_relative_output_path_is_rejected(self) -> None:
        unsafe_paths = (
            "",
            "/tmp/escape.md",
            "../escape.md",
            "nested/../escape.md",
            ".git/config",
            "script.sh",
            "safe.md.sh",
            "bad\\path.md",
        )
        for path in unsafe_paths:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    self.make_packet(artifact_relative_path=path)

    def test_packet_cannot_be_converted_into_approval_decision_automatically(self) -> None:
        packet = self.make_packet()

        self.assertFalse(hasattr(packet, "to_approval_decision"))
        with self.assertRaises(ValueError):
            assert_review_packet_is_not_approval(replace(packet, decision_status="approved"))

    def test_packet_cannot_mark_itself_approved(self) -> None:
        packet = self.make_packet()

        with self.assertRaises(ValueError):
            replace(packet, decision_status="approved")
        with self.assertRaises(ValueError):
            replace(packet, allowed_decisions=("approve", "deny", "auto_approve"))

    def test_packet_cannot_write_to_audit_or_artifact_paths(self) -> None:
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
                validate_human_approval_review_packet(packet)
                render_human_approval_review_packet_markdown(packet)
            after = self.snapshot(tmpdir)

        self.assertEqual(before, after)

    def test_packet_rendering_does_not_execute_or_interpolate_dangerous_text(self) -> None:
        dangerous_goal = "render this literally: $(touch /tmp/nope) && `rm -rf /`"
        packet = self.make_packet(goal=dangerous_goal)
        rendered = render_human_approval_review_packet_markdown(packet)

        self.assertIn("$(touch /tmp/nope)", rendered)
        self.assertIn("`rm -rf /`", rendered)
        self.assertEqual(packet.decision_status, "pending")

    def test_provider_generated_text_is_marked_untrusted(self) -> None:
        packet = self.make_packet(untrusted_inputs=("provider_generated_text",))

        self.assertIn("provider_generated_text", packet.untrusted_inputs)
        rendered = render_human_approval_review_packet_markdown(packet)
        self.assertIn("provider_generated_text", rendered)

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
            "run_dry_run_agent_and_write_artifact(",
            "create_human_approval_decision(",
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

    def make_packet(
        self,
        *,
        goal: str = "Create a safe review packet.",
        artifact_relative_path: str = "review.md",
        destination: str = "/tmp/aoia-run/artifacts",
        audit: str = "/tmp/aoia-run/audit",
        untrusted_inputs: tuple[str, ...] = (),
    ):
        return create_human_approval_review_packet(
            goal=goal,
            proposal_id="proposal-review-policy",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="review_policy_run",
            artifact_relative_path=artifact_relative_path,
            artifact_destination_summary=destination,
            audit_context_summary=audit,
            created_by="policy-test",
            untrusted_inputs=untrusted_inputs,
        )

    def snapshot(self, base: str) -> list[str]:
        return sorted(str(path.relative_to(base)) for path in Path(base).rglob("*"))


if __name__ == "__main__":
    unittest.main()
