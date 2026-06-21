from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.decision_implication_review import READY_FOR_IMPLICATION_REVIEW
from runtime.decision_review_handoff import HANDOFF_READY
from runtime.prompt_packet_review import PROMPT_PACKET_REVIEW_READY
from runtime.provider_config_review import (
    PROVIDER_CONFIG_REVIEW_BLOCKED,
    PROVIDER_CONFIG_REVIEW_INVALID,
    PROVIDER_CONFIG_REVIEW_READY,
)
from runtime.secret_boundary_review import (
    SECRET_BOUNDARY_REVIEW,
    SECRET_BOUNDARY_REVIEW_BLOCKED,
    SECRET_BOUNDARY_TEXT,
    SECRET_BOUNDARY_WARNINGS,
    SECRET_BOUNDARY_REVIEW_INVALID,
    SECRET_BOUNDARY_REVIEW_READY,
    SECRET_BOUNDARY_REVIEW_SCHEMA_VERSION,
    SECRET_POLICY_MATERIAL,
    SecretBoundaryReview,
)


PROVIDER_REQUEST_REVIEW = "PROVIDER_REQUEST_REVIEW"
PROVIDER_REQUEST_REVIEW_SCHEMA_VERSION = "1.0"
PROVIDER_REQUEST_REVIEW_READY = "provider_request_review_ready"
PROVIDER_REQUEST_REVIEW_BLOCKED = "blocked"
PROVIDER_REQUEST_REVIEW_INVALID = "invalid"
REQUEST_POLICY_MATERIAL = (
    "blocked_by_default",
    "generic_provider_request_review_only",
    "no_live_provider_request",
    "no_request_payload_created",
    "no_prompt_sending",
    "no_model_call",
    "no_provider_call",
    "no_api_key_loading",
    "no_secret_loading",
    "no_environment_variable_reads",
    "no_env_file_reads",
    "no_provider_endpoint_material",
    "no_network_client_material",
    "no_platform_integration",
    "no_cost_generating_path",
    "human_review_required",
    "future_provider_request_requires_separate_boundary_review",
)
PROVIDER_REQUEST_BOUNDARY_WARNINGS = (
    "This generic provider request review object is not a real provider request, request payload, provider live connection, provider or model call, prompt sending, secret or API-key handling, endpoint configuration, platform integration, paid API path, dispatch, execution, approval, permission, or merge authority.",
    "No provider-specific configuration, organization or project identifier, endpoint, credential, secret, API key, environment value, network client, send instruction, or cost-generating material is present.",
)
PROVIDER_REQUEST_BOUNDARY_TEXT = (
    "note: generic provider request review only\n"
    "note: not a real provider request or request payload\n"
    "note: no provider live, provider call, or model call\n"
    "note: no prompt sending\n"
    "note: no secret, API key, or environment reads\n"
    "note: no endpoint, network client, or platform integration\n"
    "note: no paid API or cost-generating path\n"
    "note: not an execution instruction\n"
    "note: no authority granted"
)
_MAX_COLLECTION_ITEMS = 40
_MAX_ITEM_CHARS = 512
_MAX_COLLECTION_CHARS = 8192
_FORBIDDEN_INHERITED_MATERIAL = (
    "http://",
    "https://",
    "authorization:",
    "bearer ",
    "api_key=",
    "api-key:",
    "apikey=",
    "password=",
    "passwd=",
    "secret=",
    "token=",
    "credential=",
    "client_secret",
    "private_key",
    "private key",
    "-----begin",
    "export ",
    "setenv ",
    "org_",
    "proj_",
    "organization_id",
    "organization id",
    "project_id",
    "project id",
    "platform_id",
    "platform integration",
    "billing",
    "paid api",
    "cost=",
    "cost generating",
    "cost-generating",
    "sk-",
    "ghp_",
    "xoxb-",
    "openai",
    "anthropic",
    "gemini",
    "gpt-",
    "claude-",
    "request body",
    "message payload",
    '"messages"',
    '"model"',
    "send prompt",
    "execute command",
    "dispatch request",
)
_INERT_FLAG_NAMES = (
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
_SECRET_REVIEW_FIELDS = {
    "object_type",
    "schema_version",
    "state",
    "source_provider_config_state",
    "source_prompt_packet_state",
    "source_handoff_state",
    "source_implication_state",
    "source_readiness_state",
    "decision_id",
    "decision_hash",
    "decision_status",
    "bundle_id",
    "bundle_hash",
    "secret_policy_material",
    "blockers",
    "warnings",
    "review_context",
    "review_next",
    "constraints",
    "boundary_text",
    "is_review_only",
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "real_secret_boundary_created",
    "secret_config_created",
    "secret_config_read",
    "secret_config_mutated",
    "secret_loaded",
    "secret_read",
    "secret_stored",
    "secret_displayed",
    "api_key_loaded",
    "api_key_accessed",
    "api_key_stored",
    "credential_accessed",
    "environment_variables_read",
    "env_file_read",
    "real_provider_config_created",
    "provider_config_read",
    "provider_config_mutated",
    "provider_live_enabled",
    "provider_request_created",
    "prompt_sent",
    "endpoint_configured",
    "network_client_created",
    "merge_authority_granted",
    "review_executes_anything",
}
_SECRET_INERT_FLAG_NAMES = (
    "authority_granted",
    "execution_allowed",
    "dispatch_allowed",
    "provider_call_allowed",
    "artifact_write_allowed",
    "persistence_allowed",
    "real_secret_boundary_created",
    "secret_config_created",
    "secret_config_read",
    "secret_config_mutated",
    "secret_loaded",
    "secret_read",
    "secret_stored",
    "secret_displayed",
    "api_key_loaded",
    "api_key_accessed",
    "api_key_stored",
    "credential_accessed",
    "environment_variables_read",
    "env_file_read",
    "real_provider_config_created",
    "provider_config_read",
    "provider_config_mutated",
    "provider_live_enabled",
    "provider_request_created",
    "prompt_sent",
    "endpoint_configured",
    "network_client_created",
    "merge_authority_granted",
    "review_executes_anything",
)


@dataclass(frozen=True)
class _CanonicalSecretReview:
    state: str
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
    secret_policy_material: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    review_context: tuple[str, ...]
    review_next: tuple[str, ...]
    constraints: tuple[str, ...]


@dataclass(frozen=True)
class ProviderRequestReview:
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
    request_policy_material: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    review_context: tuple[str, ...]
    review_next: tuple[str, ...]
    constraints: tuple[str, ...]
    boundary_text: str
    is_review_only: bool = True
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    provider_live_enabled: bool = False
    real_provider_request_created: bool = False
    request_payload_created: bool = False
    prompt_sent: bool = False
    model_call_created: bool = False
    endpoint_configured: bool = False
    network_client_created: bool = False
    secret_loaded: bool = False
    api_key_loaded: bool = False
    credential_accessed: bool = False
    environment_variables_read: bool = False
    env_file_read: bool = False
    provider_config_created: bool = False
    provider_config_read: bool = False
    provider_config_mutated: bool = False
    secret_config_created: bool = False
    secret_config_read: bool = False
    secret_config_mutated: bool = False
    platform_integration_created: bool = False
    organization_id_used: bool = False
    project_id_used: bool = False
    paid_api_used: bool = False
    cost_generating_path_created: bool = False
    merge_authority_granted: bool = False
    review_executes_anything: bool = False
    object_type: str = PROVIDER_REQUEST_REVIEW
    schema_version: str = PROVIDER_REQUEST_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        state = _normalize_state(self.state)
        blockers = _bounded_text_tuple(self.blockers, "blockers")
        warnings = _bounded_text_tuple(self.warnings, "warnings")
        review_context = _bounded_text_tuple(self.review_context, "review_context")
        review_next = _bounded_text_tuple(self.review_next, "review_next")
        constraints = _bounded_text_tuple(self.constraints, "constraints")
        inherited_warnings = tuple(
            warning for warning in warnings if warning not in SECRET_BOUNDARY_WARNINGS
        )
        for values in (blockers, inherited_warnings, review_context, review_next, constraints):
            _validate_inherited_material(values)
        warnings = _merge_warnings(warnings)
        constraints = _merge_constraints(constraints)

        object.__setattr__(self, "state", state)
        object.__setattr__(self, "request_policy_material", REQUEST_POLICY_MATERIAL)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "review_next", review_next)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "boundary_text", PROVIDER_REQUEST_BOUNDARY_TEXT)
        object.__setattr__(self, "is_review_only", True)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", PROVIDER_REQUEST_REVIEW)
        object.__setattr__(self, "schema_version", PROVIDER_REQUEST_REVIEW_SCHEMA_VERSION)

        if state == PROVIDER_REQUEST_REVIEW_READY:
            if blockers:
                raise ValueError("ready provider request review cannot contain blockers")
            if not review_context or not review_next:
                raise ValueError("ready provider request review requires bounded review context")
            object.__setattr__(self, "source_secret_boundary_state", SECRET_BOUNDARY_REVIEW_READY)
            object.__setattr__(self, "source_provider_config_state", PROVIDER_CONFIG_REVIEW_READY)
            object.__setattr__(self, "source_prompt_packet_state", PROMPT_PACKET_REVIEW_READY)
            object.__setattr__(self, "source_handoff_state", HANDOFF_READY)
            object.__setattr__(self, "source_implication_state", READY_FOR_IMPLICATION_REVIEW)
            object.__setattr__(self, "source_readiness_state", READY_FOR_IMPLICATION_REVIEW)
            object.__setattr__(self, "blockers", ())
            object.__setattr__(self, "review_context", review_context)
            for field_name in (
                "decision_id",
                "decision_hash",
                "decision_status",
                "bundle_id",
                "bundle_hash",
            ):
                object.__setattr__(
                    self,
                    field_name,
                    _required_text(getattr(self, field_name), field_name),
                )
            return

        if not blockers:
            raise ValueError("fail-closed provider request review requires blockers")
        source_state = (
            SECRET_BOUNDARY_REVIEW_BLOCKED
            if state == PROVIDER_REQUEST_REVIEW_BLOCKED
            else SECRET_BOUNDARY_REVIEW_INVALID
        )
        object.__setattr__(self, "source_secret_boundary_state", source_state)
        for field_name in (
            "source_provider_config_state",
            "source_prompt_packet_state",
            "source_handoff_state",
            "source_implication_state",
            "source_readiness_state",
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
        ):
            object.__setattr__(self, field_name, "")
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "review_context", ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "state": self.state,
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
            "request_policy_material": list(self.request_policy_material),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "review_context": list(self.review_context),
            "review_next": list(self.review_next),
            "constraints": list(self.constraints),
            "boundary_text": self.boundary_text,
            "is_review_only": self.is_review_only,
            "authority_granted": self.authority_granted,
            "execution_allowed": self.execution_allowed,
            "dispatch_allowed": self.dispatch_allowed,
            "provider_call_allowed": self.provider_call_allowed,
            "artifact_write_allowed": self.artifact_write_allowed,
            "persistence_allowed": self.persistence_allowed,
            "provider_live_enabled": self.provider_live_enabled,
            "real_provider_request_created": self.real_provider_request_created,
            "request_payload_created": self.request_payload_created,
            "prompt_sent": self.prompt_sent,
            "model_call_created": self.model_call_created,
            "endpoint_configured": self.endpoint_configured,
            "network_client_created": self.network_client_created,
            "secret_loaded": self.secret_loaded,
            "api_key_loaded": self.api_key_loaded,
            "credential_accessed": self.credential_accessed,
            "environment_variables_read": self.environment_variables_read,
            "env_file_read": self.env_file_read,
            "provider_config_created": self.provider_config_created,
            "provider_config_read": self.provider_config_read,
            "provider_config_mutated": self.provider_config_mutated,
            "secret_config_created": self.secret_config_created,
            "secret_config_read": self.secret_config_read,
            "secret_config_mutated": self.secret_config_mutated,
            "platform_integration_created": self.platform_integration_created,
            "organization_id_used": self.organization_id_used,
            "project_id_used": self.project_id_used,
            "paid_api_used": self.paid_api_used,
            "cost_generating_path_created": self.cost_generating_path_created,
            "merge_authority_granted": self.merge_authority_granted,
            "review_executes_anything": self.review_executes_anything,
        }


