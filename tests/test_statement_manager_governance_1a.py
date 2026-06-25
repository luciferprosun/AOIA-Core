from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.schemas.statement_manager_governance import (
    StatementDocumentKind,
    StatementGovernanceFlag,
    StatementGovernanceRequest,
    StatementGovernanceStatus,
    StatementSensitivityClass,
    StatementSourceTrust,
    build_statement_governance_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
STATEMENT_GOVERNANCE = REPO_ROOT / "runtime" / "schemas" / "statement_manager_governance.py"
HASH = "a" * 64
OTHER_HASH = "b" * 64


class StatementManagerGovernance1ATests(unittest.TestCase):
    def test_basic_statement_governance_preview_is_deterministic(self):
        first = self.preview()
        second = self.preview()

        self.assertEqual(first.statement_governance_hash, second.statement_governance_hash)
        self.assertEqual(first.statement_governance_id, second.statement_governance_id)
        self.assertEqual("statement-governance-" + first.statement_governance_hash[:24], first.statement_governance_id)
        self.assertEqual("AOIA_STATEMENT_GOVERNANCE_1A", first.schema_version)
        self.assertEqual(StatementDocumentKind.BANK_STATEMENT, first.document_kind)
        self.assertEqual(StatementSensitivityClass.FINANCIAL, first.sensitivity_class)
        self.assert_all_authority_false(first)

    def test_same_request_produces_same_hash_id(self):
        request = self.request("sparkasse bank statement")

        self.assertEqual(
            build_statement_governance_preview(request).statement_governance_hash,
            build_statement_governance_preview(request).statement_governance_hash,
        )
        self.assertEqual(
            build_statement_governance_preview(request).statement_governance_id,
            build_statement_governance_preview(request).statement_governance_id,
        )

    def test_different_document_metadata_changes_hash_id(self):
        first = self.preview("sparkasse bank statement")
        second = self.preview("jobcenter bescheid")

        self.assertNotEqual(first.document_label_hash, second.document_label_hash)
        self.assertNotEqual(first.statement_governance_hash, second.statement_governance_hash)
        self.assertNotEqual(first.statement_governance_id, second.statement_governance_id)

    def test_bank_statement_is_financial_sensitive_review_metadata_only(self):
        preview = self.preview("kontoauszug account statement sparkasse statement")

        self.assertEqual(StatementDocumentKind.BANK_STATEMENT, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.FINANCIAL, preview.sensitivity_class)
        self.assertEqual(StatementGovernanceStatus.SENSITIVE_DOCUMENT_REVIEW_REQUIRED, preview.status)
        self.assertIn(StatementGovernanceFlag.FINANCIAL_DOCUMENT, preview.flags)
        self.assertIn(StatementGovernanceFlag.BANK_STATEMENT_REVIEW_REQUIRED, preview.flags)
        self.assert_all_authority_false(preview)

    def test_official_letter_bescheid_is_official_review_metadata_only(self):
        preview = self.preview("official letter bescheid arbeitsagentur")

        self.assertEqual(StatementDocumentKind.OFFICIAL_LETTER, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.OFFICIAL, preview.sensitivity_class)
        self.assertIn(StatementGovernanceFlag.OFFICIAL_DOCUMENT, preview.flags)
        self.assert_all_authority_false(preview)

    def test_benefit_decision_is_sensitive_official_review_metadata_only(self):
        preview = self.preview("jobcenter bescheid benefit decision")

        self.assertEqual(StatementDocumentKind.BENEFIT_DECISION, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.OFFICIAL, preview.sensitivity_class)
        self.assertIn(StatementGovernanceFlag.BENEFIT_DECISION_REVIEW_REQUIRED, preview.flags)
        self.assertIn(StatementGovernanceFlag.OFFICIAL_DOCUMENT, preview.flags)
        self.assert_all_authority_false(preview)

    def test_payslip_is_financial_personal_review_metadata_only(self):
        preview = self.preview("lohnabrechnung payslip")

        self.assertEqual(StatementDocumentKind.PAYSLIP, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.FINANCIAL, preview.sensitivity_class)
        self.assertIn(StatementGovernanceFlag.FINANCIAL_DOCUMENT, preview.flags)
        self.assert_all_authority_false(preview)

    def test_identity_document_is_high_risk_review_metadata_only(self):
        preview = self.preview("passport identity id card")

        self.assertEqual(StatementDocumentKind.IDENTITY_DOCUMENT, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.IDENTITY, preview.sensitivity_class)
        self.assertIn(StatementGovernanceFlag.IDENTITY_DOCUMENT, preview.flags)
        self.assert_all_authority_false(preview)

    def test_medical_document_is_high_risk_review_metadata_only(self):
        preview = self.preview("medical doctor patient diagnosis")

        self.assertEqual(StatementDocumentKind.MEDICAL_DOCUMENT, preview.document_kind)
        self.assertEqual(StatementSensitivityClass.MEDICAL, preview.sensitivity_class)
        self.assertIn(StatementGovernanceFlag.MEDICAL_DOCUMENT, preview.flags)
        self.assert_all_authority_false(preview)

    def test_unknown_document_metadata_is_review_required(self):
        preview = self.preview("miscellaneous document", source_filename="document.bin")

        self.assertEqual(StatementDocumentKind.UNKNOWN, preview.document_kind)
        self.assertEqual(StatementGovernanceStatus.NOT_YET_GOVERNED, preview.status)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_source_file_hash_is_metadata_only_and_never_computed(self):
        preview = self.preview(source_file_hash=HASH, source_file_hash_algorithm="sha256")

        self.assertEqual(HASH, preview.source_file_hash)
        self.assertEqual("sha256", preview.source_file_hash_algorithm)
        self.assertFalse(preview.file_read)
        self.assertFalse(preview.file_opened)
        self.assert_all_authority_false(preview)

    def test_missing_source_file_hash_can_be_flagged(self):
        preview = self.preview(source_file_hash=None)

        self.assertIn(StatementGovernanceFlag.MISSING_FILE_HASH_METADATA, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_download_governance_source_hash_metadata_is_inert(self):
        preview = self.preview(
            source_download_governance_id="download-governance-example",
            source_download_governance_hash=OTHER_HASH,
        )

        self.assertEqual("download-governance-example", preview.source_download_governance_id)
        self.assertEqual(OTHER_HASH, preview.source_download_governance_hash)
        self.assertIn(StatementGovernanceFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY, preview.flags)
        self.assert_all_authority_false(preview)

    def test_automatic_fact_extraction_requests_are_blocked(self):
        cases = (
            "extract facts automatically",
            "parse now",
            "ocr now",
            "read file",
            "open file",
        )
        for phrase in cases:
            with self.subTest(phrase=phrase):
                preview = self.preview("bank statement", metadata={"request": phrase})

                self.assertEqual(StatementGovernanceStatus.BLOCKED_AUTOMATIC_FACT_EXTRACTION, preview.status)
                self.assertIn(StatementGovernanceFlag.AUTOMATIC_FACT_EXTRACTION_BLOCKED, preview.flags)
                self.assert_all_authority_false(preview)

    def test_automatic_decision_requests_are_blocked(self):
        cases = (
            ("decide eligibility", StatementGovernanceStatus.BLOCKED_FINANCIAL_DECISION_ATTEMPT),
            ("approve benefit", StatementGovernanceStatus.BLOCKED_FINANCIAL_DECISION_ATTEMPT),
            ("reject benefit", StatementGovernanceStatus.BLOCKED_FINANCIAL_DECISION_ATTEMPT),
            ("calculate legal entitlement", StatementGovernanceStatus.BLOCKED_LEGAL_DECISION_ATTEMPT),
            ("make financial decision", StatementGovernanceStatus.BLOCKED_FINANCIAL_DECISION_ATTEMPT),
        )
        for phrase, expected_status in cases:
            with self.subTest(phrase=phrase):
                preview = self.preview("bank statement", metadata={"request": phrase})

                self.assertEqual(expected_status, preview.status)
                self.assertIn(StatementGovernanceFlag.AUTOMATIC_DECISION_BLOCKED, preview.flags)
                self.assert_all_authority_false(preview)

    def test_parser_and_ocr_tool_names_are_flagged(self):
        cases = ("pdfplumber", "PyMuPDF", "fitz", "pytesseract")
        for tool_name in cases:
            with self.subTest(tool_name=tool_name):
                preview = self.preview("bank statement", metadata={"tool": tool_name})

                self.assertEqual(StatementGovernanceStatus.BLOCKED_AUTOMATIC_FACT_EXTRACTION, preview.status)
                self.assertIn(StatementGovernanceFlag.AUTOMATIC_FACT_EXTRACTION_BLOCKED, preview.flags)
                self.assert_all_authority_false(preview)

    def test_authority_claiming_metadata_is_flagged(self):
        authority_terms = (
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "file_read",
            "pdf_parsed",
            "ocr_performed",
            "facts_extracted",
            "financial_decision_made",
            "legal_decision_made",
            "benefit_decision_made",
        )
        for term in authority_terms:
            with self.subTest(term=term):
                preview = self.preview(metadata={term: True})

                self.assertTrue(
                    StatementGovernanceFlag.UNSAFE_DOCUMENT_METADATA in preview.flags
                    or StatementGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM in preview.flags
                    or StatementGovernanceFlag.AUTOMATIC_FACT_EXTRACTION_BLOCKED in preview.flags
                    or StatementGovernanceFlag.AUTOMATIC_DECISION_BLOCKED in preview.flags
                )
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_untrusted_provider_output_forces_human_review(self):
        preview = self.preview(source_trust=StatementSourceTrust.UNTRUSTED_PROVIDER_OUTPUT)

        self.assertIn(StatementGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED, preview.flags)
        self.assertIn(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_input_claims_cannot_enable_authority_fields(self):
        preview = self.preview(authority_claims={"file_read": True, "ocr_performed": True, "approval_granted": True})
        replaced = replace(
            preview,
            file_read=True,
            file_opened=True,
            file_written=True,
            pdf_parsed=True,
            ocr_performed=True,
            document_text_extracted=True,
            facts_extracted=True,
            parsing_performed=True,
            financial_decision_made=True,
            legal_decision_made=True,
            benefit_decision_made=True,
            network_called=True,
            provider_called=True,
            approval_created=True,
            gate_changed=True,
            tool_called=True,
            can_call_tool=True,
            can_execute=True,
            can_write=True,
            can_commit=True,
            can_change_approval_gate=True,
            can_change_policy=True,
            can_access_network=True,
            can_read_env=True,
            can_load_api_key=True,
        )

        self.assertIn(StatementGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM, preview.flags)
        self.assert_all_authority_false(preview)
        self.assert_all_authority_false(replaced)

    def test_inconsistent_source_hash_metadata_is_detected(self):
        cases = (
            self.request(source_download_governance_id="download-governance-example", source_download_governance_hash=None),
            self.request(source_action_proposal_id="action-proposal-example", source_action_proposal_hash=None),
            self.request(source_tool_call_preview_id="tool-call-preview-example", source_tool_call_preview_hash="not-a-hash"),
            self.request(source_intent_route_id="intent-route-example", source_intent_route_hash="not-a-hash"),
            self.request(source_policy_check_id="local-policy-check-example", source_policy_check_hash="not-a-hash"),
            self.request(source_test_runner_control_id="test-runner-control-example", source_test_runner_control_hash=None),
            self.request(source_file_hash="not-a-hash"),
            self.request(source_url_hash="not-a-hash"),
        )
        for request in cases:
            with self.subTest(request=request):
                preview = build_statement_governance_preview(request)

                self.assertEqual(StatementGovernanceStatus.INCONSISTENT_METADATA, preview.status)
                self.assertIn(StatementGovernanceFlag.INCONSISTENT_HASH_METADATA, preview.flags)
                self.assert_all_authority_false(preview)

    def test_preview_is_frozen(self):
        preview = self.preview()

        with self.assertRaises(FrozenInstanceError):
            preview.status = StatementGovernanceStatus.STATEMENT_GOVERNANCE_PREVIEW_READY

    def test_no_runtime_creation_routing_policy_or_dispatch_methods(self):
        preview = self.preview()
        forbidden_methods = (
            "execute",
            "run",
            "call",
            "invoke",
            "dispatch",
            "approve",
            "allow",
            "deny",
            "read_file",
            "open_file",
            "parse_pdf",
            "ocr",
            "extract_facts",
            "make_decision",
            "create_action_proposal",
            "build_action_proposal",
            "create_preview",
            "build_tool_call_preview",
            "route_intent",
            "evaluate_local_policy",
            "build_test_runner_control_preview",
            "build_download_governance_preview",
            "create_approval",
            "register_tool",
        )

        for method_name in forbidden_methods:
            with self.subTest(method_name=method_name):
                self.assertFalse(callable(getattr(preview, method_name, None)))

    def test_no_filesystem_reads_or_writes_occur(self):
        with TemporaryDirectory() as workspace:
            candidate = Path(workspace) / "statement.pdf"
            before = list(Path(workspace).rglob("*"))
            _preview = self.preview(source_filename=str(candidate))
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_import_has_no_side_effect_filesystem_writes(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            __import__("runtime.schemas.statement_manager_governance")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        source = STATEMENT_GOVERNANCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess",
            "os",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "http.client",
            "webbrowser",
            "playwright",
            "selenium",
            "openai",
            "anthropic",
            "git",
            "dotenv",
            "fitz",
            "pdfplumber",
            "pytesseract",
            "PIL",
            "runtime.control_write",
            "runtime.human_decision_gated_artifact_write",
            "runtime.human_decision_gate_integration",
            "runtime.tools.executor",
            "runtime.tools.browser_tools",
            "runtime.tools.shell_tools",
            "runtime.provider_runtime",
            "runtime.provider_selector",
            "runtime.schemas.action_proposal",
            "runtime.schemas.tool_call_preview",
            "runtime.schemas.intent_router",
            "runtime.schemas.local_policy_engine",
            "runtime.schemas.test_runner_controller",
            "runtime.schemas.download_manager_governance",
            "runtime.schemas.approval_decision",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, forbidden_modules)
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn(node.module, forbidden_modules)

        lowered = source.lower()
        forbidden_terms = (
            "sub" + "process(",
            "os" + "." + "system(",
            "popen",
            "socket",
            "requests",
            "urllib",
            "http.client",
            "open(",
            ".read(",
            ".write(",
            "mkdir(",
            "pathlib",
            "shutil",
            "webbrowser",
            "playwright",
            "selenium",
            "dotenv",
            "os.environ",
            "getenv(",
            "pdf" + "plumber",
            "fi" + "tz",
            "pytess" + "eract",
            "dispatch(",
            "invoke(",
            "execute(",
            "approve(",
            "allow(",
            "deny(",
            "read_file(",
            "open_file(",
            "parse_pdf(",
            "ocr(",
            "extract_facts(",
            "make_decision(",
            "build_action_proposal(",
            "build_tool_call_preview(",
            "route_intent(",
            "evaluate_local_policy(",
            "build_test_runner_control_preview(",
            "build_download_governance_preview(",
            "create_action_proposal",
            "create_preview",
            "create_approval",
            "approvaldecision",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

    def request(self, document_label="sparkasse bank statement", **kwargs):
        base = {
            "document_label": document_label,
            "source_filename": "statement.pdf",
            "source_file_hash": HASH,
            "source_file_hash_algorithm": "sha256",
        }
        base.update(kwargs)
        return StatementGovernanceRequest(**base)

    def preview(self, document_label="sparkasse bank statement", **kwargs):
        return build_statement_governance_preview(self.request(document_label, **kwargs))

    def assert_all_authority_false(self, preview):
        self.assertFalse(preview.file_read)
        self.assertFalse(preview.file_opened)
        self.assertFalse(preview.file_written)
        self.assertFalse(preview.pdf_parsed)
        self.assertFalse(preview.ocr_performed)
        self.assertFalse(preview.document_text_extracted)
        self.assertFalse(preview.facts_extracted)
        self.assertFalse(preview.parsing_performed)
        self.assertFalse(preview.financial_decision_made)
        self.assertFalse(preview.legal_decision_made)
        self.assertFalse(preview.benefit_decision_made)
        self.assertFalse(preview.network_called)
        self.assertFalse(preview.provider_called)
        self.assertFalse(preview.approval_created)
        self.assertFalse(preview.gate_changed)
        self.assertFalse(preview.tool_called)
        self.assertFalse(preview.can_call_tool)
        self.assertFalse(preview.can_execute)
        self.assertFalse(preview.can_write)
        self.assertFalse(preview.can_commit)
        self.assertFalse(preview.can_change_approval_gate)
        self.assertFalse(preview.can_change_policy)
        self.assertFalse(preview.can_access_network)
        self.assertFalse(preview.can_read_env)
        self.assertFalse(preview.can_load_api_key)


if __name__ == "__main__":
    unittest.main()
