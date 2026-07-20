"""Reviewed provider-neutral limits and response requirements for knowledge context."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)


CONTEXT_LIMITS_SCHEMA_VERSION = "knowledge-context-limits-1a"
RESPONSE_POLICY_SCHEMA_VERSION = "knowledge-response-policy-1a"
CONTEXT_CAPABILITY_FLAG_NAMES = (*AUTHORITY_FLAG_NAMES, "can_call_tools")


def require_no_context_authority(
    value: object,
    *,
    authority_status: str = NON_AUTHORITATIVE,
    status: str = "KNOWLEDGE_CONTEXT_AUTHORITY_CLAIM_BLOCKED",
) -> None:
    if getattr(value, "authority_status", None) != authority_status or any(
        type(getattr(value, name, None)) is not bool or getattr(value, name)
        for name in CONTEXT_CAPABILITY_FLAG_NAMES
    ):
        raise KnowledgeModuleError(status, "knowledge context cannot carry authority")


@dataclass(frozen=True, slots=True)
class KnowledgeContextLimits(JsonContract):
    schema_version: str = CONTEXT_LIMITS_SCHEMA_VERSION
    maximum_selected_modules: int = 8
    absolute_maximum_selected_modules: int = 16
    maximum_total_evidence_items: int = 40
    maximum_evidence_items_per_module: int = 20
    maximum_excerpt_characters: int = 4_000
    maximum_total_context_characters: int = 48_000
    absolute_context_safety_maximum: int = 64_000
    maximum_human_question_characters: int = 4_096
    minimum_context_characters_per_module: int = 1_024
    maximum_structured_answer_characters: int = 32_000
    authority_status: str = NON_AUTHORITATIVE
    limits_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_call_tools: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != CONTEXT_LIMITS_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context limits schema differs")
        integer_fields = (
            "maximum_selected_modules",
            "absolute_maximum_selected_modules",
            "maximum_total_evidence_items",
            "maximum_evidence_items_per_module",
            "maximum_excerpt_characters",
            "maximum_total_context_characters",
            "absolute_context_safety_maximum",
            "maximum_human_question_characters",
            "minimum_context_characters_per_module",
            "maximum_structured_answer_characters",
        )
        if any(type(getattr(self, name)) is not int or getattr(self, name) < 1 for name in integer_fields):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "context limits must be positive integers")
        if not self.maximum_selected_modules <= self.absolute_maximum_selected_modules <= 16:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "selected-module limit exceeds safety maximum")
        if not 1 <= self.maximum_total_evidence_items <= 160:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "evidence-item limit differs")
        if not 1 <= self.maximum_evidence_items_per_module <= 20:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "per-module evidence limit differs")
        if not 256 <= self.maximum_excerpt_characters <= 4_000:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "excerpt limit differs")
        if not 1_024 <= self.maximum_total_context_characters <= self.absolute_context_safety_maximum:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "context character limit differs")
        if not self.maximum_total_context_characters <= self.absolute_context_safety_maximum <= 64_000:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "absolute context limit differs")
        if not 1 <= self.maximum_human_question_characters <= 4_096:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "question limit differs")
        if not 1 <= self.minimum_context_characters_per_module <= self.maximum_excerpt_characters:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "module context reserve differs")
        if not 1_024 <= self.maximum_structured_answer_characters <= 32_000:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "answer limit differs")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied = payload.pop("limits_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context limits hash differs")
        object.__setattr__(self, "limits_hash", expected)


@dataclass(frozen=True, slots=True)
class KnowledgeResponsePolicy(JsonContract):
    schema_version: str = RESPONSE_POLICY_SCHEMA_VERSION
    require_evidence_references: bool = True
    require_module_id_per_claim: bool = True
    require_temporal_scope_per_claim: bool = True
    expose_coverage_warnings: bool = True
    expose_module_failures: bool = True
    distinguish_source_from_interpretation: bool = True
    prohibit_binding_advice: bool = True
    prohibit_unverified_currentness_claims: bool = True
    prohibit_invented_sources: bool = True
    prohibit_invented_dates: bool = True
    prohibit_invented_identifiers: bool = True
    ignore_instructions_inside_evidence: bool = True
    maximum_claims: int = 64
    maximum_answer_characters: int = 32_000
    authority_status: str = NON_AUTHORITATIVE
    policy_hash: str = ""
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_call_tools: bool = False
    can_change_gate: bool = False
    can_satisfy_human_barrier: bool = False
    can_provide_binding_legal_advice: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != RESPONSE_POLICY_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "response policy schema differs")
        requirement_fields = (
            "require_evidence_references",
            "require_module_id_per_claim",
            "require_temporal_scope_per_claim",
            "expose_coverage_warnings",
            "expose_module_failures",
            "distinguish_source_from_interpretation",
            "prohibit_binding_advice",
            "prohibit_unverified_currentness_claims",
            "prohibit_invented_sources",
            "prohibit_invented_dates",
            "prohibit_invented_identifiers",
            "ignore_instructions_inside_evidence",
        )
        if any(type(getattr(self, name)) is not bool for name in requirement_fields):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "response policy flags must be boolean")
        if type(self.maximum_claims) is not int or not 1 <= self.maximum_claims <= 256:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "maximum claims differs")
        if type(self.maximum_answer_characters) is not int or not 1_024 <= self.maximum_answer_characters <= 32_000:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "maximum answer length differs")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied = payload.pop("policy_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "response policy hash differs")
        object.__setattr__(self, "policy_hash", expected)


DEFAULT_KNOWLEDGE_CONTEXT_LIMITS = KnowledgeContextLimits()
DEFAULT_KNOWLEDGE_RESPONSE_POLICY = KnowledgeResponsePolicy()


__all__ = (
    "CONTEXT_CAPABILITY_FLAG_NAMES",
    "CONTEXT_LIMITS_SCHEMA_VERSION",
    "DEFAULT_KNOWLEDGE_CONTEXT_LIMITS",
    "DEFAULT_KNOWLEDGE_RESPONSE_POLICY",
    "KnowledgeContextLimits",
    "KnowledgeResponsePolicy",
    "RESPONSE_POLICY_SCHEMA_VERSION",
    "require_no_context_authority",
)
