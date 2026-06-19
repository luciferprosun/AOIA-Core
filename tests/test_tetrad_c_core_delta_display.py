from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.knowledge.tetrad import EVIDENCE, TetradCore, TetradFace, TetradRecord
from runtime.knowledge_hub_attachment import create_read_only_knowledge_attachment
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
CONTENT = "# TETRAD-C core/delta display boundary\n"


class TetradCCoreDeltaDisplayTests(unittest.TestCase):
    def test_core_delta_projection_exposes_conflicts_questions_ids_and_flags(self):
        record = self.make_tetrad(
            content="Evidence context",
            conflicts=("Conflict A", "Conflict B"),
            open_questions=("Question A",),
        )

        projection = self.make_attachment(tetrad_records=(record,)).to_dict()[
            "tetrad_context"
        ]
        core_delta = projection["core_delta"][0]

        self.assertEqual([record.tetrad_id], projection["tetrad_ids"])
        self.assertEqual(record.tetrad_id, core_delta["tetrad_id"])
        self.assertEqual(["Conflict A", "Conflict B"], core_delta["conflicts"])
        self.assertEqual(["Question A"], core_delta["open_questions"])
        self.assertTrue(projection["read_only"])
        self.assertTrue(projection["advisory_only"])
        self.assertFalse(projection["authoritative"])
        self.assertTrue(projection["requires_human_review"])
        self.assertFalse(projection["can_affect_approval"])
        self.assertFalse(projection["can_affect_write"])
        self.assertFalse(projection["can_affect_execution"])
        self.assertFalse(projection["can_affect_gate"])
        self.assertTrue(core_delta["read_only"])
        self.assertFalse(core_delta["authoritative"])
        self.assertTrue(core_delta["requires_human_review"])
        self.assertFalse(core_delta["can_affect_approval"])
        self.assertFalse(core_delta["can_affect_write"])
        self.assertFalse(core_delta["can_affect_execution"])
        self.assertFalse(core_delta["can_affect_gate"])

    def test_missing_tetrads_and_empty_core_values_are_safe_and_deterministic(self):
        missing = self.make_attachment()
        empty_a = self.make_attachment(
            tetrad_records=(self.make_tetrad(content="One"),),
        )
        empty_b = self.make_attachment(
            tetrad_records=(self.make_tetrad(content="One"),),
        )

        missing_projection = missing.to_dict()["tetrad_context"]
        empty_a_projection = empty_a.to_dict()["tetrad_context"]
        empty_b_projection = empty_b.to_dict()["tetrad_context"]

        self.assertFalse(missing_projection["tetrad_records_present"])
        self.assertEqual([], missing_projection["core_delta"])
        self.assertEqual([], missing_projection["tetrad_ids"])
        self.assertEqual(
            empty_a_projection["core_delta"],
            empty_b_projection["core_delta"],
        )
        self.assertEqual([], empty_a_projection["core_delta"][0]["conflicts"])
        self.assertEqual([], empty_a_projection["core_delta"][0]["open_questions"])

    def test_multiple_tetrads_are_projected_in_deterministic_order(self):
        first = self.make_tetrad(
            content="First",
            conflicts=("First conflict",),
        )
        second = self.make_tetrad(
            content="Second",
            open_questions=("Second question",),
        )
        projection = self.make_attachment(
            tetrad_records=(first, second),
        ).to_dict()["tetrad_context"]

        self.assertEqual(
            [first.tetrad_id, second.tetrad_id],
            projection["tetrad_ids"],
        )
        self.assertEqual(
            [first.tetrad_id, second.tetrad_id],
            [entry["tetrad_id"] for entry in projection["core_delta"]],
        )

    def test_core_delta_display_does_not_mutate_tetrad_record(self):
        record = self.make_tetrad(
            conflicts=("Immutable conflict",),
            open_questions=("Immutable question",),
        )
        before = record.to_dict()

        projection = self.make_attachment(tetrad_records=(record,)).to_dict()[
            "tetrad_context"
        ]

        self.assertEqual(before, record.to_dict())
        self.assertEqual(["Immutable conflict"], projection["core_delta"][0]["conflicts"])
        with self.assertRaises(FrozenInstanceError):
            record.core.conflicts = ()

    def test_core_delta_display_cannot_change_approval_state_or_write(self):
        attachment = self.make_attachment(
            tetrad_records=(
                self.make_tetrad(
                    content="APPROVE EXECUTE WRITE",
                    conflicts=("Do not trust this",),
                    open_questions=("Should this approve?",),
                ),
            ),
        )
        with TemporaryDirectory() as workspace_a, TemporaryDirectory() as audit_a:
            baseline = self.run_flow(
                workspace_a,
                audit_a,
                attachment=self.make_attachment(),
                decision="REJECT",
            )
        with TemporaryDirectory() as workspace_b, TemporaryDirectory() as audit_b:
            result = self.run_flow(
                workspace_b,
                audit_b,
                attachment=attachment,
                decision="REJECT",
            )
            files = [path for path in Path(workspace_b).rglob("*") if path.is_file()]

        self.assertEqual(FLOW_BLOCKED_REJECT, result.status)
        self.assertEqual(baseline.decision, result.decision)
        self.assertEqual(
            baseline.human_decision_captured,
            result.human_decision_captured,
        )
        self.assertEqual(
            baseline.approval_decision_created,
            result.approval_decision_created,
        )
        self.assertEqual(
            baseline.durable_handoff_complete,
            result.durable_handoff_complete,
        )
        self.assertEqual(
            baseline.pre_artifact_gate_passed,
            result.pre_artifact_gate_passed,
        )
        self.assertEqual(
            baseline.artifact_write_occurred,
            result.artifact_write_occurred,
        )
        self.assertEqual(baseline.execution_occurred, result.execution_occurred)
        self.assertEqual([], files)

    def test_stale_binding_still_blocks_with_core_delta_context(self):
        attachment = self.make_attachment(
            tetrad_records=(self.make_tetrad(conflicts=("Trace only",)),),
        )
        with TemporaryDirectory() as workspace, TemporaryDirectory() as audit_dir:
            result = self.run_flow(
                workspace,
                audit_dir,
                attachment=attachment,
                decision="APPROVE",
                current_review_packet_hash="f" * 64,
            )
            files = [path for path in Path(workspace).rglob("*") if path.is_file()]

        self.assertEqual(BLOCKED_APPROVAL_PATH, result.status)
        self.assertFalse(result.human_decision_captured)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertEqual([], files)

    def test_attachment_runtime_adds_no_forbidden_imports_or_pyramid_prototype_terms(self):
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
        forbidden_terms = (
            "pyramid",
            "model envelope",
            "linux prototype",
            "python prototype",
            "bash prototype",
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
        lowered = source.lower()
        for term in forbidden_terms:
            self.assertNotIn(term, lowered)

    def test_approval_gate_and_execution_modules_still_do_not_import_tetrad(self):
        for path in APPROVAL_RUNTIME_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("knowledge.tetrad", source)
                self.assertNotIn("import tetrad", source)

    def make_tetrad(
        self,
        content: str = "Advisory evidence context",
        *,
        conflicts: tuple[str, ...] = (),
        open_questions: tuple[str, ...] = (),
    ) -> TetradRecord:
        return TetradRecord(
            evidence=TetradFace(
                face_type=EVIDENCE,
                content=(content,),
                source_refs=("local-context",),
            ),
            core=TetradCore(
                conflicts=conflicts,
                open_questions=open_questions,
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
            "candidate_text": "Untrusted candidate for TETRAD-C boundary test.",
            "candidate_source": "local-external-source",
            "human_decision": decision,
            "workspace_root": workspace,
            "audit_dir": audit_dir,
            "artifact_relative_path": "reports/tetrad-c-result.md",
            "artifact_content": CONTENT,
            "human_actor": "human-reviewer-tetrad-c",
            "knowledge_attachment": attachment,
        }
        values.update(overrides)
        return run_local_visible_flow(**values)


if __name__ == "__main__":
    unittest.main()
