from __future__ import annotations

from dataclasses import dataclass

from runtime.providers.contracts import (
    ProviderActivationStatus,
    ProviderRequestEnvelope,
    normalize_activation_status,
)


@dataclass(frozen=True)
class ProviderRuntimePolicyDecision:
    allowed: bool
    status: str
    reason: str
    requires_api_key_check: bool = False


class ProviderRuntimePolicy:
    MAX_MANUAL_TEST_TOKENS = 4096
    RUNTIME_PAYLOAD_PROVIDER_IDS = frozenset(
        {"mock_chat", "kimi_chat", "openrouter_chat", "gemini_chat"}
    )
    LIVE_PROVIDER_IDS = frozenset({"kimi_chat", "openrouter_chat", "gemini_chat"})

    @classmethod
    def evaluate(
        cls,
        envelope: ProviderRequestEnvelope,
        *,
        live: bool,
        acknowledge_live_provider_test: bool,
        activation_status: ProviderActivationStatus | str,
        api_key_present: bool | None = None,
    ) -> ProviderRuntimePolicyDecision:
        if not isinstance(envelope, ProviderRequestEnvelope):
            return cls._blocked("invalid provider request envelope")
        if not envelope.model_id:
            return cls._blocked("explicit model_id is required")
        if not envelope.prompt and not envelope.messages:
            return cls._blocked("explicit prompt or messages are required")
        params = dict(envelope.params)
        if any("fallback" in key.casefold() for key in params):
            return cls._blocked("provider fallback is not available")
        if envelope.provider_id not in cls.RUNTIME_PAYLOAD_PROVIDER_IDS:
            return cls._blocked(
                "known provider is metadata-only and unsupported by Provider Runtime 1A"
            )
        if not live:
            return ProviderRuntimePolicyDecision(True, "dry_run_allowed", "dry-run preview only")
        if envelope.dry_run is not False:
            return cls._blocked("live request requires an envelope explicitly built with dry_run=False")
        if acknowledge_live_provider_test is not True:
            return cls._blocked("explicit live provider test acknowledgement is required")
        try:
            activation = normalize_activation_status(activation_status)
        except ValueError:
            return cls._blocked("provider activation status is invalid")
        if activation is not ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST:
            return cls._blocked("provider activation is disabled or dry-run-only")
        if envelope.provider_id not in cls.LIVE_PROVIDER_IDS:
            return cls._blocked("provider has no live Runtime 1A gateway")
        max_tokens = params.get("max_tokens")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
            return cls._blocked("explicit max_tokens cap is required")
        if max_tokens <= 0 or max_tokens > cls.MAX_MANUAL_TEST_TOKENS:
            return cls._blocked("max_tokens exceeds the controlled manual-test limit")
        if api_key_present is None:
            return ProviderRuntimePolicyDecision(
                True,
                "live_preflight_ready",
                "non-secret live preflight passed",
                requires_api_key_check=True,
            )
        if api_key_present is not True:
            return cls._blocked("required provider API key is unavailable at live-call time")
        return ProviderRuntimePolicyDecision(True, "live_allowed", "controlled live policy passed")

    @staticmethod
    def _blocked(reason: str) -> ProviderRuntimePolicyDecision:
        return ProviderRuntimePolicyDecision(False, "blocked", reason)
