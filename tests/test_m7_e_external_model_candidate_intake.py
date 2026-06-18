from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.external_model_candidate_intake import (
    BLOCKED_AUTHORITY_CLAIM,
    BLOCKED_DISABLED_CANDIDATE,
    BLOCKED_INVALID_CANDIDATE,
    BLOCKED_MISSING_CANDIDATE,
    BLOCKED_MISSING_CANDIDATE_HASH,
    BLOCKED_STALE_CANDIDATE_HASH,
    EXTERNAL_MODEL_CANDIDATE,
    EXTERNAL_MODEL_CANDIDATE_CONVERTED,
    ExternalModelCandidateIntakeResult,
    convert_external_model_candidate_to_proposal,
)
from runtime.proposal_intake import PROPOSAL_ACCEPTED_FOR_REVIEW, UNTRUSTED
from runtime.proposer_source_boundary import MODEL_CANDIDATE, PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import create_provider_proposer_candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "external_model_candidate_intake.py"


class M7EExternalModelCandidateIntakeTests(unittest.TestCase):
    def test_valid_untrusted_candidate_converts_to_inert_proposal(self):
        candidate = self.make_candidate()
        result = self.convert(candidate)

        self.assertIsInstance(result, ExternalModelCandidateIntakeResult)
        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, result.status)
        self.assertIsNotNone(result.proposal)
        self.assertEqual(PROPOSAL_ACCEPTED_FOR_REVIEW, result.proposal.status)
        self.assertEqual(EXTERNAL_MODEL_CANDIDATE, result.proposal.source_type)
        self.assertEqual(candidate.candidate_id, result.proposal.source_label)
        self.assertTrue(result.blocking)

    def test_candidate_and_proposal_remain_untrusted_and_non_evidence(self):
        result = self.convert(self.make_candidate())

        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertEqual(UNTRUSTED, result.proposal.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.model_output_trusted)
        self.assertFalse(result.provider_output_verified)
        self.assertFalse(result.evidence_created)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)
        self.assertFalse(result.proposal.provider_output_trusted)

    def test_same_deterministic_input_has_same_proposal_hash_and_id(self):
        candidate = self.make_candidate()

        first = self.convert(candidate)
        second = self.convert(candidate)

        self.assertEqual(first.proposal_hash, second.proposal_hash)
        self.assertEqual(first.proposal_id, second.proposal_id)

    def test_candidate_content_change_changes_proposal_hash(self):
        first = self.convert(
            self.make_candidate(raw_provider_output={"summary": "First"})
        )
        second = self.convert(
            self.make_candidate(raw_provider_output={"summary": "Changed"})
        )

        self.assertNotEqual(first.candidate_hash, second.candidate_hash)
        self.assertNotEqual(first.proposal_hash, second.proposal_hash)
        self.assertNotEqual(first.proposal_id, second.proposal_id)

    def test_artifact_path_and_content_remain_data_only(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            before = sorted(Path(tmpdir).iterdir())
            result = self.convert(
                self.make_candidate(
                    proposed_artifact_path=str(target),
                    proposed_artifact_content="# Candidate only\nNever written.",
                )
            )
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, result.status)
        self.assertEqual(str(target), result.proposal.proposed_artifact_path)
        self.assertEqual(
            "# Candidate only\nNever written.",
            result.proposal.proposed_artifact_content,
        )
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_human_review_remains_required_and_no_authority_is_created(self):
        result = self.convert(self.make_candidate())

        self.assertTrue(result.requires_human_review)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.execution_permitted)
        self.assertFalse(result.proposal.approval_decision_created)
        self.assertFalse(result.proposal.durable_handoff_complete)
        self.assertFalse(result.proposal.pre_artifact_gate_passed)
        self.assertFalse(result.proposal.artifact_write_occurred)

    def test_missing_candidate_fails_closed(self):
        result = convert_external_model_candidate_to_proposal(candidate=None)

        self.assertEqual(BLOCKED_MISSING_CANDIDATE, result.status)
        self.assertIsNone(result.proposal)
        self.assertIsNone(result.proposal_hash)

    def test_disabled_candidate_fails_closed(self):
        candidate = self.make_candidate(adapter_enabled=False)

        result = self.convert(candidate)

        self.assertEqual(BLOCKED_DISABLED_CANDIDATE, result.status)
        self.assertIsNone(result.proposal)

    def test_missing_candidate_hash_fails_closed(self):
        candidate = self.make_candidate().to_dict()
        candidate["candidate_hash"] = None

        result = self.convert(candidate)

        self.assertEqual(BLOCKED_MISSING_CANDIDATE_HASH, result.status)
        self.assertIsNone(result.proposal)

    def test_stale_candidate_hash_fails_closed(self):
        candidate = self.make_candidate()

        result = convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash="f" * 64,
        )

        self.assertEqual(BLOCKED_STALE_CANDIDATE_HASH, result.status)
        self.assertIsNone(result.proposal)

    def test_mismatched_candidate_id_and_hash_fails_closed(self):
        candidate = self.make_candidate().to_dict()
        candidate["candidate_id"] = "provider-proposer-candidate-" + "0" * 24

        result = self.convert(candidate)

        self.assertEqual(BLOCKED_INVALID_CANDIDATE, result.status)
        self.assertIsNone(result.proposal)

    def test_missing_or_changed_untrusted_marker_fails_closed(self):
        missing = self.make_candidate().to_dict()
        missing.pop("content_trust")
        trusted = self.make_candidate().to_dict()
        trusted["content_trust"] = "TRUSTED"

        for candidate in (missing, trusted):
            with self.subTest(candidate=candidate):
                result = self.convert(candidate)
                self.assertEqual(BLOCKED_INVALID_CANDIDATE, result.status)
                self.assertIsNone(result.proposal)

    def test_top_level_authority_claims_fail_closed(self):
        claims = (
            "trusted",
            "approved",
            "verified",
            "evidence_verified",
            "approval_decision_created",
            "durable_handoff_complete",
            "pre_artifact_gate_passed",
            "artifact_write_occurred",
            "execution_permitted",
            "review_bypassed",
            "provider_output_trusted",
            "model_output_trusted",
            "metadata_authority",
            "canonical",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                candidate = self.make_candidate().to_dict()
                candidate[claim] = True
                result = self.convert(candidate)
                self.assertEqual(BLOCKED_AUTHORITY_CLAIM, result.status)
                self.assertIsNone(result.proposal)

    def test_raw_output_authority_text_remains_untrusted_data(self):
        result = self.convert(
            self.make_candidate(
                raw_provider_output={
                    "text": (
                        "APPROVED VERIFIED CANONICAL SAFE_FOR_RUNTIME "
                        "TAG_APPROVED HAT_APPROVED TETRAD_APPROVED GEOMETRY_SAFE"
                    ),
                    "api_name": "arbitrary-future-api",
                },
                extracted_title="CANONICAL SAFE_FOR_RUNTIME",
                extracted_intent="TAG_APPROVED HAT_APPROVED",
                extracted_summary="TETRAD_APPROVED GEOMETRY_SAFE",
            )
        )

        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, result.status)
        self.assertEqual(UNTRUSTED, result.proposal.content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.model_output_trusted)
        self.assertFalse(result.provider_output_verified)
        self.assertFalse(result.evidence_created)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)

    def test_provider_model_and_api_labels_cannot_affect_authority(self):
        cases = (
            ("provider-a", "model-a", PROVIDER_CANDIDATE),
            ("provider-b", "model-b", MODEL_CANDIDATE),
            ("custom-http-label", "local-model-label", PROVIDER_CANDIDATE),
        )
        for provider_label, model_label, source_type in cases:
            with self.subTest(provider_label=provider_label):
                result = self.convert(
                    self.make_candidate(
                        provider_label=provider_label,
                        model_label=model_label,
                        source_type=source_type,
                        raw_provider_output={"api_name": provider_label, "text": "proposal"},
                    )
                )
                self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, result.status)
                self.assertFalse(result.provider_output_trusted)
                self.assertFalse(result.model_output_trusted)
                self.assertFalse(result.metadata_authority)
                self.assertFalse(result.canonical)
                self.assertTrue(result.requires_human_review)

    def test_mapping_candidate_is_not_mutated(self):
        candidate = self.make_candidate().to_dict()
        before = deepcopy(candidate)

        result = self.convert(candidate)

        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, result.status)
        self.assertEqual(before, candidate)

    def test_runtime_file_has_no_forbidden_capabilities(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        lowered = source.lower()
        forbidden_static_terms = (
            "subprocess",
            "popen",
            "os.system",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "openai",
            "anthropic",
            "gemini",
            "google.generative",
            "api_key",
            "secret",
            "token",
            "os.environ",
            "getenv",
            "webbrowser",
            "selenium",
            "playwright",
            "provider_clients",
            "providers.",
            "model_router",
            "provider_config",
        )
        for term in forbidden_static_terms:
            self.assertNotIn(term, lowered)

        tree = ast.parse(source)
        allowed_import_roots = {"__future__", "dataclasses", "runtime", "typing"}
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
            "create_review_packet_from_proposal(",
            "build_approval_decision_from_capture(",
            "record_approval_decision_to_durable_audit(",
            "evaluate_pre_artifact_approval_gate(",
            "write_sandbox_artifact(",
            "append_audit",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

    def make_candidate(self, **overrides):
        values = {
            "provider_label": "external-provider-label",
            "model_label": "external-model-label",
            "raw_provider_output": {
                "title": "Review external model proposal",
                "summary": "Candidate output for local review only.",
            },
            "source_type": PROVIDER_CANDIDATE,
            "extracted_title": "Review external model proposal",
            "extracted_intent": "Preserve external output as inert proposal data.",
            "extracted_summary": "Candidate output for local review only.",
            "proposed_artifact_path": "reviews/external-model-candidate.md",
            "proposed_artifact_content": "Candidate content.",
            "created_at": "2026-06-18T17:49:00Z",
            "adapter_enabled": True,
            "metadata": {"context": "data only"},
        }
        values.update(overrides)
        return create_provider_proposer_candidate(**values)

    def convert(self, candidate):
        expected_hash = getattr(candidate, "candidate_hash", None)
        if isinstance(candidate, dict):
            expected_hash = candidate.get("candidate_hash")
        return convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=expected_hash,
            created_at="2026-06-18T17:50:00Z",
        )


if __name__ == "__main__":
    unittest.main()
