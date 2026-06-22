from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.provider_request_review import (
    PROVIDER_REQUEST_BOUNDARY_WARNINGS,
    PROVIDER_REQUEST_REVIEW,
    PROVIDER_REQUEST_REVIEW_BLOCKED,
    PROVIDER_REQUEST_REVIEW_INVALID,
    PROVIDER_REQUEST_REVIEW_READY,
    PROVIDER_REQUEST_REVIEW_SCHEMA_VERSION,
    REQUEST_POLICY_MATERIAL,
    ProviderRequestReview,
)


PROVIDER_LIVE_READINESS_REVIEW = "PROVIDER_LIVE_READINESS_REVIEW"
PROVIDER_LIVE_READINESS_REVIEW_SCHEMA_VERSION = "1.0"
PROVIDER_LIVE_READINESS_REVIEW_READY = "provider_live_readiness_review_ready"
PROVIDER_LIVE_READINESS_REVIEW_BLOCKED = "blocked"
PROVIDER_LIVE_READINESS_REVIEW_INVALID = "invalid"
LIVE_TARGET_LABEL = "generic_provider_live_future_review"
FUTURE_PROVIDER_HINT = "openrouter_future_candidate_review_only"
LIVE_READINESS_STATUS = "not_live_review_only"
LIVE_READINESS_POLICY_MATERIAL = (
    "zero_cost_review_only",
    "openrouter_future_candidate_review_only",
    "no_provider_live_enabled",
    "no_provider_configured",
    "no_api_key_loading",
    "no_secret_loading",
    "no_environment_variable_reads",
    "no_env_file_reads",
    "no_network_clients",
    "no_endpoints",
    "no_prompt_sending",
    "no_model_call",
    "no_provider_call",
    "no_execution",
    "no_dispatch",
    "no_artifact_writing",
    "future_provider_live_requires_separate_design_review",
    "future_openrouter_adapter_contract_required",
    "future_key_boundary_required",
    "future_cost_guard_required",
    "future_manual_one_shot_test_required",
    "future_provider_live_requires_explicit_human_approval",
)
PROVIDER_LIVE_READINESS_WARNINGS = (
    "This is not Provider Live or OpenRouter Live. It enables no provider or model call, API key, secret, environment read, endpoint, network client, prompt sending, execution, dispatch, authority, or cost-generating path.",
    "OpenRouter is a future candidate label only; a separate adapter contract, key boundary, cost guard, manual one-shot test plan, and explicit human approval are required before any future live design may be reviewed.",
)
PROVIDER_LIVE_READINESS_REVIEW_NEXT = (
    "Do not proceed to real Provider Live without a separate design review.",
    "Do not add API keys, secrets, environment reads, endpoints, or network clients in this review.",
    "Do not create cost-generating behavior.",
    "Review a separate inert OpenRouter adapter contract before any live call.",
    "Review a separate key boundary and cost guard.",
    "Review a separate manual one-shot test plan with explicit human approval.",
)
PROVIDER_LIVE_READINESS_BOUNDARY_TEXT = (
    "note: provider live readiness review only\n"
    "note: not Provider Live or OpenRouter Live\n"
    "note: OpenRouter is a future candidate label only\n"
    "note: no provider or model call and no prompt sending\n"
    "note: no API key, secret, environment, endpoint, or network access\n"
    "note: zero-cost and not cost-generating\n"
    "note: not an execution instruction\n"
    "note: no authority granted"
)
_MAX_COLLECTION_ITEMS = 40
_MAX_ITEM_CHARS = 512
_MAX_COLLECTION_CHARS = 8192
_INERT_FLAG_NAMES = (
    "authority_granted",
    "provider_live_enabled",
    "openrouter_live_enabled",
    "provider_configured",
    "provider_call_allowed",
    "model_call_allowed",
    "prompt_send_allowed",
    "api_key_loaded",
    "secret_loaded",
    "environment_variables_read",
    "env_file_read",
    "endpoint_configured",
    "network_client_created",
    "cost_generating_path_created",
    "execution_allowed",
    "dispatch_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "merge_authority_granted",
    "review_executes_anything",
)
_SOURCE_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "provider_live_enabled",
    "real_provider_request_created",
    "request_payload_created",
    "prompt_sent",
    "model_call_created",
    "endpoint_configured",
    "network_client_created",
    "secret_loaded",
    "api_key_loaded",
    "credential_accessed",
    "environment_variables_read",
    "env_file_read",
    "provider_config_created",
    "provider_config_read",
    "provider_config_mutated",
    "secret_config_created",
    "secret_config_read",
    "secret_config_mutated",
    "platform_integration_created",
    "organization_id_used",
    "project_id_used",
    "paid_api_used",
    "cost_generating_path_created",
    "merge_authority_granted",
    "review_executes_anything",
)
_SOURCE_FIELDS = {
    "object_type", "schema_version", "state", "source_secret_boundary_state",
    "source_provider_config_state", "source_prompt_packet_state",
    "source_handoff_state", "source_implication_state", "source_readiness_state",
    "decision_id", "decision_hash", "decision_status", "bundle_id", "bundle_hash",
    "request_policy_material", "blockers", "warnings", "review_context",
    "review_next", "constraints", "boundary_text", "is_review_only",
    *_SOURCE_INERT_FLAG_NAMES,
}


