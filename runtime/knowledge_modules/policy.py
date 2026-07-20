"""Reviewed, provider-independent Knowledge Hub resource policy."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)


POLICY_SCHEMA_VERSION = "knowledge-hub-policy-1b"


@dataclass(frozen=True, slots=True)
class KnowledgeHubPolicy(JsonContract):
    schema_version: str = POLICY_SCHEMA_VERSION
    default_max_selected_modules: int = 8
    absolute_max_selected_modules: int = 16
    maximum_total_evidence_items: int = 160
    maximum_total_context_characters: int = 256_000
    maximum_excerpt_characters: int = 4_000
    maximum_per_module_results: int = 20
    maximum_per_module_context_characters: int = 32_000
    minimum_results_per_module: int = 1
    minimum_context_characters_per_module: int = 1_024
    authority_status: str = NON_AUTHORITATIVE
    policy_hash: str = ""
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
        if self.schema_version != POLICY_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "policy schema differs")
        integer_fields = (
            "default_max_selected_modules",
            "absolute_max_selected_modules",
            "maximum_total_evidence_items",
            "maximum_total_context_characters",
            "maximum_excerpt_characters",
            "maximum_per_module_results",
            "maximum_per_module_context_characters",
            "minimum_results_per_module",
            "minimum_context_characters_per_module",
        )
        if any(type(getattr(self, name)) is not int or getattr(self, name) < 1 for name in integer_fields):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "policy limits must be positive integers")
        if not (
            self.default_max_selected_modules
            <= self.absolute_max_selected_modules
            <= 16
        ):
            raise KnowledgeModuleError(
                "PROFILE_LIMIT_EXCEEDED", "module-selection policy exceeds absolute safety limit"
            )
        if not 256 <= self.maximum_excerpt_characters <= 4_000:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "excerpt policy is outside bounds")
        if not 1 <= self.maximum_per_module_results <= 20:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "per-module result policy differs")
        if not 1_024 <= self.maximum_per_module_context_characters <= 32_000:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "per-module context policy differs")
        if self.minimum_results_per_module > self.maximum_per_module_results:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "result reserve exceeds module maximum")
        if self.minimum_context_characters_per_module > self.maximum_per_module_context_characters:
            raise KnowledgeModuleError("PROFILE_LIMIT_EXCEEDED", "context reserve exceeds module maximum")
        if self.authority_status != NON_AUTHORITATIVE or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "policy cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("policy_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "policy hash differs")
        object.__setattr__(self, "policy_hash", expected)


DEFAULT_KNOWLEDGE_HUB_POLICY = KnowledgeHubPolicy()


__all__ = (
    "DEFAULT_KNOWLEDGE_HUB_POLICY",
    "KnowledgeHubPolicy",
    "POLICY_SCHEMA_VERSION",
)
