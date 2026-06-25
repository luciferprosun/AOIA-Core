from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.schemas.download_manager_governance import (
    DownloadGovernanceFlag,
    DownloadGovernanceRequest,
    DownloadGovernanceStatus,
    DownloadSourceTrust,
    DownloadTargetKind,
    build_download_governance_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_GOVERNANCE = REPO_ROOT / "runtime" / "schemas" / "download_manager_governance.py"


class DownloadManagerGovernance1ATests(unittest.TestCase):
    def test_basic_download_governance_preview_is_deterministic(self):
        first = self.preview()
        second = self.preview()

        self.assertEqual(first.download_governance_hash, second.download_governance_hash)
        self.assertEqual(first.download_governance_id, second.download_governance_id)
        self.assertEqual("download-governance-" + first.download_governance_hash[:24], first.download_governance_id)
        self.assertEqual("AOIA_DOWNLOAD_GOVERNANCE_1A", first.schema_version)
        self.assertEqual(DownloadTargetKind.PDF_DOCUMENT, first.target_kind)
        self.assertEqual(DownloadGovernanceStatus.DOWNLOAD_REVIEW_REQUIRED, first.status)
        self.assert_all_authority_false(first)

    def test_same_request_produces_same_hash_id(self):
        request = self.request("https://example.com/report.pdf", "downloads/report.pdf")

        self.assertEqual(
            build_download_governance_preview(request).download_governance_hash,
            build_download_governance_preview(request).download_governance_hash,
        )
        self.assertEqual(
            build_download_governance_preview(request).download_governance_id,
            build_download_governance_preview(request).download_governance_id,
        )

    def test_different_url_or_target_changes_hash_id(self):
        first = self.preview("https://example.com/report.pdf", "downloads/report.pdf")
        second = self.preview("https://example.com/statement.pdf", "downloads/report.pdf")
        third = self.preview("https://example.com/report.pdf", "downloads/statement.pdf")

        self.assertNotEqual(first.source_url_hash, second.source_url_hash)
        self.assertNotEqual(first.download_governance_hash, second.download_governance_hash)
        self.assertNotEqual(first.download_governance_id, second.download_governance_id)
        self.assertNotEqual(first.target_path_hash, third.target_path_hash)
        self.assertNotEqual(first.download_governance_hash, third.download_governance_hash)

    def test_clean_external_https_pdf_is_review_required_metadata_only(self):
        preview = self.preview("https://example.com/statement.pdf", "downloads/statement.pdf")

        self.assertEqual(DownloadGovernanceStatus.DOWNLOAD_REVIEW_REQUIRED, preview.status)
        self.assertIn(DownloadGovernanceFlag.EXTERNAL_URL_REVIEW_REQUIRED, preview.flags)
        self.assertIn(DownloadGovernanceFlag.PDF_REVIEW_REQUIRED, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assertFalse(preview.download_performed)
        self.assertFalse(preview.network_called)
        self.assert_all_authority_false(preview)

    def test_safe_relative_target_path_is_metadata_only(self):
        for target_path in (
            "downloads/example.pdf",
            "downloads/statement.pdf",
            "downloads/document.txt",
            "downloads/report.md",
        ):
            with self.subTest(target_path=target_path):
                preview = self.preview("https://example.com/file.pdf", target_path)

                self.assertEqual(target_path, preview.normalized_target_path)
                self.assertNotIn(DownloadGovernanceFlag.UNSAFE_TARGET_PATH, preview.flags)
                self.assert_all_authority_false(preview)

    def test_absolute_target_path_is_blocked(self):
        preview = self.preview("https://example.com/passwd", "/etc/passwd")

        self.assertEqual(DownloadGovernanceStatus.BLOCKED_UNSAFE_TARGET_PATH, preview.status)
        self.assertIn(DownloadGovernanceFlag.ABSOLUTE_PATH_BLOCKED, preview.flags)
        self.assertIn(DownloadGovernanceFlag.UNSAFE_TARGET_PATH, preview.flags)
        self.assert_all_authority_false(preview)

    def test_path_traversal_target_path_is_blocked(self):
        for target_path in ("../secret.pdf", "downloads/../../secret.pdf"):
            with self.subTest(target_path=target_path):
                preview = self.preview("https://example.com/secret.pdf", target_path)

                self.assertEqual(DownloadGovernanceStatus.BLOCKED_UNSAFE_TARGET_PATH, preview.status)
                self.assertIn(DownloadGovernanceFlag.PATH_TRAVERSAL_BLOCKED, preview.flags)
                self.assert_all_authority_false(preview)

    def test_empty_target_path_is_malformed(self):
        preview = self.preview("https://example.com/document.pdf", "")

        self.assertEqual(DownloadGovernanceStatus.MALFORMED_REQUEST, preview.status)
        self.assertIn(DownloadGovernanceFlag.UNSAFE_TARGET_PATH, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_null_byte_target_path_is_blocked(self):
        preview = self.preview("https://example.com/document.pdf", "downloads/file.pdf\x00")

        self.assertEqual(DownloadGovernanceStatus.BLOCKED_UNSAFE_TARGET_PATH, preview.status)
        self.assertIn(DownloadGovernanceFlag.NULL_BYTE_BLOCKED, preview.flags)
        self.assert_all_authority_false(preview)

    def test_document_like_extensions_are_metadata_only(self):
        cases = {
            ".pdf": DownloadTargetKind.PDF_DOCUMENT,
            ".txt": DownloadTargetKind.TEXT_DOCUMENT,
            ".md": DownloadTargetKind.MARKDOWN_DOCUMENT,
            ".csv": DownloadTargetKind.CSV_DOCUMENT,
            ".json": DownloadTargetKind.JSON_DOCUMENT,
            ".png": DownloadTargetKind.IMAGE_FILE,
            ".jpg": DownloadTargetKind.IMAGE_FILE,
            ".jpeg": DownloadTargetKind.IMAGE_FILE,
            ".webp": DownloadTargetKind.IMAGE_FILE,
        }
        for extension, target_kind in cases.items():
            with self.subTest(extension=extension):
                preview = self.preview("https://example.com/file" + extension, "downloads/file" + extension)

                self.assertEqual(target_kind, preview.target_kind)
                self.assertNotIn(DownloadGovernanceFlag.RISKY_FILE_EXTENSION, preview.flags)
                self.assertFalse(preview.file_written)
                self.assert_all_authority_false(preview)

    def test_executable_and_script_extensions_are_blocked(self):
        cases = {
            ".exe": DownloadGovernanceFlag.EXECUTABLE_FILE_BLOCKED,
            ".sh": DownloadGovernanceFlag.SCRIPT_FILE_BLOCKED,
            ".py": DownloadGovernanceFlag.SCRIPT_FILE_BLOCKED,
            ".js": DownloadGovernanceFlag.SCRIPT_FILE_BLOCKED,
            ".ps1": DownloadGovernanceFlag.SCRIPT_FILE_BLOCKED,
        }
        for extension, expected_flag in cases.items():
            with self.subTest(extension=extension):
                preview = self.preview("https://example.com/file" + extension, "downloads/file" + extension)

                self.assertEqual(DownloadGovernanceStatus.BLOCKED_RISKY_FILE_TYPE, preview.status)
                self.assertIn(expected_flag, preview.flags)
                self.assertIn(DownloadGovernanceFlag.RISKY_FILE_EXTENSION, preview.flags)
                self.assertTrue(preview.quarantine_required)
                self.assert_all_authority_false(preview)

    def test_archive_extensions_are_review_required_or_blocked(self):
        for extension in (".zip", ".tar", ".gz", ".7z", ".rar"):
            with self.subTest(extension=extension):
                preview = self.preview("https://example.com/archive" + extension, "downloads/archive" + extension)

                self.assertEqual(DownloadTargetKind.ARCHIVE_FILE, preview.target_kind)
                self.assertIn(DownloadGovernanceFlag.ARCHIVE_REVIEW_REQUIRED, preview.flags)
                self.assertIn(DownloadGovernanceFlag.RISKY_FILE_EXTENSION, preview.flags)
                self.assertTrue(preview.human_review_required)
                self.assertTrue(preview.quarantine_required)
                self.assert_all_authority_false(preview)

    def test_unsafe_urls_are_flagged_or_blocked(self):
        unsafe_urls = (
            "javascript:alert(1)",
            "data:text/html",
            "file:///etc/passwd",
            "about:config",
            "chrome://settings",
            "ftp://example.com/file.pdf",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal",
            "http://localhost/admin.pdf",
            "http://127.0.0.1:8000/private.pdf",
            "https://example.com/login",
            "https://example.com/oauth",
            "https://example.com/checkout",
            "https://example.com/download?token=secret",
        )
        for source_url in unsafe_urls:
            with self.subTest(source_url=source_url):
                preview = self.preview(source_url, "downloads/file.pdf")

                self.assertIn(
                    preview.status,
                    {
                        DownloadGovernanceStatus.BLOCKED_UNSAFE_URL,
                        DownloadGovernanceStatus.BLOCKED_CREDENTIAL_OR_SECRET_RISK,
                    },
                )
                self.assertTrue(
                    DownloadGovernanceFlag.UNSAFE_URL in preview.flags
                    or DownloadGovernanceFlag.SECRET_OR_TOKEN_PATTERN in preview.flags
                )
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_authority_claiming_metadata_is_flagged(self):
        authority_terms = (
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "download_performed",
            "network_called",
            "url_fetched",
            "file_written",
            "directory_created",
            "quarantine_created",
        )
        for term in authority_terms:
            with self.subTest(term=term):
                preview = self.preview(metadata={term: True})

                self.assertTrue(
                    DownloadGovernanceFlag.SECRET_OR_TOKEN_PATTERN in preview.flags
                    or DownloadGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM in preview.flags
                )
                self.assertTrue(preview.human_review_required)
                self.assert_all_authority_false(preview)

    def test_untrusted_provider_output_forces_human_review(self):
        preview = self.preview(source_trust=DownloadSourceTrust.UNTRUSTED_PROVIDER_OUTPUT)

        self.assertIn(DownloadGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED, preview.flags)
        self.assertIn(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED, preview.flags)
        self.assertTrue(preview.human_review_required)
        self.assert_all_authority_false(preview)

    def test_expected_content_hash_is_metadata_only(self):
        expected_hash = "a" * 64
        preview = self.preview(expected_content_hash=expected_hash, expected_content_hash_algorithm="sha256")

        self.assertEqual(expected_hash, preview.expected_content_hash)
        self.assertEqual("sha256", preview.expected_content_hash_algorithm)
        self.assertFalse(preview.content_hash_computed_from_file)
        self.assert_all_authority_false(preview)

    def test_quarantine_required_is_metadata_only_and_creates_no_files(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            preview = self.preview("https://example.com/file.zip", "downloads/file.zip")
            after = list(Path(workspace).rglob("*"))

        self.assertTrue(preview.quarantine_required)
        self.assertEqual("quarantine_required_metadata_only", preview.quarantine_label)
        self.assertFalse(preview.quarantine_created)
        self.assertEqual(before, after)
        self.assert_all_authority_false(preview)

    def test_input_claims_cannot_enable_authority_fields(self):
        preview = self.preview(
            authority_claims={
                "can_access_network": True,
                "download_performed": True,
                "approval_granted": True,
            },
        )
        replaced = replace(
            preview,
            download_performed=True,
            network_called=True,
            url_fetched=True,
            file_opened=True,
            file_written=True,
            directory_created=True,
            quarantine_created=True,
            content_hash_computed_from_file=True,
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

        self.assertIn(DownloadGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM, preview.flags)
        self.assert_all_authority_false(preview)
        self.assert_all_authority_false(replaced)

    def test_inconsistent_source_hash_metadata_is_detected(self):
        cases = (
            self.request(source_action_proposal_id="action-proposal-example", source_action_proposal_hash=None),
            self.request(source_tool_call_preview_id="tool-call-preview-example", source_tool_call_preview_hash=None),
            self.request(source_intent_route_id="intent-route-example", source_intent_route_hash="not-a-hash"),
            self.request(source_policy_check_id="local-policy-check-example", source_policy_check_hash="not-a-hash"),
            self.request(source_test_runner_control_id="test-runner-control-example", source_test_runner_control_hash=None),
            self.request(expected_content_hash="not-a-hash", expected_content_hash_algorithm="sha256"),
        )
        for request in cases:
            with self.subTest(request=request):
                preview = build_download_governance_preview(request)

                self.assertEqual(DownloadGovernanceStatus.INCONSISTENT_METADATA, preview.status)
                self.assertIn(DownloadGovernanceFlag.INCONSISTENT_HASH_METADATA, preview.flags)
                self.assert_all_authority_false(preview)

    def test_preview_is_frozen(self):
        preview = self.preview()

        with self.assertRaises(FrozenInstanceError):
            preview.status = DownloadGovernanceStatus.DOWNLOAD_PREVIEW_READY

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
            "fetch",
            "download",
            "open_url",
            "write_file",
            "create_directory",
            "create_action_proposal",
            "build_action_proposal",
            "create_preview",
            "build_tool_call_preview",
            "route_intent",
            "evaluate_local_policy",
            "build_test_runner_control_preview",
            "create_approval",
            "register_tool",
        )

        for method_name in forbidden_methods:
            with self.subTest(method_name=method_name):
                self.assertFalse(callable(getattr(preview, method_name, None)))

    def test_no_filesystem_writes_occur(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            _preview = self.preview("https://example.com/document.pdf", f"{workspace}/document.pdf")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_import_has_no_side_effect_filesystem_writes(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            __import__("runtime.schemas.download_manager_governance")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        source = DOWNLOAD_GOVERNANCE.read_text(encoding="utf-8")
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
            "dispatch(",
            "invoke(",
            "execute(",
            "approve(",
            "allow(",
            "deny(",
            "fetch(",
            "download(",
            "open_url(",
            "write_file(",
            "create_directory(",
            "build_action_proposal(",
            "build_tool_call_preview(",
            "route_intent(",
            "evaluate_local_policy(",
            "build_test_runner_control_preview(",
            "create_action_proposal",
            "create_preview",
            "create_approval",
            "approvaldecision",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

    def request(self, source_url="https://example.com/report.pdf", target_path="downloads/report.pdf", **kwargs):
        base = {
            "source_url": source_url,
            "proposed_target_path": target_path,
        }
        base.update(kwargs)
        return DownloadGovernanceRequest(**base)

    def preview(self, source_url="https://example.com/report.pdf", target_path="downloads/report.pdf", **kwargs):
        return build_download_governance_preview(self.request(source_url, target_path, **kwargs))

    def assert_all_authority_false(self, preview):
        self.assertFalse(preview.download_performed)
        self.assertFalse(preview.network_called)
        self.assertFalse(preview.url_fetched)
        self.assertFalse(preview.file_opened)
        self.assertFalse(preview.file_written)
        self.assertFalse(preview.directory_created)
        self.assertFalse(preview.quarantine_created)
        self.assertFalse(preview.content_hash_computed_from_file)
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
