from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from runtime.provider_controlled_flow import (
    NO_ARTIFACT_WRITE,
    NO_EXECUTION,
    REVIEW_REQUIRED,
    ProviderControlledFlowResult,
    ProviderControlledFlowStage,
)
from runtime.provider_proposer_adapter import UNTRUSTED
from runtime.provider_request_flow import (
    MOCK_PROVIDER_REQUEST_ALLOWED,
    UNTRUSTED_PROVIDER_OUTPUT,
)


INERT_PROVIDER_CRITIC_REVIEW = "INERT_PROVIDER_CRITIC_REVIEW"

PROVIDER_OUTPUT_UNTRUSTED = "provider_output_untrusted"
HUMAN_REVIEW_REQUIRED = "human_review_required"
NO_EXECUTION_PERMITTED = "no_execution_permitted"
NO_ARTIFACT_WRITE_PERMITTED = "no_artifact_write_permitted"
REGISTRY_DECISION_REQUIRED = "registry_decision_required"
LIVE_CALL_NOT_USED = "live_call_not_used"
UNSAFE_INSTRUCTION_DETECTED = "unsafe_instruction_detected"
AUTHORITY_CLAIM_DETECTED = "authority_claim_detected"
MISSING_CONTEXT = "missing_context"

_AUTHORITY_PHRASES = ("approved", "human approved")
_UNSAFE_INSTRUCTION_PHRASES = (
    "execute this",
    "write file",
    "ignore safety",
    "bypass",
    "run command",
    "secret",
    "api key",
)


class ProviderCriticReviewBlocked(ValueError):
    """Raised when Provider-E receives anything outside the inert Provider-D boundary."""


class ProviderCriticSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ProviderCriticFinding:
    category: str
    severity: ProviderCriticSeverity
    summary: str
    matched_phrases: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "summary": self.summary,
            "matched_phrases": list(self.matched_phrases),
        }


@dataclass(frozen=True)
class ProviderCriticReview:
    critic_label: str
    critic_review_id: str
    critic_review_hash: str
    status: str
    execution_status: str
    artifact_write_status: str
    output_trust_label: str
    request_id: str
    request_hash: str
    provider_id: str
    provider_output_id: str
    provider_output_hash: str
    model_label: str
    request_metadata: Mapping[str, Any]
    provider_metadata: Mapping[str, Any]
    registry_decision_summary: Mapping[str, Any]
    local_visible_metadata: Mapping[str, Any]
    findings: tuple[ProviderCriticFinding, ...]
    risk_categories: tuple[str, ...]
    requires_human_review: bool
    approved: bool
    rejected: bool
    authoritative: bool
    gate_eligible: bool
    write_eligible: bool
    execution_occurred: bool
    artifact_write_occurred: bool
    provider_live_call_used: bool
    blocking: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "critic_label": self.critic_label,
            "critic_review_id": self.critic_review_id,
            "critic_review_hash": self.critic_review_hash,
            "status": self.status,
            "execution_status": self.execution_status,
            "artifact_write_status": self.artifact_write_status,
            "output_trust_label": self.output_trust_label,
            "request_id": self.request_id,
            "request_hash": self.request_hash,
            "provider_id": self.provider_id,
            "provider_output_id": self.provider_output_id,
            "provider_output_hash": self.provider_output_hash,
            "model_label": self.model_label,
            "request_metadata": dict(self.request_metadata),
            "provider_metadata": dict(self.provider_metadata),
            "registry_decision_summary": dict(self.registry_decision_summary),
            "local_visible_metadata": dict(self.local_visible_metadata),
            "findings": [finding.to_dict() for finding in self.findings],
            "risk_categories": list(self.risk_categories),
            "requires_human_review": self.requires_human_review,
            "approved": self.approved,
            "rejected": self.rejected,
            "authoritative": self.authoritative,
            "gate_eligible": self.gate_eligible,
            "write_eligible": self.write_eligible,
            "execution_occurred": self.execution_occurred,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_live_call_used": self.provider_live_call_used,
            "blocking": self.blocking,
            "reason": self.reason,
        }


