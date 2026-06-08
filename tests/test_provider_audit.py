from __future__ import annotations

import unittest

from runtime.provider_audit import ProviderAuditEvent, make_provider_audit_event


class ProviderAuditTests(unittest.TestCase):
    def test_audit_defaults_keep_provider_output_untrusted_and_non_executing(self) -> None:
        event = ProviderAuditEvent(
            event_id="audit-1",
            timestamp_utc="2026-06-08T13:00:00Z",
            provider_id="gemini",
            model_id="gemini/gemini-2.5-flash",
            status="CALL_BLOCKED",
            reason="human approval is required",
        )

        self.assertFalse(event.provider_output_trusted)
        self.assertFalse(event.execution_triggered)
        self.assertFalse(event.canonical_promotion_triggered)
        self.assertFalse(event.automatic_fallback_used)
        self.assertTrue(event.secrets_redacted)

    def test_audit_rejects_trusted_output_or_execution_flags(self) -> None:
        bad_flags = {
            "provider_output_trusted": True,
            "execution_triggered": True,
            "canonical_promotion_triggered": True,
            "automatic_fallback_used": True,
            "secrets_redacted": False,
        }
        for field, value in bad_flags.items():
            with self.subTest(field=field):
                kwargs = {
                    "event_id": "audit-1",
                    "timestamp_utc": "2026-06-08T13:00:00Z",
                    "provider_id": "gemini",
                    "model_id": "gemini/gemini-2.5-flash",
                    "status": "CALL_BLOCKED",
                    "reason": "blocked",
                    field: value,
                }
                with self.assertRaises(ValueError):
                    ProviderAuditEvent(**kwargs)

    def test_factory_creates_memory_only_redacted_event(self) -> None:
        event = make_provider_audit_event(
            provider_id="openrouter",
            model_id="openrouter/google/gemma-3-27b-it",
            status="CALL_MADE",
            reason="approved one-shot call",
            call_made=True,
            human_approved=True,
            provider_call_permitted=True,
        )

        payload = event.to_dict()
        self.assertTrue(payload["event_id"].startswith("provider-audit-"))
        self.assertTrue(payload["timestamp_utc"].endswith("Z"))
        self.assertFalse(payload["provider_output_trusted"])
        self.assertFalse(payload["execution_triggered"])
        self.assertFalse(payload["canonical_promotion_triggered"])
        self.assertTrue(payload["secrets_redacted"])


if __name__ == "__main__":
    unittest.main()
