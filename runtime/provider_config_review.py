from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.decision_implication_review import READY_FOR_IMPLICATION_REVIEW
from runtime.decision_review_handoff import HANDOFF_READY
from runtime.prompt_packet_review import (
    PROMPT_PACKET_REVIEW,
    PROMPT_PACKET_REVIEW_BLOCKED,
    PROMPT_PACKET_REVIEW_INVALID,
    PROMPT_PACKET_REVIEW_READY,
    PROMPT_PACKET_REVIEW_SCHEMA_VERSION,
    PromptPacketReview,
)


PROVIDER_CONFIG_REVIEW = "PROVIDER_CONFIG_REVIEW"
PROVIDER_CONFIG_REVIEW_SCHEMA_VERSION = "1.0"
PROVIDER_CONFIG_REVIEW_READY = "provider_config_review_ready"
PROVIDER_CONFIG_REVIEW_BLOCKED = "blocked"
PROVIDER_CONFIG_REVIEW_INVALID = "invalid"
PROVIDER_POLICY_MATERIAL = (
    "blocked_by_default",
    "no_live_calls",
    "no_secret_material",
    "no_api_key_material",
    "no_provider_endpoint_material",
    "no_network_client_material",
    "human_review_required",
    "future_provider_config_requires_separate_boundary_review",
)
PROVIDER_CONFIG_BOUNDARY_WARNINGS = (
    "This provider configuration review object is not real provider configuration, provider live, a provider request, prompt sending, secret or API key handling, dispatch, execution, approval, permission, or merge authority.",
    "No provider endpoint, live model, credential, token, secret, API key, network client, or send instruction is present.",
)
PROVIDER_CONFIG_REVIEW_BOUNDARY_TEXT = (
    "note: not real provider configuration\n"
    "note: not provider live\n"
    "note: not a provider request\n"
    "note: no secret or API key material\n"
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
    "secret=",
    "token=",
    "client_secret",
    "org_",
    "project_id",
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
)
_PROMPT_REVIEW_FIELDS = {
    "object_type",
    "schema_version",
    "state",
    "source_handoff_state",
    "source_implication_state",
    "decision_id",
    "decision_hash",
    "decision_status",
    "bundle_id",
    "bundle_hash",
    "prompt_material",
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
    "provider_request_created",
    "prompt_sent",
    "provider_config_accessed",
    "secret_accessed",
    "api_key_accessed",
    "network_accessed",
    "merge_authority_granted",
    "review_executes_anything",
}


@dataclass(frozen=True)
class ProviderConfigReview:
    state: str
    source_prompt_packet_state: str
    source_handoff_state: str
    source_implication_state: str
    decision_id: str
    decision_hash: str
    decision_status: str
    bundle_id: str
    bundle_hash: str
    provider_policy_material: tuple[str, ...]
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
    real_provider_config_created: bool = False
    provider_live_enabled: bool = False
    provider_request_created: bool = False
    prompt_sent: bool = False
    provider_config_read: bool = False
    provider_config_mutated: bool = False
    secret_accessed: bool = False
    api_key_accessed: bool = False
    credential_accessed: bool = False
    endpoint_configured: bool = False
    network_client_created: bool = False
    merge_authority_granted: bool = False
    review_executes_anything: bool = False
    object_type: str = PROVIDER_CONFIG_REVIEW
    schema_version: str = PROVIDER_CONFIG_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        state = _normalize_state(self.state)
        blockers = _bounded_text_tuple(self.blockers, "blockers")
        warnings = _merge_warnings(self.warnings)
        review_context = _bounded_text_tuple(self.review_context, "review_context")
        review_next = _bounded_text_tuple(self.review_next, "review_next")
        constraints = _merge_constraints(self.constraints)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "provider_policy_material", PROVIDER_POLICY_MATERIAL)
        object.__setattr__(self, "warnings", warnings)
        object.__setattr__(self, "review_next", review_next)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "boundary_text", PROVIDER_CONFIG_REVIEW_BOUNDARY_TEXT)
        object.__setattr__(self, "is_review_only", True)
        for flag_name in _INERT_FLAG_NAMES:
            object.__setattr__(self, flag_name, False)
        object.__setattr__(self, "object_type", PROVIDER_CONFIG_REVIEW)
        object.__setattr__(self, "schema_version", PROVIDER_CONFIG_REVIEW_SCHEMA_VERSION)

        if state == PROVIDER_CONFIG_REVIEW_READY:
            if blockers:
                raise ValueError("ready provider config review cannot contain blockers")
            if not review_context or not review_next:
                raise ValueError("ready provider config review requires bounded review context")
            _validate_inherited_material(review_context)
            _validate_inherited_material(review_next)
            object.__setattr__(self, "source_prompt_packet_state", PROMPT_PACKET_REVIEW_READY)
            object.__setattr__(self, "source_handoff_state", HANDOFF_READY)
            object.__setattr__(self, "source_implication_state", READY_FOR_IMPLICATION_REVIEW)
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
            raise ValueError("fail-closed provider config review requires blockers")
        object.__setattr__(self, "source_prompt_packet_state", PROMPT_PACKET_REVIEW_BLOCKED if state == PROVIDER_CONFIG_REVIEW_BLOCKED else PROMPT_PACKET_REVIEW_INVALID)
        object.__setattr__(self, "source_handoff_state", "")
        object.__setattr__(self, "source_implication_state", "")
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "review_context", ())
        for field_name in (
            "decision_id",
            "decision_hash",
            "decision_status",
            "bundle_id",
            "bundle_hash",
        ):
            object.__setattr__(self, field_name, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "schema_version": self.schema_version,
            "state": self.state,
            "source_prompt_packet_state": self.source_prompt_packet_state,
            "source_handoff_state": self.source_handoff_state,
            "source_implication_state": self.source_implication_state,
            "decision_id": self.decision_id,
            "decision_hash": self.decision_hash,
            "decision_status": self.decision_status,
            "bundle_id": self.bundle_id,
            "bundle_hash": self.bundle_hash,
            "provider_policy_material": list(self.provider_policy_material),
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
            "real_provider_config_created": self.real_provider_config_created,
            "provider_live_enabled": self.provider_live_enabled,
            "provider_request_created": self.provider_request_created,
            "prompt_sent": self.prompt_sent,
            "provider_config_read": self.provider_config_read,
            "provider_config_mutated": self.provider_config_mutated,
            "secret_accessed": self.secret_accessed,
            "api_key_accessed": self.api_key_accessed,
            "credential_accessed": self.credential_accessed,
            "endpoint_configured": self.endpoint_configured,
            "network_client_created": self.network_client_created,
            "merge_authority_granted": self.merge_authority_granted,
            "review_executes_anything": self.review_executes_anything,
        }


