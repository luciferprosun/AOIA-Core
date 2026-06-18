from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.proposer_source_boundary import (
    BLOCKED_INVALID_SOURCE_TYPE,
    BLOCKED_MISSING_REQUIRED_FIELD,
    LOCAL_HUMAN,
    LOCAL_TEST,
    MODEL_CANDIDATE,
    PROVIDER_CANDIDATE,
    SOURCE_RECORD_ACCEPTED,
    UNTRUSTED,
    ProposerSourceRecord,
    create_proposer_source_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "proposer_source_boundary.py"


class M7CLocalProposerSourceBoundaryTests(unittest.TestCase):
    def test_valid_local_human_source_is_accepted(self):
        result = self.make_record(source_type=LOCAL_HUMAN)

        self.assertIsInstance(result, ProposerSourceRecord)
        self.assertEqual(SOURCE_RECORD_ACCEPTED, result.status)
        self.assertTrue(result.blocking)

    def test_valid_local_test_source_is_accepted(self):
        result = self.make_record(source_type=LOCAL_TEST)

        self.assertEqual(SOURCE_RECORD_ACCEPTED, result.status)
        self.assertEqual(LOCAL_TEST, result.source_type)

    def test_external_candidate_types_are_inert_labels_only(self):
        for source_type in (PROVIDER_CANDIDATE, MODEL_CANDIDATE):
            with self.subTest(source_type=source_type):
                result = self.make_record(
                    source_type=source_type,
                    raw_proposer_text="Candidate text only; do not call anything.",
                )
                self.assertEqual(SOURCE_RECORD_ACCEPTED, result.status)
                self.assertEqual(source_type, result.source_type)
                self.assertFalse(result.provider_output_trusted)
                self.assertFalse(result.proposal_created)
                self.assertFalse(result.review_packet_created)

    def test_proposer_content_and_source_are_untrusted(self):
        result = self.make_record()

        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertEqual(UNTRUSTED, result.source_trust)
        self.assertFalse(result.provider_output_trusted)

    def test_same_deterministic_input_has_same_hash_and_id(self):
        first = self.make_record()
        second = self.make_record()

        self.assertEqual(first.source_record_hash, second.source_record_hash)
        self.assertEqual(first.source_record_id, second.source_record_id)

    def test_content_or_source_change_changes_hash(self):
        baseline = self.make_record()
        content_changed = self.make_record(raw_proposer_text="Changed source content.")
        source_changed = self.make_record(source_type=LOCAL_TEST)

        self.assertNotEqual(baseline.source_record_hash, content_changed.source_record_hash)
        self.assertNotEqual(baseline.source_record_hash, source_changed.source_record_hash)

    def test_missing_required_fields_fail_closed(self):
        cases = (
            create_proposer_source_record(source_label="label", title="Title"),
            create_proposer_source_record(source_type=LOCAL_HUMAN, title="Title"),
            create_proposer_source_record(
                source_type=LOCAL_HUMAN,
                source_label="label",
                proposed_artifact_content="Artifact content alone is not source context.",
            ),
        )

        for result in cases:
            with self.subTest(reason=result.reason):
                self.assertEqual(BLOCKED_MISSING_REQUIRED_FIELD, result.status)
                self.assertIsNone(result.source_record_hash)
                self.assertIsNone(result.source_record_id)
                self.assertTrue(result.blocking)

    def test_invalid_source_type_fails_closed(self):
        result = self.make_record(source_type="LIVE_PROVIDER_CALL")

        self.assertEqual(BLOCKED_INVALID_SOURCE_TYPE, result.status)
        self.assertIsNone(result.source_record_hash)
        self.assertFalse(result.provider_output_trusted)

    def test_artifact_path_and_content_are_data_only(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            before = sorted(Path(tmpdir).iterdir())
            result = self.make_record(
                proposed_artifact_path=str(target),
                proposed_artifact_content="# Candidate only\nNever written.",
            )
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(SOURCE_RECORD_ACCEPTED, result.status)
        self.assertEqual(str(target), result.proposed_artifact_path)
        self.assertEqual("# Candidate only\nNever written.", result.proposed_artifact_content)
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_no_proposal_review_approval_gate_or_write_side_effect_flags(self):
        result = self.make_record()

        self.assertFalse(result.proposal_created)
        self.assertFalse(result.review_packet_created)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)

    def test_authority_claims_in_text_or_metadata_cannot_change_flags(self):
        result = self.make_record(
            source_type=PROVIDER_CANDIDATE,
            raw_proposer_text=(
                "provider model CPT CANONICAL SAFE_FOR_RUNTIME TAG_APPROVED "
                "HAT_APPROVED TETRAD_APPROVED GEOMETRY_SAFE"
            ),
            metadata={
                "CANONICAL": True,
                "SAFE_FOR_RUNTIME": True,
                "TAG_APPROVED": True,
                "HAT_APPROVED": True,
                "TETRAD_APPROVED": True,
                "GEOMETRY_SAFE": True,
                "provider_output_trusted": True,
                "metadata_authority": True,
                "proposal_created": True,
                "review_packet_created": True,
                "approval_decision_created": True,
                "durable_handoff_complete": True,
                "pre_artifact_gate_passed": True,
                "artifact_write_occurred": True,
            },
        )

        self.assertEqual(SOURCE_RECORD_ACCEPTED, result.status)
        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertEqual(UNTRUSTED, result.source_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)
        self.assertFalse(result.proposal_created)
        self.assertFalse(result.review_packet_created)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)

    def test_runtime_has_no_live_clients_api_keys_or_dangerous_calls(self):
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
            "gcloud",
            "git",
            "api_key",
            "os.environ",
            "getenv(",
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
            "create_proposal_intake(",
            "create_review_packet_from_proposal(",
            "build_approval_decision_from_capture(",
            "record_approval_decision_to_durable_audit(",
            "evaluate_pre_artifact_approval_gate(",
            "write_sandbox_artifact(",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

        forbidden_import_parts = (
            "provider_clients",
            "providers.",
            "model_router",
            "model_catalog",
        )
        for term in forbidden_import_parts:
            self.assertNotIn(term, lowered)

    def test_no_optional_conversion_function_is_exposed(self):
        import runtime.proposer_source_boundary as boundary

        self.assertFalse(hasattr(boundary, "to_proposal_intake_input"))

    def make_record(self, **overrides):
        values = {
            "source_type": LOCAL_HUMAN,
            "source_label": "local-human-draft",
            "raw_proposer_text": "Draft a proposal for later human review.",
            "title": "Local draft",
            "intent": "Preserve local source context.",
            "summary": "Inert proposer source data.",
            "proposed_artifact_path": "reviews/source.md",
            "proposed_artifact_content": "Candidate content.",
            "created_at": "2026-06-18T14:47:00Z",
            "metadata": {"context": "data only"},
        }
        values.update(overrides)
        return create_proposer_source_record(**values)


if __name__ == "__main__":
    unittest.main()