def build_provider_request_review(source: object) -> ProviderRequestReview:
    try:
        secret_review = _canonical_secret_review(source)
    except ValueError as error:
        return _failed_review(PROVIDER_REQUEST_REVIEW_INVALID, (str(error),), (), ())

    try:
        inherited_warnings = tuple(
            warning
            for warning in secret_review.warnings
            if warning not in SECRET_BOUNDARY_WARNINGS
        )
        for values in (
            secret_review.secret_policy_material,
            secret_review.blockers,
            inherited_warnings,
            secret_review.review_context,
            secret_review.review_next,
            secret_review.constraints,
        ):
            _validate_inherited_material(values)
    except ValueError:
        return _failed_review(
            PROVIDER_REQUEST_REVIEW_INVALID,
            ("source secret boundary contains forbidden inherited material",),
            (),
            (),
        )

    if secret_review.state != SECRET_BOUNDARY_REVIEW_READY:
        blockers = secret_review.blockers or ("source secret boundary review is not ready",)
        state = (
            PROVIDER_REQUEST_REVIEW_BLOCKED
            if secret_review.state == SECRET_BOUNDARY_REVIEW_BLOCKED
            else PROVIDER_REQUEST_REVIEW_INVALID
        )
        return _failed_review(state, blockers, secret_review.review_next, secret_review.warnings)

    try:
        return ProviderRequestReview(
            state=PROVIDER_REQUEST_REVIEW_READY,
            source_secret_boundary_state=secret_review.state,
            source_provider_config_state=secret_review.source_provider_config_state,
            source_prompt_packet_state=secret_review.source_prompt_packet_state,
            source_handoff_state=secret_review.source_handoff_state,
            source_implication_state=secret_review.source_implication_state,
            source_readiness_state=secret_review.source_readiness_state,
            decision_id=secret_review.decision_id,
            decision_hash=secret_review.decision_hash,
            decision_status=secret_review.decision_status,
            bundle_id=secret_review.bundle_id,
            bundle_hash=secret_review.bundle_hash,
            request_policy_material=REQUEST_POLICY_MATERIAL,
            blockers=(),
            warnings=secret_review.warnings,
            review_context=secret_review.review_context,
            review_next=secret_review.review_next,
            constraints=secret_review.constraints,
            boundary_text=PROVIDER_REQUEST_BOUNDARY_TEXT,
        )
    except ValueError:
        return _failed_review(
            PROVIDER_REQUEST_REVIEW_INVALID,
            ("source secret boundary cannot produce a safe provider request review",),
            (),
            (),
        )


