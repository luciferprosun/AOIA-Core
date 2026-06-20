from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from runtime.provider_request_flow import (
    UNTRUSTED_PROVIDER_OUTPUT,
    ProviderRegistryDecision,
    ProviderRequest,
)
from runtime.provider_registry import get_provider_profile
from runtime.safety.provider_call_limits import ProviderCallBudgetConfig


LIVE_PROVIDER_ADAPTER_BLOCKED = "LIVE_PROVIDER_ADAPTER_BLOCKED"
FUTURE_LIVE_SMOKE_TEST = "future_live_smoke_test"
MANUAL_SMOKE_TEST_REQUIRED = "manual_smoke_test_required"
REGISTRY_ALLOW_REQUIRED = "registry_allow_required"
BUDGET_LIMIT_REQUIRED = "budget_limit_required"


class ProviderLiveCallBlockedError(RuntimeError):
    """Raised only when a caller explicitly requests exception-style blocking."""


@dataclass(frozen=True)
class LiveProviderAdapterRequest:
    request: ProviderRequest
    model_label: str
    manual_live_call_requested: bool = False
    adapter_metadata: Mapping[str, Any] = field(default_factory=dict)
    adapter_request_id: str = field(init=False)
    adapter_request_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, ProviderRequest):
            raise TypeError("request must be a ProviderRequest")
        model_label = _required_text(self.model_label, "model_label")
        if not isinstance(self.manual_live_call_requested, bool):
            raise TypeError("manual_live_call_requested must be boolean")
        metadata = _canonical_mapping(self.adapter_metadata, "adapter_metadata")
        values = {
            "request_id": self.request.request_id,
            "request_hash": self.request.request_hash,
            "provider_id": self.request.provider_id,
            "model_label": model_label,
            "manual_live_call_requested": self.manual_live_call_requested,
            "adapter_metadata": metadata,
        }
        adapter_request_hash = _stable_hash(values)
        object.__setattr__(self, "model_label", model_label)
        object.__setattr__(self, "adapter_metadata", metadata)
        object.__setattr__(self, "adapter_request_hash", adapter_request_hash)
        object.__setattr__(
            self,
            "adapter_request_id",
            "provider-e-live-adapter-request-" + adapter_request_hash[:24],
        )


@dataclass(frozen=True)
class LiveProviderAdapterDecision:
    status: str
    provider_id: str
    model_label: str
    adapter_request_id: str
    adapter_request_hash: str
    provider_request_id: str
    provider_request_hash: str
    registry_decision_summary: Mapping[str, Any] | None
    manual_live_call_requested: bool
    budget_limit_present: bool
    profile_registered: bool
    profile_enabled: bool
    network_allowed: bool
    live_call_attempted: bool
    live_call_blocked: bool
    blocked_reason: str
    trust_label: str
    real_provider_response_text: str | None
    future_smoke_test_seam: str
    manual_smoke_test_required: bool
    registry_allow_required: bool
    budget_limit_required: bool
    decision_id: str = field(init=False)
    decision_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.live_call_attempted is not False:
            raise ValueError("Provider-E cannot attempt a live call")
        if self.live_call_blocked is not True:
            raise ValueError("Provider-E decisions must remain blocked")
        if self.trust_label != UNTRUSTED_PROVIDER_OUTPUT:
            raise ValueError("Provider-E trust cannot exceed UNTRUSTED_PROVIDER_OUTPUT")
        if self.real_provider_response_text is not None:
            raise ValueError("Provider-E cannot contain real provider response text")
        values = {
            "status": self.status,
            "provider_id": self.provider_id,
            "model_label": self.model_label,
            "adapter_request_id": self.adapter_request_id,
            "adapter_request_hash": self.adapter_request_hash,
            "provider_request_id": self.provider_request_id,
            "provider_request_hash": self.provider_request_hash,
            "registry_decision_summary": self.registry_decision_summary,
            "manual_live_call_requested": self.manual_live_call_requested,
            "budget_limit_present": self.budget_limit_present,
            "profile_registered": self.profile_registered,
            "profile_enabled": self.profile_enabled,
            "network_allowed": self.network_allowed,
            "live_call_attempted": False,
            "live_call_blocked": True,
            "blocked_reason": self.blocked_reason,
            "trust_label": UNTRUSTED_PROVIDER_OUTPUT,
            "real_provider_response_text": None,
            "future_smoke_test_seam": self.future_smoke_test_seam,
            "manual_smoke_test_required": self.manual_smoke_test_required,
            "registry_allow_required": self.registry_allow_required,
            "budget_limit_required": self.budget_limit_required,
        }
        decision_hash = _stable_hash(values)
        object.__setattr__(self, "decision_hash", decision_hash)
        object.__setattr__(
            self,
            "decision_id",
            "provider-e-live-adapter-decision-" + decision_hash[:24],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "status": self.status,
            "provider_id": self.provider_id,
            "model_label": self.model_label,
            "adapter_request_id": self.adapter_request_id,
            "adapter_request_hash": self.adapter_request_hash,
            "provider_request_id": self.provider_request_id,
            "provider_request_hash": self.provider_request_hash,
            "registry_decision_summary": (
                dict(self.registry_decision_summary)
                if self.registry_decision_summary is not None
                else None
            ),
            "manual_live_call_requested": self.manual_live_call_requested,
            "budget_limit_present": self.budget_limit_present,
            "profile_registered": self.profile_registered,
            "profile_enabled": self.profile_enabled,
            "network_allowed": self.network_allowed,
            "live_call_attempted": False,
            "live_call_blocked": True,
            "blocked_reason": self.blocked_reason,
            "trust_label": UNTRUSTED_PROVIDER_OUTPUT,
            "real_provider_response_text": None,
            "future_smoke_test_seam": FUTURE_LIVE_SMOKE_TEST,
            "manual_smoke_test_required": True,
            "registry_allow_required": True,
            "budget_limit_required": True,
        }


