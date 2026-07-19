"""Source-bound evidence and aggregate Knowledge Hub result contracts."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from runtime.knowledge_modules.contracts import (
    AUTHORITY_FLAG_NAMES,
    JsonContract,
    KnowledgeModuleError,
    KnowledgeModuleFailure,
    KnowledgeModuleVerificationResult,
    canonical_hash,
    exact_fields,
)


EVIDENCE_ITEM_SCHEMA_VERSION = "knowledge-evidence-item-1a"
EVIDENCE_BUNDLE_SCHEMA_VERSION = "knowledge-evidence-bundle-1a"
COVERAGE_WARNING_SCHEMA_VERSION = "knowledge-coverage-warning-1a"
HUB_RESULT_SCHEMA_VERSION = "knowledge-hub-result-1a"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _date_or_none(name: str, value: str | None) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", f"{name} is not a date")
    try:
        normalized = date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", f"{name} is not a date") from exc
    if normalized != value:
        raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", f"{name} is not a date")


@dataclass(frozen=True, slots=True)
class KnowledgeCoverageWarning(JsonContract):
    schema_version: str
    code: str
    message: str

    def __post_init__(self) -> None:
        if self.schema_version != COVERAGE_WARNING_SCHEMA_VERSION or any(
            not isinstance(value, str) or not value for value in (self.code, self.message)
        ):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "invalid coverage warning")

    @classmethod
    def create(cls, code: str, message: str) -> "KnowledgeCoverageWarning":
        return cls(COVERAGE_WARNING_SCHEMA_VERSION, code, message)


@dataclass(frozen=True, slots=True)
class KnowledgeEvidenceItem(JsonContract):
    schema_version: str
    evidence_id: str
    module_id: str
    module_version: str
    corpus_snapshot_id: str
    temporal_snapshot_id: str
    retrieval_mode: str
    jurisdiction: str
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
    retrieval_score: float
    warnings: tuple[str, ...]
    source_snapshot_id: str | None
    authority_status: str
    evidence_hash: str = ""
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
        if self.schema_version != EVIDENCE_ITEM_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "evidence schema differs")
        required = (
            self.module_id,
            self.module_version,
            self.corpus_snapshot_id,
            self.temporal_snapshot_id,
            self.jurisdiction,
            self.document_id,
            self.version_id,
            self.document_type,
            self.source_class,
            self.official_title,
            self.bounded_excerpt,
            self.source_url,
            self.licence_status,
        )
        if any(not isinstance(value, str) or not value for value in required):
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "evidence source identity is incomplete"
            )
        if self.retrieval_mode not in ("SOURCE_DISCOVERY", "VERIFIED_AS_OF"):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "invalid evidence retrieval mode")
        if len(self.bounded_excerpt) > 4_000:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "evidence excerpt exceeds limit")
        if not _SHA256.fullmatch(self.source_object_sha256):
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "evidence source SHA-256 is invalid"
            )
        if type(self.excerpt_truncated) is not bool:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "invalid truncation flag")
        try:
            warning_values = tuple(self.warnings)
        except TypeError as exc:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "evidence warnings are invalid"
            ) from exc
        if isinstance(self.warnings, str) or any(
            not isinstance(item, str) or not item for item in warning_values
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "evidence warnings are invalid")
        object.__setattr__(self, "warnings", tuple(sorted(set(warning_values))))
        if self.excerpt_truncated and "EXCERPT_TRUNCATED" not in self.warnings:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "truncated evidence lacks warning"
            )
        expected_temporal = (
            "CURRENTNESS_NOT_VERIFIED"
            if self.retrieval_mode == "SOURCE_DISCOVERY"
            else "VERIFIED_AS_OF"
        )
        if self.temporal_status != expected_temporal:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "evidence temporal status differs from mode"
            )
        if self.retrieval_mode == "SOURCE_DISCOVERY" and "CURRENTNESS_NOT_VERIFIED" not in self.warnings:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "source discovery evidence lacks currentness warning"
            )
        if self.retrieval_mode == "VERIFIED_AS_OF" and not self.effective_from:
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "verified evidence lacks interval start"
            )
        if (
            self.document_type == "ADMINISTRATIVE_RULE"
            or self.source_class == "OFFICIAL_ADMINISTRATIVE_RULE"
        ) and not (
            self.document_type == "ADMINISTRATIVE_RULE"
            and self.source_class == "OFFICIAL_ADMINISTRATIVE_RULE"
        ):
            raise KnowledgeModuleError(
                "MODULE_OUTPUT_MALFORMED", "administrative rule is misclassified"
            )
        for name in ("publication_date", "effective_from", "effective_until"):
            _date_or_none(name, getattr(self, name))
        if type(self.retrieval_score) not in (int, float) or not math.isfinite(
            float(self.retrieval_score)
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "retrieval score is invalid")
        object.__setattr__(self, "retrieval_score", float(self.retrieval_score))
        if self.authority_status != "NON_AUTHORITATIVE_EVIDENCE" or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "evidence cannot carry authority"
            )
        payload = self.to_dict()
        supplied_hash = payload.pop("evidence_hash")
        supplied_id = payload.pop("evidence_id")
        base_hash = canonical_hash(payload)
        expected_id = f"knowledge-evidence-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "evidence ID differs")
        object.__setattr__(self, "evidence_id", expected_id)
        payload["evidence_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "evidence hash differs")
        object.__setattr__(self, "evidence_hash", expected_hash)


@dataclass(frozen=True, slots=True)
class KnowledgeEvidenceBundle(JsonContract):
    schema_version: str
    bundle_id: str
    query_hash: str
    module_id: str
    module_version: str
    descriptor_hash: str
    retrieval_mode: str
    query_as_of_date: str | None
    corpus_snapshot_id: str
    temporal_snapshot_id: str
    evidence_items: tuple[KnowledgeEvidenceItem, ...]
    coverage_warnings: tuple[KnowledgeCoverageWarning, ...]
    retrieval_failures: tuple[KnowledgeModuleFailure, ...]
    total_context_characters: int
    truncated: bool
    authority_status: str
    bundle_hash: str = ""
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
        if self.schema_version != EVIDENCE_BUNDLE_SCHEMA_VERSION:
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "bundle schema differs")
        for name in (
            "query_hash",
            "descriptor_hash",
        ):
            if not _SHA256.fullmatch(getattr(self, name)):
                raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", f"{name} is invalid")
        if self.retrieval_mode not in ("SOURCE_DISCOVERY", "VERIFIED_AS_OF"):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle mode is invalid")
        if self.retrieval_mode == "SOURCE_DISCOVERY" and self.query_as_of_date is not None:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "discovery bundle has a date")
        if self.retrieval_mode == "VERIFIED_AS_OF":
            _date_or_none("query_as_of_date", self.query_as_of_date)
            if self.query_as_of_date is None:
                raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "verified bundle lacks date")
        object.__setattr__(self, "evidence_items", tuple(self.evidence_items))
        object.__setattr__(self, "coverage_warnings", tuple(self.coverage_warnings))
        object.__setattr__(self, "retrieval_failures", tuple(self.retrieval_failures))
        if type(self.total_context_characters) is not int or self.total_context_characters < 0:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "invalid context total")
        if self.total_context_characters != sum(
            len(item.bounded_excerpt) for item in self.evidence_items
        ):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "context total differs")
        if len(self.evidence_items) > 20 or self.total_context_characters > 32_000:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle exceeds AOIA limits")
        if type(self.truncated) is not bool:
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "invalid bundle truncation")
        for item in self.evidence_items:
            if (
                item.module_id != self.module_id
                or item.module_version != self.module_version
                or item.corpus_snapshot_id != self.corpus_snapshot_id
                or item.temporal_snapshot_id != self.temporal_snapshot_id
                or item.retrieval_mode != self.retrieval_mode
            ):
                raise KnowledgeModuleError(
                    "MODULE_OUTPUT_MALFORMED", "bundle provenance is not isolated"
                )
        if self.authority_status != "NON_AUTHORITATIVE_EVIDENCE_BUNDLE" or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "bundle cannot carry authority"
            )
        payload = self.to_dict()
        supplied_hash = payload.pop("bundle_hash")
        supplied_id = payload.pop("bundle_id")
        base_hash = canonical_hash(payload)
        expected_id = f"knowledge-bundle-{base_hash[:32]}"
        if supplied_id not in ("", expected_id):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle ID differs")
        object.__setattr__(self, "bundle_id", expected_id)
        payload["bundle_id"] = expected_id
        expected_hash = canonical_hash(payload)
        if supplied_hash not in ("", expected_hash):
            raise KnowledgeModuleError("MODULE_OUTPUT_MALFORMED", "bundle hash differs")
        object.__setattr__(self, "bundle_hash", expected_hash)


@dataclass(frozen=True, slots=True)
class KnowledgeHubResult(JsonContract):
    schema_version: str
    status: str
    selection_hash: str
    selected_module_ids: tuple[str, ...]
    verification_results: tuple[KnowledgeModuleVerificationResult, ...]
    evidence_bundles: tuple[KnowledgeEvidenceBundle, ...]
    module_failures: tuple[KnowledgeModuleFailure, ...]
    authority_status: str = "NON_AUTHORITATIVE"
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
        if (
            self.schema_version != HUB_RESULT_SCHEMA_VERSION
            or not isinstance(self.status, str)
            or not self.status
        ):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "hub result schema differs")
        if not _SHA256.fullmatch(self.selection_hash):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "selection hash is invalid")
        selected = tuple(sorted(self.selected_module_ids))
        if len(selected) != len(set(selected)):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "hub result repeats modules")
        object.__setattr__(self, "selected_module_ids", selected)
        object.__setattr__(
            self,
            "verification_results",
            tuple(sorted(self.verification_results, key=lambda item: item.module_id)),
        )
        object.__setattr__(
            self,
            "evidence_bundles",
            tuple(sorted(self.evidence_bundles, key=lambda item: item.module_id)),
        )
        object.__setattr__(
            self,
            "module_failures",
            tuple(sorted(self.module_failures, key=lambda item: (item.module_id, item.code))),
        )
        if self.status == "NO_KNOWLEDGE_MODULE_SELECTED" and (
            self.selected_module_ids
            or self.verification_results
            or self.evidence_bundles
            or self.module_failures
        ):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "zero-module result has payload")
        if self.authority_status != "NON_AUTHORITATIVE" or any(
            type(getattr(self, name)) is not bool or getattr(self, name)
            for name in AUTHORITY_FLAG_NAMES
        ):
            raise KnowledgeModuleError(
                "MODULE_AUTHORITY_CLAIM_BLOCKED", "hub result cannot carry authority"
            )
        payload = self.to_dict()
        supplied = payload.pop("result_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("INVALID_MODULE_CONTRACT", "hub result hash differs")
        object.__setattr__(self, "result_hash", expected)


def evidence_item_from_fields(**fields: Any) -> KnowledgeEvidenceItem:
    return KnowledgeEvidenceItem(
        schema_version=EVIDENCE_ITEM_SCHEMA_VERSION,
        evidence_id="",
        evidence_hash="",
        **fields,
    )


def evidence_bundle_from_fields(**fields: Any) -> KnowledgeEvidenceBundle:
    return KnowledgeEvidenceBundle(
        schema_version=EVIDENCE_BUNDLE_SCHEMA_VERSION,
        bundle_id="",
        bundle_hash="",
        **fields,
    )


__all__ = (
    "COVERAGE_WARNING_SCHEMA_VERSION",
    "EVIDENCE_BUNDLE_SCHEMA_VERSION",
    "EVIDENCE_ITEM_SCHEMA_VERSION",
    "HUB_RESULT_SCHEMA_VERSION",
    "KnowledgeCoverageWarning",
    "KnowledgeEvidenceBundle",
    "KnowledgeEvidenceItem",
    "KnowledgeHubResult",
    "evidence_bundle_from_fields",
    "evidence_item_from_fields",
)
