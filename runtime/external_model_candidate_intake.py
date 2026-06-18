from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from runtime.proposal_intake import (
    PROPOSAL_ACCEPTED_FOR_REVIEW,
    UNTRUSTED,
    ProposalIntake,
    create_proposal_intake,
)
from runtime.proposer_source_boundary import MODEL_CANDIDATE, PROVIDER_CANDIDATE
from runtime.provider_proposer_adapter import (
    PROVIDER_PROPOSER_CANDIDATE_RECORDED,
    ProviderProposerCandidate,
)


EXTERNAL_MODEL_CANDIDATE_CONVERTED = "EXTERNAL_MODEL_CANDIDATE_CONVERTED"
BLOCKED_MISSING_CANDIDATE = "BLOCKED_MISSING_CANDIDATE"
BLOCKED_DISABLED_CANDIDATE = "BLOCKED_DISABLED_CANDIDATE"
BLOCKED_MISSING_CANDIDATE_HASH = "BLOCKED_MISSING_CANDIDATE_HASH"
BLOCKED_STALE_CANDIDATE_HASH = "BLOCKED_STALE_CANDIDATE_HASH"
BLOCKED_INVALID_CANDIDATE = "BLOCKED_INVALID_CANDIDATE"
BLOCKED_AUTHORITY_CLAIM = "BLOCKED_AUTHORITY_CLAIM"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"
EXTERNAL_MODEL_CANDIDATE = "EXTERNAL_MODEL_CANDIDATE"

ALLOWED_STATUSES = frozenset(
    {
        EXTERNAL_MODEL_CANDIDATE_CONVERTED,
        BLOCKED_MISSING_CANDIDATE,
        BLOCKED_DISABLED_CANDIDATE,
        BLOCKED_MISSING_CANDIDATE_HASH,
        BLOCKED_STALE_CANDIDATE_HASH,
        BLOCKED_INVALID_CANDIDATE,
        BLOCKED_AUTHORITY_CLAIM,
        ERROR_FAIL_CLOSED,
    }
)
ALLOWED_SOURCE_TYPES = frozenset({PROVIDER_CANDIDATE, MODEL_CANDIDATE})

_AUTHORITY_CLAIM_FIELDS = frozenset(
    {
        "approved",
        "approval_created",
        "approval_decision_created",
        "artifact_write_occurred",
        "artifact_write_permitted",
        "canonical",
        "durable_handoff_complete",
        "evidence_created",
        "evidence_verified",
        "execution_allowed",
        "execution_permitted",
        "execution_triggered",
        "human_review_bypassed",
        "metadata_authority",
        "model_output_trusted",
        "pre_artifact_gate_passed",
        "provider_output_trusted",
        "review_bypassed",
        "trusted",
        "verified",
        "verified_evidence",
    }
)


@dataclass(frozen=True)
class ExternalModelCandidateIntakeResult:
    candidate_id: str | None
    candidate_hash: str | None
    proposal: ProposalIntake | None
    proposal_id: str | None
    proposal_hash: str | None
    content_trust: str
    provider_output_trusted: bool
    model_output_trusted: bool
    provider_output_verified: bool
    evidence_created: bool
    metadata_authority: bool
    canonical: bool
    requires_human_review: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    execution_permitted: bool
    blocking: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "proposal": self.proposal.to_dict() if self.proposal is not None else None,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "content_trust": self.content_trust,
            "provider_output_trusted": self.provider_output_trusted,
            "model_output_trusted": self.model_output_trusted,
            "provider_output_verified": self.provider_output_verified,
            "evidence_created": self.evidence_created,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "requires_human_review": self.requires_human_review,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "execution_permitted": self.execution_permitted,
            "blocking": self.blocking,
            "status": self.status,
            "reason": self.reason,
        }