def build_provider_config_review(source: object) -> ProviderConfigReview:
    try:
        prompt_review = _canonical_prompt_review(source)
    except ValueError as error:
        return _failed_review(PROVIDER_CONFIG_REVIEW_INVALID, (str(error),), (), ())

    try:
        _validate_inherited_material(prompt_review.blockers)
        _validate_inherited_material(prompt_review.warnings)
        _validate_inherited_material(prompt_review.review_context)
        _validate_inherited_material(prompt_review.review_next)
        _validate_inherited_material(prompt_review.constraints)
    except ValueError:
        return _failed_review(
            PROVIDER_CONFIG_REVIEW_INVALID,
            ("source prompt review contains forbidden inherited material",),
            (),
            (),
        )

    if prompt_review.state != PROMPT_PACKET_REVIEW_READY:
        blockers = prompt_review.blockers or ("source prompt packet review is not ready",)
        state = PROVIDER_CONFIG_REVIEW_BLOCKED if prompt_review.state == PROMPT_PACKET_REVIEW_BLOCKED else PROVIDER_CONFIG_REVIEW_INVALID
        return _failed_review(state, blockers, prompt_review.review_next, prompt_review.warnings)

    try:
        return ProviderConfigReview(
            state=PROVIDER_CONFIG_REVIEW_READY,
            source_prompt_packet_state=prompt_review.state,
            source_handoff_state=prompt_review.source_handoff_state,
            source_implication_state=prompt_review.source_implication_state,
            decision_id=prompt_review.decision_id,
            decision_hash=prompt_review.decision_hash,
            decision_status=prompt_review.decision_status,
            bundle_id=prompt_review.bundle_id,
            bundle_hash=prompt_review.bundle_hash,
            provider_policy_material=PROVIDER_POLICY_MATERIAL,
            blockers=(),
            warnings=prompt_review.warnings,
            review_context=prompt_review.review_context,
            review_next=prompt_review.review_next,
            constraints=prompt_review.constraints,
            boundary_text=PROVIDER_CONFIG_REVIEW_BOUNDARY_TEXT,
        )
    except ValueError as error:
        return _failed_review(PROVIDER_CONFIG_REVIEW_INVALID, (str(error),), (), prompt_review.warnings)


def provider_config_review_to_dict(review: object) -> dict[str, Any]:
    if not isinstance(review, ProviderConfigReview):
        raise ValueError("review must be a ProviderConfigReview")
    return review.to_dict()


