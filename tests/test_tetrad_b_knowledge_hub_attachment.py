from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.knowledge.tetrad import (
    EVIDENCE,
    TetradFace,
    TetradRecord,
)
from runtime.knowledge_hub_attachment import (
    create_read_only_knowledge_attachment,
    is_read_only_knowledge_attachment,
)
from runtime.local_visible_flow import (
    BLOCKED_APPROVAL_PATH,
    FLOW_BLOCKED_REJECT,
    run_local_visible_flow,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ATTACHMENT_RUNTIME = REPO_ROOT / "runtime" / "knowledge_hub_attachment.py"
APPROVAL_RUNTIME_PATHS = (
    REPO_ROOT / "runtime" / "schemas" / "approval_decision.py",
    REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_policy.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py",
    REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
)
CONTENT = "# TETRAD-B attachment boundary\n"


class TetradBKnowledgeHubAttachmentTests(unittest.TestCase):
    def test_valid_tetrad_record_attaches_as_read_only_context(self):
        record = self.make_tetrad()
        attachment = self.make_attachment(tetrad_records=[record])

        self.assertEqual((record,), attachment.tetrad_records)
        self.assertTrue(is_read_only_knowledge_attachment(attachment))
        self.assertTrue(attachment.read_only)
        self.assertFalse(attachment.can_authorize)
        self.assertFalse(attachment.can_approve)
        self.assertFalse(attachment.can_write)

    def test_missing_and_empty_tetrad_collections_are_safe(self):
        missing = self.make_attachment()
        empty = self.make_attachment(tetrad_records=[])

        self.assertEqual((), missing.tetrad_records)
        self.assertEqual((), empty.tetrad_records)
        self.assertTrue(is_read_only_knowledge_attachment(missing))
        self.assertTrue(is_read_only_knowledge_attachment(empty))
        self.assertEqual(missing.attachment_id, empty.attachment_id)

    def test_attached_record_remains_immutable(self):
        record = self.make_tetrad()
        attachment = self.make_attachment(tetrad_records=(record,))

        self.assertIs(record, attachment.tetrad_records[0])
        with self.assertRaises(FrozenInstanceError):
            attachment.tetrad_records[0].read_only = False
        with self.assertRaises(FrozenInstanceError):
            attachment.tetrad_records = ()

    def test_tetrad_ids_and_advisory_boundary_are_visible(self):
        records = (
            self.make_tetrad("First context"),
            self.make_tetrad("Second context"),
        )
        projection = self.make_attachment(tetrad_records=records).to_dict()[
            "tetrad_context"
        ]

        self.assertTrue(projection["tetrad_records_present"])
        self.assertEqual(2, projection["tetrad_record_count"])
        self.assertEqual(
            [record.tetrad_id for record in records],
            projection["tetrad_ids"],
        )
        self.assertTrue(projection["read_only"])
        self.assertTrue(projection["advisory_only"])
        self.assertFalse(projection["can_affect_approval"])
        self.assertFalse(projection["can_affect_write"])
        self.assertFalse(projection["can_affect_execution"])

    def test_tetrad_attachment_does_not_change_flow_authority_state(self):
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            baseline = self.run_flow(
                workspace_a,
                audit_a,
                attachment=self.make_attachment(),
                decision="REJECT",
            )
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            attached = self.run_flow(
                workspace_b,
                audit_b,
                attachment=self.make_attachment(
                    tetrad_records=(self.make_tetrad(),),
                ),
                decision="REJECT",
            )

        authority_fields = (
            "decision",
            "human_decision_captured",
            "approval_decision_created",
            "durable_handoff_complete",
            "pre_artifact_gate_passed",
            "artifact_write_occurred",
            "provider_output_trusted",
            "metadata_authority",
            "canonical",
            "execution_occurred",
        )
        for field_name in authority_fields:
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    getattr(baseline, field_name),
                    getattr(attached, field_name),
                )
        self.assertEqual(baseline.review_packet_hash, attached.review_packet_hash)
        self.assertEqual(baseline.artifact_hash, attached.artifact_hash)

    def test_reject_still_blocks_and_tetrad_cannot_cause_write(self):
        attachment = self.make_attachment(
            tetrad_records=(self.make_tetrad("APPROVE WRITE EXECUTE"),),
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                attachment=attachment,
                decision="REJECT",
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(FLOW_BLOCKED_REJECT, result.status)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.provider_output_trusted)
        self.assertEqual([], files)

    def test_stale_binding_still_blocks_with_tetrad_context(self):
        attachment = self.make_attachment(
            tetrad_records=(self.make_tetrad(),),
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                attachment=attachment,
                decision="APPROVE",
                current_review_packet_hash="c" * 64,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertFalse(result.human_decision_captured)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], files)

    def test_malformed_non_tetrad_attachment_is_rejected(self):
        invalid_values = (
            [object()],
            ["not-a-tetrad"],
            [self.make_tetrad(), object()],
        )

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(TypeError):
                    self.make_attachment(tetrad_records=values)

    def test_attachment_id_changes_only_with_attached_tetrad_metadata(self):
        first = self.make_attachment(
            tetrad_records=(self.make_tetrad("First"),),
        )
        same = self.make_attachment(
            tetrad_records=(self.make_tetrad("First"),),
        )
        changed = self.make_attachment(
            tetrad_records=(self.make_tetrad("Changed"),),
        )

        self.assertEqual(first.attachment_id, same.attachment_id)
        self.assertNotEqual(first.attachment_id, changed.attachment_id)

    def test_no_forbidden_capability_graph_or_authority_token_is_added(self):
        source = ATTACHMENT_RUNTIME.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_import_roots = {
            "anthropic",
            "httpx",
            "openai",
            "pexpect",
            "playwright",
            "pty",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = (
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
        )
        forbidden_architecture = (
            "vector_db",
            "embedding",
            "directed_acyclic_graph",
            "approval_status",
            "gate_result",
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".", 1)[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".", 1)[0]}
            else:
                continue
            self.assertTrue(roots.isdisjoint(forbidden_import_roots))
        for forbidden_call in forbidden_calls:
            self.assertNotIn(forbidden_call, source)
        for term in forbidden_architecture:
            self.assertNotIn(term, source.lower())

    def test_approval_gate_and_execution_modules_still_do_not_import_tetrad(self):
        for path in APPROVAL_RUNTIME_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("knowledge.tetrad", source)
                self.assertNotIn("import tetrad", source)

    def make_tetrad(self, content: str = "Advisory evidence context") -> TetradRecord:
        return TetradRecord(
            evidence=TetradFace(
                face_type=EVIDENCE,
                content=(content,),
                source_refs=("local-context",),
            ),
        )

    def make_attachment(self, **overrides):
        values = {
            "title": "Read-only Knowledge Hub context",
            "source_label": "local-knowledge-hub",
            "content_summary": "Advisory context only.",
            "labels": ("read-only", "advisory"),
        }
        values.update(overrides)
        return create_read_only_knowledge_attachment(**values)

    def run_flow(
        self,
        workspace: str,
        audit_dir: str,
        *,
        attachment,
        decision: str,
        **overrides,
    ):
        values = {
            "candidate_text": "Untrusted candidate for TETRAD-B boundary test.",
            "candidate_source": "local-external-source",
            "human_decision": decision,
            "workspace_root": workspace,
            "audit_dir": audit_dir,
            "artifact_relative_path": "reports/tetrad-b-result.md",
            "artifact_content": CONTENT,
            "human_actor": "human-reviewer-tetrad-b",
            "knowledge_attachment": attachment,
        }
        values.update(overrides)
        return run_local_visible_flow(**values)


if __name__ == "__main__":
    unittest.main()
