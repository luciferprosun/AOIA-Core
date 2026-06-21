from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.decision_implication_review import READY_FOR_IMPLICATION_REVIEW
from runtime.decision_review_handoff import HANDOFF_READY
from runtime.prompt_packet_review import PROMPT_PACKET_REVIEW_READY
from runtime.provider_config_review import (
    PROVIDER_CONFIG_REVIEW,
    PROVIDER_CONFIG_REVIEW_BLOCKED,
    PROVIDER_CONFIG_REVIEW_INVALID,
    PROVIDER_CONFIG_REVIEW_READY,
    PROVIDER_CONFIG_REVIEW_SCHEMA_VERSION,
    ProviderConfigReview,
)


SECRET_BOUNDARY_REVIEW = "SECRET_BOUNDARY_REVIEW"
SECRET_BOUNDARY_REVIEW_SCHEMA_VERSION = "1.0"
SECRET_BOUNDARY_REVIEW_READY = "secret_boundary_review_ready"
SECRET_BOUNDARY_REVIEW_BLOCKED = "blocked"
SECRET_BOUNDARY_REVIEW_INVALID = "invalid"
SECRET_POLICY_MATERIAL = (
    "blocked_by_default",
    "no_live_secrets",
    "no_secret_material",
    "no_api_key_loading",
    "no_secret_storage",
    "no_secret_display",
    "no_env_file_reads",
    "no_environment_variable_reads",
    "no_provider_endpoint_material",
    "no_network_client_material",
    "human_review_required",
    "future_secret_handling_requires_separate_boundary_review",
)
SECRET_BOUNDARY_WARNINGS = (
    "This secrets and API-key boundary review object is not secret loading, API-key handling, credential storage, provider configuration, provider live, a provider request, prompt sending, dispatch, execution, approval, permission, or merge authority.",
    "No secret, API key, credential, token, password, private key, environment value, endpoint, network client, or send instruction is present.",
)
SECRET_BOUNDARY_TEXT = (
    "note: not a real secret boundary\n"
    "note: no secret or API key loading\n"
    "note: no environment variable or env file reads\n"
    "note: not provider configuration or provider live\n"
    "note: not a provider request\n"
    "note: no network or prompt sending\n"
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
    "project_id",
    "sk-",
    "ghp_",
    "xoxb-",
    "openai",
    "anthropic",
    "gemini",
    "gpt-",
    "claude-",
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
_PROVIDER_REVIEW_FIELDS = {
    "object_type",
    "schema_version",
    "state",
    "source_prompt_packet_state",
    "source_handoff_state",
    "source_implication_state",
    "decision_id",
    "decision_hash",
    "decision_status",
    "bundle_id",
    "bundle_hash",
    "provider_policy_material",
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
    "real_provider_config_created",
    "provider_live_enabled",
    "provider_request_created",
    "prompt_sent",
    "provider_config_read",
    "provider_config_mutated",
    "secret_accessed",
    "api_key_accessed",
    "credential_accessed",
    "endpoint_configured",
    "network_client_created",
    "merge_authority_granted",
    "review_executes_anything",
}


@dataclass(frozen=True)
class SecretBoundaryReview:
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
    boundary_text: str
    is_review_only: bool = True
    authority_granted: bool = False
    execution_allowed: bool = False
    dispatch_allowed: bool = False
    provider_call_allowed: bool = False
    artifact_write_allowed: bool = False
    persistence_allowed: bool = False
    real_secret_boundary_created: bool = False
    secret_config_created: bool = False
    secret_config_read: bool = False
    secret_config_mutated: bool = False
    secret_loaded: bool = False
    secret_read: bool = False
    secret_stored: bool = False
    secret_displayed: bool = False
    api_key_loaded: bool = False
    api_key_accessed: bool = False
    api_key_stored: bool = False
    credential_accessed: bool = False
    environment_variables_read: bool = False
    env_file_read: bool = False
    real_provider_config_created: bool = False
    provider_config_read: bool = False
    provider_config_mutated: bool = False
    provider_live_enabled: bool = False
    provider_request_created: bool = False
    prompt_sent: bool = False
    endpoint_configured: bool = False
    network_client_created: bool = False
    merge_authority_granted: bool = False
    review_executes_anything: bool = False
    object_type: str = SECRET_BOUNDARY_REVIEW
    schema_version: str = SECRET_BOUNDARY_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        state = _normalize_state(self.state)
        blockers = _bounded_text_tuple(self.blockers, "blockers")
        warnings = _bounded_text_tuple(self.warnings, "warnings")
        review_context = _bounded_text_tuple(self.review_context, "review_context")
        review_next = _bounded_text_tuple(self.review_next, "review_next")
        constraints = _bounded_text_tuple(self.constraints, "constraints")
        for values in (blockers, warnings, review_context, review_next, constraints):
            _validate_inherited_material(values)
        warnings = _merge_warnings(warnings)
        constraints = _merge_constraints(constraints)

        object.__setattr__(self, "state", state)
        object.__setattr__(self, "secret_policy_material", SECRET_POLICY_MATERIAL)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "review_next", review_next)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "boundary_text", SECRET_BOUNDARY_TEXT)
        object.__setattr__(self, "is_review_only", True)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", SECRET_BOUNDARY_REVIEW)
        object.__setattr__(self, "schema_version", SECRET_BOUNDARY_REVIEW_SCHEMA_VERSION)

        if state == SECRET_BOUNDARY_REVIEW_READY:
            if blockers:
                raise ValueError("ready secret boundary review cannot contain blockers")
            if not review_context or not review_next:
                raise ValueError("ready secret boundary review requires bounded review context")
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
            raise ValueError("fail-closed secret boundary review requires blockers")
        source_state = (
            PROVIDER_CONFIG_REVIEW_BLOCKED
            if state == SECRET_BOUNDARY_REVIEW_BLOCKED
            else PROVIDER_CONFIG_REVIEW_INVALID
        )
        object.__setattr__(self, "source_provider_config_state", source_state)
        for field_name in (
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
            "secret_policy_material": list(self.secret_policy_material),
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
            "real_secret_boundary_created": self.real_secret_boundary_created,
            "secret_config_created": self.secret_config_created,
            "secret_config_read": self.secret_config_read,
            "secret_config_mutated": self.secret_config_mutated,
            "secret_loaded": self.secret_loaded,
            "secret_read": self.secret_read,
            "secret_stored": self.secret_stored,
            "secret_displayed": self.secret_displayed,
            "api_key_loaded": self.api_key_loaded,
            "api_key_accessed": self.api_key_accessed,
            "api_key_stored": self.api_key_stored,
            "credential_accessed": self.credential_accessed,
            "environment_variables_read": self.environment_variables_read,
            "env_file_read": self.env_file_read,
            "real_provider_config_created": self.real_provider_config_created,
            "provider_config_read": self.provider_config_read,
            "provider_config_mutated": self.provider_config_mutated,
            "provider_live_enabled": self.provider_live_enabled,
            "provider_request_created": self.provider_request_created,
            "prompt_sent": self.prompt_sent,
            "endpoint_configured": self.endpoint_configured,
            "network_client_created": self.network_client_created,
            "merge_authority_granted": self.merge_authority_granted,
            "review_executes_anything": self.review_executes_anything,
        }


