from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from runtime.approval_policy_projection import ApprovalPolicyHumanProjection

from runtime.knowledge_hub_attachment import (
    ReadOnlyKnowledgeAttachment,
    is_read_only_knowledge_attachment,
)
from runtime.proposal_intake import (
    PROPOSAL_ACCEPTED_FOR_REVIEW,
    UNTRUSTED,
    ProposalIntake,
)
from runtime.proposal_review_packet import (
    REVIEW_PACKET_READY,
    ProposalReviewPacket,
)


REVIEW_PACKET_PROJECTION_READY = "REVIEW_PACKET_PROJECTION_READY"
NOT_DECIDED = "NOT_DECIDED"
NOT_APPROVED = "NOT_APPROVED"
AUTHORITY_STATUS_DISPLAY_ONLY = "AUTHORITY_STATUS_DISPLAY_ONLY"
NO_EXECUTION = "NO_EXECUTION"
NO_ARTIFACT_WRITE = "NO_ARTIFACT_WRITE"
NO_PROVIDER_LIVE_CALL = "NO_PROVIDER_LIVE_CALL"
NO_PROVIDER_TRUST_CHANGE = "NO_PROVIDER_TRUST_CHANGE"
NO_GITHUB_ACTION = "NO_GITHUB_ACTION"
NO_CANONICAL_PROMOTION = "NO_CANONICAL_PROMOTION"
REVIEW_PACKET_NOT_AUTHORITY = "REVIEW_PACKET_NOT_AUTHORITY"


class AuthorityStatusProjectionError(ValueError):
    """Raised when optional authority display data violates inert boundaries."""


@dataclass(frozen=True)
class AuthorityStatusDisplay:
    section_name: str
    source_bridge_status: str
    source_evaluation_hash: str
    allowed_as: str
    authority_summary: Mapping[str, bool]
    blocked_capabilities: tuple[str, ...]
    required_next_human_step: str
    final_status: str
    safety_boundaries: tuple[str, ...]
    execution_authority: bool
    artifact_write_authority: bool
    provider_live_call_authority: bool
    provider_trust_authority: bool
    github_authority: bool
    canonical_promotion_authority: bool
    display_only: bool = True
    authoritative: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_name": self.section_name,
            "source_bridge_status": self.source_bridge_status,
            "source_evaluation_hash": self.source_evaluation_hash,
            "allowed_as": self.allowed_as,
            "authority_summary": dict(self.authority_summary),
            "blocked_capabilities": list(self.blocked_capabilities),
            "required_next_human_step": self.required_next_human_step,
            "final_status": self.final_status,
            "safety_boundaries": list(self.safety_boundaries),
            "execution_authority": self.execution_authority,
            "artifact_write_authority": self.artifact_write_authority,
            "provider_live_call_authority": self.provider_live_call_authority,
            "provider_trust_authority": self.provider_trust_authority,
            "github_authority": self.github_authority,
            "canonical_promotion_authority": self.canonical_promotion_authority,
            "display_only": self.display_only,
            "authoritative": self.authoritative,
        }


@dataclass(frozen=True)
class TetradCoreDeltaDisplay:
    tetrad_id: str
    conflicts: tuple[str, ...]
    open_questions: tuple[str, ...]
    read_only: bool = True
    authoritative: bool = False
    can_affect_approval: bool = False
    can_affect_gate: bool = False
    can_affect_write: bool = False
    can_affect_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tetrad_id": self.tetrad_id,
            "conflicts": list(self.conflicts),
            "open_questions": list(self.open_questions),
            "read_only": self.read_only,
            "authoritative": self.authoritative,
            "can_affect_approval": self.can_affect_approval,
            "can_affect_gate": self.can_affect_gate,
            "can_affect_write": self.can_affect_write,
            "can_affect_execution": self.can_affect_execution,
        }