def review_provider_controlled_flow(
    controlled_flow: ProviderControlledFlowResult,
) -> ProviderCriticReview:
    _validate_controlled_flow(controlled_flow)

    output = controlled_flow.provider_output
    projection = controlled_flow.local_visible_review
    findings = _critic_findings(controlled_flow)
    risk_categories = tuple(finding.category for finding in findings)
    request_metadata = dict(controlled_flow.request_metadata)
    provider_metadata = dict(output.provider_metadata)
    registry_summary = dict(controlled_flow.registry_decision_summary)
    local_visible_metadata = {
        "critic_label": INERT_PROVIDER_CRITIC_REVIEW,
        "controlled_flow_status": REVIEW_REQUIRED,
        "projection_id": projection.projection_id,
        "projection_hash": projection.projection_hash,
        "provider_output_trust": UNTRUSTED_PROVIDER_OUTPUT,
        "risk_categories": list(risk_categories),
        "requires_human_review": True,
        "approved": False,
        "rejected": False,
        "authoritative": False,
        "gate_eligible": False,
        "write_eligible": False,
        "execution_occurred": False,
        "artifact_write_occurred": False,
        "provider_live_call_used": False,
    }
    material = {
        "critic_label": INERT_PROVIDER_CRITIC_REVIEW,
        "status": REVIEW_REQUIRED,
        "execution_status": NO_EXECUTION,
        "artifact_write_status": NO_ARTIFACT_WRITE,
        "output_trust_label": UNTRUSTED_PROVIDER_OUTPUT,
        "request_id": controlled_flow.request_id,
        "request_hash": controlled_flow.request_hash,
        "provider_id": controlled_flow.provider_id,
        "provider_output_id": output.output_id,
        "provider_output_hash": output.output_hash,
        "model_label": output.model_label,
        "request_metadata": request_metadata,
        "provider_metadata": provider_metadata,
        "registry_decision_summary": registry_summary,
        "local_visible_metadata": local_visible_metadata,
        "findings": [finding.to_dict() for finding in findings],
    }
    review_hash = _stable_hash(material)
    return ProviderCriticReview(
        critic_label=INERT_PROVIDER_CRITIC_REVIEW,
        critic_review_id="provider-e-critic-review-" + review_hash[:24],
        critic_review_hash=review_hash,
        status=REVIEW_REQUIRED,
        execution_status=NO_EXECUTION,
        artifact_write_status=NO_ARTIFACT_WRITE,
        output_trust_label=UNTRUSTED_PROVIDER_OUTPUT,
        request_id=controlled_flow.request_id,
        request_hash=controlled_flow.request_hash,
        provider_id=controlled_flow.provider_id,
        provider_output_id=output.output_id,
        provider_output_hash=output.output_hash,
        model_label=output.model_label,
        request_metadata=request_metadata,
        provider_metadata=provider_metadata,
        registry_decision_summary=registry_summary,
        local_visible_metadata=local_visible_metadata,
        findings=findings,
        risk_categories=risk_categories,
        requires_human_review=True,
        approved=False,
        rejected=False,
        authoritative=False,
        gate_eligible=False,
        write_eligible=False,
        execution_occurred=False,
        artifact_write_occurred=False,
        provider_live_call_used=False,
        blocking=True,
        reason="inert provider critic findings are ready for human review only",
    )