def build_secret_boundary_review(source: object) -> SecretBoundaryReview:
    try:
        provider_review = _canonical_provider_review(source)
    except ValueError as error:
        return _failed_review(SECRET_BOUNDARY_REVIEW_INVALID, (str(error),), (), ())

    try:
        for values in (
            provider_review.provider_policy_material,
            provider_review.blockers,
            provider_review.warnings,
            provider_review.review_context,
            provider_review.review_next,
            provider_review.constraints,
        ):
            _validate_inherited_material(values)
    except ValueError:
        return _failed_review(
            SECRET_BOUNDARY_REVIEW_INVALID,
            ("source provider review contains forbidden inherited material",),
            (),
            (),
        )

    if provider_review.state != PROVIDER_CONFIG_REVIEW_READY:
        blockers = provider_review.blockers or ("source provider config review is not ready",)
        state = (
            SECRET_BOUNDARY_REVIEW_BLOCKED
            if provider_review.state == PROVIDER_CONFIG_REVIEW_BLOCKED
            else SECRET_BOUNDARY_REVIEW_INVALID
        )
        return _failed_review(state, blockers, provider_review.review_next, provider_review.warnings)

    try:
        return SecretBoundaryReview(
            state=SECRET_BOUNDARY_REVIEW_READY,
            source_provider_config_state=provider_review.state,
            source_prompt_packet_state=provider_review.source_prompt_packet_state,
            source_handoff_state=provider_review.source_handoff_state,
            source_implication_state=provider_review.source_implication_state,
            source_readiness_state=READY_FOR_IMPLICATION_REVIEW,
            decision_id=provider_review.decision_id,
            decision_hash=provider_review.decision_hash,
            decision_status=provider_review.decision_status,
            bundle_id=provider_review.bundle_id,
            bundle_hash=provider_review.bundle_hash,
            secret_policy_material=SECRET_POLICY_MATERIAL,
            blockers=(),
            warnings=provider_review.warnings,
            review_context=provider_review.review_context,
            review_next=provider_review.review_next,
            constraints=provider_review.constraints,
            boundary_text=SECRET_BOUNDARY_TEXT,
        )
    except ValueError:
        return _failed_review(
            SECRET_BOUNDARY_REVIEW_INVALID,
            ("source provider review cannot produce a safe boundary review",),
            (),
            (),
        )