@dataclass(frozen=True)
class _CanonicalProviderRequestReview:
    state: str
    source_secret_boundary_state: str
    source_provider_config_state: str
    source_prompt_packet_state: str
    source_handoff_state: str
    source_implication_state: str
    source_readiness_state: str
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    review_context: tuple[str, ...]
    review_next: tuple[str, ...]
    constraints: tuple[str, ...]


@dataclass(frozen=True)
class ProviderLiveReadinessReview:
    state: str
    source_provider_request_state: str
    source_secret_boundary_state: str
    source_provider_config_state: str
    source_prompt_packet_state: str
    source_handoff_state: str
    source_implication_state: str
    source_readiness_state: str
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    live_target_label: str
    future_provider_hint: str
    live_readiness_status: str
    live_readiness_policy_material: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    review_context: tuple[str, ...]
    review_next: tuple[str, ...]
    constraints: tuple[str, ...]
    boundary_text: str
    is_review_only: bool = True
    authority_granted: bool = False
    provider_live_enabled: bool = False
    openrouter_live_enabled: bool = False
    provider_configured: bool = False
    provider_call_allowed: bool = False
    model_call_allowed: bool = False
    prompt_send_allowed: bool = False
    api_key_loaded: bool = False
    secret_loaded: bool = False
    environment_variables_read: bool = False
    env_file_read: bool = False
    endpoint_configured: bool = False
    network_client_created: bool = False
    cost_generating_path_created: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    merge_authority_granted: bool = False
    review_executes_anything: bool = False
    object_type: str = PROVIDER_LIVE_READINESS_REVIEW
    schema_version: str = PROVIDER_LIVE_READINESS_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        state = _normalize_state(self.state)
        blockers = _bounded_text_tuple(self.blockers, "blockers")
        warnings = _merge(PROVIDER_LIVE_READINESS_WARNINGS, self.warnings, "warnings")
        review_context = _bounded_text_tuple(self.review_context, "review_context")
        review_next = _merge(PROVIDER_LIVE_READINESS_REVIEW_NEXT, self.review_next, "review_next")
        constraints = _merge(LIVE_READINESS_POLICY_MATERIAL, self.constraints, "constraints")

        object.__setattr__(self, "state", state)
        object.__setattr__(self, "live_target_label", LIVE_TARGET_LABEL)
        object.__setattr__(self, "future_provider_hint", FUTURE_PROVIDER_HINT)
        object.__setattr__(self, "live_readiness_status", LIVE_READINESS_STATUS)
        object.__setattr__(self, "live_readiness_policy_material", LIVE_READINESS_POLICY_MATERIAL)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "review_next", review_next)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "boundary_text", PROVIDER_LIVE_READINESS_BOUNDARY_TEXT)
        object.__setattr__(self, "is_review_only", True)
        for name in _INERT_FLAG_NAMES:
            object.__setattr__(self, name, False)
        object.__setattr__(self, "object_type", PROVIDER_LIVE_READINESS_REVIEW)
        object.__setattr__(self, "schema_version", PROVIDER_LIVE_READINESS_REVIEW_SCHEMA_VERSION)

        if state == PROVIDER_LIVE_READINESS_REVIEW_READY:
            if blockers or not review_context:
                raise ValueError("ready live readiness review requires context and no blockers")
            object.__setattr__(self, "source_provider_request_state", PROVIDER_REQUEST_REVIEW_READY)
            object.__setattr__(self, "blockers", ())
            object.__setattr__(self, "review_context", review_context)
            for name in (
                "source_secret_boundary_state", "source_provider_config_state",
                "source_prompt_packet_state", "source_handoff_state",
                "source_implication_state", "source_readiness_state", "decision_id",
                "decision_hash", "decision_status", "bundle_id", "bundle_hash",
            ):
                object.__setattr__(self, name, _required_text(getattr(self, name), name))
            return

        if not blockers:
            raise ValueError("fail-closed live readiness review requires blockers")
        source_state = (
            PROVIDER_REQUEST_REVIEW_BLOCKED
            if state == PROVIDER_LIVE_READINESS_REVIEW_BLOCKED
            else PROVIDER_REQUEST_REVIEW_INVALID
        )
        object.__setattr__(self, "source_provider_request_state", source_state)
        for name in (
            "source_secret_boundary_state", "source_provider_config_state",
            "source_prompt_packet_state", "source_handoff_state",
            "source_implication_state", "source_readiness_state", "decision_id",
            "decision_hash", "decision_status", "bundle_id", "bundle_hash",
        ):
            object.__setattr__(self, name, "")
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "review_context", ())

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "state": self.state,
            "source_provider_request_state": self.source_provider_request_state,
            "source_secret_boundary_state": self.source_secret_boundary_state,
            "source_provider_config_state": self.source_provider_config_state,
            "source_prompt_packet_state": self.source_prompt_packet_state,
            "source_handoff_state": self.source_handoff_state,
            "source_implication_state": self.source_implication_state,
            "source_readiness_state": self.source_readiness_state,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "live_target_label": self.live_target_label,
            "future_provider_hint": self.future_provider_hint,
            "live_readiness_status": self.live_readiness_status,
            "live_readiness_policy_material": list(self.live_readiness_policy_material),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "review_context": list(self.review_context),
            "review_next": list(self.review_next),
            "constraints": list(self.constraints),
            "boundary_text": self.boundary_text,
            "is_review_only": self.is_review_only,
        }
        result.update({name: getattr(self, name) for name in _INERT_FLAG_NAMES})
        return result


