from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.provider_controlled_flow import (
    NO_ARTIFACT_WRITE,
    NO_EXECUTION,
    REVIEW_REQUIRED,
    ProviderControlledFlowResult,
    ProviderControlledFlowStage,
)
from runtime.provider_critic_review import (
    INERT_PROVIDER_CRITIC_REVIEW,
    ProviderCriticReview,
)
from runtime.provider_live_adapter import (
    LIVE_PROVIDER_ADAPTER_BLOCKED,
    LiveProviderAdapterDecision,
)
from runtime.provider_request_flow import UNTRUSTED_PROVIDER_OUTPUT
from runtime.review_packet_projection import NOT_APPROVED, NOT_DECIDED


PROVIDER_REVIEW_PROJECTION = "PROVIDER_REVIEW_PROJECTION"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
CRITIC_NOT_ATTACHED = "CRITIC_NOT_ATTACHED"
LIVE_ADAPTER_STATUS_NOT_ATTACHED = "LIVE_ADAPTER_STATUS_NOT_ATTACHED"
DEFAULT_OFF_LIVE_ADAPTER = "DEFAULT_OFF_LIVE_ADAPTER"
NO_AUTO_APPROVAL = "NO_AUTO_APPROVAL"
NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE = (
    "NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE"
)


class ProviderReviewProjectionBlocked(ValueError):
    """Raised when the provider review chain contains an authority claim."""


@dataclass(frozen=True)
class ProviderReviewProjectionSection:
    section_label: str
    status: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_label": self.section_label,
            "status": self.status,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ProviderReviewCriticFinding:
    category: str
    severity: str
    message: str
    source: str
    matched_phrases: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
            "matched_phrases": list(self.matched_phrases),
        }


@dataclass(frozen=True)
class ProviderReviewProjection:
    projection_label: str
    projection_id: str
    projection_hash: str
    human_review_projection_id: str
    human_review_projection_hash: str
    review_packet_id: str
    review_packet_hash: str
    provider_id: str
    provider_profile_id: str
    provider_request_summary: Mapping[str, Any]
    registry_decision_summary: Mapping[str, Any]
    provider_output_summary: Mapping[str, Any]
    live_adapter_section: ProviderReviewProjectionSection
    critic_section: ProviderReviewProjectionSection
    provider_output_trust_label: str
    critic_label: str
    critic_findings: tuple[ProviderReviewCriticFinding, ...]
    required_human_action: str
    safety_boundary_summary: tuple[str, ...]
    status: str
    requires_human_review: bool
    approved: bool
    automatic_approval: bool
    authoritative: bool
    gate_eligible: bool
    write_eligible: bool
    execution_occurred: bool
    artifact_write_occurred: bool
    provider_live_call_used: bool
    blocking: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_label": self.projection_label,
            "projection_id": self.projection_id,
            "projection_hash": self.projection_hash,
            "human_review_projection_id": self.human_review_projection_id,
            "human_review_projection_hash": self.human_review_projection_hash,
            "review_packet_id": self.review_packet_id,
            "review_packet_hash": self.review_packet_hash,
            "provider_id": self.provider_id,
            "provider_profile_id": self.provider_profile_id,
            "provider_request_summary": dict(self.provider_request_summary),
            "registry_decision_summary": dict(self.registry_decision_summary),
            "provider_output_summary": dict(self.provider_output_summary),
            "live_adapter_section": self.live_adapter_section.to_dict(),
            "critic_section": self.critic_section.to_dict(),
            "provider_output_trust_label": self.provider_output_trust_label,
            "critic_label": self.critic_label,
            "critic_findings": [
                finding.to_dict() for finding in self.critic_findings
            ],
            "required_human_action": self.required_human_action,
            "safety_boundary_summary": list(self.safety_boundary_summary),
            "status": self.status,
            "requires_human_review": self.requires_human_review,
            "approved": self.approved,
            "automatic_approval": self.automatic_approval,
            "authoritative": self.authoritative,
            "gate_eligible": self.gate_eligible,
            "write_eligible": self.write_eligible,
            "execution_occurred": self.execution_occurred,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_live_call_used": self.provider_live_call_used,
            "blocking": self.blocking,
        }


