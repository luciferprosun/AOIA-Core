from __future__ import annotations

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import (
    ALLOWED_HUMAN_DECISIONS,
    HUMAN_DECISION_CAPTURE_VERSION,
    HumanDecisionCapture,
    capture_human_decision,
    hash_human_approval_review_packet,
    human_decision_capture_to_dict,
    render_human_decision_capture_markdown,
)
from runtime.safety import (
    audit_event_logger,
    dry_run_artifact_integration,
    local_agent_entrypoint,
    sandbox_artifact_runner,
)
from runtime.safety.human_decision_capture_policy import validate_human_decision_capture


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "human_decision_capture.py",
    REPO_ROOT / "runtime" / "safety" / "human_decision_capture_policy.py",
)


class Macrostep5BHumanDecisionCaptureTests(unittest.TestCase):
    def test_decision_capture_exists_and_is_import_safe(self) -> None:
        self.assertTrue(callable(capture_human_decision))
        self.assertTrue(callable(render_human_decision_capture_markdown))
        self.assertEqual(ALLOWED_HUMAN_DECISIONS, ("approve", "deny"))

    def test_decision_capture_consumes_valid_review_packet(self) -> None:
        packet = self.make_packet()
        capture = capture_human_decision(
            review_packet=packet,
            decision="approve",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:55:00Z",
            reason="Reviewed the packet.",
        )

        self.assertIsInstance(capture, HumanDecisionCapture)
        self.assertEqual(capture.decision_version, HUMAN_DECISION_CAPTURE_VERSION)
        self.assertEqual(capture.review_packet_id, packet.packet_id)
        self.assertEqual(capture.review_packet_hash, hash_human_approval_review_packet(packet))

    def test_decision_capture_requires_explicit_decision_input(self) -> None:
        packet = self.make_packet()

        with self.assertRaises(TypeError):
            capture_human_decision(  # type: ignore[call-arg]
                review_packet=packet,
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:55:00Z",
            )
        with self.assertRaises(ValueError):
            capture_human_decision(
                review_packet=packet,
                decision="",
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:55:00Z",
            )

    def test_decision_capture_accepts_only_approve_or_deny(self) -> None:
        packet = self.make_packet()
        approve = capture_human_decision(
            review_packet=packet,
            decision="approve",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:55:00Z",
        )
        deny = capture_human_decision(
            review_packet=packet,
            decision="deny",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:56:00Z",
        )

        self.assertEqual(approve.decision, "approve")
        self.assertEqual(deny.decision, "deny")
        with self.assertRaises(ValueError):
            capture_human_decision(
                review_packet=packet,
                decision="maybe",
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:57:00Z",
            )

    def test_decision_capture_requires_reviewer_id(self) -> None:
        with self.assertRaises(ValueError):
            capture_human_decision(
                review_packet=self.make_packet(),
                decision="approve",
                reviewer_id="",
                captured_at="2026-06-13T15:55:00Z",
            )

    def test_decision_capture_records_pending_status_and_timestamp(self) -> None:
        capture = self.make_capture()

        self.assertEqual(capture.decision_status_before, "pending")
        self.assertEqual(capture.captured_at, "2026-06-13T15:55:00Z")

    def test_decision_capture_creates_stable_id_and_hash_from_content(self) -> None:
        first = self.make_capture()
        second = self.make_capture()
        changed = capture_human_decision(
            review_packet=self.make_packet(),
            decision="deny",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:55:00Z",
            reason="Reviewed the packet.",
        )

        self.assertEqual(first.decision_id, second.decision_id)
        self.assertEqual(first.decision_hash, second.decision_hash)
        self.assertNotEqual(first.decision_id, changed.decision_id)
        self.assertTrue(first.decision_id.startswith("human-decision-capture-"))

    def test_decision_capture_serializes_to_dict(self) -> None:
        serialized = human_decision_capture_to_dict(self.make_capture())

        self.assertEqual(serialized["decision"], "approve")
        self.assertEqual(serialized["decision_status_before"], "pending")
        self.assertFalse(serialized["creates_approval_decision"])
        self.assertFalse(serialized["writes_artifact"])
        self.assertFalse(serialized["writes_audit"])
        self.assertFalse(serialized["triggers_execution"])

    def test_decision_capture_renders_deterministic_markdown_summary(self) -> None:
        capture = self.make_capture()
        first = render_human_decision_capture_markdown(capture)
        second = render_human_decision_capture_markdown(capture)

        self.assertEqual(first, second)
        self.assertIn("# Human Decision Capture", first)
        self.assertIn("Decision: approve", first)
        self.assertIn("Previous packet decision status: pending", first)

    def test_decision_capture_does_not_write_or_call_agent_paths(self) -> None:
        with TemporaryDirectory() as tmpdir:
            before = self.snapshot(tmpdir)
            with patch.object(
                audit_event_logger,
                "append_audit_event_jsonl",
                side_effect=AssertionError("decision capture must not append audit logs"),
            ), patch.object(
                sandbox_artifact_runner,
                "write_sandbox_artifact",
                side_effect=AssertionError("decision capture must not write artifacts"),
            ), patch.object(
                local_agent_entrypoint,
                "run_durable_local_agent_entrypoint",
                side_effect=AssertionError("decision capture must not run local entrypoint"),
            ), patch.object(
                dry_run_artifact_integration,
                "run_dry_run_agent_and_write_artifact",
                side_effect=AssertionError("decision capture must not use old non-durable path"),
            ):
                capture = self.make_capture()
                validate_human_decision_capture(capture)
                render_human_decision_capture_markdown(capture)
            after = self.snapshot(tmpdir)

        self.assertEqual(before, after)

    def test_decision_capture_runtime_does_not_call_forbidden_capabilities(self) -> None:
        self.assert_runtime_files_do_not_call_forbidden_capabilities()

    def make_packet(self):
        return create_human_approval_review_packet(
            goal="Create a safe post-review decision capture.",
            proposal_id="proposal-decision-capture-1",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="decision_capture_run",
            artifact_relative_path="decision-capture.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="unit-test",
        )

    def make_capture(self) -> HumanDecisionCapture:
        return capture_human_decision(
            review_packet=self.make_packet(),
            decision="approve",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:55:00Z",
            reason="Reviewed the packet.",
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
            "run_durable_local_agent_entrypoint(",
            "run_dry_run_agent_and_write_artifact(",
            "create_human_approval_decision(",
            "create_rejection_decision(",
            "input(",
            "readline(",
            "mkdir(",
            "write_text(",
            "open(",
        )
        for source_file in DECISION_RUNTIME_FILES:
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
