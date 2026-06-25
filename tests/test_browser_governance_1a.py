from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.schemas.browser_governance import (
    BrowserActionKind,
    BrowserGovernanceFlag,
    BrowserGovernanceRequest,
    BrowserGovernanceStatus,
    BrowserSourceTrust,
    build_browser_governance_check,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
BROWSER_GOVERNANCE = REPO_ROOT / "runtime" / "schemas" / "browser_governance.py"
HASH = "a" * 64


class BrowserGovernance1ATests(unittest.TestCase):
    def test_basic_browser_governance_check_is_deterministic(self):
        first = self.check()
        second = self.check()

        self.assertEqual(first.browser_governance_hash, second.browser_governance_hash)
        self.assertEqual(first.browser_governance_id, second.browser_governance_id)
        self.assertEqual("browser-governance-" + first.browser_governance_hash[:24], first.browser_governance_id)
        self.assertEqual("AOIA_BROWSER_GOVERNANCE_1A", first.schema_version)
        self.assertEqual(BrowserActionKind.READ_ONLY_VIEW, first.action_kind)
        self.assertEqual(BrowserGovernanceStatus.READ_ONLY_BROWSER_REVIEW_REQUIRED, first.status)
        self.assert_all_authority_false(first)

    def test_same_request_produces_same_hash_id(self):
        request = self.request(BrowserActionKind.URL_REVIEW, "https://example.com")

        self.assertEqual(
            build_browser_governance_check(request).browser_governance_hash,
            build_browser_governance_check(request).browser_governance_hash,
        )
        self.assertEqual(
            build_browser_governance_check(request).browser_governance_id,
            build_browser_governance_check(request).browser_governance_id,
        )

    def test_different_action_kind_or_url_changes_hash_id(self):
        first = self.check(BrowserActionKind.READ_ONLY_VIEW, "https://example.com")
        second = self.check(BrowserActionKind.URL_REVIEW, "https://example.com")
        third = self.check(BrowserActionKind.READ_ONLY_VIEW, "https://example.org")

        self.assertNotEqual(first.browser_governance_hash, second.browser_governance_hash)
        self.assertNotEqual(first.browser_governance_id, second.browser_governance_id)
        self.assertNotEqual(first.target_url_hash, third.target_url_hash)
        self.assertNotEqual(first.browser_governance_hash, third.browser_governance_hash)

    def test_clean_external_https_url_is_review_required_metadata_only(self):
        check = self.check(BrowserActionKind.READ_ONLY_VIEW, "https://example.com/page")

        self.assertEqual(BrowserGovernanceStatus.READ_ONLY_BROWSER_REVIEW_REQUIRED, check.status)
        self.assertIn(BrowserGovernanceFlag.EXTERNAL_URL_REVIEW_REQUIRED, check.flags)
        self.assertIn(BrowserGovernanceFlag.READ_ONLY_BROWSER_METADATA, check.flags)
        self.assertTrue(check.human_review_required)
        self.assert_all_authority_false(check)

    def test_read_only_view_does_not_open_browser(self):
        check = self.check(BrowserActionKind.READ_ONLY_VIEW, "https://example.com")

        self.assertIn(BrowserGovernanceFlag.READ_ONLY_BROWSER_METADATA, check.flags)
        self.assertFalse(check.browser_opened)
        self.assertFalse(check.page_fetched)
        self.assert_all_authority_false(check)

    def test_url_review_does_not_fetch_url(self):
        check = self.check(BrowserActionKind.URL_REVIEW, "https://example.com")

        self.assertEqual(BrowserGovernanceStatus.READ_ONLY_BROWSER_REVIEW_REQUIRED, check.status)
        self.assertFalse(check.page_fetched)
        self.assertFalse(check.page_read)
        self.assert_all_authority_false(check)

    def test_screenshot_request_is_review_required_or_not_yet_governed(self):
        check = self.check(BrowserActionKind.SCREENSHOT_REQUEST, "https://example.com")

        self.assertIn(check.status, {BrowserGovernanceStatus.NOT_YET_GOVERNED, BrowserGovernanceStatus.BROWSER_REVIEW_REQUIRED})
        self.assertFalse(check.screenshot_taken)
        self.assert_all_authority_false(check)

    def test_active_browser_actions_are_blocked_or_not_yet_governed(self):
        cases = (
            (BrowserActionKind.CLICK, BrowserGovernanceFlag.ACTIVE_BROWSER_ACTION_BLOCKED),
            (BrowserActionKind.TYPE, BrowserGovernanceFlag.ACTIVE_BROWSER_ACTION_BLOCKED),
            (BrowserActionKind.SCROLL, BrowserGovernanceFlag.ACTIVE_BROWSER_ACTION_BLOCKED),
        )
        for action_kind, expected_flag in cases:
            with self.subTest(action_kind=action_kind):
                check = self.check(action_kind, "https://example.com")

                self.assertIn(check.status, {BrowserGovernanceStatus.BLOCKED_ACTIVE_BROWSER_ACTION, BrowserGovernanceStatus.NOT_YET_GOVERNED})
                self.assertIn(expected_flag, check.flags)
                self.assert_all_authority_false(check)

    def test_form_download_upload_login_cookie_session_actions_are_blocked(self):
        cases = (
            (BrowserActionKind.FORM_SUBMIT, BrowserGovernanceStatus.BLOCKED_FORM_SUBMISSION, BrowserGovernanceFlag.FORM_SUBMIT_BLOCKED),
            (BrowserActionKind.DOWNLOAD, BrowserGovernanceStatus.BLOCKED_DOWNLOAD_OR_UPLOAD, BrowserGovernanceFlag.DOWNLOAD_BLOCKED),
            (BrowserActionKind.UPLOAD, BrowserGovernanceStatus.BLOCKED_DOWNLOAD_OR_UPLOAD, BrowserGovernanceFlag.UPLOAD_BLOCKED),
            (BrowserActionKind.LOGIN, BrowserGovernanceStatus.BLOCKED_LOGIN_OR_CREDENTIAL_RISK, BrowserGovernanceFlag.LOGIN_BLOCKED),
            (BrowserActionKind.COOKIE_ACCESS, BrowserGovernanceStatus.BLOCKED_COOKIE_OR_SESSION_RISK, BrowserGovernanceFlag.COOKIE_BLOCKED),
            (BrowserActionKind.SESSION_ACCESS, BrowserGovernanceStatus.BLOCKED_COOKIE_OR_SESSION_RISK, BrowserGovernanceFlag.SESSION_BLOCKED),
        )
        for action_kind, expected_status, expected_flag in cases:
            with self.subTest(action_kind=action_kind):
                check = self.check(action_kind, "https://example.com")

                self.assertEqual(expected_status, check.status)
                self.assertIn(expected_flag, check.flags)
                self.assert_all_authority_false(check)

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
            "http://localhost/admin",
            "http://127.0.0.1:8000/private",
            "https://example.com/login",
            "https://example.com/oauth",
            "https://example.com/checkout",
            "https://example.com/admin/delete",
            "https://example.com/download?token=secret",
        )
        for target_url in unsafe_urls:
            with self.subTest(target_url=target_url):
                check = self.check(BrowserActionKind.READ_ONLY_VIEW, target_url)

                self.assertTrue(
                    BrowserGovernanceFlag.UNSAFE_URL in check.flags
                    or BrowserGovernanceFlag.SECRET_OR_TOKEN_PATTERN in check.flags
                    or BrowserGovernanceFlag.SUSPICIOUS_URL in check.flags
                )
                self.assertTrue(check.human_review_required)
                self.assert_all_authority_false(check)

    def test_authority_claiming_metadata_is_flagged(self):
        authority_terms = (
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "browser_opened",
            "browser_action_performed",
            "page_fetched",
            "page_read",
            "screenshot_taken",
            "click_performed",
            "typing_performed",
            "form_submitted",
            "download_performed",
            "upload_performed",
            "cookie_accessed",
            "session_accessed",
            "credential_used",
            "network_called",
        )
        for term in authority_terms:
            with self.subTest(term=term):
                check = self.check(metadata={term: True})

                self.assertTrue(
                    BrowserGovernanceFlag.SECRET_OR_TOKEN_PATTERN in check.flags
                    or BrowserGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM in check.flags
                )
                self.assertTrue(check.human_review_required)
                self.assert_all_authority_false(check)

    def test_untrusted_provider_output_forces_human_review(self):
        check = self.check(source_trust=BrowserSourceTrust.UNTRUSTED_PROVIDER_OUTPUT)

        self.assertIn(BrowserGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED, check.flags)
        self.assertIn(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED, check.flags)
        self.assertTrue(check.human_review_required)
        self.assert_all_authority_false(check)

    def test_input_claims_cannot_enable_authority_fields(self):
        check = self.check(authority_claims={"can_access_network": True, "browser_opened": True, "approval_granted": True})
        replaced = replace(
            check,
            browser_opened=True,
            browser_action_performed=True,
            page_fetched=True,
            page_read=True,
            screenshot_taken=True,
            click_performed=True,
            typing_performed=True,
            scroll_performed=True,
            form_submitted=True,
            download_performed=True,
            upload_performed=True,
            cookie_accessed=True,
            session_accessed=True,
            credential_used=True,
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

        self.assertIn(BrowserGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM, check.flags)
        self.assert_all_authority_false(check)
        self.assert_all_authority_false(replaced)

    def test_inconsistent_source_hash_metadata_is_detected(self):
        cases = (
            self.request(source_action_proposal_id="action-proposal-example", source_action_proposal_hash=None),
            self.request(source_tool_call_preview_id="tool-call-preview-example", source_tool_call_preview_hash="not-a-hash"),
            self.request(source_intent_route_id="intent-route-example", source_intent_route_hash="not-a-hash"),
            self.request(source_policy_check_id="local-policy-check-example", source_policy_check_hash="not-a-hash"),
            self.request(source_test_runner_control_id="test-runner-control-example", source_test_runner_control_hash=None),
            self.request(source_download_governance_id="download-governance-example", source_download_governance_hash=None),
            self.request(source_statement_governance_id="statement-governance-example", source_statement_governance_hash="not-a-hash"),
        )
        for request in cases:
            with self.subTest(request=request):
                check = build_browser_governance_check(request)

                self.assertEqual(BrowserGovernanceStatus.INCONSISTENT_METADATA, check.status)
                self.assertIn(BrowserGovernanceFlag.INCONSISTENT_HASH_METADATA, check.flags)
                self.assert_all_authority_false(check)

    def test_source_hash_metadata_is_inert(self):
        check = self.check(
            source_statement_governance_id="statement-governance-example",
            source_statement_governance_hash=HASH,
            source_download_governance_id="download-governance-example",
            source_download_governance_hash=HASH,
        )

        self.assertEqual(HASH, check.source_statement_governance_hash)
        self.assertEqual(HASH, check.source_download_governance_hash)
        self.assertIn(BrowserGovernanceFlag.STATEMENT_GOVERNANCE_METADATA_ONLY, check.flags)
        self.assertIn(BrowserGovernanceFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY, check.flags)
        self.assert_all_authority_false(check)

    def test_unknown_action_kind_is_not_yet_governed(self):
        check = self.check("made_up_action", "https://example.com")

        self.assertEqual(BrowserActionKind.UNKNOWN, check.action_kind)
        self.assertEqual(BrowserGovernanceStatus.NOT_YET_GOVERNED, check.status)
        self.assertTrue(check.human_review_required)
        self.assert_all_authority_false(check)

    def test_check_is_frozen(self):
        check = self.check()

        with self.assertRaises(FrozenInstanceError):
            check.status = BrowserGovernanceStatus.BROWSER_GOVERNANCE_CHECK_READY

    def test_no_runtime_creation_routing_policy_or_dispatch_methods(self):
        check = self.check()
        forbidden_methods = (
            "execute",
            "run",
            "call",
            "invoke",
            "dispatch",
            "approve",
            "allow",
            "deny",
            "open_browser",
            "fetch_url",
            "read_page",
            "screenshot",
            "click",
            "type",
            "submit",
            "download",
            "upload",
            "create_action_proposal",
            "build_action_proposal",
            "create_preview",
            "build_tool_call_preview",
            "route_intent",
            "evaluate_local_policy",
            "build_test_runner_control_preview",
            "build_download_governance_preview",
            "build_statement_governance_preview",
            "create_approval",
            "register_tool",
        )

        for method_name in forbidden_methods:
            with self.subTest(method_name=method_name):
                self.assertFalse(callable(getattr(check, method_name, None)))

    def test_no_filesystem_reads_or_writes_occur(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            _check = self.check(BrowserActionKind.READ_ONLY_VIEW, f"https://example.com/{workspace}/page")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_import_has_no_side_effect_filesystem_writes(self):
        with TemporaryDirectory() as workspace:
            before = list(Path(workspace).rglob("*"))
            __import__("runtime.schemas.browser_governance")
            after = list(Path(workspace).rglob("*"))

        self.assertEqual(before, after)

    def test_static_forbidden_imports_and_capabilities(self):
        source = BROWSER_GOVERNANCE.read_text(encoding="utf-8")
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
            "runtime.schemas.download_manager_governance",
            "runtime.schemas.statement_manager_governance",
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
            "dispatch(",
            "invoke(",
            "execute(",
            "approve(",
            "allow(",
            "deny(",
            "open_browser(",
            "fetch_url(",
            "read_page(",
            "screenshot(",
            "click(",
            "type(",
            "submit(",
            "download(",
            "upload(",
            "build_action_proposal(",
            "build_tool_call_preview(",
            "route_intent(",
            "evaluate_local_policy(",
            "build_test_runner_control_preview(",
            "build_download_governance_preview(",
            "build_statement_governance_preview(",
            "create_action_proposal",
            "create_preview",
            "create_approval",
            "approvaldecision",
        )
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

    def request(self, action_kind=BrowserActionKind.READ_ONLY_VIEW, target_url="https://example.com", **kwargs):
        base = {
            "action_kind": action_kind,
            "target_url": target_url,
        }
        base.update(kwargs)
        return BrowserGovernanceRequest(**base)

    def check(self, action_kind=BrowserActionKind.READ_ONLY_VIEW, target_url="https://example.com", **kwargs):
        return build_browser_governance_check(self.request(action_kind, target_url, **kwargs))

    def assert_all_authority_false(self, check):
        self.assertFalse(check.browser_opened)
        self.assertFalse(check.browser_action_performed)
        self.assertFalse(check.page_fetched)
        self.assertFalse(check.page_read)
        self.assertFalse(check.screenshot_taken)
        self.assertFalse(check.click_performed)
        self.assertFalse(check.typing_performed)
        self.assertFalse(check.scroll_performed)
        self.assertFalse(check.form_submitted)
        self.assertFalse(check.download_performed)
        self.assertFalse(check.upload_performed)
        self.assertFalse(check.cookie_accessed)
        self.assertFalse(check.session_accessed)
        self.assertFalse(check.credential_used)
        self.assertFalse(check.network_called)
        self.assertFalse(check.provider_called)
        self.assertFalse(check.approval_created)
        self.assertFalse(check.gate_changed)
        self.assertFalse(check.tool_called)
        self.assertFalse(check.can_call_tool)
        self.assertFalse(check.can_execute)
        self.assertFalse(check.can_write)
        self.assertFalse(check.can_commit)
        self.assertFalse(check.can_change_approval_gate)
        self.assertFalse(check.can_change_policy)
        self.assertFalse(check.can_access_network)
        self.assertFalse(check.can_read_env)
        self.assertFalse(check.can_load_api_key)


if __name__ == "__main__":
    unittest.main()
