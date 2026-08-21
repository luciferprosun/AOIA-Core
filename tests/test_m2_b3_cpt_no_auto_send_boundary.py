from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from runtime.cpt.transformer import transform_prompt
from runtime.safety.cpt_provider_boundary import (
    CPTProviderAutoSendBlockedError,
    assert_cpt_does_not_auto_send,
    build_cpt_blocked_provider_attempt,
    evaluate_cpt_provider_boundary,
)


BOUNDARY_PATH = Path("runtime/safety/cpt_provider_boundary.py")
WEB_APP_PATH = Path("web/app.js")
RUNTIME_WEBAPP_PATH = Path("runtime/webapp.py")
FORBIDDEN_IMPORTS = {
    "requests",
    "urllib",
    "http",
    "http.client",
    "socket",
    "google",
    "openai",
    "anthropic",
    "subprocess",
    "os",
    "pathlib",
    "runtime.tools",
    "runtime.providers",
    "runtime.provider_clients",
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class M2B3CPTNoAutoSendBoundaryTests(unittest.TestCase):
    def test_cpt_local_transform_is_allowed_as_local_only_concept(self) -> None:
        record = transform_prompt("Review this local-only boundary.")
        decision = evaluate_cpt_provider_boundary(auto_send_requested=False, human_triggered=False)

        self.assertTrue(decision.cpt_transform_allowed)
        self.assertFalse(record.provider_call_permitted)
        self.assertFalse(record.execution_permitted)

    def test_provider_send_is_not_allowed_by_default(self) -> None:
        decision = evaluate_cpt_provider_boundary(auto_send_requested=False, human_triggered=False)

        self.assertFalse(decision.provider_send_allowed)
        self.assertTrue(decision.human_trigger_required)

    def test_auto_send_requested_true_is_blocked(self) -> None:
        decision = evaluate_cpt_provider_boundary(auto_send_requested=True, human_triggered=True)

        self.assertTrue(decision.auto_send_blocked)
        self.assertFalse(decision.provider_send_allowed)
        with self.assertRaises(CPTProviderAutoSendBlockedError):
            assert_cpt_does_not_auto_send(auto_send_requested=True, human_triggered=True)

    def test_human_triggered_false_is_blocked(self) -> None:
        with self.assertRaises(CPTProviderAutoSendBlockedError):
            assert_cpt_does_not_auto_send(auto_send_requested=False, human_triggered=False)

    def test_human_triggered_true_does_not_create_live_provider_call(self) -> None:
        decision = evaluate_cpt_provider_boundary(auto_send_requested=False, human_triggered=True)
        audit_record = build_cpt_blocked_provider_attempt(
            transformed_prompt="local transformed prompt",
            provider_name="future",
            model_name="future-model",
            human_triggered=True,
        )

        self.assertTrue(decision.provider_send_allowed)
        self.assertTrue(audit_record.blocked)
        self.assertFalse(audit_record.network_allowed)

    def test_boundary_can_create_blocked_provider_attempt_audit_record(self) -> None:
        audit_record = build_cpt_blocked_provider_attempt(
            transformed_prompt="local transformed prompt",
            provider_name="future",
            model_name="future-model",
            notes="CPT boundary test",
        )

        self.assertTrue(audit_record.attempted)
        self.assertTrue(audit_record.blocked)

    def test_blocked_audit_record_has_blocked_true(self) -> None:
        audit_record = build_cpt_blocked_provider_attempt(transformed_prompt="prompt")

        self.assertTrue(audit_record.blocked)

    def test_blocked_audit_record_has_network_allowed_false(self) -> None:
        audit_record = build_cpt_blocked_provider_attempt(transformed_prompt="prompt", human_triggered=True)

        self.assertFalse(audit_record.network_allowed)

    def test_no_network_or_client_imports_appear_in_boundary(self) -> None:
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(BOUNDARY_PATH)))

    def test_no_api_key_or_env_access_is_required(self) -> None:
        source_text = BOUNDARY_PATH.read_text(encoding="utf-8").lower()

        self.assertNotIn("os.environ", source_text)
        self.assertNotIn("getenv", source_text)
        self.assertNotIn("api_key", source_text)

    def test_no_background_or_repeat_concept_exists(self) -> None:
        source_text = BOUNDARY_PATH.read_text(encoding="utf-8").lower()

        for forbidden in ("background", "cron", "timer", "poll", "retry"):
            self.assertNotIn(forbidden, source_text)

    def test_cpt_boundary_does_not_write_evidence_memory(self) -> None:
        payload = build_cpt_blocked_provider_attempt(transformed_prompt="prompt").to_dict()

        self.assertNotIn("evidence_write_allowed", payload)
        self.assertNotIn("evidence_memory", json.dumps(payload, sort_keys=True).lower())

    def test_cpt_boundary_does_not_write_canonical_knowledge(self) -> None:
        payload = build_cpt_blocked_provider_attempt(transformed_prompt="prompt").to_dict()

        self.assertNotIn("canonical_write_allowed", payload)

    def test_cpt_boundary_does_not_approve_action(self) -> None:
        payload = build_cpt_blocked_provider_attempt(transformed_prompt="prompt").to_dict()

        self.assertNotIn("action_approval_allowed", payload)

    def test_cpt_boundary_does_not_execute(self) -> None:
        payload = build_cpt_blocked_provider_attempt(transformed_prompt="prompt").to_dict()

        self.assertTrue(payload["blocked"])
        self.assertNotIn("execution_allowed", payload)

    def test_web_ui_critic_transform_does_not_auto_send(self) -> None:
        app_source = WEB_APP_PATH.read_text(encoding="utf-8")
        start = app_source.index("async function transformComposerPrompt")
        end = app_source.index("elements.composer.addEventListener", start)
        transform_body = app_source[start:end]

        self.assertNotIn("sendPrompt(", transform_body)
        self.assertIn("Manual send required", transform_body)

    def test_runtime_cpt_endpoint_returns_transform_only(self) -> None:
        source = RUNTIME_WEBAPP_PATH.read_text(encoding="utf-8")
        start = source.index('if path == "/api/cpt/transform"')
        end = source.index('if path == "/api/chat"', start)
        cpt_endpoint_body = source[start:end]

        self.assertIn("build_cpt_transform_payload", cpt_endpoint_body)
        self.assertNotIn("run_prompt", cpt_endpoint_body)
        self.assertNotIn("execute_approved_model_call_once", cpt_endpoint_body)


if __name__ == "__main__":
    unittest.main()