def provider_request_review_to_dict(review: object) -> dict[str, Any]:
    if not isinstance(review, ProviderRequestReview):
        raise ValueError("review must be a ProviderRequestReview")
    return review.to_dict()


def render_provider_request_review(review: object) -> str:
    if not isinstance(review, ProviderRequestReview):
        raise ValueError("review must be a ProviderRequestReview")
    blockers = " | ".join(review.blockers)
    warnings = " | ".join(review.warnings)
    constraints = " | ".join(review.constraints)
    review_next = " | ".join(review.review_next)
    policy = " | ".join(review.request_policy_material)
    if review.state != PROVIDER_REQUEST_REVIEW_READY:
        return (
            f"provider_request_review: {review.state}\n"
            "is_review_only: true\n"
            f"request_policy_material: {policy}\n"
            f"blockers: {blockers}\n"
            f"constraints: {constraints}\n"
            f"warnings: {warnings}\n"
            f"{review.boundary_text}"
        )
    context = " | ".join(review.review_context)
    return (
        "provider_request_review: provider_request_review_ready\n"
        "is_review_only: true\n"
        f"source_secret_boundary_state: {review.source_secret_boundary_state}\n"
        f"source_provider_config_state: {review.source_provider_config_state}\n"
        f"source_prompt_packet_state: {review.source_prompt_packet_state}\n"
        f"source_handoff_state: {review.source_handoff_state}\n"
        f"source_implication_state: {review.source_implication_state}\n"
        f"source_readiness_state: {review.source_readiness_state}\n"
        f"decision_id: {review.decision_id}\n"
        f"decision_hash: {review.decision_hash}\n"
        f"decision_status: {review.decision_status}\n"
        f"bundle_id: {review.bundle_id}\n"
        f"bundle_hash: {review.bundle_hash}\n"
        f"request_policy_material: {policy}\n"
        f"review_context: {context}\n"
        f"review_next: {review_next}\n"
        f"constraints: {constraints}\n"
        f"warnings: {warnings}\n"
        f"{review.boundary_text}"
    )


