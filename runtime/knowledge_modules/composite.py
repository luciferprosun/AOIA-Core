"""Provenance-preserving composition without semantic merge or conflict resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.evidence import KnowledgeEvidenceBundle, KnowledgeEvidenceItem
from runtime.knowledge_modules.instances import KnowledgeModuleInstanceDescriptor
from runtime.knowledge_modules.planning import CompositeKnowledgeQueryPlan, ModuleQueryPlan
from runtime.knowledge_modules.policy import KnowledgeHubPolicy
from runtime.knowledge_modules.profiles import KnowledgeProfile


ITEM_PROVENANCE_SCHEMA_VERSION = "knowledge-evidence-instance-provenance-1b"
MODULE_INSTANCE_BUNDLE_SCHEMA_VERSION = "module-instance-evidence-bundle-1b"
COMPOSITE_BUNDLE_SCHEMA_VERSION = "composite-knowledge-evidence-bundle-1b"
EXECUTION_RESULT_SCHEMA_VERSION = "knowledge-hub-execution-result-1b"
NOT_EVALUATED = "NOT_EVALUATED"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _authority_is_false(value: Any) -> bool:
    return all(type(getattr(value, name)) is bool and not getattr(value, name) for name in AUTHORITY_FLAG_NAMES)


@dataclass(frozen=True, slots=True)
class KnowledgeEvidenceInstanceProvenance(JsonContract):
    schema_version: str
    evidence_id: str
    module_id: str
    instance_id: str
    module_version: str
    domain: str
    corpus_snapshot_id: str
    source_object_sha256: str
    jurisdiction: str
    temporal_status: str
    source_class: str
    warnings: tuple[str, ...]
    evidence_item: KnowledgeEvidenceItem
    authority_status: str = NON_AUTHORITATIVE
    provenance_hash: str = ""
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
        if self.schema_version != ITEM_PROVENANCE_SCHEMA_VERSION:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "item provenance schema differs")
        required = (
            self.evidence_id,
            self.module_id,
            self.instance_id,
            self.module_version,
            self.domain,
            self.corpus_snapshot_id,
            self.source_object_sha256,
            self.jurisdiction,
            self.temporal_status,
            self.source_class,
        )
        if any(not isinstance(value, str) or not value for value in required):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "item provenance is incomplete")
        object.__setattr__(self, "warnings", tuple(sorted(set(self.warnings))))
        if (
            not isinstance(self.evidence_item, KnowledgeEvidenceItem)
            or self.evidence_item.evidence_id != self.evidence_id
            or self.evidence_item.module_id != self.module_id
            or self.evidence_item.module_version != self.module_version
            or self.evidence_item.corpus_snapshot_id != self.corpus_snapshot_id
            or self.evidence_item.source_object_sha256 != self.source_object_sha256
            or self.evidence_item.jurisdiction != self.jurisdiction
            or self.evidence_item.temporal_status != self.temporal_status
            or self.evidence_item.source_class != self.source_class
            or self.evidence_item.warnings != self.warnings
        ):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "wrapped evidence provenance differs")
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "item provenance cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("provenance_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "item provenance hash differs")
        object.__setattr__(self, "provenance_hash", expected)


@dataclass(frozen=True, slots=True)
class ModuleExecutionOutcome:
    descriptor: KnowledgeModuleDescriptor
    instance: KnowledgeModuleInstanceDescriptor
    bundle: KnowledgeEvidenceBundle

    def __post_init__(self) -> None:
        if (
            self.bundle.module_id != self.descriptor.module_id
            or self.bundle.module_version != self.descriptor.module_version
            or self.instance.module_id != self.descriptor.module_id
            or self.instance.module_version != self.descriptor.module_version
        ):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module outcome provenance differs")


@dataclass(frozen=True, slots=True)
class ModuleInstanceEvidenceBundle(JsonContract):
    schema_version: str
    module_id: str
    instance_id: str
    module_version: str
    deployment_id: str
    domain: str
    source_bundle_hash: str
    evidence_bundle: KnowledgeEvidenceBundle
    evidence_items: tuple[KnowledgeEvidenceInstanceProvenance, ...]
    truncated: bool
    authority_status: str = NON_AUTHORITATIVE
    module_instance_bundle_hash: str = ""
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
        if self.schema_version != MODULE_INSTANCE_BUNDLE_SCHEMA_VERSION:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module instance bundle schema differs")
        if (
            self.evidence_bundle.module_id != self.module_id
            or self.evidence_bundle.module_version != self.module_version
        ):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module bundle provenance differs")
        if any(
            not isinstance(value, str) or not value
            for value in (
                self.module_id,
                self.instance_id,
                self.module_version,
                self.deployment_id,
                self.domain,
            )
        ) or not _SHA256.fullmatch(self.source_bundle_hash):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module bundle identity is incomplete")
        provenance = tuple(self.evidence_items)
        if len(provenance) != len(self.evidence_bundle.evidence_items):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "item provenance count differs")
        for item, proof in zip(self.evidence_bundle.evidence_items, provenance, strict=True):
            if (
                proof.evidence_id != item.evidence_id
                or proof.module_id != self.module_id
                or proof.instance_id != self.instance_id
                or proof.module_version != self.module_version
                or proof.domain != self.domain
                or proof.source_object_sha256 != item.source_object_sha256
            ):
                raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "item instance provenance differs")
        object.__setattr__(self, "evidence_items", provenance)
        if type(self.truncated) is not bool:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module truncation flag is invalid")
        if self.truncated != self.evidence_bundle.truncated:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module truncation binding differs")
        if not self.truncated and self.source_bundle_hash != self.evidence_bundle.bundle_hash:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "source bundle hash differs")
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "module bundle cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("module_instance_bundle_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module instance bundle hash differs")
        object.__setattr__(self, "module_instance_bundle_hash", expected)

    @property
    def item_provenance(self) -> tuple[KnowledgeEvidenceInstanceProvenance, ...]:
        """Compatibility name for callers introduced during the 1B transition."""
        return self.evidence_items


@dataclass(frozen=True, slots=True)
class CompositeKnowledgeEvidenceBundle(JsonContract):
    schema_version: str
    composite_bundle_id: str
    profile_id: str
    profile_hash: str
    query_hash: str
    selected_module_ids: tuple[str, ...]
    selected_instance_ids: tuple[str, ...]
    module_bundles: tuple[ModuleInstanceEvidenceBundle, ...]
    module_failures: tuple[KnowledgeModuleFailure, ...]
    total_evidence_items: int
    total_context_characters: int
    truncated: bool
    conflict_evaluation_status: str = NOT_EVALUATED
    authority_status: str = NON_AUTHORITATIVE
    composite_bundle_hash: str = ""
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
        if self.schema_version != COMPOSITE_BUNDLE_SCHEMA_VERSION:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite bundle schema differs")
        module_ids = tuple(self.selected_module_ids)
        instance_ids = tuple(self.selected_instance_ids)
        if len(module_ids) != len(set(module_ids)) or len(instance_ids) != len(set(instance_ids)):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite selection repeats identity")
        if len(module_ids) != len(instance_ids):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "selected module and instance counts differ")
        object.__setattr__(self, "selected_module_ids", module_ids)
        object.__setattr__(self, "selected_instance_ids", instance_ids)
        bundles = tuple(self.module_bundles)
        bundle_pairs = tuple((item.module_id, item.instance_id) for item in bundles)
        selected_pairs = tuple(zip(module_ids, instance_ids, strict=True))
        if len(bundle_pairs) != len(set(bundle_pairs)) or any(
            pair not in selected_pairs for pair in bundle_pairs
        ):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module bundle selection differs")
        positions = tuple(selected_pairs.index(pair) for pair in bundle_pairs)
        if positions != tuple(sorted(positions)):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module bundle order differs")
        object.__setattr__(self, "module_bundles", bundles)
        failures = tuple(sorted(self.module_failures, key=lambda item: (item.module_id, item.code, item.failure_hash)))
        if any(item.module_id not in module_ids for item in failures):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "module failure selection differs")
        object.__setattr__(self, "module_failures", failures)
        if self.total_evidence_items != sum(len(item.evidence_bundle.evidence_items) for item in bundles):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite evidence total differs")
        if self.total_context_characters != sum(item.evidence_bundle.total_context_characters for item in bundles):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite context total differs")
        if type(self.truncated) is not bool:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite truncation flag is invalid")
        if any(item.truncated for item in bundles) and not self.truncated:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite omitted module truncation")
        if self.conflict_evaluation_status != NOT_EVALUATED:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "conflicts must remain unevaluated")
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "composite bundle cannot carry authority")
        payload = self.to_dict()
        supplied_hash = payload.pop("composite_bundle_hash")
        supplied_id = payload.pop("composite_bundle_id")
        base_hash = canonical_hash(payload)
        expected_id = f"composite-knowledge-bundle-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite bundle ID differs")
        object.__setattr__(self, "composite_bundle_id", expected_id)
        payload["composite_bundle_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "composite bundle hash differs")
        object.__setattr__(self, "composite_bundle_hash", expected_hash)


@dataclass(frozen=True, slots=True)
class KnowledgeHubExecutionResult(JsonContract):
    schema_version: str
    status: str
    profile: KnowledgeProfile
    query_plan: CompositeKnowledgeQueryPlan
    composite_bundle: CompositeKnowledgeEvidenceBundle
    verification_results: tuple[KnowledgeModuleVerificationResult, ...]
    authority_status: str = NON_AUTHORITATIVE
    result_hash: str = ""
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
        if self.schema_version != EXECUTION_RESULT_SCHEMA_VERSION or not self.status:
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "execution result schema differs")
        if (
            self.profile.profile_hash != self.query_plan.profile_hash
            or self.profile.profile_hash != self.composite_bundle.profile_hash
            or self.query_plan.query_hash != self.composite_bundle.query_hash
        ):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "execution result binding differs")
        object.__setattr__(self, "verification_results", tuple(self.verification_results))
        if self.authority_status != NON_AUTHORITATIVE or not _authority_is_false(self):
            raise KnowledgeModuleError("MODULE_AUTHORITY_CLAIM_BLOCKED", "execution result cannot carry authority")
        payload = self.to_dict()
        supplied = payload.pop("result_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("COMPOSITE_BUILD_FAILED", "execution result hash differs")
        object.__setattr__(self, "result_hash", expected)


def _bounded_item(item: KnowledgeEvidenceItem, allowed_characters: int) -> KnowledgeEvidenceItem:
    if len(item.bounded_excerpt) <= allowed_characters:
        return item
    warnings = tuple(sorted(set((*item.warnings, "EXCERPT_TRUNCATED"))))
    return replace(
        item,
        bounded_excerpt=item.bounded_excerpt[:allowed_characters],
        excerpt_truncated=True,
        warnings=warnings,
        evidence_id="",
        evidence_hash="",
    )


def _bounded_bundle(
    bundle: KnowledgeEvidenceBundle,
    plan: ModuleQueryPlan,
    remaining_items: int,
    remaining_context: int,
) -> tuple[KnowledgeEvidenceBundle, int, int, bool]:
    item_limit = min(plan.max_results, remaining_items)
    context_limit = min(plan.max_total_context_characters, remaining_context)
    selected: list[KnowledgeEvidenceItem] = []
    used_context = 0
    changed = False
    for item in bundle.evidence_items:
        if len(selected) >= item_limit or used_context >= context_limit:
            changed = True
            break
        allowed = min(
            plan.max_excerpt_characters,
            context_limit - used_context,
            len(item.bounded_excerpt),
        )
        if allowed <= 0:
            changed = True
            break
        bounded = _bounded_item(item, allowed)
        changed = changed or bounded is not item
        selected.append(bounded)
        used_context += len(bounded.bounded_excerpt)
    if len(selected) != len(bundle.evidence_items):
        changed = True
    truncated = bundle.truncated or changed
    if not changed:
        return bundle, len(selected), used_context, truncated
    rebuilt = replace(
        bundle,
        evidence_items=tuple(selected),
        total_context_characters=used_context,
        truncated=truncated,
        bundle_id="",
        bundle_hash="",
    )
    return rebuilt, len(selected), used_context, truncated


def build_composite_evidence_bundle(
    profile: KnowledgeProfile,
    plan: CompositeKnowledgeQueryPlan,
    outcomes: Mapping[str, ModuleExecutionOutcome],
    failures: tuple[KnowledgeModuleFailure, ...],
    policy: KnowledgeHubPolicy,
) -> CompositeKnowledgeEvidenceBundle:
    remaining_items = min(profile.global_max_results, policy.maximum_total_evidence_items)
    remaining_context = min(
        profile.global_max_context_characters,
        policy.maximum_total_context_characters,
    )
    wrappers: list[ModuleInstanceEvidenceBundle] = []
    composite_truncated = False
    for module_plan in plan.module_plans:
        outcome = outcomes.get(module_plan.instance_id)
        if outcome is None:
            continue
        bounded, used_items, used_context, truncated = _bounded_bundle(
            outcome.bundle,
            module_plan,
            remaining_items,
            remaining_context,
        )
        remaining_items -= used_items
        remaining_context -= used_context
        composite_truncated = composite_truncated or truncated
        proofs = tuple(
            KnowledgeEvidenceInstanceProvenance(
                schema_version=ITEM_PROVENANCE_SCHEMA_VERSION,
                evidence_id=item.evidence_id,
                module_id=item.module_id,
                instance_id=outcome.instance.instance_id,
                module_version=item.module_version,
                domain=outcome.descriptor.domain,
                corpus_snapshot_id=item.corpus_snapshot_id,
                source_object_sha256=item.source_object_sha256,
                jurisdiction=item.jurisdiction,
                temporal_status=item.temporal_status,
                source_class=item.source_class,
                warnings=item.warnings,
                evidence_item=item,
            )
            for item in bounded.evidence_items
        )
        wrappers.append(
            ModuleInstanceEvidenceBundle(
                schema_version=MODULE_INSTANCE_BUNDLE_SCHEMA_VERSION,
                module_id=outcome.descriptor.module_id,
                instance_id=outcome.instance.instance_id,
                module_version=outcome.descriptor.module_version,
                deployment_id=outcome.instance.deployment_id,
                domain=outcome.descriptor.domain,
                source_bundle_hash=outcome.bundle.bundle_hash,
                evidence_bundle=bounded,
                evidence_items=proofs,
                truncated=truncated,
            )
        )
    total_items = sum(len(item.evidence_bundle.evidence_items) for item in wrappers)
    total_context = sum(item.evidence_bundle.total_context_characters for item in wrappers)
    if total_items > policy.maximum_total_evidence_items or total_context > policy.maximum_total_context_characters:
        raise KnowledgeModuleError("GLOBAL_BUDGET_EXCEEDED", "composite exceeds reviewed global policy")
    return CompositeKnowledgeEvidenceBundle(
        schema_version=COMPOSITE_BUNDLE_SCHEMA_VERSION,
        composite_bundle_id="",
        profile_id=profile.profile_id,
        profile_hash=profile.profile_hash,
        query_hash=plan.query_hash,
        selected_module_ids=tuple(item.module_id for item in plan.module_plans),
        selected_instance_ids=tuple(item.instance_id for item in plan.module_plans),
        module_bundles=tuple(wrappers),
        module_failures=failures,
        total_evidence_items=total_items,
        total_context_characters=total_context,
        truncated=composite_truncated,
    )


__all__ = (
    "COMPOSITE_BUNDLE_SCHEMA_VERSION",
    "CompositeKnowledgeEvidenceBundle",
    "EXECUTION_RESULT_SCHEMA_VERSION",
    "ITEM_PROVENANCE_SCHEMA_VERSION",
    "KnowledgeEvidenceInstanceProvenance",
    "KnowledgeHubExecutionResult",
    "MODULE_INSTANCE_BUNDLE_SCHEMA_VERSION",
    "ModuleExecutionOutcome",
    "ModuleInstanceEvidenceBundle",
    "NOT_EVALUATED",
    "build_composite_evidence_bundle",
)