LiveProviderAdapterBlocked = LiveProviderAdapterDecision


class DefaultOffProviderAdapter:
    """Future live-provider seam that cannot construct or perform a call."""

    def evaluate(
        self,
        *,
        adapter_request: LiveProviderAdapterRequest,
        registry_decision: ProviderRegistryDecision | None,
        budget_limit: ProviderCallBudgetConfig | None,
    ) -> LiveProviderAdapterBlocked:
        if not isinstance(adapter_request, LiveProviderAdapterRequest):
            raise TypeError("adapter_request must be a LiveProviderAdapterRequest")
        request = adapter_request.request
        profile = get_provider_profile(request.provider_id)
        registered = profile is not None
        enabled = bool(profile is not None and profile.enabled)
        network_allowed = bool(profile is not None and profile.network_allowed)
        registry_summary = (
            registry_decision.summary()
            if isinstance(registry_decision, ProviderRegistryDecision)
            else None
        )

        if not _decision_matches_request(request, registry_decision):
            reason = "registry allow required: matching registry decision is missing"
        elif adapter_request.manual_live_call_requested is not True:
            reason = "manual smoke test required: explicit manual live-call flag is absent"
        elif budget_limit is None:
            reason = "budget limit required: provider call budget is absent"
        elif not isinstance(budget_limit, ProviderCallBudgetConfig):
            reason = "budget limit required: provider call budget is invalid"
        elif not registered:
            reason = "registry allow required: provider profile is not registered"
        elif not enabled:
            reason = "registry allow required: provider profile is disabled"
        elif not network_allowed:
            reason = "registry allow required: provider profile is offline-only"
        elif registry_decision.live_call_allowed is not True:
            reason = "registry allow required: live calls are not explicitly allowed"
        else:
            reason = "future live smoke test seam is inactive in Provider-E"

        return LiveProviderAdapterDecision(
            status=LIVE_PROVIDER_ADAPTER_BLOCKED,
            provider_id=request.provider_id,
            model_label=adapter_request.model_label,
            adapter_request_id=adapter_request.adapter_request_id,
            adapter_request_hash=adapter_request.adapter_request_hash,
            provider_request_id=request.request_id,
            provider_request_hash=request.request_hash,
            registry_decision_summary=registry_summary,
            manual_live_call_requested=adapter_request.manual_live_call_requested,
            budget_limit_present=isinstance(
                budget_limit,
                ProviderCallBudgetConfig,
            ),
            profile_registered=registered,
            profile_enabled=enabled,
            network_allowed=network_allowed,
            live_call_attempted=False,
            live_call_blocked=True,
            blocked_reason=reason,
            trust_label=UNTRUSTED_PROVIDER_OUTPUT,
            real_provider_response_text=None,
            future_smoke_test_seam=FUTURE_LIVE_SMOKE_TEST,
            manual_smoke_test_required=True,
            registry_allow_required=True,
            budget_limit_required=True,
        )

    def require_blocked(
        self,
        *,
        adapter_request: LiveProviderAdapterRequest,
        registry_decision: ProviderRegistryDecision | None,
        budget_limit: ProviderCallBudgetConfig | None,
    ) -> None:
        decision = self.evaluate(
            adapter_request=adapter_request,
            registry_decision=registry_decision,
            budget_limit=budget_limit,
        )
        raise ProviderLiveCallBlockedError(decision.blocked_reason)


def _decision_matches_request(
    request: ProviderRequest,
    decision: ProviderRegistryDecision | None,
) -> bool:
    return bool(
        isinstance(decision, ProviderRegistryDecision)
        and decision.request_id == request.request_id
        and decision.request_hash == request.request_hash
        and decision.provider_id == request.provider_id
    )


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _canonical_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        result = json.loads(encoded)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must contain deterministic JSON values") from error
    if not isinstance(result, dict):
        raise TypeError(f"{name} must be a mapping")
    return result


def _stable_hash(values: Mapping[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
