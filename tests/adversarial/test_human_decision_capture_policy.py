from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.schemas.human_approval_review import create_human_approval_review_packet
from runtime.schemas.human_decision_capture import (
    MAX_HUMAN_DECISION_REVIEWER_ID_BYTES,
    HumanDecisionCapture,
    capture_human_decision,
    render_human_decision_capture_markdown,
)
from runtime.safety import (
    audit_event_logger,
    dry_run_artifact_integration,
    local_agent_entrypoint,
    sandbox_artifact_runner,
)
from runtime.safety.human_decision_capture_policy import (
    HumanDecisionCaptureBlockedError,
    validate_human_decision_capture,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DECISION_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "schemas" / "human_decision_capture.py",
    REPO_ROOT / "runtime" / "safety" / "human_decision_capture_policy.py",
)


class HumanDecisionCapturePolicyTests(unittest.TestCase):
    def test_missing_packet_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            capture_human_decision(
                review_packet=None,  # type: ignore[arg-type]
                decision="approve",
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:55:00Z",
            )

    def test_malformed_packet_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            capture_human_decision(
                review_packet=object(),  # type: ignore[arg-type]
                decision="approve",
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:55:00Z",
            )

    def test_non_pending_review_packet_is_rejected_by_packet_schema(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.make_packet(), decision_status="approved")

    def test_packet_with_invalid_packet_id_is_rejected_by_packet_schema(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.make_packet(), packet_id="tampered-packet-id")

    def test_automatic_approval_without_explicit_decision_is_impossible(self) -> None:
        packet = self.make_packet()

        with self.assertRaises(TypeError):
            capture_human_decision(  # type: ignore[call-arg]
                review_packet=packet,
                reviewer_id="reviewer-1",
                captured_at="2026-06-13T15:55:00Z",
            )
        capture = capture_human_decision(
            review_packet=packet,
            decision="approve",
            reviewer_id="reviewer-1",
            captured_at="2026-06-13T15:55:00Z",
        )
        self.assertFalse(capture.creates_approval_decision)

    def test_decision_string_with_control_characters_is_rejected(self) -> None:
        for decision in ("approve\nexecute", "approve\x00", "approve\t"):
            with self.subTest(decision=repr(decision)):
                with self.assertRaises(ValueError):
                    capture_human_decision(
                        review_packet=self.make_packet(),
                        decision=decision,
                        reviewer_id="reviewer-1",
                        captured_at="2026-06-13T15:55:00Z",
                    )

    def test_empty_overlong_or_control_reviewer_id_is_rejected(self) -> None:
        invalid_reviewers = (
            "",
            "x" * (MAX_HUMAN_DECISION_REVIEWER_ID_BYTES + 1),
            "reviewer\x00id",
            "reviewer\nid",
        )
        for reviewer_id in invalid_reviewers:
            with self.subTest(reviewer_id=repr(reviewer_id)):
                with self.assertRaises(ValueError):
                    capture_human_decision(
                        review_packet=self.make_packet(),
                        decision="approve",
                        reviewer_id=reviewer_id,
                        captured_at="2026-06-13T15:55:00Z",
                    )

    def test_policy_rejects_capture_that_claims_execution_or_writes(self) -> None:
        capture = self.make_capture()

        for field_name in ("creates_approval_decision", "writes_artifact", "writes_audit", "triggers_execution"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValueError):
                    replace(capture, **{field_name: True})

        malformed = HumanDecisionCapture(
            decision_version=capture.decision_version,
            decision_id="",
            decision_hash="",
            review_packet_id=capture.review_packet_id,
            review_packet_hash=capture.review_packet_hash,
            decision=capture.decision,
            reviewer_id=capture.reviewer_id,
            captured_at=capture.captured_at,
            decision_status_before=capture.decision_status_before,
            creates_approval_decision=False,
            writes_artifact=False,
            writes_audit=False,
            triggers_execution=False,
            reason=capture.reason,
        )
        validate_human_decision_capture(malformed)

    def test_policy_rejects_non_capture_object(self) -> None:
        with self.assertRaises(TypeError):
            validate_human_decision_capture(object())  # type: ignore[arg-type]

    def test_policy_blocks_manual_write_or_execution_flags_if_constructed(self) -> None:
        capture = self.make_capture()

        with self.assertRaises(ValueError):
            HumanDecisionCapture(
                decision_version=capture.decision_version,
                decision_id="",
                decision_hash="",
                review_packet_id=capture.review_packet_id,
                review_packet_hash=capture.review_packet_hash,
                decision=capture.decision,
                reviewer_id=capture.reviewer_id,
                captured_at=capture.captured_at,
                decision_status_before=capture.decision_status_before,
                creates_approval_decision=False,
                writes_artifact=True,
                writes_audit=False,
                triggers_execution=False,
                reason=None,
            )
        with self.assertRaises(HumanDecisionCaptureBlockedError):
            raise HumanDecisionCaptureBlockedError("manual execution path blocked")

    def test_capture_cannot_write_or_trigger_entrypoints(self) -> None:
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
                side_effect=AssertionError("decision capture must not trigger entrypoint"),
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
            "run_durable_local_agent_entrypoint(",
            "run_dry_run_agent_and_write_artifact(",
            "create_human_approval_decision(",
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

    def make_packet(self):
        return create_human_approval_review_packet(
            goal="Create a safe decision capture.",
            proposal_id="proposal-decision-policy",
            proposed_action_summary="workspace-bound markdown artifact",
            run_id="decision_policy_run",
            artifact_relative_path="decision-policy.md",
            artifact_destination_summary="/tmp/aoia-run/artifacts",
            audit_context_summary="/tmp/aoia-run/audit",
            created_by="policy-test",
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


if __name__ == "__main__":
    unittest.main()
