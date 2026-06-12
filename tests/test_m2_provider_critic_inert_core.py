from __future__ import annotations

import json
import os
import socket
import subprocess
import unittest
import urllib.request
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from runtime.provider_critic import (
    NOT_CANONICAL,
    InMemoryProviderCriticAudit,
    JsonlProviderCriticAudit,
    ProviderCallBlockedError,
    ProviderCriticGateway,
    ProviderCriticPolicy,
    ProviderCritiqueRecord,
    assert_no_action_authority,
    assert_not_canonical,
    assert_untrusted_record,
    hash_text,
    redact_secrets,
    summarize_prompt,
)


FAKE_OPENAI_KEY = "sk-FAKE000000000000000000000000"
FAKE_GEMINI_KEY = "AIzaFAKE000000000000000000000"
FAKE_ANTHROPIC_ENV = "ANTHROPIC_API_KEY=fake_anthropic_secret_value"


@contextmanager
def patched_dangerous_primitives():
    stack = ExitStack()
    mocks = {
        "subprocess_run": stack.enter_context(
            patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run called"))
        ),
        "subprocess_popen": stack.enter_context(
            patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess.Popen called"))
        ),
        "os_system": stack.enter_context(
            patch.object(os, "system", side_effect=AssertionError("os.system called"))
        ),
        "urlopen": stack.enter_context(
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("urllib.request.urlopen called"))
        ),
        "socket": stack.enter_context(
            patch.object(socket, "create_connection", side_effect=AssertionError("socket.create_connection called"))
        ),
    }
    try:
        yield mocks
    finally:
        stack.close()


