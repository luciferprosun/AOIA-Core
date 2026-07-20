from __future__ import annotations

import json
import unittest

from runtime.knowledge_modules.citation_validation import (
    NO_KNOWLEDGE_MODULE_SELECTED,
    PROVIDER_RESPONSE_INVALID_CITATIONS,
    PROVIDER_RESPONSE_MISSING_CITATIONS,
    PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
    PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE,
    validate_knowledge_citations,
)
from runtime.knowledge_modules.context_policy import DEFAULT_KNOWLEDGE_RESPONSE_POLICY
from runtime.knowledge_modules.structured_answer import parse_structured_knowledge_answer
from tests.knowledge_context_test_support_1a import (
    context_fixture,
    structured_answer_payload,
    zero_module_fixture,
)


def parsed(payload: dict[str, object]):
    return parse_structured_knowledge_answer(
        json.dumps(payload, sort_keys=True),
        DEFAULT_KNOWLEDGE_RESPONSE_POLICY,
    )


class KnowledgeCitationValidation1ATests(unittest.TestCase):
    def test_exact_current_request_reference_is_structurally_grounded(self):
        package = context_fixture().package
        answer = parse_structured_knowledge_answer(
            structured_answer_payload(package), DEFAULT_KNOWLEDGE_RESPONSE_POLICY
        )
        result = validate_knowledge_citations(answer, package)
        self.assertEqual(result.status, PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED)
        self.assertTrue(result.valid)

    def test_missing_and_cross_request_citations_are_reported_without_retry(self):
        package = context_fixture().package
        payload = json.loads(structured_answer_payload(package))
        payload["claims"][0]["evidence_ids"] = []
        payload["cited_evidence_ids"] = []
        missing = validate_knowledge_citations(parsed(payload), package)
        self.assertEqual(missing.status, PROVIDER_RESPONSE_MISSING_CITATIONS)

        other = context_fixture(("other-module-1a",)).package
        foreign_id = other.module_sections[0].evidence_items[0].evidence_id
        payload["claims"][0]["evidence_ids"] = [foreign_id]
        payload["cited_evidence_ids"] = [foreign_id]
        invalid = validate_knowledge_citations(parsed(payload), package)
        self.assertEqual(invalid.status, PROVIDER_RESPONSE_INVALID_CITATIONS)
        self.assertIn(foreign_id, invalid.invalid_evidence_ids)

    def test_cross_module_evidence_confusion_is_rejected(self):
        package = context_fixture(("alpha-module-1a", "beta-module-1a")).package
        alpha_id = package.module_sections[0].evidence_items[0].evidence_id
        payload = json.loads(structured_answer_payload(package))
        payload["claims"][0]["module_ids"] = ["beta-module-1a"]
        payload["claims"][0]["evidence_ids"] = [alpha_id]
        payload["cited_evidence_ids"] = [alpha_id]
        result = validate_knowledge_citations(parsed(payload), package)
        self.assertEqual(result.status, PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE)
        self.assertEqual(result.wrong_module_references[0][1], alpha_id)

    def test_zero_module_answer_must_not_cite_module_evidence(self):
        package = zero_module_fixture().package
        clean = parse_structured_knowledge_answer(
            structured_answer_payload(package), DEFAULT_KNOWLEDGE_RESPONSE_POLICY
        )
        self.assertEqual(validate_knowledge_citations(clean, package).status, NO_KNOWLEDGE_MODULE_SELECTED)
        payload = json.loads(structured_answer_payload(package))
        payload["claims"][0]["module_ids"] = ["unselected-module"]
        payload["claims"][0]["evidence_ids"] = ["foreign-evidence"]
        payload["cited_evidence_ids"] = ["foreign-evidence"]
        invalid = validate_knowledge_citations(parsed(payload), package)
        self.assertEqual(invalid.status, PROVIDER_RESPONSE_INVALID_CITATIONS)


if __name__ == "__main__":
    unittest.main()
