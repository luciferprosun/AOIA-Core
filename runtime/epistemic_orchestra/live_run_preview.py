"""Pure plan preview for a bounded, explicitly confirmed Orchestra session.

The preview binds exact public model selections to the existing inert
EpistemicRunContract.  It cannot call a provider or satisfy confirmation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.epistemic_orchestra.canonical import (
    EpistemicContractError,
    canonical_sha256,
    canonical_value,
    exact_text_sha256,
    require_exact_fields,
    require_sha256,
)
from runtime.epistemic_orchestra.contracts import (
    NON_AUTHORITATIVE,
    EpistemicRunContract,
    JsonContract,
    OrchestrationMode,
    StageRole,
    build_epistemic_run_contract,
)
from runtime.epistemic_orchestra.role_binding import (
    MAXIMUM_SELECTED_MODELS,
    MINIMUM_SELECTED_MODELS,
    ModelRoleAssignment,
    OrchestraOperatorRole,
    OrchestraRoleSelection,
)


PLANNED_LIVE_STAGE_SCHEMA_VERSION = "orchestra-planned-live-stage-1a"
LIVE_RUN_PREVIEW_SCHEMA_VERSION = "orchestra-live-run-preview-1a"
LIVE_RUN_CONFIRMATION_MATERIAL_SCHEMA_VERSION = (
    "orchestra-live-run-confirmation-material-1a"
)
LIVE_RUN_POLICY_VERSION = "orchestra-controlled-live-demo-policy-1a"
RUN_ORCHESTRA_ONCE_ACTION = "RUN_ORCHESTRA_ONCE"
MINIMUM_TIMEOUT_SECONDS = 1
MAXIMUM_TIMEOUT_SECONDS = 30
MINIMUM_OUTPUT_TOKENS = 1
MAXIMUM_OUTPUT_TOKENS = 512

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


def _identifier(name: str, value: object) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise EpistemicContractError(f"{name} is not a bounded identifier")
    return value


def _bounded_int(name: str, value: object, *, minimum: int, maximum: int) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise EpistemicContractError(f"{name} must be between {minimum} and {maximum}")
    return value


def _positive_epoch(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise EpistemicContractError(f"{name} must be a positive integer epoch")
    return value


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
class PlannedLiveStage(JsonContract):
    schema_version: str
    call_index: int
    stage_id: str
    operator_role: str
    role_assignment_hash: str
    connection_id: str
    connection_revision_hash: str
    model_profile_id: str
    model_revision_hash: str
    remote_model_id: str
    timeout_seconds: int
    maximum_output_tokens: int
    plan_entry_hash: str = ""
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
        if self.schema_version != PLANNED_LIVE_STAGE_SCHEMA_VERSION:
            raise EpistemicContractError("planned live stage schema_version differs")
        _bounded_int("call_index", self.call_index, minimum=0, maximum=4)
        _identifier("stage_id", self.stage_id)
        try:
            role = OrchestraOperatorRole(self.operator_role).value
        except (TypeError, ValueError) as exc:
            raise EpistemicContractError("planned live stage role is unsupported") from exc
        object.__setattr__(self, "operator_role", role)
        require_sha256("role_assignment_hash", self.role_assignment_hash)
        _identifier("connection_id", self.connection_id)
        require_sha256("connection_revision_hash", self.connection_revision_hash)
        _identifier("model_profile_id", self.model_profile_id)
        require_sha256("model_revision_hash", self.model_revision_hash)
        if not isinstance(self.remote_model_id, str) or not self.remote_model_id.strip():
            raise EpistemicContractError("remote_model_id must be non-blank text")
        _bounded_int(
            "timeout_seconds",
            self.timeout_seconds,
            minimum=MINIMUM_TIMEOUT_SECONDS,
            maximum=MAXIMUM_TIMEOUT_SECONDS,
        )
        _bounded_int(
            "maximum_output_tokens",
            self.maximum_output_tokens,
            minimum=MINIMUM_OUTPUT_TOKENS,
            maximum=MAXIMUM_OUTPUT_TOKENS,
        )
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "plan_entry_hash",
            _self_hash(self, "plan_entry_hash", self.plan_entry_hash),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PlannedLiveStage":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("plan_entry_hash", value["plan_entry_hash"])
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class OrchestraLiveRunPreview(JsonContract):
    schema_version: str
    orchestra_run_id: str
    run_hash: str
    source_request_hash: str
    source_prompt_hash: str
    role_selection_hash: str
    epistemic_stage_plan_hash: str
    planned_calls: tuple[PlannedLiveStage, ...]
    final_primary_stage_id: str
    final_primary_is_inert: bool
    timeout_seconds: int
    maximum_output_tokens: int
    expires_at_epoch: int
    live_run_policy_version: str
    preview_hash: str = ""
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
        if self.schema_version != LIVE_RUN_PREVIEW_SCHEMA_VERSION:
            raise EpistemicContractError("live run preview schema_version differs")
        _identifier("orchestra_run_id", self.orchestra_run_id)
        for name in (
            "run_hash",
            "source_request_hash",
            "source_prompt_hash",
            "role_selection_hash",
            "epistemic_stage_plan_hash",
        ):
            require_sha256(name, getattr(self, name))
        calls = tuple(self.planned_calls)
        if any(not isinstance(item, PlannedLiveStage) for item in calls):
            raise EpistemicContractError("planned_calls must contain PlannedLiveStage objects")
        if not MINIMUM_SELECTED_MODELS <= len(calls) <= MAXIMUM_SELECTED_MODELS:
            raise EpistemicContractError("preview requires two to five planned calls")
        if tuple(item.call_index for item in calls) != tuple(range(len(calls))):
            raise EpistemicContractError("planned call indexes must be exact and ordered")
        if calls[0].operator_role != OrchestraOperatorRole.MAIN.value:
            raise EpistemicContractError("first planned call must be MAIN")
        roles = tuple(item.operator_role for item in calls)
        if roles.count(OrchestraOperatorRole.MAIN.value) != 1:
            raise EpistemicContractError("preview requires exactly one MAIN call")
        if not any(
            role in (OrchestraOperatorRole.CRITIC.value, OrchestraOperatorRole.AUDITOR.value)
            for role in roles
        ):
            raise EpistemicContractError("preview requires a CRITIC or AUDITOR call")
        has_synthesizer = OrchestraOperatorRole.SYNTHESIZER.value in roles
        if roles.count(OrchestraOperatorRole.SYNTHESIZER.value) > 1 or (
            has_synthesizer and roles[-1] != OrchestraOperatorRole.SYNTHESIZER.value
        ):
            raise EpistemicContractError("preview SYNTHESIZER must be unique and last")
        if type(self.final_primary_is_inert) is not bool:
            raise EpistemicContractError("final_primary_is_inert must be bool")
        if self.final_primary_is_inert == has_synthesizer:
            raise EpistemicContractError("final primary inertness differs from selection")
        _identifier("final_primary_stage_id", self.final_primary_stage_id)
        stage_ids = tuple(item.stage_id for item in calls)
        if len(stage_ids) != len(set(stage_ids)):
            raise EpistemicContractError("planned live stage IDs must be unique")
        if has_synthesizer:
            if calls[-1].stage_id != self.final_primary_stage_id:
                raise EpistemicContractError("SYNTHESIZER must bind the final PRIMARY stage")
        elif self.final_primary_stage_id in stage_ids:
            raise EpistemicContractError("inert final PRIMARY cannot be a planned call")
        _bounded_int(
            "timeout_seconds",
            self.timeout_seconds,
            minimum=MINIMUM_TIMEOUT_SECONDS,
            maximum=MAXIMUM_TIMEOUT_SECONDS,
        )
        _bounded_int(
            "maximum_output_tokens",
            self.maximum_output_tokens,
            minimum=MINIMUM_OUTPUT_TOKENS,
            maximum=MAXIMUM_OUTPUT_TOKENS,
        )
        if any(
            item.timeout_seconds != self.timeout_seconds
            or item.maximum_output_tokens != self.maximum_output_tokens
            for item in calls
        ):
            raise EpistemicContractError("planned call bounds differ from preview bounds")
        _positive_epoch("expires_at_epoch", self.expires_at_epoch)
        if self.live_run_policy_version != LIVE_RUN_POLICY_VERSION:
            raise EpistemicContractError("live run policy version differs")
        object.__setattr__(self, "planned_calls", calls)
        _assert_no_authority(self)
        object.__setattr__(
            self,
            "preview_hash",
            _self_hash(self, "preview_hash", self.preview_hash),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OrchestraLiveRunPreview":
        require_exact_fields(value, set(cls.__dataclass_fields__), label=cls.__name__)
        require_sha256("preview_hash", value["preview_hash"])
        payload = dict(value)
        if not isinstance(payload["planned_calls"], list):
            raise EpistemicContractError("planned_calls must be an array")
        payload["planned_calls"] = tuple(
            PlannedLiveStage.from_dict(item) for item in payload["planned_calls"]
        )
        return cls(**payload)

    def confirmation_material(self) -> dict[str, Any]:
        """Return exact material a later explicit human action must confirm."""

        return {
            "schema_version": LIVE_RUN_CONFIRMATION_MATERIAL_SCHEMA_VERSION,
            "action": RUN_ORCHESTRA_ONCE_ACTION,
            "orchestra_run_id": self.orchestra_run_id,
            "run_hash": self.run_hash,
            "role_selection_hash": self.role_selection_hash,
            "preview_hash": self.preview_hash,
            "expires_at_epoch": self.expires_at_epoch,
            "authority_status": NON_AUTHORITATIVE,
            "provider_call_permitted": False,
            "human_action_required": True,
        }


def _stage_id(prefix: str, assignment: ModelRoleAssignment) -> str:
    return f"orchestra-{prefix}-{assignment.ordinal}-{assignment.role_assignment_hash[:16]}"


def _planned_call(
    *,
    assignment: ModelRoleAssignment,
    stage_id: str,
    timeout_seconds: int,
    maximum_output_tokens: int,
) -> PlannedLiveStage:
    return PlannedLiveStage(
        schema_version=PLANNED_LIVE_STAGE_SCHEMA_VERSION,
        call_index=assignment.ordinal,
        stage_id=stage_id,
        operator_role=assignment.role,
        role_assignment_hash=assignment.role_assignment_hash,
        connection_id=assignment.connection_id,
        connection_revision_hash=assignment.connection_revision_hash,
        model_profile_id=assignment.model_profile_id,
        model_revision_hash=assignment.model_revision_hash,
        remote_model_id=assignment.remote_model_id,
        timeout_seconds=timeout_seconds,
        maximum_output_tokens=maximum_output_tokens,
    )


def build_live_run_preview(
    *,
    orchestra_run_id: str,
    source_prompt: str,
    role_selection: OrchestraRoleSelection,
    timeout_seconds: int,
    maximum_output_tokens: int,
    expires_at_epoch: int,
) -> tuple[EpistemicRunContract, OrchestraLiveRunPreview]:
    """Build an inert preview; this function performs no provider call."""

    if not isinstance(role_selection, OrchestraRoleSelection):
        raise EpistemicContractError("role_selection must be OrchestraRoleSelection")
    timeout = _bounded_int(
        "timeout_seconds",
        timeout_seconds,
        minimum=MINIMUM_TIMEOUT_SECONDS,
        maximum=MAXIMUM_TIMEOUT_SECONDS,
    )
    output_tokens = _bounded_int(
        "maximum_output_tokens",
        maximum_output_tokens,
        minimum=MINIMUM_OUTPUT_TOKENS,
        maximum=MAXIMUM_OUTPUT_TOKENS,
    )
    expiration = _positive_epoch("expires_at_epoch", expires_at_epoch)
    assignments = role_selection.assignments
    synthesizer = (
        assignments[-1]
        if assignments[-1].role == OrchestraOperatorRole.SYNTHESIZER.value
        else None
    )
    review_assignments = assignments[1:-1] if synthesizer is not None else assignments[1:]

    main_stage_id = _stage_id("main", assignments[0])
    review_stage_ids = tuple(_stage_id("review", item) for item in review_assignments)
    final_stage_id = (
        _stage_id("synthesis", synthesizer)
        if synthesizer is not None
        else f"orchestra-final-inert-{role_selection.role_selection_hash[:16]}"
    )
    stage_id_by_ordinal = {assignments[0].ordinal: main_stage_id}
    stage_id_by_ordinal.update(
        {assignment.ordinal: stage_id for assignment, stage_id in zip(review_assignments, review_stage_ids)}
    )
    if synthesizer is not None:
        stage_id_by_ordinal[synthesizer.ordinal] = final_stage_id
    planned_calls = tuple(
        _planned_call(
            assignment=assignment,
            stage_id=stage_id_by_ordinal[assignment.ordinal],
            timeout_seconds=timeout,
            maximum_output_tokens=output_tokens,
        )
        for assignment in assignments
    )
    source_prompt_hash = exact_text_sha256(source_prompt)
    source_request_hash = canonical_sha256(
        {
            "domain": "aoia-controlled-live-orchestra-source-request-1a",
            "source_prompt_hash": source_prompt_hash,
            "role_selection_hash": role_selection.role_selection_hash,
            "planned_call_hashes": tuple(item.plan_entry_hash for item in planned_calls),
            "final_primary_stage_id": final_stage_id,
            "final_primary_is_inert": synthesizer is None,
            "timeout_seconds": timeout,
            "maximum_output_tokens": output_tokens,
            "expires_at_epoch": expiration,
            "live_run_policy_version": LIVE_RUN_POLICY_VERSION,
        }
    )
    planned_stage_ids = (main_stage_id, *review_stage_ids, final_stage_id)
    planned_stage_roles = (
        StageRole.PRIMARY.value,
        *(StageRole.CRITIC.value for _ in review_stage_ids),
        StageRole.PRIMARY.value,
    )
    run = build_epistemic_run_contract(
        run_id=orchestra_run_id,
        orchestration_mode=OrchestrationMode.INDEPENDENT_PANEL_V1,
        source_request_hash=source_request_hash,
        source_prompt=source_prompt,
        planned_stage_ids=planned_stage_ids,
        planned_stage_roles=planned_stage_roles,
    )
    preview = OrchestraLiveRunPreview(
        schema_version=LIVE_RUN_PREVIEW_SCHEMA_VERSION,
        orchestra_run_id=run.run_id,
        run_hash=run.run_hash,
        source_request_hash=source_request_hash,
        source_prompt_hash=run.source_prompt_hash,
        role_selection_hash=role_selection.role_selection_hash,
        epistemic_stage_plan_hash=run.stage_plan_hash,
        planned_calls=planned_calls,
        final_primary_stage_id=final_stage_id,
        final_primary_is_inert=synthesizer is None,
        timeout_seconds=timeout,
        maximum_output_tokens=output_tokens,
        expires_at_epoch=expiration,
        live_run_policy_version=LIVE_RUN_POLICY_VERSION,
    )
    return run, preview


def build_live_run_confirmation_material(
    preview: OrchestraLiveRunPreview,
) -> dict[str, Any]:
    if not isinstance(preview, OrchestraLiveRunPreview):
        raise EpistemicContractError("preview must be OrchestraLiveRunPreview")
    return preview.confirmation_material()


def validate_live_run_preview(
    preview: OrchestraLiveRunPreview,
    *,
    run: EpistemicRunContract,
    source_prompt: str,
    role_selection: OrchestraRoleSelection,
) -> None:
    """Rebuild the preview and reject stale or altered confirmation material."""

    if not isinstance(preview, OrchestraLiveRunPreview) or not isinstance(
        run, EpistemicRunContract
    ):
        raise EpistemicContractError("canonical run and preview contracts are required")
    expected_run, expected_preview = build_live_run_preview(
        orchestra_run_id=preview.orchestra_run_id,
        source_prompt=source_prompt,
        role_selection=role_selection,
        timeout_seconds=preview.timeout_seconds,
        maximum_output_tokens=preview.maximum_output_tokens,
        expires_at_epoch=preview.expires_at_epoch,
    )
    if canonical_value(run) != canonical_value(expected_run):
        raise EpistemicContractError("live run contract differs from the exact preview")
    if canonical_value(preview) != canonical_value(expected_preview):
        raise EpistemicContractError("live run preview is stale or altered")
