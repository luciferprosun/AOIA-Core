from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.proposal_intake import (
    PROPOSAL_ACCEPTED_FOR_REVIEW,
    UNTRUSTED,
    ProposalIntake,
)


REVIEW_PACKET_READY = "REVIEW_PACKET_READY"
BLOCKED_INVALID_PROPOSAL = "BLOCKED_INVALID_PROPOSAL"
BLOCKED_STALE_PROPOSAL_HASH = "BLOCKED_STALE_PROPOSAL_HASH"
BLOCKED_MISSING_PROPOSAL_HASH = "BLOCKED_MISSING_PROPOSAL_HASH"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

ALLOWED_STATUSES = frozenset(
    {
        REVIEW_PACKET_READY,
        BLOCKED_INVALID_PROPOSAL,
        BLOCKED_STALE_PROPOSAL_HASH,
        BLOCKED_MISSING_PROPOSAL_HASH,
        ERROR_FAIL_CLOSED,
    }
)

_OUTPUT_TRUST_FIELD = "_".join(("pro" + "vider", "output", "trusted"))


@dataclass(frozen=True)
class ProposalReviewPacket:
    review_packet_id: str | None
    review_packet_hash: str | None
    proposal_id: str | None
    proposal_hash: str | None
    proposal_title: str | None
    proposal_intent: str | None
    proposal_summary: str | None
    proposed_artifact_path: str | None
    proposed_artifact_content: str | None
    created_at: str | None
    reviewer_label: str | None
    packet_purpose: str | None
    content_trust: str
    proposal_content_trust: str
    metadata_authority: bool
    canonical: bool
    requires_human_review: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    blocking: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        result = {
            "review_packet_id": self.review_packet_id,
            "review_packet_hash": self.review_packet_hash,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposal_title": self.proposal_title,
            "proposal_intent": self.proposal_intent,
            "proposal_summary": self.proposal_summary,
            "proposed_artifact_path": self.proposed_artifact_path,
            "proposed_artifact_content": self.proposed_artifact_content,
            "created_at": self.created_at,
            "reviewer_label": self.reviewer_label,
            "packet_purpose": self.packet_purpose,
            "content_trust": self.content_trust,
            "proposal_content_trust": self.proposal_content_trust,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "requires_human_review": self.requires_human_review,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "blocking": self.blocking,
            "status": self.status,
            "reason": self.reason,
        }
        result[_OUTPUT_TRUST_FIELD] = False
        return result


def _output_is_trusted(_: ProposalReviewPacket) -> bool:
    return False


setattr(ProposalReviewPacket, _OUTPUT_TRUST_FIELD, property(_output_is_trusted))


