from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
import unittest

from runtime.knowledge.tetrad import (
    AUDIT,
    CAPABILITY,
    CONSTRAINT,
    EVIDENCE,
    TetradCore,
    TetradFace,
    TetradRecord,
    TrustLevel,
    canonical_tetrad_json,
    compute_tetrad_id,
)
from runtime.safety.approval_artifact_gate import (
    evaluate_pre_artifact_approval_gate,
)
from runtime.schemas.approval_decision import approval_decision_to_dict


REPO_ROOT = Path(__file__).resolve().parents[1]
TETRAD_RUNTIME = REPO_ROOT / "runtime" / "knowledge" / "tetrad.py"
APPROVAL_RUNTIME_PATHS = (
    REPO_ROOT / "runtime" / "schemas" / "approval_decision.py",
    REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_policy.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py",
    REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
)


class TetradAInertSkeletonTests(unittest.TestCase):
    def test_tetrad_face_is_immutable_and_normalizes_mutable_input(self):
        content = ["  source   statement  "]
        face = TetradFace(
            face_type=" EVIDENCE ",
            content=content,
            source_refs=[" source-1 "],
            trust_level="HUMAN_PROVIDED",
        )
        content.append("later mutation")

        self.assertEqual(EVIDENCE, face.face_type)
        self.assertEqual(("source statement",), face.content)
        self.assertEqual(("source-1",), face.source_refs)
        self.assertEqual(TrustLevel.HUMAN_PROVIDED, face.trust_level)
        with self.assertRaises(FrozenInstanceError):
            face.content = ()

    def test_tetrad_core_is_immutable(self):
        core = TetradCore(
            conflicts=["  source A   conflicts with source B "],
            open_questions=["  Which source is current? "],
        )

        self.assertEqual(
            ("source A conflicts with source B",),
            core.conflicts,
        )
        self.assertEqual(("Which source is current?",), core.open_questions)
        with self.assertRaises(FrozenInstanceError):
            core.conflicts = ()

    def test_tetrad_record_is_immutable_and_read_only(self):
        record = self.make_record()

        self.assertTrue(record.read_only)
        with self.assertRaises(FrozenInstanceError):
            record.read_only = False
        with self.assertRaises(FrozenInstanceError):
            record.tetrad_id = "forged"

    def test_invalid_or_misplaced_face_type_fails_closed(self):
        with self.assertRaises(ValueError):
            TetradFace(face_type="decision")
        with self.assertRaises(ValueError):
            TetradRecord(evidence=TetradFace(face_type=CONSTRAINT))

    def test_missing_faces_are_valid_and_deterministic(self):
        first = TetradRecord()
        second = TetradRecord()

        self.assertEqual(first.tetrad_id, second.tetrad_id)
        self.assertIsNone(first.evidence)
        self.assertIsNone(first.constraint)
        self.assertIsNone(first.capability)
        self.assertIsNone(first.audit)

    def test_empty_face_content_is_valid_and_deterministic(self):
        first = TetradRecord(evidence=TetradFace(face_type=EVIDENCE))
        second = TetradRecord(evidence=TetradFace(face_type=EVIDENCE, content=[]))

        self.assertEqual((), first.evidence.content)
        self.assertEqual(first.tetrad_id, second.tetrad_id)

    def test_identical_semantic_content_has_identical_id(self):
        first = self.make_record()
        second = self.make_record()

        self.assertEqual(first.tetrad_id, second.tetrad_id)
        self.assertEqual(
            first.tetrad_id,
            compute_tetrad_id(
                evidence=first.evidence,
                constraint=first.constraint,
                capability=first.capability,
                audit=first.audit,
                core=first.core,
            ),
        )

    def test_face_content_source_and_trust_changes_change_id(self):
        baseline = self.make_record()
        changed_values = (
            {"content": ("Different evidence",), "source_refs": ("source-1",)},
            {"content": ("Observed fact",), "source_refs": ("source-2",)},
            {
                "content": ("Observed fact",),
                "source_refs": ("source-1",),
                "trust_level": TrustLevel.SYSTEM_INTERNAL,
            },
        )

        for values in changed_values:
            with self.subTest(values=values):
                changed = self.make_record(
                    evidence=TetradFace(face_type=EVIDENCE, **values)
                )
                self.assertNotEqual(baseline.tetrad_id, changed.tetrad_id)

    def test_core_conflicts_and_questions_change_id_without_authority(self):
        baseline = self.make_record()
        conflict = self.make_record(
            core=TetradCore(conflicts=("Informational conflict",))
        )
        question = self.make_record(
            core=TetradCore(open_questions=("Informational question",))
        )

        self.assertNotEqual(baseline.tetrad_id, conflict.tetrad_id)
        self.assertNotEqual(baseline.tetrad_id, question.tetrad_id)
        self.assertFalse(hasattr(conflict.core, "approve"))
        self.assertFalse(hasattr(conflict.core, "gate"))

    def test_created_at_does_not_change_id(self):
        first = self.make_record(created_at="2026-06-19T08:00:00Z")
        second = self.make_record(created_at="2030-01-01T00:00:00Z")

        self.assertNotEqual(first.created_at, second.created_at)
        self.assertEqual(first.tetrad_id, second.tetrad_id)

    def test_forbidden_authority_and_status_fields_do_not_exist(self):
        names = {item.name for item in fields(TetradRecord)}
        forbidden = {
            "authority_flags",
            "canonical",
            "approval_status",
            "can_execute",
            "can_write",
            "gate_result",
            "provider_decision",
            "approval_decision",
            "execution_status",
        }

        self.assertTrue(names.isdisjoint(forbidden))

    def test_tetrad_is_rejected_as_approval_decision_and_denied_by_gate(self):
        record = self.make_record()

        with self.assertRaises(TypeError):
            approval_decision_to_dict(record)
        result = evaluate_pre_artifact_approval_gate(
            approval_decision=record,
            approval_audit_handoff_result=object(),
        )
        self.assertFalse(result.allowed)
        self.assertIsNone(result.approval_decision_id)

    def test_approval_gate_and_execution_modules_do_not_import_tetrad(self):
        for path in APPROVAL_RUNTIME_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("knowledge.tetrad", source)
                self.assertNotIn("import tetrad", source)

    def test_tetrad_module_has_no_forbidden_imports_or_behavior(self):
        source = TETRAD_RUNTIME.read_text(encoding="utf-8")
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
        }
        forbidden_calls = (
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
        )
        forbidden_method_names = {
            "approve",
            "execute",
            "gate",
            "route",
            "run",
            "write",
        }

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
        class_methods = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue(class_methods.isdisjoint(forbidden_method_names))

    def test_canonical_json_is_deterministic_and_excludes_created_at(self):
        record = self.make_record(created_at="2026-06-19T08:00:00Z")
        first = canonical_tetrad_json(
            evidence=record.evidence,
            constraint=record.constraint,
            capability=record.capability,
            audit=record.audit,
            core=record.core,
        )
        second = canonical_tetrad_json(
            core=record.core,
            audit=record.audit,
            capability=record.capability,
            constraint=record.constraint,
            evidence=record.evidence,
        )

        self.assertEqual(first, second)
        self.assertNotIn("created_at", first)
        self.assertEqual(record.tetrad_id, compute_tetrad_id(
            evidence=record.evidence,
            constraint=record.constraint,
            capability=record.capability,
            audit=record.audit,
            core=record.core,
        ))

    def make_record(self, **overrides):
        values = {
            "evidence": TetradFace(
                face_type=EVIDENCE,
                content=("Observed fact",),
                source_refs=("source-1",),
                trust_level=TrustLevel.HUMAN_PROVIDED,
            ),
            "constraint": TetradFace(
                face_type=CONSTRAINT,
                content=("Human approval remains required",),
            ),
            "capability": TetradFace(
                face_type=CAPABILITY,
                content=("May organize context",),
            ),
            "audit": TetradFace(
                face_type=AUDIT,
                content=("No action occurred",),
            ),
            "core": TetradCore(),
        }
        values.update(overrides)
        return TetradRecord(**values)


if __name__ == "__main__":
    unittest.main()
