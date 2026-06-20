from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from runtime.external_model_candidate_intake import (
    EXTERNAL_MODEL_CANDIDATE_CONVERTED,
    ExternalModelCandidateIntakeResult,
    convert_external_model_candidate_to_proposal,
)
from runtime.proposal_review_packet import (
    REVIEW_PACKET_READY,
    ProposalReviewPacket,
    create_review_packet_from_proposal,
)
from runtime.provider_proposer_adapter import ProviderProposerCandidate
from runtime.provider_request_flow import (
    MOCK_PROVIDER_REQUEST_ALLOWED,
    UNTRUSTED_PROVIDER_OUTPUT,
    MockProviderProposer,
    ProviderRegistryDecision,
    ProviderRequest,
    ProviderRequestFlowBlocked,
    UntrustedProviderOutput,
    convert_untrusted_provider_output_to_candidate,
)
from runtime.review_packet_projection import (
    REVIEW_PACKET_PROJECTION_READY,
    HumanReadableReviewPacketProjection,
    create_human_readable_review_packet_projection,
)


REVIEW_REQUIRED = "REVIEW_REQUIRED"
NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
BLOCKED_REGISTRY_DECISION = "BLOCKED_REGISTRY_DECISION"
BLOCKED_PROVIDER_OUTPUT = "BLOCKED_PROVIDER_OUTPUT"
BLOCKED_PROPOSAL_CONVERSION = "BLOCKED_PROPOSAL_CONVERSION"
BLOCKED_REVIEW_PACKET = "BLOCKED_REVIEW_PACKET"
BLOCKED_REVIEW_PROJECTION = "BLOCKED_REVIEW_PROJECTION"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"


class ProviderControlledFlowStage(str, Enum):
    REQUEST = "REQUEST"
    REGISTRY_DECISION = "REGISTRY_DECISION"
    MOCK_PROVIDER_OUTPUT = "MOCK_PROVIDER_OUTPUT"
    PROPOSAL_CANDIDATE = "PROPOSAL_CANDIDATE"
    PROPOSAL_INTAKE = "PROPOSAL_INTAKE"
    REVIEW_PACKET = "REVIEW_PACKET"
    LOCAL_VISIBLE_REVIEW = "LOCAL_VISIBLE_REVIEW"


@dataclass(frozen=True)
class ProviderControlledFlowResult:
    status: str
    stage: ProviderControlledFlowStage
    execution_status: str
    artifact_write_status: str
    trust_label: str
    request_id: str
    request_hash: str
    provider_id: str
    request_metadata: Mapping[str, Any]
    registry_decision_summary: Mapping[str, Any] | None
    provider_output: UntrustedProviderOutput | None
    candidate: ProviderProposerCandidate | None
    proposal_conversion: ExternalModelCandidateIntakeResult | None
    review_packet: ProposalReviewPacket | None
    local_visible_review: HumanReadableReviewPacketProjection | None
    requires_human_review: bool
    approved: bool
    gate_eligible: bool
    write_eligible: bool
    execution_occurred: bool
    artifact_write_occurred: bool
    provider_live_call_used: bool
    blocking: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stage": self.stage.value,
            "execution_status": self.execution_status,
            "artifact_write_status": self.artifact_write_status,
            "trust_label": self.trust_label,
            "request_id": self.request_id,
            "request_hash": self.request_hash,
            "provider_id": self.provider_id,
            "request_metadata": dict(self.request_metadata),
            "registry_decision_summary": (
                dict(self.registry_decision_summary)
                if self.registry_decision_summary is not None
                else None
            ),
            "provider_output": (
                {
                    "output_id": self.provider_output.output_id,
                    "output_hash": self.provider_output.output_hash,
                    "provider_id": self.provider_output.provider_id,
                    "model_label": self.provider_output.model_label,
                    "request_id": self.provider_output.request_id,
                    "request_hash": self.provider_output.request_hash,
                    "registry_decision_summary": dict(
                        self.provider_output.registry_decision_summary
                    ),
                    "raw_text": self.provider_output.raw_text,
                    "provider_metadata": dict(
                        self.provider_output.provider_metadata
                    ),
                    "trust_label": self.provider_output.trust_label,
                    "live_call_used": self.provider_output.live_call_used,
                }
                if self.provider_output is not None
                else None
            ),
            "candidate": (
                self.candidate.to_dict() if self.candidate is not None else None
            ),
            "proposal_conversion": (
                self.proposal_conversion.to_dict()
                if self.proposal_conversion is not None
                else None
            ),
            "review_packet": (
                self.review_packet.to_dict()
                if self.review_packet is not None
                else None
            ),
            "local_visible_review": (
                self.local_visible_review.to_dict()
                if self.local_visible_review is not None
                else None
            ),
            "requires_human_review": self.requires_human_review,
            "approved": self.approved,
            "gate_eligible": self.gate_eligible,
            "write_eligible": self.write_eligible,
            "execution_occurred": self.execution_occurred,
            "artifact_write_occurred": self.artifact_write_occurred,
            "provider_live_call_used": self.provider_live_call_used,
            "blocking": self.blocking,
            "reason": self.reason,
        }