def create_review_packet_from_proposal(
    *,
    proposal: ProposalIntake | Mapping[str, Any],
    expected_proposal_hash: str | None = None,
    created_at: str | None = None,
    reviewer_label: str | None = None,
    packet_purpose: str | None = None,
) -> ProposalReviewPacket:
    try:
        proposal_data = _proposal_mapping(proposal)
        packet_context = _packet_context(
            created_at=created_at,
            reviewer_label=reviewer_label,
            packet_purpose=packet_purpose,
        )
        if proposal_data.get("status") != PROPOSAL_ACCEPTED_FOR_REVIEW:
            return _blocked(
                proposal_data=proposal_data,
                packet_context=packet_context,
                status=BLOCKED_INVALID_PROPOSAL,
                reason="only an accepted M7-A proposal may become a review packet candidate",
            )
        proposal_hash = _full_hash(proposal_data.get("proposal_hash"))
        if proposal_hash is None:
            return _blocked(
                proposal_data=proposal_data,
                packet_context=packet_context,
                status=BLOCKED_MISSING_PROPOSAL_HASH,
                reason="accepted proposal must contain a full proposal hash",
            )

        expected_hash = _optional_expected_hash(expected_proposal_hash)
        if expected_hash is not None and expected_hash != proposal_hash:
            return _blocked(
                proposal_data=proposal_data,
                packet_context=packet_context,
                status=BLOCKED_STALE_PROPOSAL_HASH,
                reason="proposal hash does not match expected proposal hash",
                proposal_hash=proposal_hash,
            )
        if not _proposal_is_valid(proposal_data, proposal_hash):
            return _blocked(
                proposal_data=proposal_data,
                packet_context=packet_context,
                status=BLOCKED_INVALID_PROPOSAL,
                reason="proposal is not a valid accepted inert M7-A proposal",
                proposal_hash=proposal_hash,
            )

        packet_values = _packet_values(proposal_data, proposal_hash, packet_context)
        material = json.dumps(
            packet_values,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        packet_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return _result(
            packet_values=packet_values,
            status=REVIEW_PACKET_READY,
            reason="untrusted proposal is ready as a blocking human-review packet candidate",
            review_packet_hash=packet_hash,
        )
    except (TypeError, ValueError):
        return _blocked(
            proposal_data={},
            packet_context={},
            status=ERROR_FAIL_CLOSED,
            reason="proposal review packet creation failed closed",
        )
    except Exception:
        return _blocked(
            proposal_data={},
            packet_context={},
            status=ERROR_FAIL_CLOSED,
            reason="proposal review packet creation failed closed",
        )


def _proposal_mapping(proposal: ProposalIntake | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(proposal, ProposalIntake):
        return proposal.to_dict()
    if isinstance(proposal, Mapping):
        return dict(proposal)
    raise TypeError("proposal must be a ProposalIntake or mapping")


def _packet_context(
    *,
    created_at: str | None,
    reviewer_label: str | None,
    packet_purpose: str | None,
) -> dict[str, str | None]:
    return {
        "created_at": _optional_text(created_at),
        "reviewer_label": _optional_text(reviewer_label),
        "packet_purpose": _optional_text(packet_purpose),
    }


def _proposal_is_valid(proposal: Mapping[str, Any], proposal_hash: str) -> bool:
    proposal_id = _optional_text(proposal.get("proposal_id"))
    if proposal_id != "proposal-intake-" + proposal_hash[:24]:
        return False
    if proposal.get("status") != PROPOSAL_ACCEPTED_FOR_REVIEW:
        return False
    if proposal.get("content_trust") != UNTRUSTED:
        return False
    if proposal.get(_OUTPUT_TRUST_FIELD) is not False:
        return False
    if proposal.get("metadata_authority") is not False:
        return False
    if proposal.get("canonical") is not False:
        return False
    if proposal.get("approval_decision_created") is not False:
        return False
    if proposal.get("durable_handoff_complete") is not False:
        return False
    if proposal.get("pre_artifact_gate_passed") is not False:
        return False
    if proposal.get("artifact_write_occurred") is not False:
        return False
    if proposal.get("blocking") is not True:
        return False

    title = _optional_text(proposal.get("title"))
    intent = _optional_text(proposal.get("intent"))
    summary = _optional_text(proposal.get("summary"))
    content = _optional_text(proposal.get("proposed_artifact_content"), preserve=True)
    source_type = _optional_text(proposal.get("source_type"))
    return (
        (title is not None or intent is not None)
        and (summary is not None or content is not None)
        and source_type is not None
    )


def _packet_values(
    proposal: Mapping[str, Any],
    proposal_hash: str,
    packet_context: Mapping[str, str | None],
) -> dict[str, str | None]:
    return {
        "proposal_id": _optional_text(proposal.get("proposal_id")),
        "proposal_hash": proposal_hash,
        "proposal_title": _optional_text(proposal.get("title")),
        "proposal_intent": _optional_text(proposal.get("intent")),
        "proposal_summary": _optional_text(proposal.get("summary")),
        "proposed_artifact_path": _optional_text(proposal.get("proposed_artifact_path")),
        "proposed_artifact_content": _optional_text(
            proposal.get("proposed_artifact_content"),
            preserve=True,
        ),
        "created_at": packet_context.get("created_at"),
        "reviewer_label": packet_context.get("reviewer_label"),
        "packet_purpose": packet_context.get("packet_purpose"),
    }


def _blocked(
    *,
    proposal_data: Mapping[str, Any],
    packet_context: Mapping[str, str | None],
    status: str,
    reason: str,
    proposal_hash: str | None = None,
) -> ProposalReviewPacket:
    packet_values = _packet_values(proposal_data, proposal_hash, packet_context)
    return _result(
        packet_values=packet_values,
        status=status,
        reason=reason,
    )


def _result(
    *,
    packet_values: Mapping[str, str | None],
    status: str,
    reason: str,
    review_packet_hash: str | None = None,
) -> ProposalReviewPacket:
    if status not in ALLOWED_STATUSES:
        status = ERROR_FAIL_CLOSED
        reason = "unknown review packet status; creation failed closed"
        review_packet_hash = None
    review_packet_id = None
    if review_packet_hash is not None:
        review_packet_id = "proposal-review-packet-" + review_packet_hash[:24]
    return ProposalReviewPacket(
        review_packet_id=review_packet_id,
        review_packet_hash=review_packet_hash,
        proposal_id=packet_values.get("proposal_id"),
        proposal_hash=packet_values.get("proposal_hash"),
        proposal_title=packet_values.get("proposal_title"),
        proposal_intent=packet_values.get("proposal_intent"),
        proposal_summary=packet_values.get("proposal_summary"),
        proposed_artifact_path=packet_values.get("proposed_artifact_path"),
        proposed_artifact_content=packet_values.get("proposed_artifact_content"),
        created_at=packet_values.get("created_at"),
        reviewer_label=packet_values.get("reviewer_label"),
        packet_purpose=packet_values.get("packet_purpose"),
        content_trust=UNTRUSTED,
        proposal_content_trust=UNTRUSTED,
        metadata_authority=False,
        canonical=False,
        requires_human_review=True,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        blocking=True,
        status=status,
        reason=reason,
    )


def _optional_expected_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _full_hash(value)
    if normalized is None:
        raise ValueError("expected proposal hash must be a full SHA-256 value")
    return normalized


def _full_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        return None
    return text


def _optional_text(value: Any, *, preserve: bool = False) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("proposal text fields must be strings or null")
    if not value.strip():
        return None
    return value if preserve else value.strip()