def convert_external_model_candidate_to_proposal(
    *,
    candidate: ProviderProposerCandidate | Mapping[str, Any] | None,
    expected_candidate_hash: str | None = None,
    created_at: str | None = None,
) -> ExternalModelCandidateIntakeResult:
    if candidate is None:
        return _result(
            candidate_data={},
            status=BLOCKED_MISSING_CANDIDATE,
            reason="external model candidate is required",
        )

    try:
        candidate_data = _candidate_mapping(candidate)
        if candidate_data.get("adapter_enabled") is not True:
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_DISABLED_CANDIDATE,
                reason="disabled adapter candidates cannot enter proposal intake",
            )
        candidate_hash = _full_hash(candidate_data.get("candidate_hash"))
        if candidate_hash is None:
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_MISSING_CANDIDATE_HASH,
                reason="candidate must contain a full stable hash",
            )
        expected_hash = _optional_expected_hash(expected_candidate_hash)
        if expected_hash is not None and expected_hash != candidate_hash:
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_STALE_CANDIDATE_HASH,
                reason="candidate hash does not match expected candidate hash",
                candidate_hash=candidate_hash,
            )
        if _has_authority_claim(candidate_data):
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_AUTHORITY_CLAIM,
                reason="external model candidate contains a forbidden authority claim",
                candidate_hash=candidate_hash,
            )
        if not _candidate_is_valid(candidate_data, candidate_hash):
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_INVALID_CANDIDATE,
                reason="candidate is not a valid inert untrusted M7-D record",
                candidate_hash=candidate_hash,
            )

        proposal = create_proposal_intake(
            title=_optional_text(candidate_data.get("extracted_title")),
            intent=_optional_text(candidate_data.get("extracted_intent")),
            summary=_optional_text(candidate_data.get("extracted_summary")),
            proposed_artifact_path=_optional_text(
                candidate_data.get("proposed_artifact_path")
            ),
            proposed_artifact_content=_optional_text(
                candidate_data.get("proposed_artifact_content"),
                preserve=True,
            ),
            source_type=EXTERNAL_MODEL_CANDIDATE,
            source_label=_optional_text(candidate_data.get("candidate_id")),
            human_actor=None,
            created_at=_optional_text(created_at)
            or _optional_text(candidate_data.get("created_at")),
            metadata={
                "candidate_hash": candidate_hash,
                "candidate_source_type": candidate_data.get("source_type"),
                "provider_label": candidate_data.get("provider_label"),
                "model_label": candidate_data.get("model_label"),
                "raw_external_model_output": candidate_data.get("raw_provider_output"),
                "content_trust": UNTRUSTED,
                "provider_output_trusted": False,
                "model_output_trusted": False,
                "provider_output_verified": False,
                "evidence_created": False,
                "metadata_authority": False,
            },
        )
        if proposal.status != PROPOSAL_ACCEPTED_FOR_REVIEW:
            return _result(
                candidate_data=candidate_data,
                status=BLOCKED_INVALID_CANDIDATE,
                reason="candidate could not form a valid inert proposal intake",
                candidate_hash=candidate_hash,
            )
        return _result(
            candidate_data=candidate_data,
            status=EXTERNAL_MODEL_CANDIDATE_CONVERTED,
            reason="untrusted external model candidate converted for human review",
            candidate_hash=candidate_hash,
            proposal=proposal,
        )
    except (TypeError, ValueError):
        return _result(
            candidate_data={},
            status=BLOCKED_INVALID_CANDIDATE,
            reason="external model candidate contains invalid data",
        )
    except Exception:
        return _result(
            candidate_data={},
            status=ERROR_FAIL_CLOSED,
            reason="external model candidate intake failed closed",
        )


def _candidate_mapping(
    candidate: ProviderProposerCandidate | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(candidate, ProviderProposerCandidate):
        return candidate.to_dict()
    if isinstance(candidate, Mapping):
        return dict(candidate)
    raise TypeError("candidate must be an M7-D candidate or mapping")


def _candidate_is_valid(candidate: Mapping[str, Any], candidate_hash: str) -> bool:
    if candidate.get("candidate_id") != "provider-proposer-candidate-" + candidate_hash[:24]:
        return False
    if candidate.get("status") != PROVIDER_PROPOSER_CANDIDATE_RECORDED:
        return False
    if candidate.get("source_type") not in ALLOWED_SOURCE_TYPES:
        return False
    if candidate.get("content_trust") != UNTRUSTED:
        return False
    if candidate.get("provider_output_trusted") is not False:
        return False
    if candidate.get("model_output_trusted") is not False:
        return False
    if candidate.get("metadata_authority") is not False:
        return False
    if candidate.get("canonical") is not False:
        return False
    if candidate.get("live_call_attempted") is not False:
        return False
    if candidate.get("network_call_attempted") is not False:
        return False
    if candidate.get("proposal_intake_created") is not False:
        return False
    if candidate.get("approval_decision_created") is not False:
        return False
    if candidate.get("durable_handoff_complete") is not False:
        return False
    if candidate.get("pre_artifact_gate_passed") is not False:
        return False
    if candidate.get("artifact_write_occurred") is not False:
        return False
    if candidate.get("blocking") is not True:
        return False
    if candidate.get("raw_provider_output") is None:
        return False

    title = _optional_text(candidate.get("extracted_title"))
    intent = _optional_text(candidate.get("extracted_intent"))
    summary = _optional_text(candidate.get("extracted_summary"))
    content = _optional_text(
        candidate.get("proposed_artifact_content"),
        preserve=True,
    )
    return (title is not None or intent is not None) and (
        summary is not None or content is not None
    )


def _has_authority_claim(candidate: Mapping[str, Any]) -> bool:
    for field in _AUTHORITY_CLAIM_FIELDS:
        if field in candidate and candidate.get(field) not in (False, None):
            return True
    return False


def _optional_expected_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _full_hash(value)
    if normalized is None:
        raise ValueError("expected candidate hash must be a full SHA-256 value")
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
        raise TypeError("candidate text fields must be strings or null")
    if not value.strip():
        return None
    return value if preserve else value.strip()


def _result(
    *,
    candidate_data: Mapping[str, Any],
    status: str,
    reason: str,
    candidate_hash: str | None = None,
    proposal: ProposalIntake | None = None,
) -> ExternalModelCandidateIntakeResult:
    if status not in ALLOWED_STATUSES:
        status = ERROR_FAIL_CLOSED
        reason = "unknown conversion status; external model intake failed closed"
        proposal = None
        candidate_hash = None
    return ExternalModelCandidateIntakeResult(
        candidate_id=_optional_result_text(candidate_data.get("candidate_id")),
        candidate_hash=candidate_hash,
        proposal=proposal,
        proposal_id=proposal.proposal_id if proposal is not None else None,
        proposal_hash=proposal.proposal_hash if proposal is not None else None,
        content_trust=UNTRUSTED,
        provider_output_trusted=False,
        model_output_trusted=False,
        provider_output_verified=False,
        evidence_created=False,
        metadata_authority=False,
        canonical=False,
        requires_human_review=True,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        execution_permitted=False,
        blocking=True,
        status=status,
        reason=reason,
    )


def _optional_result_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
