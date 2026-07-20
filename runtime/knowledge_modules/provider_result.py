"""Non-authoritative result contract for knowledge-bound provider execution."""

from __future__ import annotations

import re
from dataclasses import dataclass

from runtime.knowledge_modules.citation_validation import (
    DRY_RUN_ONLY,
    KNOWLEDGE_CONTEXT_PREPARED,
    NO_KNOWLEDGE_MODULE_SELECTED,
    PROVIDER_OUTPUT_MALFORMED,
    PROVIDER_RESPONSE_INVALID_CITATIONS,
    PROVIDER_RESPONSE_MISSING_CITATIONS,
    PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
    PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE,
    RETRIEVAL_FAILED_CLOSED,
    KnowledgeCitationValidationResult,
)
from runtime.knowledge_modules.context import KnowledgeContextFailure
from runtime.knowledge_modules.context_policy import require_no_context_authority
from runtime.knowledge_modules.contracts import (
    JsonContract,
    KnowledgeModuleError,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.provider_target import ProviderTarget
from runtime.knowledge_modules.structured_answer import (
    NON_AUTHORITATIVE_PROVIDER_OUTPUT,
    StructuredKnowledgeAnswer,
)


PROVIDER_RESULT_SCHEMA_VERSION = "knowledge-provider-result-1a"
PROVIDER_REQUEST_SCHEMA_VERSION = "knowledge-provider-request-1a"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GROUNDING_STATUSES = {
    DRY_RUN_ONLY,
    KNOWLEDGE_CONTEXT_PREPARED,
    NO_KNOWLEDGE_MODULE_SELECTED,
    PROVIDER_OUTPUT_MALFORMED,
    PROVIDER_RESPONSE_INVALID_CITATIONS,
    PROVIDER_RESPONSE_MISSING_CITATIONS,
    PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
    PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE,
    RETRIEVAL_FAILED_CLOSED,
}


@dataclass(frozen=True, slots=True)
class KnowledgeProviderRequest(JsonContract):
    schema_version: str
    human_question: str
    context_package_hash: str
    provider_target: ProviderTarget
    provider_message_payload_preview: str
    request_id: str
    authority_status: str = NON_AUTHORITATIVE
    request_hash: str = ""
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
        if self.schema_version != PROVIDER_REQUEST_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "knowledge provider request schema differs")
        if not isinstance(self.human_question, str) or not self.human_question.strip() or len(self.human_question) > 4_096:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request question differs")
        object.__setattr__(self, "human_question", self.human_question.strip())
        if not _SHA256.fullmatch(self.context_package_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request context hash differs")
        if not isinstance(self.provider_target, ProviderTarget):
            raise KnowledgeModuleError("PROVIDER_TARGET_INVALID", "provider request target type differs")
        if not isinstance(self.provider_message_payload_preview, str) or not self.provider_message_payload_preview:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider payload preview is missing")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied_hash = payload.pop("request_hash")
        supplied_id = payload.pop("request_id")
        base_hash = canonical_hash(payload)
        expected_id = f"knowledge-provider-request-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request ID differs")
        object.__setattr__(self, "request_id", expected_id)
        payload["request_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request hash differs")
        object.__setattr__(self, "request_hash", expected_hash)


@dataclass(frozen=True, slots=True)
class KnowledgeProviderResult(JsonContract):
    schema_version: str
    result_id: str
    request_id: str | None
    request_hash: str | None
    provider_target_hash: str
    provider_id: str
    model_id: str
    knowledge_profile_id: str
    knowledge_profile_hash: str
    selected_module_ids: tuple[str, ...]
    selected_instance_ids: tuple[str, ...]
    composite_bundle_hash: str
    context_package_hash: str
    provider_request_hash: str | None
    provider_status: str
    structured_answer: StructuredKnowledgeAnswer | None
    citation_validation: KnowledgeCitationValidationResult
    warnings: tuple[str, ...]
    module_failures: tuple[KnowledgeContextFailure, ...]
    knowledge_grounding_status: str
    provider_invocation_count: int
    authority_status: str = NON_AUTHORITATIVE_PROVIDER_OUTPUT
    result_hash: str = ""
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
        if self.schema_version != PROVIDER_RESULT_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result schema differs")
        required_text = (
            "provider_id",
            "model_id",
            "knowledge_profile_id",
            "provider_status",
            "knowledge_grounding_status",
        )
        if any(not isinstance(getattr(self, name), str) or not getattr(self, name).strip() for name in required_text):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result identity is incomplete")
        if self.knowledge_grounding_status not in _GROUNDING_STATUSES:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result grounding status differs")
        for name in (
            "provider_target_hash",
            "knowledge_profile_hash",
            "composite_bundle_hash",
            "context_package_hash",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} is invalid")
        if self.request_id is None or self.request_hash is None or self.provider_request_hash is None:
            if not (self.request_id is self.request_hash is self.provider_request_hash is None):
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request result binding differs")
            if self.provider_invocation_count != 0:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider invocation occurred without a request")
        else:
            if not isinstance(self.request_id, str) or not self.request_id:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request ID is invalid")
            if not _SHA256.fullmatch(self.request_hash) or self.provider_request_hash != self.request_hash:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider request hash binding differs")
            if self.provider_invocation_count != 1:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider invocation count differs")
        module_ids = tuple(self.selected_module_ids)
        instance_ids = tuple(self.selected_instance_ids)
        if len(module_ids) != len(set(module_ids)) or len(instance_ids) != len(set(instance_ids)) or len(module_ids) != len(instance_ids):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result selection differs")
        object.__setattr__(self, "selected_module_ids", module_ids)
        object.__setattr__(self, "selected_instance_ids", instance_ids)
        if self.structured_answer is not None and not isinstance(self.structured_answer, StructuredKnowledgeAnswer):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "structured answer type differs")
        if not isinstance(self.citation_validation, KnowledgeCitationValidationResult):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "citation validation type differs")
        warnings = tuple(sorted(self.warnings))
        if any(not isinstance(item, str) or not item for item in warnings) or len(warnings) != len(set(warnings)):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result warnings differ")
        object.__setattr__(self, "warnings", warnings)
        failures = tuple(sorted(self.module_failures, key=lambda item: (item.module_id, item.code, item.failure_hash)))
        if any(item.module_id not in module_ids for item in failures):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result failure module differs")
        object.__setattr__(self, "module_failures", failures)
        if self.authority_status != NON_AUTHORITATIVE_PROVIDER_OUTPUT:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_AUTHORITY_CLAIM_BLOCKED", "provider result claimed authority")
        require_no_context_authority(
            self,
            authority_status=NON_AUTHORITATIVE_PROVIDER_OUTPUT,
            status="KNOWLEDGE_CONTEXT_AUTHORITY_CLAIM_BLOCKED",
        )
        payload = self.to_dict()
        supplied_hash = payload.pop("result_hash")
        supplied_id = payload.pop("result_id")
        base_hash = canonical_hash(payload)
        expected_id = f"knowledge-provider-result-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result ID differs")
        object.__setattr__(self, "result_id", expected_id)
        payload["result_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "provider result hash differs")
        object.__setattr__(self, "result_hash", expected_hash)


__all__ = (
    "KnowledgeProviderRequest",
    "KnowledgeProviderResult",
    "PROVIDER_REQUEST_SCHEMA_VERSION",
    "PROVIDER_RESULT_SCHEMA_VERSION",
)
