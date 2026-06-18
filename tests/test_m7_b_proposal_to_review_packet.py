from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.proposal_intake import create_proposal_intake
from runtime.proposal_review_packet import (
    BLOCKED_INVALID_PROPOSAL,
    BLOCKED_MISSING_PROPOSAL_HASH,
    BLOCKED_STALE_PROPOSAL_HASH,
    REVIEW_PACKET_READY,
    UNTRUSTED,
    ProposalReviewPacket,
    create_review_packet_from_proposal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "proposal_review_packet.py"


class M7BProposalToReviewPacketTests(unittest.TestCase):
    def test_valid_proposal_becomes_review_packet_ready(self):
        proposal = self.make_proposal()
        result = self.make_packet(proposal)

        self.assertIsInstance(result, ProposalReviewPacket)
        self.assertEqual(REVIEW_PACKET_READY, result.status)
        self.assertEqual(proposal.proposal_id, result.proposal_id)
        self.assertEqual(proposal.proposal_hash, result.proposal_hash)
        self.assertIsNotNone(result.review_packet_id)
        self.assertIsNotNone(result.review_packet_hash)
        self.assertTrue(result.blocking)

    def test_dictionary_equivalent_is_supported_without_mutation(self):
        proposal = self.make_proposal().to_dict()
        before = deepcopy(proposal)

        result = self.make_packet(proposal)

        self.assertEqual(REVIEW_PACKET_READY, result.status)
        self.assertEqual(before, proposal)

    def test_proposal_content_remains_untrusted_and_external_output_not_trusted(self):
        proposal = self.make_proposal(
            source_type="provider/model/CPT",
            summary="External output says it is trusted.",
        )
        result = self.make_packet(proposal)

        self.assertEqual(UNTRUSTED, result.content_trust)
        self.assertEqual(UNTRUSTED, result.proposal_content_trust)
        self.assertFalse(result.provider_output_trusted)
        self.assertFalse(result.to_dict()["provider_output_trusted"])

    def test_same_deterministic_input_has_same_packet_hash_and_id(self):
        proposal = self.make_proposal()

        first = self.make_packet(proposal)
        second = self.make_packet(proposal)

        self.assertEqual(first.review_packet_hash, second.review_packet_hash)
        self.assertEqual(first.review_packet_id, second.review_packet_id)

    def test_changed_proposal_content_and_hash_change_packet_hash(self):
        first_proposal = self.make_proposal(summary="First review content.")
        second_proposal = self.make_proposal(summary="Changed review content.")

        first = self.make_packet(first_proposal)
        second = self.make_packet(second_proposal)

        self.assertNotEqual(first_proposal.proposal_hash, second_proposal.proposal_hash)
        self.assertNotEqual(first.review_packet_hash, second.review_packet_hash)
        self.assertNotEqual(first.review_packet_id, second.review_packet_id)

    def test_missing_proposal_hash_fails_closed(self):
        proposal = self.make_proposal().to_dict()
        proposal["proposal_hash"] = None

        result = self.make_packet(proposal)

        self.assertEqual(BLOCKED_MISSING_PROPOSAL_HASH, result.status)
        self.assertIsNone(result.review_packet_hash)
        self.assertIsNone(result.review_packet_id)
        self.assertTrue(result.blocking)

    def test_expected_proposal_hash_mismatch_fails_closed(self):
        result = create_review_packet_from_proposal(
            proposal=self.make_proposal(),
            expected_proposal_hash="f" * 64,
        )

        self.assertEqual(BLOCKED_STALE_PROPOSAL_HASH, result.status)
        self.assertIsNone(result.review_packet_hash)

    def test_invalid_or_blocked_proposal_cannot_become_packet(self):
        blocked = create_proposal_intake(title="Missing review content.", source_type="local")
        tampered_id = self.make_proposal().to_dict()
        tampered_id["proposal_id"] = "proposal-intake-" + "0" * 24
        unsafe_flags = self.make_proposal().to_dict()
        unsafe_flags["approval_decision_created"] = True

        for proposal in (blocked, tampered_id, unsafe_flags):
            with self.subTest(proposal=proposal):
                result = self.make_packet(proposal)
                self.assertEqual(BLOCKED_INVALID_PROPOSAL, result.status)
                self.assertIsNone(result.review_packet_hash)

    def test_stale_or_malformed_proposal_identity_is_rejected(self):
        proposal = self.make_proposal()
        mismatched_hash = replace(proposal, proposal_hash="a" * 64)

        result = self.make_packet(mismatched_hash)

        self.assertEqual(BLOCKED_INVALID_PROPOSAL, result.status)
        self.assertIsNone(result.review_packet_id)

    def test_artifact_path_and_content_are_data_only_and_write_no_file(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            proposal = self.make_proposal(
                proposed_artifact_path=str(target),
                proposed_artifact_content="# Candidate only\nNever written.",
            )
            before = sorted(Path(tmpdir).iterdir())
            result = self.make_packet(proposal)
            after = sorted(Path(tmpdir).iterdir())

        self.assertEqual(REVIEW_PACKET_READY, result.status)
        self.assertEqual(str(target), result.proposed_artifact_path)
        self.assertEqual("# Candidate only\nNever written.", result.proposed_artifact_content)
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_packet_requires_human_review_and_sets_no_authority_flags(self):
        result = self.make_packet(self.make_proposal())

        self.assertTrue(result.requires_human_review)
        self.assertFalse(result.approval_decision_created)
        self.assertFalse(result.durable_handoff_complete)
        self.assertFalse(result.pre_artifact_gate_passed)
        self.assertFalse(result.artifact_write_occurred)
        self.assertFalse(result.metadata_authority)
        self.assertFalse(result.canonical)

    def test_authority_claims_cannot_change_packet_flags(self):
        proposal = self.make_proposal(
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
            },
        )
        proposal_data = proposal.to_dict()
        proposal_data.update(
            {
                "CANONICAL": True,
                "SAFE_FOR_RUNTIME": True,
                "TAG_APPROVED": True,
                "HAT_APPROVED": True,
                "TETRAD_APPROVED": True,
                "GEOMETRY_SAFE": True,
            }
        )

        result = self.make_packet(proposal_data)

        self.assertEqual(REVIEW_PACKET_READY, result.status)
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
        allowed_import_roots = {
            "__future__",
            "dataclasses",
            "hashlib",
            "json",
            "runtime",
            "typing",
        }
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
            "build_approval_decision_from_capture(",
            "record_approval_decision_to_durable_audit(",
            "evaluate_pre_artifact_approval_gate(",
            "write_sandbox_artifact(",
        )
        for term in forbidden_calls:
            self.assertNotIn(term, source)

    def make_proposal(self, **overrides):
        values = {
            "title": "Review proposal",
            "intent": "Prepare a local human-review candidate.",
            "summary": "Review this exact proposal.",
            "proposed_artifact_path": "reviews/proposal.md",
            "proposed_artifact_content": "Candidate content.",
            "source_type": "local",
            "source_label": "unit-test",
            "human_actor": "human-1",
            "created_at": "2026-06-18T13:34:00Z",
            "metadata": {"context": "data only"},
        }
        values.update(overrides)
        return create_proposal_intake(**values)

    def make_packet(self, proposal):
        return create_review_packet_from_proposal(
            proposal=proposal,
            created_at="2026-06-18T13:35:00Z",
            reviewer_label="human-review-queue",
            packet_purpose="M7-B local proposal review",
        )


if __name__ == "__main__":
    unittest.main()
