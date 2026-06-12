from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.safety.provider_attempt_audit import (
    ProviderAttemptAuditRecord,
    create_blocked_provider_attempt_audit,
)


class CPTProviderAutoSendBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class CPTProviderBoundaryDecision:
    cpt_transform_allowed: bool
    provider_send_allowed: bool
    auto_send_blocked: bool
    human_trigger_required: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cpt_transform_allowed", bool(self.cpt_transform_allowed))
        object.__setattr__(self, "provider_send_allowed", bool(self.provider_send_allowed))
        object.__setattr__(self, "auto_send_blocked", bool(self.auto_send_blocked))
        object.__setattr__(self, "human_trigger_required", bool(self.human_trigger_required))
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a nonempty string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpt_transform_allowed": self.cpt_transform_allowed,
            "provider_send_allowed": self.provider_send_allowed,
            "auto_send_blocked": self.auto_send_blocked,
            "human_trigger_required": self.human_trigger_required,
            "reason": self.reason,
        }


def evaluate_cpt_provider_boundary(
    *,
    auto_send_requested: bool,
    human_triggered: bool,
) -> CPTProviderBoundaryDecision:
    auto_requested = bool(auto_send_requested)
    human_requested = bool(human_triggered)
    if auto_requested:
        return CPTProviderBoundaryDecision(
            cpt_transform_allowed=True,
            provider_send_allowed=False,
            auto_send_blocked=True,
            human_trigger_required=True,
            reason="CPT provider handoff cannot be automatic",
        )
    if not human_requested:
        return CPTProviderBoundaryDecision(
            cpt_transform_allowed=True,
            provider_send_allowed=False,
            auto_send_blocked=False,
            human_trigger_required=True,
            reason="CPT provider handoff requires an explicit human trigger",
        )
    return CPTProviderBoundaryDecision(
        cpt_transform_allowed=True,
        provider_send_allowed=True,
        auto_send_blocked=False,
        human_trigger_required=False,
        reason="CPT provider handoff may proceed only to the blocked provider gateway boundary",
    )


def assert_cpt_does_not_auto_send(
    *,
    auto_send_requested: bool,
    human_triggered: bool,
) -> None:
    decision = evaluate_cpt_provider_boundary(
        auto_send_requested=auto_send_requested,
        human_triggered=human_triggered,
    )
    if decision.auto_send_blocked or not decision.provider_send_allowed:
        raise CPTProviderAutoSendBlockedError(decision.reason)


def build_cpt_blocked_provider_attempt(
    *,
    transformed_prompt: str,
    provider_name: str = "",
    model_name: str = "",
    auto_send_requested: bool = False,
    human_triggered: bool = False,
    notes: str = "",
    known_secrets: list[str] | None = None,
) -> ProviderAttemptAuditRecord:
    if not isinstance(transformed_prompt, str):
        raise TypeError("transformed_prompt must be a string")
    decision = evaluate_cpt_provider_boundary(
        auto_send_requested=auto_send_requested,
        human_triggered=human_triggered,
    )
    return create_blocked_provider_attempt_audit(
        provider_name=provider_name,
        model_name=model_name,
        request_text=transformed_prompt,
        block_reason=decision.reason,
        enabled_flag_present=human_triggered,
        network_allowed=False,
        estimated_tokens=0,
        estimated_cost="0",
        notes=notes,
        known_secrets=known_secrets,
    )
