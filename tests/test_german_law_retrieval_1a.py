from __future__ import annotations

import hashlib
import copy
import unittest
from pathlib import Path

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.external_gateway import GermanLawExternalGateway
from runtime.knowledge_modules.german_law import (
    EXPECTED_GERMAN_LAW_DESCRIPTOR,
    EXPECTED_MANIFEST_HASHES,
    GERMAN_LAW_EXPECTED_HEAD,
    GermanLawModuleAdapter,
    production_german_law_configuration,
)
from runtime.knowledge_modules.selection import KnowledgeModuleQuery


GERMAN_REPOSITORY = "/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack"
CORPUS_ROOT = "/home/l/AOIA_PRODUCTION/data/german-law-corpus"


def configuration():
    return production_german_law_configuration(
        module_repository_path=GERMAN_REPOSITORY,
        corpus_data_root=CORPUS_ROOT,
        expected_repository_head=GERMAN_LAW_EXPECTED_HEAD,
    )


def manifest_hashes():
    root = Path(CORPUS_ROOT).resolve()
    return tuple(
        (relative, hashlib.sha256((root / relative).read_bytes()).hexdigest())
        for relative, _ in EXPECTED_MANIFEST_HASHES
    )


class GermanLawRetrieval1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = GermanLawModuleAdapter()
        cls.configuration = configuration()

    def test_real_source_discovery_is_source_bound_currentness_unverified_and_deterministic(self):
        query = KnowledgeModuleQuery(
            question="§ 2 NachwG",
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=8,
            max_excerpt_characters=2000,
            max_total_context_characters=16000,
        )
        before = manifest_hashes()
        first = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        second = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        after = manifest_hashes()
        self.assertEqual(before, after)
        self.assertEqual(first.bundle_hash, second.bundle_hash)
        self.assertEqual(len(first.evidence_items), 1)
        item = first.evidence_items[0]
        self.assertRegex(item.source_object_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(item.temporal_status, "CURRENTNESS_NOT_VERIFIED")
        self.assertIn("CURRENTNESS_NOT_VERIFIED", item.warnings)
        self.assertNotEqual(item.document_type, "ADMINISTRATIVE_RULE")
        self.assertNotEqual(item.source_class, "OFFICIAL_ADMINISTRATIVE_RULE")
        self.assertLessEqual(len(first.evidence_items), query.max_results)
        self.assertLessEqual(len(item.bounded_excerpt), query.max_excerpt_characters)
        self.assertLessEqual(first.total_context_characters, query.max_total_context_characters)

    def test_real_historical_query_fails_closed_without_mode_fallback_and_is_deterministic(self):
        query = KnowledgeModuleQuery(
            question="What did § 2 NachwG require on 2022-09-01?",
            retrieval_mode="VERIFIED_AS_OF",
            as_of_date="2022-09-01",
            max_results=8,
        )
        first = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        second = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertEqual(first.bundle_hash, second.bundle_hash)
        self.assertEqual(first.retrieval_mode, "VERIFIED_AS_OF")
        self.assertEqual(first.query_as_of_date, "2022-09-01")
        self.assertEqual(first.evidence_items, ())
        self.assertEqual(
            [failure.code for failure in first.retrieval_failures],
            ["DATE_OUTSIDE_SUPPORTED_RANGE"],
        )
        self.assertNotIn(
            "SOURCE_DISCOVERY_ONLY",
            [warning.code for warning in first.coverage_warnings],
        )

    def test_nachwg_demo_reports_actual_ambiguous_discovery_result(self):
        query = KnowledgeModuleQuery(
            question="What information does § 2 NachwG require an employer to document?",
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=8,
        )
        bundle = self.adapter.query(
            self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR
        )
        self.assertEqual(bundle.evidence_items, ())
        self.assertEqual(
            [failure.code for failure in bundle.retrieval_failures],
            ["AMBIGUOUS_CITATION"],
        )
        self.assertIn(
            "CURRENTNESS_NOT_VERIFIED",
            [warning.code for warning in bundle.coverage_warnings],
        )

    def test_context_truncation_is_stable_and_within_requested_budget(self):
        query = KnowledgeModuleQuery(
            question="§ 2 NachwG",
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=1,
            max_excerpt_characters=256,
            max_total_context_characters=1024,
        )
        first = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        second = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertEqual(first.bundle_hash, second.bundle_hash)
        self.assertEqual(len(first.evidence_items), 1)
        item = first.evidence_items[0]
        self.assertEqual(len(item.bounded_excerpt), 256)
        self.assertTrue(item.excerpt_truncated)
        self.assertIn("EXCERPT_TRUNCATED", item.warnings)
        self.assertTrue(first.truncated)

    def test_sql_injection_text_is_never_promoted_to_a_command(self):
        query = KnowledgeModuleQuery(
            question="§ 2 NachwG'; DROP TABLE provisions; --",
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=1,
        )
        before = manifest_hashes()
        bundle = self.adapter.query(self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertEqual(before, manifest_hashes())
        self.assertEqual(bundle.retrieval_mode, "SOURCE_DISCOVERY")

    def test_external_evidence_authority_claim_and_invalid_hash_are_rejected(self):
        query = KnowledgeModuleQuery(
            question="§ 2 NachwG", retrieval_mode="SOURCE_DISCOVERY", max_results=1
        )
        raw = GermanLawExternalGateway().query(self.configuration, query)

        class FixedQueryGateway:
            def __init__(self, payload):
                self.payload = payload

            def query(self, configuration, supplied_query):
                self.assert_same(configuration, supplied_query)
                return self.payload

            def assert_same(self, configuration, supplied_query):
                if configuration != self_configuration or supplied_query != query:
                    raise AssertionError("adapter changed validated query or configuration")

        self_configuration = self.configuration
        for field, value, status in (
            ("can_write", True, "MODULE_AUTHORITY_CLAIM_BLOCKED"),
            ("source_object_sha256", "invalid", "MODULE_OUTPUT_MALFORMED"),
        ):
            with self.subTest(field=field):
                payload = copy.deepcopy(raw)
                payload["evidence_items"][0][field] = value
                adapter = GermanLawModuleAdapter(FixedQueryGateway(payload))
                with self.assertRaises(KnowledgeModuleError) as caught:
                    adapter.query(
                        self.configuration, query, EXPECTED_GERMAN_LAW_DESCRIPTOR
                    )
                self.assertEqual(caught.exception.status, status)


if __name__ == "__main__":
    unittest.main()
