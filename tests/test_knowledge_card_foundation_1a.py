from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from runtime.memory.evidence_link import KnowledgeEvidenceLink
from runtime.memory.knowledge_card import KnowledgeCard
from runtime.memory.knowledge_claim import KnowledgeClaim
from runtime.memory.knowledge_source import KnowledgeSource
from runtime.memory.provenance import KnowledgeProvenance
from runtime.memory.validation import KnowledgeValidationError, hash_knowledge_value


class KnowledgeCardFoundation1ATests(unittest.TestCase):
    def test_valid_knowledge_card_creation_succeeds(self):
        card = self.card()

        self.assertEqual(card.card_id, "kc-001")
        self.assertEqual(len(card.claims), 1)
        self.assertEqual(len(card.card_hash), 64)
        self.assertEqual(len(card.claims[0].claim_hash), 64)
        self.assertEqual(len(card.claims[0].sources[0].source_hash), 64)
        self.assertEqual(len(card.claims[0].evidence_links[0].evidence_hash), 64)

    def test_source_less_claim_fails_closed(self):
        evidence = self.evidence()

        with self.assertRaises(KnowledgeValidationError):
            KnowledgeClaim(
                claim_id="claim-no-source",
                statement="A reviewable claim needs source binding.",
                sources=(),
                evidence_links=(evidence,),
            )

    def test_evidence_less_claim_fails_closed(self):
        source = self.source()

        with self.assertRaises(KnowledgeValidationError):
            KnowledgeClaim(
                claim_id="claim-no-evidence",
                statement="A reviewable claim needs evidence binding.",
                sources=(source,),
                evidence_links=(),
            )

    def test_claim_hash_is_deterministic(self):
        self.assertEqual(self.claim().claim_hash, self.claim().claim_hash)
        self.assertNotEqual(self.claim().claim_hash, self.claim(statement="Different source-bound claim.").claim_hash)

    def test_source_hash_and_evidence_hash_are_deterministic(self):
        self.assertEqual(self.source().source_hash, self.source().source_hash)
        self.assertEqual(self.evidence().evidence_hash, self.evidence().evidence_hash)
        self.assertNotEqual(self.source().source_hash, self.source(description="Changed source.").source_hash)
        self.assertNotEqual(self.evidence().evidence_hash, self.evidence(excerpt="Changed evidence.").evidence_hash)

    def test_malformed_provenance_fails_closed(self):
        claim = self.claim()

        with self.assertRaises(KnowledgeValidationError):
            KnowledgeProvenance(
                provenance_id="prov-bad",
                card_id="kc-bad",
                source_hashes=("bad",),
                evidence_hashes=tuple(link.evidence_hash for link in claim.evidence_links),
                claim_hashes=(claim.claim_hash,),
                created_by="tester",
            )

    def test_model_output_cannot_become_authority(self):
        with self.assertRaises(KnowledgeValidationError):
            self.claim(author_type="model", metadata={"is_truth": True})

    def test_authority_flags_remain_false(self):
        card = self.card()
        objects = (
            card,
            card.provenance,
            card.claims[0],
            card.claims[0].sources[0],
            card.claims[0].evidence_links[0],
        )
        for item in objects:
            with self.subTest(item=type(item).__name__):
                self.assertFalse(item.can_execute)
                self.assertFalse(item.can_write)
                self.assertFalse(item.gate_satisfied)
                self.assertFalse(item.can_dispatch)
                self.assertFalse(item.can_approve)
                payload = item.to_dict()
                self.assertFalse(payload["can_execute"])
                self.assertFalse(payload["can_write"])
                self.assertFalse(payload["gate_satisfied"])
                self.assertFalse(payload["can_dispatch"])
                self.assertFalse(payload["can_approve"])

    def test_mutation_and_overwrite_are_rejected(self):
        claim = self.claim()

        with self.assertRaises(FrozenInstanceError):
            claim.statement = "overwrite"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            claim.sources = ()  # type: ignore[misc]

    def test_revision_requires_append_safe_representation(self):
        claim = self.claim()
        revision = claim.revision_placeholder(
            claim_id="claim-001-rev1",
            statement="Revised source-bound claim.",
            evidence_links=(
                self.evidence(
                    evidence_id="ev-001-rev1",
                    claim_id="claim-001-rev1",
                ),
            ),
        )

        self.assertNotEqual(claim.claim_hash, revision.claim_hash)
        self.assertEqual(revision.previous_claim_hash, claim.claim_hash)
        self.assertEqual(claim.previous_claim_hash, "")
        self.assertEqual(revision.review_status, "needs_review")

    def test_retrieval_score_cannot_satisfy_permission(self):
        with self.assertRaises(KnowledgeValidationError):
            self.claim(metadata={"retrieval_score": 0.99, "permission": True})

    def test_metadata_cannot_become_approval(self):
        with self.assertRaises(KnowledgeValidationError):
            self.claim(metadata={"approved": True})

    def test_recorded_hash_mismatch_fails_closed(self):
        with self.assertRaises(KnowledgeValidationError):
            self.source(source_hash="f" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.evidence(evidence_hash="e" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.claim(claim_hash="d" * 64)

    def source(self, **overrides):
        values = {
            "source_id": "s-001",
            "description": "Single UNIX Specification overview",
            "url": "https://www.unix.org/overview.html",
            "citation": "overview lines 16-30",
            "content_hash": hash_knowledge_value({"fixture": "sus-overview"}),
            "source_type": "standard",
        }
        values.update(overrides)
        return KnowledgeSource(**values)

    def evidence(self, **overrides):
        values = {
            "evidence_id": "ev-001",
            "source_id": "s-001",
            "claim_id": "claim-001",
            "locator": "overview lines 16-30",
            "excerpt": "The Single UNIX Specification Version 5 uses Issue 8 as its core.",
        }
        values.update(overrides)
        return KnowledgeEvidenceLink(**values)

    def claim(self, **overrides):
        claim_id = overrides.get("claim_id", "claim-001")
        values = {
            "claim_id": claim_id,
            "statement": "The Single UNIX Specification Version 5 uses Issue 8 as its core.",
            "sources": (self.source(),),
            "evidence_links": (self.evidence(claim_id=claim_id),),
        }
        values.update(overrides)
        return KnowledgeClaim(**values)

    def provenance(self, claim=None, card_id="kc-001", **overrides):
        claim = claim or self.claim()
        values = {
            "provenance_id": "prov-001",
            "card_id": card_id,
            "source_hashes": tuple(source.source_hash for source in claim.sources),
            "evidence_hashes": tuple(link.evidence_hash for link in claim.evidence_links),
            "claim_hashes": (claim.claim_hash,),
            "created_by": "foundation-test",
        }
        values.update(overrides)
        return KnowledgeProvenance(**values)

    def card(self, **overrides):
        claim = overrides.pop("claim", self.claim())
        card_id = overrides.get("card_id", "kc-001")
        values = {
            "card_id": card_id,
            "claims": (claim,),
            "provenance": self.provenance(claim, card_id=card_id),
        }
        values.update(overrides)
        return KnowledgeCard(**values)


if __name__ == "__main__":
    unittest.main()
