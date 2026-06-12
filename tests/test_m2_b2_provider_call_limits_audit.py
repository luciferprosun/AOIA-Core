from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from runtime.safety.provider_attempt_audit import (
    audit_record_to_dict,
    create_blocked_provider_attempt_audit,
)
from runtime.safety.provider_call_limits import (
    ProviderCallBudgetConfig,
    ProviderCallLimitExceededError,
    ProviderCallSessionState,
    assert_call_within_limits,
    default_provider_call_budget_config,
    estimate_tokens_from_chars,
    record_blocked_call,
)
from runtime.safety.provider_gateway import ProviderGatewayConfig, request_provider_critique_blocked


CALL_LIMITS_PATH = Path("runtime/safety/provider_call_limits.py")
ATTEMPT_AUDIT_PATH = Path("runtime/safety/provider_attempt_audit.py")
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
SYNTHETIC_GEMINI_KEY = "AIza" + "A" * 32
SYNTHETIC_OPENAI_KEY = "sk-" + "B" * 32


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def permissive_budget(**overrides: object) -> ProviderCallBudgetConfig:
    payload = {
        "max_calls_per_session": 2,
        "max_calls_per_day": 2,
        "max_input_chars_per_request": 100,
        "max_estimated_tokens_per_request": 100,
        "max_estimated_cost_per_session": "1.00",
        "max_estimated_cost_per_day": "1.00",
    }
    payload.update(overrides)
    return ProviderCallBudgetConfig(**payload)


