"""Deterministic, read-only comparison of sanitized Orchestra session evidence.

This module consumes only :class:`OrchestraSessionView`.  It never reads live
provider objects or credentials and cannot invoke a provider, consume a plan,
record a decision, write an artifact, or mutate a gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from runtime.epistemic_orchestra.canonical import (
    EpistemicContractError,
    canonical_json_bytes,
    canonical_sha256,
    exact_text_sha256,
    require_sha256,
)
from runtime.epistemic_orchestra.contracts import JsonContract, NON_AUTHORITATIVE
from runtime.epistemic_orchestra.session_view import (
    AUDIT_EVIDENCE_ONLY_LABEL,
    CRITIC_NON_AUTHORITY_LABEL,
    OrchestraAuditResultView,
    OrchestraCriticResultView,
    OrchestraRoleResultView,
    OrchestraSessionView,
    SESSION_STATES,
    validate_orchestra_session_id,
)


HUMAN_REVIEW_WORKSPACE_SCHEMA_VERSION = "orchestra-human-review-workspace-1a"
RESPONSE_CANDIDATE_SCHEMA_VERSION = "orchestra-response-candidate-view-1a"
RESPONSE_PAIR_COMPARISON_SCHEMA_VERSION = "orchestra-response-pair-comparison-1a"
AGREEMENT_OVERVIEW_SCHEMA_VERSION = "orchestra-agreement-overview-1a"

HUMAN_COMPARISON_WARNING = (
    "HUMAN COMPARISON WORKSPACE — REVIEW ONLY. NO RESPONSE, CONSENSUS, "
    "CRITIC RESULT OR UI ACTION GRANTS APPROVAL, WRITE OR EXECUTION AUTHORITY."
)
DESCRIPTIVE_AGREEMENT_LABEL = (
    "DESCRIPTIVE AGREEMENT ONLY — NOT AN APPROVAL OR CORRECTNESS DETERMINATION"
)

AGREEMENT_STATES = frozenset(
    {
        "NO_COMPARABLE_RESPONSES",
        "ONE_COMPARABLE_RESPONSE",
        "ALL_EXACTLY_EQUAL",
        "PARTIAL_EXACT_MATCH",
        "RESPONSES_DIFFER",
    }
)
PRESENTATION_STATUSES = frozenset(
    {
        "AVAILABLE",
        "TRUNCATED",
        "FAILED",
        "INCOMPLETE",
        "MISSING",
        "WITHHELD_FAIL_CLOSED",
    }
)
EVIDENCE_VALIDITY_STATUSES = frozenset(
    {
        "VALID_NON_AUTHORITATIVE",
        "INVALID_FAIL_CLOSED",
        "FAILED",
        "INCOMPLETE",
    }
)
REDACTION_STATUSES = frozenset(
    {"NOT_REDACTED_OR_SANITIZED", "REDACTED_OR_SANITIZED"}
)
TRUNCATION_STATUSES = frozenset(
    {"NOT_TRUNCATED", "TRUNCATED_FOR_COMPARISON", "NOT_APPLICABLE"}
)

MAXIMUM_COMPARISON_RESPONSE_CHARACTERS = 20_000
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_CODE = re.compile(r"[A-Z][A-Z0-9_:-]{0,127}\Z")
_HORIZONTAL_WHITESPACE = re.compile(r"[ \t\f\v]+")


class OrchestraHumanReviewWorkspaceError(EpistemicContractError):
    """Fail-closed error for malformed comparison presentation evidence."""


def _strict_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise OrchestraHumanReviewWorkspaceError(f"{name} must be boolean")
    return value


def _nonnegative(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OrchestraHumanReviewWorkspaceError(
            f"{name} must be a non-negative integer"
        )
    return value


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise OrchestraHumanReviewWorkspaceError(f"{name} is malformed")
    return value


def _code(name: str, value: object) -> str:
    if not isinstance(value, str) or not _CODE.fullmatch(value):
        raise OrchestraHumanReviewWorkspaceError(f"{name} is malformed")
    return value


def _bounded_text(name: str, value: object, *, maximum: int = 20_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise OrchestraHumanReviewWorkspaceError(
            f"{name} must be bounded non-blank text"
        )
    return value


def _optional_bounded_text(
    name: str,
    value: object,
    *,
    maximum: int = MAXIMUM_COMPARISON_RESPONSE_CHARACTERS,
) -> str | None:
    if value is None:
        return None
    return _bounded_text(name, value, maximum=maximum)


def _optional_sha256(name: str, value: object) -> str | None:
    if value is None:
        return None
    try:
        return require_sha256(name, value)
    except EpistemicContractError as error:
        raise OrchestraHumanReviewWorkspaceError(str(error)) from None


def _hash_tuple(name: str, values: object) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        raise OrchestraHumanReviewWorkspaceError(f"{name} must be a sequence")
    result = tuple(values)
    if len(result) != len(set(result)):
        raise OrchestraHumanReviewWorkspaceError(f"{name} contains duplicates")
    for value in result:
        try:
            require_sha256(name, value)
        except EpistemicContractError as error:
            raise OrchestraHumanReviewWorkspaceError(str(error)) from None
    return result


def _line_tuple(name: str, values: object) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, (tuple, list)):
        raise OrchestraHumanReviewWorkspaceError(f"{name} must be a sequence")
    result = tuple(values)
    if len(result) != len(set(result)) or tuple(sorted(result)) != result:
        raise OrchestraHumanReviewWorkspaceError(
            f"{name} must contain unique deterministically sorted lines"
        )
    for value in result:
        if not isinstance(value, str) or len(value) > MAXIMUM_COMPARISON_RESPONSE_CHARACTERS:
            raise OrchestraHumanReviewWorkspaceError(f"{name} contains invalid text")
    return result


def _ordered_unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _self_hash(value: JsonContract, field_name: str, supplied: str) -> str:
    material = value.to_dict()
    material.pop(field_name)
    expected = canonical_sha256(material)
    if supplied not in ("", expected):
        raise OrchestraHumanReviewWorkspaceError(
            f"{field_name} differs from presentation fields"
        )
    return expected


def _assert_no_authority(value: object) -> None:
    if getattr(value, "authority_status", None) != NON_AUTHORITATIVE:
        raise OrchestraHumanReviewWorkspaceError(
            "comparison authority status must be NON_AUTHORITATIVE"
        )
    for name in (
        "provider_output_is_authority",
        "provider_consensus_is_authority",
        "critic_output_is_authority",
        "audit_output_is_authority",
        "agreement_is_authority",
        "candidate_selection_is_authority",
        "execution_permitted",
        "write_permitted",
        "dispatch_permitted",
        "provider_call_permitted",
        "approval_permitted",
        "gate_mutation_permitted",
        "human_barrier_satisfied",
    ):
        if type(getattr(value, name, None)) is not bool or getattr(value, name):
            raise OrchestraHumanReviewWorkspaceError(f"{name} must be False")
    if getattr(value, "human_review_required", None) is not True:
        raise OrchestraHumanReviewWorkspaceError(
            "comparison presentation must require human review"
        )


def normalize_response_text(value: str) -> str:
    """Normalize layout only; no words are removed, inferred, or rewritten."""

    if not isinstance(value, str):
        raise OrchestraHumanReviewWorkspaceError("response text must be text")
    normalized_lines = [
        _HORIZONTAL_WHITESPACE.sub(" ", line.rstrip(" \t\f\v"))
        for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    while normalized_lines and not normalized_lines[0].strip():
        normalized_lines.pop(0)
    while normalized_lines and not normalized_lines[-1].strip():
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def _line_count(value: str | None) -> int:
    if value is None or value == "":
        return 0
    return len(value.split("\n"))


@dataclass(frozen=True, slots=True)
class OrchestraResponseCandidateView(JsonContract):
    schema_version: str
    candidate_id: str
    candidate_digest: str
    ordering_index: int
    role_identifier: str
    role_display_name: str
    connection_id: str
    provider_type: str
    selected_model: str
    provider_reported_model: str | None
    model_profile_id: str
    invocation_status: str
    response_status: str
    presentation_status: str
    response_text: str | None
    normalized_response_text: str | None
    response_digest: str | None
    presented_response_digest: str | None
    source_response_character_count: int
    presented_response_character_count: int
    presented_response_line_count: int
    usage_metadata_available: bool
    latency_ms: int | None
    redaction_status: str
    truncation_status: str
    evidence_validity_status: str
    evidence_references: tuple[str, ...]
    critic_report_references: tuple[str, ...]
    audit_report_references: tuple[str, ...]
    trust_status: str = "UNTRUSTED"
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    agreement_is_authority: bool = False
    candidate_selection_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != RESPONSE_CANDIDATE_SCHEMA_VERSION:
            raise OrchestraHumanReviewWorkspaceError("candidate schema differs")
        _identifier("candidate_id", self.candidate_id)
        _nonnegative("ordering_index", self.ordering_index)
        for name in (
            "role_identifier",
            "connection_id",
            "provider_type",
            "model_profile_id",
            "invocation_status",
            "response_status",
        ):
            _identifier(name, getattr(self, name))
        _bounded_text("role_display_name", self.role_display_name, maximum=128)
        _bounded_text("selected_model", self.selected_model, maximum=512)
        if self.provider_reported_model is not None:
            _bounded_text(
                "provider_reported_model",
                self.provider_reported_model,
                maximum=512,
            )
        if self.presentation_status not in PRESENTATION_STATUSES:
            raise OrchestraHumanReviewWorkspaceError(
                "candidate presentation status is unsupported"
            )
        if self.evidence_validity_status not in EVIDENCE_VALIDITY_STATUSES:
            raise OrchestraHumanReviewWorkspaceError(
                "candidate evidence status is unsupported"
            )
        if self.redaction_status not in REDACTION_STATUSES:
            raise OrchestraHumanReviewWorkspaceError(
                "candidate redaction status is unsupported"
            )
        if self.truncation_status not in TRUNCATION_STATUSES:
            raise OrchestraHumanReviewWorkspaceError(
                "candidate truncation status is unsupported"
            )
        response = _optional_bounded_text("response_text", self.response_text)
        normalized = _optional_bounded_text(
            "normalized_response_text", self.normalized_response_text
        )
        _optional_sha256("response_digest", self.response_digest)
        _optional_sha256("presented_response_digest", self.presented_response_digest)
        source_count = _nonnegative(
            "source_response_character_count", self.source_response_character_count
        )
        presented_count = _nonnegative(
            "presented_response_character_count",
            self.presented_response_character_count,
        )
        line_count = _nonnegative(
            "presented_response_line_count", self.presented_response_line_count
        )
        if response is None:
            if any(
                value is not None
                for value in (
                    normalized,
                    self.response_digest,
                    self.presented_response_digest,
                )
            ) or source_count or presented_count or line_count:
                raise OrchestraHumanReviewWorkspaceError(
                    "unavailable candidate contains response presentation data"
                )
            if self.truncation_status != "NOT_APPLICABLE":
                raise OrchestraHumanReviewWorkspaceError(
                    "unavailable candidate truncation state differs"
                )
        else:
            if normalized != normalize_response_text(response):
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate normalized response differs"
                )
            if self.presented_response_digest != exact_text_sha256(response):
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate presented response digest differs"
                )
            if self.response_digest is None:
                raise OrchestraHumanReviewWorkspaceError(
                    "available candidate source display digest is missing"
                )
            if presented_count != len(response) or line_count != _line_count(response):
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate response measurements differ"
                )
            if source_count < presented_count:
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate source response is shorter than its presentation"
                )
            truncated = source_count > presented_count
            if truncated != (self.truncation_status == "TRUNCATED_FOR_COMPARISON"):
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate truncation evidence differs"
                )
            expected_status = "TRUNCATED" if truncated else "AVAILABLE"
            if self.presentation_status != expected_status:
                raise OrchestraHumanReviewWorkspaceError(
                    "candidate availability presentation differs"
                )
        _strict_bool("usage_metadata_available", self.usage_metadata_available)
        if self.latency_ms is not None:
            _nonnegative("latency_ms", self.latency_ms)
        object.__setattr__(
            self, "evidence_references", _hash_tuple("evidence_references", self.evidence_references)
        )
        object.__setattr__(
            self,
            "critic_report_references",
            _hash_tuple("critic_report_references", self.critic_report_references),
        )
        object.__setattr__(
            self,
            "audit_report_references",
            _hash_tuple("audit_report_references", self.audit_report_references),
        )
        if self.trust_status != "UNTRUSTED":
            raise OrchestraHumanReviewWorkspaceError(
                "candidate provider result must remain UNTRUSTED"
            )
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "candidate_digest",
            _self_hash(self, "candidate_digest", self.candidate_digest),
        )


@dataclass(frozen=True, slots=True)
class OrchestraResponsePairComparison(JsonContract):
    schema_version: str
    comparison_digest: str
    candidate_a_id: str
    candidate_b_id: str
    candidate_a_digest: str
    candidate_b_digest: str
    candidate_a_ordering_index: int
    candidate_b_ordering_index: int
    comparison_available: bool
    exact_text_equal: bool
    normalized_text_equal: bool
    casefolded_normalized_text_equal: bool
    response_digest_equal: bool
    candidate_a_response_length: int
    candidate_b_response_length: int
    candidate_a_line_count: int
    candidate_b_line_count: int
    common_normalized_lines: tuple[str, ...]
    candidate_a_only_normalized_lines: tuple[str, ...]
    candidate_b_only_normalized_lines: tuple[str, ...]
    candidate_a_missing_response: bool
    candidate_b_missing_response: bool
    candidate_a_truncated: bool
    candidate_b_truncated: bool
    candidate_a_invalid_evidence: bool
    candidate_b_invalid_evidence: bool
    descriptive_only: bool = True
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    agreement_is_authority: bool = False
    candidate_selection_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != RESPONSE_PAIR_COMPARISON_SCHEMA_VERSION:
            raise OrchestraHumanReviewWorkspaceError("pair comparison schema differs")
        _identifier("candidate_a_id", self.candidate_a_id)
        _identifier("candidate_b_id", self.candidate_b_id)
        if self.candidate_a_id == self.candidate_b_id:
            raise OrchestraHumanReviewWorkspaceError(
                "pair comparison requires two distinct candidates"
            )
        require_sha256("candidate_a_digest", self.candidate_a_digest)
        require_sha256("candidate_b_digest", self.candidate_b_digest)
        for name in (
            "candidate_a_ordering_index",
            "candidate_b_ordering_index",
            "candidate_a_response_length",
            "candidate_b_response_length",
            "candidate_a_line_count",
            "candidate_b_line_count",
        ):
            _nonnegative(name, getattr(self, name))
        for name in (
            "comparison_available",
            "exact_text_equal",
            "normalized_text_equal",
            "casefolded_normalized_text_equal",
            "response_digest_equal",
            "candidate_a_missing_response",
            "candidate_b_missing_response",
            "candidate_a_truncated",
            "candidate_b_truncated",
            "candidate_a_invalid_evidence",
            "candidate_b_invalid_evidence",
            "descriptive_only",
        ):
            _strict_bool(name, getattr(self, name))
        if self.descriptive_only is not True:
            raise OrchestraHumanReviewWorkspaceError(
                "pair comparison must remain descriptive only"
            )
        for name in (
            "common_normalized_lines",
            "candidate_a_only_normalized_lines",
            "candidate_b_only_normalized_lines",
        ):
            object.__setattr__(self, name, _line_tuple(name, getattr(self, name)))
        if not self.comparison_available and any(
            (
                self.exact_text_equal,
                self.normalized_text_equal,
                self.casefolded_normalized_text_equal,
                self.response_digest_equal,
            )
        ):
            raise OrchestraHumanReviewWorkspaceError(
                "unavailable comparison cannot claim equality"
            )
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "comparison_digest",
            _self_hash(self, "comparison_digest", self.comparison_digest),
        )


@dataclass(frozen=True, slots=True)
class OrchestraAgreementOverview(JsonContract):
    schema_version: str
    agreement_digest: str
    agreement_state: str
    comparable_candidate_count: int
    exact_match_pair_count: int
    distinct_response_digest_count: int
    presentation_label: str
    descriptive_only: bool = True
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    agreement_is_authority: bool = False
    candidate_selection_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != AGREEMENT_OVERVIEW_SCHEMA_VERSION:
            raise OrchestraHumanReviewWorkspaceError("agreement schema differs")
        if self.agreement_state not in AGREEMENT_STATES:
            raise OrchestraHumanReviewWorkspaceError("agreement state is unsupported")
        comparable = _nonnegative(
            "comparable_candidate_count", self.comparable_candidate_count
        )
        exact_pairs = _nonnegative(
            "exact_match_pair_count", self.exact_match_pair_count
        )
        distinct = _nonnegative(
            "distinct_response_digest_count", self.distinct_response_digest_count
        )
        maximum_pairs = comparable * (comparable - 1) // 2
        if exact_pairs > maximum_pairs or distinct > comparable:
            raise OrchestraHumanReviewWorkspaceError(
                "agreement counts are inconsistent"
            )
        if self.presentation_label != DESCRIPTIVE_AGREEMENT_LABEL:
            raise OrchestraHumanReviewWorkspaceError("agreement label differs")
        if self.descriptive_only is not True:
            raise OrchestraHumanReviewWorkspaceError(
                "agreement overview must remain descriptive only"
            )
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "agreement_digest",
            _self_hash(self, "agreement_digest", self.agreement_digest),
        )


@dataclass(frozen=True, slots=True)
class OrchestraHumanReviewWorkspace(JsonContract):
    schema_version: str
    comparison_snapshot_digest: str
    session_id: str
    session_state: str
    session_digest: str
    created_at_epoch: int
    configured_role_count: int
    completed_response_count: int
    failed_response_count: int
    incomplete_response_count: int
    withheld_response_count: int
    valid_evidence_candidate_count: int
    invalid_evidence_candidate_count: int
    redacted_candidate_count: int
    truncated_candidate_count: int
    evidence_status_summary: tuple[str, ...]
    candidates: tuple[OrchestraResponseCandidateView, ...]
    pair_comparisons: tuple[OrchestraResponsePairComparison, ...]
    agreement_overview: OrchestraAgreementOverview
    critic_results: tuple[OrchestraCriticResultView, ...]
    audit_result: OrchestraAuditResultView
    critic_presentation_label: str
    audit_presentation_label: str
    human_comparison_warning: str
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    agreement_is_authority: bool = False
    candidate_selection_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != HUMAN_REVIEW_WORKSPACE_SCHEMA_VERSION:
            raise OrchestraHumanReviewWorkspaceError("workspace schema differs")
        try:
            validate_orchestra_session_id(self.session_id)
            require_sha256("session_digest", self.session_digest)
        except EpistemicContractError as error:
            raise OrchestraHumanReviewWorkspaceError(str(error)) from None
        if self.session_state not in SESSION_STATES:
            raise OrchestraHumanReviewWorkspaceError(
                "workspace session state is unsupported"
            )
        if (
            isinstance(self.created_at_epoch, bool)
            or not isinstance(self.created_at_epoch, int)
            or self.created_at_epoch <= 0
        ):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace creation timestamp must be a positive integer epoch"
            )
        counts = {
            name: _nonnegative(name, getattr(self, name))
            for name in (
                "configured_role_count",
                "completed_response_count",
                "failed_response_count",
                "incomplete_response_count",
                "withheld_response_count",
                "valid_evidence_candidate_count",
                "invalid_evidence_candidate_count",
                "redacted_candidate_count",
                "truncated_candidate_count",
            )
        }
        candidates = tuple(self.candidates)
        if any(not isinstance(item, OrchestraResponseCandidateView) for item in candidates):
            raise OrchestraHumanReviewWorkspaceError("workspace candidates are malformed")
        if tuple(item.ordering_index for item in candidates) != tuple(range(len(candidates))):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace candidate ordering is not deterministic"
            )
        if len({item.candidate_id for item in candidates}) != len(candidates):
            raise OrchestraHumanReviewWorkspaceError("workspace candidate IDs differ")
        if counts["configured_role_count"] != len(candidates):
            raise OrchestraHumanReviewWorkspaceError("workspace role count differs")
        if (
            counts["completed_response_count"]
            + counts["failed_response_count"]
            + counts["incomplete_response_count"]
            != len(candidates)
        ):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace lifecycle counts differ"
            )
        expected_counts = {
            "completed_response_count": sum(
                item.invocation_status == "COMPLETED" for item in candidates
            ),
            "failed_response_count": sum(
                item.invocation_status == "FAILED" for item in candidates
            ),
            "withheld_response_count": sum(
                item.presentation_status == "WITHHELD_FAIL_CLOSED"
                for item in candidates
            ),
            "valid_evidence_candidate_count": sum(
                item.evidence_validity_status == "VALID_NON_AUTHORITATIVE"
                for item in candidates
            ),
            "invalid_evidence_candidate_count": sum(
                item.evidence_validity_status == "INVALID_FAIL_CLOSED"
                for item in candidates
            ),
            "redacted_candidate_count": sum(
                item.redaction_status == "REDACTED_OR_SANITIZED"
                for item in candidates
            ),
            "truncated_candidate_count": sum(
                item.truncation_status == "TRUNCATED_FOR_COMPARISON"
                for item in candidates
            ),
        }
        expected_counts["incomplete_response_count"] = (
            len(candidates)
            - expected_counts["completed_response_count"]
            - expected_counts["failed_response_count"]
        )
        for name, expected in expected_counts.items():
            if counts[name] != expected:
                raise OrchestraHumanReviewWorkspaceError(
                    f"workspace {name} differs from candidates"
                )
        object.__setattr__(self, "candidates", candidates)
        comparisons = tuple(self.pair_comparisons)
        if any(
            not isinstance(item, OrchestraResponsePairComparison)
            for item in comparisons
        ):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace pair comparisons are malformed"
            )
        expected_pairs = tuple(
            (left.candidate_id, right.candidate_id)
            for left in candidates
            for right in candidates
            if left.candidate_id != right.candidate_id
        )
        if tuple(
            (item.candidate_a_id, item.candidate_b_id) for item in comparisons
        ) != expected_pairs:
            raise OrchestraHumanReviewWorkspaceError(
                "workspace pair comparison ordering differs"
            )
        expected_comparisons = tuple(
            compare_response_candidates(left, right)
            for left in candidates
            for right in candidates
            if left.candidate_id != right.candidate_id
        )
        if comparisons != expected_comparisons:
            raise OrchestraHumanReviewWorkspaceError(
                "workspace pair comparison evidence differs"
            )
        object.__setattr__(self, "pair_comparisons", comparisons)
        if not isinstance(self.agreement_overview, OrchestraAgreementOverview):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace agreement overview is malformed"
            )
        if self.agreement_overview != build_agreement_overview(candidates):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace agreement overview differs from candidates"
            )
        critics = tuple(self.critic_results)
        if any(not isinstance(item, OrchestraCriticResultView) for item in critics):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace critic evidence is malformed"
            )
        object.__setattr__(self, "critic_results", critics)
        if not isinstance(self.audit_result, OrchestraAuditResultView):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace audit evidence is malformed"
            )
        statuses = tuple(self.evidence_status_summary)
        if not statuses or len(statuses) != len(set(statuses)):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace evidence summary is malformed"
            )
        for status in statuses:
            _code("evidence_status_summary", status)
        if statuses[0] not in {
            "FAIL_CLOSED",
            "INCOMPLETE",
            "VALID_NON_AUTHORITATIVE",
        }:
            raise OrchestraHumanReviewWorkspaceError(
                "workspace source evidence status is unsupported"
            )
        expected_statuses = [statuses[0]]
        if counts["withheld_response_count"]:
            expected_statuses.append("RESPONSES_WITHHELD_FAIL_CLOSED")
        if counts["failed_response_count"]:
            expected_statuses.append("PROVIDER_FAILURES_PRESENT")
        if counts["incomplete_response_count"]:
            expected_statuses.append("INCOMPLETE_ROLES_PRESENT")
        if counts["redacted_candidate_count"]:
            expected_statuses.append("REDACTION_OR_SANITIZATION_PRESENT")
        if counts["truncated_candidate_count"]:
            expected_statuses.append("COMPARISON_TRUNCATION_PRESENT")
        if statuses != tuple(expected_statuses):
            raise OrchestraHumanReviewWorkspaceError(
                "workspace evidence summary differs from candidates"
            )
        object.__setattr__(self, "evidence_status_summary", statuses)
        if self.critic_presentation_label != CRITIC_NON_AUTHORITY_LABEL:
            raise OrchestraHumanReviewWorkspaceError("critic label differs")
        if self.audit_presentation_label != AUDIT_EVIDENCE_ONLY_LABEL:
            raise OrchestraHumanReviewWorkspaceError("audit label differs")
        if self.human_comparison_warning != HUMAN_COMPARISON_WARNING:
            raise OrchestraHumanReviewWorkspaceError("human comparison warning differs")
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "comparison_snapshot_digest",
            _self_hash(
                self,
                "comparison_snapshot_digest",
                self.comparison_snapshot_digest,
            ),
        )


_ROLE_DISPLAY_NAMES = {
    "MAIN": "Main response",
    "CRITIC": "Critic response",
    "AUDITOR": "Auditor response",
    "SYNTHESIZER": "Synthesizer draft",
}


def _candidate_references(
    role: OrchestraRoleResultView,
    *,
    critics: tuple[OrchestraCriticResultView, ...],
    audit: OrchestraAuditResultView,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    critic_references: list[str] = []
    for critic in critics:
        if critic.ordering_index != role.ordering_index:
            continue
        if critic.report_digest is not None:
            critic_references.append(critic.report_digest)
        critic_references.extend(critic.evidence_references)
    audit_references = [audit.audit_digest, *audit.evidence_references]
    return _ordered_unique(critic_references), _ordered_unique(audit_references)


def build_response_candidate_views(
    session_view: OrchestraSessionView,
) -> tuple[OrchestraResponseCandidateView, ...]:
    """Project every role into a bounded candidate without dropping failures."""

    if not isinstance(session_view, OrchestraSessionView):
        raise OrchestraHumanReviewWorkspaceError("OrchestraSessionView is required")
    candidates: list[OrchestraResponseCandidateView] = []
    critics = tuple(session_view.critic_results)
    audit = session_view.audit_result
    for role in sorted(session_view.role_results, key=lambda item: item.ordering_index):
        invalid = (
            session_view.evidence_status == "FAIL_CLOSED"
            or role.invocation_status == "EVIDENCE_MISMATCH"
            or role.response_status == "EVIDENCE_MISMATCH"
        )
        source_response = role.redacted_provider_response
        source_digest = role.display_response_digest
        response: str | None = None
        normalized: str | None = None
        presented_digest: str | None = None
        source_count = 0
        presented_count = 0
        presented_lines = 0
        truncation_status = "NOT_APPLICABLE"
        if invalid:
            presentation_status = "WITHHELD_FAIL_CLOSED"
            evidence_status = "INVALID_FAIL_CLOSED"
        elif role.invocation_status == "FAILED":
            presentation_status = "FAILED"
            evidence_status = "FAILED"
        elif source_response is None or source_digest is None:
            presentation_status = (
                "MISSING"
                if role.invocation_status == "COMPLETED"
                else "INCOMPLETE"
            )
            evidence_status = "INCOMPLETE"
        else:
            source_count = len(source_response)
            response = source_response[:MAXIMUM_COMPARISON_RESPONSE_CHARACTERS]
            presented_count = len(response)
            normalized = normalize_response_text(response)
            presented_lines = _line_count(response)
            presented_digest = exact_text_sha256(response)
            if source_count > presented_count:
                presentation_status = "TRUNCATED"
                truncation_status = "TRUNCATED_FOR_COMPARISON"
            else:
                presentation_status = "AVAILABLE"
                truncation_status = "NOT_TRUNCATED"
            evidence_status = "VALID_NON_AUTHORITATIVE"
        critic_references, audit_references = _candidate_references(
            role,
            critics=critics,
            audit=audit,
        )
        candidate = OrchestraResponseCandidateView(
            schema_version=RESPONSE_CANDIDATE_SCHEMA_VERSION,
            candidate_id=f"role-{role.ordering_index}-{role.operator_role.lower()}",
            candidate_digest="",
            ordering_index=role.ordering_index,
            role_identifier=role.operator_role,
            role_display_name=_ROLE_DISPLAY_NAMES[role.operator_role],
            connection_id=role.connection_id,
            provider_type=role.provider_type,
            selected_model=role.selected_model,
            provider_reported_model=role.provider_reported_model,
            model_profile_id=role.model_profile_id,
            invocation_status=role.invocation_status,
            response_status=role.response_status,
            presentation_status=presentation_status,
            response_text=response,
            normalized_response_text=normalized,
            response_digest=source_digest if response is not None else None,
            presented_response_digest=presented_digest,
            source_response_character_count=source_count,
            presented_response_character_count=presented_count,
            presented_response_line_count=presented_lines,
            usage_metadata_available=role.usage_metadata_available,
            latency_ms=role.latency_ms,
            redaction_status=(
                "REDACTED_OR_SANITIZED"
                if role.redaction_or_sanitization_applied
                else "NOT_REDACTED_OR_SANITIZED"
            ),
            truncation_status=truncation_status,
            evidence_validity_status=evidence_status,
            evidence_references=role.evidence_references,
            critic_report_references=critic_references,
            audit_report_references=audit_references,
        )
        candidates.append(candidate)
    return tuple(candidates)


def _normalized_line_set(value: str | None) -> set[str]:
    if value is None:
        return set()
    return {line for line in value.split("\n") if line != ""}


def compare_response_candidates(
    candidate_a: OrchestraResponseCandidateView,
    candidate_b: OrchestraResponseCandidateView,
) -> OrchestraResponsePairComparison:
    """Return non-semantic, orientation-explicit comparison metadata."""

    if not isinstance(candidate_a, OrchestraResponseCandidateView) or not isinstance(
        candidate_b, OrchestraResponseCandidateView
    ):
        raise OrchestraHumanReviewWorkspaceError(
            "two OrchestraResponseCandidateView values are required"
        )
    if candidate_a.candidate_id == candidate_b.candidate_id:
        raise OrchestraHumanReviewWorkspaceError(
            "pair comparison requires two distinct candidates"
        )
    response_a = candidate_a.response_text
    response_b = candidate_b.response_text
    normalized_a = candidate_a.normalized_response_text
    normalized_b = candidate_b.normalized_response_text
    available = (
        response_a is not None
        and response_b is not None
        and candidate_a.evidence_validity_status == "VALID_NON_AUTHORITATIVE"
        and candidate_b.evidence_validity_status == "VALID_NON_AUTHORITATIVE"
    )
    exact_equal = bool(available and response_a == response_b)
    normalized_equal = bool(available and normalized_a == normalized_b)
    casefolded_equal = bool(
        available
        and normalized_a is not None
        and normalized_b is not None
        and normalized_a.casefold() == normalized_b.casefold()
    )
    digest_equal = bool(
        available
        and candidate_a.response_digest is not None
        and candidate_a.response_digest == candidate_b.response_digest
    )
    lines_a = _normalized_line_set(normalized_a) if available else set()
    lines_b = _normalized_line_set(normalized_b) if available else set()
    return OrchestraResponsePairComparison(
        schema_version=RESPONSE_PAIR_COMPARISON_SCHEMA_VERSION,
        comparison_digest="",
        candidate_a_id=candidate_a.candidate_id,
        candidate_b_id=candidate_b.candidate_id,
        candidate_a_digest=candidate_a.candidate_digest,
        candidate_b_digest=candidate_b.candidate_digest,
        candidate_a_ordering_index=candidate_a.ordering_index,
        candidate_b_ordering_index=candidate_b.ordering_index,
        comparison_available=available,
        exact_text_equal=exact_equal,
        normalized_text_equal=normalized_equal,
        casefolded_normalized_text_equal=casefolded_equal,
        response_digest_equal=digest_equal,
        candidate_a_response_length=len(response_a) if response_a is not None else 0,
        candidate_b_response_length=len(response_b) if response_b is not None else 0,
        candidate_a_line_count=_line_count(response_a),
        candidate_b_line_count=_line_count(response_b),
        common_normalized_lines=tuple(sorted(lines_a & lines_b)),
        candidate_a_only_normalized_lines=tuple(sorted(lines_a - lines_b)),
        candidate_b_only_normalized_lines=tuple(sorted(lines_b - lines_a)),
        candidate_a_missing_response=response_a is None,
        candidate_b_missing_response=response_b is None,
        candidate_a_truncated=(
            candidate_a.truncation_status == "TRUNCATED_FOR_COMPARISON"
        ),
        candidate_b_truncated=(
            candidate_b.truncation_status == "TRUNCATED_FOR_COMPARISON"
        ),
        candidate_a_invalid_evidence=(
            candidate_a.evidence_validity_status == "INVALID_FAIL_CLOSED"
        ),
        candidate_b_invalid_evidence=(
            candidate_b.evidence_validity_status == "INVALID_FAIL_CLOSED"
        ),
    )


def build_agreement_overview(
    candidates: tuple[OrchestraResponseCandidateView, ...] | list[OrchestraResponseCandidateView],
) -> OrchestraAgreementOverview:
    """Summarize exact equality without ranking, correctness, or approval."""

    if isinstance(candidates, str) or not isinstance(candidates, (tuple, list)):
        raise OrchestraHumanReviewWorkspaceError("candidate collection is required")
    ordered = tuple(candidates)
    if any(not isinstance(item, OrchestraResponseCandidateView) for item in ordered):
        raise OrchestraHumanReviewWorkspaceError("candidate collection is malformed")
    comparable = tuple(
        item
        for item in ordered
        if item.response_text is not None
        and item.evidence_validity_status == "VALID_NON_AUTHORITATIVE"
    )
    exact_pairs = sum(
        left.response_text == right.response_text
        for index, left in enumerate(comparable)
        for right in comparable[index + 1 :]
    )
    distinct_digests = len(
        {
            item.response_digest
            for item in comparable
            if item.response_digest is not None
        }
    )
    if not comparable:
        state = "NO_COMPARABLE_RESPONSES"
    elif len(comparable) == 1:
        state = "ONE_COMPARABLE_RESPONSE"
    elif exact_pairs == len(comparable) * (len(comparable) - 1) // 2:
        state = "ALL_EXACTLY_EQUAL"
    elif exact_pairs:
        state = "PARTIAL_EXACT_MATCH"
    else:
        state = "RESPONSES_DIFFER"
    return OrchestraAgreementOverview(
        schema_version=AGREEMENT_OVERVIEW_SCHEMA_VERSION,
        agreement_digest="",
        agreement_state=state,
        comparable_candidate_count=len(comparable),
        exact_match_pair_count=exact_pairs,
        distinct_response_digest_count=distinct_digests,
        presentation_label=DESCRIPTIVE_AGREEMENT_LABEL,
    )


def build_orchestra_human_review_workspace(
    session_view: OrchestraSessionView,
) -> OrchestraHumanReviewWorkspace:
    """Build one immutable workspace solely from a validated sanitized view."""

    if not isinstance(session_view, OrchestraSessionView):
        raise OrchestraHumanReviewWorkspaceError("OrchestraSessionView is required")
    candidates = build_response_candidate_views(session_view)
    comparisons = tuple(
        compare_response_candidates(left, right)
        for left in candidates
        for right in candidates
        if left.candidate_id != right.candidate_id
    )
    completed = sum(item.invocation_status == "COMPLETED" for item in candidates)
    failed = sum(item.invocation_status == "FAILED" for item in candidates)
    incomplete = len(candidates) - completed - failed
    withheld = sum(
        item.presentation_status == "WITHHELD_FAIL_CLOSED" for item in candidates
    )
    valid = sum(
        item.evidence_validity_status == "VALID_NON_AUTHORITATIVE"
        for item in candidates
    )
    invalid = sum(
        item.evidence_validity_status == "INVALID_FAIL_CLOSED"
        for item in candidates
    )
    redacted = sum(
        item.redaction_status == "REDACTED_OR_SANITIZED" for item in candidates
    )
    truncated = sum(
        item.truncation_status == "TRUNCATED_FOR_COMPARISON"
        for item in candidates
    )
    summary = [session_view.evidence_status]
    if withheld:
        summary.append("RESPONSES_WITHHELD_FAIL_CLOSED")
    if failed:
        summary.append("PROVIDER_FAILURES_PRESENT")
    if incomplete:
        summary.append("INCOMPLETE_ROLES_PRESENT")
    if redacted:
        summary.append("REDACTION_OR_SANITIZATION_PRESENT")
    if truncated:
        summary.append("COMPARISON_TRUNCATION_PRESENT")
    return OrchestraHumanReviewWorkspace(
        schema_version=HUMAN_REVIEW_WORKSPACE_SCHEMA_VERSION,
        comparison_snapshot_digest="",
        session_id=session_view.session_id,
        session_state=session_view.session_state,
        session_digest=session_view.session_digest,
        created_at_epoch=session_view.created_at_epoch,
        configured_role_count=len(candidates),
        completed_response_count=completed,
        failed_response_count=failed,
        incomplete_response_count=incomplete,
        withheld_response_count=withheld,
        valid_evidence_candidate_count=valid,
        invalid_evidence_candidate_count=invalid,
        redacted_candidate_count=redacted,
        truncated_candidate_count=truncated,
        evidence_status_summary=tuple(summary),
        candidates=candidates,
        pair_comparisons=comparisons,
        agreement_overview=build_agreement_overview(candidates),
        critic_results=session_view.critic_results,
        audit_result=session_view.audit_result,
        critic_presentation_label=CRITIC_NON_AUTHORITY_LABEL,
        audit_presentation_label=AUDIT_EVIDENCE_ONLY_LABEL,
        human_comparison_warning=HUMAN_COMPARISON_WARNING,
    )


def serialize_orchestra_human_review_workspace(
    workspace: OrchestraHumanReviewWorkspace,
) -> bytes:
    if not isinstance(workspace, OrchestraHumanReviewWorkspace):
        raise OrchestraHumanReviewWorkspaceError(
            "OrchestraHumanReviewWorkspace is required"
        )
    return canonical_json_bytes(workspace)


__all__ = [
    "AGREEMENT_OVERVIEW_SCHEMA_VERSION",
    "AGREEMENT_STATES",
    "DESCRIPTIVE_AGREEMENT_LABEL",
    "HUMAN_COMPARISON_WARNING",
    "HUMAN_REVIEW_WORKSPACE_SCHEMA_VERSION",
    "MAXIMUM_COMPARISON_RESPONSE_CHARACTERS",
    "OrchestraAgreementOverview",
    "OrchestraHumanReviewWorkspace",
    "OrchestraHumanReviewWorkspaceError",
    "OrchestraResponseCandidateView",
    "OrchestraResponsePairComparison",
    "RESPONSE_CANDIDATE_SCHEMA_VERSION",
    "RESPONSE_PAIR_COMPARISON_SCHEMA_VERSION",
    "build_agreement_overview",
    "build_orchestra_human_review_workspace",
    "build_response_candidate_views",
    "compare_response_candidates",
    "normalize_response_text",
    "serialize_orchestra_human_review_workspace",
]
