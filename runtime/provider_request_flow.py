from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from runtime.provider_proposer_adapter import (
    PROVIDER_PROPOSER_CANDIDATE_RECORDED,
    ProviderProposerCandidate,
    create_provider_proposer_candidate,
)
from runtime.provider_registry import get_provider_profile
from runtime.proposer_source_boundary import PROVIDER_CANDIDATE


UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
MOCK_PROVIDER_REQUEST_ALLOWED = "MOCK_PROVIDER_REQUEST_ALLOWED"
BLOCKED_PROVIDER_NOT_REGISTERED = "BLOCKED_PROVIDER_NOT_REGISTERED"
BLOCKED_LIVE_CALL_REQUESTED = "BLOCKED_LIVE_CALL_REQUESTED"


class ProviderRequestFlowBlocked(RuntimeError):
    """Raised when an inert mock-provider flow fails a registry boundary."""


@dataclass(frozen=True)
class ProviderRequest:
    provider_id: str
    task_text: str
    purpose: str
    caller_label: str
    live_call_requested: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)
    request_id: str = field(init=False)
    request_hash: str = field(init=False)

    def __post_init__(self) -> None:
        provider_id = _required_text(self.provider_id, "provider_id").lower()
        task_text = _required_text(self.task_text, "task_text", preserve=True)
        purpose = _required_text(self.purpose, "purpose")
        caller_label = _required_text(self.caller_label, "caller_label")
        if not isinstance(self.live_call_requested, bool):
            raise TypeError("live_call_requested must be boolean")
        metadata = _canonical_mapping(self.metadata, "metadata")
        values = {
            "provider_id": provider_id,
            "task_text": task_text,
            "purpose": purpose,
            "caller_label": caller_label,
            "live_call_requested": self.live_call_requested,
            "metadata": metadata,
        }
        request_hash = _stable_hash(values)
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "task_text", task_text)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "caller_label", caller_label)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "request_hash", request_hash)
        object.__setattr__(self, "request_id", "provider-c-request-" + request_hash[:24])


@dataclass(frozen=True)
class ProviderRegistryDecision:
    request_id: str
    request_hash: str
    provider_id: str
    profile_registered: bool
    profile_enabled: bool
    network_allowed: bool
    mock_output_allowed: bool
    live_call_allowed: bool
    status: str
    reason: str
    decision_id: str = field(init=False)
    decision_hash: str = field(init=False)

    def __post_init__(self) -> None:
        values = {
            "request_id": _required_text(self.request_id, "request_id"),
            "request_hash": _full_hash(self.request_hash, "request_hash"),
            "provider_id": _required_text(self.provider_id, "provider_id").lower(),
            "profile_registered": _required_bool(
                self.profile_registered, "profile_registered"
            ),
            "profile_enabled": _required_bool(self.profile_enabled, "profile_enabled"),
            "network_allowed": _required_bool(
                self.network_allowed, "network_allowed"
            ),
            "mock_output_allowed": _required_bool(
                self.mock_output_allowed, "mock_output_allowed"
            ),
            "live_call_allowed": _required_bool(
                self.live_call_allowed, "live_call_allowed"
            ),
            "status": _required_text(self.status, "status"),
            "reason": _required_text(self.reason, "reason"),
        }
        if values["live_call_allowed"] is not False:
            raise ValueError("Provider-C registry decisions cannot allow live calls")
        decision_hash = _stable_hash(values)
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "decision_hash", decision_hash)
        object.__setattr__(
            self,
            "decision_id",
            "provider-c-registry-decision-" + decision_hash[:24],
        )

    def summary(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "status": self.status,
            "reason": self.reason,
            "profile_registered": self.profile_registered,
            "profile_enabled": self.profile_enabled,
            "network_allowed": self.network_allowed,
            "mock_output_allowed": self.mock_output_allowed,
            "live_call_allowed": False,
        }


