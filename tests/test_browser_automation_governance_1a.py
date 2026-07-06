from __future__ import annotations

import ast
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.browser_ops.browser_automation_governance import (
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EFFECT_EVIDENCE,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_NON_JSON_SERIALIZABLE,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_STALE_EVIDENCE,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD,
    BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_RISK,
    BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY,
    BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY,
    BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED,
    BROWSER_AUTOMATION_GOVERNANCE_RISK_MEDIUM,
    BrowserAutomationGovernancePolicy,
    canonical_browser_automation_governance_json,
    create_browser_automation_governance_policy,
    evaluate_browser_automation_governance,
)
from runtime.browser_ops.browser_automation_preview import (
    BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION,
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
RUNTIME_FILE = REPO_ROOT / "runtime" / "browser_ops" / "browser_automation_governance.py"


class BrowserAutomationGovernance1ATests(unittest.TestCase):
    def test_valid_click_type_and_wait_preview_creates_future_review_metadata_only_governance(self):
        request, preview = self.preview_for_steps(
            (
                create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),
                create_browser_automation_preview_step(action="type", target="#title", value="Reviewed", description="Propose type."),
                create_browser_automation_preview_step(action="wait_for_selector", target="#ready", description="Propose wait."),
            )
        )

        result = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)

        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY, result.status)
        self.assertEqual((BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY,), result.reason_codes)
        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_RISK_MEDIUM, result.risk_tier)
        self.assertEqual(preview.preview_hash, result.preview_hash)
        self.assertEqual(preview.request_hash, result.request_hash)
        self.assertEqual(preview.step_hashes, result.step_hashes)
        self.assertEqual(("click", "type", "wait_for_selector"), result.allowed_for_future_review_actions)
        self.assertIn("exact_preview_hash", result.required_future_evidence)
        self.assertIn("explicit_hash_bound_human_barrier", result.required_future_evidence)
        self.assert_metadata_only(result.to_dict())

    def test_hash_governance_policy_and_canonical_json_are_deterministic(self):
        request, preview = self.preview_for_steps(
            (create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),)
        )

        first = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)
        second = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)
        policy = create_browser_automation_governance_policy()
        policy_again = create_browser_automation_governance_policy()

        self.assertEqual(first.governance_hash, second.governance_hash)
        self.assertEqual(first.policy_hash, policy.policy_hash)
        self.assertEqual(policy.policy_hash, policy_again.policy_hash)
        self.assertEqual(
            canonical_browser_automation_governance_json({"b": 1, "a": ("x",)}),
            canonical_browser_automation_governance_json({"a": ["x"], "b": 1}),
        )

    def test_policy_blocked_high_risk_actions_fail_closed_as_metadata(self):
        request, preview = self.preview_for_steps(
            (
                create_browser_automation_preview_step(action="submit", target="#save-form", description="Propose submit."),
                create_browser_automation_preview_step(action="navigate", target="/local/path", description="Propose local navigation."),
                create_browser_automation_preview_step(action="download", target="#report", description="Propose download."),
                create_browser_automation_preview_step(action="upload", target="#file", value="report.pdf", description="Propose upload."),
                create_browser_automation_preview_step(action="set_cookie", target="mode", value="review", description="Propose cookie."),
                create_browser_automation_preview_step(action="set_storage", target="review.state", value="draft", description="Propose storage."),
            )
        )

        result = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)

        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
        self.assertIn(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION, result.reason_codes)
        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED, result.risk_tier)
        self.assertEqual(("download", "navigate", "set_cookie", "set_storage", "submit", "upload"), result.blocked_actions)
        self.assert_metadata_only(result.to_dict())

    def test_missing_malformed_stale_unknown_and_non_json_evidence_fail_closed(self):
        request, preview = self.preview_for_steps(
            (create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),)
        )
        cases = (
            ({}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE),
            (preview, {**request, "expires_at_tick": 5}, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_STALE_EVIDENCE),
            ({**preview.to_dict(), "unknown": "field"}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD),
            (preview, {**request, "unknown": "field"}, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD),
            (preview, {**request, "metadata": {"bad": object()}}, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_NON_JSON_SERIALIZABLE),
        )
        for preview_evidence, request_evidence, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_browser_automation_governance(
                    preview_result=preview_evidence,
                    preview_request=request_evidence,
                    now_tick=12,
                )

                self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_hash_request_step_source_and_risk_tampering_fail_closed(self):
        request, preview = self.preview_for_steps(
            (create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),)
        )
        tampered_step = dict(request["steps"][0])
        tampered_step["target"] = "#changed"
        tampered_request = {**request, "steps": (tampered_step,)}
        cases = (
            ({**preview.to_dict(), "preview_hash": "0" * 64}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH),
            ({**preview.to_dict(), "request_hash": "0" * 64}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH),
            ({**preview.to_dict(), "source_hash": "0" * 64}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH),
            ({**preview.to_dict(), "risk_codes": ("BROWSER_AUTOMATION_RISK_UNKNOWN",)}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_RISK),
            (preview, tampered_request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH),
        )
        for preview_evidence, request_evidence, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_browser_automation_governance(
                    preview_result=preview_evidence,
                    preview_request=request_evidence,
                    now_tick=12,
                )

                self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_blocked_preview_result_never_becomes_governance_ready(self):
        read_result = self.browser_read_snapshot()
        step = create_browser_automation_preview_step(
            action="navigate",
            target="https://example.invalid",
            description="Remote navigation.",
        )
        request = self.request(read_result, steps=(step,))
        preview = create_browser_automation_preview(request, now_tick=12)

        result = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)

        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
        self.assertIn(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY, result.reason_codes)
        self.assert_metadata_only(result.to_dict())

    def test_authority_effect_and_executable_claims_fail_closed(self):
        request, preview = self.preview_for_steps(
            (create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),)
        )
        cases = (
            ({**preview.to_dict(), "can_execute": True}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM),
            ({**preview.to_dict(), "browser_action_performed": True}, request, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EFFECT_EVIDENCE),
            (preview, {**request, "metadata": {"approved": True}}, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM),
            (preview, {**request, "metadata": {"script": "use selenium webdriver"}}, BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE),
        )
        for preview_evidence, request_evidence, reason in cases:
            with self.subTest(reason=reason):
                result = evaluate_browser_automation_governance(
                    preview_result=preview_evidence,
                    preview_request=request_evidence,
                    now_tick=12,
                )

                self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
                self.assertIn(reason, result.reason_codes)
                self.assert_metadata_only(result.to_dict())

    def test_custom_policy_hash_and_max_steps_are_enforced(self):
        request, preview = self.preview_for_steps(
            (
                create_browser_automation_preview_step(action="click", target="#a", description="Propose click A."),
                create_browser_automation_preview_step(action="type", target="#b", value="b", description="Propose type B."),
            )
        )
        base = create_browser_automation_governance_policy()
        custom = create_browser_automation_governance_policy(max_steps=1)

        result = evaluate_browser_automation_governance(
            preview_result=preview,
            preview_request=request,
            now_tick=12,
            policy=custom,
        )

        self.assertNotEqual(base.policy_hash, custom.policy_hash)
        self.assertEqual(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED, result.status)
        self.assertIn(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION, result.reason_codes)
        self.assertEqual(custom.policy_hash, result.policy_hash)
        self.assert_metadata_only(result.to_dict())

    def test_policy_rejects_invalid_authority_relaxation(self):
        policy = create_browser_automation_governance_policy()
        data = policy.to_dict()

        with self.assertRaises(ValueError):
            BrowserAutomationGovernancePolicy(**{**data, "requires_human_review": False})
        with self.assertRaises(ValueError):
            BrowserAutomationGovernancePolicy(
                **{
                    **data,
                    "allowed_preview_actions": (*data["allowed_preview_actions"], data["blocked_actions"][0]),
                }
            )

    def test_governance_result_cannot_satisfy_gate_or_future_authority_even_if_replaced(self):
        request, preview = self.preview_for_steps(
            (create_browser_automation_preview_step(action="click", target="#edit", description="Propose click."),)
        )
        result = evaluate_browser_automation_governance(preview_result=preview, preview_request=request, now_tick=12)
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
            gate_satisfied=True,
            human_barrier_satisfied=True,
            governance_passed=True,
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
        for method_name in ("execute", "dispatch", "click", "type", "submit", "navigate", "download", "open_browser"):
            self.assertFalse(hasattr(result, method_name))

    def test_module_static_surface_is_governance_only(self):
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
            "step 47 controlled browser automation",
            "step 48",
        ):
            self.assertNotIn(forbidden_text, source)

    def preview_for_steps(self, steps):
        read_result = self.browser_read_snapshot()
        request = self.request(read_result, steps=steps)
        preview = create_browser_automation_preview(request, now_tick=12)
        self.assertEqual("BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY", preview.status)
        return request, preview

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
            sandbox_root="/tmp/browser-governance",
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
            "governance_passed",
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
        self.assertIs(data["human_review_required"], True)
        self.assertIs(data["requires_step47_controlled_execution"], True)


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
