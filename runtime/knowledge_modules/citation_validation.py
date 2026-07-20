"""Deterministic structural citation checks; this is not semantic validation."""

from __future__ import annotations

from dataclasses import dataclass

from runtime.knowledge_modules.context import KnowledgeContextPackage
from runtime.knowledge_modules.context_policy import require_no_context_authority
from runtime.knowledge_modules.contracts import JsonContract, KnowledgeModuleError, NON_AUTHORITATIVE, canonical_hash
from runtime.knowledge_modules.structured_answer import StructuredKnowledgeAnswer


CITATION_VALIDATION_SCHEMA_VERSION = "knowledge-citation-validation-1a"

NO_KNOWLEDGE_MODULE_SELECTED = "NO_KNOWLEDGE_MODULE_SELECTED"
KNOWLEDGE_CONTEXT_PREPARED = "KNOWLEDGE_CONTEXT_PREPARED"
PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED = "PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED"
PROVIDER_RESPONSE_MISSING_CITATIONS = "PROVIDER_RESPONSE_MISSING_CITATIONS"
PROVIDER_RESPONSE_INVALID_CITATIONS = "PROVIDER_RESPONSE_INVALID_CITATIONS"
PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE = "PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE"
PROVIDER_OUTPUT_MALFORMED = "PROVIDER_OUTPUT_MALFORMED"
RETRIEVAL_FAILED_CLOSED = "RETRIEVAL_FAILED_CLOSED"
DRY_RUN_ONLY = "DRY_RUN_ONLY"


