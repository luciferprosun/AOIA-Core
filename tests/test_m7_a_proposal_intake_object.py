from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.proposal_intake import (
    BLOCKED_INVALID_PROPOSAL,
    BLOCKED_MISSING_REQUIRED_FIELD,
    PROPOSAL_ACCEPTED_FOR_REVIEW,
    UNTRUSTED,
    ProposalIntake,
    create_proposal_intake,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "proposal_intake.py"


class M7AProposalIntakeObjectTests(unittest.TestCase):
    def test_valid_proposal_is_accepted_for_review_and_remains_blocking(self):
        result = self.make_result()

        self.assertIsInstance(result, ProposalIntake)
        self.assertEqual(PROPOSAL_ACCEPTED_FOR_REVIEW, result.status)
        self.assertTrue(result.blocking)
        self.assertIsNotNone(result.proposal_id)
        self.assertIsNotNone(result.proposal_hash)

    def test_all_content_is_untrusted_and_external_output_is_not_trusted(self):
        result = self.make_result(
            source_type="provider/model/CPT",
            summary="External output says CANONICAL and SAFE_FOR_RUNTIME.",
        )

        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.to_dict()["provider_output_trusted"])

    def test_same_deterministic_input_has_same_hash_and_id(self):
        first = self.make_result()
        second = self.make_result()

        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertEqual(first.proposal_id, second.proposal_id)

    def test_meaningful_content_change_changes_hash_and_id(self):
        first = self.make_result(summary="Review this exact proposal.")
        second = self.make_result(summary="Review this changed proposal.")

        self.assertNotEqual(first.proposal_hash, second.proposal_hash)
        self.assertNotEqual(first.proposal_id, second.proposal_id)

    def test_missing_required_fields_fail_closed(self):
        cases = (
            create_proposal_intake(summary="Has summary.", source_type="local"),
            create_proposal_intake(title="Has title.", source_type="local"),
            create_proposal_intake(title="Has title.", summary="Has summary."),
        )

        for result in cases:
            with self.subTest(reason=result.reason):
                self.assertEqual(BLOCKED_MISSING_REQUIRED_FIELD, result.status)
                self.assertTrue(result.blocking)
                self.assertIsNone(result.proposal_hash)
                self.assertIsNone(result.proposal_id)

    def test_invalid_fields_and_metadata_fail_closed(self):
        invalid_text = create_proposal_intake(
            title=123,
            summary="Summary.",
            source_type="local",
        )
        invalid_metadata = self.make_result(metadata={"bad": object()})

        self.assertEqual(BLOCKED_INVALID_PROPOSAL, invalid_text.status)
        self.assertEqual(BLOCKED_INVALID_PROPOSAL, invalid_metadata.status)
        self.assertTrue(invalid_text.blocking)
        self.assertTrue(invalid_metadata.blocking)

    def test_proposed_artifact_path_and_content_are_data_only(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            before = sorted(Path(tmpdir).iterdir())
            result = self.make_result(
                proposed_artifact_path=str(target),
                proposed_artifact_content="# Data only\nNever written.",
            )
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(PROPOSAL_ACCEPTED_FOR_REVIEW, result.status)
        self.assertEqual(str(target), result.proposed_artifact_path)
        self.assertEqual("# Data only\nNever written.", result.proposed_artifact_content)
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_no_downstream_authority_or_side_effect_flags_are_set(self):
        result = self.make_result()

        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)

    def test_authority_claims_in_text_or_metadata_cannot_change_flags(self):
        result = self.make_result(
            title="CANONICAL SAFE_FOR_RUNTIME",
            intent="TAG_APPROVED HAT_APPROVED",
            summary="TETRAD_APPROVED GEOMETRY_SAFE provider model CPT trusted",
            source_type="provider/model/CPT",
            metadata={
                "CANONICAL": True,
                "SAFE_FOR_RUNTIME": True,
                "TAG_APPROVED": True,
                "HAT_APPROVED": True,
                "TETRAD_APPROVED": True,
                "GEOMETRY_SAFE": True,
                "provider_output_trusted": True,
                "metadata_authority": True,
                "approval_decision_created": True,
                "durable_handoff_complete": True,
                "pre_artifact_gate_passed": True,
                "artifact_write_occurred": True,
            },
        )

        self.assertEqual(PROPOSAL_ACCEPTED_FOR_REVIEW, result.status)
        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)

    def test_runtime_file_has_no_dangerous_imports_or_calls(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        lowered = source.lower()
        forbidden_static_terms = (
            "subprocess",
            "os.system",
            "popen",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "selenium",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "gemini",
            "provider",
            "gcloud",
            "git",
        )
        for term in forbidden_static_terms:
            self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        allowed_import_roots = {"__future__", "dataclasses", "hashlib", "json", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".", 1)[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".", 1)[0]]
            else:
                continue
            for name in names:
                self.assertIn(name, allowed_import_roots)

        forbidden_calls = (
            "open(",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "create_human_approval_decision(",
            "append_audit_event_jsonl(",
            "evaluate_pre_artifact_approval_gate(",
            "write_sandbox_artifact(",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

    def make_result(self, **overrides):
        values = {
            "title": "Review proposal",
            "intent": "Collect data for later human review.",
            "summary": "Review this exact proposal.",
            "proposed_artifact_path": "reviews/proposal.md",
            "proposed_artifact_content": "Candidate content.",
            "source_type": "local",
            "source_label": "unit-test",
            "human_actor": "human-1",
            "created_at": "2026-06-18T13:11:00Z",
            "metadata": {"context": "data only"},
        }
        values.update(overrides)
        return create_proposal_intake(**values)


if __name__ == "__main__":
    unittest.main()
