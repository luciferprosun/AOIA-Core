from __future__ import annotations

import unittest

from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.selection import KnowledgeModuleQuery, KnowledgeModuleSelection


class KnowledgeModuleSelection1ATests(unittest.TestCase):
    def test_zero_one_and_multiple_explicit_modules_are_deterministic(self):
        self.assertEqual(KnowledgeModuleSelection().module_ids, ())
        self.assertEqual(
            KnowledgeModuleSelection(module_ids=("z-module", "a-module")).module_ids,
            ("a-module", "z-module"),
        )
        self.assertEqual(
            KnowledgeModuleSelection(module_ids=("a-module",)).selection_hash,
            KnowledgeModuleSelection(module_ids=("a-module",)).selection_hash,
        )

    def test_duplicate_module_ids_are_rejected(self):
        with self.assertRaises(KnowledgeModuleError) as caught:
            KnowledgeModuleSelection(module_ids=("same-module", "same-module"))
        self.assertEqual(caught.exception.status, "DUPLICATE_MODULE_ID")

    def test_selection_unknown_fields_are_rejected(self):
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeModuleSelection.from_dict({"module_ids": [], "automatic": True})

    def test_query_unknown_fields_invalid_dates_and_bounds_are_rejected(self):
        minimal = KnowledgeModuleQuery.from_dict(
            {"question": "§ 1 GG", "retrieval_mode": "SOURCE_DISCOVERY"}
        )
        self.assertEqual(minimal.max_results, 10)
        self.assertEqual(minimal.languages, ("de",))
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeModuleQuery.from_dict(
                {
                    "question": "§ 1 GG",
                    "retrieval_mode": "SOURCE_DISCOVERY",
                    "automatic_module": True,
                }
            )
        for invalid in ("2026-02-30", "19-07-2026", "2026-7-1"):
            with self.subTest(value=invalid):
                with self.assertRaises(KnowledgeModuleError):
                    KnowledgeModuleQuery(
                        question="§ 1 GG",
                        retrieval_mode="VERIFIED_AS_OF",
                        as_of_date=invalid,
                    )
        for kwargs in (
            {"max_results": 0},
            {"max_results": 21},
            {"max_excerpt_characters": 255},
            {"max_excerpt_characters": 4001},
            {"max_total_context_characters": 1023},
            {"max_total_context_characters": 32001},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(KnowledgeModuleError):
                    KnowledgeModuleQuery(
                        question="§ 1 GG", retrieval_mode="SOURCE_DISCOVERY", **kwargs
                    )

    def test_verified_as_of_requires_explicit_iso_date(self):
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeModuleQuery(question="§ 1 GG", retrieval_mode="VERIFIED_AS_OF")

    def test_source_discovery_rejects_date_and_implicit_currentness(self):
        with self.assertRaises(KnowledgeModuleError):
            KnowledgeModuleQuery(
                question="§ 1 GG",
                retrieval_mode="SOURCE_DISCOVERY",
                as_of_date="2026-07-19",
            )
        for word in ("today", "currently", "now", "latest", "presently"):
            with self.subTest(word=word):
                with self.assertRaises(KnowledgeModuleError) as caught:
                    KnowledgeModuleQuery(
                        question=f"What applies {word}?", retrieval_mode="SOURCE_DISCOVERY"
                    )
                self.assertEqual(caught.exception.status, "IMPLICIT_CURRENTNESS_FORBIDDEN")

    def test_administrative_rules_are_excluded_by_default(self):
        query = KnowledgeModuleQuery(question="SGB II", retrieval_mode="SOURCE_DISCOVERY")
        self.assertFalse(query.include_administrative_rules)
        with self.assertRaises(KnowledgeModuleError) as caught:
            KnowledgeModuleQuery(
                question="SGB II",
                retrieval_mode="SOURCE_DISCOVERY",
                document_types=("ADMINISTRATIVE_RULE",),
            )
        self.assertEqual(caught.exception.status, "CONFLICTING_KNOWLEDGE_FILTERS")


if __name__ == "__main__":
    unittest.main()
