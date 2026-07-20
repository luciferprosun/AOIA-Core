"""Immutable, non-authoritative contracts for epistemic review metadata.

This module compiles and validates metadata only.  It contains no dispatcher,
provider, network, filesystem, approval, gate, or execution capability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from runtime.epistemic_orchestra.canonical import (
    EpistemicContractError,
    canonical_sha256,
    canonical_value,
    exact_text_sha256,
    parse_strict_json_object,
    require_exact_fields,
    require_sha256,
)


RUN_SCHEMA_VERSION = "epistemic-run-contract-1a"
STAGE_SCHEMA_VERSION = "epistemic-stage-contract-1a"
TRUNCATION_SCHEMA_VERSION = "epistemic-truncation-evidence-1a"
CRITIC_PAYLOAD_SCHEMA_VERSION = "epistemic-critic-stage-payload-1a"
RUN_POLICY_VERSION = "epistemic-run-policy-1a"
STAGE_POLICY_VERSION = "epistemic-stage-policy-1a"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
MAXIMUM_ABSOLUTE_STAGE_COUNT = 32

EMPTY_KNOWLEDGE_CONTEXT_HASH = canonical_sha256(
    {"sentinel": "NO_KNOWLEDGE_CONTEXT_SELECTED", "schema_version": RUN_SCHEMA_VERSION}
)
EMPTY_KNOWLEDGE_PROFILE_HASH = canonical_sha256(
    {"sentinel": "NO_KNOWLEDGE_PROFILE_SELECTED", "schema_version": RUN_SCHEMA_VERSION}
)
EMPTY_CPT_TRANSFORMATION_HASH = canonical_sha256(
    {"sentinel": "NO_CPT_TRANSFORMATION", "schema_version": STAGE_SCHEMA_VERSION}
)
NO_CPT_TRANSFORMATION_ID = "NO_CPT_TRANSFORMATION"

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")

AUTHORITY_FIELD_NAMES = (
    "authority_status",
    "provider_output_is_authority",
    "critic_output_is_authority",
    "cpt_output_is_authority",
    "revision_output_is_authority",
    "multi_model_agreement_is_authority",
    "execution_permitted",
    "write_permitted",
    "dispatch_permitted",
    "provider_call_permitted",
    "approval_permitted",
    "gate_mutation_permitted",
    "human_barrier_satisfied",
    "human_review_required",
)


class OrchestrationMode(str, Enum):
    SEQUENTIAL_RING_V1 = "SEQUENTIAL_RING_V1"
    INDEPENDENT_PANEL_V1 = "INDEPENDENT_PANEL_V1"


class StageRole(str, Enum):
    PRIMARY = "PRIMARY"
    CRITIC = "CRITIC"


class CriticOutcome(str, Enum):
    MATERIAL_ISSUES_FOUND = "MATERIAL_ISSUES_FOUND"
    NO_MATERIAL_ISSUE_FOUND = "NO_MATERIAL_ISSUE_FOUND"
    CRITIC_OUTPUT_BLOCKED = "CRITIC_OUTPUT_BLOCKED"
    CRITIC_OUTPUT_INVALID = "CRITIC_OUTPUT_INVALID"


class CriticSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def _enum_value(enum_type: type[Enum], name: str, value: object) -> str:
    try:
        if isinstance(value, enum_type):
            return str(value.value)
        return str(enum_type(value).value)
    except (TypeError, ValueError) as exc:
        raise EpistemicContractError(f"unsupported {name}: {value!r}") from exc


def _required_text(name: str, value: object, *, maximum: int = 20_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise EpistemicContractError(f"{name} must be non-blank text <= {maximum} characters")
    return value


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise EpistemicContractError(f"{name} is not a bounded identifier")
    return value


def _tuple_text(
    name: str,
    value: Iterable[str],
    *,
    unique: bool = True,
    sort_values: bool = False,
) -> tuple[str, ...]:
    if isinstance(value, str):
        raise EpistemicContractError(f"{name} must be a sequence")
    result = tuple(value)
    for item in result:
        _required_text(name, item, maximum=256)
    if unique and len(result) != len(set(result)):
        raise EpistemicContractError(f"{name} contains duplicates")
    return tuple(sorted(result)) if sort_values else result


def _require_nonnegative_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EpistemicContractError(f"{name} must be a non-negative integer")
    return value


def _assert_no_authority(value: object) -> None:
    if getattr(value, "authority_status", None) != NON_AUTHORITATIVE:
        raise EpistemicContractError("authority_status must be NON_AUTHORITATIVE")
    false_fields = (
        "provider_output_is_authority",
        "critic_output_is_authority",
        "cpt_output_is_authority",
        "revision_output_is_authority",
        "multi_model_agreement_is_authority",
        "execution_permitted",
        "write_permitted",
        "dispatch_permitted",
        "provider_call_permitted",
        "approval_permitted",
        "gate_mutation_permitted",
        "human_barrier_satisfied",
    )
    for name in false_fields:
        if type(getattr(value, name, None)) is not bool or getattr(value, name):
            raise EpistemicContractError(f"{name} must be False")
    if getattr(value, "human_review_required", None) is not True:
        raise EpistemicContractError("human_review_required must be True")


class JsonContract:
    def to_dict(self) -> dict[str, Any]:
        value = canonical_value(self)
        if not isinstance(value, dict):
            raise TypeError("contract did not serialize to an object")
        return value


def _verify_self_hash(value: JsonContract, field_name: str, supplied: str) -> str:
    payload = value.to_dict()
    payload.pop(field_name)
    expected = canonical_sha256(payload)
    if supplied not in ("", expected):
        raise EpistemicContractError(f"{field_name} does not match canonical fields")
    return expected


def compute_stage_plan_hash(
    *,
    orchestration_mode: str | OrchestrationMode,
    planned_stage_ids: Sequence[str],
    planned_stage_roles: Sequence[str | StageRole],
    maximum_stage_count: int,
) -> str:
    mode = _enum_value(OrchestrationMode, "orchestration_mode", orchestration_mode)
    ids = tuple(_identifier("stage_id", item) for item in planned_stage_ids)
    roles = tuple(_enum_value(StageRole, "stage_role", item) for item in planned_stage_roles)
    _require_nonnegative_int("maximum_stage_count", maximum_stage_count)
    return canonical_sha256(
        {
            "domain": "epistemic-stage-plan-1a",
            "orchestration_mode": mode,
            "planned_stage_ids": ids,
            "planned_stage_roles": roles,
            "maximum_stage_count": maximum_stage_count,
        }
    )


@dataclass(frozen=True, slots=True)
class EpistemicRunContract(JsonContract):
    schema_version: str
    run_id: str
    orchestration_mode: str
    source_request_hash: str
    source_prompt_hash: str
    knowledge_context_hash: str
    knowledge_profile_hash: str
    stage_plan_hash: str
    planned_stage_ids: tuple[str, ...]
    planned_stage_roles: tuple[str, ...]
    maximum_stage_count: int
    run_policy_version: str
    run_hash: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    critic_output_is_authority: bool = False
    cpt_output_is_authority: bool = False
    revision_output_is_authority: bool = False
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
        if self.schema_version != RUN_SCHEMA_VERSION:
            raise EpistemicContractError("run schema_version differs")
        object.__setattr__(self, "run_id", _identifier("run_id", self.run_id))
        object.__setattr__(
            self,
            "orchestration_mode",
            _enum_value(OrchestrationMode, "orchestration_mode", self.orchestration_mode),
        )
        for name in (
            "source_request_hash",
            "source_prompt_hash",
            "knowledge_context_hash",
            "knowledge_profile_hash",
            "stage_plan_hash",
        ):
            require_sha256(name, getattr(self, name))
        ids = tuple(_identifier("planned_stage_id", item) for item in self.planned_stage_ids)
        roles = tuple(
            _enum_value(StageRole, "planned_stage_role", item)
            for item in self.planned_stage_roles
        )
        if not ids or len(ids) != len(roles):
            raise EpistemicContractError("stage plan IDs and roles must be non-empty and aligned")
        if len(roles) < 3 or roles[0] != StageRole.PRIMARY.value or roles[-1] != StageRole.PRIMARY.value:
            raise EpistemicContractError("run plan requires initial and revision PRIMARY stages")
        if any(role != StageRole.CRITIC.value for role in roles[1:-1]):
            raise EpistemicContractError("run plan permits only CRITIC stages between PRIMARY stages")
        if len(ids) != len(set(ids)):
            raise EpistemicContractError("planned stage IDs must be unique")
        maximum = _require_nonnegative_int("maximum_stage_count", self.maximum_stage_count)
        if not 1 <= len(ids) <= maximum <= MAXIMUM_ABSOLUTE_STAGE_COUNT:
            raise EpistemicContractError("maximum_stage_count does not bound the exact stage plan")
        object.__setattr__(self, "planned_stage_ids", ids)
        object.__setattr__(self, "planned_stage_roles", roles)
        _required_text("run_policy_version", self.run_policy_version, maximum=128)
        expected_plan = compute_stage_plan_hash(
            orchestration_mode=self.orchestration_mode,
            planned_stage_ids=ids,
            planned_stage_roles=roles,
            maximum_stage_count=maximum,
        )
        if self.stage_plan_hash != expected_plan:
            raise EpistemicContractError("stage_plan_hash does not match the exact plan")
        _assert_no_authority(self)
        object.__setattr__(self, "run_hash", _verify_self_hash(self, "run_hash", self.run_hash))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicRunContract":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("run_hash", value["run_hash"])
        payload = dict(value)
        if not isinstance(payload["planned_stage_ids"], list):
            raise EpistemicContractError("planned_stage_ids must be an array")
        if not isinstance(payload["planned_stage_roles"], list):
            raise EpistemicContractError("planned_stage_roles must be an array")
        payload["planned_stage_ids"] = tuple(payload["planned_stage_ids"])
        payload["planned_stage_roles"] = tuple(payload["planned_stage_roles"])
        return cls(**payload)


def build_epistemic_run_contract(
    *,
    run_id: str,
    orchestration_mode: str | OrchestrationMode,
    source_request_hash: str,
    source_prompt: str,
    planned_stage_ids: Sequence[str],
    planned_stage_roles: Sequence[str | StageRole],
    maximum_stage_count: int | None = None,
    knowledge_context_hash: str = EMPTY_KNOWLEDGE_CONTEXT_HASH,
    knowledge_profile_hash: str = EMPTY_KNOWLEDGE_PROFILE_HASH,
    run_policy_version: str = RUN_POLICY_VERSION,
) -> EpistemicRunContract:
    _required_text("source_prompt", source_prompt)
    maximum = len(planned_stage_ids) if maximum_stage_count is None else maximum_stage_count
    plan_hash = compute_stage_plan_hash(
        orchestration_mode=orchestration_mode,
        planned_stage_ids=planned_stage_ids,
        planned_stage_roles=planned_stage_roles,
        maximum_stage_count=maximum,
    )
    return EpistemicRunContract(
        schema_version=RUN_SCHEMA_VERSION,
        run_id=run_id,
        orchestration_mode=_enum_value(OrchestrationMode, "orchestration_mode", orchestration_mode),
        source_request_hash=require_sha256("source_request_hash", source_request_hash),
        source_prompt_hash=exact_text_sha256(source_prompt),
        knowledge_context_hash=knowledge_context_hash,
        knowledge_profile_hash=knowledge_profile_hash,
        stage_plan_hash=plan_hash,
        planned_stage_ids=tuple(planned_stage_ids),
        planned_stage_roles=tuple(
            _enum_value(StageRole, "planned_stage_role", role) for role in planned_stage_roles
        ),
        maximum_stage_count=maximum,
        run_policy_version=run_policy_version,
    )


@dataclass(frozen=True, slots=True)
class EpistemicStageContract(JsonContract):
    schema_version: str
    run_id: str
    run_hash: str
    stage_id: str
    stage_index: int
    stage_role: str
    orchestration_mode: str
    source_revision_id: str
    source_revision_hash: str
    source_prompt_hash: str
    parent_stage_id: str | None
    parent_stage_hash: str | None
    parent_revision_hash: str | None
    critic_transformation_id: str
    critic_transformation_hash: str
    bound_critic_payload_hashes: tuple[str, ...]
    expected_output_kind: str
    stage_policy_version: str
    stage_hash: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    critic_output_is_authority: bool = False
    cpt_output_is_authority: bool = False
    revision_output_is_authority: bool = False
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
        if self.schema_version != STAGE_SCHEMA_VERSION:
            raise EpistemicContractError("stage schema_version differs")
        object.__setattr__(self, "run_id", _identifier("run_id", self.run_id))
        object.__setattr__(self, "stage_id", _identifier("stage_id", self.stage_id))
        object.__setattr__(
            self, "stage_role", _enum_value(StageRole, "stage_role", self.stage_role)
        )
        object.__setattr__(
            self,
            "orchestration_mode",
            _enum_value(OrchestrationMode, "orchestration_mode", self.orchestration_mode),
        )
        _require_nonnegative_int("stage_index", self.stage_index)
        _identifier("source_revision_id", self.source_revision_id)
        for name in (
            "run_hash",
            "source_revision_hash",
            "source_prompt_hash",
            "critic_transformation_hash",
        ):
            require_sha256(name, getattr(self, name))
        parent_values = (self.parent_stage_id, self.parent_stage_hash, self.parent_revision_hash)
        if self.stage_index == 0:
            if any(value is not None for value in parent_values):
                raise EpistemicContractError("first stage must not carry a parent binding")
        else:
            if any(value is None for value in parent_values):
                raise EpistemicContractError("stage after index zero requires complete parent binding")
            _identifier("parent_stage_id", self.parent_stage_id)
            require_sha256("parent_stage_hash", self.parent_stage_hash)
            require_sha256("parent_revision_hash", self.parent_revision_hash)
        payload_hashes = tuple(self.bound_critic_payload_hashes)
        for value in payload_hashes:
            require_sha256("bound_critic_payload_hash", value)
        if len(payload_hashes) != len(set(payload_hashes)):
            raise EpistemicContractError("bound critic payload hashes contain duplicates")
        object.__setattr__(self, "bound_critic_payload_hashes", payload_hashes)
        if self.stage_role == StageRole.CRITIC.value:
            _identifier("critic_transformation_id", self.critic_transformation_id)
            if self.critic_transformation_id == NO_CPT_TRANSFORMATION_ID:
                raise EpistemicContractError("critic stage requires a CPT transformation")
            if self.expected_output_kind != "CRITIC_STAGE_PAYLOAD":
                raise EpistemicContractError("critic stage output kind differs")
            if payload_hashes:
                raise EpistemicContractError("critic stage cannot bind revision payloads")
        else:
            if self.critic_transformation_id != NO_CPT_TRANSFORMATION_ID:
                raise EpistemicContractError("primary stage cannot carry a CPT transformation")
            if self.critic_transformation_hash != EMPTY_CPT_TRANSFORMATION_HASH:
                raise EpistemicContractError("primary stage CPT sentinel differs")
            expected = "PRIMARY_CANDIDATE" if self.stage_index == 0 else "PRIMARY_REVISION"
            if self.expected_output_kind != expected:
                raise EpistemicContractError("primary stage output kind differs")
            if self.stage_index == 0 and payload_hashes:
                raise EpistemicContractError("initial primary stage cannot bind critic payloads")
            if self.stage_index > 0 and not payload_hashes:
                raise EpistemicContractError("primary revision stage requires critic payload hashes")
        _required_text("stage_policy_version", self.stage_policy_version, maximum=128)
        _assert_no_authority(self)
        object.__setattr__(self, "stage_hash", _verify_self_hash(self, "stage_hash", self.stage_hash))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicStageContract":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("stage_hash", value["stage_hash"])
        payload = dict(value)
        if not isinstance(payload["bound_critic_payload_hashes"], list):
            raise EpistemicContractError("bound_critic_payload_hashes must be an array")
        payload["bound_critic_payload_hashes"] = tuple(payload["bound_critic_payload_hashes"])
        return cls(**payload)


def validate_stage_against_run(
    stage: EpistemicStageContract,
    run: EpistemicRunContract,
) -> None:
    if not isinstance(stage, EpistemicStageContract) or not isinstance(run, EpistemicRunContract):
        raise EpistemicContractError("stage and run must be canonical contracts")
    if stage.run_id != run.run_id or stage.run_hash != run.run_hash:
        raise EpistemicContractError("stage binds another run")
    if stage.orchestration_mode != run.orchestration_mode:
        raise EpistemicContractError("stage orchestration mode differs from run")
    if stage.source_prompt_hash != run.source_prompt_hash:
        raise EpistemicContractError("stage source prompt hash differs from run")
    if stage.stage_index >= len(run.planned_stage_ids):
        raise EpistemicContractError("stage index is outside the reviewed run plan")
    if run.planned_stage_ids[stage.stage_index] != stage.stage_id:
        raise EpistemicContractError("stage ID or ordering differs from run plan")
    if run.planned_stage_roles[stage.stage_index] != stage.stage_role:
        raise EpistemicContractError("stage role differs from run plan")


def validate_stage_parent_binding(
    stage: EpistemicStageContract,
    parent_stage: EpistemicStageContract | None,
    *,
    parent_revision_hash: str | None = None,
) -> None:
    if stage.stage_index == 0:
        if parent_stage is not None or parent_revision_hash is not None:
            raise EpistemicContractError("first stage cannot bind a parent")
        return
    if parent_stage is None or parent_revision_hash is None:
        raise EpistemicContractError("parent stage and revision hash are required")
    require_sha256("parent_revision_hash", parent_revision_hash)
    if stage.run_id != parent_stage.run_id or stage.run_hash != parent_stage.run_hash:
        raise EpistemicContractError("parent stage belongs to another run")
    if stage.parent_stage_id != parent_stage.stage_id:
        raise EpistemicContractError("parent stage ID differs")
    if stage.parent_stage_hash != parent_stage.stage_hash:
        raise EpistemicContractError("parent stage hash differs")
    if stage.parent_revision_hash != parent_revision_hash:
        raise EpistemicContractError("parent revision hash differs")
    if parent_revision_hash != parent_stage.source_revision_hash:
        raise EpistemicContractError("parent revision is not bound to the parent stage source")
    if stage.source_revision_id != parent_stage.source_revision_id:
        raise EpistemicContractError("stage source revision ID differs from its parent")
    if stage.orchestration_mode == OrchestrationMode.SEQUENTIAL_RING_V1.value:
        if parent_stage.stage_index != stage.stage_index - 1:
            raise EpistemicContractError("sequential stage parent is reordered")
        if stage.source_revision_hash != parent_revision_hash:
            raise EpistemicContractError("sequential stage source revision differs from parent")
    elif stage.orchestration_mode == OrchestrationMode.INDEPENDENT_PANEL_V1.value:
        if parent_stage.stage_index != 0 or parent_stage.stage_role != StageRole.PRIMARY.value:
            raise EpistemicContractError("panel stages must bind the common primary source stage")
        if stage.source_revision_hash != parent_revision_hash:
            raise EpistemicContractError("panel stage does not bind the common source revision")
    else:
        raise EpistemicContractError("unsupported stage orchestration mode")


def build_epistemic_stage_contract(
    *,
    run: EpistemicRunContract,
    stage_index: int,
    source_revision_id: str,
    source_revision_hash: str,
    parent_stage: EpistemicStageContract | None = None,
    parent_revision_hash: str | None = None,
    critic_transformation_record: object | None = None,
    bound_critic_payload_hashes: Sequence[str] = (),
    stage_policy_version: str = STAGE_POLICY_VERSION,
) -> EpistemicStageContract:
    if not isinstance(run, EpistemicRunContract):
        raise EpistemicContractError("run must be an EpistemicRunContract")
    _require_nonnegative_int("stage_index", stage_index)
    if stage_index >= len(run.planned_stage_ids):
        raise EpistemicContractError("stage index is outside the reviewed run plan")
    role = run.planned_stage_roles[stage_index]
    if role == StageRole.CRITIC.value:
        if critic_transformation_record is None:
            raise EpistemicContractError("critic stage requires a CriticTransformationRecord")
        from runtime.cpt.schema import CriticTransformationRecord
        from runtime.epistemic_orchestra.cpt_stage import hash_critic_transformation_record

        if not isinstance(critic_transformation_record, CriticTransformationRecord):
            raise EpistemicContractError("critic stage transformation type differs")
        transformation_id = critic_transformation_record.transformation_id
        transformation_hash = hash_critic_transformation_record(critic_transformation_record)
        expected_output = "CRITIC_STAGE_PAYLOAD"
    else:
        if critic_transformation_record is not None:
            raise EpistemicContractError("primary stage cannot carry a CPT transformation")
        transformation_id = NO_CPT_TRANSFORMATION_ID
        transformation_hash = EMPTY_CPT_TRANSFORMATION_HASH
        expected_output = "PRIMARY_CANDIDATE" if stage_index == 0 else "PRIMARY_REVISION"
    stage = EpistemicStageContract(
        schema_version=STAGE_SCHEMA_VERSION,
        run_id=run.run_id,
        run_hash=run.run_hash,
        stage_id=run.planned_stage_ids[stage_index],
        stage_index=stage_index,
        stage_role=role,
        orchestration_mode=run.orchestration_mode,
        source_revision_id=source_revision_id,
        source_revision_hash=source_revision_hash,
        source_prompt_hash=run.source_prompt_hash,
        parent_stage_id=None if parent_stage is None else parent_stage.stage_id,
        parent_stage_hash=None if parent_stage is None else parent_stage.stage_hash,
        parent_revision_hash=parent_revision_hash,
        critic_transformation_id=transformation_id,
        critic_transformation_hash=transformation_hash,
        bound_critic_payload_hashes=tuple(bound_critic_payload_hashes),
        expected_output_kind=expected_output,
        stage_policy_version=stage_policy_version,
    )
    validate_stage_against_run(stage, run)
    validate_stage_parent_binding(
        stage,
        parent_stage,
        parent_revision_hash=parent_revision_hash,
    )
    return stage


def validate_stage_replay_state(
    stage: EpistemicStageContract,
    *,
    consumed_stage_hashes: Iterable[str] = (),
    consumed_stage_ids: Iterable[str] = (),
) -> None:
    hashes = tuple(consumed_stage_hashes)
    ids = tuple(consumed_stage_ids)
    for value in hashes:
        require_sha256("consumed_stage_hash", value)
    if len(hashes) != len(set(hashes)) or len(ids) != len(set(ids)):
        raise EpistemicContractError("replay state contains duplicate entries")
    if stage.stage_hash in hashes or stage.stage_id in ids:
        raise EpistemicContractError("stage result has already been consumed")


def verify_epistemic_stage_chain(
    run: EpistemicRunContract,
    stages: Sequence[EpistemicStageContract],
) -> None:
    ordered = tuple(stages)
    if len(ordered) != len(run.planned_stage_ids):
        raise EpistemicContractError("stage chain does not contain the exact reviewed plan")
    if len({stage.stage_id for stage in ordered}) != len(ordered):
        raise EpistemicContractError("stage chain contains duplicate stage IDs")
    if len({stage.stage_hash for stage in ordered}) != len(ordered):
        raise EpistemicContractError("stage chain contains replayed stage hashes")
    for index, stage in enumerate(ordered):
        if stage.stage_index != index:
            raise EpistemicContractError("stage chain is reordered")
        validate_stage_against_run(stage, run)
        if index == 0:
            validate_stage_parent_binding(stage, None)
            continue
        if run.orchestration_mode == OrchestrationMode.SEQUENTIAL_RING_V1.value:
            parent = ordered[index - 1]
        else:
            parent = ordered[0]
        validate_stage_parent_binding(
            stage,
            parent,
            parent_revision_hash=parent.source_revision_hash,
        )
    if run.orchestration_mode == OrchestrationMode.INDEPENDENT_PANEL_V1.value:
        common_source = ordered[0].source_revision_hash
        for stage in ordered[1:]:
            if stage.stage_role == StageRole.CRITIC.value and stage.source_revision_hash != common_source:
                raise EpistemicContractError("independent-panel critics do not share one source revision")


@dataclass(frozen=True, slots=True)
class TruncationEvidence(JsonContract):
    schema_version: str
    was_truncated: bool
    original_character_count: int
    retained_character_count: int
    truncation_reason: str
    truncated_component: str
    content_hash_before_truncation: str
    content_hash_after_truncation: str

    def __post_init__(self) -> None:
        if self.schema_version != TRUNCATION_SCHEMA_VERSION:
            raise EpistemicContractError("truncation schema_version differs")
        if type(self.was_truncated) is not bool:
            raise EpistemicContractError("was_truncated must be bool")
        original = _require_nonnegative_int(
            "original_character_count", self.original_character_count
        )
        retained = _require_nonnegative_int(
            "retained_character_count", self.retained_character_count
        )
        _required_text("truncation_reason", self.truncation_reason, maximum=256)
        _identifier("truncated_component", self.truncated_component)
        require_sha256("content_hash_before_truncation", self.content_hash_before_truncation)
        require_sha256("content_hash_after_truncation", self.content_hash_after_truncation)
        if self.was_truncated:
            if retained >= original:
                raise EpistemicContractError("truncated content must retain fewer characters")
            if self.truncation_reason == "NOT_TRUNCATED":
                raise EpistemicContractError("truncated content requires an explicit reason")
        else:
            if retained != original:
                raise EpistemicContractError("non-truncated character counts must match")
            if self.content_hash_before_truncation != self.content_hash_after_truncation:
                raise EpistemicContractError("non-truncated content hashes must match")
            if self.truncation_reason != "NOT_TRUNCATED":
                raise EpistemicContractError("non-truncated evidence must say NOT_TRUNCATED")

    def verify_contents(self, original_content: str, retained_content: str) -> None:
        if not isinstance(original_content, str) or not isinstance(retained_content, str):
            raise EpistemicContractError("truncation contents must be text")
        if len(original_content) != self.original_character_count:
            raise EpistemicContractError("original truncation character count differs")
        if len(retained_content) != self.retained_character_count:
            raise EpistemicContractError("retained truncation character count differs")
        if exact_text_sha256(original_content) != self.content_hash_before_truncation:
            raise EpistemicContractError("pre-truncation content hash differs")
        if exact_text_sha256(retained_content) != self.content_hash_after_truncation:
            raise EpistemicContractError("post-truncation content hash differs")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TruncationEvidence":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        return cls(**dict(value))


def build_truncation_evidence(
    *,
    original_content: str,
    retained_content: str,
    truncated_component: str,
    truncation_reason: str,
) -> TruncationEvidence:
    if not isinstance(original_content, str) or not isinstance(retained_content, str):
        raise EpistemicContractError("truncation contents must be text")
    was_truncated = original_content != retained_content
    evidence = TruncationEvidence(
        schema_version=TRUNCATION_SCHEMA_VERSION,
        was_truncated=was_truncated,
        original_character_count=len(original_content),
        retained_character_count=len(retained_content),
        truncation_reason=truncation_reason if was_truncated else "NOT_TRUNCATED",
        truncated_component=truncated_component,
        content_hash_before_truncation=exact_text_sha256(original_content),
        content_hash_after_truncation=exact_text_sha256(retained_content),
    )
    evidence.verify_contents(original_content, retained_content)
    return evidence


@dataclass(frozen=True, slots=True)
class CriticIssue(JsonContract):
    issue_id: str
    issue_code: str
    severity: str
    summary: str
    evidence: str
    affected_section: str
    recommended_revision: str
    source_revision_hash: str

    def __post_init__(self) -> None:
        _identifier("issue_id", self.issue_id)
        _identifier("issue_code", self.issue_code)
        object.__setattr__(
            self, "severity", _enum_value(CriticSeverity, "severity", self.severity)
        )
        for name, maximum in (
            ("summary", 4_000),
            ("evidence", 8_000),
            ("affected_section", 1_000),
            ("recommended_revision", 8_000),
        ):
            _required_text(name, getattr(self, name), maximum=maximum)
        require_sha256("source_revision_hash", self.source_revision_hash)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CriticIssue":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class CriticStagePayload(JsonContract):
    schema_version: str
    run_id: str
    run_hash: str
    stage_id: str
    stage_hash: str
    source_revision_hash: str
    source_prompt_hash: str
    critic_outcome: str
    issues: tuple[CriticIssue, ...]
    critic_output_hash: str
    truncation_evidence: TruncationEvidence
    payload_hash: str = ""
    authority_status: str = NON_AUTHORITATIVE
    provider_output_is_authority: bool = False
    critic_output_is_authority: bool = False
    cpt_output_is_authority: bool = False
    revision_output_is_authority: bool = False
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
        if self.schema_version != CRITIC_PAYLOAD_SCHEMA_VERSION:
            raise EpistemicContractError("critic payload schema_version differs")
        _identifier("run_id", self.run_id)
        _identifier("stage_id", self.stage_id)
        for name in (
            "run_hash",
            "stage_hash",
            "source_revision_hash",
            "source_prompt_hash",
        ):
            require_sha256(name, getattr(self, name))
        object.__setattr__(
            self,
            "critic_outcome",
            _enum_value(CriticOutcome, "critic_outcome", self.critic_outcome),
        )
        issues = tuple(self.issues)
        if any(not isinstance(issue, CriticIssue) for issue in issues):
            raise EpistemicContractError("critic issues must be CriticIssue objects")
        ids = tuple(issue.issue_id for issue in issues)
        if len(ids) != len(set(ids)):
            raise EpistemicContractError("critic issue IDs must be unique")
        if any(issue.source_revision_hash != self.source_revision_hash for issue in issues):
            raise EpistemicContractError("critic issue reviews another source revision")
        object.__setattr__(self, "issues", issues)
        if not isinstance(self.truncation_evidence, TruncationEvidence):
            raise EpistemicContractError("critic truncation evidence is required")
        if self.truncation_evidence.was_truncated:
            if self.critic_outcome != CriticOutcome.CRITIC_OUTPUT_BLOCKED.value or issues:
                raise EpistemicContractError("truncated critic output must fail closed as blocked")
        elif self.critic_outcome == CriticOutcome.MATERIAL_ISSUES_FOUND.value and not issues:
            raise EpistemicContractError("material critic outcome requires at least one issue")
        elif self.critic_outcome == CriticOutcome.NO_MATERIAL_ISSUE_FOUND.value and issues:
            raise EpistemicContractError("no-material-issue outcome requires an empty issue list")
        elif self.critic_outcome in (
            CriticOutcome.CRITIC_OUTPUT_BLOCKED.value,
            CriticOutcome.CRITIC_OUTPUT_INVALID.value,
        ) and issues:
            raise EpistemicContractError("blocked or invalid critic output cannot carry usable issues")
        _assert_no_authority(self)
        output_payload = self.to_dict()
        supplied_output = output_payload.pop("critic_output_hash")
        output_payload.pop("payload_hash")
        expected_output = canonical_sha256(
            {"domain": "epistemic-critic-output-1a", "payload": output_payload}
        )
        if supplied_output not in ("", expected_output):
            raise EpistemicContractError("critic_output_hash does not match strict critic output")
        object.__setattr__(self, "critic_output_hash", expected_output)
        object.__setattr__(self, "payload_hash", _verify_self_hash(self, "payload_hash", self.payload_hash))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CriticStagePayload":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("critic_output_hash", value["critic_output_hash"])
        require_sha256("payload_hash", value["payload_hash"])
        payload = dict(value)
        if not isinstance(payload["issues"], list):
            raise EpistemicContractError("critic issues must be an array")
        payload["issues"] = tuple(CriticIssue.from_dict(item) for item in payload["issues"])
        payload["truncation_evidence"] = TruncationEvidence.from_dict(
            payload["truncation_evidence"]
        )
        return cls(**payload)


def build_critic_stage_payload(
    *,
    stage: EpistemicStageContract,
    critic_outcome: str | CriticOutcome,
    issues: Sequence[CriticIssue],
    truncation_evidence: TruncationEvidence,
) -> CriticStagePayload:
    if stage.stage_role != StageRole.CRITIC.value:
        raise EpistemicContractError("critic payload requires a critic stage")
    return CriticStagePayload(
        schema_version=CRITIC_PAYLOAD_SCHEMA_VERSION,
        run_id=stage.run_id,
        run_hash=stage.run_hash,
        stage_id=stage.stage_id,
        stage_hash=stage.stage_hash,
        source_revision_hash=stage.source_revision_hash,
        source_prompt_hash=stage.source_prompt_hash,
        critic_outcome=_enum_value(CriticOutcome, "critic_outcome", critic_outcome),
        issues=tuple(issues),
        critic_output_hash="",
        truncation_evidence=truncation_evidence,
    )


def parse_critic_stage_payload(value: str | bytes) -> CriticStagePayload:
    """Parse one strict JSON object; missing/malformed text is never a no-issue result."""

    return CriticStagePayload.from_dict(parse_strict_json_object(value))


def validate_critic_payload_against_stage(
    payload: CriticStagePayload,
    stage: EpistemicStageContract,
) -> None:
    if stage.stage_role != StageRole.CRITIC.value:
        raise EpistemicContractError("critic payload cannot bind a primary stage")
    expected = (
        (payload.run_id, stage.run_id, "run_id"),
        (payload.run_hash, stage.run_hash, "run_hash"),
        (payload.stage_id, stage.stage_id, "stage_id"),
        (payload.stage_hash, stage.stage_hash, "stage_hash"),
        (payload.source_revision_hash, stage.source_revision_hash, "source_revision_hash"),
        (payload.source_prompt_hash, stage.source_prompt_hash, "source_prompt_hash"),
    )
    for actual, bound, name in expected:
        if actual != bound:
            raise EpistemicContractError(f"critic payload {name} binding differs")
