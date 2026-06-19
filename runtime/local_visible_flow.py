from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runtime.external_model_candidate_intake import (
    EXTERNAL_MODEL_CANDIDATE_CONVERTED,
    convert_external_model_candidate_to_proposal,
)
from runtime.human_decision_end_to_end_demo import (
    DEMO_COMPLETED,
    LocalApprovalArtifactDemoResult,
    run_local_approval_to_artifact_demo,
)
from runtime.proposal_intake import PROPOSAL_ACCEPTED_FOR_REVIEW, UNTRUSTED
from runtime.proposal_review_packet import (
    REVIEW_PACKET_READY,
    create_review_packet_from_proposal,
)
from runtime.proposer_source_boundary import PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import (
    PROVIDER_PROPOSER_CANDIDATE_RECORDED,
    create_provider_proposer_candidate,
)


FLOW_COMPLETED = "FLOW_COMPLETED"
FLOW_BLOCKED_REJECT = "FLOW_BLOCKED_REJECT"
BLOCKED_CANDIDATE = "BLOCKED_CANDIDATE"
BLOCKED_PROPOSAL = "BLOCKED_PROPOSAL"
BLOCKED_REVIEW_PACKET = "BLOCKED_REVIEW_PACKET"
BLOCKED_APPROVAL_PATH = "BLOCKED_APPROVAL_PATH"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"


@dataclass(frozen=True)
class LocalVisibleFlowResult:
    status: str
    candidate_status: str
    candidate_id: str | None
    candidate_hash: str | None
    proposal_status: str | None
    proposal_id: str | None
    proposal_hash: str | None
    proposal_source_type: str | None
    proposal_source_label: str | None
    review_packet_status: str | None
    review_packet_id: str | None
    review_packet_hash: str | None
    artifact_hash: str | None
    decision: str
    human_decision_captured: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    artifact_path: str | None
    content_trust: str
    provider_output_trusted: bool
    model_output_trusted: bool
    provider_output_verified: bool
    evidence_created: bool
    metadata_authority: bool
    canonical: bool
    execution_occurred: bool
    requires_human_review: bool
    blocking: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate_status": self.candidate_status,
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "proposal_status": self.proposal_status,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposal_source_type": self.proposal_source_type,
            "proposal_source_label": self.proposal_source_label,
            "review_packet_status": self.review_packet_status,
            "review_packet_id": self.review_packet_id,
            "review_packet_hash": self.review_packet_hash,
            "artifact_hash": self.artifact_hash,
            "decision": self.decision,
            "human_decision_captured": self.human_decision_captured,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "artifact_path": self.artifact_path,
            "content_trust": self.content_trust,
            "provider_output_trusted": self.provider_output_trusted,
            "model_output_trusted": self.model_output_trusted,
            "provider_output_verified": self.provider_output_verified,
            "evidence_created": self.evidence_created,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "execution_occurred": self.execution_occurred,
            "requires_human_review": self.requires_human_review,
            "blocking": self.blocking,
            "reason": self.reason,
        }


def run_local_visible_flow(
    *,
    candidate_text: str,
    candidate_source: str,
    human_decision: str,
    workspace_root: str | Path,
    audit_dir: str | Path,
    artifact_relative_path: str = "reports/m7-g-visible-flow.md",
    artifact_content: str | None = None,
    expected_review_packet_hash: str | None = None,
    current_review_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    human_actor: str = "local-human-reviewer",
    metadata: Mapping[str, Any] | None = None,
) -> LocalVisibleFlowResult:
    candidate = create_provider_proposer_candidate(
        provider_label=candidate_source,
        model_label="external-model-candidate",
        raw_provider_output=candidate_text,
        source_type=PROVIDER_CANDIDATE,
        extracted_title="Local visible flow candidate",
        extracted_intent="Present untrusted external candidate data for human review.",
        extracted_summary=candidate_text,
        proposed_artifact_path=artifact_relative_path,
        proposed_artifact_content=(
            candidate_text if artifact_content is None else artifact_content
        ),
        created_at="2026-06-19T00:00:00Z",
        adapter_enabled=True,
        metadata=metadata,
    )
    if candidate.status != PROVIDER_PROPOSER_CANDIDATE_RECORDED:
        return _blocked(
            status=BLOCKED_CANDIDATE,
            candidate_status=candidate.status,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            reason=candidate.reason,
        )

    conversion = convert_external_model_candidate_to_proposal(
        candidate=candidate,
        expected_candidate_hash=candidate.candidate_hash,
        created_at="2026-06-19T00:01:00Z",
    )
    proposal = conversion.proposal
    if (
        conversion.status != EXTERNAL_MODEL_CANDIDATE_CONVERTED
        or proposal is None
        or proposal.status != PROPOSAL_ACCEPTED_FOR_REVIEW
    ):
        return _blocked(
            status=BLOCKED_PROPOSAL,
            candidate_status=candidate.status,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            proposal_status=conversion.status,
            proposal_id=conversion.proposal_id,
            proposal_hash=conversion.proposal_hash,
            reason=conversion.reason,
        )

    packet = create_review_packet_from_proposal(
        proposal=proposal,
        expected_proposal_hash=conversion.proposal_hash,
        created_at="2026-06-19T00:02:00Z",
        reviewer_label=human_actor,
        packet_purpose="M7-G local visible human review flow",
    )
    if packet.status != REVIEW_PACKET_READY or packet.review_packet_hash is None:
        return _blocked(
            status=BLOCKED_REVIEW_PACKET,
            candidate_status=candidate.status,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            proposal_status=proposal.status,
            proposal_id=proposal.proposal_id,
            proposal_hash=proposal.proposal_hash,
            proposal_source_type=proposal.source_type,
            proposal_source_label=proposal.source_label,
            review_packet_status=packet.status,
            review_packet_id=packet.review_packet_id,
            review_packet_hash=packet.review_packet_hash,
            reason=packet.reason,
        )

    content = (
        candidate_text if artifact_content is None else artifact_content
    )
    artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    expected_packet_hash = (
        packet.review_packet_hash
        if expected_review_packet_hash is None
        else expected_review_packet_hash
    )
    approval_flow = run_local_approval_to_artifact_demo(
        workspace_root=workspace_root,
        audit_dir=audit_dir,
        decision=human_decision,
        packet_hash=packet.review_packet_hash,
        artifact_relative_path=artifact_relative_path,
        artifact_content=content,
        expected_packet_hash=expected_packet_hash,
        expected_artifact_hash=(
            artifact_hash
            if expected_artifact_hash is None
            else expected_artifact_hash
        ),
        current_packet_hash=current_review_packet_hash,
        human_actor=human_actor,
        reason="explicit M7-G local visible flow decision",
        metadata=metadata,
    )
    return _completed_or_blocked(
        candidate=candidate,
        conversion=conversion,
        packet=packet,
        approval_flow=approval_flow,
    )