def run_mock_provider_controlled_flow(
    *,
    request: ProviderRequest,
    registry_decision: ProviderRegistryDecision | None,
    model_label: str,
    mock_response_text: str,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    created_at: str = "2026-06-20T12:36:00Z",
) -> ProviderControlledFlowResult:
    if not isinstance(request, ProviderRequest):
        raise TypeError("request must be a ProviderRequest")
    if not _decision_matches_request(request, registry_decision):
        return _blocked(
            request=request,
            registry_decision=registry_decision,
            stage=ProviderControlledFlowStage.REGISTRY_DECISION,
            status=BLOCKED_REGISTRY_DECISION,
            reason="an accepted matching registry decision is required",
        )

    try:
        proposer = MockProviderProposer(
            model_label=model_label,
            mock_response_text=mock_response_text,
        )
        output = proposer.propose(
            request=request,
            registry_decision=registry_decision,
        )
        if (
            output.trust_label != UNTRUSTED_PROVIDER_OUTPUT
            or output.live_call_used is not False
        ):
            return _blocked(
                request=request,
                registry_decision=registry_decision,
                stage=ProviderControlledFlowStage.MOCK_PROVIDER_OUTPUT,
                status=BLOCKED_PROVIDER_OUTPUT,
                reason="mock provider output violated the inert trust boundary",
            )

        candidate = convert_untrusted_provider_output_to_candidate(
            output=output,
            registry_decision=registry_decision,
            proposed_artifact_path=proposed_artifact_path,
            proposed_artifact_content=proposed_artifact_content,
            created_at=created_at,
        )
        conversion = convert_external_model_candidate_to_proposal(
            candidate=candidate,
            expected_candidate_hash=candidate.candidate_hash,
            created_at=created_at,
        )
        if (
            conversion.status != EXTERNAL_MODEL_CANDIDATE_CONVERTED
            or conversion.proposal is None
        ):
            return _blocked(
                request=request,
                registry_decision=registry_decision,
                stage=ProviderControlledFlowStage.PROPOSAL_INTAKE,
                status=BLOCKED_PROPOSAL_CONVERSION,
                reason=conversion.reason,
                output=output,
                candidate=candidate,
                conversion=conversion,
            )

        packet = create_review_packet_from_proposal(
            proposal=conversion.proposal,
            expected_proposal_hash=conversion.proposal_hash,
            created_at=created_at,
            reviewer_label="local-human-reviewer",
            packet_purpose="Provider-D controlled mock provider review",
        )
        if packet.status != REVIEW_PACKET_READY:
            return _blocked(
                request=request,
                registry_decision=registry_decision,
                stage=ProviderControlledFlowStage.REVIEW_PACKET,
                status=BLOCKED_REVIEW_PACKET,
                reason=packet.reason,
                output=output,
                candidate=candidate,
                conversion=conversion,
                packet=packet,
            )

        projection = create_human_readable_review_packet_projection(
            proposal=conversion.proposal,
            review_packet=packet,
        )
        if projection.status != REVIEW_PACKET_PROJECTION_READY:
            return _blocked(
                request=request,
                registry_decision=registry_decision,
                stage=ProviderControlledFlowStage.LOCAL_VISIBLE_REVIEW,
                status=BLOCKED_REVIEW_PROJECTION,
                reason="human-readable review projection failed closed",
                output=output,
                candidate=candidate,
                conversion=conversion,
                packet=packet,
            )
        return ProviderControlledFlowResult(
            status=REVIEW_REQUIRED,
            stage=ProviderControlledFlowStage.LOCAL_VISIBLE_REVIEW,
            execution_status=NO_EXECUTION,
            artifact_write_status=NO_ARTIFACT_WRITE,
            trust_label=UNTRUSTED_PROVIDER_OUTPUT,
            request_id=request.request_id,
            request_hash=request.request_hash,
            provider_id=request.provider_id,
            request_metadata=request.metadata,
            registry_decision_summary=registry_decision.summary(),
            provider_output=output,
            candidate=candidate,
            proposal_conversion=conversion,
            review_packet=packet,
            local_visible_review=projection,
            requires_human_review=True,
            approved=False,
            gate_eligible=False,
            write_eligible=False,
            execution_occurred=False,
            artifact_write_occurred=False,
            provider_live_call_used=False,
            blocking=True,
            reason="untrusted mock provider output is ready for human review only",
        )
    except (ProviderRequestFlowBlocked, TypeError, ValueError) as error:
        return _blocked(
            request=request,
            registry_decision=registry_decision,
            stage=ProviderControlledFlowStage.MOCK_PROVIDER_OUTPUT,
            status=BLOCKED_PROVIDER_OUTPUT,
            reason=str(error),
        )
    except Exception:
        return _blocked(
            request=request,
            registry_decision=registry_decision,
            stage=ProviderControlledFlowStage.MOCK_PROVIDER_OUTPUT,
            status=ERROR_FAIL_CLOSED,
            reason="controlled mock provider flow failed closed",
        )