def _validate_controlled_flow(flow: ProviderControlledFlowResult) -> None:
    if not isinstance(flow, ProviderControlledFlowResult):
        raise ProviderCriticReviewBlocked(
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
        raise ProviderCriticReviewBlocked(
            "controlled flow must remain inert, untrusted, and review-required"
        )
    if (
        flow.provider_output is None
        or flow.candidate is None
        or flow.proposal_conversion is None
        or flow.review_packet is None
        or flow.local_visible_review is None
        or flow.registry_decision_summary is None
    ):
        raise ProviderCriticReviewBlocked(
            "complete controlled flow review context is required"
        )

    output = flow.provider_output
    registry = flow.registry_decision_summary
    if (
        output.trust_label != UNTRUSTED_PROVIDER_OUTPUT
        or output.live_call_used is not False
        or output.request_id != flow.request_id
        or output.request_hash != flow.request_hash
        or output.provider_id != flow.provider_id
        or dict(output.registry_decision_summary) != dict(registry)
        or registry.get("status") != MOCK_PROVIDER_REQUEST_ALLOWED
        or registry.get("network_allowed") is not False
        or registry.get("mock_output_allowed") is not True
        or registry.get("live_call_allowed") is not False
    ):
        raise ProviderCriticReviewBlocked(
            "provider output and registry metadata must remain inert and matched"
        )

    candidate = flow.candidate
    conversion = flow.proposal_conversion
    packet = flow.review_packet
    projection = flow.local_visible_review
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
        projection.authoritative,
        projection.canonical,
        projection.evidence,
        projection.provider_output_trusted,
        projection.model_output_trusted,
        projection.provider_output_verified,
        projection.approved,
        projection.gate_eligible,
        projection.write_eligible,
        projection.provider_live_call_permitted,
        projection.knowledge_authoritative,
        projection.tetrad_authoritative,
        projection.context_can_affect_approval,
        projection.context_can_affect_gate,
        projection.context_can_affect_write,
        projection.context_can_affect_execution,
        projection.approval_decision_created,
        projection.durable_audit_event_created,
        projection.artifact_write_occurred,
        projection.execution_occurred,
    )
    if any(value is not False for value in forbidden_truths):
        raise ProviderCriticReviewBlocked(
            "nested controlled flow records contain a forbidden authority claim"
        )
    if (
        candidate.content_trust != UNTRUSTED
        or conversion.content_trust != UNTRUSTED
        or packet.content_trust != UNTRUSTED
        or packet.proposal_content_trust != UNTRUSTED
        or projection.trust_status != UNTRUSTED
    ):
        raise ProviderCriticReviewBlocked(
            "nested controlled flow records must remain untrusted"
        )
    if (
        conversion.requires_human_review is not True
        or packet.requires_human_review is not True
        or packet.blocking is not True
        or projection.inert is not True
        or projection.blocking is not True
        or projection.requires_human_review is not True
    ):
        raise ProviderCriticReviewBlocked(
            "nested controlled flow records must remain blocking and review-required"
        )


def _critic_findings(
    flow: ProviderControlledFlowResult,
) -> tuple[ProviderCriticFinding, ...]:
    findings = [
        ProviderCriticFinding(
            category=PROVIDER_OUTPUT_UNTRUSTED,
            severity=ProviderCriticSeverity.WARNING,
            summary="Provider output remains explicitly untrusted.",
        ),
        ProviderCriticFinding(
            category=HUMAN_REVIEW_REQUIRED,
            severity=ProviderCriticSeverity.WARNING,
            summary="A human reviewer is required before any later decision.",
        ),
        ProviderCriticFinding(
            category=NO_EXECUTION_PERMITTED,
            severity=ProviderCriticSeverity.INFO,
            summary="The controlled flow grants no execution permission.",
        ),
        ProviderCriticFinding(
            category=NO_ARTIFACT_WRITE_PERMITTED,
            severity=ProviderCriticSeverity.INFO,
            summary="The controlled flow grants no artifact-write permission.",
        ),
        ProviderCriticFinding(
            category=REGISTRY_DECISION_REQUIRED,
            severity=ProviderCriticSeverity.INFO,
            summary="The provider output is bound to a matching inert registry decision.",
        ),
        ProviderCriticFinding(
            category=LIVE_CALL_NOT_USED,
            severity=ProviderCriticSeverity.INFO,
            summary="No live provider call was used.",
        ),
    ]
    text = flow.provider_output.raw_text
    authority_phrases = _matched_phrases(text, _AUTHORITY_PHRASES)
    if authority_phrases:
        findings.append(
            ProviderCriticFinding(
                category=AUTHORITY_CLAIM_DETECTED,
                severity=ProviderCriticSeverity.HIGH,
                summary="Provider text contains an inert authority claim.",
                matched_phrases=authority_phrases,
            )
        )
    unsafe_phrases = _matched_phrases(text, _UNSAFE_INSTRUCTION_PHRASES)
    if unsafe_phrases:
        findings.append(
            ProviderCriticFinding(
                category=UNSAFE_INSTRUCTION_DETECTED,
                severity=ProviderCriticSeverity.HIGH,
                summary="Provider text contains unsafe instruction language.",
                matched_phrases=unsafe_phrases,
            )
        )
    projection = flow.local_visible_review
    if (
        not flow.request_metadata
        or not flow.provider_output.provider_metadata
        or (
            projection.proposal_summary is None
            and projection.proposed_artifact_content is None
        )
    ):
        findings.append(
            ProviderCriticFinding(
                category=MISSING_CONTEXT,
                severity=ProviderCriticSeverity.WARNING,
                summary="One or more non-authoritative review context fields are missing.",
            )
        )
    return tuple(findings)


def _matched_phrases(text: str, phrases: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        phrase
        for phrase in phrases
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.IGNORECASE)
    )


def _stable_hash(values: Mapping[str, Any]) -> str:
    material = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