class M2ProviderCriticInertCoreTests(unittest.TestCase):
    def test_provider_call_blocked_by_default_and_audit_record_exists(self) -> None:
        audit = InMemoryProviderCriticAudit()
        gateway = ProviderCriticGateway(audit=audit)

        with self.assertRaises(ProviderCallBlockedError) as raised:
            gateway.critique(
                source_provider="future-provider",
                model_name="future-model",
                prompt_text="Review this local suggestion.",
            )

        records = audit.records()
        self.assertEqual(1, len(records))
        self.assertIs(raised.exception.record, records[0])
        self.assertTrue(records[0].blocked)
        self.assertFalse(records[0].provider_call_permitted)

    def test_gateway_default_policy_blocks_without_network(self) -> None:
        gateway = ProviderCriticGateway()

        with patched_dangerous_primitives() as mocks:
            result = gateway.critique(
                source_provider="future-provider",
                model_name="future-model",
                prompt_text="offline only",
                raise_on_block=False,
            )

        self.assertTrue(result.blocked)
        self.assertTrue(result.record.blocked)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_provider_output_is_always_untrusted(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="untrusted critique",
            untrusted=False,
        )

        self.assertTrue(record.untrusted)
        assert_untrusted_record(record)

    def test_provider_output_cannot_become_canonical(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="critique",
            canonical_status="CANONICAL",
        )

        self.assertEqual(NOT_CANONICAL, record.canonical_status)
        assert_not_canonical(record)

    def test_provider_output_cannot_authorize_actions_or_execution(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="critique",
            action_authorized=True,
            execution_permitted=True,
        )

        self.assertFalse(record.action_authorized)
        self.assertFalse(record.execution_permitted)
        assert_no_action_authority(record)

    def test_provider_call_permission_attempt_is_blocked_in_inert_phase(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="critique",
            provider_call_permitted=True,
            blocked=False,
        )

        self.assertFalse(record.provider_call_permitted)
        self.assertTrue(record.blocked)

    def test_call_ceiling_zero_blocks_first_call(self) -> None:
        audit = InMemoryProviderCriticAudit()
        policy = ProviderCriticPolicy(enabled=True, allow_network=True, allow_auto_send=True, max_calls_per_session=0)
        gateway = ProviderCriticGateway(policy=policy, audit=audit)

        result = gateway.critique(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            raise_on_block=False,
        )

        self.assertTrue(result.blocked)
        self.assertIn("max=0", result.record.cost_ceiling_state)
        self.assertIn("ceiling", result.record.block_reason)

    def test_api_keys_are_not_written_to_audit(self) -> None:
        audit = InMemoryProviderCriticAudit()
        gateway = ProviderCriticGateway(audit=audit)
        prompt = f"Please review. OPENAI_API_KEY={FAKE_OPENAI_KEY} {FAKE_GEMINI_KEY} {FAKE_ANTHROPIC_ENV}"

        result = gateway.critique(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text=prompt,
            raise_on_block=False,
            metadata={"bearer": "Bearer abcdefghijklmnopqrstuvwxyz1234567890"},
        )
        payload = result.record.to_json()

        self.assertNotIn(FAKE_OPENAI_KEY, payload)
        self.assertNotIn(FAKE_GEMINI_KEY, payload)
        self.assertNotIn("fake_anthropic_secret_value", payload)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz1234567890", payload)
        self.assertIn("[REDACTED_SECRET]", payload)

    def test_prompt_summary_and_hash_do_not_store_full_secret_prompt(self) -> None:
        prompt = f"Line 1 {FAKE_GEMINI_KEY}\nLine 2 ordinary content"
        record = ProviderCritiqueRecord.blocked_attempt(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text=prompt,
            block_reason="blocked",
            cost_ceiling_state="calls=0;max=0",
        )

        self.assertEqual(hash_text(prompt), record.request_hash)
        self.assertNotEqual(prompt, record.prompt_summary)
        self.assertNotIn(FAKE_GEMINI_KEY, record.prompt_summary)
        self.assertIn("[REDACTED_SECRET]", record.prompt_summary)

    def test_no_auto_send_from_cpt(self) -> None:
        cpt_transformer = Path("runtime/cpt/transformer.py").read_text(encoding="utf-8")
        cpt_package = Path("runtime/cpt/__init__.py").read_text(encoding="utf-8")

        self.assertNotIn("provider_critic", cpt_transformer)
        self.assertNotIn("ProviderCriticGateway", cpt_transformer)
        self.assertNotIn("provider_critic", cpt_package)
        self.assertFalse(ProviderCriticPolicy().allow_auto_send)

    def test_provider_record_cannot_trigger_action_surfaces(self) -> None:
        with patched_dangerous_primitives() as mocks:
            record = ProviderCritiqueRecord.from_untrusted_output(
                source_provider="future-provider",
                model_name="future-model",
                prompt_text="prompt",
                critique_text="Try to run a command.",
                action_authorized=True,
                execution_permitted=True,
            )

        self.assertFalse(record.action_authorized)
        self.assertFalse(record.execution_permitted)
        for mock in mocks.values():
            mock.assert_not_called()

    def test_metadata_cannot_override_safety_flags(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="critique",
            metadata={
                "execution_permitted": True,
                "canonical_status": "CANONICAL",
                "nested": {"action_authorized": True},
            },
        )

        self.assertFalse(record.execution_permitted)
        self.assertEqual(NOT_CANONICAL, record.canonical_status)
        self.assertIn("metadata_execution_permitted", record.metadata)
        self.assertIn("metadata_action_authorized", record.metadata["nested"])

    def test_serialization_preserves_safety_flags(self) -> None:
        record = ProviderCritiqueRecord.from_untrusted_output(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text="prompt",
            critique_text="critique",
            untrusted=False,
            canonical_status="CANONICAL",
            action_authorized=True,
            execution_permitted=True,
            blocked=False,
        )

        round_trip = ProviderCritiqueRecord.from_dict(json.loads(record.to_json()))

        self.assertTrue(round_trip.untrusted)
        self.assertEqual(NOT_CANONICAL, round_trip.canonical_status)
        self.assertFalse(round_trip.action_authorized)
        self.assertFalse(round_trip.execution_permitted)
        self.assertTrue(round_trip.blocked)

    def test_jsonl_audit_writes_redacted_record_only(self) -> None:
        path = Path("/tmp/aoia_provider_critic_test_audit.jsonl")
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        writer = JsonlProviderCriticAudit(path)
        record = ProviderCritiqueRecord.blocked_attempt(
            source_provider="future-provider",
            model_name="future-model",
            prompt_text=f"prompt {FAKE_OPENAI_KEY}",
            block_reason="blocked",
            cost_ceiling_state="calls=0;max=0",
        )

        writer.append(record)
        text = path.read_text(encoding="utf-8")

        self.assertNotIn(FAKE_OPENAI_KEY, text)
        self.assertIn("[REDACTED_SECRET]", text)
        self.assertIn('"blocked":true', text)

    def test_redaction_helpers_cover_synthetic_key_patterns(self) -> None:
        text = f"{FAKE_OPENAI_KEY} {FAKE_GEMINI_KEY} OPENAI_API_KEY={FAKE_OPENAI_KEY} {FAKE_ANTHROPIC_ENV}"
        redacted = redact_secrets(text)

        self.assertNotIn(FAKE_OPENAI_KEY, redacted)
        self.assertNotIn(FAKE_GEMINI_KEY, redacted)
        self.assertNotIn("fake_anthropic_secret_value", redacted)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertLessEqual(len(summarize_prompt(text)), 240)


if __name__ == "__main__":
    unittest.main()