@dataclass(frozen=True)
class KnowledgeContextDisplay:
    attachment_id: str
    title: str
    source_label: str
    content_summary: str
    trust_status: str
    tetrad_ids: tuple[str, ...]
    core_delta: tuple[TetradCoreDeltaDisplay, ...]
    read_only: bool = True
    authoritative: bool = False
    evidence: bool = False
    can_affect_approval: bool = False
    can_affect_gate: bool = False
    can_affect_write: bool = False
    can_affect_execution: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "title": self.title,
            "source_label": self.source_label,
            "content_summary": self.content_summary,
            "trust_status": self.trust_status,
            "tetrad_ids": list(self.tetrad_ids),
            "core_delta": [item.to_dict() for item in self.core_delta],
            "read_only": self.read_only,
            "authoritative": self.authoritative,
            "evidence": self.evidence,
            "can_affect_approval": self.can_affect_approval,
            "can_affect_gate": self.can_affect_gate,
            "can_affect_write": self.can_affect_write,
            "can_affect_execution": self.can_affect_execution,
        }


@dataclass(frozen=True)
class HumanReadableReviewPacketProjection:
    projection_id: str
    projection_hash: str
    review_packet_id: str
    review_packet_hash: str
    proposal_id: str
    proposal_hash: str
    proposal_title: str | None
    proposal_intent: str | None
    proposal_summary: str | None
    proposed_artifact_path: str | None
    proposed_artifact_content: str | None
    proposer_source_type: str
    proposer_source_label: str | None
    trust_status: str
    inert: bool
    blocking: bool
    authoritative: bool
    canonical: bool
    evidence: bool
    provider_output_trusted: bool
    model_output_trusted: bool
    provider_output_verified: bool
    requires_human_review: bool
    human_decision_status: str
    approval_status: str
    approved: bool
    gate_eligible: bool
    write_eligible: bool
    provider_live_call_permitted: bool
    read_only_context: bool
    knowledge_authoritative: bool
    tetrad_authoritative: bool
    context_can_affect_approval: bool
    context_can_affect_gate: bool
    context_can_affect_write: bool
    context_can_affect_execution: bool
    approval_decision_created: bool
    durable_audit_event_created: bool
    artifact_write_occurred: bool
    execution_occurred: bool
    knowledge_context: KnowledgeContextDisplay | None
    status: str
    authority_status: AuthorityStatusDisplay | None = None
    safety_boundaries: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        values = {
            "projection_id": self.projection_id,
            "projection_hash": self.projection_hash,
            "review_packet_id": self.review_packet_id,
            "review_packet_hash": self.review_packet_hash,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposal_title": self.proposal_title,
            "proposal_intent": self.proposal_intent,
            "proposal_summary": self.proposal_summary,
            "proposed_artifact_path": self.proposed_artifact_path,
            "proposed_artifact_content": self.proposed_artifact_content,
            "proposer_source_type": self.proposer_source_type,
            "proposer_source_label": self.proposer_source_label,
            "trust_status": self.trust_status,
            "inert": self.inert,
            "blocking": self.blocking,
            "authoritative": self.authoritative,
            "canonical": self.canonical,
            "evidence": self.evidence,
            "provider_output_trusted": self.provider_output_trusted,
            "model_output_trusted": self.model_output_trusted,
            "provider_output_verified": self.provider_output_verified,
            "requires_human_review": self.requires_human_review,
            "human_decision_status": self.human_decision_status,
            "approval_status": self.approval_status,
            "approved": self.approved,
            "gate_eligible": self.gate_eligible,
            "write_eligible": self.write_eligible,
            "provider_live_call_permitted": self.provider_live_call_permitted,
            "read_only_context": self.read_only_context,
            "knowledge_authoritative": self.knowledge_authoritative,
            "tetrad_authoritative": self.tetrad_authoritative,
            "context_can_affect_approval": self.context_can_affect_approval,
            "context_can_affect_gate": self.context_can_affect_gate,
            "context_can_affect_write": self.context_can_affect_write,
            "context_can_affect_execution": self.context_can_affect_execution,
            "approval_decision_created": self.approval_decision_created,
            "durable_audit_event_created": self.durable_audit_event_created,
            "artifact_write_occurred": self.artifact_write_occurred,
            "execution_occurred": self.execution_occurred,
            "knowledge_context": (
                self.knowledge_context.to_dict()
                if self.knowledge_context is not None
                else None
            ),
            "status": self.status,
        }
        if self.authority_status is not None:
            values["authority_status"] = self.authority_status.to_dict()
            values["safety_boundaries"] = list(self.safety_boundaries)
        return values


