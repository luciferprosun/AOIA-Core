from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.browser_ops.browser_automation_governance import evaluate_browser_automation_governance
from runtime.browser_ops.browser_automation_preview import (
    BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION,
    compute_browser_automation_request_hash,
    create_browser_automation_preview,
    create_browser_automation_preview_step,
)
from runtime.browser_ops.controlled_browser_automation import (
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_ACTION,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_AUTHORITY_CLAIM,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_HASH_MISMATCH,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_SCOPE_MISMATCH,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_EFFECT_EVIDENCE,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MISSING_HUMAN_BARRIER,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_OFFLINE_CONTEXT,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_READ_NOT_READY,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND,
    CONTROLLED_BROWSER_AUTOMATION_BLOCKED_STALE_EVIDENCE,
    CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED,
    CONTROLLED_BROWSER_AUTOMATION_SIMULATED,
    BrowserAutomationHumanBarrier,
    canonical_controlled_browser_automation_json,
    create_browser_automation_human_barrier,
    create_controlled_browser_automation_context,
    execute_controlled_browser_automation,
)
from runtime.browser_ops.controlled_browser_read import (
    compute_browser_read_source_hash,
    create_browser_read_human_barrier,
    create_controlled_browser_read_context,
    create_controlled_browser_read_request,
    execute_controlled_browser_read,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "browser_ops" / "controlled_browser_automation.py"


class ControlledBrowserAutomation1ATests(unittest.TestCase):
    def test_valid_local_snapshot_actions_are_simulated_in_memory_only(self):
        evidence = self.evidence()

        result = execute_controlled_browser_automation(**evidence)

        self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_SIMULATED, result.status)
        self.assertEqual((CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED,), result.reason_codes)
        self.assertTrue(result.simulation_performed)
        self.assertEqual(("#edit",), result.selected_link_targets)
        self.assertEqual((("title", "Reviewed title"),), result.typed_fields)
        self.assertEqual((("mode", "review"),), result.selected_options)
        self.assertIn(("#ready", True), result.selector_checks)
        self.assertNotEqual(result.before_state_hash, result.after_state_hash)
        self.assertEqual(evidence["browser_read_result"].result_hash, result.browser_read_result_hash)
        self.assertEqual(evidence["preview_result"].preview_hash, result.preview_hash)
        self.assertEqual(evidence["governance_result"].governance_hash, result.governance_hash)
        self.assert_metadata_only(result.to_dict())

    def test_hashes_and_canonical_json_are_deterministic(self):
        first = execute_controlled_browser_automation(**self.evidence())
        second = execute_controlled_browser_automation(**self.evidence())

        self.assertEqual(first.result_hash, second.result_hash)
        self.assertEqual(first.before_state_hash, second.before_state_hash)
        self.assertEqual(first.after_state_hash, second.after_state_hash)
        self.assertEqual(
            canonical_controlled_browser_automation_json({"b": 1, "a": ("x",)}),
            canonical_controlled_browser_automation_json({"a": ["x"], "b": 1}),
        )

    def test_missing_hash_mismatch_stale_and_wrong_barrier_fail_closed(self):
        evidence = self.evidence()
        bad_barrier = evidence["human_barrier"].to_dict()
        bad_barrier["barrier_hash"] = "0" * 64
        cases = (
            ({**evidence, "human_barrier": None}, CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MISSING_HUMAN_BARRIER),
            ({**evidence, "html_snapshot": evidence["html_snapshot"] + "<p>Changed</p>"}, CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH),
            ({**evidence, "human_barrier": bad_barrier}, CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_HASH_MISMATCH),
            (
                {
                    **evidence,
                    "human_barrier": create_browser_automation_human_barrier(
                        browser_read_result_hash=evidence["browser_read_result"].result_hash,
                        preview_hash=evidence["preview_result"].preview_hash,
                        request_hash=evidence["preview_request"]["request_hash"],
                        governance_hash=evidence["governance_result"].governance_hash,
                        context_hash=evidence["context"].context_hash,
                        source_hash=evidence["browser_read_result"].source_hash,
                        approved_step_hashes=evidence["preview_result"].step_hashes,
                        approved_actions=("click",),
                        approved_by="tester",
                        approval_reason="Wrong scope.",
                        approved_at=10,
                        expires_at=20,
                    ),
                },
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_SCOPE_MISMATCH,
            ),
            (
                {
                    **evidence,
                    "human_barrier": create_browser_automation_human_barrier(
                        browser_read_result_hash=evidence["browser_read_result"].result_hash,
                        preview_hash=evidence["preview_result"].preview_hash,
                        request_hash=evidence["preview_request"]["request_hash"],
                        governance_hash=evidence["governance_result"].governance_hash,
                        context_hash=evidence["context"].context_hash,
                        source_hash=evidence["browser_read_result"].source_hash,
                        approved_step_hashes=evidence["preview_result"].step_hashes,
                        approved_actions=evidence["governance_result"].action_labels,
                        approved_by="tester",
                        approval_reason="Expired.",
                        approved_at=1,
                        expires_at=5,
                    ),
                },
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_STALE_EVIDENCE,
            ),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = execute_controlled_browser_automation(**altered)

                self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_read_preview_governance_and_context_are_required(self):
        evidence = self.evidence()
        cases = (
            (
                {**evidence, "browser_read_result": {**evidence["browser_read_result"].to_dict(), "status": "BLOCKED"}},
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_READ_NOT_READY,
            ),
            (
                {**evidence, "preview_result": {**evidence["preview_result"].to_dict(), "status": "BLOCKED"}},
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY,
            ),
            (
                {**evidence, "governance_result": {**evidence["governance_result"].to_dict(), "status": "BLOCKED"}},
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY,
            ),
            (
                {
                    **evidence,
                    "context": create_controlled_browser_automation_context(
                        current_tick=12,
                        sandbox_root="/tmp/browser-automation",
                        network_disabled=False,
                    ),
                },
                CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_OFFLINE_CONTEXT,
            ),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = execute_controlled_browser_automation(**altered)

                self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_blocked_actions_and_missing_selectors_fail_closed(self):
        blocked = self.evidence(
            steps=(
                create_browser_automation_preview_step(action="navigate", target="/local", description="Try local navigation."),
            )
        )
        missing = self.evidence(
            steps=(
                create_browser_automation_preview_step(action="wait_for_selector", target="#missing", description="Wait missing."),
            )
        )

        blocked_result = execute_controlled_browser_automation(**blocked)
        missing_result = execute_controlled_browser_automation(**missing)

        self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_BLOCKED, blocked_result.status)
        self.assertIn(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_ACTION, blocked_result.reason_codes)
        self.assertIn("navigate", blocked_result.blocked_actions)
        self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_BLOCKED, missing_result.status)
        self.assertIn(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND, missing_result.reason_codes)
        self.assert_metadata_only(blocked_result.to_dict())
        self.assert_metadata_only(missing_result.to_dict())

    def test_authority_claims_and_effect_evidence_fail_closed(self):
        evidence = self.evidence()
        cases = (
            ({**evidence, "preview_result": {**evidence["preview_result"].to_dict(), "can_execute": True}}, CONTROLLED_BROWSER_AUTOMATION_BLOCKED_AUTHORITY_CLAIM),
            ({**evidence, "governance_result": {**evidence["governance_result"].to_dict(), "browser_action_performed": True}}, CONTROLLED_BROWSER_AUTOMATION_BLOCKED_EFFECT_EVIDENCE),
        )
        for altered, reason in cases:
            with self.subTest(reason=reason):
                result = execute_controlled_browser_automation(**altered)

                self.assertEqual(CONTROLLED_BROWSER_AUTOMATION_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_result_cannot_satisfy_gate_or_grant_future_authority_even_if_replaced(self):
        result = execute_controlled_browser_automation(**self.evidence())
        forced = replace(
            result,
            browser_opened=True,
            browser_action_performed=True,
            network_called=True,
            javascript_executed=True,
            link_followed=True,
            navigation_performed=True,
            form_submitted=True,
            download_performed=True,
            upload_performed=True,
            cookie_mutated=True,
            storage_mutated=True,
            file_written=True,
            gate_satisfied=True,
            human_barrier_satisfied=True,
            can_browse=True,
            can_click=True,
            can_type=True,
            can_submit=True,
            can_navigate=True,
            can_download=True,
            can_upload=True,
            can_execute=True,
            future_browser_action_authorized=True,
        )

        self.assert_metadata_only(forced.to_dict())
        for method_name in ("dispatch", "click", "type", "submit", "navigate", "download", "open_browser"):
            self.assertFalse(hasattr(result, method_name))

    def test_human_barrier_rejects_authority_relaxation(self):
        evidence = self.evidence()
        data = evidence["human_barrier"].to_dict()

        barrier = BrowserAutomationHumanBarrier(**{**data, "can_execute": True, "future_browser_action_authorized": True})

        self.assertIs(barrier.can_execute, False)
        self.assertIs(barrier.future_browser_action_authorized, False)
        self.assertIs(barrier.to_dict()["can_execute"], False)
        self.assertIs(barrier.to_dict()["future_browser_action_authorized"], False)

    def test_module_static_surface_is_local_offline_only(self):
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
        for forbidden_text in ("shell=true", "os.environ", "getenv", "api_key", "step 48"):
            self.assertNotIn(forbidden_text, source)

    def evidence(self, *, steps=None):
        html = (
            "<html><title>Example</title><body>"
            '<a id="edit" href="#edit">Edit</a>'
            '<div id="title" data-aoia-control="field" data-aoia-name="title">Title</div>'
            '<div id="mode" data-aoia-control="select" data-aoia-name="mode" data-aoia-options="draft,review">Mode</div>'
            '<div id="ready">Ready</div>'
            "</body></html>"
        )
        read_result = self.browser_read_snapshot(html)
        if steps is None:
            steps = (
                create_browser_automation_preview_step(action="click", target="#edit", description="Select link metadata."),
                create_browser_automation_preview_step(action="type", target="#title", value="Reviewed title", description="Type inert value."),
                create_browser_automation_preview_step(action="type", target="#mode", value="review", description="Select inert option."),
                create_browser_automation_preview_step(action="wait_for_selector", target="#ready", description="Check readiness."),
                create_browser_automation_preview_step(action="read_snapshot", target="document", description="Read inert snapshot."),
            )
        request = self.request(read_result, steps=steps)
        preview = create_browser_automation_preview(request, now_tick=12)
        governance = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)
        context = create_controlled_browser_automation_context(
            current_tick=12,
            sandbox_root="/tmp/browser-automation",
        )
        barrier = create_browser_automation_human_barrier(
            browser_read_result_hash=read_result.result_hash,
            preview_hash=preview.preview_hash,
            request_hash=request["request_hash"],
            governance_hash=governance.governance_hash,
            context_hash=context.context_hash,
            source_hash=read_result.source_hash,
            approved_step_hashes=preview.step_hashes,
            approved_actions=governance.action_labels,
            approved_by="tester",
            approval_reason="Allow inert local simulation only.",
            approved_at=10,
            expires_at=20,
        )
        return {
            "browser_read_result": read_result,
            "preview_result": preview,
            "preview_request": request,
            "governance_result": governance,
            "context": context,
            "human_barrier": barrier,
            "html_snapshot": html,
        }

    def browser_read_snapshot(self, html):
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
            sandbox_root="/tmp/browser-automation",
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

    def request(self, read_result, *, steps):
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
            "can_type",
            "can_submit",
            "can_navigate",
            "can_download",
            "can_upload",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            self.assertIs(data[field], False)


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
