from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class ProviderClass(str, Enum):
    GEMINI = "GEMINI"
    OPENROUTER = "OPENROUTER"
    OPENROUTER_FREE = "OPENROUTER_FREE"
    PAID_MODEL = "PAID_MODEL"
    LOCAL_MODEL = "LOCAL_MODEL"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"


class TrustLevel(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    TRUSTED_PAID = "TRUSTED_PAID"
    THIRD_PARTY_PAID = "THIRD_PARTY_PAID"
    THIRD_PARTY_FREE = "THIRD_PARTY_FREE"
    UNKNOWN = "UNKNOWN"


class TaskSensitivity(str, Enum):
    PUBLIC_DEV = "PUBLIC_DEV"
    INTERNAL_NON_CANONICAL = "INTERNAL_NON_CANONICAL"
    SENSITIVE = "SENSITIVE"
    CANONICAL = "CANONICAL"
    SECRET_ADJACENT = "SECRET_ADJACENT"


class RoutingDecisionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
    APPROVED_BY_HUMAN = "APPROVED_BY_HUMAN"
    DISABLED = "DISABLED"


def _require_nonblank(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")


def _require_string_sequence(name: str, values: Sequence[str]) -> None:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError(f"{name} must be a sequence of strings")
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"{name} must contain only nonblank strings")


def _enforce_no_active_authority(
    provider_call_permitted: bool,
    automatic_fallback_permitted: bool,
    execution_permitted: bool,
    canonical_promotion_permitted: bool,
) -> None:
    if provider_call_permitted is not False:
        raise ValueError("provider_call_permitted must remain False")
    if automatic_fallback_permitted is not False:
        raise ValueError("automatic_fallback_permitted must remain False")
    if execution_permitted is not False:
        raise ValueError("execution_permitted must remain False")
    if canonical_promotion_permitted is not False:
        raise ValueError("canonical_promotion_permitted must remain False")


def _free_or_unknown_provider(provider_class: ProviderClass, trust_level: TrustLevel) -> bool:
    return (
        provider_class in {ProviderClass.OPENROUTER_FREE, ProviderClass.UNKNOWN}
        or trust_level in {TrustLevel.THIRD_PARTY_FREE, TrustLevel.UNKNOWN}
    )


@dataclass(frozen=True)
class ModelProviderProfile:
    provider_id: str
    display_name: str
    provider_class: ProviderClass
    trust_level: TrustLevel
    enabled: bool = False
    allows_sensitive_tasks: bool = False
    allows_canonical_tasks: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonblank("provider_id", self.provider_id)
        _require_nonblank("display_name", self.display_name)
        _require_string_sequence("notes", self.notes)
        if self.provider_class in {ProviderClass.DISABLED, ProviderClass.UNKNOWN} and self.enabled:
            raise ValueError("disabled or unknown providers cannot be enabled")
        if _free_or_unknown_provider(self.provider_class, self.trust_level):
            if self.allows_sensitive_tasks:
                raise ValueError("free or unknown providers cannot allow sensitive tasks")
            if self.allows_canonical_tasks:
                raise ValueError("free or unknown providers cannot allow canonical tasks")
        if self.provider_class is ProviderClass.LOCAL_MODEL and self.trust_level is not TrustLevel.LOCAL_ONLY:
            raise ValueError("local models must use LOCAL_ONLY trust level")


@dataclass(frozen=True)
class ModelCatalogEntry:
    model_id: str
    display_name: str
    provider_id: str
    provider_class: ProviderClass
    trust_level: TrustLevel
    enabled: bool = False
    free_tier: bool = False
    paid_tier: bool = False
    allows_sensitive_tasks: bool = False
    allows_canonical_tasks: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonblank("model_id", self.model_id)
        _require_nonblank("display_name", self.display_name)
        _require_nonblank("provider_id", self.provider_id)
        _require_string_sequence("notes", self.notes)
        if self.free_tier and self.paid_tier:
            raise ValueError("model cannot be both free_tier and paid_tier")
        if self.provider_class in {ProviderClass.DISABLED, ProviderClass.UNKNOWN} and self.enabled:
            raise ValueError("disabled or unknown model entries cannot be enabled")
        if _free_or_unknown_provider(self.provider_class, self.trust_level) or self.free_tier:
            if self.allows_sensitive_tasks:
                raise ValueError("free or unknown models cannot allow sensitive tasks")
            if self.allows_canonical_tasks:
                raise ValueError("free or unknown models cannot allow canonical tasks")


@dataclass(frozen=True)
class ModelTaskContext:
    task_id: str
    sensitivity: TaskSensitivity
    prompt_summary_redacted: str
    requester: str
    source_reference: str = ""
    secret_bearing: bool = False
    canonical_task: bool = False
    execution_requested: bool = False

    def __post_init__(self) -> None:
        _require_nonblank("task_id", self.task_id)
        _require_nonblank("prompt_summary_redacted", self.prompt_summary_redacted)
        _require_nonblank("requester", self.requester)
        if self.source_reference:
            _require_nonblank("source_reference", self.source_reference)
        if self.secret_bearing and self.sensitivity is not TaskSensitivity.SECRET_ADJACENT:
            raise ValueError("secret-bearing tasks must use SECRET_ADJACENT sensitivity")
        if self.canonical_task and self.sensitivity is not TaskSensitivity.CANONICAL:
            raise ValueError("canonical tasks must use CANONICAL sensitivity")
        if self.execution_requested:
            raise ValueError("model-router task contexts cannot request execution")


@dataclass(frozen=True)
class ModelSelectionProposal:
    proposal_id: str
    task_context: ModelTaskContext
    requested_model_id: str
    requested_provider_id: str
    provider_class: ProviderClass
    trust_level: TrustLevel
    rationale: str
    status: RoutingDecisionStatus = RoutingDecisionStatus.PROPOSED
    fallback_model_ids: tuple[str, ...] = ()
    human_review_required: bool = True
    provider_call_permitted: bool = False
    automatic_fallback_permitted: bool = False
    execution_permitted: bool = False
    canonical_promotion_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonblank("proposal_id", self.proposal_id)
        _require_nonblank("requested_model_id", self.requested_model_id)
        _require_nonblank("requested_provider_id", self.requested_provider_id)
        _require_nonblank("rationale", self.rationale)
        _require_string_sequence("fallback_model_ids", self.fallback_model_ids)
        if self.human_review_required is not True:
            raise ValueError("human_review_required must remain True")
        if self.status is RoutingDecisionStatus.APPROVED_BY_HUMAN:
            raise ValueError("M0-C proposals cannot be pre-approved")
        if self.task_context.secret_bearing and self.status is not RoutingDecisionStatus.REJECTED_BY_POLICY:
            raise ValueError("secret-bearing tasks must be rejected by policy")
        if self.task_context.canonical_task and _free_or_unknown_provider(self.provider_class, self.trust_level):
            raise ValueError("free or unknown providers cannot be proposed for canonical tasks")
        _enforce_no_active_authority(
            self.provider_call_permitted,
            self.automatic_fallback_permitted,
            self.execution_permitted,
            self.canonical_promotion_permitted,
        )


@dataclass(frozen=True)
class ModelSelectionApproval:
    approval_id: str
    proposal_id: str
    reviewer_human_id: str
    approved_provider_id: str
    approved_model_id: str
    timestamp_utc: str
    approval_scope: str
    status: RoutingDecisionStatus = RoutingDecisionStatus.APPROVED_BY_HUMAN
    provider_call_permitted: bool = False
    automatic_fallback_permitted: bool = False
    execution_permitted: bool = False
    canonical_promotion_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonblank("approval_id", self.approval_id)
        _require_nonblank("proposal_id", self.proposal_id)
        _require_nonblank("reviewer_human_id", self.reviewer_human_id)
        _require_nonblank("approved_provider_id", self.approved_provider_id)
        _require_nonblank("approved_model_id", self.approved_model_id)
        _require_nonblank("timestamp_utc", self.timestamp_utc)
        _require_nonblank("approval_scope", self.approval_scope)
        if self.status is not RoutingDecisionStatus.APPROVED_BY_HUMAN:
            raise ValueError("approval status must be APPROVED_BY_HUMAN")
        _enforce_no_active_authority(
            self.provider_call_permitted,
            self.automatic_fallback_permitted,
            self.execution_permitted,
            self.canonical_promotion_permitted,
        )


@dataclass(frozen=True)
class ModelRoutingDecision:
    decision_id: str
    proposal_id: str
    provider_id: str
    model_id: str
    reason: str
    status: RoutingDecisionStatus = RoutingDecisionStatus.REQUIRES_HUMAN_APPROVAL
    human_review_required: bool = True
    audit_log_required: bool = True
    provider_call_permitted: bool = False
    automatic_fallback_permitted: bool = False
    execution_permitted: bool = False
    canonical_promotion_permitted: bool = False

    def __post_init__(self) -> None:
        _require_nonblank("decision_id", self.decision_id)
        _require_nonblank("proposal_id", self.proposal_id)
        _require_nonblank("provider_id", self.provider_id)
        _require_nonblank("model_id", self.model_id)
        _require_nonblank("reason", self.reason)
        if self.human_review_required is not True:
            raise ValueError("human_review_required must remain True")
        if self.audit_log_required is not True:
            raise ValueError("audit_log_required must remain True")
        if self.status is RoutingDecisionStatus.APPROVED_BY_HUMAN:
            raise ValueError("routing decisions cannot authorize provider calls in M0-C")
        _enforce_no_active_authority(
            self.provider_call_permitted,
            self.automatic_fallback_permitted,
            self.execution_permitted,
            self.canonical_promotion_permitted,
        )