def secret_boundary_review_to_dict(review: object) -> dict[str, Any]:
    if not isinstance(review, SecretBoundaryReview):
        raise ValueError("review must be a SecretBoundaryReview")
    return review.to_dict()


def render_secret_boundary_review(review: object) -> str:
    if not isinstance(review, SecretBoundaryReview):
        raise ValueError("review must be a SecretBoundaryReview")
    blockers = " | ".join(review.blockers)
    warnings = " | ".join(review.warnings)
    constraints = " | ".join(review.constraints)
    review_next = " | ".join(review.review_next)
    policy = " | ".join(review.secret_policy_material)
    if review.state != SECRET_BOUNDARY_REVIEW_READY:
        return (
            f"secret_boundary_review: {review.state}\n"
            "is_review_only: true\n"
            f"secret_policy_material: {policy}\n"
            f"blockers: {blockers}\n"
            f"constraints: {constraints}\n"
            f"warnings: {warnings}\n"
            f"{review.boundary_text}"
        )
    context = " | ".join(review.review_context)
    return (
        "secret_boundary_review: secret_boundary_review_ready\n"
        "is_review_only: true\n"
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
        f"secret_policy_material: {policy}\n"
        f"review_context: {context}\n"
        f"review_next: {review_next}\n"
        f"constraints: {constraints}\n"
        f"warnings: {warnings}\n"
        f"{review.boundary_text}"
    )