def render_provider_config_review(review: object) -> str:
    if not isinstance(review, ProviderConfigReview):
        raise ValueError("review must be a ProviderConfigReview")
    blockers = " | ".join(review.blockers)
    warnings = " | ".join(review.warnings)
    constraints = " | ".join(review.constraints)
    review_next = " | ".join(review.review_next)
    policy = " | ".join(review.provider_policy_material)
    if review.state != PROVIDER_CONFIG_REVIEW_READY:
        return (
            f"provider_config_review: {review.state}\n"
            "is_review_only: true\n"
            f"provider_policy_material: {policy}\n"
            f"blockers: {blockers}\n"
            f"constraints: {constraints}\n"
            f"warnings: {warnings}\n"
            f"{review.boundary_text}"
        )
    context = " | ".join(review.review_context)
    return (
        "provider_config_review: provider_config_review_ready\n"
        "is_review_only: true\n"
        f"source_prompt_packet_state: {review.source_prompt_packet_state}\n"
        f"source_handoff_state: {review.source_handoff_state}\n"
        f"source_implication_state: {review.source_implication_state}\n"
        f"decision_id: {review.decision_id}\n"
        f"decision_hash: {review.decision_hash}\n"
        f"decision_status: {review.decision_status}\n"
        f"bundle_id: {review.bundle_id}\n"
        f"bundle_hash: {review.bundle_hash}\n"
        f"provider_policy_material: {policy}\n"
        f"review_context: {context}\n"
        f"review_next: {review_next}\n"
        f"constraints: {constraints}\n"
        f"warnings: {warnings}\n"
        f"{review.boundary_text}"
    )


def _canonical_prompt_review(source: object) -> PromptPacketReview:
    if isinstance(source, PromptPacketReview):
        mapping = source.to_dict()
    elif isinstance(source, Mapping):
        mapping = dict(source)
    else:
        raise ValueError("source must be a prompt packet review")
    if set(mapping) != _PROMPT_REVIEW_FIELDS:
        raise ValueError("source prompt review fields do not match the canonical schema")
    if mapping["object_type"] != PROMPT_PACKET_REVIEW:
        raise ValueError("source prompt review object type is invalid")
    if mapping["schema_version"] != PROMPT_PACKET_REVIEW_SCHEMA_VERSION:
        raise ValueError("source prompt review schema version is invalid")
    try:
        canonical = PromptPacketReview(
            state=mapping["state"],
            source_handoff_state=mapping["source_handoff_state"],
            source_implication_state=mapping["source_implication_state"],
            decision_id=mapping["decision_id"],
            decision_hash=mapping["decision_hash"],
            decision_status=mapping["decision_status"],
            bundle_id=mapping["bundle_id"],
            bundle_hash=mapping["bundle_hash"],
            prompt_material=mapping["prompt_material"],
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
            provider_request_created=mapping["provider_request_created"],
            prompt_sent=mapping["prompt_sent"],
            provider_config_accessed=mapping["provider_config_accessed"],
            secret_accessed=mapping["secret_accessed"],
            api_key_accessed=mapping["api_key_accessed"],
            network_accessed=mapping["network_accessed"],
            merge_authority_granted=mapping["merge_authority_granted"],
            review_executes_anything=mapping["review_executes_anything"],
            object_type=mapping["object_type"],
            schema_version=mapping["schema_version"],
        )
    except (TypeError, ValueError) as error:
        raise ValueError("source prompt review is malformed") from error
    if canonical.to_dict() != mapping:
        raise ValueError("source prompt review is not canonical")
    return canonical


def _failed_review(
    state: str,
    blockers: tuple[str, ...],
    review_next: tuple[str, ...],
    warnings: tuple[str, ...],
) -> ProviderConfigReview:
    return ProviderConfigReview(
        state=state,
        source_prompt_packet_state="",
        source_handoff_state="",
        source_implication_state="",
        decision_id="",
        decision_hash="",
        decision_status="",
        bundle_id="",
        bundle_hash="",
        provider_policy_material=PROVIDER_POLICY_MATERIAL,
        blockers=blockers,
        warnings=warnings,
        review_context=(),
        review_next=review_next,
        constraints=(),
        boundary_text=PROVIDER_CONFIG_REVIEW_BOUNDARY_TEXT,
    )


def _normalize_state(value: object) -> str:
    if value not in (
        PROVIDER_CONFIG_REVIEW_READY,
        PROVIDER_CONFIG_REVIEW_BLOCKED,
        PROVIDER_CONFIG_REVIEW_INVALID,
    ):
        raise ValueError("state must be a supported provider config review state")
    return str(value)


def _merge_warnings(value: object) -> tuple[str, ...]:
    warnings = list(_bounded_text_tuple(value, "warnings"))
    for warning in PROVIDER_CONFIG_BOUNDARY_WARNINGS:
        if warning not in warnings:
            warnings.append(warning)
    return _bounded_text_tuple(warnings, "warnings")


def _merge_constraints(value: object) -> tuple[str, ...]:
    constraints = list(_bounded_text_tuple(value, "constraints"))
    for constraint in PROVIDER_POLICY_MATERIAL:
        if constraint not in constraints:
            constraints.append(constraint)
    return _bounded_text_tuple(constraints, "constraints")


def _validate_inherited_material(values: tuple[str, ...]) -> None:
    for value in values:
        normalized = value.casefold()
        if any(term in normalized for term in _FORBIDDEN_INHERITED_MATERIAL):
            raise ValueError("inherited review material contains forbidden provider or secret material")


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
