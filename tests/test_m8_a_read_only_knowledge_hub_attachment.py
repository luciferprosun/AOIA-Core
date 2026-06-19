from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from runtime.human_decision_end_to_end_demo import LocalApprovalArtifactDemoResult
from runtime.knowledge_hub_attachment import (
    UNTRUSTED_CONTEXT,
    attach_knowledge_context_to_flow_result,
    create_read_only_knowledge_attachment,
)
from runtime.local_visible_flow import (
    BLOCKED_APPROVAL_PATH,
    BLOCKED_KNOWLEDGE_ATTACHMENT,
    FLOW_BLOCKED_REJECT,
    run_local_visible_flow,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ATTACHMENT_RUNTIME = REPO_ROOT / "runtime" / "knowledge_hub_attachment.py"
FLOW_RUNTIME = REPO_ROOT / "runtime" / "local_visible_flow.py"
CONTENT = "# Attachment-boundary test artifact\n"
ARTIFACT_HASH = hashlib.sha256(CONTENT.encode("utf-8")).hexdigest()


class M8AReadOnlyKnowledgeHubAttachmentTests(unittest.TestCase):
    def test_attachment_is_deterministic_immutable_and_non_authoritative(self):
        first = self.make_attachment()
        second = self.make_attachment()

        self.assertEqual(first, second)
        self.assertEqual(first.attachment_id, second.attachment_id)
        self.assertEqual(UNTRUSTED_CONTEXT, first.trust_status)
        self.assertTrue(first.read_only)
        self.assertFalse(first.can_authorize)
        self.assertFalse(first.can_approve)
        self.assertFalse(first.can_write)
        self.assertFalse(first.canonical)
        self.assertFalse(first.evidence)
        with self.assertRaises(FrozenInstanceError):
            first.can_approve = True

    def test_attachment_is_visible_context_on_flow_result(self):
        attachment = self.make_attachment()
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                decision="REJECT",
                attachment=attachment,
            )

        self.assertIs(attachment, result.knowledge_attachment)
        self.assertEqual(
            attachment.to_dict(),
            result.to_dict()["knowledge_attachment"],
        )

    def test_attach_helper_changes_only_context_field(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            original = self.run_flow(
                workspace,
                audit_dir,
                decision="REJECT",
                attachment=None,
            )
        attached = attach_knowledge_context_to_flow_result(
            flow_result=original,
            attachment=self.make_attachment(),
        )

        original_payload = original.to_dict()
        attached_payload = attached.to_dict()
        original_payload.pop("knowledge_attachment")
        attached_payload.pop("knowledge_attachment")
        self.assertEqual(original_payload, attached_payload)

    def test_attachment_does_not_change_packet_or_artifact_hashes(self):
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            without_attachment = self.run_flow(
                workspace_a,
                audit_a,
                decision="REJECT",
                attachment=None,
            )
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            with_attachment = self.run_flow(
                workspace_b,
                audit_b,
                decision="REJECT",
                attachment=self.make_attachment(),
            )

        self.assertEqual(
            without_attachment.review_packet_hash,
            with_attachment.review_packet_hash,
        )
        self.assertEqual(without_attachment.artifact_hash, with_attachment.artifact_hash)

    def test_reject_still_blocks_with_attachment(self):
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                decision="REJECT",
                attachment=self.make_attachment(),
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(FLOW_BLOCKED_REJECT, result.status)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], files)

    def test_stale_and_mismatched_bindings_still_block_with_attachment(self):
        cases = (
            {"current_review_packet_hash": "c" * 64},
            {"expected_artifact_hash": "d" * 64},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
                    result = self.run_flow(
                        workspace,
                        audit_dir,
                        decision="APPROVE",
                        attachment=self.make_attachment(),
                        **overrides,
                    )
                    files = [
                        path for path in Path(workspace).rglob("*") if path.is_file()
                    ]

                self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
                self.assertFalse(result.pre_artifact_gate_passed)
                self.assertFalse(result.artifact_write_occurred)
                self.assertEqual([], files)

    def test_incomplete_handoff_still_blocks_with_attachment(self):
        blocked_demo = LocalApprovalArtifactDemoResult(
            status="BLOCKED_DURABLE_HANDOFF",
            demo_completed=False,
            decision="APPROVE",
            capture_created=True,
            approval_decision_created=True,
            durable_handoff_complete=False,
            pre_artifact_gate_passed=False,
            write_attempted=False,
            artifact_write_occurred=False,
            artifact_path=None,
            packet_hash="a" * 64,
            artifact_hash=ARTIFACT_HASH,
            provider_output_trusted=False,
            metadata_authority=False,
            blocking=True,
            reason="durable handoff unavailable",
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            with patch(
                "runtime.local_visible_flow.run_local_approval_to_artifact_demo",
                return_value=blocked_demo,
            ):
                result = self.run_flow(
                    workspace,
                    audit_dir,
                    decision="APPROVE",
                    attachment=self.make_attachment(),
                )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], files)

    def test_authority_claiming_labels_remain_inert_context(self):
        attachment = self.make_attachment(
            labels=("CANONICAL", "APPROVED", "WRITE_ALLOWED"),
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                decision="REJECT",
                attachment=attachment,
            )

        self.assertFalse(attachment.can_authorize)
        self.assertFalse(attachment.can_approve)
        self.assertFalse(attachment.can_write)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.canonical)
        self.assertFalse(result.evidence_created)

    def test_manually_altered_attachment_fails_closed_before_flow(self):
        altered = replace(self.make_attachment(), can_approve=True, can_write=True)
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                decision="APPROVE",
                attachment=altered,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_KNOWLEDGE_ATTACHMENT, result.status)
        self.assertFalse(result.human_decision_captured)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], files)

    def test_attachment_runtime_adds_no_forbidden_capability_or_future_structure(self):
        forbidden_imports = {
            "anthropic",
            "httpx",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = (
            "P" + "open(",
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
        )
        deferred_structure_terms = (
            "tet" + "rad",
            "geo" + "metry",
            "tri" + "angle",
            "pyra" + "mid",
        )

        for path in (ATTACHMENT_RUNTIME, FLOW_RUNTIME):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom):
                    roots = {(node.module or "").split(".", 1)[0]}
                else:
                    continue
                self.assertTrue(roots.isdisjoint(forbidden_imports))
            for forbidden_call in forbidden_calls:
                self.assertNotIn(forbidden_call, source)
            lowered = source.lower()
            for term in deferred_structure_terms:
                self.assertNotIn(term, lowered)

    def make_attachment(self, **overrides):
        values = {
            "title": "Read-only local context",
            "source_label": "local-knowledge-hub",
            "content_summary": "Context for display only; never approval authority.",
            "labels": ("local", "read-only"),
        }
        values.update(overrides)
        return create_read_only_knowledge_attachment(**values)

    def run_flow(
        self,
        workspace: str,
        audit_dir: str,
        *,
        decision: str,
        attachment,
        **overrides,
    ):
        values = {
            "candidate_text": "Untrusted candidate with optional context.",
            "candidate_source": "local-external-source",
            "human_decision": decision,
            "workspace_root": workspace,
            "audit_dir": audit_dir,
            "artifact_relative_path": "reports/m8-a-result.md",
            "artifact_content": CONTENT,
            "human_actor": "human-reviewer-m8-a",
            "knowledge_attachment": attachment,
        }
        values.update(overrides)
        return run_local_visible_flow(**values)


if __name__ == "__main__":
    unittest.main()