def build_provider_live_readiness_review(source: object) -> ProviderLiveReadinessReview:
    try:
        request_review = _canonical_source(source)
    except ValueError as error:
        return _failed(PROVIDER_LIVE_READINESS_REVIEW_INVALID, (str(error),), (), ())

    if request_review.state != PROVIDER_REQUEST_REVIEW_READY:
        state = (
            PROVIDER_LIVE_READINESS_REVIEW_BLOCKED
            if request_review.state == PROVIDER_REQUEST_REVIEW_BLOCKED
            else PROVIDER_LIVE_READINESS_REVIEW_INVALID
        )
        return _failed(
            state,
            request_review.blockers or ("source provider request review is not ready",),
            request_review.review_next,
            request_review.warnings,
        )

    return ProviderLiveReadinessReview(
        state=PROVIDER_LIVE_READINESS_REVIEW_READY,
        source_provider_request_state=request_review.state,
        source_secret_boundary_state=request_review.source_secret_boundary_state,
        source_provider_config_state=request_review.source_provider_config_state,
        source_prompt_packet_state=request_review.source_prompt_packet_state,
        source_handoff_state=request_review.source_handoff_state,
        source_implication_state=request_review.source_implication_state,
        source_readiness_state=request_review.source_readiness_state,
        decision_id=request_review.decision_id,
        decision_hash=request_review.decision_hash,
        decision_status=request_review.decision_status,
        bundle_id=request_review.bundle_id,
        bundle_hash=request_review.bundle_hash,
        live_target_label=LIVE_TARGET_LABEL,
        future_provider_hint=FUTURE_PROVIDER_HINT,
        live_readiness_status=LIVE_READINESS_STATUS,
        live_readiness_policy_material=LIVE_READINESS_POLICY_MATERIAL,
        blockers=(),
        warnings=request_review.warnings,
        review_context=request_review.review_context,
        review_next=request_review.review_next,
        constraints=request_review.constraints,
        boundary_text=PROVIDER_LIVE_READINESS_BOUNDARY_TEXT,
    )


