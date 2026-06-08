from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence


class Chat4ProposalStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    NEEDS_REVISION = "NEEDS_REVISION"
    REJECTED = "REJECTED"
    APPROVED_FOR_MANUAL_ACTION = "APPROVED_FOR_MANUAL_ACTION"
    ARCHIVED = "ARCHIVED"


class Chat4CanonicalStatus(str, Enum):
    NOT_CANONICAL = "NOT_CANONICAL"


class Chat4VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    REJECTED = "REJECTED"


class Chat4HatTarget(str, Enum):
    HAT_001_BASH_SAFETY = "HAT_001_BASH_SAFETY"
    HAT_002_LINUX_RHCSA = "HAT_002_LINUX_RHCSA"
    HAT_003_PYTHON_KNOWLEDGE = "HAT_003_PYTHON_KNOWLEDGE"
    HAT_004_BROWSER_FILE_GOVERNANCE = "HAT_004_BROWSER_FILE_GOVERNANCE"
    UNASSIGNED = "UNASSIGNED"


class Chat4ObjectType(str, Enum):
    MODEL_RESEARCH_PROPOSAL = "MODEL_RESEARCH_PROPOSAL"
    SOURCE_CANDIDATE = "SOURCE_CANDIDATE"
    HAT_KNOWLEDGE_CANDIDATE = "HAT_KNOWLEDGE_CANDIDATE"
    HAT_UPDATE_PROPOSAL = "HAT_UPDATE_PROPOSAL"
    CONTRADICTION_REPORT = "CONTRADICTION_REPORT"
    GAP_REPORT = "GAP_REPORT"
    REVIEWER_DECISION = "REVIEWER_DECISION"
    AUDIT_TRAIL_ENTRY = "AUDIT_TRAIL_ENTRY"


def _enforce_common_inert_invariants(
    status: Chat4ProposalStatus,
    canonical_status: Chat4CanonicalStatus,
    verification_status: Chat4VerificationStatus,
    human_review_required: bool,
    execution_permitted: bool,
    automatic_commit_permitted: bool,
) -> None:
    if status is not Chat4ProposalStatus.DRAFT:
        raise ValueError("status must remain DRAFT")
    if canonical_status is not Chat4CanonicalStatus.NOT_CANONICAL:
        raise ValueError("canonical_status must remain NOT_CANONICAL")
    if verification_status is not Chat4VerificationStatus.UNVERIFIED:
        raise ValueError("verification_status must remain UNVERIFIED")
    if human_review_required is not True:
        raise ValueError("human_review_required must remain True")
    if execution_permitted is not False:
        raise ValueError("execution_permitted must remain False")
    if automatic_commit_permitted is not False:
        raise ValueError("automatic_commit_permitted must remain False")


def _require_nonempty_sequence(name: str, values: Sequence[str]) -> None:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(f"{name} must be a sequence of strings")
    if not values:
        raise ValueError(f"{name} cannot be empty")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"{name} must contain only nonblank strings")


def _require_metadata_mapping(name: str, values: Mapping[str, str]) -> None:
    if not isinstance(values, Mapping):
        raise TypeError(f"{name} must be a mapping")


@dataclass(frozen=True)
class ModelResearchProposal:
    proposal_id: str
    model_name: str
    model_version: str
    hat_target: Chat4HatTarget
    research_question: str
    summary_untrusted: str
    source_candidate_ids: Sequence[str]
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonempty_sequence("source_candidate_ids", self.source_candidate_ids)
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class SourceCandidate:
    source_id: str
    proposal_id: str
    source_type: str
    source_reference: str
    title: str
    captured_utc: str
    capture_method: str
    content_excerpt_redacted: str
    provenance_hash: str
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class HatKnowledgeCandidate:
    candidate_id: str
    hat_target: Chat4HatTarget
    domain_tag: str
    title: str
    inert_content_text: str
    source_ids: Sequence[str]
    model_name: str
    created_utc: str
    duplicate_of_id: str = ""
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonempty_sequence("source_ids", self.source_ids)
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class HatUpdateProposal:
    update_id: str
    target_hat: Chat4HatTarget
    target_record_id: str
    proposed_diff_text: str
    rationale: str
    risk_class: str
    source_ids: Sequence[str]
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonempty_sequence("source_ids", self.source_ids)
        if len(self.proposed_diff_text.splitlines()) > 80:
            raise ValueError("proposed_diff_text cannot exceed 80 lines")
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class ContradictionReport:
    report_id: str
    hat_target: Chat4HatTarget
    record_a_id: str
    record_b_id: str
    contradiction_summary: str
    evidence_excerpt_redacted: str
    severity: str
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class GapReport:
    gap_id: str
    hat_target: Chat4HatTarget
    missing_topic: str
    suggested_source_references: Sequence[str]
    priority: str
    status: Chat4ProposalStatus = Chat4ProposalStatus.DRAFT
    canonical_status: Chat4CanonicalStatus = Chat4CanonicalStatus.NOT_CANONICAL
    verification_status: Chat4VerificationStatus = Chat4VerificationStatus.UNVERIFIED
    human_review_required: bool = True
    execution_permitted: bool = False
    automatic_commit_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonempty_sequence(
            "suggested_source_references", self.suggested_source_references
        )
        _enforce_common_inert_invariants(
            self.status,
            self.canonical_status,
            self.verification_status,
            self.human_review_required,
            self.execution_permitted,
            self.automatic_commit_permitted,
        )


@dataclass(frozen=True)
class ReviewerDecision:
    decision_id: str
    object_type: Chat4ObjectType
    object_id: str
    reviewer_human_id: str
    decision: str
    rationale: str
    timestamp_utc: str
    promotion_allowed: bool = False
    execution_authorized: bool = False
    commit_authorized: bool = False
    human_reviewed: bool = True

    def __post_init__(self) -> None:
        if self.promotion_allowed is not False:
            raise ValueError("promotion_allowed must remain False")
        if self.execution_authorized is not False:
            raise ValueError("execution_authorized must remain False")
        if self.commit_authorized is not False:
            raise ValueError("commit_authorized must remain False")
        if self.human_reviewed is not True:
            raise ValueError("human_reviewed must remain True")


@dataclass(frozen=True)
class AuditTrailEntry:
    entry_id: str
    timestamp_utc: str
    actor_type: str
    actor_id: str
    action: str
    object_type: Chat4ObjectType
    object_id: str
    redacted_payload_summary: str
    local_only: bool = True
    secret_redacted: bool = True
    compliance_claim: str = "NOT_COMPLIANCE_GRADE"
    metadata: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.local_only is not True:
            raise ValueError("local_only must remain True")
        if self.secret_redacted is not True:
            raise ValueError("secret_redacted must remain True")
        if self.compliance_claim != "NOT_COMPLIANCE_GRADE":
            raise ValueError("compliance_claim must remain NOT_COMPLIANCE_GRADE")
        if self.metadata is not None:
            _require_metadata_mapping("metadata", self.metadata)
