from __future__ import annotations

import json
import unittest

from runtime.knowledge_modules.context_policy import DEFAULT_KNOWLEDGE_RESPONSE_POLICY
from runtime.knowledge_modules.contracts import KnowledgeModuleError
from runtime.knowledge_modules.structured_answer import parse_structured_knowledge_answer
from tests.knowledge_context_test_support_1a import context_fixture, structured_answer_payload


class StructuredKnowledgeAnswer1ATests(unittest.TestCase):
    def test_strict_valid_answer_parses_deterministically(self):
        package = context_fixture().package
        raw = structured_answer_payload(package)
        first = parse_structured_knowledge_answer(raw, DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
        second = parse_structured_knowledge_answer(raw, DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
        self.assertEqual(first.answer_hash, second.answer_hash)
        self.assertEqual(first.authority_status, "NON_AUTHORITATIVE_PROVIDER_OUTPUT")
        self.assertEqual(first.claims[0].confidence_label, "EVIDENCE_DIRECT")

    def test_prose_and_markdown_wrappers_are_rejected_without_repair(self):
        raw = structured_answer_payload(context_fixture().package)
        for wrapped in (f"Answer: {raw}", f"```json\n{raw}\n```"):
            with self.subTest(wrapped=wrapped[:8]):
                with self.assertRaises(KnowledgeModuleError) as caught:
                    parse_structured_knowledge_answer(wrapped, DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
                self.assertEqual(caught.exception.status, "PROVIDER_OUTPUT_MALFORMED")

    def test_unknown_fields_and_authority_claims_are_rejected(self):
        payload = json.loads(structured_answer_payload(context_fixture().package))
        payload["tool_calls"] = []
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(json.dumps(payload), DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
        payload.pop("tool_calls")
        payload["authority_status"] = "AUTHORITATIVE"
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(json.dumps(payload), DEFAULT_KNOWLEDGE_RESPONSE_POLICY)

    def test_duplicate_fields_and_non_json_numbers_are_rejected(self):
        raw = structured_answer_payload(context_fixture().package)
        duplicate = raw.replace(
            '"schema_version":"structured-knowledge-answer-1a"',
            '"schema_version":"structured-knowledge-answer-1a","schema_version":"structured-knowledge-answer-1a"',
            1,
        )
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(duplicate, DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
        non_json = raw.replace('"answer_markdown":"A bounded, non-authoritative answer."', '"answer_markdown":NaN', 1)
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(non_json, DEFAULT_KNOWLEDGE_RESPONSE_POLICY)

    def test_malformed_temporal_scope_and_invented_claim_kind_are_rejected(self):
        payload = json.loads(structured_answer_payload(context_fixture().package))
        payload["claims"][0]["temporal_scope"] = "today"
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(json.dumps(payload), DEFAULT_KNOWLEDGE_RESPONSE_POLICY)
        payload["claims"][0]["temporal_scope"] = "CURRENTNESS_NOT_VERIFIED"
        payload["claims"][0]["claim_kind"] = "BINDING_LEGAL_ADVICE"
        with self.assertRaises(KnowledgeModuleError):
            parse_structured_knowledge_answer(json.dumps(payload), DEFAULT_KNOWLEDGE_RESPONSE_POLICY)


if __name__ == "__main__":
    unittest.main()