@dataclass(frozen=True, slots=True)
class KnowledgeCitationValidationResult(JsonContract):
    schema_version: str
    status: str
    valid: bool
    selected_module_ids: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]
    missing_citation_claim_ids: tuple[str, ...]
    invalid_evidence_ids: tuple[str, ...]
    wrong_module_references: tuple[tuple[str, str, str], ...]
    invalid_module_ids: tuple[str, ...]
    authority_status: str = NON_AUTHORITATIVE
    validation_hash: str = ""
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
        allowed = {
            NO_KNOWLEDGE_MODULE_SELECTED,
            KNOWLEDGE_CONTEXT_PREPARED,
            PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
            PROVIDER_RESPONSE_MISSING_CITATIONS,
            PROVIDER_RESPONSE_INVALID_CITATIONS,
            PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE,
            PROVIDER_OUTPUT_MALFORMED,
            RETRIEVAL_FAILED_CLOSED,
            DRY_RUN_ONLY,
        }
        if self.schema_version != CITATION_VALIDATION_SCHEMA_VERSION or self.status not in allowed:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "citation validation schema or status differs")
        if type(self.valid) is not bool:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "citation validity flag differs")
        for name in (
            "selected_module_ids",
            "cited_evidence_ids",
            "missing_citation_claim_ids",
            "invalid_evidence_ids",
            "invalid_module_ids",
        ):
            values = tuple(sorted(getattr(self, name)))
            if any(not isinstance(item, str) or not item for item in values) or len(values) != len(set(values)):
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} differs")
            object.__setattr__(self, name, values)
        wrong = tuple(sorted(self.wrong_module_references))
        if any(
            not isinstance(item, (tuple, list))
            or len(item) != 3
            or any(not isinstance(value, str) or not value for value in item)
            for item in wrong
        ):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "wrong-module references differ")
        object.__setattr__(self, "wrong_module_references", wrong)
        expected_valid = self.status in {
            NO_KNOWLEDGE_MODULE_SELECTED,
            PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED,
        }
        if self.valid != expected_valid:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "citation validity and status differ")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied = payload.pop("validation_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "citation validation hash differs")
        object.__setattr__(self, "validation_hash", expected)


def citation_status_result(
    status: str,
    package: KnowledgeContextPackage,
) -> KnowledgeCitationValidationResult:
    return KnowledgeCitationValidationResult(
        schema_version=CITATION_VALIDATION_SCHEMA_VERSION,
        status=status,
        valid=status == NO_KNOWLEDGE_MODULE_SELECTED,
        selected_module_ids=package.selected_module_ids,
        cited_evidence_ids=(),
        missing_citation_claim_ids=(),
        invalid_evidence_ids=(),
        wrong_module_references=(),
        invalid_module_ids=(),
    )


def validate_knowledge_citations(
    answer: StructuredKnowledgeAnswer,
    package: KnowledgeContextPackage,
) -> KnowledgeCitationValidationResult:
    if not isinstance(answer, StructuredKnowledgeAnswer) or not isinstance(package, KnowledgeContextPackage):
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "citation validation input differs")
    selected = set(package.selected_module_ids)
    evidence = {
        item.evidence_id: item
        for section in package.module_sections
        for item in section.evidence_items
    }
    cited = set(answer.cited_evidence_ids)
    invalid_evidence = {item for item in cited if item not in evidence}
    invalid_modules: set[str] = set()
    wrong_module: set[tuple[str, str, str]] = set()
    missing_claims: set[str] = set()
    claim_evidence_union: set[str] = set()

    for claim in answer.claims:
        claim_modules = set(claim.module_ids)
        invalid_modules.update(claim_modules - selected)
        claim_evidence_union.update(claim.evidence_ids)
        for evidence_id in claim.evidence_ids:
            reference = evidence.get(evidence_id)
            if reference is None:
                invalid_evidence.add(evidence_id)
            elif reference.module_id not in claim_modules:
                wrong_module.add((claim.claim_id, evidence_id, reference.module_id))
        evidence_grounded = claim.claim_kind not in {"LIMITATION", "UNANSWERED"}
        if selected and package.response_policy.require_module_id_per_claim and evidence_grounded and not claim_modules:
            missing_claims.add(claim.claim_id)
        if selected and package.response_policy.require_evidence_references and evidence_grounded and not claim.evidence_ids:
            missing_claims.add(claim.claim_id)
        if (
            package.response_policy.require_temporal_scope_per_claim
            and evidence_grounded
            and claim.temporal_scope == "UNSPECIFIED"
        ):
            missing_claims.add(claim.claim_id)

    invalid_evidence.update(claim_evidence_union - set(evidence))
    if claim_evidence_union != cited:
        missing_claims.update(
            claim.claim_id
            for claim in answer.claims
            if set(claim.evidence_ids) - cited
        )
        invalid_evidence.update(cited - claim_evidence_union)

    if not selected:
        if cited or claim_evidence_union or any(claim.module_ids for claim in answer.claims):
            status = PROVIDER_RESPONSE_INVALID_CITATIONS
        else:
            status = NO_KNOWLEDGE_MODULE_SELECTED
    elif wrong_module or invalid_modules:
        status = PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE
    elif invalid_evidence:
        status = PROVIDER_RESPONSE_INVALID_CITATIONS
    elif missing_claims:
        status = PROVIDER_RESPONSE_MISSING_CITATIONS
    else:
        status = PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED
    return KnowledgeCitationValidationResult(
        schema_version=CITATION_VALIDATION_SCHEMA_VERSION,
        status=status,
        valid=status in {NO_KNOWLEDGE_MODULE_SELECTED, PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED},
        selected_module_ids=package.selected_module_ids,
        cited_evidence_ids=answer.cited_evidence_ids,
        missing_citation_claim_ids=tuple(missing_claims),
        invalid_evidence_ids=tuple(invalid_evidence),
        wrong_module_references=tuple(wrong_module),
        invalid_module_ids=tuple(invalid_modules),
    )


__all__ = (
    "CITATION_VALIDATION_SCHEMA_VERSION",
    "DRY_RUN_ONLY",
    "KNOWLEDGE_CONTEXT_PREPARED",
    "KnowledgeCitationValidationResult",
    "NO_KNOWLEDGE_MODULE_SELECTED",
    "PROVIDER_OUTPUT_MALFORMED",
    "PROVIDER_RESPONSE_INVALID_CITATIONS",
    "PROVIDER_RESPONSE_MISSING_CITATIONS",
    "PROVIDER_RESPONSE_STRUCTURALLY_GROUNDED",
    "PROVIDER_RESPONSE_WRONG_MODULE_REFERENCE",
    "RETRIEVAL_FAILED_CLOSED",
    "citation_status_result",
    "validate_knowledge_citations",
)