def _completed_or_blocked(
    *,
    candidate: Any,
    conversion: Any,
    packet: Any,
    approval_flow: LocalApprovalArtifactDemoResult,
) -> LocalVisibleFlowResult:
    completed = approval_flow.status == DEMO_COMPLETED
    rejected = approval_flow.decision == "REJECT"
    return LocalVisibleFlowResult(
        status=(
            FLOW_COMPLETED
            if completed
            else FLOW_BLOCKED_REJECT
            if rejected
            else BLOCKED_APPROVAL_PATH
        ),
        candidate_status=candidate.status,
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        proposal_status=conversion.proposal.status,
        proposal_id=conversion.proposal_id,
        proposal_hash=conversion.proposal_hash,
        proposal_source_type=conversion.proposal.source_type,
        proposal_source_label=conversion.proposal.source_label,
        review_packet_status=packet.status,
        review_packet_id=packet.review_packet_id,
        review_packet_hash=packet.review_packet_hash,
        artifact_hash=approval_flow.artifact_hash,
        decision=approval_flow.decision,
        human_decision_captured=approval_flow.capture_created,
        approval_decision_created=approval_flow.approval_decision_created,
        durable_handoff_complete=approval_flow.durable_handoff_complete,
        pre_artifact_gate_passed=approval_flow.pre_artifact_gate_passed,
        artifact_write_occurred=approval_flow.artifact_write_occurred,
        artifact_path=approval_flow.artifact_path,
        content_trust=UNTRUSTED,
        provider_output_trusted=False,
        model_output_trusted=False,
        provider_output_verified=False,
        evidence_created=False,
        metadata_authority=False,
        canonical=False,
        execution_occurred=False,
        requires_human_review=True,
        blocking=approval_flow.blocking,
        reason=approval_flow.reason,
    )


def _blocked(
    *,
    status: str,
    candidate_status: str,
    reason: str,
    candidate_id: str | None = None,
    candidate_hash: str | None = None,
    proposal_status: str | None = None,
    proposal_id: str | None = None,
    proposal_hash: str | None = None,
    proposal_source_type: str | None = None,
    proposal_source_label: str | None = None,
    review_packet_status: str | None = None,
    review_packet_id: str | None = None,
    review_packet_hash: str | None = None,
) -> LocalVisibleFlowResult:
    return LocalVisibleFlowResult(
        status=status,
        candidate_status=candidate_status,
        candidate_id=candidate_id,
        candidate_hash=candidate_hash,
        proposal_status=proposal_status,
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        proposal_source_type=proposal_source_type,
        proposal_source_label=proposal_source_label,
        review_packet_status=review_packet_status,
        review_packet_id=review_packet_id,
        review_packet_hash=review_packet_hash,
        artifact_hash=None,
        decision="BLOCKED",
        human_decision_captured=False,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        artifact_path=None,
        content_trust=UNTRUSTED,
        provider_output_trusted=False,
        model_output_trusted=False,
        provider_output_verified=False,
        evidence_created=False,
        metadata_authority=False,
        canonical=False,
        execution_occurred=False,
        requires_human_review=True,
        blocking=True,
        reason=reason,
    )