def _decision_matches_request(
    request: ProviderRequest,
    decision: ProviderRegistryDecision | None,
) -> bool:
    return bool(
        isinstance(decision, ProviderRegistryDecision)
        and decision.status == MOCK_PROVIDER_REQUEST_ALLOWED
        and decision.mock_output_allowed is True
        and decision.live_call_allowed is False
        and decision.request_id == request.request_id
        and decision.request_hash == request.request_hash
        and decision.provider_id == request.provider_id
    )


def _blocked(
    *,
    request: ProviderRequest,
    registry_decision: ProviderRegistryDecision | None,
    stage: ProviderControlledFlowStage,
    status: str,
    reason: str,
    output: UntrustedProviderOutput | None = None,
    candidate: ProviderProposerCandidate | None = None,
    conversion: ExternalModelCandidateIntakeResult | None = None,
    packet: ProposalReviewPacket | None = None,
) -> ProviderControlledFlowResult:
    return ProviderControlledFlowResult(
        status=status,
        stage=stage,
        execution_status=NO_EXECUTION,
        artifact_write_status=NO_ARTIFACT_WRITE,
        trust_label=UNTRUSTED_PROVIDER_OUTPUT,
        request_id=request.request_id,
        request_hash=request.request_hash,
        provider_id=request.provider_id,
        request_metadata=request.metadata,
        registry_decision_summary=(
            registry_decision.summary()
            if isinstance(registry_decision, ProviderRegistryDecision)
            else None
        ),
        provider_output=output,
        candidate=candidate,
        proposal_conversion=conversion,
        review_packet=packet,
        local_visible_review=None,
        requires_human_review=True,
        approved=False,
        gate_eligible=False,
        write_eligible=False,
        execution_occurred=False,
        artifact_write_occurred=False,
        provider_live_call_used=False,
        blocking=True,
        reason=reason,
    )
