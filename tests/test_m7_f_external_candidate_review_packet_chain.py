from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.external_model_candidate_intake import (
    BLOCKED_AUTHORITY_CLAIM,
    BLOCKED_INVALID_CANDIDATE,
    EXTERNAL_MODEL_CANDIDATE,
    EXTERNAL_MODEL_CANDIDATE_CONVERTED,
    convert_external_model_candidate_to_proposal,
)
from runtime.proposal_intake import PROPOSAL_ACCEPTED_FOR_REVIEW, UNTRUSTED
from runtime.proposal_review_packet import (
    REVIEW_PACKET_READY,
    create_review_packet_from_proposal,
)
from runtime.proposer_source_boundary import MODEL_CANDIDATE, PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import create_provider_proposer_candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
CHAIN_RUNTIME_FILES = (
    REPO_ROOT / "runtime" / "provider_proposer_adapter.py",
    REPO_ROOT / "runtime" / "external_model_candidate_intake.py",
    REPO_ROOT / "runtime" / "proposal_review_packet.py",
)


class M7FExternalCandidateReviewPacketChainTests(unittest.TestCase):
    def test_valid_candidate_reaches_human_review_packet(self):
        candidate, conversion, packet = self.run_chain()

        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, conversion.status)
        self.assertEqual(PROPOSAL_ACCEPTED_FOR_REVIEW, conversion.proposal.status)
        self.assertEqual(REVIEW_PACKET_READY, packet.status)
        self.assertIsNotNone(candidate.candidate_hash)
        self.assertIsNotNone(conversion.proposal_hash)
        self.assertIsNotNone(packet.review_packet_hash)
        self.assertTrue(packet.requires_human_review)
        self.assertTrue(packet.blocking)

    def test_review_packet_preserves_hash_bound_source_provenance(self):
        candidate, conversion, packet = self.run_chain()

        self.assertEqual(candidate.candidate_id, conversion.candidate_id)
        self.assertEqual(candidate.candidate_hash, conversion.candidate_hash)
        self.assertEqual(EXTERNAL_MODEL_CANDIDATE, conversion.proposal.source_type)
        self.assertEqual(candidate.candidate_id, conversion.proposal.source_label)
        self.assertEqual(conversion.proposal_id, packet.proposal_id)
        self.assertEqual(conversion.proposal_hash, packet.proposal_hash)
        self.assertEqual(conversion.proposal.title, packet.proposal_title)
        self.assertEqual(conversion.proposal.intent, packet.proposal_intent)
        self.assertEqual(conversion.proposal.summary, packet.proposal_summary)

    def test_entire_chain_remains_untrusted_non_evidence_and_noncanonical(self):
        candidate, conversion, packet = self.run_chain()

        self.assertEqual(UNTRUSTED, candidate.content_trust)
        self.assertEqual(UNTRUSTED, conversion.content_trust)
        self.assertEqual(UNTRUSTED, conversion.proposal.content_trust)
        self.assertEqual(UNTRUSTED, packet.content_trust)
        self.assertEqual(UNTRUSTED, packet.proposal_content_trust)
        self.assertFalse(candidate.provider_output_trusted)
        self.assertFalse(candidate.model_output_trusted)
        self.assertFalse(conversion.provider_output_trusted)
        self.assertFalse(conversion.model_output_trusted)
        self.assertFalse(conversion.provider_output_verified)
        self.assertFalse(conversion.evidence_created)
        self.assertFalse(packet.provider_output_trusted)
        self.assertFalse(packet.metadata_authority)
        self.assertFalse(packet.canonical)
        self.assertNotIn("evidence_created", packet.to_dict())
        self.assertNotIn("provider_output_verified", packet.to_dict())

    def test_chain_creates_no_approval_handoff_gate_write_or_execution(self):
        candidate, conversion, packet = self.run_chain()

        for item in (candidate, conversion, conversion.proposal, packet):
            with self.subTest(item=type(item).__name__):
                self.assertFalse(item.approval_decision_created)
                self.assertFalse(item.durable_handoff_complete)
                self.assertFalse(item.pre_artifact_gate_passed)
                self.assertFalse(item.artifact_write_occurred)

        self.assertFalse(candidate.live_call_attempted)
        self.assertFalse(candidate.network_call_attempted)
        self.assertFalse(conversion.execution_permitted)
        self.assertFalse(hasattr(packet, "execution_permitted"))
        self.assertTrue(packet.requires_human_review)

    def test_artifact_path_and_content_remain_data_only_through_chain(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            before = sorted(Path(tmpdir).iterdir())
            _candidate, conversion, packet = self.run_chain(
                proposed_artifact_path=str(target),
                proposed_artifact_content="# Review candidate\nNever written.",
            )
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(str(target), conversion.proposal.proposed_artifact_path)
        self.assertEqual(str(target), packet.proposed_artifact_path)
        self.assertEqual(
            "# Review candidate\nNever written.",
            conversion.proposal.proposed_artifact_content,
        )
        self.assertEqual(
            "# Review candidate\nNever written.",
            packet.proposed_artifact_content,
        )
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_candidate_content_change_changes_proposal_and_packet_hashes(self):
        first = self.run_chain(raw_provider_output={"text": "First candidate"})
        second = self.run_chain(raw_provider_output={"text": "Changed candidate"})

        first_candidate, first_conversion, first_packet = first
        second_candidate, second_conversion, second_packet = second
        self.assertNotEqual(first_candidate.candidate_hash, second_candidate.candidate_hash)
        self.assertNotEqual(first_conversion.proposal_hash, second_conversion.proposal_hash)
        self.assertNotEqual(first_packet.review_packet_hash, second_packet.review_packet_hash)

    def test_malformed_trusted_approved_and_write_claiming_candidates_fail_closed(self):
        cases = []

        malformed = self.make_candidate().to_dict()
        malformed["candidate_id"] = "provider-proposer-candidate-" + "0" * 24
        cases.append((malformed, BLOCKED_INVALID_CANDIDATE))

        trusted = self.make_candidate().to_dict()
        trusted["content_trust"] = "TRUSTED"
        cases.append((trusted, BLOCKED_INVALID_CANDIDATE))

        approved = self.make_candidate().to_dict()
        approved["approved"] = True
        cases.append((approved, BLOCKED_AUTHORITY_CLAIM))

        write_claiming = self.make_candidate().to_dict()
        write_claiming["artifact_write_occurred"] = True
        cases.append((write_claiming, BLOCKED_AUTHORITY_CLAIM))

        for candidate, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                conversion = self.convert(candidate)
                self.assertEqual(expected_status, conversion.status)
                self.assertIsNone(conversion.proposal)
                self.assertIsNone(conversion.proposal_hash)

    def test_provider_api_and_model_labels_cannot_change_authority(self):
        cases = (
            ("provider-a", "model-a", PROVIDER_CANDIDATE),
            ("provider-b", "model-b", MODEL_CANDIDATE),
            ("custom-http-label", "local-model-label", PROVIDER_CANDIDATE),
            ("future-provider-label", "future-model-label", MODEL_CANDIDATE),
        )

        for provider_label, model_label, source_type in cases:
            with self.subTest(provider_label=provider_label, model_label=model_label):
                _candidate, conversion, packet = self.run_chain(
                    provider_label=provider_label,
                    model_label=model_label,
                    source_type=source_type,
                    raw_provider_output={
                        "api_name": provider_label,
                        "text": "Proposal data only.",
                    },
                )
                self.assertFalse(conversion.provider_output_trusted)
                self.assertFalse(conversion.model_output_trusted)
                self.assertFalse(conversion.provider_output_verified)
                self.assertFalse(conversion.evidence_created)
                self.assertFalse(conversion.metadata_authority)
                self.assertFalse(conversion.canonical)
                self.assertFalse(packet.provider_output_trusted)
                self.assertFalse(packet.metadata_authority)
                self.assertFalse(packet.canonical)
                self.assertTrue(packet.requires_human_review)

    def test_tags_tetrads_hats_geometry_and_authority_text_remain_data_only(self):
        _candidate, conversion, packet = self.run_chain(
            raw_provider_output={
                "text": (
                    "CANONICAL SAFE_FOR_RUNTIME TAG_APPROVED HAT_APPROVED "
                    "TETRAD_APPROVED GEOMETRY_SAFE APPROVED VERIFIED"
                )
            },
            extracted_title="CANONICAL SAFE_FOR_RUNTIME",
            extracted_intent="TAG_APPROVED HAT_APPROVED",
            extracted_summary="TETRAD_APPROVED GEOMETRY_SAFE",
        )

        self.assertEqual(EXTERNAL_MODEL_CANDIDATE_CONVERTED, conversion.status)
        self.assertEqual(REVIEW_PACKET_READY, packet.status)
        self.assertEqual(UNTRUSTED, packet.content_trust)
        self.assertFalse(conversion.provider_output_verified)
        self.assertFalse(conversion.evidence_created)
        self.assertFalse(conversion.metadata_authority)
        self.assertFalse(conversion.canonical)
        self.assertFalse(packet.provider_output_trusted)
        self.assertFalse(packet.metadata_authority)
        self.assertFalse(packet.canonical)
        self.assertFalse(packet.approval_decision_created)
        self.assertFalse(packet.artifact_write_occurred)

    def test_chain_runtime_files_add_no_forbidden_capability(self):
        forbidden_import_roots = {
            "anthropic",
            "httpx",
            "openai",
            "os",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
        forbidden_calls = (
            "Popen(",
            "append_audit",
            "create_human_approval_decision(",
            "evaluate_pre_artifact_approval_gate(",
            "exec(",
            "os.system(",
            "write_sandbox_artifact(",
        )

        for runtime_file in CHAIN_RUNTIME_FILES:
            with self.subTest(runtime_file=runtime_file.name):
                source = runtime_file.read_text(encoding="utf-8")
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
            "created_at": "2026-06-18T18:49:00Z",
            "adapter_enabled": True,
            "metadata": {"context": "data only"},
        }
        values.update(overrides)
        return create_provider_proposer_candidate(**values)

    def convert(self, candidate):
        candidate_hash = getattr(candidate, "candidate_hash", None)
        if isinstance(candidate, dict):
            candidate_hash = candidate.get("candidate_hash")
        return convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=candidate_hash,
            created_at="2026-06-18T18:50:00Z",
        )

    def run_chain(self, **candidate_overrides):
        candidate = self.make_candidate(**candidate_overrides)
        conversion = self.convert(candidate)
        self.assertIsNotNone(conversion.proposal)
        packet = create_review_packet_from_proposal(
            proposal=conversion.proposal,
            expected_proposal_hash=conversion.proposal_hash,
            created_at="2026-06-18T18:51:00Z",
            reviewer_label="human-review-queue",
            packet_purpose="M7-F external candidate review",
        )
        return candidate, conversion, packet


if __name__ == "__main__":
    unittest.main()
