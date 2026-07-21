"""Pure, hash-bound operator role selection for live Orchestra previews.

This module binds public provider-connection and model-profile metadata only.
It never reads credentials, calls a provider, or grants provider-call authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from runtime.epistemic_orchestra.canonical import (
    EpistemicContractError,
    canonical_sha256,
    canonical_value,
    require_exact_fields,
    require_sha256,
)
from runtime.epistemic_orchestra.contracts import JsonContract, NON_AUTHORITATIVE


ROLE_ASSIGNMENT_SCHEMA_VERSION = "orchestra-model-role-assignment-1a"
ROLE_SELECTION_SCHEMA_VERSION = "orchestra-role-selection-1a"
MINIMUM_SELECTED_MODELS = 2
MAXIMUM_SELECTED_MODELS = 5

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class OrchestraOperatorRole(str, Enum):
    MAIN = "MAIN"
    CRITIC = "CRITIC"
    AUDITOR = "AUDITOR"
    SYNTHESIZER = "SYNTHESIZER"


class ProviderConnectionSnapshot(Protocol):
    connection_id: str
    connection_revision_hash: str
    enabled: bool


class ModelProfileSnapshot(Protocol):
    model_profile_id: str
    connection_id: str
    remote_model_id: str
    enabled: bool
    allowed_roles: Sequence[str]
    model_revision_hash: str


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise EpistemicContractError(f"{name} is not a bounded identifier")
    return value


def _required_text(name: str, value: object, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EpistemicContractError(
            f"{name} must be non-blank text <= {maximum} characters"
        )
    return value


def _nonnegative_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EpistemicContractError(f"{name} must be a non-negative integer")
    return value


def _role_value(value: str | OrchestraOperatorRole) -> str:
    try:
        if isinstance(value, OrchestraOperatorRole):
            return value.value
        return OrchestraOperatorRole(value).value
    except (TypeError, ValueError) as exc:
        raise EpistemicContractError("Orchestra operator role is unsupported") from exc


def _attribute(value: object, name: str, *, label: str) -> object:
    try:
        return getattr(value, name)
    except AttributeError as exc:
        raise EpistemicContractError(f"{label} is missing {name}") from exc


def _assert_no_authority(value: object) -> None:
    if getattr(value, "authority_status", None) != NON_AUTHORITATIVE:
        raise EpistemicContractError("authority_status must be NON_AUTHORITATIVE")
    for name in (
        "provider_output_is_authority",
        "critic_output_is_authority",
        "auditor_output_is_authority",
        "synthesis_output_is_authority",
        "multi_model_agreement_is_authority",
        "execution_permitted",
        "write_permitted",
        "dispatch_permitted",
        "provider_call_permitted",
        "approval_permitted",
        "gate_mutation_permitted",
        "human_barrier_satisfied",
    ):
        if type(getattr(value, name, None)) is not bool or getattr(value, name):
            raise EpistemicContractError(f"{name} must be False")
    if getattr(value, "human_review_required", None) is not True:
        raise EpistemicContractError("human_review_required must be True")


def _self_hash(value: JsonContract, hash_field: str, supplied: str) -> str:
    material = value.to_dict()
    material.pop(hash_field)
    expected = canonical_sha256(material)
    if supplied not in ("", expected):
        raise EpistemicContractError(f"{hash_field} does not match canonical fields")
    return expected


@dataclass(frozen=True, slots=True)
class ModelRoleAssignment(JsonContract):
    schema_version: str
    ordinal: int
    connection_id: str
    connection_revision_hash: str
    model_profile_id: str
    model_revision_hash: str
    remote_model_id: str
    role: str
    role_assignment_hash: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    critic_output_is_authority: bool = False
    auditor_output_is_authority: bool = False
    synthesis_output_is_authority: bool = False
    multi_model_agreement_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != ROLE_ASSIGNMENT_SCHEMA_VERSION:
            raise EpistemicContractError("role assignment schema_version differs")
        _nonnegative_int("ordinal", self.ordinal)
        _identifier("connection_id", self.connection_id)
        _identifier("model_profile_id", self.model_profile_id)
        require_sha256("connection_revision_hash", self.connection_revision_hash)
        require_sha256("model_revision_hash", self.model_revision_hash)
        _required_text("remote_model_id", self.remote_model_id)
        object.__setattr__(self, "role", _role_value(self.role))
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "role_assignment_hash",
            _self_hash(self, "role_assignment_hash", self.role_assignment_hash),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelRoleAssignment":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("role_assignment_hash", value["role_assignment_hash"])
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class OrchestraRoleSelection(JsonContract):
    schema_version: str
    assignments: tuple[ModelRoleAssignment, ...]
    role_selection_hash: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    critic_output_is_authority: bool = False
    auditor_output_is_authority: bool = False
    synthesis_output_is_authority: bool = False
    multi_model_agreement_is_authority: bool = False
    execution_permitted: bool = False
    write_permitted: bool = False
    dispatch_permitted: bool = False
    provider_call_permitted: bool = False
    approval_permitted: bool = False
    gate_mutation_permitted: bool = False
    human_barrier_satisfied: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        if self.schema_version != ROLE_SELECTION_SCHEMA_VERSION:
            raise EpistemicContractError("role selection schema_version differs")
        assignments = tuple(self.assignments)
        if any(not isinstance(item, ModelRoleAssignment) for item in assignments):
            raise EpistemicContractError("assignments must be ModelRoleAssignment objects")
        if not MINIMUM_SELECTED_MODELS <= len(assignments) <= MAXIMUM_SELECTED_MODELS:
            raise EpistemicContractError("Orchestra selection requires two to five models")
        if tuple(item.ordinal for item in assignments) != tuple(range(len(assignments))):
            raise EpistemicContractError("role assignment ordinals must be exact and ordered")
        profile_ids = tuple(item.model_profile_id for item in assignments)
        if len(profile_ids) != len(set(profile_ids)):
            raise EpistemicContractError("selected model profiles must be unique")
        assignment_hashes = tuple(item.role_assignment_hash for item in assignments)
        if len(assignment_hashes) != len(set(assignment_hashes)):
            raise EpistemicContractError("role assignments must be unique")
        roles = tuple(item.role for item in assignments)
        if roles.count(OrchestraOperatorRole.MAIN.value) != 1:
            raise EpistemicContractError("exactly one selected model must be MAIN")
        if roles[0] != OrchestraOperatorRole.MAIN.value:
            raise EpistemicContractError("MAIN must be the first selected model")
        if not any(
            role in (OrchestraOperatorRole.CRITIC.value, OrchestraOperatorRole.AUDITOR.value)
            for role in roles
        ):
            raise EpistemicContractError("selection requires at least one CRITIC or AUDITOR")
        if roles.count(OrchestraOperatorRole.SYNTHESIZER.value) > 1:
            raise EpistemicContractError("selection permits at most one SYNTHESIZER")
        if OrchestraOperatorRole.SYNTHESIZER.value in roles and roles[-1] != OrchestraOperatorRole.SYNTHESIZER.value:
            raise EpistemicContractError("SYNTHESIZER must be the last selected model")
        review_roles = tuple(
            role for role in roles[1:] if role != OrchestraOperatorRole.SYNTHESIZER.value
        )
        if (
            OrchestraOperatorRole.AUDITOR.value in review_roles
            and OrchestraOperatorRole.CRITIC.value in review_roles
            and review_roles.index(OrchestraOperatorRole.AUDITOR.value)
            < max(
                index
                for index, role in enumerate(review_roles)
                if role == OrchestraOperatorRole.CRITIC.value
            )
        ):
            raise EpistemicContractError("all CRITIC stages must precede AUDITOR stages")
        object.__setattr__(self, "assignments", assignments)
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "role_selection_hash",
            _self_hash(self, "role_selection_hash", self.role_selection_hash),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OrchestraRoleSelection":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("role_selection_hash", value["role_selection_hash"])
        payload = dict(value)
        if not isinstance(payload["assignments"], list):
            raise EpistemicContractError("assignments must be an array")
        payload["assignments"] = tuple(
            ModelRoleAssignment.from_dict(item) for item in payload["assignments"]
        )
        return cls(**payload)


def build_model_role_assignment(
    *,
    ordinal: int,
    connection: ProviderConnectionSnapshot,
    model_profile: ModelProfileSnapshot,
    role: str | OrchestraOperatorRole,
) -> ModelRoleAssignment:
    """Bind one enabled model to one explicit operator-selected role."""

    normalized_role = _role_value(role)
    if _attribute(connection, "enabled", label="connection") is not True:
        raise EpistemicContractError("disabled connection cannot be selected")
    if _attribute(model_profile, "enabled", label="model profile") is not True:
        raise EpistemicContractError("disabled model profile cannot be selected")
    connection_id = _identifier(
        "connection_id", _attribute(connection, "connection_id", label="connection")
    )
    profile_connection_id = _identifier(
        "model_profile.connection_id",
        _attribute(model_profile, "connection_id", label="model profile"),
    )
    if profile_connection_id != connection_id:
        raise EpistemicContractError("model profile belongs to another connection")
    allowed_raw = _attribute(model_profile, "allowed_roles", label="model profile")
    if isinstance(allowed_raw, str) or not isinstance(allowed_raw, Sequence):
        raise EpistemicContractError("model profile allowed_roles must be a sequence")
    allowed_roles = tuple(_role_value(item) for item in allowed_raw)
    if not allowed_roles or len(allowed_roles) != len(set(allowed_roles)):
        raise EpistemicContractError("model profile allowed_roles must be non-empty and unique")
    if normalized_role not in allowed_roles:
        raise EpistemicContractError("model profile does not allow the selected role")
    return ModelRoleAssignment(
        schema_version=ROLE_ASSIGNMENT_SCHEMA_VERSION,
        ordinal=_nonnegative_int("ordinal", ordinal),
        connection_id=connection_id,
        connection_revision_hash=require_sha256(
            "connection_revision_hash",
            _attribute(connection, "connection_revision_hash", label="connection"),
        ),
        model_profile_id=_identifier(
            "model_profile_id",
            _attribute(model_profile, "model_profile_id", label="model profile"),
        ),
        model_revision_hash=require_sha256(
            "model_revision_hash",
            _attribute(model_profile, "model_revision_hash", label="model profile"),
        ),
        remote_model_id=_required_text(
            "remote_model_id",
            _attribute(model_profile, "remote_model_id", label="model profile"),
        ),
        role=normalized_role,
    )


def build_orchestra_role_selection(
    assignments: Sequence[ModelRoleAssignment],
) -> OrchestraRoleSelection:
    if isinstance(assignments, (str, bytes)):
        raise EpistemicContractError("assignments must be a sequence")
    return OrchestraRoleSelection(
        schema_version=ROLE_SELECTION_SCHEMA_VERSION,
        assignments=tuple(assignments),
    )


def validate_role_selection_against_current_profiles(
    selection: OrchestraRoleSelection,
    *,
    connections_by_id: Mapping[str, ProviderConnectionSnapshot],
    model_profiles_by_id: Mapping[str, ModelProfileSnapshot],
) -> None:
    """Fail closed when saved provider/model metadata changed after selection."""

    if not isinstance(selection, OrchestraRoleSelection):
        raise EpistemicContractError("selection must be OrchestraRoleSelection")
    if not isinstance(connections_by_id, Mapping) or not isinstance(
        model_profiles_by_id, Mapping
    ):
        raise EpistemicContractError("current connection and model indexes are required")
    for assignment in selection.assignments:
        connection = connections_by_id.get(assignment.connection_id)
        profile = model_profiles_by_id.get(assignment.model_profile_id)
        if connection is None or profile is None:
            raise EpistemicContractError("selected connection or model profile is missing")
        current = build_model_role_assignment(
            ordinal=assignment.ordinal,
            connection=connection,
            model_profile=profile,
            role=assignment.role,
        )
        if canonical_value(current) != canonical_value(assignment):
            raise EpistemicContractError("selected connection or model revision is stale")
