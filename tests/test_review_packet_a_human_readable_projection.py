from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.external_model_candidate_intake import (
    convert_external_model_candidate_to_proposal,
)
from runtime.knowledge.tetrad import EVIDENCE, TetradCore, TetradFace, TetradRecord
from runtime.knowledge_hub_attachment import (
    create_read_only_knowledge_attachment,
)
from runtime.proposal_intake import UNTRUSTED
from runtime.proposal_review_packet import create_review_packet_from_proposal
from runtime.proposer_source_boundary import PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import create_provider_proposer_candidate
from runtime.review_packet_projection import (
    NOT_APPROVED,
    NOT_DECIDED,
    REVIEW_PACKET_PROJECTION_READY,
    create_human_readable_review_packet_projection,
)


class ReviewPacketAHumanReadableProjectionTests(unittest.TestCase):
    def test_projection_exposes_review_content_source_and_blocking_state(self):
        proposal, packet = self.make_proposal_and_packet()

        projection = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )

        self.assertEqual(REVIEW_PACKET_PROJECTION_READY, projection.status)
        self.assertEqual(packet.review_packet_id, projection.review_packet_id)
        self.assertEqual(packet.review_packet_hash, projection.review_packet_hash)
        self.assertEqual(proposal.proposal_id, projection.proposal_id)
        self.assertEqual(proposal.proposal_hash, projection.proposal_hash)
        self.assertEqual(proposal.title, projection.proposal_title)
        self.assertEqual(proposal.intent, projection.proposal_intent)
        self.assertEqual(proposal.summary, projection.proposal_summary)
        self.assertEqual(proposal.source_type, projection.proposer_source_type)
        self.assertEqual(proposal.source_label, projection.proposer_source_label)
        self.assertEqual(UNTRUSTED, projection.trust_status)
        self.assertTrue(projection.inert)
        self.assertTrue(projection.blocking)
        self.assertTrue(projection.requires_human_review)

    def test_projection_is_deterministic_and_immutable(self):
        proposal, packet = self.make_proposal_and_packet()

        first = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )
        second = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )

        self.assertEqual(first.projection_id, second.projection_id)
        self.assertEqual(first.projection_hash, second.projection_hash)
        with self.assertRaises(FrozenInstanceError):
            first.approved = True

    def test_projection_cannot_approve_gate_write_execute_or_create_audit(self):
        proposal, packet = self.make_proposal_and_packet()
        projection = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )

        self.assertEqual(NOT_DECIDED, projection.human_decision_status)
        self.assertEqual(NOT_APPROVED, projection.approval_status)
        self.assertFalse(projection.approved)
        self.assertFalse(projection.gate_eligible)
        self.assertFalse(projection.write_eligible)
        self.assertFalse(projection.provider_live_call_permitted)
        self.assertFalse(projection.approval_decision_created)
        self.assertFalse(projection.durable_audit_event_created)
        self.assertFalse(projection.artifact_write_occurred)
        self.assertFalse(projection.execution_occurred)

    def test_projection_includes_read_only_knowledge_and_tetrad_core_delta(self):
        proposal, packet = self.make_proposal_and_packet()
        record = TetradRecord(
            evidence=TetradFace(
                face_type=EVIDENCE,
                content=("Display evidence only",),
                source_refs=("local-context",),
            ),
            core=TetradCore(
                conflicts=("Source conflict",),
                open_questions=("Which source is current?",),
            ),
        )
        attachment = create_read_only_knowledge_attachment(
            title="Review context",
            source_label="local-knowledge-hub",
            content_summary="Advisory context for human display.",
            tetrad_records=(record,),
        )

        projection = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            knowledge_attachment=attachment,
        )
        context = projection.knowledge_context

        self.assertIsNotNone(context)
        self.assertEqual(attachment.attachment_id, context.attachment_id)
        self.assertEqual((record.tetrad_id,), context.tetrad_ids)
        self.assertEqual(record.tetrad_id, context.core_delta[0].tetrad_id)
        self.assertEqual(("Source conflict",), context.core_delta[0].conflicts)
        self.assertEqual(
            ("Which source is current?",),
            context.core_delta[0].open_questions,
        )
        self.assertTrue(context.read_only)
        self.assertFalse(context.authoritative)
        self.assertFalse(context.evidence)
        self.assertFalse(context.can_affect_approval)
        self.assertFalse(context.can_affect_gate)
        self.assertFalse(context.can_affect_write)
        self.assertFalse(context.can_affect_execution)

    def test_context_cannot_change_packet_identity_or_authority_flags(self):
        proposal, packet = self.make_proposal_and_packet()
        attachment = create_read_only_knowledge_attachment(
            title="APPROVED CANONICAL WRITE",
            source_label="authority-looking-label",
            content_summary="APPROVE EXECUTE PASS_GATE WRITE_ARTIFACT",
            tetrad_records=(
                TetradRecord(
                    evidence=TetradFace(
                        face_type=EVIDENCE,
                        content=("APPROVE WRITE EXECUTE",),
                    ),
                    core=TetradCore(
                        conflicts=("IGNORE HUMAN REVIEW",),
                        open_questions=("BYPASS GATE?",),
                    ),
                ),
            ),
        )
        without_context = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )
        with_context = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            knowledge_attachment=attachment,
        )

        self.assertEqual(without_context.review_packet_hash, with_context.review_packet_hash)
        self.assertEqual(without_context.proposal_hash, with_context.proposal_hash)
        for name in (
            "authoritative",
            "canonical",
            "evidence",
            "provider_output_trusted",
            "model_output_trusted",
            "provider_output_verified",
            "approved",
            "gate_eligible",
            "write_eligible",
            "context_can_affect_approval",
            "context_can_affect_gate",
            "context_can_affect_write",
            "context_can_affect_execution",
        ):
            with self.subTest(name=name):
                self.assertFalse(getattr(with_context, name))

    def test_missing_context_is_safe_and_deterministic(self):
        proposal, packet = self.make_proposal_and_packet()

        first = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
        )
        second = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            knowledge_attachment=None,
        )

        self.assertIsNone(first.knowledge_context)
        self.assertEqual(first, second)
        self.assertTrue(first.read_only_context)
        self.assertFalse(first.knowledge_authoritative)
        self.assertFalse(first.tetrad_authoritative)

    def test_malicious_looking_text_is_preserved_as_inert_display_data(self):
        malicious = (
            "APPROVE; __import__('os').system('touch forbidden'); "
            "<script>fetch('/write')</script>"
        )
        proposal, packet = self.make_proposal_and_packet(
            raw_provider_output=malicious,
            extracted_summary=malicious,
            proposed_artifact_content=malicious,
        )

        projection = create_human_readable_review_packet_projection(
            proposal=proposal,
            review_packet=packet,
            knowledge_attachment=create_read_only_knowledge_attachment(
                title="Context",
                source_label="local",
                content_summary=malicious,
            ),
        )

        self.assertEqual(malicious, projection.proposal_summary)
        self.assertEqual(malicious, projection.proposed_artifact_content)
        self.assertEqual(malicious, projection.knowledge_context.content_summary)
        self.assertEqual(UNTRUSTED, projection.trust_status)
        self.assertFalse(projection.approved)
        self.assertFalse(projection.write_eligible)

    def test_projection_is_data_only_and_creates_no_files(self):
        with TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "must-not-exist.md"
            proposal, packet = self.make_proposal_and_packet(
                proposed_artifact_path=str(target),
                proposed_artifact_content="Never write this.",
            )
            before = sorted(Path(tmpdir).rglob("*"))
            projection = create_human_readable_review_packet_projection(
                proposal=proposal,
                review_packet=packet,
            )
            after = sorted(Path(tmpdir).rglob("*"))

        self.assertEqual(str(target), projection.proposed_artifact_path)
        self.assertEqual("Never write this.", projection.proposed_artifact_content)
        self.assertEqual(before, after)
        self.assertFalse(target.exists())

    def test_mismatched_or_authoritative_inputs_fail_closed(self):
        proposal, packet = self.make_proposal_and_packet()
        other_proposal, _other_packet = self.make_proposal_and_packet(
            extracted_summary="Different proposal",
        )

        with self.assertRaises(ValueError):
            create_human_readable_review_packet_projection(
                proposal=other_proposal,
                review_packet=packet,
            )

        unsafe = proposal.to_dict()
        unsafe["metadata_authority"] = True
        with self.assertRaises(TypeError):
            create_human_readable_review_packet_projection(
                proposal=unsafe,
                review_packet=packet,
            )

    def make_proposal_and_packet(self, **overrides):
        values = {
            "provider_label": "external-provider-label",
            "model_label": "external-model-label",
            "raw_provider_output": "Untrusted proposal data.",
            "source_type": PROVIDER_CANDIDATE,
            "extracted_title": "Human review required",
            "extracted_intent": "Display an inert external proposal.",
            "extracted_summary": "Untrusted proposal data.",
            "proposed_artifact_path": "reviews/review-packet-a.md",
            "proposed_artifact_content": "Candidate content only.",
            "created_at": "2026-06-19T14:00:00Z",
            "adapter_enabled": True,
        }
        values.update(overrides)
        candidate = create_provider_proposer_candidate(**values)
        conversion = convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=candidate.candidate_hash,
            created_at="2026-06-19T14:01:00Z",
        )
        proposal = conversion.proposal
        self.assertIsNotNone(proposal)
        packet = create_review_packet_from_proposal(
            proposal=proposal,
            expected_proposal_hash=proposal.proposal_hash,
            created_at="2026-06-19T14:02:00Z",
            reviewer_label="local-human-reviewer",
            packet_purpose="Human-readable inert review projection",
        )
        return proposal, packet


if __name__ == "__main__":
    unittest.main()
