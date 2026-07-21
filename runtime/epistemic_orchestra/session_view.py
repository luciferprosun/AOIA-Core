"""Deterministic, read-only presentation of one Orchestra live session.

The records in this module are inert display metadata.  They cannot issue or
consume a provider-call capability, refresh a preview, approve a result, write
an artifact, execute a command, or mutate a gate.
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
from runtime.epistemic_orchestra.contracts import (
    CriticIssue,
    CriticOutcome,
    CriticSeverity,
    CriticStagePayload,
    EpistemicRunContract,
    EpistemicStageContract,
    JsonContract,
    NON_AUTHORITATIVE,
    OrchestrationMode,
    validate_critic_payload_against_stage,
    validate_stage_against_run,
    validate_stage_parent_binding,
    verify_epistemic_stage_chain,
)
from runtime.epistemic_orchestra.live_run_preview import OrchestraLiveRunPreview
from runtime.epistemic_orchestra.live_session import (
    LiveOrchestraSessionResult,
    LiveProviderStageResult,
)
from runtime.epistemic_orchestra.role_binding import (
    OrchestraOperatorRole,
    OrchestraRoleSelection,
)
from runtime.providers.redaction import (
    redact_provider_display_text,
    redact_provider_text,
    sanitize_provider_display_text,
)


SESSION_VIEW_SCHEMA_VERSION = "orchestra-session-view-1a"
SESSION_SNAPSHOT_SCHEMA_VERSION = "orchestra-session-presentation-snapshot-1a"
ROLE_RESULT_VIEW_SCHEMA_VERSION = "orchestra-role-result-view-1a"
CRITIC_RESULT_VIEW_SCHEMA_VERSION = "orchestra-critic-result-view-1a"
AUDIT_RESULT_VIEW_SCHEMA_VERSION = "orchestra-audit-result-view-1a"
FINDING_VIEW_SCHEMA_VERSION = "orchestra-finding-view-1a"
PROVIDER_TYPE_SNAPSHOT_SCHEMA_VERSION = "orchestra-provider-type-snapshot-1a"
FAILED_STAGE_EVIDENCE_SCHEMA_VERSION = "orchestra-failed-stage-evidence-1a"

CRITIC_NON_AUTHORITY_LABEL = "CRITIC RESULT — NON-AUTHORITATIVE METADATA"
AUDIT_EVIDENCE_ONLY_LABEL = "AUDIT RESULT — EVIDENCE ONLY"
HUMAN_REVIEW_WARNING = (
    "HUMAN REVIEW REQUIRED — NO RESULT SHOWN HERE GRANTS APPROVAL, "
    "WRITE OR EXECUTION AUTHORITY"
)

SESSION_STATES = frozenset(
    {
        "NOT_EXECUTED",
        "RUNNING",
        "COMPLETED",
        "FAILED",
        "PARTIAL",
        "EXPIRED",
        "INVALIDATED",
    }
)
INVOCATION_STATUSES = frozenset(
    {"NOT_EXECUTED", "COMPLETED", "FAILED", "INCOMPLETE", "EVIDENCE_MISMATCH"}
)
RESPONSE_STATUSES = frozenset(
    {"UNAVAILABLE", "AVAILABLE", "FAILED", "EVIDENCE_MISMATCH"}
)
REVIEW_STATUSES = frozenset(
    {
        "NOT_EXECUTED",
        "MISSING",
        "MALFORMED",
        "EVIDENCE_MISMATCH",
        *(item.value for item in CriticOutcome),
    }
)
AUDIT_STATUSES = frozenset(
    {
        "FAIL_CLOSED",
        "FINDINGS_PRESENT",
        "NOT_YET_COMPLETE",
        "NOT_REQUESTED",
        "CLEAN",
    }
)
EVIDENCE_STATUSES = frozenset(
    {"FAIL_CLOSED", "INCOMPLETE", "VALID_NON_AUTHORITATIVE"}
)
SESSION_ERROR_CODES = frozenset(
    {
        "RUN_ACTION_REJECTED",
        "SESSION_EXECUTION_VALIDATION_FAILED",
        "SESSION_OUTPUT_WITHHELD_BY_CREDENTIAL_BOUNDARY",
        "CONNECTION_CONFIGURATION_DISABLED",
        "MODEL_CONFIGURATION_DISABLED",
    }
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_:-]{0,127}\Z")
_MAXIMUM_DISPLAY_CHARACTERS = 100_000


class OrchestraSessionViewError(EpistemicContractError):
    """Fail-closed error for malformed presentation evidence."""


class OrchestraSessionNotFoundError(OrchestraSessionViewError):
    """Raised when a syntactically valid session ID is not retained."""


def validate_orchestra_session_id(value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise OrchestraSessionViewError("session identifier is malformed")
    return value


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise OrchestraSessionViewError(f"{name} is malformed")
    return value


def _code(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SAFE_CODE.fullmatch(value):
        raise OrchestraSessionViewError(f"{name} is malformed")
    return value


def _text(name: str, value: object, *, maximum: int = 4_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise OrchestraSessionViewError(f"{name} must be bounded non-blank text")
    return value


def _optional_text(name: str, value: object, *, maximum: int = 4_000) -> str | None:
    if value is None:
        return None
    return _text(name, value, maximum=maximum)


def _epoch(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OrchestraSessionViewError(f"{name} must be a positive integer epoch")
    return value


def _nonnegative(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OrchestraSessionViewError(f"{name} must be a non-negative integer")
    return value


def _strict_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise OrchestraSessionViewError(f"{name} must be boolean")
    return value


def _optional_sha256(name: str, value: object) -> str | None:
    if value is None:
        return None
    return require_sha256(name, value)


def _tuple_text(
    name: str,
    value: object,
    *,
    codes: bool = False,
    unique: bool = True,
) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (tuple, list)):
        raise OrchestraSessionViewError(f"{name} must be a sequence")
    result = tuple(value)
    for item in result:
        if codes:
            _code(name, item)
        else:
            _text(name, item, maximum=512)
    if unique and len(result) != len(set(result)):
        raise OrchestraSessionViewError(f"{name} contains duplicates")
    return result


def _self_hash(value: JsonContract, field_name: str, supplied: str) -> str:
    material = value.to_dict()
    material.pop(field_name)
    expected = canonical_sha256(material)
    if supplied not in ("", expected):
        raise OrchestraSessionViewError(f"{field_name} differs from presentation fields")
    return expected


def _assert_no_authority(value: object) -> None:
    if getattr(value, "authority_status", None) != NON_AUTHORITATIVE:
        raise OrchestraSessionViewError("presentation authority status must be NON_AUTHORITATIVE")
    for name in (
        "provider_output_is_authority",
        "provider_consensus_is_authority",
        "critic_output_is_authority",
        "audit_output_is_authority",
        "session_view_is_authority",
        "execution_permitted",
        "write_permitted",
        "dispatch_permitted",
        "provider_call_permitted",
        "approval_permitted",
        "gate_mutation_permitted",
        "human_barrier_satisfied",
    ):
        if type(getattr(value, name, None)) is not bool or getattr(value, name):
            raise OrchestraSessionViewError(f"{name} must be False")
    if getattr(value, "human_review_required", None) is not True:
        raise OrchestraSessionViewError("presentation must require human review")


def _ordered_unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)


def _display_text(
    value: str,
    *,
    maximum: int = _MAXIMUM_DISPLAY_CHARACTERS,
) -> tuple[str, str, bool]:
    sanitized = sanitize_provider_display_text(value)
    redacted = redact_provider_display_text(sanitized)
    if len(redacted) > maximum:
        redacted = redacted[:maximum]
    if not redacted.strip():
        redacted = "[SANITIZED_PROVIDER_OUTPUT]"
    return redacted, exact_text_sha256(redacted), redacted != value


def _display_identifier(
    value: str,
    *,
    fallback: str,
    opaque_candidates_are_unsafe: bool = False,
) -> tuple[str, bool]:
    sanitized = sanitize_provider_display_text(value)
    redacted = (
        redact_provider_display_text(sanitized)
        if opaque_candidates_are_unsafe
        else redact_provider_text(sanitized)
    )
    if redacted != value:
        return fallback, True
    return value, False


@dataclass(frozen=True, slots=True)
class OrchestraProviderTypeSnapshot(JsonContract):
    schema_version: str
    connection_id: str
    provider_type: str

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_TYPE_SNAPSHOT_SCHEMA_VERSION:
            raise OrchestraSessionViewError("provider type snapshot schema differs")
        _identifier("connection_id", self.connection_id)
        _identifier("provider_type", self.provider_type)


@dataclass(frozen=True, slots=True)
class OrchestraFailedStageEvidence(JsonContract):
    schema_version: str
    reason_code: str
    stage_id: str
    call_index: int
    operator_role: str
    connection_id: str
    model_profile_id: str

    def __post_init__(self) -> None:
        if self.schema_version != FAILED_STAGE_EVIDENCE_SCHEMA_VERSION:
            raise OrchestraSessionViewError("failed stage evidence schema differs")
        if self.reason_code != "ORCHESTRA_EXACT_STAGE_FAILED":
            raise OrchestraSessionViewError("failed stage reason is unsupported")
        _identifier("stage_id", self.stage_id)
        _nonnegative("call_index", self.call_index)
        try:
            OrchestraOperatorRole(self.operator_role)
        except (TypeError, ValueError) as error:
            raise OrchestraSessionViewError("failed stage role is malformed") from error
        _identifier("connection_id", self.connection_id)
        _identifier("model_profile_id", self.model_profile_id)


@dataclass(frozen=True, slots=True)
class OrchestraSessionSnapshot:
    """Immutable process-local evidence copied by mutating service operations."""

    schema_version: str
    session_id: str
    session_state: str
    created_at_epoch: int
    updated_at_epoch: int
    run: EpistemicRunContract
    preview: OrchestraLiveRunPreview
    role_selection: OrchestraRoleSelection
    provider_types: tuple[OrchestraProviderTypeSnapshot, ...]
    plan_available: bool
    plan_consumed: bool
    exact_human_confirmation_recorded: bool
    confirmation_hash: str | None
    completed_stage_results: tuple[object, ...] = ()
    completed_stage_chain: tuple[object, ...] = ()
    session_result: object | None = None
    failed_stage: OrchestraFailedStageEvidence | None = None
    session_error_code: str | None = None
    redaction_warning: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != SESSION_SNAPSHOT_SCHEMA_VERSION:
            raise OrchestraSessionViewError("session snapshot schema differs")
        validate_orchestra_session_id(self.session_id)
        if self.session_state not in SESSION_STATES:
            raise OrchestraSessionViewError("session snapshot state is unsupported")
        created = _epoch("created_at_epoch", self.created_at_epoch)
        updated = _epoch("updated_at_epoch", self.updated_at_epoch)
        if updated < created:
            raise OrchestraSessionViewError("session snapshot timestamps are inverted")
        if not isinstance(self.run, EpistemicRunContract):
            raise OrchestraSessionViewError("session snapshot run is malformed")
        if not isinstance(self.preview, OrchestraLiveRunPreview):
            raise OrchestraSessionViewError("session snapshot preview is malformed")
        if not isinstance(self.role_selection, OrchestraRoleSelection):
            raise OrchestraSessionViewError("session snapshot role selection is malformed")
        provider_types = tuple(self.provider_types)
        if any(not isinstance(item, OrchestraProviderTypeSnapshot) for item in provider_types):
            raise OrchestraSessionViewError("session provider type evidence is malformed")
        if len({item.connection_id for item in provider_types}) != len(provider_types):
            raise OrchestraSessionViewError("session provider type evidence contains duplicates")
        object.__setattr__(self, "provider_types", provider_types)
        object.__setattr__(self, "completed_stage_results", tuple(self.completed_stage_results))
        object.__setattr__(self, "completed_stage_chain", tuple(self.completed_stage_chain))
        for name in (
            "plan_available",
            "plan_consumed",
            "exact_human_confirmation_recorded",
            "redaction_warning",
        ):
            _strict_bool(name, getattr(self, name))
        _optional_sha256("confirmation_hash", self.confirmation_hash)
        if self.failed_stage is not None and not isinstance(
            self.failed_stage, OrchestraFailedStageEvidence
        ):
            raise OrchestraSessionViewError("failed stage evidence is malformed")
        if self.session_error_code is not None:
            if self.session_error_code not in SESSION_ERROR_CODES:
                raise OrchestraSessionViewError("session error code is unsupported")


@dataclass(frozen=True, slots=True)
class OrchestraFindingView(JsonContract):
    schema_version: str
    source_kind: str
    source_identifier: str
    finding_id: str
    category: str
    severity: str
    summary: str
    evidence: str
    affected_section: str
    recommended_revision: str
    source_revision_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != FINDING_VIEW_SCHEMA_VERSION:
            raise OrchestraSessionViewError("finding view schema differs")
        if self.source_kind not in {"CRITIC", "AUDITOR"}:
            raise OrchestraSessionViewError("finding source kind is unsupported")
        _identifier("source_identifier", self.source_identifier)
        for name in ("source_identifier", "finding_id", "category"):
            value = getattr(self, name)
            safe_value, changed = _display_identifier(
                value,
                fallback="REDACTED",
                opaque_candidates_are_unsafe=name in {"finding_id", "category"},
            )
            if changed or safe_value != value:
                raise OrchestraSessionViewError(f"{name} is not safe display identity")
        if self.severity not in {item.value for item in CriticSeverity}:
            raise OrchestraSessionViewError("finding severity is unsupported")
        for name in ("summary", "evidence", "affected_section", "recommended_revision"):
            value = _text(name, getattr(self, name), maximum=8_000)
            safe_value, _digest, changed = _display_text(value, maximum=8_000)
            if changed or safe_value != value:
                raise OrchestraSessionViewError(f"{name} is not safe presentation text")
        require_sha256("source_revision_hash", self.source_revision_hash)


@dataclass(frozen=True, slots=True)
class OrchestraRoleResultView(JsonContract):
    schema_version: str
    ordering_index: int
    operator_role: str
    connection_id: str
    provider_type: str
    selected_model: str
    model_profile_id: str
    connection_revision_hash: str
    model_revision_hash: str
    role_assignment_hash: str
    stage_id: str
    stage_hash: str | None
    invocation_status: str
    response_status: str
    redacted_provider_response: str | None
    response_digest: str | None
    display_response_digest: str | None
    redaction_or_sanitization_applied: bool
    provider_reported_model: str | None
    usage_metadata_available: bool
    latency_ms: int | None
    error_code: str | None
    evidence_references: tuple[str, ...]
    trust_status: str = "UNTRUSTED"
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    session_view_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != ROLE_RESULT_VIEW_SCHEMA_VERSION:
            raise OrchestraSessionViewError("role result view schema differs")
        _nonnegative("ordering_index", self.ordering_index)
        try:
            OrchestraOperatorRole(self.operator_role)
        except (TypeError, ValueError) as error:
            raise OrchestraSessionViewError("role result operator role is unsupported") from error
        _identifier("connection_id", self.connection_id)
        _identifier("provider_type", self.provider_type)
        selected_model = _text("selected_model", self.selected_model, maximum=512)
        _identifier("model_profile_id", self.model_profile_id)
        for name, value in (
            ("connection_id", self.connection_id),
            ("provider_type", self.provider_type),
            ("selected_model", selected_model),
            ("model_profile_id", self.model_profile_id),
            ("stage_id", self.stage_id),
        ):
            safe_value, changed = _display_identifier(value, fallback="redacted")
            if changed or safe_value != value:
                raise OrchestraSessionViewError(f"{name} is not safe display identity")
        for name in ("connection_revision_hash", "model_revision_hash", "role_assignment_hash"):
            require_sha256(name, getattr(self, name))
        _identifier("stage_id", self.stage_id)
        _optional_sha256("stage_hash", self.stage_hash)
        if self.invocation_status not in INVOCATION_STATUSES:
            raise OrchestraSessionViewError("invocation status is unsupported")
        if self.response_status not in RESPONSE_STATUSES:
            raise OrchestraSessionViewError("response status is unsupported")
        if (self.invocation_status == "COMPLETED") != (
            self.response_status == "AVAILABLE"
        ):
            raise OrchestraSessionViewError("role invocation and response states differ")
        response = _optional_text(
            "redacted_provider_response",
            self.redacted_provider_response,
            maximum=_MAXIMUM_DISPLAY_CHARACTERS,
        )
        _optional_sha256("response_digest", self.response_digest)
        _optional_sha256("display_response_digest", self.display_response_digest)
        _strict_bool(
            "redaction_or_sanitization_applied",
            self.redaction_or_sanitization_applied,
        )
        if response is not None:
            safe_response, safe_digest, changed = _display_text(response)
            if changed or safe_response != response:
                raise OrchestraSessionViewError("provider response is not safe display text")
            if self.display_response_digest != safe_digest:
                raise OrchestraSessionViewError("display response digest differs")
            if self.redaction_or_sanitization_applied:
                if self.response_digest is not None:
                    raise OrchestraSessionViewError(
                        "redacted response cannot expose its source digest"
                    )
            elif self.response_digest is None:
                raise OrchestraSessionViewError("available response digest is missing")
        elif self.display_response_digest is not None or self.response_digest is not None:
            raise OrchestraSessionViewError("unavailable response contains response digests")
        reported_model = _optional_text(
            "provider_reported_model", self.provider_reported_model, maximum=512
        )
        if reported_model is not None:
            safe_model, _digest, changed = _display_text(reported_model, maximum=512)
            if changed or safe_model != reported_model:
                raise OrchestraSessionViewError("provider model is not safe display text")
        if self.usage_metadata_available is not False:
            raise OrchestraSessionViewError("uncaptured usage metadata cannot be reported")
        if self.latency_ms is not None:
            _nonnegative("latency_ms", self.latency_ms)
        if self.error_code is not None:
            if self.error_code not in {
                "ORCHESTRA_EXACT_STAGE_FAILED",
                "RESULT_TYPE_MISMATCH",
                "RESULT_BINDING_MISMATCH",
            }:
                raise OrchestraSessionViewError("role error code is unsupported")
        references = _tuple_text("evidence_references", self.evidence_references)
        for reference in references:
            require_sha256("evidence_reference", reference)
        object.__setattr__(self, "evidence_references", references)
        if self.trust_status != "UNTRUSTED":
            raise OrchestraSessionViewError("role result must remain UNTRUSTED")
        _assert_no_authority(self)


@dataclass(frozen=True, slots=True)
class OrchestraCriticResultView(JsonContract):
    schema_version: str
    presentation_label: str
    ordering_index: int
    critic_identifier: str
    critic_status: str
    findings: tuple[OrchestraFindingView, ...]
    report_digest: str | None
    critic_output_digest: str | None
    evidence_references: tuple[str, ...]
    malformed_or_unavailable: bool
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    session_view_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != CRITIC_RESULT_VIEW_SCHEMA_VERSION:
            raise OrchestraSessionViewError("critic result view schema differs")
        if self.presentation_label != CRITIC_NON_AUTHORITY_LABEL:
            raise OrchestraSessionViewError("critic presentation label differs")
        _nonnegative("ordering_index", self.ordering_index)
        _identifier("critic_identifier", self.critic_identifier)
        safe_identifier, changed = _display_identifier(
            self.critic_identifier,
            fallback="redacted-critic",
        )
        if changed or safe_identifier != self.critic_identifier:
            raise OrchestraSessionViewError("critic identifier is not safe display identity")
        if self.critic_status not in REVIEW_STATUSES:
            raise OrchestraSessionViewError("critic status is unsupported")
        findings = tuple(self.findings)
        if any(not isinstance(item, OrchestraFindingView) for item in findings):
            raise OrchestraSessionViewError("critic findings are malformed")
        object.__setattr__(self, "findings", findings)
        _optional_sha256("report_digest", self.report_digest)
        _optional_sha256("critic_output_digest", self.critic_output_digest)
        references = _tuple_text("evidence_references", self.evidence_references)
        for reference in references:
            require_sha256("evidence_reference", reference)
        object.__setattr__(self, "evidence_references", references)
        _strict_bool("malformed_or_unavailable", self.malformed_or_unavailable)
        _assert_no_authority(self)


@dataclass(frozen=True, slots=True)
class OrchestraAuditResultView(JsonContract):
    schema_version: str
    presentation_label: str
    audit_status: str
    auditor_identifiers: tuple[str, ...]
    auditor_statuses: tuple[str, ...]
    findings: tuple[OrchestraFindingView, ...]
    detected_inconsistencies: tuple[str, ...]
    missing_role_outputs: tuple[str, ...]
    provider_failures: tuple[str, ...]
    hash_mismatches: tuple[str, ...]
    stale_or_malformed_evidence: tuple[str, ...]
    redaction_warnings: tuple[str, ...]
    evidence_references: tuple[str, ...]
    audit_digest: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    session_view_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != AUDIT_RESULT_VIEW_SCHEMA_VERSION:
            raise OrchestraSessionViewError("audit result view schema differs")
        if self.presentation_label != AUDIT_EVIDENCE_ONLY_LABEL:
            raise OrchestraSessionViewError("audit presentation label differs")
        if self.audit_status not in AUDIT_STATUSES:
            raise OrchestraSessionViewError("audit status is unsupported")
        identifiers = _tuple_text("auditor_identifiers", self.auditor_identifiers)
        for identifier in identifiers:
            _identifier("auditor_identifier", identifier)
            safe_identifier, changed = _display_identifier(
                identifier,
                fallback="redacted-auditor",
            )
            if changed or safe_identifier != identifier:
                raise OrchestraSessionViewError(
                    "auditor identifier is not safe display identity"
                )
        object.__setattr__(self, "auditor_identifiers", identifiers)
        object.__setattr__(
            self,
            "auditor_statuses",
            _tuple_text(
                "auditor_statuses",
                self.auditor_statuses,
                codes=True,
                unique=False,
            ),
        )
        if len(self.auditor_statuses) != len(self.auditor_identifiers):
            raise OrchestraSessionViewError("auditor identities and statuses differ")
        findings = tuple(self.findings)
        if any(not isinstance(item, OrchestraFindingView) for item in findings):
            raise OrchestraSessionViewError("audit findings are malformed")
        object.__setattr__(self, "findings", findings)
        for name in (
            "detected_inconsistencies",
            "missing_role_outputs",
            "provider_failures",
            "hash_mismatches",
            "stale_or_malformed_evidence",
            "redaction_warnings",
        ):
            object.__setattr__(self, name, _tuple_text(name, getattr(self, name), codes=True))
        references = _tuple_text("evidence_references", self.evidence_references)
        for reference in references:
            require_sha256("evidence_reference", reference)
        object.__setattr__(self, "evidence_references", references)
        _assert_no_authority(self)
        object.__setattr__(self, "audit_digest", _self_hash(self, "audit_digest", self.audit_digest))


@dataclass(frozen=True, slots=True)
class OrchestraSessionView(JsonContract):
    schema_version: str
    session_id: str
    session_state: str
    created_at_epoch: int
    updated_at_epoch: int
    session_digest: str
    run_hash: str
    live_run_plan_digest: str
    role_selection_digest: str
    source_prompt_digest: str
    plan_expiration_epoch: int
    plan_available: bool
    plan_consumed: bool
    plan_reusable: bool
    exact_human_confirmation_recorded: bool
    confirmation_digest: str | None
    confirmation_is_evidence_only: bool
    selected_role_count: int
    completed_role_count: int
    failed_or_incomplete_role_count: int
    role_results: tuple[OrchestraRoleResultView, ...]
    critic_results: tuple[OrchestraCriticResultView, ...]
    audit_result: OrchestraAuditResultView
    final_draft: str | None
    final_draft_digest: str | None
    final_draft_display_digest: str | None
    final_draft_redaction_or_sanitization_applied: bool
    evidence_status: str
    evidence_references: tuple[str, ...]
    safety_warnings: tuple[str, ...]
    human_review_warning: str
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    provider_consensus_is_authority: bool = False
    critic_output_is_authority: bool = False
    audit_output_is_authority: bool = False
    session_view_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != SESSION_VIEW_SCHEMA_VERSION:
            raise OrchestraSessionViewError("session view schema differs")
        validate_orchestra_session_id(self.session_id)
        if self.session_state not in SESSION_STATES:
            raise OrchestraSessionViewError("session view state is unsupported")
        created = _epoch("created_at_epoch", self.created_at_epoch)
        updated = _epoch("updated_at_epoch", self.updated_at_epoch)
        if updated < created:
            raise OrchestraSessionViewError("session view timestamps are inverted")
        for name in (
            "run_hash",
            "live_run_plan_digest",
            "role_selection_digest",
            "source_prompt_digest",
        ):
            require_sha256(name, getattr(self, name))
        _epoch("plan_expiration_epoch", self.plan_expiration_epoch)
        for name in (
            "plan_available",
            "plan_consumed",
            "plan_reusable",
            "exact_human_confirmation_recorded",
            "confirmation_is_evidence_only",
            "final_draft_redaction_or_sanitization_applied",
        ):
            _strict_bool(name, getattr(self, name))
        if self.plan_reusable:
            raise OrchestraSessionViewError("session presentation cannot make a plan reusable")
        if not self.confirmation_is_evidence_only:
            raise OrchestraSessionViewError("confirmation must remain evidence only")
        _optional_sha256("confirmation_digest", self.confirmation_digest)
        selected = _nonnegative("selected_role_count", self.selected_role_count)
        completed = _nonnegative("completed_role_count", self.completed_role_count)
        incomplete = _nonnegative(
            "failed_or_incomplete_role_count", self.failed_or_incomplete_role_count
        )
        if completed + incomplete != selected:
            raise OrchestraSessionViewError("session role counts are inconsistent")
        roles = tuple(self.role_results)
        if len(roles) != selected or any(
            not isinstance(item, OrchestraRoleResultView) for item in roles
        ):
            raise OrchestraSessionViewError("session role presentation is malformed")
        if tuple(item.ordering_index for item in roles) != tuple(range(len(roles))):
            raise OrchestraSessionViewError("session role ordering is not deterministic")
        object.__setattr__(self, "role_results", roles)
        critics = tuple(self.critic_results)
        if any(not isinstance(item, OrchestraCriticResultView) for item in critics):
            raise OrchestraSessionViewError("session critic presentation is malformed")
        object.__setattr__(self, "critic_results", critics)
        if not isinstance(self.audit_result, OrchestraAuditResultView):
            raise OrchestraSessionViewError("session audit presentation is malformed")
        final_draft = _optional_text(
            "final_draft", self.final_draft, maximum=_MAXIMUM_DISPLAY_CHARACTERS
        )
        _optional_sha256("final_draft_digest", self.final_draft_digest)
        _optional_sha256("final_draft_display_digest", self.final_draft_display_digest)
        if final_draft is not None:
            safe_draft, safe_digest, changed = _display_text(final_draft)
            if changed or safe_draft != final_draft:
                raise OrchestraSessionViewError("final draft is not safe display text")
            if self.final_draft_display_digest != safe_digest:
                raise OrchestraSessionViewError("final draft display digest differs")
            if self.final_draft_redaction_or_sanitization_applied:
                if self.final_draft_digest is not None:
                    raise OrchestraSessionViewError(
                        "redacted final draft cannot expose its source digest"
                    )
            elif self.final_draft_digest is None:
                raise OrchestraSessionViewError("final draft digest is missing")
        elif self.final_draft_digest is not None or self.final_draft_display_digest is not None:
            raise OrchestraSessionViewError("missing final draft contains digests")
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise OrchestraSessionViewError("evidence status is unsupported")
        references = _tuple_text("evidence_references", self.evidence_references)
        for reference in references:
            require_sha256("evidence_reference", reference)
        object.__setattr__(self, "evidence_references", references)
        warnings = _tuple_text("safety_warnings", self.safety_warnings)
        object.__setattr__(self, "safety_warnings", warnings)
        if self.human_review_warning != HUMAN_REVIEW_WARNING:
            raise OrchestraSessionViewError("human review warning differs")
        _assert_no_authority(self)
        object.__setattr__(self, "session_digest", _self_hash(self, "session_digest", self.session_digest))


def _finding_view(
    *,
    issue: CriticIssue,
    source_kind: str,
    source_identifier: str,
) -> tuple[OrchestraFindingView, bool]:
    changed = False
    finding_id, identifier_changed = _display_identifier(
        issue.issue_id,
        fallback="redacted-issue",
        opaque_candidates_are_unsafe=True,
    )
    category, category_changed = _display_identifier(
        issue.issue_code,
        fallback="redacted-category",
        opaque_candidates_are_unsafe=True,
    )
    changed = identifier_changed or category_changed
    displayed: dict[str, str] = {}
    for name in ("summary", "evidence", "affected_section", "recommended_revision"):
        value, _digest, was_changed = _display_text(
            getattr(issue, name),
            maximum=8_000,
        )
        displayed[name] = value
        changed = changed or was_changed
    return (
        OrchestraFindingView(
            schema_version=FINDING_VIEW_SCHEMA_VERSION,
            source_kind=source_kind,
            source_identifier=source_identifier,
            finding_id=finding_id,
            category=category,
            severity=issue.severity,
            summary=displayed["summary"],
            evidence=displayed["evidence"],
            affected_section=displayed["affected_section"],
            recommended_revision=displayed["recommended_revision"],
            source_revision_hash=issue.source_revision_hash,
        ),
        changed,
    )


def _binding_matches_plan(
    result: LiveProviderStageResult,
    *,
    plan: object,
    run: EpistemicRunContract,
) -> bool:
    binding = result.binding
    try:
        binding_material = binding.to_dict()
        supplied_binding_hash = binding_material.pop("binding_hash")
        binding_hash_matches = supplied_binding_hash == canonical_sha256(binding_material)
    except (AttributeError, KeyError, TypeError, ValueError):
        binding_hash_matches = False
    return (
        binding_hash_matches
        and result.operator_role == binding.operator_role
        and binding.orchestra_run_id == run.run_id
        and binding.run_hash == run.run_hash
        and binding.source_prompt_hash == run.source_prompt_hash
        and binding.stage_id == getattr(plan, "stage_id", None)
        and binding.connection_id == getattr(plan, "connection_id", None)
        and binding.connection_revision_hash
        == getattr(plan, "connection_revision_hash", None)
        and binding.model_profile_id == getattr(plan, "model_profile_id", None)
        and binding.model_revision_hash == getattr(plan, "model_revision_hash", None)
        and binding.remote_model_id == getattr(plan, "remote_model_id", None)
        and binding.operator_role == getattr(plan, "operator_role", None)
        and binding.role_assignment_hash == getattr(plan, "role_assignment_hash", None)
        and binding.plan_entry_hash == getattr(plan, "plan_entry_hash", None)
        and binding.maximum_output_tokens
        == getattr(plan, "maximum_output_tokens", None)
        and binding.timeout_seconds == getattr(plan, "timeout_seconds", None)
        and result.response_hash == exact_text_sha256(result.response_text)
    )


def build_orchestra_session_view(session: OrchestraSessionSnapshot) -> OrchestraSessionView:
    """Build a pure presentation after independently validating bound evidence."""

    if not isinstance(session, OrchestraSessionSnapshot):
        raise OrchestraSessionViewError("session snapshot is required")
    run = session.run
    preview = session.preview
    selection = session.role_selection
    plans = tuple(preview.planned_calls)
    assignments = tuple(selection.assignments)
    mismatches: list[str] = []
    stale_or_malformed: list[str] = []
    redaction_warnings: list[str] = []

    if not (
        session.session_id == run.run_id == preview.orchestra_run_id
        and run.run_hash == preview.run_hash
        and run.source_request_hash == preview.source_request_hash
        and run.source_prompt_hash == preview.source_prompt_hash
        and run.stage_plan_hash == preview.epistemic_stage_plan_hash
        and selection.role_selection_hash == preview.role_selection_hash
    ):
        mismatches.append("SESSION_RUN_PREVIEW_BINDING_MISMATCH")
    planned_call_stage_ids = tuple(plan.stage_id for plan in plans)
    expected_run_stage_ids = (
        (*planned_call_stage_ids, preview.final_primary_stage_id)
        if preview.final_primary_is_inert
        else planned_call_stage_ids
    )
    if tuple(run.planned_stage_ids) != expected_run_stage_ids or not (
        run.planned_stage_roles[0] == "PRIMARY"
        and run.planned_stage_roles[-1] == "PRIMARY"
        and all(role == "CRITIC" for role in run.planned_stage_roles[1:-1])
    ):
        mismatches.append("RUN_STAGE_PLAN_BINDING_MISMATCH")
    if session.plan_available and session.plan_consumed:
        mismatches.append("PLAN_AVAILABILITY_STATE_MISMATCH")
    if session.exact_human_confirmation_recorded != (
        session.confirmation_hash is not None
    ) or (
        session.exact_human_confirmation_recorded and not session.plan_consumed
    ):
        mismatches.append("CONFIRMATION_EVIDENCE_STATE_MISMATCH")
    if session.session_state in {"RUNNING", "COMPLETED", "PARTIAL"} and not (
        session.plan_consumed and session.exact_human_confirmation_recorded
    ):
        mismatches.append("SESSION_LIFECYCLE_EVIDENCE_MISMATCH")
    if session.session_state in {"EXPIRED", "INVALIDATED"} and session.plan_available:
        mismatches.append("TERMINAL_PLAN_AVAILABILITY_MISMATCH")
    if session.plan_available != (session.session_state == "NOT_EXECUTED"):
        mismatches.append("SESSION_PLAN_STATE_MISMATCH")
    if session.plan_consumed != (
        session.session_state in {"RUNNING", "COMPLETED", "PARTIAL", "FAILED"}
    ):
        mismatches.append("SESSION_CONSUMPTION_STATE_MISMATCH")
    if session.session_error_code is not None:
        stale_or_malformed.append(session.session_error_code)
    if session.session_state == "EXPIRED":
        stale_or_malformed.append("LIVE_RUN_PLAN_EXPIRED")
    if len(plans) != len(assignments):
        mismatches.append("ROLE_PLAN_COUNT_MISMATCH")
    for index, (plan, assignment) in enumerate(zip(plans, assignments)):
        if not (
            plan.call_index == index == assignment.ordinal
            and plan.role_assignment_hash == assignment.role_assignment_hash
            and plan.connection_id == assignment.connection_id
            and plan.connection_revision_hash == assignment.connection_revision_hash
            and plan.model_profile_id == assignment.model_profile_id
            and plan.model_revision_hash == assignment.model_revision_hash
            and plan.remote_model_id == assignment.remote_model_id
            and plan.operator_role == assignment.role
        ):
            mismatches.append("ROLE_PLAN_BINDING_MISMATCH")

    provider_types = {item.connection_id: item.provider_type for item in session.provider_types}
    selected_connection_ids = {assignment.connection_id for assignment in assignments}
    if set(provider_types) != selected_connection_ids:
        mismatches.append("PROVIDER_TYPE_EVIDENCE_BINDING_MISMATCH")

    results = tuple(session.completed_stage_results)
    stages = tuple(session.completed_stage_chain)
    if len(results) > len(plans):
        mismatches.append("COMPLETED_RESULT_COUNT_EXCEEDS_PLAN")
    result_by_index: dict[int, LiveProviderStageResult] = {}
    plan_index_by_hash = {plan.plan_entry_hash: index for index, plan in enumerate(plans)}
    for result in results:
        if not isinstance(result, LiveProviderStageResult):
            mismatches.append("RESULT_TYPE_MISMATCH")
            continue
        index = plan_index_by_hash.get(result.binding.plan_entry_hash)
        if index is None or index in result_by_index:
            mismatches.append("RESULT_PLAN_MEMBERSHIP_MISMATCH")
            continue
        result_by_index[index] = result
    ordered_results = tuple(
        result_by_index[index]
        for index in range(len(plans))
        if index in result_by_index
    )
    if any(not isinstance(item, EpistemicStageContract) for item in stages):
        mismatches.append("COMPLETED_STAGE_CHAIN_MALFORMED")
        stages = ()
    elif stages:
        stage_ids = tuple(item.stage_id for item in stages)
        stage_hashes = tuple(item.stage_hash for item in stages)
        if (
            stage_ids != tuple(run.planned_stage_ids[: len(stages)])
            or len(stage_ids) != len(set(stage_ids))
            or len(stage_hashes) != len(set(stage_hashes))
        ):
            mismatches.append("COMPLETED_STAGE_CHAIN_ORDER_MISMATCH")
        try:
            for index, stage in enumerate(stages):
                if stage.stage_index != index:
                    raise EpistemicContractError("stage chain is reordered")
                validate_stage_against_run(stage, run)
                parent = None
                if index:
                    parent = (
                        stages[index - 1]
                        if run.orchestration_mode
                        == OrchestrationMode.SEQUENTIAL_RING_V1.value
                        else stages[0]
                    )
                validate_stage_parent_binding(
                    stage,
                    parent,
                    parent_revision_hash=(
                        None if parent is None else parent.source_revision_hash
                    ),
                )
        except EpistemicContractError:
            mismatches.append("COMPLETED_STAGE_CHAIN_BINDING_MISMATCH")
    if session.session_state == "COMPLETED" and stages:
        try:
            verify_epistemic_stage_chain(run, stages)
        except EpistemicContractError:
            mismatches.append("COMPLETED_STAGE_CHAIN_INVALID")
    stage_by_id = {
        item.stage_id: item for item in stages if isinstance(item, EpistemicStageContract)
    }
    valid_results: dict[int, LiveProviderStageResult] = {}
    role_views: list[OrchestraRoleResultView] = []
    tainted_result_indexes: set[int] = set()
    failed = session.failed_stage
    failed_index: int | None = None
    if failed is not None:
        if failed.call_index >= len(plans):
            mismatches.append("FAILED_STAGE_EVIDENCE_MISMATCH")
        else:
            failed_plan = plans[failed.call_index]
            if not (
                failed.stage_id == failed_plan.stage_id
                and failed.operator_role == failed_plan.operator_role
                and failed.connection_id == failed_plan.connection_id
                and failed.model_profile_id == failed_plan.model_profile_id
            ):
                mismatches.append("FAILED_STAGE_EVIDENCE_MISMATCH")
            else:
                failed_index = failed.call_index
    if session.session_state in {"NOT_EXECUTED", "RUNNING", "EXPIRED", "INVALIDATED"} and (
        results or stages or session.session_result is not None or failed is not None
    ):
        mismatches.append("SESSION_LIFECYCLE_PAYLOAD_MISMATCH")
    if session.session_state == "FAILED" and results:
        mismatches.append("FAILED_SESSION_CONTAINS_COMPLETED_RESULTS")
    if session.session_state == "PARTIAL" and (not results or failed_index is None):
        mismatches.append("PARTIAL_SESSION_EVIDENCE_MISMATCH")
    if session.session_state == "COMPLETED" and (
        failed is not None or session.session_error_code is not None
    ):
        mismatches.append("COMPLETED_SESSION_CONTAINS_FAILURE_EVIDENCE")

    for index, plan in enumerate(plans):
        result = result_by_index.get(index)
        invocation_status = "NOT_EXECUTED"
        response_status = "UNAVAILABLE"
        display_response = None
        response_digest = None
        display_digest = None
        display_changed = False
        latency_ms = None
        stage_hash = None
        error_code = None
        references = [
            plan.plan_entry_hash,
            plan.role_assignment_hash,
            plan.connection_revision_hash,
            plan.model_revision_hash,
        ]
        if plan.operator_role == OrchestraOperatorRole.CRITIC.value:
            binding_depends_on_redacted_output = 0 in tainted_result_indexes
        elif plan.operator_role == OrchestraOperatorRole.AUDITOR.value:
            binding_depends_on_redacted_output = any(
                prior_index in tainted_result_indexes
                and plans[prior_index].operator_role
                in {
                    OrchestraOperatorRole.MAIN.value,
                    OrchestraOperatorRole.CRITIC.value,
                }
                for prior_index in range(index)
            )
        elif plan.operator_role == OrchestraOperatorRole.SYNTHESIZER.value:
            binding_depends_on_redacted_output = any(
                prior_index in tainted_result_indexes for prior_index in range(index)
            )
        else:
            binding_depends_on_redacted_output = False
        if result is not None:
            if not isinstance(result, LiveProviderStageResult):
                invocation_status = "EVIDENCE_MISMATCH"
                response_status = "EVIDENCE_MISMATCH"
                error_code = "RESULT_TYPE_MISMATCH"
                mismatches.append("RESULT_TYPE_MISMATCH")
            else:
                stage = stage_by_id.get(result.binding.stage_id)
                if (
                    not _binding_matches_plan(result, plan=plan, run=run)
                    or stage is None
                    or stage.stage_hash != result.binding.stage_hash
                ):
                    invocation_status = "EVIDENCE_MISMATCH"
                    response_status = "EVIDENCE_MISMATCH"
                    error_code = "RESULT_BINDING_MISMATCH"
                    mismatches.append("RESULT_BINDING_MISMATCH")
                else:
                    invocation_status = "COMPLETED"
                    response_status = "AVAILABLE"
                    display_response, display_digest, display_changed = _display_text(
                        result.response_text
                    )
                    latency_ms = result.latency_ms
                    stage_hash = (
                        None
                        if binding_depends_on_redacted_output
                        else result.binding.stage_hash
                    )
                    if stage_hash is not None:
                        references.append(stage_hash)
                    if display_changed or binding_depends_on_redacted_output:
                        response_digest = None
                    else:
                        response_digest = result.response_hash
                        references.append(result.response_hash)
                        references.append(result.binding.binding_hash)
                    valid_results[index] = result
                    if display_changed:
                        redaction_warnings.append("PROVIDER_DISPLAY_REDACTED_OR_SANITIZED")
                    if display_changed or binding_depends_on_redacted_output:
                        tainted_result_indexes.add(index)
                    if binding_depends_on_redacted_output:
                        redaction_warnings.append(
                            "DOWNSTREAM_EVIDENCE_DIGESTS_WITHHELD_BY_REDACTION"
                        )
        elif failed_index == index:
            invocation_status = "FAILED"
            response_status = "FAILED"
            error_code = failed.reason_code
        elif session.session_state in {"FAILED", "PARTIAL", "COMPLETED"}:
            invocation_status = "INCOMPLETE"
            response_status = "UNAVAILABLE"

        role_views.append(
            OrchestraRoleResultView(
                schema_version=ROLE_RESULT_VIEW_SCHEMA_VERSION,
                ordering_index=index,
                operator_role=plan.operator_role,
                connection_id=plan.connection_id,
                provider_type=provider_types.get(plan.connection_id, "unknown"),
                selected_model=plan.remote_model_id,
                model_profile_id=plan.model_profile_id,
                connection_revision_hash=plan.connection_revision_hash,
                model_revision_hash=plan.model_revision_hash,
                role_assignment_hash=plan.role_assignment_hash,
                stage_id=plan.stage_id,
                stage_hash=stage_hash,
                invocation_status=invocation_status,
                response_status=response_status,
                redacted_provider_response=display_response,
                response_digest=response_digest,
                display_response_digest=display_digest,
                redaction_or_sanitization_applied=(
                    display_changed or binding_depends_on_redacted_output
                ),
                provider_reported_model=None,
                usage_metadata_available=False,
                latency_ms=latency_ms,
                error_code=error_code,
                evidence_references=_ordered_unique(references),
            )
        )

    result_contract = session.session_result
    if result_contract is not None:
        if not isinstance(result_contract, LiveOrchestraSessionResult):
            mismatches.append("SESSION_RESULT_TYPE_MISMATCH")
        elif not (
            result_contract.orchestra_run_id == run.run_id
            and result_contract.run_hash == run.run_hash
            and result_contract.preview_hash == preview.preview_hash
            and result_contract.confirmation_hash == session.confirmation_hash
            and result_contract.role_selection_hash == selection.role_selection_hash
            and tuple(result_contract.stage_results) == ordered_results
            and tuple(result_contract.stage_chain) == stages
            and result_contract.synthesis_performed
            is (not preview.final_primary_is_inert)
            and bool(ordered_results)
            and result_contract.final_draft
            == (
                ordered_results[-1].response_text
                if result_contract.synthesis_performed
                else ordered_results[0].response_text
            )
        ):
            mismatches.append("SESSION_RESULT_BINDING_MISMATCH")
    if session.session_state == "COMPLETED" and (
        not isinstance(result_contract, LiveOrchestraSessionResult)
        or len(valid_results) != len(plans)
    ):
        mismatches.append("SESSION_COMPLETION_EVIDENCE_MISMATCH")

    critic_views: list[OrchestraCriticResultView] = []
    auditor_identifiers: list[str] = []
    auditor_statuses: list[str] = []
    auditor_findings: list[OrchestraFindingView] = []
    audit_references: list[str] = [preview.preview_hash, run.run_hash, selection.role_selection_hash]

    for index, plan in enumerate(plans):
        if plan.operator_role not in {
            OrchestraOperatorRole.CRITIC.value,
            OrchestraOperatorRole.AUDITOR.value,
        }:
            continue
        source_kind = plan.operator_role
        source_identifier = plan.model_profile_id
        result = valid_results.get(index)
        payload = result.critic_payload if result is not None else None
        status = "NOT_EXECUTED"
        findings: list[OrchestraFindingView] = []
        report_digest = None
        output_digest = None
        malformed = False
        references = [plan.plan_entry_hash, plan.role_assignment_hash]
        review_display_changed = (
            role_views[index].redaction_or_sanitization_applied
            or index in tainted_result_indexes
        )
        if result is None:
            status = (
                "EVIDENCE_MISMATCH"
                if role_views[index].invocation_status == "EVIDENCE_MISMATCH"
                else "MISSING"
                if role_views[index].invocation_status in {"COMPLETED", "INCOMPLETE", "FAILED"}
                else "NOT_EXECUTED"
            )
            malformed = status in {"EVIDENCE_MISMATCH", "MISSING"}
        elif payload is None:
            status = "MISSING"
            malformed = True
            stale_or_malformed.append("REVIEW_PAYLOAD_MISSING")
        elif not isinstance(payload, CriticStagePayload):
            status = "MALFORMED"
            malformed = True
            stale_or_malformed.append("REVIEW_PAYLOAD_MALFORMED")
        else:
            stage = stage_by_id.get(result.binding.stage_id)
            try:
                if stage is None:
                    raise OrchestraSessionViewError("review stage evidence is missing")
                validate_critic_payload_against_stage(payload, stage)
            except EpistemicContractError:
                status = "EVIDENCE_MISMATCH"
                malformed = True
                mismatches.append("REVIEW_PAYLOAD_BINDING_MISMATCH")
            else:
                status = payload.critic_outcome
                report_digest = payload.payload_hash
                output_digest = payload.critic_output_hash
                references.extend(
                    (
                        payload.payload_hash,
                        payload.critic_output_hash,
                        payload.stage_hash,
                        payload.source_revision_hash,
                    )
                )
                if payload.critic_outcome in {
                    CriticOutcome.CRITIC_OUTPUT_BLOCKED.value,
                    CriticOutcome.CRITIC_OUTPUT_INVALID.value,
                }:
                    malformed = True
                    stale_or_malformed.append(payload.critic_outcome)
                for issue in payload.issues:
                    finding, changed = _finding_view(
                        issue=issue,
                        source_kind=source_kind,
                        source_identifier=source_identifier,
                    )
                    findings.append(finding)
                    if changed:
                        review_display_changed = True
                        redaction_warnings.append("REVIEW_DISPLAY_REDACTED_OR_SANITIZED")
                if review_display_changed:
                    report_digest = None
                    output_digest = None
                    references = [plan.plan_entry_hash, plan.role_assignment_hash]
                    redaction_warnings.append("REVIEW_DIGEST_WITHHELD_BY_REDACTION")

        if source_kind == OrchestraOperatorRole.CRITIC.value:
            critic_views.append(
                OrchestraCriticResultView(
                    schema_version=CRITIC_RESULT_VIEW_SCHEMA_VERSION,
                    presentation_label=CRITIC_NON_AUTHORITY_LABEL,
                    ordering_index=index,
                    critic_identifier=source_identifier,
                    critic_status=status,
                    findings=tuple(findings),
                    report_digest=report_digest,
                    critic_output_digest=output_digest,
                    evidence_references=_ordered_unique(references),
                    malformed_or_unavailable=malformed,
                )
            )
        else:
            auditor_identifiers.append(source_identifier)
            auditor_statuses.append(status)
            auditor_findings.extend(findings)
            audit_references.extend(references)

    missing_roles = tuple(
        f"ROLE_{item.ordering_index}_{item.operator_role}_MISSING"
        for item in role_views
        if item.response_status != "AVAILABLE"
    )
    provider_failures = tuple(
        f"ROLE_{item.ordering_index}_{item.operator_role}_PROVIDER_FAILURE"
        for item in role_views
        if item.invocation_status == "FAILED"
    )
    if session.redaction_warning:
        redaction_warnings.append("SESSION_OUTPUT_WITHHELD_BY_CREDENTIAL_BOUNDARY")
    hash_mismatches = _ordered_unique(mismatches)
    stale_evidence = _ordered_unique(stale_or_malformed)
    redaction_codes = _ordered_unique(redaction_warnings)
    detected = _ordered_unique(
        [*hash_mismatches, *stale_evidence, *provider_failures, *missing_roles]
    )
    auditor_requested = any(
        plan.operator_role == OrchestraOperatorRole.AUDITOR.value for plan in plans
    )
    if hash_mismatches or stale_evidence:
        audit_status = "FAIL_CLOSED"
    elif session.session_state in {"NOT_EXECUTED", "EXPIRED", "RUNNING"}:
        audit_status = "NOT_YET_COMPLETE"
    elif detected or auditor_findings or redaction_codes:
        audit_status = "FINDINGS_PRESENT"
    elif not auditor_requested:
        audit_status = "NOT_REQUESTED"
    else:
        audit_status = "CLEAN"

    audit_result = OrchestraAuditResultView(
        schema_version=AUDIT_RESULT_VIEW_SCHEMA_VERSION,
        presentation_label=AUDIT_EVIDENCE_ONLY_LABEL,
        audit_status=audit_status,
        auditor_identifiers=tuple(auditor_identifiers),
        auditor_statuses=tuple(auditor_statuses),
        findings=tuple(auditor_findings),
        detected_inconsistencies=detected,
        missing_role_outputs=missing_roles,
        provider_failures=provider_failures,
        hash_mismatches=hash_mismatches,
        stale_or_malformed_evidence=stale_evidence,
        redaction_warnings=redaction_codes,
        evidence_references=_ordered_unique(audit_references),
    )

    final_draft = None
    final_draft_digest = None
    final_draft_display_digest = None
    final_draft_changed = False
    final_draft_source_tainted = False
    if isinstance(result_contract, LiveOrchestraSessionResult) and not hash_mismatches:
        final_draft, final_draft_display_digest, final_draft_changed = _display_text(
            result_contract.final_draft
        )
        final_result_index = len(plans) - 1 if result_contract.synthesis_performed else 0
        final_draft_source_tainted = final_result_index in tainted_result_indexes
        final_draft_digest = (
            None
            if final_draft_changed or final_draft_source_tainted
            else result_contract.final_draft_hash
        )

    completed_count = sum(
        item.invocation_status == "COMPLETED" for item in role_views
    )
    evidence_status = (
        "FAIL_CLOSED"
        if hash_mismatches or stale_evidence
        else "INCOMPLETE"
        if completed_count != len(role_views)
        else "VALID_NON_AUTHORITATIVE"
    )
    evidence_references = _ordered_unique(
        [
            run.run_hash,
            preview.preview_hash,
            preview.epistemic_stage_plan_hash,
            selection.role_selection_hash,
            run.source_prompt_hash,
            audit_result.audit_digest,
            *(() if session.confirmation_hash is None else (session.confirmation_hash,)),
        ]
    )
    return OrchestraSessionView(
        schema_version=SESSION_VIEW_SCHEMA_VERSION,
        session_id=session.session_id,
        session_state=session.session_state,
        created_at_epoch=session.created_at_epoch,
        updated_at_epoch=session.updated_at_epoch,
        session_digest="",
        run_hash=run.run_hash,
        live_run_plan_digest=preview.preview_hash,
        role_selection_digest=selection.role_selection_hash,
        source_prompt_digest=run.source_prompt_hash,
        plan_expiration_epoch=preview.expires_at_epoch,
        plan_available=session.plan_available,
        plan_consumed=session.plan_consumed,
        plan_reusable=False,
        exact_human_confirmation_recorded=session.exact_human_confirmation_recorded,
        confirmation_digest=session.confirmation_hash,
        confirmation_is_evidence_only=True,
        selected_role_count=len(role_views),
        completed_role_count=completed_count,
        failed_or_incomplete_role_count=len(role_views) - completed_count,
        role_results=tuple(role_views),
        critic_results=tuple(critic_views),
        audit_result=audit_result,
        final_draft=final_draft,
        final_draft_digest=final_draft_digest,
        final_draft_display_digest=final_draft_display_digest,
        final_draft_redaction_or_sanitization_applied=(
            final_draft_changed or final_draft_source_tainted
        ),
        evidence_status=evidence_status,
        evidence_references=evidence_references,
        safety_warnings=(
            CRITIC_NON_AUTHORITY_LABEL,
            AUDIT_EVIDENCE_ONLY_LABEL,
            HUMAN_REVIEW_WARNING,
        ),
        human_review_warning=HUMAN_REVIEW_WARNING,
    )


def serialize_orchestra_session_view(view: OrchestraSessionView) -> bytes:
    if not isinstance(view, OrchestraSessionView):
        raise OrchestraSessionViewError("OrchestraSessionView is required")
    return canonical_json_bytes(view)


__all__ = [
    "AUDIT_EVIDENCE_ONLY_LABEL",
    "CRITIC_NON_AUTHORITY_LABEL",
    "FAILED_STAGE_EVIDENCE_SCHEMA_VERSION",
    "HUMAN_REVIEW_WARNING",
    "OrchestraAuditResultView",
    "OrchestraCriticResultView",
    "OrchestraFailedStageEvidence",
    "OrchestraFindingView",
    "OrchestraProviderTypeSnapshot",
    "OrchestraRoleResultView",
    "OrchestraSessionNotFoundError",
    "OrchestraSessionSnapshot",
    "OrchestraSessionView",
    "OrchestraSessionViewError",
    "PROVIDER_TYPE_SNAPSHOT_SCHEMA_VERSION",
    "SESSION_SNAPSHOT_SCHEMA_VERSION",
    "SESSION_VIEW_SCHEMA_VERSION",
    "build_orchestra_session_view",
    "serialize_orchestra_session_view",
    "validate_orchestra_session_id",
]
