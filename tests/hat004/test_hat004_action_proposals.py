from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from runtime.schemas.hat004_action_proposals import (
    FORBIDDEN_NEAR_TERM_ACTIONS,
    HUMAN_REVIEW_REQUIRED_ACTIONS,
    READ_ONLY_ACTIONS,
    Hat004ActionDomain,
    Hat004ActionProposal,
    Hat004ReviewState,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "runtime" / "schemas" / "hat004_action_proposals.py"
REPORT_PATH = PROJECT_ROOT / "docs" / "audit" / "HAT_004_INERT_SCHEMA_DEFINITION.md"


class Hat004ActionProposalTests(unittest.TestCase):
    def test_read_only_browser_candidate_is_inert(self) -> None:
        proposal = Hat004ActionProposal(
            action_type="browser_read_visible_text",
            target="https://example.invalid/page",
            reason="review visible text proposal shape",
            source="unit_test",
            created_by="test_case",
            proposal_id="fixed-id",
        )

        self.assertEqual(Hat004ActionDomain.BROWSER, proposal.domain)
        self.assertEqual(Hat004ReviewState.READ_ONLY_CANDIDATE, proposal.review_state)
        self.assertFalse(proposal.requires_human_review)
        self.assertFalse(proposal.execution_permitted)
        self.assertTrue(proposal.dry_run)
        self.assertTrue(proposal.proposal_only)

    def test_human_review_required_browser_candidate_is_not_executable(self) -> None:
        proposal = Hat004ActionProposal(
            action_type="browser_click_visible_element",
            target="button: Continue",
            reason="clicks require human review",
            source="unit_test",
            created_by="test_case",
        )

        self.assertEqual(Hat004ReviewState.REQUIRES_HUMAN_REVIEW, proposal.review_state)
        self.assertTrue(proposal.requires_human_review)
        self.assertFalse(proposal.execution_permitted)

    def test_forbidden_near_term_login_action_is_representable_but_blocked(self) -> None:
        proposal = Hat004ActionProposal(
            action_type="browser_login",
            target="login form",
            reason="forbidden near-term action vocabulary",
            source="unit_test",
            created_by="test_case",
        )

        self.assertEqual(Hat004ReviewState.FORBIDDEN_NEAR_TERM, proposal.review_state)
        self.assertTrue(proposal.requires_human_review)
        self.assertTrue(proposal.forbidden_near_term)
        self.assertFalse(proposal.execution_permitted)

    def test_file_pdf_and_zip_domains_are_represented_as_proposals_only(self) -> None:
        examples = {
            "file_describe_local_candidate": Hat004ActionDomain.FILE,
            "pdf_describe_candidate": Hat004ActionDomain.PDF,
            "zip_describe_candidate": Hat004ActionDomain.ZIP,
        }
        for action_type, domain in examples.items():
            with self.subTest(action_type=action_type):
                proposal = Hat004ActionProposal(
                    action_type=action_type,
                    target="local candidate path string only",
                    reason="proposal vocabulary only",
                    source="unit_test",
                    created_by="test_case",
                )
                self.assertEqual(domain, proposal.domain)
                self.assertTrue(proposal.proposal_only)
                self.assertFalse(proposal.execution_permitted)

    def test_round_trip_preserves_inert_fields(self) -> None:
        proposal = Hat004ActionProposal(
            action_type="zip_list_entries_review",
            target="candidate.zip",
            reason="listing ZIP entries requires review",
            source="unit_test",
            created_by="test_case",
            metadata={"ticket": "H4-B"},
            proposal_id="h4b-fixed",
        )
        restored = Hat004ActionProposal.from_dict(proposal.to_dict())

        self.assertEqual(proposal.to_dict(), restored.to_dict())

    def test_execution_and_autonomous_flags_are_rejected(self) -> None:
        bad_flags = {
            "dry_run": False,
            "proposal_only": False,
            "execution_permitted": True,
            "autonomous_action": True,
            "login_requested": True,
            "credential_handling_requested": True,
            "cookie_access_requested": True,
            "session_access_requested": True,
            "form_submission_requested": True,
            "download_requested": True,
            "file_write_requested": True,
            "pdf_parse_requested": True,
            "zip_unpack_requested": True,
            "external_network_action_requested": True,
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "action_type": "browser_read_current_url",
                    "target": "about:blank",
                    "reason": "reject unsafe flag",
                    "source": "unit_test",
                    "created_by": "test_case",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    Hat004ActionProposal(**kwargs)

    def test_from_dict_rejects_unknown_payload_fields(self) -> None:
        payload = {
            "action_type": "browser_read_current_url",
            "target": "about:blank",
            "reason": "reject unknown field",
            "source": "unit_test",
            "created_by": "test_case",
            "browser_session_token": "must-not-be-carried",
        }

        with self.assertRaises(ValueError):
            Hat004ActionProposal.from_dict(payload)

    def test_from_dict_rejects_mismatched_derived_fields(self) -> None:
        base_payload = Hat004ActionProposal(
            action_type="pdf_extract_text_review",
            target="candidate.pdf",
            reason="PDF extraction proposal requires review",
            source="unit_test",
            created_by="test_case",
        ).to_dict()
        bad_values = {
            "domain": "browser",
            "review_state": Hat004ReviewState.READ_ONLY_CANDIDATE.value,
            "requires_human_review": False,
            "forbidden_near_term": True,
        }

        for field, value in bad_values.items():
            with self.subTest(field=field):
                payload = dict(base_payload)
                payload[field] = value
                with self.assertRaises(ValueError):
                    Hat004ActionProposal.from_dict(payload)

        type_mismatch_payload = dict(base_payload)
        type_mismatch_payload["requires_human_review"] = 1
        with self.assertRaises(ValueError):
            Hat004ActionProposal.from_dict(type_mismatch_payload)

    def test_unknown_action_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Hat004ActionProposal(
                action_type="browser_execute_arbitrary_script",
                target="page",
                reason="unknown action",
                source="unit_test",
                created_by="test_case",
            )

    def test_action_sets_are_non_empty_and_disjoint(self) -> None:
        self.assertTrue(READ_ONLY_ACTIONS)
        self.assertTrue(HUMAN_REVIEW_REQUIRED_ACTIONS)
        self.assertTrue(FORBIDDEN_NEAR_TERM_ACTIONS)
        self.assertTrue(READ_ONLY_ACTIONS.isdisjoint(HUMAN_REVIEW_REQUIRED_ACTIONS))
        self.assertTrue(READ_ONLY_ACTIONS.isdisjoint(FORBIDDEN_NEAR_TERM_ACTIONS))
        self.assertTrue(HUMAN_REVIEW_REQUIRED_ACTIONS.isdisjoint(FORBIDDEN_NEAR_TERM_ACTIONS))

    def test_schema_module_contains_no_runtime_execution_or_browser_imports(self) -> None:
        source = SCHEMA_PATH.read_text(encoding="utf-8")
        forbidden_patterns = (
            r"\bplaywright\b",
            r"\bselenium\b",
            r"\brequests\b",
            r"\bsubprocess\b",
            r"\bsocket\b",
            r"\bexecutor\b",
            r"\bbrowser_tools\b",
            r"\bshell_tools\b",
            r"\bevent_ledger\b",
            r"\bopen\(",
            r"\bread_text\(",
            r"\bwrite_text\(",
            r"\bmkdir\(",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, source))

        tree = ast.parse(source)
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, forbidden_calls)

    def test_schema_definition_report_exists_and_states_non_implementation(self) -> None:
        text = REPORT_PATH.read_text(encoding="utf-8")

        self.assertIn("H4-B defines inert proposal vocabulary only.", text)
        self.assertIn("No browser automation was implemented.", text)
        self.assertIn("No PDF or ZIP file was read, created, modified, packed, unpacked, or parsed.", text)
        self.assertIn("execution_permitted`: `false", text)


if __name__ == "__main__":
    unittest.main()
