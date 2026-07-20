"""Deterministic, non-semantic planning for explicit Knowledge Profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.policy import KnowledgeHubPolicy
from runtime.knowledge_modules.profiles import (
    KnowledgeProfile,
    KnowledgeProfileModuleSelection,
    normalize_module_filters,
)


KNOWLEDGE_QUERY_SCHEMA_VERSION = "knowledge-query-1b"
MODULE_QUERY_PLAN_SCHEMA_VERSION = "module-query-plan-1b"
COMPOSITE_QUERY_PLAN_SCHEMA_VERSION = "composite-knowledge-query-plan-1b"
SEQUENTIAL = "SEQUENTIAL"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _authority_is_false(value: Any) -> bool:
    return all(
        type(getattr(value, name)) is bool and not getattr(value, name)
        for name in AUTHORITY_FLAG_NAMES
    )


@dataclass(frozen=True, slots=True)
class KnowledgeQuery(JsonContract):
    schema_version: str
    question: str
    authority_status: str = NON_AUTHORITATIVE
    query_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != KNOWLEDGE_QUERY_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROFILE_INVALID", "knowledge query schema differs")
        if not isinstance(self.question, str) or not self.question.strip():
            raise KnowledgeModuleError("PROFILE_INVALID", "question must not be empty")
        question = self.question.strip()
        if len(question) > 16_000:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "question exceeds bounded length")
        object.__setattr__(self, "question", question)
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "query cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("query_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROFILE_INVALID", "query hash differs")
        object.__setattr__(self, "query_hash", expected)


@dataclass(frozen=True, slots=True)
class ModuleQueryPlan(JsonContract):
    schema_version: str
    module_id: str
    instance_id: str
    module_version: str
    expected_module_descriptor_hash: str
    priority: int
    question: str
    retrieval_mode: str
    module_specific_filters: tuple[tuple[str, Any], ...]
    max_results: int
    max_excerpt_characters: int
    max_total_context_characters: int
    authority_status: str = NON_AUTHORITATIVE
    plan_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != MODULE_QUERY_PLAN_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROFILE_INVALID", "module query plan schema differs")
        if not all(isinstance(value, str) and value for value in (self.module_id, self.instance_id, self.module_version, self.question)):
            raise KnowledgeModuleError("PROFILE_INVALID", "module query plan identity is incomplete")
        if not _SHA256.fullmatch(self.expected_module_descriptor_hash):
            raise KnowledgeModuleError("PROFILE_INVALID", "module descriptor hash is invalid")
        if type(self.priority) is not int or not 0 <= self.priority <= 10_000:
            raise KnowledgeModuleError("PROFILE_INVALID", "module query priority is invalid")
        object.__setattr__(
            self,
            "module_specific_filters",
            normalize_module_filters(self.module_specific_filters),
        )
        if type(self.max_results) is not int or not 1 <= self.max_results <= 20:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "planned result limit differs")
        if type(self.max_excerpt_characters) is not int or not 256 <= self.max_excerpt_characters <= 4_000:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "planned excerpt limit differs")
        if (
            type(self.max_total_context_characters) is not int
            or not 1_024 <= self.max_total_context_characters <= 32_000
        ):
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "planned context limit differs")
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "module plan cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("plan_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROFILE_INVALID", "module query plan hash differs")
        object.__setattr__(self, "plan_hash", expected)

@dataclass(frozen=True, slots=True)
class CompositeKnowledgeQueryPlan(JsonContract):
    schema_version: str
    profile_id: str
    profile_hash: str
    query_hash: str
    module_plans: tuple[ModuleQueryPlan, ...]
    total_planned_results: int
    total_planned_context_characters: int
    execution_model: str = SEQUENTIAL
    authority_status: str = NON_AUTHORITATIVE
    plan_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != COMPOSITE_QUERY_PLAN_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROFILE_INVALID", "composite query plan schema differs")
        if not _SHA256.fullmatch(self.profile_hash) or not _SHA256.fullmatch(self.query_hash):
            raise KnowledgeModuleError("PROFILE_INVALID", "composite query binding hash is invalid")
        plans = tuple(self.module_plans)
        if plans != tuple(sorted(plans, key=lambda item: (item.priority, item.module_id, item.instance_id))):
            raise KnowledgeModuleError("PROFILE_INVALID", "module plan ordering differs")
        if len(plans) != len({item.module_id for item in plans}) or len(plans) != len({item.instance_id for item in plans}):
            raise KnowledgeModuleError("PROFILE_INVALID", "composite plan repeats a module or instance")
        object.__setattr__(self, "module_plans", plans)
        if self.total_planned_results != sum(item.max_results for item in plans):
            raise KnowledgeModuleError("PROFILE_INVALID", "planned result total differs")
        if self.total_planned_context_characters != sum(item.max_total_context_characters for item in plans):
            raise KnowledgeModuleError("PROFILE_INVALID", "planned context total differs")
        if self.execution_model != SEQUENTIAL:
            raise KnowledgeModuleError("PROFILE_INVALID", "execution model must be sequential")
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "composite plan cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("plan_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROFILE_INVALID", "composite query plan hash differs")
        object.__setattr__(self, "plan_hash", expected)


@dataclass(frozen=True, slots=True)
class _Allocation:
    selection: KnowledgeProfileModuleSelection
    max_results: int
    max_context: int


def _allocate_budgets(
    selections: tuple[KnowledgeProfileModuleSelection, ...],
    profile: KnowledgeProfile,
    policy: KnowledgeHubPolicy,
) -> tuple[_Allocation, ...]:
    """Reserve each module's minimum, then grant remaining budget in plan order.

    The input is already ordered by explicit profile priority, module ID, and
    instance ID. Each enabled module first receives the lesser of its requested
    allocation and the reviewed minimum. Remaining result and context capacity
    is then granted in that stable order up to each explicit per-module maximum.
    """
    if not selections:
        return ()
    reserved_results = [min(item.per_module_max_results, policy.minimum_results_per_module) for item in selections]
    reserved_context = [
        min(item.per_module_max_context_characters, policy.minimum_context_characters_per_module)
        for item in selections
    ]
    if sum(reserved_results) > profile.global_max_results or sum(reserved_context) > profile.global_max_context_characters:
        raise KnowledgeModuleError(
            "GLOBAL_BUDGET_EXCEEDED", "global budget cannot reserve every enabled module"
        )
    remaining_results = profile.global_max_results - sum(reserved_results)
    remaining_context = profile.global_max_context_characters - sum(reserved_context)
    result_allocations = list(reserved_results)
    context_allocations = list(reserved_context)
    for index, selection in enumerate(selections):
        result_capacity = selection.per_module_max_results - result_allocations[index]
        granted_results = min(result_capacity, remaining_results)
        result_allocations[index] += granted_results
        remaining_results -= granted_results
        context_capacity = selection.per_module_max_context_characters - context_allocations[index]
        granted_context = min(context_capacity, remaining_context)
        context_allocations[index] += granted_context
        remaining_context -= granted_context
    return tuple(
        _Allocation(selection, result_allocations[index], context_allocations[index])
        for index, selection in enumerate(selections)
    )


def build_composite_query_plan(
    registry: Any,
    profile: KnowledgeProfile,
    query: KnowledgeQuery,
    policy: KnowledgeHubPolicy,
) -> CompositeKnowledgeQueryPlan:
    resolved = registry.resolve_profile(profile, policy)
    selections = tuple(item[0] for item in resolved)
    allocations = _allocate_budgets(selections, profile, policy)
    resolved_by_instance = {item[0].instance_id: item for item in resolved}
    plans: list[ModuleQueryPlan] = []
    for allocation in allocations:
        selection, registration, instance_registration = resolved_by_instance[allocation.selection.instance_id]
        descriptor = registration.descriptor
        instance = instance_registration.descriptor
        if selection.retrieval_mode not in descriptor.retrieval_modes:
            raise KnowledgeModuleError("PROFILE_INVALID", "module retrieval mode is unsupported")
        selected_filters = dict(selection.module_specific_filters)
        unknown_filters = set(selected_filters) - set(descriptor.supported_filters)
        if unknown_filters:
            raise KnowledgeModuleError("PROFILE_INVALID", f"module filters are unsupported: {sorted(unknown_filters)}")
        selected_filters.setdefault("jurisdictions", descriptor.jurisdictions)
        selected_filters.setdefault("languages", descriptor.languages)
        plan = ModuleQueryPlan(
            schema_version=MODULE_QUERY_PLAN_SCHEMA_VERSION,
            module_id=descriptor.module_id,
            instance_id=instance.instance_id,
            module_version=descriptor.module_version,
            expected_module_descriptor_hash=descriptor.descriptor_hash,
            priority=selection.priority,
            question=query.question,
            retrieval_mode=selection.retrieval_mode,
            module_specific_filters=tuple(selected_filters.items()),
            max_results=min(allocation.max_results, policy.maximum_per_module_results),
            max_excerpt_characters=policy.maximum_excerpt_characters,
            max_total_context_characters=min(
                allocation.max_context,
                policy.maximum_per_module_context_characters,
            ),
        )
        plans.append(plan)
    ordered = tuple(sorted(plans, key=lambda item: (item.priority, item.module_id, item.instance_id)))
    return CompositeKnowledgeQueryPlan(
        schema_version=COMPOSITE_QUERY_PLAN_SCHEMA_VERSION,
        profile_id=profile.profile_id,
        profile_hash=profile.profile_hash,
        query_hash=query.query_hash,
        module_plans=ordered,
        total_planned_results=sum(item.max_results for item in ordered),
        total_planned_context_characters=sum(item.max_total_context_characters for item in ordered),
    )


__all__ = (
    "COMPOSITE_QUERY_PLAN_SCHEMA_VERSION",
    "CompositeKnowledgeQueryPlan",
    "KNOWLEDGE_QUERY_SCHEMA_VERSION",
    "KnowledgeQuery",
    "MODULE_QUERY_PLAN_SCHEMA_VERSION",
    "ModuleQueryPlan",
    "SEQUENTIAL",
    "build_composite_query_plan",
)