def provider_live_readiness_review_to_dict(review: object) -> dict[str, Any]:
    if not isinstance(review, ProviderLiveReadinessReview):
        raise ValueError("review must be a ProviderLiveReadinessReview")
    return review.to_dict()


def render_provider_live_readiness_review(review: object) -> str:
    if not isinstance(review, ProviderLiveReadinessReview):
        raise ValueError("review must be a ProviderLiveReadinessReview")
    lines = (
        f"provider_live_readiness_review: {review.state}",
        "is_review_only: true",
        f"live_readiness_status: {review.live_readiness_status}",
        f"future_provider_hint: {review.future_provider_hint}",
        f"decision_id: {review.decision_id}",
        f"decision_hash: {review.decision_hash}",
        f"bundle_id: {review.bundle_id}",
        f"bundle_hash: {review.bundle_hash}",
        f"blockers: {' | '.join(review.blockers)}",
        f"review_context: {' | '.join(review.review_context)}",
        f"review_next: {' | '.join(review.review_next)}",
        f"constraints: {' | '.join(review.constraints)}",
        f"warnings: {' | '.join(review.warnings)}",
        review.boundary_text,
    )
    return "\n".join(lines)


def _canonical_source(source: object) -> _CanonicalProviderRequestReview:
    if isinstance(source, ProviderRequestReview):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a provider request review")
    if set(mapping) != _SOURCE_FIELDS:
        raise ValueError("source provider request fields do not match the canonical schema")
    if mapping["object_type"] != PROVIDER_REQUEST_REVIEW:
        raise ValueError("source provider request object type is invalid")
    if mapping["schema_version"] != PROVIDER_REQUEST_REVIEW_SCHEMA_VERSION:
        raise ValueError("source provider request schema version is invalid")
    if mapping["is_review_only"] is not True:
        raise ValueError("source provider request is not canonical")
    if any(mapping[name] is not False for name in _SOURCE_INERT_FLAG_NAMES):
        raise ValueError("source provider request is not canonical")
    if tuple(mapping["request_policy_material"]) != REQUEST_POLICY_MATERIAL:
        raise ValueError("source provider request is not canonical")
    warnings = _bounded_text_tuple(mapping["warnings"], "warnings")
    constraints = _bounded_text_tuple(mapping["constraints"], "constraints")
    if any(item not in warnings for item in PROVIDER_REQUEST_BOUNDARY_WARNINGS):
        raise ValueError("source provider request is not canonical")
    if any(item not in constraints for item in REQUEST_POLICY_MATERIAL):
        raise ValueError("source provider request is not canonical")

    state = mapping["state"]
    if state not in (
        PROVIDER_REQUEST_REVIEW_READY,
        PROVIDER_REQUEST_REVIEW_BLOCKED,
        PROVIDER_REQUEST_REVIEW_INVALID,
    ):
        raise ValueError("source provider request is malformed")
    blockers = _bounded_text_tuple(mapping["blockers"], "blockers")
    review_context = _bounded_text_tuple(mapping["review_context"], "review_context")
    review_next = _bounded_text_tuple(mapping["review_next"], "review_next")
    text_names = (
        "source_secret_boundary_state", "source_provider_config_state",
        "source_prompt_packet_state", "source_handoff_state", "source_implication_state",
        "source_readiness_state", "decision_id", "decision_hash", "decision_status",
        "bundle_id", "bundle_hash",
    )
    if any(not isinstance(mapping[name], str) for name in text_names):
        raise ValueError("source provider request is malformed")
    if state == PROVIDER_REQUEST_REVIEW_READY:
        if blockers or not review_context or not review_next:
            raise ValueError("source provider request is not canonical")
        if any(not mapping[name].strip() for name in text_names):
            raise ValueError("source provider request is not canonical")
    else:
        if not blockers or review_context:
            raise ValueError("source provider request is not canonical")
        if mapping["source_secret_boundary_state"] != state:
            raise ValueError("source provider request is not canonical")
        empty_names = tuple(
            name for name in text_names if name != "source_secret_boundary_state"
        )
        if any(mapping[name] != "" for name in empty_names):
            raise ValueError("source provider request is not canonical")

    return _CanonicalProviderRequestReview(
        state=state,
        source_secret_boundary_state=mapping["source_secret_boundary_state"],
        source_provider_config_state=mapping["source_provider_config_state"],
        source_prompt_packet_state=mapping["source_prompt_packet_state"],
        source_handoff_state=mapping["source_handoff_state"],
        source_implication_state=mapping["source_implication_state"],
        source_readiness_state=mapping["source_readiness_state"],
        decision_id=mapping["decision_id"], decision_hash=mapping["decision_hash"],
        decision_status=mapping["decision_status"], bundle_id=mapping["bundle_id"],
        bundle_hash=mapping["bundle_hash"], blockers=blockers, warnings=warnings,
        review_context=review_context, review_next=review_next, constraints=constraints,
    )