class M2B2ProviderCallLimitsAuditTests(unittest.TestCase):
    def test_default_call_budget_allows_zero_calls(self) -> None:
        config = default_provider_call_budget_config()

        self.assertEqual(0, config.max_calls_per_session)
        self.assertEqual(0, config.max_calls_per_day)

    def test_call_limit_blocks_by_default(self) -> None:
        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                default_provider_call_budget_config(),
                ProviderCallSessionState(session_id="session"),
                input_chars=1,
                estimated_tokens=1,
                estimated_cost="0",
            )

    def test_session_call_ceiling_blocks_next_attempt(self) -> None:
        state = ProviderCallSessionState(session_id="session", calls_attempted=1)

        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                permissive_budget(max_calls_per_session=1),
                state,
                input_chars=1,
                estimated_tokens=1,
                estimated_cost="0.01",
            )

    def test_day_call_ceiling_blocks_next_attempt(self) -> None:
        state = ProviderCallSessionState(session_id="session", calls_attempted=1, day_key="2026-06-12")

        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                permissive_budget(max_calls_per_day=1),
                state,
                input_chars=1,
                estimated_tokens=1,
                estimated_cost="0.01",
            )

    def test_input_char_ceiling_blocks_oversized_prompt(self) -> None:
        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                permissive_budget(max_input_chars_per_request=3),
                ProviderCallSessionState(session_id="session"),
                input_chars=4,
                estimated_tokens=1,
                estimated_cost="0.01",
            )

    def test_token_estimate_ceiling_blocks_oversized_prompt(self) -> None:
        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                permissive_budget(max_estimated_tokens_per_request=1),
                ProviderCallSessionState(session_id="session"),
                input_chars=8,
                estimated_tokens=2,
                estimated_cost="0.01",
            )

    def test_cost_ceiling_blocks_over_budget_attempt(self) -> None:
        with self.assertRaises(ProviderCallLimitExceededError):
            assert_call_within_limits(
                permissive_budget(max_estimated_cost_per_session="0.05"),
                ProviderCallSessionState(session_id="session", estimated_cost_total="0.04"),
                input_chars=1,
                estimated_tokens=1,
                estimated_cost="0.02",
            )

    def test_rough_token_estimate_is_deterministic(self) -> None:
        self.assertEqual(1, estimate_tokens_from_chars(""))
        self.assertEqual(1, estimate_tokens_from_chars("abcd"))
        self.assertEqual(2, estimate_tokens_from_chars("abcde"))
        self.assertEqual(estimate_tokens_from_chars("same text"), estimate_tokens_from_chars("same text"))

    def test_blocked_call_increments_blocked_counter(self) -> None:
        updated = record_blocked_call(ProviderCallSessionState(session_id="session"))

        self.assertEqual(1, updated.calls_attempted)
        self.assertEqual(1, updated.calls_blocked)
        self.assertEqual(0, updated.calls_allowed)

    def test_audit_record_for_blocked_attempt_is_created(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name="future",
            model_name="future-model",
            request_text="review local text",
            block_reason="blocked by M2-B2",
            created_at="2026-06-12T15:09:00Z",
            audit_event_id="audit-m2-b2",
        )

        self.assertEqual("audit-m2-b2", record.audit_event_id)
        self.assertTrue(record.request_hash)

    def test_audit_record_has_attempted_true_and_blocked_true(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name="future",
            model_name="future-model",
            request_text="review",
            block_reason="blocked",
        )

        self.assertTrue(record.attempted)
        self.assertTrue(record.blocked)

    def test_audit_record_has_network_allowed_false(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name="future",
            model_name="future-model",
            request_text="review",
            block_reason="blocked",
            network_allowed=True,
        )

        self.assertFalse(record.network_allowed)

    def test_audit_record_contains_no_unredacted_synthetic_gemini_key(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name="future",
            model_name="future-model",
            request_text=f"request {SYNTHETIC_GEMINI_KEY}",
            block_reason=f"blocked {SYNTHETIC_GEMINI_KEY}",
            notes=f"note {SYNTHETIC_GEMINI_KEY}",
            known_secrets=[SYNTHETIC_GEMINI_KEY],
        )
        payload = json.dumps(audit_record_to_dict(record), sort_keys=True)

        self.assertNotIn(SYNTHETIC_GEMINI_KEY, payload)
        self.assertTrue(record.redaction_applied)
        self.assertFalse(record.secret_present_after_redaction)

    def test_audit_record_contains_no_unredacted_synthetic_openai_key(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name=f"future {SYNTHETIC_OPENAI_KEY}",
            model_name="future-model",
            request_text=f"request {SYNTHETIC_OPENAI_KEY}",
            block_reason="blocked",
            notes=f"note {SYNTHETIC_OPENAI_KEY}",
            known_secrets=[SYNTHETIC_OPENAI_KEY],
        )
        payload = json.dumps(audit_record_to_dict(record), sort_keys=True)

        self.assertNotIn(SYNTHETIC_OPENAI_KEY, payload)
        self.assertTrue(record.redaction_applied)
        self.assertFalse(record.secret_present_after_redaction)

    def test_audit_record_serializes_to_dict(self) -> None:
        record = create_blocked_provider_attempt_audit(
            provider_name="future",
            model_name="future-model",
            request_text="review",
            block_reason="blocked",
            estimated_tokens=2,
            estimated_cost="0",
        )
        payload = audit_record_to_dict(record)

        self.assertIsInstance(payload, dict)
        self.assertEqual(2, payload["estimated_tokens"])
        self.assertTrue(payload["blocked"])

    def test_provider_gateway_remains_blocked_by_default(self) -> None:
        attempt = request_provider_critique_blocked(
            request_text="review",
            config=ProviderGatewayConfig(),
        )

        self.assertTrue(attempt.blocked)
        self.assertIn("disabled", attempt.reason)

    def test_no_network_or_client_imports_appear_in_new_files(self) -> None:
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(CALL_LIMITS_PATH)))
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(ATTEMPT_AUDIT_PATH)))

    def test_no_api_key_or_env_access_is_required(self) -> None:
        source_text = (
            CALL_LIMITS_PATH.read_text(encoding="utf-8")
            + "\n"
            + ATTEMPT_AUDIT_PATH.read_text(encoding="utf-8")
        ).lower()

        self.assertNotIn("os.environ", source_text)
        self.assertNotIn("getenv", source_text)
        self.assertNotIn("api_key", source_text)

    def test_no_background_send_or_repeat_concept_exists(self) -> None:
        source_text = (
            CALL_LIMITS_PATH.read_text(encoding="utf-8")
            + "\n"
            + ATTEMPT_AUDIT_PATH.read_text(encoding="utf-8")
        ).lower()

        for forbidden in ("auto_send", "autosend", "background", "cron", "timer", "poll", "retry"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
