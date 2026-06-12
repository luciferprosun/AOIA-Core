from __future__ import annotations

import ast
import json
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.safety.evidence_memory_policy import (
    CanonicalPromotionBlockedError,
    EvidenceWriteBlockedError,
    ProviderCritiqueEvidenceContaminationError,
    assert_can_write_evidence,
    assert_canonical_promotion_blocked_by_default,
    assert_evidence_cannot_approve_action,
    assert_evidence_cannot_execute,
    assert_provider_critique_cannot_be_evidence,
    classify_write_channel,
)
from runtime.schemas.evidence_memory import (
    EvidenceMemoryRecord,
    EvidenceProvenance,
    EvidenceSourceType,
    EvidenceTrustState,
    NonEvidenceChannel,
    create_human_entered_evidence,
    create_local_parsed_document_evidence,
    evidence_record_to_dict,
)
from runtime.schemas.provider_critic import create_inert_provider_critique_record


SCHEMA_PATH = Path("runtime/schemas/evidence_memory.py")
POLICY_PATH = Path("runtime/safety/evidence_memory_policy.py")
FORBIDDEN_IMPORTS = {
    "requests",
    "urllib",
    "http",
    "http.client",
    "socket",
    "subprocess",
    "webbrowser",
    "playwright",
    "selenium",
    "openai",
    "anthropic",
    "google",
    "google.generativeai",
    "google.cloud",
}
FORBIDDEN_STRINGS = {
    "requests",
    "urllib",
    "http.client",
    "socket",
    "subprocess",
    "os.system",
    "webbrowser",
    "playwright",
    "selenium",
    "openai",
    "anthropic",
    "google.generativeai",
    "google.cloud",
    "os.environ",
    "getenv",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def make_human_record() -> EvidenceMemoryRecord:
    return create_human_entered_evidence(
        content_text="Observed command output from local review.",
        source_id="human-note-1",
        source_uri="",
        collector="reviewer",
        created_at="2026-06-12T15:51:00Z",
        evidence_id="evidence-human-1",
    )


class EvidenceMemoryIntakeBoundaryTests(unittest.TestCase):
    def test_human_entered_evidence_creates_candidate_record(self) -> None:
        record = make_human_record()

        self.assertEqual(EvidenceSourceType.HUMAN_ENTERED, record.source_type)
        self.assertEqual(EvidenceTrustState.CANDIDATE, record.trust_state)
        self.assertFalse(record.provider_generated)

    def test_local_parsed_document_evidence_creates_candidate_record(self) -> None:
        record = create_local_parsed_document_evidence(
            content_text="Local parsed document text.",
            source_id="doc-1",
            source_uri="local://doc-1",
            created_at="2026-06-12T15:51:00Z",
        )

        self.assertEqual(EvidenceSourceType.LOCAL_PARSED_DOCUMENT, record.source_type)
        self.assertEqual(EvidenceTrustState.CANDIDATE, record.trust_state)

    def test_evidence_content_hash_is_deterministic(self) -> None:
        first = create_human_entered_evidence(content_text="same text", source_id="a", created_at="t")
        second = create_human_entered_evidence(content_text="same text", source_id="b", created_at="u")

        self.assertEqual(first.content_hash, second.content_hash)

    def test_evidence_record_serializes_to_dict(self) -> None:
        payload = evidence_record_to_dict(make_human_record())

        self.assertIsInstance(payload, dict)
        self.assertEqual("HUMAN_ENTERED", payload["source_type"])
        self.assertEqual("CANDIDATE", payload["trust_state"])
        self.assertEqual("HUMAN_ENTERED", payload["provenance"]["source_type"])

    def test_human_entered_evidence_passes_write_policy(self) -> None:
        assert_can_write_evidence(make_human_record())

    def test_local_parsed_document_evidence_passes_write_policy(self) -> None:
        record = create_local_parsed_document_evidence(content_text="doc text", source_id="doc")

        assert_can_write_evidence(record)

    def test_provider_critique_record_cannot_write_to_evidence_memory(self) -> None:
        provider_record = create_inert_provider_critique_record(
            source_provider="future",
            source_model="future-model",
            request_text="request",
            response_text="provider critique",
        )

        with self.assertRaises(ProviderCritiqueEvidenceContaminationError):
            assert_can_write_evidence(provider_record)
        with self.assertRaises(ProviderCritiqueEvidenceContaminationError):
            assert_provider_critique_cannot_be_evidence(provider_record.to_dict())

    def test_object_with_untrusted_true_cannot_write_to_evidence_memory(self) -> None:
        class UntrustedObject:
            untrusted = True

        with self.assertRaises(ProviderCritiqueEvidenceContaminationError):
            assert_can_write_evidence(UntrustedObject())

    def test_provider_critique_channel_is_blocked_from_evidence_write(self) -> None:
        self.assertEqual("blocked_non_evidence", classify_write_channel(NonEvidenceChannel.PROVIDER_CRITIQUE))
        with self.assertRaises(ValueError):
            EvidenceSourceType("PROVIDER_CRITIQUE")

    def test_reasoning_trace_channel_is_blocked_from_evidence_write(self) -> None:
        self.assertEqual("blocked_non_evidence", classify_write_channel(NonEvidenceChannel.REASONING_TRACE))

    def test_canonical_knowledge_channel_is_blocked_as_new_evidence_source(self) -> None:
        self.assertEqual("blocked_non_evidence", classify_write_channel(NonEvidenceChannel.CANONICAL_KNOWLEDGE))

    def test_contradiction_registry_channel_is_blocked_as_new_evidence_source(self) -> None:
        self.assertEqual("blocked_non_evidence", classify_write_channel(NonEvidenceChannel.CONTRADICTION_REGISTRY))

    def test_canonical_promotion_is_blocked_by_default(self) -> None:
        with self.assertRaises(CanonicalPromotionBlockedError):
            assert_canonical_promotion_blocked_by_default(make_human_record())

    def test_evidence_cannot_approve_action(self) -> None:
        with self.assertRaises(EvidenceWriteBlockedError):
            assert_evidence_cannot_approve_action(make_human_record())

    def test_evidence_cannot_execute(self) -> None:
        with self.assertRaises(EvidenceWriteBlockedError):
            assert_evidence_cannot_execute(make_human_record())

    def test_evidence_cannot_trigger_action_surfaces(self) -> None:
        payload = evidence_record_to_dict(make_human_record())

        self.assertFalse(payload["canonical_write_allowed"])
        self.assertFalse(payload["contradiction_registry_write_allowed"])
        self.assertFalse(payload["action_approval_allowed"])
        self.assertFalse(payload["execution_allowed"])

    def test_provider_generated_flag_blocks_evidence_write_if_set(self) -> None:
        record = replace(make_human_record(), provider_generated=True)

        with self.assertRaises(ProviderCritiqueEvidenceContaminationError):
            assert_can_write_evidence(record)

    def test_no_network_or_client_imports_appear_in_new_evidence_files(self) -> None:
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(SCHEMA_PATH)))
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(POLICY_PATH)))

    def test_no_forbidden_runtime_strings_appear_in_new_evidence_files(self) -> None:
        source_text = (
            SCHEMA_PATH.read_text(encoding="utf-8")
            + "\n"
            + POLICY_PATH.read_text(encoding="utf-8")
        ).lower()

        for forbidden in FORBIDDEN_STRINGS:
            self.assertNotIn(forbidden.lower(), source_text)

    def test_no_api_key_or_env_access_is_required(self) -> None:
        source_text = (
            SCHEMA_PATH.read_text(encoding="utf-8")
            + "\n"
            + POLICY_PATH.read_text(encoding="utf-8")
        ).lower()

        self.assertNotIn("api_key", source_text)
        self.assertNotIn("os.environ", source_text)
        self.assertNotIn("getenv", source_text)

    def test_source_metadata_is_provenance_only_not_standalone_evidence(self) -> None:
        provenance = EvidenceProvenance(
            source_id="metadata",
            source_type=EvidenceSourceType.SOURCE_METADATA,
            source_uri="local://metadata",
            collected_at="2026-06-12T15:51:00Z",
            collector="reviewer",
            content_hash="metadata-hash",
        )
        record = EvidenceMemoryRecord(
            evidence_id="metadata-record",
            created_at="2026-06-12T15:51:00Z",
            source_type=EvidenceSourceType.SOURCE_METADATA,
            trust_state=EvidenceTrustState.CANDIDATE,
            content_text="metadata only",
            content_hash="ignored",
            provenance=provenance,
        )

        self.assertEqual("provenance_metadata_only", classify_write_channel(record.source_type))
        with self.assertRaises(EvidenceWriteBlockedError):
            assert_can_write_evidence(record)


if __name__ == "__main__":
    unittest.main()
