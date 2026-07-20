"""Provider-independent context package construction over composite evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Iterable

from runtime.knowledge_modules.composite import (
    CompositeKnowledgeEvidenceBundle,
    KnowledgeHubExecutionResult,
    ModuleInstanceEvidenceBundle,
)
from runtime.knowledge_modules.contracts import (
    JsonContract,
    KnowledgeModuleDescriptor,
    KnowledgeModuleError,
    KnowledgeModuleFailure,
    NON_AUTHORITATIVE,
    canonical_hash,
)
from runtime.knowledge_modules.evidence import KnowledgeCoverageWarning, KnowledgeEvidenceItem
from runtime.knowledge_modules.instances import KnowledgeModuleInstanceDescriptor
from runtime.knowledge_modules.context_policy import (
    DEFAULT_KNOWLEDGE_CONTEXT_LIMITS,
    DEFAULT_KNOWLEDGE_RESPONSE_POLICY,
    KnowledgeContextLimits,
    KnowledgeResponsePolicy,
    require_no_context_authority,
)


CONTEXT_EVIDENCE_SCHEMA_VERSION = "knowledge-context-evidence-reference-1a"
CONTEXT_FAILURE_SCHEMA_VERSION = "knowledge-context-failure-1a"
CONTEXT_MODULE_SECTION_SCHEMA_VERSION = "knowledge-context-module-section-1a"
CONTEXT_PACKAGE_SCHEMA_VERSION = "knowledge-context-package-1a"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PRIVATE_LOCATION = re.compile(r"(?:^|[\s='\"])(?:/home/|/media/|[A-Za-z]:\\Users\\)")


def _nonempty(name: str, value: object, *, maximum: int = 8_192) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} is invalid")
    return value.strip()


def _strings(name: str, value: Iterable[str], *, sort_values: bool = False) -> tuple[str, ...]:
    if isinstance(value, str):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} must be a sequence")
    result = tuple(value)
    if any(not isinstance(item, str) or not item or len(item) > 8_192 for item in result):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} contains invalid text")
    if len(result) != len(set(result)):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} contains duplicates")
    return tuple(sorted(result)) if sort_values else result


def _reject_machine_location(name: str, value: str) -> None:
    if value.casefold().startswith("file:") or _PRIVATE_LOCATION.search(value):
        raise KnowledgeModuleError(
            "KNOWLEDGE_CONTEXT_INVALID",
            f"{name} exposes a machine-specific location",
        )


@dataclass(frozen=True, slots=True)
class KnowledgeContextFailure(JsonContract):
    schema_version: str
    module_id: str
    instance_id: str
    code: str
    message: str
    details: tuple[tuple[str, str], ...] = ()
    authority_status: str = NON_AUTHORITATIVE
    failure_hash: str = ""
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
        if self.schema_version != CONTEXT_FAILURE_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context failure schema differs")
        for name in ("module_id", "instance_id", "code", "message"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _reject_machine_location("context failure message", self.message)
        details: list[tuple[str, str]] = []
        for item in self.details:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context failure details differ")
            key, value = item
            normalized_value = _nonempty("detail value", value)
            _reject_machine_location("context failure detail", normalized_value)
            details.append((_nonempty("detail name", key, maximum=128), normalized_value))
        object.__setattr__(self, "details", tuple(sorted(details)))
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied = payload.pop("failure_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context failure hash differs")
        object.__setattr__(self, "failure_hash", expected)

    @classmethod
    def from_module_failure(
        cls,
        failure: KnowledgeModuleFailure,
        instance_id: str,
    ) -> "KnowledgeContextFailure":
        return cls(
            schema_version=CONTEXT_FAILURE_SCHEMA_VERSION,
            module_id=failure.module_id,
            instance_id=instance_id,
            code=failure.code,
            message=failure.message,
            details=failure.details,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeContextEvidenceReference(JsonContract):
    schema_version: str
    evidence_id: str
    module_id: str
    module_version: str
    instance_id: str
    corpus_snapshot_id: str
    temporal_snapshot_id: str
    retrieval_mode: str
    jurisdiction_or_domain: str
    document_id: str
    provision_id: str | None
    version_id: str
    document_type: str
    source_class: str
    official_title: str
    official_abbreviation: str | None
    provision_number: str | None
    heading: str | None
    bounded_excerpt: str
    excerpt_truncated: bool
    source_url: str
    source_object_sha256: str
    publication_reference: str | None
    publication_date: str | None
    effective_from: str | None
    effective_until: str | None
    temporal_status: str
    licence_status: str
    warnings: tuple[str, ...]
    evidence_hash: str
    data_classification: str = "UNTRUSTED_EVIDENCE_DATA"
    authority_status: str = "NON_AUTHORITATIVE_EVIDENCE"
    reference_hash: str = ""
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
        if self.schema_version != CONTEXT_EVIDENCE_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context evidence schema differs")
        required = (
            "evidence_id",
            "module_id",
            "module_version",
            "instance_id",
            "corpus_snapshot_id",
            "temporal_snapshot_id",
            "retrieval_mode",
            "jurisdiction_or_domain",
            "document_id",
            "version_id",
            "document_type",
            "source_class",
            "official_title",
            "bounded_excerpt",
            "source_url",
            "temporal_status",
            "licence_status",
        )
        for name in required:
            object.__setattr__(self, name, _nonempty(name, getattr(self, name), maximum=16_000))
        if self.retrieval_mode not in ("SOURCE_DISCOVERY", "VERIFIED_AS_OF"):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context evidence retrieval mode differs")
        if not _SHA256.fullmatch(self.source_object_sha256) or not _SHA256.fullmatch(self.evidence_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context evidence hash is invalid")
        _reject_machine_location("evidence source URL", self.source_url)
        if type(self.excerpt_truncated) is not bool:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context excerpt truncation flag differs")
        object.__setattr__(self, "warnings", _strings("warnings", self.warnings, sort_values=True))
        if self.excerpt_truncated and not any("TRUNCATED" in warning for warning in self.warnings):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "truncated context evidence lacks warning")
        if self.data_classification != "UNTRUSTED_EVIDENCE_DATA":
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_AUTHORITY_CLAIM_BLOCKED", "evidence classification differs")
        require_no_context_authority(self, authority_status="NON_AUTHORITATIVE_EVIDENCE")
        payload = self.to_dict()
        supplied = payload.pop("reference_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context evidence reference hash differs")
        object.__setattr__(self, "reference_hash", expected)

    @classmethod
    def from_evidence(
        cls,
        item: KnowledgeEvidenceItem,
        *,
        instance_id: str,
        domain: str,
        maximum_excerpt_characters: int,
    ) -> "KnowledgeContextEvidenceReference":
        allowed = min(len(item.bounded_excerpt), maximum_excerpt_characters)
        truncated = item.excerpt_truncated or allowed < len(item.bounded_excerpt)
        warnings = set(item.warnings)
        if allowed < len(item.bounded_excerpt):
            warnings.add("CONTEXT_EXCERPT_TRUNCATED")
        return cls(
            schema_version=CONTEXT_EVIDENCE_SCHEMA_VERSION,
            evidence_id=item.evidence_id,
            module_id=item.module_id,
            module_version=item.module_version,
            instance_id=instance_id,
            corpus_snapshot_id=item.corpus_snapshot_id,
            temporal_snapshot_id=item.temporal_snapshot_id,
            retrieval_mode=item.retrieval_mode,
            jurisdiction_or_domain=item.jurisdiction or domain,
            document_id=item.document_id,
            provision_id=item.provision_id,
            version_id=item.version_id,
            document_type=item.document_type,
            source_class=item.source_class,
            official_title=item.official_title,
            official_abbreviation=item.official_abbreviation,
            provision_number=item.provision_number,
            heading=item.heading,
            bounded_excerpt=item.bounded_excerpt[:allowed],
            excerpt_truncated=truncated,
            source_url=item.source_url,
            source_object_sha256=item.source_object_sha256,
            publication_reference=item.publication_reference,
            publication_date=item.publication_date,
            effective_from=item.effective_from,
            effective_until=item.effective_until,
            temporal_status=item.temporal_status,
            licence_status=item.licence_status,
            warnings=tuple(warnings),
            evidence_hash=item.evidence_hash,
        )


def _truncate_reference(
    reference: KnowledgeContextEvidenceReference,
    maximum_characters: int,
) -> KnowledgeContextEvidenceReference:
    allowed = max(1, min(len(reference.bounded_excerpt), maximum_characters))
    if allowed == len(reference.bounded_excerpt):
        return reference
    return replace(
        reference,
        bounded_excerpt=reference.bounded_excerpt[:allowed],
        excerpt_truncated=True,
        warnings=tuple(sorted({*reference.warnings, "CONTEXT_EXCERPT_TRUNCATED"})),
        reference_hash="",
    )


@dataclass(frozen=True, slots=True)
class KnowledgeContextModuleSection(JsonContract):
    schema_version: str
    module_id: str
    module_version: str
    instance_id: str
    descriptor_hash: str
    corpus_snapshot_ids: tuple[str, ...]
    temporal_snapshot_id: str
    retrieval_mode: str
    evidence_items: tuple[KnowledgeContextEvidenceReference, ...]
    retrieval_failures: tuple[KnowledgeContextFailure, ...]
    coverage_warnings: tuple[KnowledgeCoverageWarning, ...]
    known_limitations: tuple[str, ...]
    context_characters: int
    truncated: bool
    authority_status: str = NON_AUTHORITATIVE
    module_section_hash: str = ""
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
        if self.schema_version != CONTEXT_MODULE_SECTION_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section schema differs")
        for name in ("module_id", "module_version", "instance_id", "temporal_snapshot_id", "retrieval_mode"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        if not _SHA256.fullmatch(self.descriptor_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module descriptor hash is invalid")
        object.__setattr__(self, "corpus_snapshot_ids", _strings("corpus_snapshot_ids", self.corpus_snapshot_ids, sort_values=True))
        if not self.corpus_snapshot_ids:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module corpus snapshots are missing")
        evidence = tuple(self.evidence_items)
        if any(
            item.module_id != self.module_id
            or item.module_version != self.module_version
            or item.instance_id != self.instance_id
            or item.retrieval_mode != self.retrieval_mode
            or item.temporal_snapshot_id != self.temporal_snapshot_id
            or item.corpus_snapshot_id not in self.corpus_snapshot_ids
            for item in evidence
        ):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module evidence provenance differs")
        if len(evidence) != len({item.evidence_id for item in evidence}):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section repeats evidence")
        object.__setattr__(self, "evidence_items", evidence)
        failures = tuple(sorted(self.retrieval_failures, key=lambda item: (item.code, item.failure_hash)))
        if any(item.module_id != self.module_id or item.instance_id != self.instance_id for item in failures):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module failure provenance differs")
        object.__setattr__(self, "retrieval_failures", failures)
        warnings = tuple(sorted(self.coverage_warnings, key=lambda item: (item.code, item.message)))
        if any(not isinstance(item, KnowledgeCoverageWarning) for item in warnings):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "coverage warnings differ")
        object.__setattr__(self, "coverage_warnings", warnings)
        limitations = _strings("known_limitations", self.known_limitations, sort_values=True)
        for limitation in limitations:
            _reject_machine_location("known limitation", limitation)
        object.__setattr__(self, "known_limitations", limitations)
        for warning in warnings:
            _reject_machine_location("coverage warning", warning.message)
        expected_context = sum(len(item.bounded_excerpt) for item in evidence)
        if type(self.context_characters) is not int or self.context_characters != expected_context:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module context character count differs")
        if type(self.truncated) is not bool:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section truncation differs")
        if any(item.excerpt_truncated for item in evidence) and not self.truncated:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section omits truncation")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied = payload.pop("module_section_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section hash differs")
        object.__setattr__(self, "module_section_hash", expected)


@dataclass(frozen=True, slots=True)
class KnowledgeContextPackage(JsonContract):
    schema_version: str
    context_package_id: str
    human_question: str
    human_question_hash: str
    knowledge_profile_id: str
    knowledge_profile_hash: str
    composite_bundle_id: str
    composite_bundle_hash: str
    selected_module_ids: tuple[str, ...]
    selected_instance_ids: tuple[str, ...]
    module_sections: tuple[KnowledgeContextModuleSection, ...]
    module_failures: tuple[KnowledgeContextFailure, ...]
    coverage_warnings: tuple[tuple[str, str, str], ...]
    response_policy: KnowledgeResponsePolicy
    total_evidence_items: int
    total_context_characters: int
    truncated: bool
    authority_status: str = NON_AUTHORITATIVE
    context_package_hash: str = ""
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
        if self.schema_version != CONTEXT_PACKAGE_SCHEMA_VERSION:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package schema differs")
        object.__setattr__(self, "human_question", _nonempty("human_question", self.human_question, maximum=4_096))
        for name in ("human_question_hash", "knowledge_profile_hash", "composite_bundle_hash"):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", f"{name} is invalid")
        for name in ("knowledge_profile_id", "composite_bundle_id"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        if self.human_question_hash != canonical_hash({"human_question": self.human_question}):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "human question hash differs")
        module_ids = _strings("selected_module_ids", self.selected_module_ids)
        instance_ids = _strings("selected_instance_ids", self.selected_instance_ids)
        if len(module_ids) != len(instance_ids):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "selected module and instance counts differ")
        object.__setattr__(self, "selected_module_ids", module_ids)
        object.__setattr__(self, "selected_instance_ids", instance_ids)
        sections = tuple(self.module_sections)
        if tuple((item.module_id, item.instance_id) for item in sections) != tuple(zip(module_ids, instance_ids, strict=True)):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "module section ordering differs")
        object.__setattr__(self, "module_sections", sections)
        failures = tuple(sorted(self.module_failures, key=lambda item: (item.module_id, item.code, item.failure_hash)))
        if any(item.module_id not in module_ids for item in failures):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context failure module was not selected")
        object.__setattr__(self, "module_failures", failures)
        warning_rows: list[tuple[str, str, str]] = []
        for item in self.coverage_warnings:
            if not isinstance(item, (tuple, list)) or len(item) != 3:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context coverage warning differs")
            module_id, code, message = item
            if module_id not in module_ids:
                raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "coverage warning module was not selected")
            warning_rows.append((module_id, _nonempty("warning code", code), _nonempty("warning message", message)))
        expected_warning_rows = tuple(
            (section.module_id, warning.code, warning.message)
            for section in sections
            for warning in section.coverage_warnings
        )
        if tuple(warning_rows) != expected_warning_rows:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context warning provenance differs")
        object.__setattr__(self, "coverage_warnings", tuple(warning_rows))
        if not isinstance(self.response_policy, KnowledgeResponsePolicy):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "response policy type differs")
        expected_items = sum(len(item.evidence_items) for item in sections)
        expected_context = sum(item.context_characters for item in sections)
        if self.total_evidence_items != expected_items or self.total_context_characters != expected_context:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package totals differ")
        if type(self.truncated) is not bool or (any(item.truncated for item in sections) and not self.truncated):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package truncation differs")
        evidence_ids = tuple(item.evidence_id for section in sections for item in section.evidence_items)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package repeats evidence IDs")
        require_no_context_authority(self)
        payload = self.to_dict()
        supplied_hash = payload.pop("context_package_hash")
        supplied_id = payload.pop("context_package_id")
        base_hash = canonical_hash(payload)
        expected_id = f"knowledge-context-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package ID differs")
        object.__setattr__(self, "context_package_id", expected_id)
        payload["context_package_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context package hash differs")
        object.__setattr__(self, "context_package_hash", expected_hash)


def _context_failure_rows(
    failures: Iterable[KnowledgeModuleFailure],
    instance_id: str,
) -> tuple[KnowledgeContextFailure, ...]:
    return tuple(KnowledgeContextFailure.from_module_failure(item, instance_id) for item in failures)


def _full_references(
    wrapper: ModuleInstanceEvidenceBundle | None,
    limits: KnowledgeContextLimits,
) -> tuple[KnowledgeContextEvidenceReference, ...]:
    if wrapper is None:
        return ()
    return tuple(
        KnowledgeContextEvidenceReference.from_evidence(
            proof.evidence_item,
            instance_id=wrapper.instance_id,
            domain=proof.domain,
            maximum_excerpt_characters=limits.maximum_excerpt_characters,
        )
        for proof in wrapper.evidence_items
    )


def _fair_context_allocation(
    candidates: tuple[tuple[KnowledgeContextEvidenceReference, ...], ...],
    per_module_maximums: tuple[int, ...],
    limits: KnowledgeContextLimits,
) -> tuple[tuple[KnowledgeContextEvidenceReference, ...], ...]:
    selected: list[list[KnowledgeContextEvidenceReference]] = [[] for _ in candidates]
    remaining_items = limits.maximum_total_evidence_items
    remaining_characters = limits.maximum_total_context_characters

    # Reserve one bounded evidence item for each module that has evidence.
    for index, values in enumerate(candidates):
        if not values or per_module_maximums[index] < 1:
            continue
        if remaining_items < 1 or remaining_characters < 1:
            raise KnowledgeModuleError(
                "KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED",
                "context budget cannot reserve every module with evidence",
            )
        reserve = min(
            len(values[0].bounded_excerpt),
            limits.minimum_context_characters_per_module,
            remaining_characters,
        )
        selected[index].append(_truncate_reference(values[0], reserve))
        remaining_items -= 1
        remaining_characters -= reserve

    # Expand the reserved item, then add more items in explicit module order.
    for index, values in enumerate(candidates):
        if not values or not selected[index]:
            continue
        first = selected[index][0]
        source = values[0]
        expansion = min(
            len(source.bounded_excerpt) - len(first.bounded_excerpt),
            remaining_characters,
        )
        if expansion > 0:
            selected[index][0] = _truncate_reference(
                source,
                len(first.bounded_excerpt) + expansion,
            )
            remaining_characters -= expansion
        for source in values[1 : per_module_maximums[index]]:
            if remaining_items < 1 or remaining_characters < 1:
                break
            allowed = min(len(source.bounded_excerpt), remaining_characters)
            selected[index].append(_truncate_reference(source, allowed))
            remaining_items -= 1
            remaining_characters -= allowed
    return tuple(tuple(items) for items in selected)


def _rebuild_package(
    package: KnowledgeContextPackage,
    sections: tuple[KnowledgeContextModuleSection, ...],
) -> KnowledgeContextPackage:
    coverage_warnings = tuple(
        (section.module_id, warning.code, warning.message)
        for section in sections
        for warning in section.coverage_warnings
    )
    return replace(
        package,
        module_sections=sections,
        coverage_warnings=coverage_warnings,
        total_evidence_items=sum(len(item.evidence_items) for item in sections),
        total_context_characters=sum(item.context_characters for item in sections),
        truncated=True,
        context_package_id="",
        context_package_hash="",
    )


def _fit_absolute_serialization_limit(
    package: KnowledgeContextPackage,
    limits: KnowledgeContextLimits,
) -> KnowledgeContextPackage:
    from runtime.knowledge_modules.context_serializer import serialize_knowledge_context

    result = package
    for _ in range(limits.maximum_total_evidence_items + 2):
        serialized = serialize_knowledge_context(
            result,
            maximum_characters=limits.absolute_context_safety_maximum,
            fail_if_oversized=False,
        )
        if len(serialized) <= limits.absolute_context_safety_maximum:
            return result
        excess = len(serialized) - limits.absolute_context_safety_maximum
        sections = list(result.module_sections)
        changed = False
        for index in range(len(sections) - 1, -1, -1):
            section = sections[index]
            if not section.evidence_items:
                continue
            evidence = list(section.evidence_items)
            final = evidence[-1]
            if len(final.bounded_excerpt) > 1:
                evidence[-1] = _truncate_reference(final, max(1, len(final.bounded_excerpt) - excess - 16))
            else:
                evidence.pop()
            warning = KnowledgeCoverageWarning.create(
                "CONTEXT_TRUNCATED",
                "Provider context was deterministically truncated to the reviewed safety limit.",
            )
            warning_by_identity = {
                (item.code, item.message): item
                for item in (*section.coverage_warnings, warning)
            }
            sections[index] = replace(
                section,
                evidence_items=tuple(evidence),
                coverage_warnings=tuple(warning_by_identity.values()),
                context_characters=sum(len(item.bounded_excerpt) for item in evidence),
                truncated=True,
                module_section_hash="",
            )
            changed = True
            break
        if not changed:
            break
        result = _rebuild_package(result, tuple(sections))
    raise KnowledgeModuleError(
        "KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED",
        "context metadata exceeds the absolute serialized safety limit",
    )


def build_knowledge_context_package(
    execution: KnowledgeHubExecutionResult,
    *,
    human_question: str,
    module_descriptors: tuple[KnowledgeModuleDescriptor, ...],
    instance_descriptors: tuple[KnowledgeModuleInstanceDescriptor, ...],
    response_policy: KnowledgeResponsePolicy = DEFAULT_KNOWLEDGE_RESPONSE_POLICY,
    limits: KnowledgeContextLimits = DEFAULT_KNOWLEDGE_CONTEXT_LIMITS,
) -> KnowledgeContextPackage:
    if not isinstance(execution, KnowledgeHubExecutionResult):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "Hub execution result type differs")
    if not isinstance(response_policy, KnowledgeResponsePolicy) or not isinstance(limits, KnowledgeContextLimits):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context policy types differ")
    if response_policy.maximum_answer_characters > limits.maximum_structured_answer_characters:
        raise KnowledgeModuleError(
            "KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED",
            "response policy exceeds the reviewed structured-answer limit",
        )
    question = _nonempty("human_question", human_question, maximum=limits.maximum_human_question_characters)
    composite = execution.composite_bundle
    if not isinstance(composite, CompositeKnowledgeEvidenceBundle):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "composite bundle type differs")
    if len(composite.selected_module_ids) > limits.maximum_selected_modules:
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "context selects too many modules")
    if any(item.question != question for item in execution.query_plan.module_plans):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context question differs from query plan")
    descriptors = {item.module_id: item for item in module_descriptors}
    instances = {item.instance_id: item for item in instance_descriptors}
    if set(descriptors) != set(composite.selected_module_ids) or set(instances) != set(composite.selected_instance_ids):
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context descriptor selection differs")

    wrappers = {item.instance_id: item for item in composite.module_bundles}
    module_failures_by_id: dict[str, list[KnowledgeModuleFailure]] = {
        module_id: [] for module_id in composite.selected_module_ids
    }
    for failure in composite.module_failures:
        module_failures_by_id[failure.module_id].append(failure)

    candidates: list[tuple[KnowledgeContextEvidenceReference, ...]] = []
    per_module_maximums: list[int] = []
    for module_plan in execution.query_plan.module_plans:
        wrapper = wrappers.get(module_plan.instance_id)
        candidates.append(_full_references(wrapper, limits))
        per_module_maximums.append(
            min(module_plan.max_results, limits.maximum_evidence_items_per_module)
        )
    allocated = _fair_context_allocation(
        tuple(candidates),
        tuple(per_module_maximums),
        limits,
    )

    sections: list[KnowledgeContextModuleSection] = []
    all_failures: list[KnowledgeContextFailure] = []
    all_warnings: list[tuple[str, str, str]] = []
    for index, module_plan in enumerate(execution.query_plan.module_plans):
        descriptor = descriptors[module_plan.module_id]
        instance = instances[module_plan.instance_id]
        if instance.module_id != descriptor.module_id:
            raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_INVALID", "context module and instance differ")
        wrapper = wrappers.get(instance.instance_id)
        local_failures = list(module_failures_by_id[module_plan.module_id])
        if wrapper is not None:
            local_failures.extend(wrapper.evidence_bundle.retrieval_failures)
        failures = _context_failure_rows(local_failures, instance.instance_id)
        all_failures.extend(failures)
        warnings = list(() if wrapper is None else wrapper.evidence_bundle.coverage_warnings)
        context_truncated = (
            wrapper is not None
            and (
                wrapper.truncated
                or len(allocated[index]) != len(candidates[index])
                or any(item.excerpt_truncated for item in allocated[index])
            )
        )
        if context_truncated and not any(item.code == "CONTEXT_TRUNCATED" for item in warnings):
            warnings.append(
                KnowledgeCoverageWarning.create(
                    "CONTEXT_TRUNCATED",
                    "Provider context was deterministically truncated to its reviewed allocation.",
                )
            )
        warnings_tuple = tuple(sorted(warnings, key=lambda item: (item.code, item.message)))
        all_warnings.extend((descriptor.module_id, item.code, item.message) for item in warnings_tuple)
        corpus_snapshot_ids = set(instance.corpus_snapshot_ids)
        if wrapper is not None:
            # An instance pins immutable source snapshots, while a returned
            # bundle may bind its evidence to a distinct derived factory/index
            # snapshot. Preserve both provenance layers.
            corpus_snapshot_ids.add(wrapper.evidence_bundle.corpus_snapshot_id)
        sections.append(
            KnowledgeContextModuleSection(
                schema_version=CONTEXT_MODULE_SECTION_SCHEMA_VERSION,
                module_id=descriptor.module_id,
                module_version=descriptor.module_version,
                instance_id=instance.instance_id,
                descriptor_hash=descriptor.descriptor_hash,
                corpus_snapshot_ids=tuple(sorted(corpus_snapshot_ids)),
                temporal_snapshot_id=instance.temporal_snapshot_id,
                retrieval_mode=module_plan.retrieval_mode,
                evidence_items=allocated[index],
                retrieval_failures=failures,
                coverage_warnings=warnings_tuple,
                known_limitations=descriptor.known_limitations,
                context_characters=sum(len(item.bounded_excerpt) for item in allocated[index]),
                truncated=context_truncated,
            )
        )
    package = KnowledgeContextPackage(
        schema_version=CONTEXT_PACKAGE_SCHEMA_VERSION,
        context_package_id="",
        human_question=question,
        human_question_hash=canonical_hash({"human_question": question}),
        knowledge_profile_id=execution.profile.profile_id,
        knowledge_profile_hash=execution.profile.profile_hash,
        composite_bundle_id=composite.composite_bundle_id,
        composite_bundle_hash=composite.composite_bundle_hash,
        selected_module_ids=composite.selected_module_ids,
        selected_instance_ids=composite.selected_instance_ids,
        module_sections=tuple(sections),
        module_failures=tuple(all_failures),
        coverage_warnings=tuple(all_warnings),
        response_policy=response_policy,
        total_evidence_items=sum(len(item.evidence_items) for item in sections),
        total_context_characters=sum(item.context_characters for item in sections),
        truncated=composite.truncated or any(item.truncated for item in sections),
    )
    if package.total_evidence_items > limits.maximum_total_evidence_items:
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "context evidence count exceeds policy")
    if package.total_context_characters > limits.maximum_total_context_characters:
        raise KnowledgeModuleError("KNOWLEDGE_CONTEXT_LIMIT_EXCEEDED", "context characters exceed policy")
    return _fit_absolute_serialization_limit(package, limits)


__all__ = (
    "CONTEXT_EVIDENCE_SCHEMA_VERSION",
    "CONTEXT_FAILURE_SCHEMA_VERSION",
    "CONTEXT_MODULE_SECTION_SCHEMA_VERSION",
    "CONTEXT_PACKAGE_SCHEMA_VERSION",
    "KnowledgeContextEvidenceReference",
    "KnowledgeContextFailure",
    "KnowledgeContextModuleSection",
    "KnowledgeContextPackage",
    "build_knowledge_context_package",
)
