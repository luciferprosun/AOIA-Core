from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.browser_ops.browser_automation_preview import (
    BROWSER_AUTOMATION_PREVIEW_BLOCKED,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_EXECUTABLE_EVIDENCE,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_NON_JSON_SERIALIZABLE,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_STALE_EVIDENCE,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNKNOWN_FIELD,
    BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNSUPPORTED_ACTION,
    BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY,
    BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY,
    BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION,
    BROWSER_AUTOMATION_RISK_CLICK,
    BROWSER_AUTOMATION_RISK_FORM_SUBMIT,
    BROWSER_AUTOMATION_RISK_NAVIGATION,
    BROWSER_AUTOMATION_RISK_TYPE,
    BrowserAutomationPreviewRequest,
    canonical_browser_automation_preview_json,
    compute_browser_automation_request_hash,
    create_browser_automation_preview,
    create_browser_automation_preview_step,
)
from runtime.browser_ops.controlled_browser_read import (
    compute_browser_read_source_hash,
    create_browser_read_human_barrier,
    create_controlled_browser_read_context,
    create_controlled_browser_read_request,
    execute_controlled_browser_read,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "browser_ops" / "browser_automation_preview.py"


class BrowserAutomationPreview1ATests(unittest.TestCase):
    def test_valid_click_type_and_submit_plan_creates_metadata_only_preview(self):
        read_result = self.browser_read_snapshot()
        steps = (
            create_browser_automation_preview_step(
                action="click",
                target="#edit",
                description="Propose selecting the edit control.",
            ),
            create_browser_automation_preview_step(
                action="type",
                target="#title",
                value="Reviewed title",
                description="Propose entering reviewed text.",
            ),
            create_browser_automation_preview_step(
                action="submit",
                target="#save-form",
                description="Propose submitting the local form later.",
            ),
        )

        result = create_browser_automation_preview(
            self.request(read_result, steps=steps),
            now_tick=12,
        )

        self.assertEqual(BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY, result.status)
        self.assertEqual((BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY,), result.reason_codes)
        self.assertEqual(
            (BROWSER_AUTOMATION_RISK_CLICK, BROWSER_AUTOMATION_RISK_FORM_SUBMIT, BROWSER_AUTOMATION_RISK_TYPE),
            result.risk_codes,
        )
        self.assertEqual(tuple(step.step_hash for step in steps), result.step_hashes)
        self.assert_metadata_only(result.to_dict())

    def test_navigation_download_upload_and_mutation_actions_are_preview_risks_only(self):
        read_result = self.browser_read_snapshot()
        steps = (
            create_browser_automation_preview_step(action="navigate", target="/local/review", description="Propose local path navigation."),
            create_browser_automation_preview_step(action="follow_link", target="#next", description="Propose following an in-page link."),
            create_browser_automation_preview_step(action="download", target="#report", description="Propose future download action."),
            create_browser_automation_preview_step(action="upload", target="#file", value="fixture.pdf", description="Propose future upload action."),
            create_browser_automation_preview_step(action="set_cookie", target="session_mode", value="review", description="Propose future cookie mutation."),
            create_browser_automation_preview_step(action="set_storage", target="review.state", value="draft", description="Propose future storage mutation."),
        )

        result = create_browser_automation_preview(self.request(read_result, steps=steps), now_tick=12)

        self.assertEqual(BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY, result.status)
        self.assertIn("BROWSER_AUTOMATION_RISK_DOWNLOAD", result.risk_codes)
        self.assertIn("BROWSER_AUTOMATION_RISK_UPLOAD", result.risk_codes)
        self.assertIn("BROWSER_AUTOMATION_RISK_COOKIE_MUTATION", result.risk_codes)
        self.assertIn("BROWSER_AUTOMATION_RISK_STORAGE_MUTATION", result.risk_codes)
        self.assert_metadata_only(result.to_dict())

    def test_preview_hash_request_hash_and_canonical_json_are_deterministic(self):
        read_result = self.browser_read_snapshot()
        request = self.request(read_result)

        first = create_browser_automation_preview(request, now_tick=12)
        second = create_browser_automation_preview(request, now_tick=12)
        changed = create_browser_automation_preview(
            self.request(
                read_result,
                steps=(
                    create_browser_automation_preview_step(
                        action="wait_for_selector",
                        target="#ready",
                        description="Propose waiting for a reviewed selector.",
                    ),
                ),
            ),
            now_tick=12,
        )

        self.assertEqual(first.preview_hash, second.preview_hash)
        self.assertNotEqual(first.preview_hash, changed.preview_hash)
        self.assertEqual(compute_browser_automation_request_hash(request), first.request_hash)
        self.assertEqual(
            canonical_browser_automation_preview_json({"b": 1, "a": ("x",)}),
            canonical_browser_automation_preview_json({"a": ["x"], "b": 1}),
        )

    def test_missing_malformed_stale_unknown_and_non_json_evidence_fail_closed(self):
        read_result = self.browser_read_snapshot()
        base = self.request(read_result)
        cases = (
            ({}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE),
            ({**base, "expires_at_tick": 5}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_STALE_EVIDENCE),
            ({**base, "unknown": "field"}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNKNOWN_FIELD),
            ({**base, "steps": []}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE),
            ({**base, "metadata": {"bad": object()}}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_NON_JSON_SERIALIZABLE),
        )
        for request, reason in cases:
            with self.subTest(reason=reason):
                result = create_browser_automation_preview(request, now_tick=12)

                self.assertEqual(BROWSER_AUTOMATION_PREVIEW_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_hash_mismatch_step_tamper_and_remote_targets_fail_closed(self):
        read_result = self.browser_read_snapshot()
        step = create_browser_automation_preview_step(
            action="click",
            target="#safe",
            description="Propose click.",
        )
        tampered_step = {**step.to_dict(), "target": "#changed"}
        cases = (
            ({**self.request(read_result), "request_hash": "0" * 64}, BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH),
            (self.request(read_result, steps=(tampered_step,)), BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH),
            (
                self.request(
                    read_result,
                    steps=(create_browser_automation_preview_step(action="navigate", target="https://example.invalid", description="Remote."),),
                ),
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET,
            ),
            (
                self.request(
                    read_result,
                    steps=(create_browser_automation_preview_step(action="follow_link", target="javascript:alert(1)", description="JS URL."),),
                ),
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET,
            ),
        )
        for request, reason in cases:
            with self.subTest(reason=reason):
                result = create_browser_automation_preview(request, now_tick=12)

                self.assertEqual(BROWSER_AUTOMATION_PREVIEW_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_unsupported_executable_and_authority_claims_fail_closed(self):
        read_result = self.browser_read_snapshot()
        cases = (
            (
                self.request(
                    read_result,
                    steps=(create_browser_automation_preview_step(action="execute_script", target="#page", description="Run script."),),
                ),
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNSUPPORTED_ACTION,
            ),
            (
                self.request(
                    read_result,
                    steps=(create_browser_automation_preview_step(action="click", target="#page", description="Use selenium webdriver."),),
                ),
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_EXECUTABLE_EVIDENCE,
            ),
            (
                {**self.request(read_result), "metadata": {"approved": True}},
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
            ),
            (
                {**self.request(read_result), "reason": "approved safe to click"},
                BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM,
            ),
        )
        for request, reason in cases:
            with self.subTest(reason=reason):
                result = create_browser_automation_preview(request, now_tick=12)

                self.assertEqual(BROWSER_AUTOMATION_PREVIEW_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_preview_result_cannot_satisfy_gate_or_future_authority_even_if_replaced(self):
        read_result = self.browser_read_snapshot()
        result = create_browser_automation_preview(self.request(read_result), now_tick=12)
        forced = replace(
            result,
            browser_opened=True,
            browser_action_performed=True,
            network_called=True,
            javascript_executed=True,
            link_followed=True,
            form_submitted=True,
            download_performed=True,
            upload_performed=True,
            cookie_mutated=True,
            storage_mutated=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            can_browse=True,
            can_click=True,
            can_download=True,
            can_execute=True,
            future_browser_action_authorized=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in ("execute", "dispatch", "click", "type", "submit", "navigate", "download", "open_browser"):
            self.assertFalse(hasattr(result, method_name))

    def test_module_static_surface_is_preview_only(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8").casefold()
        scan = scan_module(RUNTIME_FILE)

        for forbidden_import in (
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "aiohttp",
            "webbrowser",
            "selenium",
            "playwright",
            "openai",
            "anthropic",
            "runtime.providers.gateway",
            "runtime.provider_live_adapter",
            "runtime.control_write",
            "runtime.git_ops",
            "runtime.package_ops.controlled_package_install",
        ):
            self.assertNotIn(forbidden_import, scan.imports)
        for forbidden_call in (
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "eval",
            "exec",
            "__import__",
            "importlib.import_module",
        ):
            self.assertNotIn(forbidden_call, scan.calls)
        for forbidden_text in (
            "shell=true",
            "os.environ",
            "getenv",
            "api_key",
            "step 46",
            "step 47",
        ):
            self.assertNotIn(forbidden_text, source)

    def browser_read_snapshot(self):
        html = "<html><title>Example</title><body><a href=\"#edit\">Edit</a></body></html>"
        source_hash = compute_browser_read_source_hash(html)
        request = create_controlled_browser_read_request(
            source_kind="inline_html",
            source_locator=html,
            expected_source_hash=source_hash,
            reason="Create inert browser read evidence.",
            requested_by="tester",
            requested_at=10,
            expires_at=20,
            allowed_extractors=("title", "text_hash", "links"),
        )
        context = create_controlled_browser_read_context(
            current_tick=12,
            sandbox_root="/tmp/browser-preview",
            offline_mode=True,
            network_disabled=True,
            browser_launch_disabled=True,
            javascript_disabled=True,
            storage_mutation_disabled=True,
        )
        barrier = create_browser_read_human_barrier(
            request_hash=request.request_hash,
            context_hash=context.context_hash,
            source_hash=source_hash,
            source_kind="inline_html",
            approved_extractors=("title", "text_hash", "links"),
            approved_by="tester",
            approval_reason="Create inert read snapshot.",
            approved_at=10,
            expires_at=20,
        )
        result = execute_controlled_browser_read(request=request, context=context, human_barrier=barrier)
        self.assertTrue(result.snapshot_created)
        return result

    def request(self, read_result, *, steps=None):
        if steps is None:
            steps = (
                create_browser_automation_preview_step(
                    action="click",
                    target="#edit",
                    description="Propose selecting the edit control.",
                ),
            )
        request = {
            "schema_version": BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION,
            "preview_id": "browser-preview",
            "browser_read_result_hash": read_result.result_hash,
            "source_hash": read_result.source_hash,
            "reason": "Preview browser automation as inert metadata.",
            "requested_by": "tester",
            "created_at_tick": 10,
            "expires_at_tick": 20,
            "steps": tuple(step.to_dict() if hasattr(step, "to_dict") else step for step in steps),
            "metadata": {"source": "unit-test"},
        }
        request["request_hash"] = compute_browser_automation_request_hash(request)
        return request

    def assert_metadata_only(self, data):
        for field in (
            "browser_opened",
            "browser_action_performed",
            "network_called",
            "remote_resource_loaded",
            "javascript_executed",
            "link_followed",
            "navigation_performed",
            "form_submitted",
            "download_performed",
            "upload_performed",
            "cookie_mutated",
            "storage_mutated",
            "file_written",
            "provider_called",
            "git_action_performed",
            "package_installed",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_browse",
            "can_click",
            "can_download",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            self.assertIs(data[field], False)
        self.assertIs(data["human_review_required"], True)
        self.assertIs(data["future_governance_required"], True)


def scan_module(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Call):
            calls.add(call_name(node.func))
    return type("Scan", (), {"imports": tuple(sorted(imports)), "calls": tuple(sorted(calls))})()


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


if __name__ == "__main__":
    unittest.main()