def _canonical_provider_review(source: object) -> ProviderConfigReview:
    if isinstance(source, ProviderConfigReview):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a provider config review")
    if set(mapping) != _PROVIDER_REVIEW_FIELDS:
        raise ValueError("source provider review fields do not match the canonical schema")
    if mapping["object_type"] != PROVIDER_CONFIG_REVIEW:
        raise ValueError("source provider review object type is invalid")
    if mapping["schema_version"] != PROVIDER_CONFIG_REVIEW_SCHEMA_VERSION:
        raise ValueError("source provider review schema version is invalid")
    try:
        canonical = ProviderConfigReview(
            state=mapping["state"],
            source_prompt_packet_state=mapping["source_prompt_packet_state"],
            source_handoff_state=mapping["source_handoff_state"],
            source_implication_state=mapping["source_implication_state"],
            decision_id=mapping["decision_id"],
            decision_hash=mapping["decision_hash"],
            decision_status=mapping["decision_status"],
            bundle_id=mapping["bundle_id"],
            bundle_hash=mapping["bundle_hash"],
            provider_policy_material=mapping["provider_policy_material"],
            blockers=mapping["blockers"],
            warnings=mapping["warnings"],
            review_context=mapping["review_context"],
            review_next=mapping["review_next"],
            constraints=mapping["constraints"],
            boundary_text=mapping["boundary_text"],
            is_review_only=mapping["is_review_only"],
            authority_granted=mapping["authority_granted"],
            execution_allowed=mapping["execution_allowed"],
            dispatch_allowed=mapping["dispatch_allowed"],
            provider_call_allowed=mapping["provider_call_allowed"],
            artifact_write_allowed=mapping["artifact_write_allowed"],
            persistence_allowed=mapping["persistence_allowed"],
            real_provider_config_created=mapping["real_provider_config_created"],
            provider_live_enabled=mapping["provider_live_enabled"],
            provider_request_created=mapping["provider_request_created"],
            prompt_sent=mapping["prompt_sent"],
            provider_config_read=mapping["provider_config_read"],
            provider_config_mutated=mapping["provider_config_mutated"],
            secret_accessed=mapping["secret_accessed"],
            api_key_accessed=mapping["api_key_accessed"],
            credential_accessed=mapping["credential_accessed"],
            endpoint_configured=mapping["endpoint_configured"],
            network_client_created=mapping["network_client_created"],
            merge_authority_granted=mapping["merge_authority_granted"],
            review_executes_anything=mapping["review_executes_anything"],
            object_type=mapping["object_type"],
            schema_version=mapping["schema_version"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("source provider review is malformed") from error
    if canonical.to_dict() != mapping:
        raise ValueError("source provider review is not canonical")
    return canonical


def _failed_review(
    state: str,
    blockers: tuple[str, ...],
    review_next: tuple[str, ...],
    warnings: tuple[str, ...],
) -> SecretBoundaryReview:
    return SecretBoundaryReview(
        state=state,
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
        secret_policy_material=SECRET_POLICY_MATERIAL,
        blockers=blockers,
        warnings=warnings,
        review_context=(),
        review_next=review_next,
        constraints=(),
        boundary_text=SECRET_BOUNDARY_TEXT,
    )


def _normalize_state(value: object) -> str:
    if value not in (
        SECRET_BOUNDARY_REVIEW_READY,
        SECRET_BOUNDARY_REVIEW_BLOCKED,
        SECRET_BOUNDARY_REVIEW_INVALID,
    ):
        raise ValueError("state must be a supported secret boundary review state")
    return str(value)


def _merge_warnings(value: object) -> tuple[str, ...]:
    warnings = list(_bounded_text_tuple(value, "warnings"))
    for warning in SECRET_BOUNDARY_WARNINGS:
        if warning not in warnings:
            warnings.append(warning)
    return _bounded_text_tuple(warnings, "warnings")


def _merge_constraints(value: object) -> tuple[str, ...]:
    constraints = list(_bounded_text_tuple(value, "constraints"))
    for constraint in SECRET_POLICY_MATERIAL:
        if constraint not in constraints:
            constraints.append(constraint)
    return _bounded_text_tuple(constraints, "constraints")


def _validate_inherited_material(values: tuple[str, ...]) -> None:
    for value in values:
        normalized = value.casefold()
        if any(term in normalized for term in _FORBIDDEN_INHERITED_MATERIAL):
            raise ValueError("inherited review material contains forbidden secret or endpoint material")


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