def build_provider_review_projection(
    *,
    controlled_flow: ProviderControlledFlowResult,
    critic_review: ProviderCriticReview | None = None,
    live_adapter_status: LiveProviderAdapterDecision | None = None,
) -> ProviderReviewProjection:
    _validate_controlled_flow(controlled_flow)
    _validate_critic_review(controlled_flow, critic_review)
    _validate_live_adapter_status(controlled_flow, live_adapter_status)

    output = controlled_flow.provider_output
    human_projection = controlled_flow.local_visible_review
    registry_summary = dict(controlled_flow.registry_decision_summary)
    provider_metadata = dict(output.provider_metadata)
    request_summary = {
        "request_id": controlled_flow.request_id,
        "request_hash": controlled_flow.request_hash,
        "provider_id": controlled_flow.provider_id,
        "purpose": provider_metadata.get("purpose"),
        "caller_label": provider_metadata.get("caller_label"),
        "request_metadata": dict(controlled_flow.request_metadata),
    }
    output_summary = {
        "output_id": output.output_id,
        "output_hash": output.output_hash,
        "model_label": output.model_label,
        "trust_label": UNTRUSTED_PROVIDER_OUTPUT,
        "live_call_used": False,
    }
    live_section = _live_adapter_section(live_adapter_status)
    critic_section, critic_label, critic_findings = _critic_section(critic_review)
    safety_summary = (
        NO_EXECUTION,
        NO_ARTIFACT_WRITE,
        NO_AUTO_APPROVAL,
        NO_LIVE_CALL_UNLESS_EXPLICITLY_ENABLED_IN_FUTURE,
    )
    material = {
        "projection_label": PROVIDER_REVIEW_PROJECTION,
        "human_review_projection_id": human_projection.projection_id,
        "human_review_projection_hash": human_projection.projection_hash,
        "review_packet_id": human_projection.review_packet_id,
        "review_packet_hash": human_projection.review_packet_hash,
        "provider_id": controlled_flow.provider_id,
        "provider_profile_id": controlled_flow.provider_id,
        "provider_request_summary": request_summary,
        "registry_decision_summary": registry_summary,
        "provider_output_summary": output_summary,
        "live_adapter_section": live_section.to_dict(),
        "critic_section": critic_section.to_dict(),
        "provider_output_trust_label": UNTRUSTED_PROVIDER_OUTPUT,
        "critic_label": critic_label,
        "critic_findings": [finding.to_dict() for finding in critic_findings],
        "required_human_action": HUMAN_REVIEW_REQUIRED,
        "safety_boundary_summary": list(safety_summary),
        "status": REVIEW_REQUIRED,
    }
    projection_hash = _stable_hash(material)
    return ProviderReviewProjection(
        projection_label=PROVIDER_REVIEW_PROJECTION,
        projection_id="provider-f-review-projection-" + projection_hash[:24],
        projection_hash=projection_hash,
        human_review_projection_id=human_projection.projection_id,
        human_review_projection_hash=human_projection.projection_hash,
        review_packet_id=human_projection.review_packet_id,
        review_packet_hash=human_projection.review_packet_hash,
        provider_id=controlled_flow.provider_id,
        provider_profile_id=controlled_flow.provider_id,
        provider_request_summary=request_summary,
        registry_decision_summary=registry_summary,
        provider_output_summary=output_summary,
        live_adapter_section=live_section,
        critic_section=critic_section,
        provider_output_trust_label=UNTRUSTED_PROVIDER_OUTPUT,
        critic_label=critic_label,
        critic_findings=critic_findings,
        required_human_action=HUMAN_REVIEW_REQUIRED,
        safety_boundary_summary=safety_summary,
        status=REVIEW_REQUIRED,
        requires_human_review=True,
        approved=False,
        automatic_approval=False,
        authoritative=False,
        gate_eligible=False,
        write_eligible=False,
        execution_occurred=False,
        artifact_write_occurred=False,
        provider_live_call_used=False,
        blocking=True,
    )


def attach_provider_review_to_packet(
    *,
    controlled_flow: ProviderControlledFlowResult,
    critic_review: ProviderCriticReview | None = None,
    live_adapter_status: LiveProviderAdapterDecision | None = None,
) -> ProviderReviewProjection:
    return build_provider_review_projection(
        controlled_flow=controlled_flow,
        critic_review=critic_review,
        live_adapter_status=live_adapter_status,
    )