@dataclass(frozen=True)
class UntrustedProviderOutput:
    provider_id: str
    model_label: str
    request_id: str
    request_hash: str
    registry_decision_summary: Mapping[str, Any]
    raw_text: str
    provider_metadata: Mapping[str, Any]
    trust_label: str = UNTRUSTED_PROVIDER_OUTPUT
    live_call_used: bool = False
    output_id: str = field(init=False)
    output_hash: str = field(init=False)

    def __post_init__(self) -> None:
        values = {
            "provider_id": _required_text(self.provider_id, "provider_id").lower(),
            "model_label": _required_text(self.model_label, "model_label"),
            "request_id": _required_text(self.request_id, "request_id"),
            "request_hash": _full_hash(self.request_hash, "request_hash"),
            "registry_decision_summary": _canonical_mapping(
                self.registry_decision_summary,
                "registry_decision_summary",
            ),
            "raw_text": _required_text(self.raw_text, "raw_text", preserve=True),
            "provider_metadata": _canonical_mapping(
                self.provider_metadata,
                "provider_metadata",
            ),
            "trust_label": self.trust_label,
            "live_call_used": self.live_call_used,
        }
        if values["trust_label"] != UNTRUSTED_PROVIDER_OUTPUT:
            raise ValueError("provider output must remain UNTRUSTED_PROVIDER_OUTPUT")
        if values["live_call_used"] is not False:
            raise ValueError("mock provider output cannot use a live call")
        output_hash = _stable_hash(values)
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "output_hash", output_hash)
        object.__setattr__(
            self,
            "output_id",
            "untrusted-provider-output-" + output_hash[:24],
        )


class MockProviderProposer:
    """Deterministic local proposer with no provider, secret, or network access."""

    def __init__(self, *, model_label: str, mock_response_text: str) -> None:
        self.model_label = _required_text(model_label, "model_label")
        self.mock_response_text = _required_text(
            mock_response_text,
            "mock_response_text",
            preserve=True,
        )

    def propose(
        self,
        *,
        request: ProviderRequest,
        registry_decision: ProviderRegistryDecision,
    ) -> UntrustedProviderOutput:
        _require_accepted_registry_decision(request, registry_decision)
        return UntrustedProviderOutput(
            provider_id=request.provider_id,
            model_label=self.model_label,
            request_id=request.request_id,
            request_hash=request.request_hash,
            registry_decision_summary=registry_decision.summary(),
            raw_text=self.mock_response_text,
            provider_metadata={
                "request_metadata": request.metadata,
                "purpose": request.purpose,
                "caller_label": request.caller_label,
                "mock_proposer": True,
            },
        )


ProviderProposalCandidate = ProviderProposerCandidate


def decide_mock_provider_request(
    request: ProviderRequest,
) -> ProviderRegistryDecision:
    if not isinstance(request, ProviderRequest):
        raise TypeError("request must be a ProviderRequest")
    profile = get_provider_profile(request.provider_id)
    if profile is None:
        return ProviderRegistryDecision(
            request_id=request.request_id,
            request_hash=request.request_hash,
            provider_id=request.provider_id,
            profile_registered=False,
            profile_enabled=False,
            network_allowed=False,
            mock_output_allowed=False,
            live_call_allowed=False,
            status=BLOCKED_PROVIDER_NOT_REGISTERED,
            reason="provider profile is not registered",
        )
    if request.live_call_requested:
        return ProviderRegistryDecision(
            request_id=request.request_id,
            request_hash=request.request_hash,
            provider_id=request.provider_id,
            profile_registered=True,
            profile_enabled=profile.enabled,
            network_allowed=profile.network_allowed,
            mock_output_allowed=False,
            live_call_allowed=False,
            status=BLOCKED_LIVE_CALL_REQUESTED,
            reason="Provider-C accepts inert mock requests only; live calls remain blocked",
        )
    return ProviderRegistryDecision(
        request_id=request.request_id,
        request_hash=request.request_hash,
        provider_id=request.provider_id,
        profile_registered=True,
        profile_enabled=profile.enabled,
        network_allowed=profile.network_allowed,
        mock_output_allowed=True,
        live_call_allowed=False,
        status=MOCK_PROVIDER_REQUEST_ALLOWED,
        reason="registered profile accepted for deterministic offline mock proposing only",
    )


