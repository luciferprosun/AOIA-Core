from __future__ import annotations

import ast
import hashlib
import unittest
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import runtime.memory as memory
from runtime.memory.evidence_link import KnowledgeEvidenceLink
from runtime.memory.knowledge_card import KnowledgeCard
from runtime.memory.knowledge_claim import KnowledgeClaim
from runtime.memory.knowledge_source import KnowledgeSource
from runtime.memory.provenance import KnowledgeProvenance
from runtime.memory.runtime_schemas import (
    MEMORY_RUNTIME_BLOCKED_INVALID_HASH,
    MEMORY_RUNTIME_BLOCKED_INVALID_TAG,
    MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD,
    MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND,
    PheromoneMemoryTag,
    TetradKnowledgeObject,
    build_pheromone_memory_tag,
    build_tetrad_knowledge_object,
    hash_memory_runtime_value,
    validate_memory_runtime_metadata,
)
from runtime.memory.validation import (
    KNOWLEDGE_DISCOVERY_ONLY,
    KNOWLEDGE_CARD_SCHEMA_VERSION,
    KNOWLEDGE_CLAIM_SCHEMA_VERSION,
    KNOWLEDGE_EVIDENCE_LINK_SCHEMA_VERSION,
    KNOWLEDGE_PROVENANCE_SCHEMA_VERSION,
    KNOWLEDGE_SOURCE_SCHEMA_VERSION,
    KNOWLEDGE_SOURCE_CANDIDATE,
    NON_EVIDENCE_SOURCE_TYPES,
    KnowledgeValidationError,
    canonical_knowledge_json,
    hash_knowledge_value,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_MODULES = (
    REPO_ROOT / "runtime/memory/__init__.py",
    REPO_ROOT / "runtime/memory/evidence_link.py",
    REPO_ROOT / "runtime/memory/knowledge_card.py",
    REPO_ROOT / "runtime/memory/knowledge_claim.py",
    REPO_ROOT / "runtime/memory/knowledge_source.py",
    REPO_ROOT / "runtime/memory/provenance.py",
    REPO_ROOT / "runtime/memory/runtime_schemas.py",
    REPO_ROOT / "runtime/memory/validation.py",
)


class KnowledgeFoundationReconciliation1ATests(unittest.TestCase):
    def test_valid_records_are_explicit_frozen_and_inert(self):
        card = self.card()
        records = (
            card,
            card.provenance,
            card.claims[0],
            card.claims[0].sources[0],
            card.claims[0].evidence_links[0],
        )
        self.assertEqual(KNOWLEDGE_CARD_SCHEMA_VERSION, card.schema_version)
        self.assertEqual(KNOWLEDGE_PROVENANCE_SCHEMA_VERSION, card.provenance.schema_version)
        self.assertEqual(KNOWLEDGE_CLAIM_SCHEMA_VERSION, card.claims[0].schema_version)
        self.assertEqual(KNOWLEDGE_SOURCE_SCHEMA_VERSION, card.claims[0].sources[0].schema_version)
        self.assertEqual(KNOWLEDGE_EVIDENCE_LINK_SCHEMA_VERSION, card.claims[0].evidence_links[0].schema_version)
        for record in records:
            with self.subTest(record=type(record).__name__):
                for flag in ("can_execute", "can_write", "gate_satisfied", "can_dispatch", "can_approve"):
                    self.assertFalse(getattr(record, flag))
                    self.assertFalse(record.to_dict()[flag])
                for method in (
                    "approve",
                    "authorize",
                    "call_provider",
                    "dispatch",
                    "execute",
                    "mutate_gate",
                    "open_browser",
                    "run",
                    "write",
                ):
                    self.assertFalse(hasattr(record, method))
                with self.assertRaises(FrozenInstanceError):
                    record.schema_version = "forged"  # type: ignore[misc]

    def test_canonical_serialization_and_hash_are_utf8_deterministic(self):
        first = {"z": [2, 1], "a": "źródło"}
        second = {"a": "źródło", "z": (2, 1)}
        serialized = canonical_knowledge_json(first)

        self.assertEqual(serialized, canonical_knowledge_json(second))
        self.assertEqual(
            hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            hash_knowledge_value(first),
        )
        self.assertEqual(hash_knowledge_value(first), hash_knowledge_value(second))

    def test_semantically_unordered_inputs_normalize_by_identifier(self):
        source_a = self.source("source-a")
        source_b = self.source("source-b")
        link_a = self.evidence("evidence-a", source_a.source_id, "claim-order")
        link_b = self.evidence("evidence-b", source_b.source_id, "claim-order")
        forward = self.claim(
            "claim-order",
            sources=(source_a, source_b),
            evidence_links=(link_a, link_b),
        )
        reverse = self.claim(
            "claim-order",
            sources=(source_b, source_a),
            evidence_links=(link_b, link_a),
        )

        self.assertEqual(forward.claim_hash, reverse.claim_hash)
        self.assertEqual(forward.to_dict(), reverse.to_dict())

        other = self.claim("claim-z")
        card_forward = self.card(claims=(forward, other))
        card_reverse = self.card(claims=(other, reverse))
        self.assertEqual(card_forward.card_hash, card_reverse.card_hash)
        self.assertEqual(card_forward.to_dict(), card_reverse.to_dict())

    def test_provenance_hash_collections_are_unique_and_order_independent(self):
        first_claim = self.claim("claim-a")
        second_claim = self.claim("claim-b")
        values = self.provenance_values((first_claim, second_claim))
        first = KnowledgeProvenance(**values)
        reverse = KnowledgeProvenance(
            **{
                **values,
                "source_hashes": tuple(reversed(values["source_hashes"])),
                "evidence_hashes": tuple(reversed(values["evidence_hashes"])),
                "claim_hashes": tuple(reversed(values["claim_hashes"])),
            }
        )
        self.assertEqual(first.provenance_hash, reverse.provenance_hash)
        self.assertEqual(first.to_dict(), reverse.to_dict())

        with self.assertRaises(KnowledgeValidationError):
            KnowledgeProvenance(
                **{
                    **values,
                    "claim_hashes": (first_claim.claim_hash, first_claim.claim_hash),
                }
            )
        for field_name in ("source_hashes", "evidence_hashes"):
            duplicate = values[field_name][0]
            with self.subTest(field_name=field_name):
                with self.assertRaises(KnowledgeValidationError):
                    KnowledgeProvenance(**{**values, field_name: (duplicate, duplicate)})

    def test_metadata_is_deeply_immutable_and_serializes_as_plain_data(self):
        original_metadata = {"nested": {"labels": ["local", "review"]}, "confidence": 0.75}
        source = self.source(metadata=original_metadata)
        original_hash = source.source_hash

        original_metadata["nested"]["labels"][0] = "mutated-input"
        original_metadata["new"] = True
        self.assertEqual("local", source.to_dict()["metadata"]["nested"]["labels"][0])
        self.assertNotIn("new", source.to_dict()["metadata"])

        with self.assertRaises(TypeError):
            source.metadata["new"] = True  # type: ignore[index]
        with self.assertRaises(TypeError):
            source.metadata["nested"]["new"] = True  # type: ignore[index]
        with self.assertRaises(TypeError):
            source.metadata["nested"]["labels"][0] = "changed"  # type: ignore[index]

        payload = source.to_dict()
        payload["metadata"]["nested"]["labels"][0] = "detached"
        self.assertEqual(original_hash, source.source_hash)
        self.assertEqual("local", source.to_dict()["metadata"]["nested"]["labels"][0])

    def test_duplicate_source_evidence_and_claim_ids_fail_closed(self):
        source = self.source("duplicate-source")
        conflicting = self.source("duplicate-source", description="Conflicting source record")
        with self.assertRaises(KnowledgeValidationError):
            self.claim(
                sources=(source, conflicting),
                evidence_links=(self.evidence("evidence-a", source.source_id, "claim-1"),),
            )

        link = self.evidence("duplicate-evidence", source.source_id, "claim-1")
        with self.assertRaises(KnowledgeValidationError):
            self.claim(sources=(source,), evidence_links=(link, link))

        first = self.claim("duplicate-claim")
        second = self.claim("duplicate-claim", statement="A different claim with the same identifier.")
        with self.assertRaises(KnowledgeValidationError):
            self.card(claims=(first, second))

    def test_unknown_source_and_claim_references_fail_closed(self):
        source = self.source()
        with self.assertRaises(KnowledgeValidationError):
            self.claim(
                sources=(source,),
                evidence_links=(self.evidence("evidence-unknown-source", "missing-source", "claim-1"),),
            )
        with self.assertRaises(KnowledgeValidationError):
            self.claim(
                sources=(source,),
                evidence_links=(self.evidence("evidence-unknown-claim", source.source_id, "other-claim"),),
            )

    def test_every_source_requires_an_explicit_evidence_link(self):
        linked = self.source("source-linked")
        unlinked = self.source("source-unlinked")
        with self.assertRaises(KnowledgeValidationError):
            self.claim(
                sources=(linked, unlinked),
                evidence_links=(self.evidence("evidence-linked", linked.source_id, "claim-1"),),
            )

    def test_provenance_must_exactly_belong_to_its_card(self):
        claim = self.claim()
        values = self.provenance_values((claim,))
        replacements = {
            "card_id": "other-card",
            "source_hashes": (self.hash_value("foreign-source"),),
            "evidence_hashes": (self.hash_value("foreign-evidence"),),
            "claim_hashes": (self.hash_value("foreign-claim"),),
        }
        for field_name, replacement in replacements.items():
            with self.subTest(field_name=field_name):
                provenance = KnowledgeProvenance(**{**values, field_name: replacement})
                with self.assertRaises(KnowledgeValidationError):
                    KnowledgeCard(card_id="card-1", claims=(claim,), provenance=provenance)

        with self.assertRaises(KnowledgeValidationError):
            KnowledgeCard(card_id="card-1", claims=(claim,), provenance=None)  # type: ignore[arg-type]

    def test_conflicting_card_wide_source_and_evidence_ids_fail_closed(self):
        source_a = self.source("shared-source")
        source_b = self.source("shared-source", description="Conflicting shared source")
        first = self.claim(
            "claim-a",
            sources=(source_a,),
            evidence_links=(self.evidence("evidence-a", source_a.source_id, "claim-a"),),
        )
        second = self.claim(
            "claim-b",
            sources=(source_b,),
            evidence_links=(self.evidence("evidence-b", source_b.source_id, "claim-b"),),
        )
        with self.assertRaises(KnowledgeValidationError):
            self.card(claims=(first, second))

        source_c = self.source("source-c")
        source_d = self.source("source-d")
        third = self.claim(
            "claim-c",
            sources=(source_c,),
            evidence_links=(self.evidence("shared-evidence", source_c.source_id, "claim-c"),),
        )
        fourth = self.claim(
            "claim-d",
            sources=(source_d,),
            evidence_links=(self.evidence("shared-evidence", source_d.source_id, "claim-d"),),
        )
        with self.assertRaises(KnowledgeValidationError):
            self.card(claims=(third, fourth))

    def test_identical_source_id_cannot_be_repeated_across_claims(self):
        source = self.source("shared-source")
        first = self.claim(
            "claim-a",
            sources=(source,),
            evidence_links=(self.evidence("evidence-a", source.source_id, "claim-a"),),
        )
        second = self.claim(
            "claim-b",
            sources=(source,),
            evidence_links=(self.evidence("evidence-b", source.source_id, "claim-b"),),
        )
        with self.assertRaises(KnowledgeValidationError):
            self.card(claims=(first, second))

    def test_malformed_content_and_record_hashes_fail_closed(self):
        for malformed in ("", "bad", "A" * 64, "0" * 63):
            with self.subTest(content_hash=malformed):
                with self.assertRaises(KnowledgeValidationError):
                    self.source(content_hash=malformed)
        with self.assertRaises(KnowledgeValidationError):
            self.source(source_hash="f" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.evidence(evidence_hash="e" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.claim(claim_hash="d" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.provenance((self.claim(),), provenance_hash="c" * 64)
        with self.assertRaises(KnowledgeValidationError):
            self.card(card_hash="b" * 64)

    def test_empty_mandatory_identifiers_and_text_fail_closed(self):
        source_cases = (
            {"source_id": ""},
            {"source_id": "not stable"},
            {"description": "   "},
            {"url": ""},
            {"citation": ""},
        )
        for values in source_cases:
            with self.subTest(values=values):
                with self.assertRaises(KnowledgeValidationError):
                    self.source(**values)
        with self.assertRaises(KnowledgeValidationError):
            self.evidence(locator="")
        with self.assertRaises(KnowledgeValidationError):
            self.evidence(excerpt="")
        for values in (
            {"evidence_id": ""},
            {"source_id": "bad source"},
            {"claim_id": "bad claim"},
        ):
            with self.subTest(evidence_values=values):
                with self.assertRaises(KnowledgeValidationError):
                    self.evidence(**values)
        with self.assertRaises(KnowledgeValidationError):
            self.claim(statement="")
        with self.assertRaises(KnowledgeValidationError):
            self.claim(claim_id="bad claim")
        with self.assertRaises(KnowledgeValidationError):
            self.card(card_id="bad id")
        claim = self.claim()
        for values in (
            {"provenance_id": ""},
            {"card_id": "bad card"},
            {"created_by": ""},
        ):
            with self.subTest(provenance_values=values):
                with self.assertRaises(KnowledgeValidationError):
                    self.provenance((claim,), **values)

    def test_invalid_authority_review_and_source_labels_fail_closed(self):
        with self.assertRaises(KnowledgeValidationError):
            self.source(authority_label="authoritative")
        with self.assertRaises(KnowledgeValidationError):
            self.source(source_type="unknown")
        with self.assertRaises(KnowledgeValidationError):
            self.claim(review_status="approved")
        with self.assertRaises(KnowledgeValidationError):
            self.card(review_status="approved")

    def test_collection_types_and_non_knowledge_substitutes_fail_closed(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        source = self.source()
        link = self.evidence(source_id=source.source_id)
        cases = (
            {"sources": [source], "evidence_links": (link,)},
            {"sources": (tetrad,), "evidence_links": (link,)},
            {"sources": (source,), "evidence_links": [link]},
            {"sources": (source,), "evidence_links": (tag,)},
        )
        for values in cases:
            with self.subTest(values=tuple(values)):
                with self.assertRaises(KnowledgeValidationError):
                    self.claim(**values)
        valid_card = self.card()
        with self.assertRaises(KnowledgeValidationError):
            KnowledgeCard(card_id="card-1", claims=(tag,), provenance=valid_card.provenance)

    def test_generated_advisory_and_control_objects_cannot_satisfy_evidence(self):
        for source_type in sorted(NON_EVIDENCE_SOURCE_TYPES):
            with self.subTest(source_type=source_type):
                source = self.source(source_type=source_type)
                self.assertEqual(KNOWLEDGE_DISCOVERY_ONLY, source.evidence_status)
                link = self.evidence(source_id=source.source_id)
                with self.assertRaises(KnowledgeValidationError):
                    self.claim(sources=(source,), evidence_links=(link,))

        substitutes = (
            "provider_output",
            "critic_report",
            "preview",
            "action_proposal",
            "hat_metadata",
            "pheromone_metadata",
        )
        for key in substitutes:
            with self.subTest(key=key):
                with self.assertRaises(KnowledgeValidationError):
                    KnowledgeClaim(
                        claim_id="claim-no-evidence",
                        statement="Metadata cannot replace explicit source evidence.",
                        sources=(),
                        evidence_links=(),
                        metadata={key: {"id": "candidate"}},
                    )

        ordinary = self.source(source_type="document")
        self.assertEqual(KNOWLEDGE_SOURCE_CANDIDATE, ordinary.evidence_status)

        baseline = self.claim()
        for key in substitutes:
            with self.subTest(inert_metadata=key):
                claim = self.claim(metadata={key: {"artifact_id": "review-only"}})
                card = self.card(claims=(claim,))
                self.assertEqual(
                    baseline.evidence_links[0].evidence_hash,
                    claim.evidence_links[0].evidence_hash,
                )
                self.assertEqual(baseline.sources[0].source_hash, claim.sources[0].source_hash)
                self.assertFalse(card.can_execute)
                self.assertFalse(card.can_write)
                self.assertFalse(card.gate_satisfied)

    def test_forged_authority_fields_fail_closed_and_confidence_stays_descriptive(self):
        forged = (
            "approved",
            "execute",
            "execution_allowed",
            "write_allowed",
            "provider_call_allowed",
            "browser_allowed",
            "gate_satisfied",
            "human_approved",
            "unknown_can_execute",
        )
        for key in forged:
            with self.subTest(key=key):
                with self.assertRaises(KnowledgeValidationError):
                    self.source(metadata={key: True})

        claim = self.claim(metadata={"confidence": 0.91, "rank": 2})
        self.assertFalse(claim.can_execute)
        self.assertFalse(claim.can_write)
        with self.assertRaises(KnowledgeValidationError):
            self.claim(metadata={"action_proposal": {"approved": True}})
        future_metadata = self.claim(metadata={"future_review_hint": {"may_run_later": True}})
        self.assertFalse(future_metadata.can_execute)
        self.assertFalse(future_metadata.can_write)
        action_metadata = self.claim(metadata={"action_proposal": {"proposal_id": "ap-1"}})
        self.assertFalse(action_metadata.can_execute)
        self.assertFalse(action_metadata.gate_satisfied)

    def test_revision_requires_explicitly_rebound_evidence(self):
        claim = self.claim()
        with self.assertRaises(KnowledgeValidationError):
            claim.revision_placeholder(
                claim_id="claim-revision",
                statement="Revised claim.",
                evidence_links=claim.evidence_links,
            )

        rebound = self.evidence("evidence-revision", claim.sources[0].source_id, "claim-revision")
        revision = claim.revision_placeholder(
            claim_id="claim-revision",
            statement="Revised claim.",
            evidence_links=(rebound,),
        )
        self.assertEqual(claim.claim_hash, revision.previous_claim_hash)
        self.assertEqual("needs_review", revision.review_status)

    def test_tetrad_and_pheromone_public_contract_remains_backward_compatible(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(tag,), now=20)
        self.assertTrue(result.ok)
        self.assertEqual(
            (
                "schema_version",
                "object_id",
                "raw_evidence_hash",
                "structured_claims_hash",
                "semantic_view_hash",
                "audit_risk_hash",
                "source_hashes",
                "status_label",
                "summary",
                "created_at",
                "expires_at",
                "object_hash",
            ),
            tuple(field.name for field in fields(TetradKnowledgeObject)),
        )
        self.assertEqual(
            (
                "schema_version",
                "tag_id",
                "target_hash",
                "tag_kind",
                "signal_label",
                "reason",
                "created_at",
                "expires_at",
                "tag_hash",
            ),
            tuple(field.name for field in fields(PheromoneMemoryTag)),
        )
        self.assertEqual(tetrad.object_hash, self.tetrad().object_hash)
        self.assertEqual(tag.tag_hash, self.tag(tetrad.object_hash).tag_hash)

    def test_legacy_mapping_validation_rejects_missing_fields_and_non_lowercase_hashes(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)

        for missing_field in ("object_id", "summary"):
            with self.subTest(tetrad_missing=missing_field):
                payload = tetrad.to_dict()
                payload.pop(missing_field)
                payload["object_hash"] = self.rehash_payload(payload, "object_hash")
                result = validate_memory_runtime_metadata(tetrad=payload, tags=(), now=20)
                self.assertTrue(result.blocked)
                self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_TETRAD, result.reason_codes)

        for field_name, value in (
            ("raw_evidence_hash", tetrad.raw_evidence_hash.upper()),
            ("source_hashes", (tetrad.source_hashes[0].upper(),)),
            ("object_hash", tetrad.object_hash.upper()),
        ):
            with self.subTest(tetrad_hash=field_name):
                payload = {**tetrad.to_dict(), field_name: value}
                if field_name != "object_hash":
                    payload["object_hash"] = self.rehash_payload(payload, "object_hash")
                result = validate_memory_runtime_metadata(tetrad=payload, tags=(), now=20)
                self.assertTrue(result.blocked)
                self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_HASH, result.reason_codes)

        for missing_field in ("tag_id", "reason"):
            with self.subTest(tag_missing=missing_field):
                payload = tag.to_dict()
                payload.pop(missing_field)
                payload["tag_hash"] = self.rehash_payload(payload, "tag_hash")
                result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(payload,), now=20)
                self.assertTrue(result.blocked)
                self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_TAG, result.reason_codes)

        for field_name, value in (
            ("target_hash", tag.target_hash.upper()),
            ("tag_hash", tag.tag_hash.upper()),
        ):
            with self.subTest(tag_hash=field_name):
                payload = {**tag.to_dict(), field_name: value}
                if field_name != "tag_hash":
                    payload["tag_hash"] = self.rehash_payload(payload, "tag_hash")
                result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(payload,), now=20)
                self.assertTrue(result.blocked)
                self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_HASH, result.reason_codes)

    def test_unhashable_tag_identifier_fails_closed(self):
        tetrad = self.tetrad()
        payload = self.tag(tetrad.object_hash).to_dict()
        payload["tag_id"] = []
        payload["tag_hash"] = self.rehash_payload(payload, "tag_hash")

        result = validate_memory_runtime_metadata(tetrad=tetrad, tags=(payload,), now=20)

        self.assertTrue(result.blocked)
        self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_TAG, result.reason_codes)

    def test_invalid_tag_order_does_not_change_validation_identity(self):
        tetrad = self.tetrad()
        tag = self.tag(tetrad.object_hash)
        invalid_identifier = tag.to_dict()
        invalid_identifier["tag_id"] = "bad id"
        invalid_identifier["tag_hash"] = self.rehash_payload(invalid_identifier, "tag_hash")
        unknown_kind = tag.to_dict()
        unknown_kind["tag_id"] = "tag-2"
        unknown_kind["tag_kind"] = "unknown_kind"
        unknown_kind["tag_hash"] = self.rehash_payload(unknown_kind, "tag_hash")

        forward = validate_memory_runtime_metadata(
            tetrad=tetrad,
            tags=(invalid_identifier, unknown_kind),
            now=20,
        )
        reverse = validate_memory_runtime_metadata(
            tetrad=tetrad,
            tags=(unknown_kind, invalid_identifier),
            now=20,
        )

        self.assertTrue(forward.blocked)
        self.assertTrue(reverse.blocked)
        self.assertIn(MEMORY_RUNTIME_BLOCKED_INVALID_TAG, forward.reason_codes)
        self.assertIn(MEMORY_RUNTIME_BLOCKED_UNKNOWN_TAG_KIND, forward.reason_codes)
        self.assertEqual(forward.reason_codes, reverse.reason_codes)
        self.assertEqual(forward.validation_hash, reverse.validation_hash)

    def test_falsy_non_string_recorded_hashes_fail_closed(self):
        for recorded_hash in (None, False, 0, b"", [], {}):
            with self.subTest(recorded_hash=recorded_hash):
                with self.assertRaises(KnowledgeValidationError):
                    self.source(source_hash=recorded_hash)

        self.assertEqual(64, len(self.source(source_hash="").source_hash))

    def test_knowledge_card_and_tetrad_are_distinct_with_no_promotion_api(self):
        card = self.card()
        tetrad = self.tetrad()
        self.assertNotIsInstance(card, TetradKnowledgeObject)
        self.assertFalse(issubclass(KnowledgeCard, TetradKnowledgeObject))
        self.assertNotEqual(card.to_dict(), tetrad.to_dict())
        for name in ("from_tetrad", "to_card", "promote", "verify_automatically"):
            self.assertFalse(hasattr(KnowledgeCard, name))
            self.assertFalse(hasattr(TetradKnowledgeObject, name))
        public_names = set(dir(KnowledgeCard)) | set(dir(TetradKnowledgeObject))
        forbidden_fragments = (
            "from_runtime_tetrad",
            "promote_tetrad",
            "to_knowledge_card",
        )
        self.assertTrue(all(fragment not in public_names for fragment in forbidden_fragments))

    def test_package_exports_are_additive_and_duplicate_initializer_is_absent(self):
        intended = {
            "KnowledgeCard",
            "KnowledgeClaim",
            "KnowledgeEvidenceLink",
            "KnowledgeProvenance",
            "KnowledgeSource",
            "MemoryRuntimeValidationResult",
            "PheromoneMemoryTag",
            "TetradKnowledgeObject",
            "build_pheromone_memory_tag",
            "build_tetrad_knowledge_object",
            "canonical_memory_runtime_json",
            "hash_memory_runtime_value",
            "validate_memory_runtime_metadata",
        }
        self.assertEqual(intended, set(memory.__all__))
        for name in intended:
            self.assertTrue(hasattr(memory, name))
        self.assertFalse((REPO_ROOT / "runtime/memory/init.py").exists())

    def test_foundation_modules_have_no_capability_imports_or_side_effect_calls(self):
        forbidden_imports = {
            "aiohttp",
            "anthropic",
            "git",
            "gitpython",
            "google",
            "httpx",
            "importlib",
            "openai",
            "os",
            "pathlib",
            "playwright",
            "pty",
            "requests",
            "selenium",
            "shutil",
            "socket",
            "sqlite3",
            "subprocess",
            "tempfile",
            "time",
            "urllib",
            "webbrowser",
        }
        forbidden_call_names = {
            "Popen",
            "__import__",
            "connect",
            "eval",
            "exec",
            "import_module",
            "mkdir",
            "now",
            "open",
            "open_browser",
            "popen",
            "replace",
            "rename",
            "run",
            "system",
            "time",
            "touch",
            "today",
            "unlink",
            "urlopen",
            "utcnow",
            "write_bytes",
            "write_text",
        }
        forbidden_runtime_prefixes = (
            "runtime.browser_ops",
            "runtime.control_write",
            "runtime.execution",
            "runtime.git_ops",
            "runtime.human_decision_gated_artifact_write",
            "runtime.orchestrator",
            "runtime.providers",
            "runtime.retrieval",
            "runtime.safety",
            "runtime.tools",
            "runtime.webapp",
        )
        for path in FOUNDATION_MODULES:
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imports: set[str] = set()
                calls: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imports.update(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module)
                    elif isinstance(node, ast.Call):
                        calls.add(self.dotted_name(node.func))
                forbidden_found = {
                    module_name
                    for module_name in imports
                    if module_name.split(".")[0].casefold() in forbidden_imports
                    or module_name.startswith(forbidden_runtime_prefixes)
                }
                forbidden_calls = {
                    call_name
                    for call_name in calls
                    if call_name.rsplit(".", 1)[-1] in forbidden_call_names
                }
                self.assertEqual(set(), forbidden_found)
                self.assertEqual(set(), forbidden_calls)

    def test_knowledge_identity_has_no_implicit_timestamp(self):
        first = self.card(metadata={"packaged_at": "2026-07-13T00:00:00Z"})
        second = self.card(metadata={"packaged_at": "2026-07-13T00:00:00Z"})
        changed = self.card(metadata={"packaged_at": "2026-07-14T00:00:00Z"})
        self.assertEqual(first.card_hash, second.card_hash)
        self.assertNotEqual(first.card_hash, changed.card_hash)
        for record_type in (KnowledgeSource, KnowledgeEvidenceLink, KnowledgeClaim, KnowledgeProvenance, KnowledgeCard):
            self.assertNotIn("created_at", {field.name for field in fields(record_type)})

    def source(self, source_id="source-1", **overrides):
        values = {
            "source_id": source_id,
            "description": f"Source record {source_id}",
            "url": f"https://example.invalid/{source_id}",
            "citation": f"{source_id} section 1",
            "content_hash": self.hash_value(f"content:{source_id}"),
            "source_type": "document",
        }
        values.update(overrides)
        return KnowledgeSource(**values)

    def evidence(self, evidence_id="evidence-1", source_id="source-1", claim_id="claim-1", **overrides):
        values = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "claim_id": claim_id,
            "locator": f"{evidence_id} locator",
            "excerpt": f"Evidence excerpt for {evidence_id}.",
        }
        values.update(overrides)
        return KnowledgeEvidenceLink(**values)

    def claim(self, claim_id="claim-1", **overrides):
        source = self.source(f"source-{claim_id}")
        values = {
            "claim_id": claim_id,
            "statement": f"Reviewable statement for {claim_id}.",
            "sources": (source,),
            "evidence_links": (self.evidence(f"evidence-{claim_id}", source.source_id, claim_id),),
        }
        values.update(overrides)
        return KnowledgeClaim(**values)

    def provenance_values(self, claims, card_id="card-1", **overrides):
        sources = {source.source_id: source for claim in claims for source in claim.sources}
        evidence = {link.evidence_id: link for claim in claims for link in claim.evidence_links}
        values = {
            "provenance_id": f"provenance-{card_id}",
            "card_id": card_id,
            "source_hashes": tuple(source.source_hash for source in sources.values()),
            "evidence_hashes": tuple(link.evidence_hash for link in evidence.values()),
            "claim_hashes": tuple(claim.claim_hash for claim in claims),
            "created_by": "knowledge-foundation-reconciliation-test",
        }
        values.update(overrides)
        return values

    def provenance(self, claims, card_id="card-1", **overrides):
        return KnowledgeProvenance(**self.provenance_values(claims, card_id=card_id, **overrides))

    def card(self, card_id="card-1", claims=None, **overrides):
        normalized_claims = (self.claim(),) if claims is None else claims
        values = {
            "card_id": card_id,
            "claims": normalized_claims,
            "provenance": self.provenance(normalized_claims, card_id=card_id),
        }
        values.update(overrides)
        return KnowledgeCard(**values)

    def tetrad(self):
        return build_tetrad_knowledge_object(
            object_id="tetrad-1",
            raw_evidence_hash=self.hash_value("raw"),
            structured_claims_hash=self.hash_value("claims"),
            semantic_view_hash=self.hash_value("semantic"),
            audit_risk_hash=self.hash_value("audit"),
            source_hashes=(self.hash_value("source"),),
            status_label="needs_review",
            summary="Inert compatibility object.",
            created_at=10,
            expires_at=100,
        )

    def tag(self, target_hash):
        return build_pheromone_memory_tag(
            tag_id="tag-1",
            target_hash=target_hash,
            tag_kind="needs_revalidation",
            signal_label="medium",
            reason="Advisory metadata only.",
            created_at=10,
            expires_at=100,
        )

    @staticmethod
    def hash_value(value):
        return hash_knowledge_value({"fixture": value})

    @staticmethod
    def rehash_payload(payload, hash_field):
        material = {key: value for key, value in payload.items() if key != hash_field}
        return hash_memory_runtime_value(material)

    @classmethod
    def dotted_name(cls, node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = cls.dotted_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""


if __name__ == "__main__":
    unittest.main()
