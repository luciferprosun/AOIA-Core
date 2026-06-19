from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

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

    def to_dict(self) -> dict[str, Any]:
        return {
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


def create_human_readable_review_packet_projection(
    *,
    proposal: ProposalIntake,
    review_packet: ProposalReviewPacket,
    knowledge_attachment: ReadOnlyKnowledgeAttachment | None = None,
) -> HumanReadableReviewPacketProjection:
    _validate_inert_inputs(proposal, review_packet)
    knowledge_context = _knowledge_context(knowledge_attachment)
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