def _canonical_secret_review(source: object) -> _CanonicalSecretReview:
    if isinstance(source, SecretBoundaryReview):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a secret boundary review")
    if set(mapping) != _SECRET_REVIEW_FIELDS:
        raise ValueError("source secret boundary fields do not match the canonical schema")
    if mapping["object_type"] != SECRET_BOUNDARY_REVIEW:
        raise ValueError("source secret boundary object type is invalid")
    if mapping["schema_version"] != SECRET_BOUNDARY_REVIEW_SCHEMA_VERSION:
        raise ValueError("source secret boundary schema version is invalid")
    if mapping["is_review_only"] is not True:
        raise ValueError("source secret boundary is not canonical")
    if any(mapping[field_name] is not False for field_name in _SECRET_INERT_FLAG_NAMES):
        raise ValueError("source secret boundary is not canonical")
    if mapping["boundary_text"] != SECRET_BOUNDARY_TEXT:
        raise ValueError("source secret boundary is not canonical")

    try:
        policy = _bounded_text_tuple(mapping["secret_policy_material"], "secret_policy_material")
        blockers = _bounded_text_tuple(mapping["blockers"], "blockers")
        warnings = _bounded_text_tuple(mapping["warnings"], "warnings")
        review_context = _bounded_text_tuple(mapping["review_context"], "review_context")
        review_next = _bounded_text_tuple(mapping["review_next"], "review_next")
        constraints = _bounded_text_tuple(mapping["constraints"], "constraints")
    except ValueError as error:
        raise ValueError("source secret boundary is malformed") from error
    if policy != SECRET_POLICY_MATERIAL:
        raise ValueError("source secret boundary is not canonical")
    if any(warning not in warnings for warning in SECRET_BOUNDARY_WARNINGS):
        raise ValueError("source secret boundary is not canonical")
    if any(constraint not in constraints for constraint in SECRET_POLICY_MATERIAL):
        raise ValueError("source secret boundary is not canonical")

    state = mapping["state"]
    if state not in (
        SECRET_BOUNDARY_REVIEW_READY,
        SECRET_BOUNDARY_REVIEW_BLOCKED,
        SECRET_BOUNDARY_REVIEW_INVALID,
    ):
        raise ValueError("source secret boundary is malformed")
    text_fields = (
        "source_provider_config_state",
        "source_prompt_packet_state",
        "source_handoff_state",
        "source_implication_state",
        "source_readiness_state",
        "decision_id",
        "decision_hash",
        "decision_status",
        "bundle_id",
        "bundle_hash",
    )
    if any(not isinstance(mapping[field_name], str) for field_name in text_fields):
        raise ValueError("source secret boundary is malformed")

    if state == SECRET_BOUNDARY_REVIEW_READY:
        expected_states = {
            "source_provider_config_state": PROVIDER_CONFIG_REVIEW_READY,
            "source_prompt_packet_state": PROMPT_PACKET_REVIEW_READY,
            "source_handoff_state": HANDOFF_READY,
            "source_implication_state": READY_FOR_IMPLICATION_REVIEW,
            "source_readiness_state": READY_FOR_IMPLICATION_REVIEW,
        }
        if any(mapping[name] != value for name, value in expected_states.items()):
            raise ValueError("source secret boundary is not canonical")
        if blockers or not review_context or not review_next:
            raise ValueError("source secret boundary is not canonical")
        for field_name in (
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
        ):
            if _required_text(mapping[field_name], field_name) != mapping[field_name]:
                raise ValueError("source secret boundary is not canonical")
    else:
        expected_provider_state = (
            PROVIDER_CONFIG_REVIEW_BLOCKED
            if state == SECRET_BOUNDARY_REVIEW_BLOCKED
            else PROVIDER_CONFIG_REVIEW_INVALID
        )
        if mapping["source_provider_config_state"] != expected_provider_state:
            raise ValueError("source secret boundary is not canonical")
        empty_fields = (
            "source_prompt_packet_state",
            "source_handoff_state",
            "source_implication_state",
            "source_readiness_state",
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
        )
        if any(mapping[field_name] != "" for field_name in empty_fields):
            raise ValueError("source secret boundary is not canonical")
        if not blockers or review_context:
            raise ValueError("source secret boundary is not canonical")

    return _CanonicalSecretReview(
        state=state,
        source_provider_config_state=mapping["source_provider_config_state"],
        source_prompt_packet_state=mapping["source_prompt_packet_state"],
        source_handoff_state=mapping["source_handoff_state"],
        source_implication_state=mapping["source_implication_state"],
        source_readiness_state=mapping["source_readiness_state"],
        decision_id=mapping["decision_id"],
        decision_hash=mapping["decision_hash"],
        decision_status=mapping["decision_status"],
        bundle_id=mapping["bundle_id"],
        bundle_hash=mapping["bundle_hash"],
        secret_policy_material=policy,
        blockers=blockers,
        warnings=warnings,
        review_context=review_context,
        review_next=review_next,
        constraints=constraints,
    )