def _validate_controlled_flow(flow: ProviderControlledFlowResult) -> None:
    if not isinstance(flow, ProviderControlledFlowResult):
        raise ProviderReviewProjectionBlocked(
            "a Provider-D controlled flow result is required"
        )
    if (
        flow.status != REVIEW_REQUIRED
        or flow.stage is not ProviderControlledFlowStage.LOCAL_VISIBLE_REVIEW
        or flow.execution_status != NO_EXECUTION
        or flow.artifact_write_status != NO_ARTIFACT_WRITE
        or flow.trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or flow.requires_human_review is not True
        or flow.approved is not False
        or flow.gate_eligible is not False
        or flow.write_eligible is not False
        or flow.execution_occurred is not False
        or flow.artifact_write_occurred is not False
        or flow.provider_live_call_used is not False
        or flow.blocking is not True
    ):
        raise ProviderReviewProjectionBlocked(
            "controlled flow must remain inert, untrusted, and review-required"
        )
    if (
        flow.provider_output is None
        or flow.registry_decision_summary is None
        or flow.candidate is None
        or flow.proposal_conversion is None
        or flow.review_packet is None
        or flow.local_visible_review is None
    ):
        raise ProviderReviewProjectionBlocked(
            "complete provider and human review context is required"
        )
    output = flow.provider_output
    candidate = flow.candidate
    conversion = flow.proposal_conversion
    packet = flow.review_packet
    human_projection = flow.local_visible_review
    if (
        output.trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or output.live_call_used is not False
        or output.request_id != flow.request_id
        or output.request_hash != flow.request_hash
        or output.provider_id != flow.provider_id
        or dict(output.registry_decision_summary)
        != dict(flow.registry_decision_summary)
        or human_projection.inert is not True
        or human_projection.blocking is not True
        or human_projection.requires_human_review is not True
        or human_projection.human_decision_status != NOT_DECIDED
        or human_projection.approval_status != NOT_APPROVED
        or human_projection.approved is not False
        or human_projection.gate_eligible is not False
        or human_projection.write_eligible is not False
        or human_projection.provider_live_call_permitted is not False
        or human_projection.approval_decision_created is not False
        or human_projection.artifact_write_occurred is not False
        or human_projection.execution_occurred is not False
    ):
        raise ProviderReviewProjectionBlocked(
            "provider output and human review projection must remain inert"
        )
    forbidden_truths = (
        candidate.provider_output_trusted,
        candidate.model_output_trusted,
        candidate.metadata_authority,
        candidate.canonical,
        candidate.live_call_attempted,
        candidate.network_call_attempted,
        candidate.approval_decision_created,
        candidate.durable_handoff_complete,
        candidate.pre_artifact_gate_passed,
        candidate.artifact_write_occurred,
        conversion.provider_output_trusted,
        conversion.model_output_trusted,
        conversion.provider_output_verified,
        conversion.evidence_created,
        conversion.metadata_authority,
        conversion.canonical,
        conversion.approval_decision_created,
        conversion.durable_handoff_complete,
        conversion.pre_artifact_gate_passed,
        conversion.artifact_write_occurred,
        conversion.execution_permitted,
        packet.metadata_authority,
        packet.canonical,
        packet.approval_decision_created,
        packet.durable_handoff_complete,
        packet.pre_artifact_gate_passed,
        packet.artifact_write_occurred,
        human_projection.authoritative,
        human_projection.canonical,
        human_projection.evidence,
        human_projection.provider_output_trusted,
        human_projection.model_output_trusted,
        human_projection.provider_output_verified,
        human_projection.durable_audit_event_created,
    )
    if any(value is not False for value in forbidden_truths):
        raise ProviderReviewProjectionBlocked(
            "provider review chain contains a forbidden authority claim"
        )


