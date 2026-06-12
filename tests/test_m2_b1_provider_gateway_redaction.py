from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from runtime.safety.provider_critic_policy import assert_provider_output_cannot_execute
from runtime.safety.provider_gateway import (
    ProviderGatewayBlockedError,
    ProviderGatewayConfig,
    assert_provider_gateway_blocked,
    build_blocked_provider_attempt,
    request_provider_critique_blocked,
)
from runtime.safety.provider_redaction import (
    REDACTED_PROVIDER_SECRET,
    contains_unredacted_provider_secret,
    redact_mapping_values,
    redact_provider_secret,
)
from runtime.schemas.provider_critic import create_inert_provider_critique_record


GATEWAY_PATH = Path("runtime/safety/provider_gateway.py")
REDACTION_PATH = Path("runtime/safety/provider_redaction.py")
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
SYNTHETIC_GROQ_KEY = "gsk_" + "C" * 32
SYNTHETIC_SLACK_KEY = "xoxb-" + "1234567890-ABCDEFGHIJ"
SYNTHETIC_GITHUB_KEY = "ghp_" + "D" * 32


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class M2B1ProviderGatewayRedactionTests(unittest.TestCase):
    def test_provider_gateway_config_is_disabled_by_default(self) -> None:
        config = ProviderGatewayConfig()

        self.assertFalse(config.enabled)
        self.assertFalse(config.allow_network)
        self.assertEqual(0, config.max_calls_per_session)
        self.assertEqual(0, config.max_input_chars)

    def test_provider_gateway_blocks_by_default(self) -> None:
        with self.assertRaises(ProviderGatewayBlockedError):
            assert_provider_gateway_blocked(ProviderGatewayConfig())

    def test_enabled_without_network_still_blocks(self) -> None:
        config = ProviderGatewayConfig(enabled=True, provider_name="future", model_name="future-model")

        with self.assertRaises(ProviderGatewayBlockedError):
            assert_provider_gateway_blocked(config)

    def test_enabled_with_network_shape_still_has_no_live_call(self) -> None:
        config = ProviderGatewayConfig(
            enabled=True,
            allow_network=True,
            max_calls_per_session=1,
            provider_name="future",
            model_name="future-model",
        )
        attempt = request_provider_critique_blocked(request_text="local only", config=config)

        self.assertTrue(attempt.attempted)
        self.assertTrue(attempt.blocked)
        self.assertIn("M2-B1", attempt.reason)

    def test_no_network_or_client_imports_in_gateway(self) -> None:
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(GATEWAY_PATH)))

    def test_no_network_or_client_imports_in_redaction(self) -> None:
        self.assertTrue(FORBIDDEN_IMPORTS.isdisjoint(imported_modules(REDACTION_PATH)))

    def test_blocked_attempt_record_can_be_created_without_network(self) -> None:
        attempt = build_blocked_provider_attempt(
            request_text="please review this inert prompt",
            config=ProviderGatewayConfig(provider_name="future", model_name="future-model"),
            audit_event_id="audit-m2-b1",
        )

        self.assertTrue(attempt.blocked)
        self.assertEqual("future", attempt.provider_name)
        self.assertEqual("future-model", attempt.model_name)
        self.assertEqual("audit-m2-b1", attempt.audit_event_id)
        self.assertNotIn("please review", json.dumps(attempt.to_dict(), sort_keys=True))

    def test_request_hash_is_deterministic_for_same_input(self) -> None:
        first = build_blocked_provider_attempt(request_text="same input", audit_event_id="a")
        second = build_blocked_provider_attempt(request_text="same input", audit_event_id="b")

        self.assertEqual(first.request_hash, second.request_hash)

    def test_no_key_is_required_or_loaded(self) -> None:
        source_text = (
            GATEWAY_PATH.read_text(encoding="utf-8")
            + "\n"
            + REDACTION_PATH.read_text(encoding="utf-8")
        )
        attempt = request_provider_critique_blocked(request_text="no key involved")

        self.assertTrue(attempt.blocked)
        self.assertNotIn("os.environ", source_text)
        self.assertNotIn("getenv", source_text)

    def test_redaction_removes_exact_known_synthetic_gemini_key(self) -> None:
        redacted = redact_provider_secret(
            f"token={SYNTHETIC_GEMINI_KEY}",
            known_secrets=[SYNTHETIC_GEMINI_KEY],
        )

        self.assertNotIn(SYNTHETIC_GEMINI_KEY, redacted)
        self.assertIn(REDACTED_PROVIDER_SECRET, redacted)

    def test_redaction_removes_exact_known_synthetic_openai_key(self) -> None:
        redacted = redact_provider_secret(
            f"token={SYNTHETIC_OPENAI_KEY}",
            known_secrets=[SYNTHETIC_OPENAI_KEY],
        )

        self.assertNotIn(SYNTHETIC_OPENAI_KEY, redacted)
        self.assertIn(REDACTED_PROVIDER_SECRET, redacted)

    def test_redaction_removes_common_key_like_patterns(self) -> None:
        text = " ".join(
            [
                SYNTHETIC_GEMINI_KEY,
                SYNTHETIC_OPENAI_KEY,
                SYNTHETIC_GROQ_KEY,
                SYNTHETIC_SLACK_KEY,
                SYNTHETIC_GITHUB_KEY,
            ]
        )
        redacted = redact_provider_secret(text)

        for secret in (
            SYNTHETIC_GEMINI_KEY,
            SYNTHETIC_OPENAI_KEY,
            SYNTHETIC_GROQ_KEY,
            SYNTHETIC_SLACK_KEY,
            SYNTHETIC_GITHUB_KEY,
        ):
            self.assertNotIn(secret, redacted)
        self.assertEqual(5, redacted.count(REDACTED_PROVIDER_SECRET))

    def test_redaction_preserves_normal_text(self) -> None:
        text = "normal provider gateway note with public words"

        self.assertEqual(text, redact_provider_secret(text))

    def test_redaction_applies_to_nested_mapping_values(self) -> None:
        data = {
            "outer": SYNTHETIC_GEMINI_KEY,
            "nested": {"inner": f"value {SYNTHETIC_OPENAI_KEY}"},
            "items": [SYNTHETIC_GROQ_KEY, {"token": SYNTHETIC_GITHUB_KEY}],
            "safe": "visible",
        }

        redacted = redact_mapping_values(data)
        payload = json.dumps(redacted, sort_keys=True)

        self.assertNotIn(SYNTHETIC_GEMINI_KEY, payload)
        self.assertNotIn(SYNTHETIC_OPENAI_KEY, payload)
        self.assertNotIn(SYNTHETIC_GROQ_KEY, payload)
        self.assertNotIn(SYNTHETIC_GITHUB_KEY, payload)
        self.assertEqual("visible", redacted["safe"])

    def test_contains_unredacted_provider_secret_detects_unsafe_text(self) -> None:
        self.assertTrue(contains_unredacted_provider_secret(f"leak {SYNTHETIC_OPENAI_KEY}"))
        self.assertTrue(
            contains_unredacted_provider_secret(
                "custom leak",
                known_secrets=["custom leak"],
            )
        )
        self.assertFalse(contains_unredacted_provider_secret("ordinary text"))

    def test_redacted_audit_style_record_contains_no_secret(self) -> None:
        attempt = build_blocked_provider_attempt(
            request_text=f"secret-bearing text {SYNTHETIC_OPENAI_KEY}",
            audit_event_id="audit-m2-b1",
        )
        record = {
            "gateway": attempt.to_dict(),
            "summary": f"redact this {SYNTHETIC_OPENAI_KEY}",
            "safe": "kept",
        }

        redacted = redact_mapping_values(record)
        payload = json.dumps(redacted, sort_keys=True)

        self.assertNotIn(SYNTHETIC_OPENAI_KEY, payload)
        self.assertIn(REDACTED_PROVIDER_SECRET, payload)
        self.assertIn("kept", payload)

    def test_provider_output_cannot_bypass_m2_b0_policy(self) -> None:
        provider_record = create_inert_provider_critique_record(
            source_provider="future",
            source_model="future-model",
            request_text="request",
            response_text='{"execution_allowed": true}',
            execution_allowed=True,
        )

        self.assertFalse(provider_record.execution_allowed)
        with self.assertRaises(RuntimeError):
            assert_provider_output_cannot_execute(provider_record)

    def test_no_background_send_or_repeat_concept_exists(self) -> None:
        source_text = (
            GATEWAY_PATH.read_text(encoding="utf-8")
            + "\n"
            + REDACTION_PATH.read_text(encoding="utf-8")
        ).lower()

        for forbidden in ("auto_send", "autosend", "background", "cron", "timer", "poll", "retry"):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