def create_human_readable_review_packet_projection(
    *,
    proposal: ProposalIntake,
    review_packet: ProposalReviewPacket,
    knowledge_attachment: ReadOnlyKnowledgeAttachment | None = None,
    authority_projection: ApprovalPolicyHumanProjection | None = None,
) -> HumanReadableReviewPacketProjection:
    _validate_inert_inputs(proposal, review_packet)
    knowledge_context = _knowledge_context(knowledge_attachment)
    authority_status = _authority_status(authority_projection)
    packet_boundaries = (
        _authority_review_packet_boundaries()
        if authority_status is not None
        else ()
    )
    display_values = {
        "review_packet_id": review_packet.review_packet_id,
        "review_packet_hash": review_packet.review_packet_hash,
        "proposal_id": proposal.proposal_id,
        "proposal_hash": proposal.proposal_hash,
        "proposal_title": proposal.title,
        "proposal_intent": proposal.intent,
        "proposal_summary": proposal.summary,
        "proposed_artifact_path": proposal.proposed_artifact_path,
        "proposed_artifact_content": proposal.proposed_artifact_content,
        "proposer_source_type": proposal.source_type,
        "proposer_source_label": proposal.source_label,
        "trust_status": UNTRUSTED,
        "knowledge_context": (
            knowledge_context.to_dict() if knowledge_context is not None else None
        ),
    }
    if authority_status is not None:
        display_values["authority_status"] = authority_status.to_dict()
        display_values["safety_boundaries"] = list(packet_boundaries)
    material = json.dumps(
        display_values,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    projection_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return HumanReadableReviewPacketProjection(
        projection_id="review-packet-projection-" + projection_hash[:24],
        projection_hash=projection_hash,
        review_packet_id=review_packet.review_packet_id,
        review_packet_hash=review_packet.review_packet_hash,
        proposal_id=proposal.proposal_id,
        proposal_hash=proposal.proposal_hash,
        proposal_title=proposal.title,
        proposal_intent=proposal.intent,
        proposal_summary=proposal.summary,
        proposed_artifact_path=proposal.proposed_artifact_path,
        proposed_artifact_content=proposal.proposed_artifact_content,
        proposer_source_type=proposal.source_type,
        proposer_source_label=proposal.source_label,
        trust_status=UNTRUSTED,
        inert=True,
        blocking=True,
        authoritative=False,
        canonical=False,
        evidence=False,
        provider_output_trusted=False,
        model_output_trusted=False,
        provider_output_verified=False,
        requires_human_review=True,
        human_decision_status=NOT_DECIDED,
        approval_status=NOT_APPROVED,
        approved=False,
        gate_eligible=False,
        write_eligible=False,
        provider_live_call_permitted=False,
        read_only_context=True,
        knowledge_authoritative=False,
        tetrad_authoritative=False,
        context_can_affect_approval=False,
        context_can_affect_gate=False,
        context_can_affect_write=False,
        context_can_affect_execution=False,
        approval_decision_created=False,
        durable_audit_event_created=False,
        artifact_write_occurred=False,
        execution_occurred=False,
        knowledge_context=knowledge_context,
        status=REVIEW_PACKET_PROJECTION_READY,
        authority_status=authority_status,
        safety_boundaries=packet_boundaries,
    )


def _validate_inert_inputs(
    proposal: ProposalIntake,
    review_packet: ProposalReviewPacket,
) -> None:
    if not isinstance(proposal, ProposalIntake):
        raise TypeError("proposal must be a ProposalIntake")
    if not isinstance(review_packet, ProposalReviewPacket):
        raise TypeError("review_packet must be a ProposalReviewPacket")
    if proposal.status != PROPOSAL_ACCEPTED_FOR_REVIEW:
        raise ValueError("proposal must be accepted for human review")
    if review_packet.status != REVIEW_PACKET_READY:
        raise ValueError("review packet must be ready for human review")
    if not proposal.proposal_id or not proposal.proposal_hash:
        raise ValueError("proposal identity is required")
    if not review_packet.review_packet_id or not review_packet.review_packet_hash:
        raise ValueError("review packet identity is required")
    if (
        review_packet.proposal_id != proposal.proposal_id
        or review_packet.proposal_hash != proposal.proposal_hash
    ):
        raise ValueError("review packet must be bound to the proposal")
    if (
        proposal.content_trust != UNTRUSTED
        or review_packet.content_trust != UNTRUSTED
        or review_packet.proposal_content_trust != UNTRUSTED
    ):
        raise ValueError("proposal and review packet must remain untrusted")
    unsafe_flags = (
        proposal.metadata_authority,
        proposal.canonical,
        proposal.approval_decision_created,
        proposal.durable_handoff_complete,
        proposal.pre_artifact_gate_passed,
        proposal.artifact_write_occurred,
        review_packet.metadata_authority,
        review_packet.canonical,
        review_packet.approval_decision_created,
        review_packet.durable_handoff_complete,
        review_packet.pre_artifact_gate_passed,
        review_packet.artifact_write_occurred,
    )
    if any(unsafe_flags):
        raise ValueError("authoritative proposal or review packet cannot be projected")
    if proposal.blocking is not True or review_packet.blocking is not True:
        raise ValueError("proposal and review packet must remain blocking")
    if review_packet.requires_human_review is not True:
        raise ValueError("review packet must require human review")
    if not proposal.source_type:
        raise ValueError("proposal source metadata is required")


def _knowledge_context(
    attachment: ReadOnlyKnowledgeAttachment | None,
) -> KnowledgeContextDisplay | None:
    if attachment is None:
        return None
    if not is_read_only_knowledge_attachment(attachment):
        raise ValueError("knowledge attachment must be read-only untrusted context")
    core_delta = tuple(
        TetradCoreDeltaDisplay(
            tetrad_id=record.tetrad_id,
            conflicts=record.core.conflicts,
            open_questions=record.core.open_questions,
        )
        for record in attachment.tetrad_records
    )
    return KnowledgeContextDisplay(
        attachment_id=attachment.attachment_id,
        title=attachment.title,
        source_label=attachment.source_label,
        content_summary=attachment.content_summary,
        trust_status=attachment.trust_status,
        tetrad_ids=tuple(record.tetrad_id for record in attachment.tetrad_records),
        core_delta=core_delta,
    )


def _authority_status(
    projection: ApprovalPolicyHumanProjection | None,
) -> AuthorityStatusDisplay | None:
    if projection is None:
        return None

    # Local import avoids changing the existing provider/review import graph.
    from runtime.approval_policy_projection import (
        APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION,
        APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION,
        FUTURE_MILESTONE_REQUIRED,
        HUMAN_READABLE_AUTHORITY_STATUS_ONLY,
        HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION,
        HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY,
        NOT_ALLOWED,
        NO_ARTIFACT_WRITE as AUTH_NO_ARTIFACT_WRITE,
        NO_CANONICAL_PROMOTION as AUTH_NO_CANONICAL_PROMOTION,
        NO_EXECUTION as AUTH_NO_EXECUTION,
        NO_GITHUB_ACTION as AUTH_NO_GITHUB_ACTION,
        NO_PROVIDER_LIVE_CALL as AUTH_NO_PROVIDER_LIVE_CALL,
        NO_PROVIDER_TRUST_CHANGE as AUTH_NO_PROVIDER_TRUST_CHANGE,
        PROJECTION_NOT_AUTHORITY,
        PROPOSAL_ONLY,
        RECORD_ONLY,
        ApprovalPolicyAllowedAs,
        ApprovalPolicyHumanProjection,
    )

    if not isinstance(projection, ApprovalPolicyHumanProjection):
        raise AuthorityStatusProjectionError(
            "authority_projection must be an ApprovalPolicyHumanProjection"
        )
    expected_authority = {
        "execution_authority": False,
        "artifact_write_authority": False,
        "provider_live_call_authority": False,
        "provider_trust_authority": False,
        "github_authority": False,
        "canonical_promotion_authority": False,
    }
    expected_projection_boundaries = (
        AUTH_NO_EXECUTION,
        AUTH_NO_ARTIFACT_WRITE,
        AUTH_NO_PROVIDER_LIVE_CALL,
        AUTH_NO_PROVIDER_TRUST_CHANGE,
        AUTH_NO_GITHUB_ACTION,
        AUTH_NO_CANONICAL_PROMOTION,
        PROJECTION_NOT_AUTHORITY,
        HUMAN_REVIEW_REQUIRED_BEFORE_ANY_FUTURE_AUTHORITY,
    )
    status_mapping = {
        "ALLOWED_RECORD_ONLY": RECORD_ONLY,
        "ALLOWED_PROPOSAL_ONLY": PROPOSAL_ONLY,
        "DENIED": NOT_ALLOWED,
        "REQUIRES_FUTURE_MILESTONE": FUTURE_MILESTONE_REQUIRED,
    }
    required_blocked_capabilities = {
        "EXECUTION",
        "ARTIFACT_WRITE",
        "PROVIDER_LIVE_CALL",
        "PROVIDER_TRUST_CHANGE",
        "GITHUB_ACTION",
        "CANONICAL_PROMOTION",
    }
    projection_boundaries = tuple(
        item.value if hasattr(item, "value") else item
        for item in projection.safety_boundaries
    )
    if (
        projection.label != APPROVAL_POLICY_HUMAN_REVIEW_PROJECTION
        or projection.schema_version != APPROVAL_POLICY_PROJECTION_SCHEMA_VERSION
        or projection.projection_role != HUMAN_READABLE_AUTHORITY_STATUS_ONLY
        or projection.final_status != HUMAN_REVIEW_PROJECTION_ONLY_NO_EXECUTION
        or not isinstance(projection.allowed_as, ApprovalPolicyAllowedAs)
        or status_mapping.get(projection.source_bridge_status)
        != projection.allowed_as.value
        or dict(projection.authority_summary) != expected_authority
        or not required_blocked_capabilities.issubset(
            set(projection.blocked_capabilities)
        )
        or not projection.required_next_human_step
        or projection_boundaries != expected_projection_boundaries
        or projection.execution_authority is not False
        or projection.artifact_write_authority is not False
        or projection.provider_live_call_authority is not False
        or projection.provider_trust_authority is not False
        or projection.github_authority is not False
        or projection.canonical_promotion_authority is not False
    ):
        raise AuthorityStatusProjectionError(
            "authority projection violates the display-only boundary"
        )
    if (
        not isinstance(projection.source_evaluation_hash, str)
        or len(projection.source_evaluation_hash) != 64
        or any(
            character not in "0123456789abcdef"
            for character in projection.source_evaluation_hash
        )
    ):
        raise AuthorityStatusProjectionError(
            "source evaluation hash must be lowercase SHA-256"
        )
    return AuthorityStatusDisplay(
        section_name="authority_status",
        source_bridge_status=projection.source_bridge_status,
        source_evaluation_hash=projection.source_evaluation_hash,
        allowed_as=projection.allowed_as.value,
        authority_summary=dict(projection.authority_summary),
        blocked_capabilities=tuple(projection.blocked_capabilities),
        required_next_human_step=projection.required_next_human_step,
        final_status=projection.final_status,
        safety_boundaries=projection_boundaries,
        execution_authority=False,
        artifact_write_authority=False,
        provider_live_call_authority=False,
        provider_trust_authority=False,
        github_authority=False,
        canonical_promotion_authority=False,
    )


def _authority_review_packet_boundaries() -> tuple[str, ...]:
    return (
        AUTHORITY_STATUS_DISPLAY_ONLY,
        NO_EXECUTION,
        NO_ARTIFACT_WRITE,
        NO_PROVIDER_LIVE_CALL,
        NO_PROVIDER_TRUST_CHANGE,
        NO_GITHUB_ACTION,
        NO_CANONICAL_PROMOTION,
        REVIEW_PACKET_NOT_AUTHORITY,
    )