def _failed(
    state: str,
    blockers: tuple[str, ...],
    review_next: tuple[str, ...],
    warnings: tuple[str, ...],
) -> ProviderLiveReadinessReview:
    return ProviderLiveReadinessReview(
        state=state,
        source_provider_request_state="",
        source_secret_boundary_state="",
        source_provider_config_state="",
        source_prompt_packet_state="",
        source_handoff_state="",
        source_implication_state="",
        source_readiness_state="",
        decision_id="", decision_hash="", decision_status="", bundle_id="", bundle_hash="",
        live_target_label=LIVE_TARGET_LABEL,
        future_provider_hint=FUTURE_PROVIDER_HINT,
        live_readiness_status=LIVE_READINESS_STATUS,
        live_readiness_policy_material=LIVE_READINESS_POLICY_MATERIAL,
        blockers=blockers,
        warnings=warnings,
        review_context=(),
        review_next=review_next,
        constraints=(),
        boundary_text=PROVIDER_LIVE_READINESS_BOUNDARY_TEXT,
    )


def _normalize_state(value: object) -> str:
    if value not in (
        PROVIDER_LIVE_READINESS_REVIEW_READY,
        PROVIDER_LIVE_READINESS_REVIEW_BLOCKED,
        PROVIDER_LIVE_READINESS_REVIEW_INVALID,
    ):
        raise ValueError("state must be a supported live readiness review state")
    return str(value)


def _merge(required: tuple[str, ...], supplied: object, field_name: str) -> tuple[str, ...]:
    values = list(_bounded_text_tuple(supplied, field_name))
    for item in required:
        if item not in values:
            values.append(item)
    return _bounded_text_tuple(values, field_name)


def _bounded_text_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or len(value) > _MAX_COLLECTION_ITEMS:
        raise ValueError(f"{field_name} must be a bounded tuple or list")
    values = tuple(_required_text(item, field_name) for item in value)
    if any(len(item) > _MAX_ITEM_CHARS for item in values):
        raise ValueError(f"{field_name} contains an oversized item")
    if sum(len(item) for item in values) > _MAX_COLLECTION_CHARS:
        raise ValueError(f"{field_name} exceeds the total size limit")
    return values


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must contain non-empty strings")
    return value.strip()
