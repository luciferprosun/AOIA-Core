"""Strict, untrusted structured answer schema for provider output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

from runtime.knowledge_modules.context_policy import KnowledgeResponsePolicy
from runtime.knowledge_modules.contracts import JsonContract, KnowledgeModuleError, canonical_hash, exact_fields


STRUCTURED_ANSWER_SCHEMA_VERSION = "structured-knowledge-answer-1a"
NON_AUTHORITATIVE_PROVIDER_OUTPUT = "NON_AUTHORITATIVE_PROVIDER_OUTPUT"

CLAIM_KINDS = (
    "SOURCE_TEXT_SUMMARY",
    "INTERPRETATION",
    "PROCEDURAL_EXPLANATION",
    "TECHNICAL_EXPLANATION",
    "LIMITATION",
    "UNANSWERED",
)
CONFIDENCE_LABELS = (
    "EVIDENCE_DIRECT",
    "EVIDENCE_PARTIAL",
    "INTERPRETIVE",
    "UNVERIFIABLE",
)
PROVIDER_GROUNDING_LABELS = (
    "NO_KNOWLEDGE_MODULE_SELECTED",
    "EVIDENCE_GROUNDED",
    "PARTIALLY_GROUNDED",
    "UNGROUNDED",
)
_CLAIM_ID = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?\Z")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_SCOPE_PREFIX = re.compile(r"(?:AS_OF|FROM|UNTIL):(\d{4}-\d{2}-\d{2})\Z")
_SCOPE_RANGE = re.compile(r"(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})\Z")


def _required_text(name: str, value: object, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", f"{name} is invalid")
    return value.strip()


def _text_tuple(name: str, value: object, *, maximum_items: int = 256) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (tuple, list)) or len(value) > maximum_items:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", f"{name} must be a bounded list")
    normalized = tuple(_required_text(name, item, maximum=8_192) for item in value)
    if len(normalized) != len(set(normalized)):
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", f"{name} contains duplicates")
    return tuple(sorted(normalized))


def _validate_temporal_scope(value: str) -> str:
    scope = _required_text("temporal_scope", value, maximum=128)
    if scope in {"NOT_APPLICABLE", "UNSPECIFIED", "CURRENTNESS_NOT_VERIFIED"}:
        return scope
    dates: tuple[str, ...]
    if _ISO.fullmatch(scope):
        dates = (scope,)
    elif match := _SCOPE_PREFIX.fullmatch(scope):
        dates = (match.group(1),)
    elif match := _SCOPE_RANGE.fullmatch(scope):
        dates = (match.group(1), match.group(2))
    else:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "temporal_scope is malformed")
    try:
        parsed = tuple(date.fromisoformat(item).isoformat() for item in dates)
    except ValueError as exc:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "temporal_scope date is invalid") from exc
    if parsed != dates or len(parsed) == 2 and parsed[1] < parsed[0]:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "temporal_scope range is invalid")
    return scope


@dataclass(frozen=True, slots=True)
class StructuredKnowledgeClaim(JsonContract):
    claim_id: str
    claim_text: str
    module_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    jurisdiction_or_domain: str
    temporal_scope: str
    claim_kind: str
    confidence_label: str
    claim_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.claim_id, str) or not _CLAIM_ID.fullmatch(self.claim_id):
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "claim_id is invalid")
        object.__setattr__(self, "claim_text", _required_text("claim_text", self.claim_text, maximum=8_192))
        object.__setattr__(self, "module_ids", _text_tuple("module_ids", self.module_ids, maximum_items=16))
        object.__setattr__(self, "evidence_ids", _text_tuple("evidence_ids", self.evidence_ids, maximum_items=40))
        object.__setattr__(
            self,
            "jurisdiction_or_domain",
            _required_text("jurisdiction_or_domain", self.jurisdiction_or_domain, maximum=512),
        )
        object.__setattr__(self, "temporal_scope", _validate_temporal_scope(self.temporal_scope))
        if self.claim_kind not in CLAIM_KINDS:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "claim kind is unsupported")
        if self.confidence_label not in CONFIDENCE_LABELS:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "confidence label is unsupported")
        payload = self.to_dict()
        supplied = payload.pop("claim_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "claim hash differs")
        object.__setattr__(self, "claim_hash", expected)

    @classmethod
    def from_provider_dict(cls, value: Mapping[str, Any]) -> "StructuredKnowledgeClaim":
        expected = {
            "claim_id",
            "claim_text",
            "module_ids",
            "evidence_ids",
            "jurisdiction_or_domain",
            "temporal_scope",
            "claim_kind",
            "confidence_label",
        }
        exact_fields(value, expected, status="PROVIDER_OUTPUT_MALFORMED", label="structured claim")
        try:
            return cls(**dict(value))
        except TypeError as exc:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "structured claim fields differ") from exc


@dataclass(frozen=True, slots=True)
class StructuredKnowledgeAnswer(JsonContract):
    schema_version: str
    answer_markdown: str
    claims: tuple[StructuredKnowledgeClaim, ...]
    cited_evidence_ids: tuple[str, ...]
    unanswered_questions: tuple[str, ...]
    warnings: tuple[str, ...]
    knowledge_grounding_status: str
    authority_status: str
    answer_hash: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != STRUCTURED_ANSWER_SCHEMA_VERSION:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "structured answer schema differs")
        if not isinstance(self.answer_markdown, str) or len(self.answer_markdown) > 32_000:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "answer_markdown is invalid")
        claims = tuple(sorted(self.claims, key=lambda item: item.claim_id))
        if any(not isinstance(item, StructuredKnowledgeClaim) for item in claims):
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "claims differ")
        if len(claims) != len({item.claim_id for item in claims}):
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "claim IDs contain duplicates")
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "cited_evidence_ids", _text_tuple("cited_evidence_ids", self.cited_evidence_ids, maximum_items=40))
        object.__setattr__(self, "unanswered_questions", _text_tuple("unanswered_questions", self.unanswered_questions))
        object.__setattr__(self, "warnings", _text_tuple("warnings", self.warnings))
        if self.knowledge_grounding_status not in PROVIDER_GROUNDING_LABELS:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider grounding label differs")
        if self.authority_status != NON_AUTHORITATIVE_PROVIDER_OUTPUT:
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output claimed authority")
        payload = self.to_dict()
        supplied = payload.pop("answer_hash")
        expected = canonical_hash(payload)
        if supplied not in ("", expected):
            raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "structured answer hash differs")
        object.__setattr__(self, "answer_hash", expected)


def parse_structured_knowledge_answer(
    raw: str,
    policy: KnowledgeResponsePolicy,
) -> StructuredKnowledgeAnswer:
    if not isinstance(raw, str) or not raw.strip():
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output is empty")
    if len(raw) > policy.maximum_answer_characters:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output exceeds answer limit")
    def object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output repeats a JSON field")
            result[key] = value
        return result

    def reject_non_json_constant(_value: str) -> None:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output contains a non-JSON number")

    decoder = json.JSONDecoder(
        object_pairs_hook=object_without_duplicates,
        parse_constant=reject_non_json_constant,
    )
    try:
        value, end = decoder.raw_decode(raw.lstrip())
    except json.JSONDecodeError as exc:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output is not strict JSON") from exc
    if raw.lstrip()[end:].strip() or not isinstance(value, Mapping):
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider output contains prose outside one JSON object")
    expected = {
        "schema_version",
        "answer_markdown",
        "claims",
        "cited_evidence_ids",
        "unanswered_questions",
        "warnings",
        "knowledge_grounding_status",
        "authority_status",
    }
    exact_fields(value, expected, status="PROVIDER_OUTPUT_MALFORMED", label="structured answer")
    claims_value = value["claims"]
    if not isinstance(claims_value, list) or len(claims_value) > policy.maximum_claims:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "provider claims exceed policy")
    claims = tuple(StructuredKnowledgeClaim.from_provider_dict(item) for item in claims_value)
    if not isinstance(value["answer_markdown"], str) or len(value["answer_markdown"]) > policy.maximum_answer_characters:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "answer text exceeds policy")
    try:
        return StructuredKnowledgeAnswer(
            schema_version=value["schema_version"],
            answer_markdown=value["answer_markdown"],
            claims=claims,
            cited_evidence_ids=value["cited_evidence_ids"],
            unanswered_questions=value["unanswered_questions"],
            warnings=value["warnings"],
            knowledge_grounding_status=value["knowledge_grounding_status"],
            authority_status=value["authority_status"],
        )
    except TypeError as exc:
        raise KnowledgeModuleError("PROVIDER_OUTPUT_MALFORMED", "structured answer fields differ") from exc


StructuredKnowledgeAnswer1A = StructuredKnowledgeAnswer


__all__ = (
    "CLAIM_KINDS",
    "CONFIDENCE_LABELS",
    "NON_AUTHORITATIVE_PROVIDER_OUTPUT",
    "PROVIDER_GROUNDING_LABELS",
    "STRUCTURED_ANSWER_SCHEMA_VERSION",
    "StructuredKnowledgeAnswer",
    "StructuredKnowledgeAnswer1A",
    "StructuredKnowledgeClaim",
    "parse_structured_knowledge_answer",
)
