from __future__ import annotations

import ast
from pathlib import Path
import unittest

from runtime.knowledge.tetrad import EVIDENCE, TetradFace, TetradRecord
from runtime.knowledge_hub_attachment import create_read_only_knowledge_attachment
from runtime.provider_proposer_adapter import (
    BLOCKED_ADAPTER_DISABLED,
    create_provider_proposer_candidate,
)
from runtime.review_packet_projection import (
    create_human_readable_review_packet_projection,
)
from runtime.safety.approval_artifact_gate import (
    evaluate_pre_artifact_approval_gate,
)
from runtime.schemas.approval_decision import approval_decision_to_dict


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTION_RUNTIME = REPO_ROOT / "runtime" / "review_packet_projection.py"
PROVIDER_ADAPTER_RUNTIME = REPO_ROOT / "runtime" / "provider_proposer_adapter.py"
KNOWLEDGE_RUNTIME = REPO_ROOT / "runtime" / "knowledge_hub_attachment.py"
TETRAD_RUNTIME = REPO_ROOT / "runtime" / "knowledge" / "tetrad.py"
AUTHORITY_RUNTIME_PATHS = (
    REPO_ROOT / "runtime" / "schemas" / "approval_decision.py",
    REPO_ROOT / "runtime" / "safety" / "approval_artifact_gate.py",
    REPO_ROOT / "runtime" / "safety" / "approval_decision_audit_handoff.py",
    REPO_ROOT / "runtime" / "safety" / "gated_durable_artifact_flow.py",
    REPO_ROOT / "runtime" / "safety" / "sandbox_artifact_runner.py",
)


class ReviewPacketABoundaryNoProviderIOTests(unittest.TestCase):
    def test_provider_adapter_remains_default_off_and_attempts_no_io(self):
        candidate = create_provider_proposer_candidate(
            provider_label="future-provider-label",
            model_label="future-model-label",
            raw_provider_output="Local data only.",
        )

        self.assertEqual(BLOCKED_ADAPTER_DISABLED, candidate.status)
        self.assertFalse(candidate.adapter_enabled)
        self.assertFalse(candidate.live_call_attempted)
        self.assertFalse(candidate.network_call_attempted)
        self.assertFalse(candidate.approval_decision_created)
        self.assertFalse(candidate.artifact_write_occurred)

    def test_knowledge_and_tetrad_are_rejected_as_approval_decisions(self):
        record = TetradRecord(
            evidence=TetradFace(
                face_type=EVIDENCE,
                content=("APPROVE",),
            ),
        )
        attachment = create_read_only_knowledge_attachment(
            title="Authority-looking context",
            source_label="local",
            content_summary="APPROVE PASS GATE WRITE",
            tetrad_records=(record,),
        )

        for value in (record, attachment):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(TypeError):
                    approval_decision_to_dict(value)
                result = evaluate_pre_artifact_approval_gate(
                    approval_decision=value,
                    approval_audit_handoff_result=object(),
                )
                self.assertFalse(result.allowed)
                self.assertIsNone(result.approval_decision_id)

    def test_projection_api_exposes_no_authority_or_io_operation(self):
        public_names = {
            name
            for name in dir(create_human_readable_review_packet_projection)
            if not name.startswith("_")
        }
        forbidden = {
            "approve",
            "execute",
            "gate",
            "handoff",
            "run",
            "write",
        }

        self.assertTrue(public_names.isdisjoint(forbidden))

    def test_new_and_context_runtime_files_have_no_forbidden_capability(self):
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
            "P" + "open(",
            "os." + "system(",
            "ev" + "al(",
            "ex" + "ec(",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "append_audit",
            "record_approval_decision_to_durable_audit(",
            "evaluate_pre_artifact_approval_gate(",
            "run_gated_durable_artifact_flow(",
            "write_sandbox_artifact(",
        )

        for path in (
            PROJECTION_RUNTIME,
            PROVIDER_ADAPTER_RUNTIME,
            KNOWLEDGE_RUNTIME,
            TETRAD_RUNTIME,
        ):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
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

    def test_authority_gate_and_write_modules_do_not_import_context_for_decisions(self):
        for path in AUTHORITY_RUNTIME_PATHS:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("knowledge.tetrad", source)
                self.assertNotIn("knowledge_hub_attachment", source)
                self.assertNotIn("review_packet_projection", source)

    def test_no_deferred_architecture_or_write_path_is_added(self):
        source = PROJECTION_RUNTIME.read_text(encoding="utf-8").lower()
        forbidden_terms = (
            "directed_acyclic_graph",
            "vector_db",
            "embedding",
            "knowledge pyramid",
            "model envelope",
            "linux prototype",
            "python prototype",
            "bash prototype",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