def _failed_review(
    state: str,
    blockers: tuple[str, ...],
    review_next: tuple[str, ...],
    warnings: tuple[str, ...],
) -> ProviderRequestReview:
    return ProviderRequestReview(
        state=state,
        source_secret_boundary_state="",
        source_provider_config_state="",
        source_prompt_packet_state="",
        source_handoff_state="",
        source_implication_state="",
        source_readiness_state="",
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        request_policy_material=REQUEST_POLICY_MATERIAL,
        blockers=blockers,
        warnings=warnings,
        review_context=(),
        review_next=review_next,
        constraints=(),
        boundary_text=PROVIDER_REQUEST_BOUNDARY_TEXT,
    )


def _normalize_state(value: object) -> str:
    if value not in (
        PROVIDER_REQUEST_REVIEW_READY,
        PROVIDER_REQUEST_REVIEW_BLOCKED,
        PROVIDER_REQUEST_REVIEW_INVALID,
    ):
        raise ValueError("state must be a supported provider request review state")
    return str(value)


def _merge_warnings(value: object) -> tuple[str, ...]:
    warnings = list(_bounded_text_tuple(value, "warnings"))
    for warning in PROVIDER_REQUEST_BOUNDARY_WARNINGS:
        if warning not in warnings:
            warnings.append(warning)
    return _bounded_text_tuple(warnings, "warnings")


def _merge_constraints(value: object) -> tuple[str, ...]:
    constraints = list(_bounded_text_tuple(value, "constraints"))
    for constraint in REQUEST_POLICY_MATERIAL:
        if constraint not in constraints:
            constraints.append(constraint)
    return _bounded_text_tuple(constraints, "constraints")


def _validate_inherited_material(values: tuple[str, ...]) -> None:
    for value in values:
        normalized = value.casefold()
        if any(term in normalized for term in _FORBIDDEN_INHERITED_MATERIAL):
            raise ValueError("inherited review material contains forbidden request or platform material")


def _bounded_text_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be a tuple or list")
    if len(value) > _MAX_COLLECTION_ITEMS:
        raise ValueError(f"{field_name} exceeds the item limit")
    normalized = tuple(_required_text(item, field_name) for item in value)
    if any(len(item) > _MAX_ITEM_CHARS for item in normalized):
        raise ValueError(f"{field_name} contains an oversized item")
    if sum(len(item) for item in normalized) > _MAX_COLLECTION_CHARS:
        raise ValueError(f"{field_name} exceeds the total size limit")
    return normalized


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must contain non-empty strings")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must contain non-empty strings")
    return normalized