def convert_untrusted_provider_output_to_candidate(
    *,
    output: UntrustedProviderOutput,
    registry_decision: ProviderRegistryDecision,
    extracted_title: str | None = None,
    extracted_intent: str | None = None,
    extracted_summary: str | None = None,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    created_at: str | None = None,
) -> ProviderProposalCandidate:
    if not isinstance(output, UntrustedProviderOutput):
        raise TypeError("output must be an UntrustedProviderOutput")
    if not isinstance(registry_decision, ProviderRegistryDecision):
        raise TypeError("registry_decision must be a ProviderRegistryDecision")
    if (
        registry_decision.mock_output_allowed is not True
        or registry_decision.status != MOCK_PROVIDER_REQUEST_ALLOWED
        or registry_decision.request_id != output.request_id
        or registry_decision.request_hash != output.request_hash
        or registry_decision.provider_id != output.provider_id
        or output.trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or output.live_call_used is not False
    ):
        raise ProviderRequestFlowBlocked(
            "provider output is not backed by an accepted matching registry decision"
        )
    candidate = create_provider_proposer_candidate(
        provider_label=output.provider_id,
        model_label=output.model_label,
        raw_provider_output={
            "output_id": output.output_id,
            "output_hash": output.output_hash,
            "request_id": output.request_id,
            "request_hash": output.request_hash,
            "registry_decision": output.registry_decision_summary,
            "raw_text": output.raw_text,
            "provider_metadata": output.provider_metadata,
            "trust_label": UNTRUSTED_PROVIDER_OUTPUT,
            "live_call_used": False,
        },
        source_type=PROVIDER_CANDIDATE,
        extracted_title=extracted_title or "Review mock provider proposal",
        extracted_intent=extracted_intent
        or "Preserve untrusted provider output as inert proposal data.",
        extracted_summary=extracted_summary or output.raw_text,
        proposed_artifact_path=proposed_artifact_path,
        proposed_artifact_content=proposed_artifact_content,
        created_at=created_at,
        adapter_enabled=True,
        metadata={
            "provider_c_output_hash": output.output_hash,
            "registry_decision_hash": registry_decision.decision_hash,
            "trust_label": UNTRUSTED_PROVIDER_OUTPUT,
        },
    )
    if candidate.status != PROVIDER_PROPOSER_CANDIDATE_RECORDED:
        raise ProviderRequestFlowBlocked("provider proposal candidate failed closed")
    return candidate


def _require_accepted_registry_decision(
    request: ProviderRequest,
    decision: ProviderRegistryDecision,
) -> None:
    if not isinstance(request, ProviderRequest):
        raise TypeError("request must be a ProviderRequest")
    if not isinstance(decision, ProviderRegistryDecision):
        raise TypeError("registry_decision must be a ProviderRegistryDecision")
    if (
        decision.mock_output_allowed is not True
        or decision.status != MOCK_PROVIDER_REQUEST_ALLOWED
        or decision.request_id != request.request_id
        or decision.request_hash != request.request_hash
        or decision.provider_id != request.provider_id
        or decision.live_call_allowed is not False
    ):
        raise ProviderRequestFlowBlocked(
            "an accepted matching registry decision is required"
        )


def _required_text(value: Any, name: str, *, preserve: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value if preserve else value.strip()


def _required_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be boolean")
    return value


def _full_hash(value: Any, name: str) -> str:
    text = _required_text(value, name).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{name} must be a full SHA-256 hash")
    return text


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