def _validate_critic_review(
    flow: ProviderControlledFlowResult,
    review: ProviderCriticReview | None,
) -> None:
    if review is None:
        return
    if not isinstance(review, ProviderCriticReview):
        raise ProviderReviewProjectionBlocked(
            "critic review must be a ProviderCriticReview"
        )
    if (
        review.critic_label != INERT_PROVIDER_CRITIC_REVIEW
        or review.status != REVIEW_REQUIRED
        or review.execution_status != NO_EXECUTION
        or review.artifact_write_status != NO_ARTIFACT_WRITE
        or review.output_trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or review.request_id != flow.request_id
        or review.request_hash != flow.request_hash
        or review.provider_id != flow.provider_id
        or review.provider_output_id != flow.provider_output.output_id
        or review.provider_output_hash != flow.provider_output.output_hash
        or dict(review.registry_decision_summary)
        != dict(flow.registry_decision_summary)
        or review.requires_human_review is not True
        or review.approved is not False
        or review.rejected is not False
        or review.authoritative is not False
        or review.gate_eligible is not False
        or review.write_eligible is not False
        or review.execution_occurred is not False
        or review.artifact_write_occurred is not False
        or review.provider_live_call_used is not False
        or review.blocking is not True
    ):
        raise ProviderReviewProjectionBlocked(
            "critic review must remain inert, matched, and non-authoritative"
        )
    critic_visible = review.local_visible_metadata
    for name in (
        "approved",
        "authoritative",
        "gate_eligible",
        "write_eligible",
        "execution_occurred",
        "artifact_write_occurred",
        "provider_live_call_used",
    ):
        if critic_visible.get(name) is not False:
            raise ProviderReviewProjectionBlocked(
                "critic visible metadata contains a forbidden authority claim"
            )


def _validate_live_adapter_status(
    flow: ProviderControlledFlowResult,
    status: LiveProviderAdapterDecision | None,
) -> None:
    if status is None:
        return
    if not isinstance(status, LiveProviderAdapterDecision):
        raise ProviderReviewProjectionBlocked(
            "live adapter status must be a LiveProviderAdapterDecision"
        )
    if (
        status.status != LIVE_PROVIDER_ADAPTER_BLOCKED
        or status.provider_id != flow.provider_id
        or status.provider_request_id != flow.request_id
        or status.provider_request_hash != flow.request_hash
        or status.registry_decision_summary is None
        or dict(status.registry_decision_summary)
        != dict(flow.registry_decision_summary)
        or status.trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or status.live_call_attempted is not False
        or status.live_call_blocked is not True
        or status.real_provider_response_text is not None
    ):
        raise ProviderReviewProjectionBlocked(
            "live adapter must remain blocked, matched, and without a response"
        )


def _critic_section(
    review: ProviderCriticReview | None,
) -> tuple[
    ProviderReviewProjectionSection,
    str,
    tuple[ProviderReviewCriticFinding, ...],
]:
    if review is None:
        return (
            ProviderReviewProjectionSection(
                section_label="provider_critic",
                status=CRITIC_NOT_ATTACHED,
                details={
                    "critic_label": CRITIC_NOT_ATTACHED,
                    "authoritative": False,
                    "finding_count": 0,
                },
            ),
            CRITIC_NOT_ATTACHED,
            (),
        )
    findings = tuple(
        ProviderReviewCriticFinding(
            category=finding.category,
            severity=finding.severity.value,
            message=finding.summary,
            source=INERT_PROVIDER_CRITIC_REVIEW,
            matched_phrases=finding.matched_phrases,
        )
        for finding in review.findings
    )
    return (
        ProviderReviewProjectionSection(
            section_label="provider_critic",
            status=INERT_PROVIDER_CRITIC_REVIEW,
            details={
                "critic_label": INERT_PROVIDER_CRITIC_REVIEW,
                "critic_review_id": review.critic_review_id,
                "critic_review_hash": review.critic_review_hash,
                "authoritative": False,
                "finding_count": len(findings),
            },
        ),
        INERT_PROVIDER_CRITIC_REVIEW,
        findings,
    )


def _live_adapter_section(
    status: LiveProviderAdapterDecision | None,
) -> ProviderReviewProjectionSection:
    if status is None:
        return ProviderReviewProjectionSection(
            section_label="live_adapter_status",
            status=LIVE_ADAPTER_STATUS_NOT_ATTACHED,
            details={
                "adapter_label": None,
                "live_call_attempted": False,
                "live_call_blocked": None,
                "blocked_reason": "live adapter status was not attached",
            },
        )
    return ProviderReviewProjectionSection(
        section_label="live_adapter_status",
        status=LIVE_PROVIDER_ADAPTER_BLOCKED,
        details={
            "adapter_label": DEFAULT_OFF_LIVE_ADAPTER,
            "decision_id": status.decision_id,
            "decision_hash": status.decision_hash,
            "live_call_attempted": False,
            "live_call_blocked": True,
            "blocked_reason": status.blocked_reason,
            "profile_enabled": status.profile_enabled,
            "network_allowed": status.network_allowed,
        },
    )


def _stable_hash(values: Mapping[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
