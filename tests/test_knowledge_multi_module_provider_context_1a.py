from __future__ import annotations

import json
import unittest

from runtime.knowledge_modules.citation_validation import (
    PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
    PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE,
)
from runtime.knowledge_modules.context_policy import DEFAULT_KNOWLEDGE_RESPONSE_POLICY
from runtime.knowledge_modules.structured_answer import parse_structured_knowledge_answer
from runtime.knowledge_modules.citation_validation import validate_knowledge_citations
from tests.knowledge_context_test_support_1a import context_fixture, structured_answer_payload


class KnowledgeMultiModuleProviderContext1ATests(unittest.TestCase):
    def test_two_modules_remain_independent_and_are_not_semantically_merged(self):
        package = context_fixture(("alpha-module-1a", "beta-module-1a")).package
        self.assertEqual(len(package.module_sections), 2)
        self.assertEqual(
            tuple(section.module_id for section in package.module_sections),
            package.selected_module_ids,
        )
        self.assertNotEqual(
            package.module_sections[0].module_section_hash,
            package.module_sections[1].module_section_hash,
        )
        self.assertEqual(
            sum(len(section.evidence_items) for section in package.module_sections),
            package.total_evidence_items,
        )

    def test_each_claim_may_cite_its_own_module_without_provenance_loss(self):
        package = context_fixture(("alpha-module-1a", "beta-module-1a")).package
        alpha = package.module_sections[0].evidence_items[0]
        beta = package.module_sections[1].evidence_items[0]
        payload = json.loads(structured_answer_payload(package))
        payload["claims"] = [
            {
                **payload["claims"][0],
                "claim_id": "alpha-claim",
                "module_ids": [alpha.module_id],
                "evidence_ids": [alpha.evidence_id],
            },
            {
                **payload["claims"][0],
                "claim_id": "beta-claim",
                "module_ids": [beta.module_id],
                "evidence_ids": [beta.evidence_id],
            },
        ]
        payload["cited_evidence_ids"] = [alpha.evidence_id, beta.evidence_id]
        answer = parse_structured_knowledge_answer(
            json.dumps(payload), DEFAULT_KNOWLEDGE_RESPONSE_POLICY
        )
        result = validate_knowledge_citations(answer, package)
        self.assertEqual(result.status, PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED)

    def test_one_module_failure_remains_visible_and_other_module_continues(self):
        package = context_fixture(
            ("failed-module-1a", "good-module-1a"), include_failure=True
        ).package
        self.assertEqual(len(package.module_failures), 1)
        self.assertEqual(package.module_failures[0].module_id, "failed-module-1a")
        self.assertEqual(package.module_sections[0].evidence_items, ())
        self.assertEqual(len(package.module_sections[1].evidence_items), 1)


if __name__ == "__main__":
    unittest.main()
