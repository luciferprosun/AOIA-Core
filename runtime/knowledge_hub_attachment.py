from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Iterable

from runtime.knowledge.tetrad import TetradRecord

if TYPE_CHECKING:
    from runtime.local_visible_flow import LocalVisibleFlowResult


UNTRUSTED_CONTEXT = "UNTRUSTED_CONTEXT"


@dataclass(frozen=True)
class ReadOnlyKnowledgeAttachment:
    attachment_id: str
    title: str
    source_label: str
    content_summary: str
    labels: tuple[str, ...]
    trust_status: str
    read_only: bool
    can_authorize: bool
    can_approve: bool
    can_write: bool
    canonical: bool
    evidence: bool
    tetrad_records: tuple[TetradRecord, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "title": self.title,
            "source_label": self.source_label,
            "content_summary": self.content_summary,
            "labels": list(self.labels),
            "trust_status": self.trust_status,
            "read_only": self.read_only,
            "can_authorize": self.can_authorize,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "canonical": self.canonical,
            "evidence": self.evidence,
            "tetrad_context": _tetrad_context_projection(self.tetrad_records),
        }


def create_read_only_knowledge_attachment(
    *,
    title: str,
    source_label: str,
    content_summary: str,
    labels: Iterable[str] = (),
    tetrad_records: Iterable[TetradRecord] | None = None,
) -> ReadOnlyKnowledgeAttachment:
    normalized_title = _required_text("title", title)
    normalized_source = _required_text("source_label", source_label)
    normalized_summary = _required_text("content_summary", content_summary)
    normalized_labels = _labels(labels)
    normalized_tetrads = _tetrad_records(tetrad_records)
    material = json.dumps(
        {
            "title": normalized_title,
            "source_label": normalized_source,
            "content_summary": normalized_summary,
            "labels": normalized_labels,
            "tetrad_ids": [
                record.tetrad_id for record in normalized_tetrads
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    attachment_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return ReadOnlyKnowledgeAttachment(
        attachment_id="knowledge-attachment-" + attachment_hash[:24],
        title=normalized_title,
        source_label=normalized_source,
        content_summary=normalized_summary,
        labels=normalized_labels,
        trust_status=UNTRUSTED_CONTEXT,
        read_only=True,
        can_authorize=False,
        can_approve=False,
        can_write=False,
        canonical=False,
        evidence=False,
        tetrad_records=normalized_tetrads,
    )


def attach_knowledge_context_to_flow_result(
    *,
    flow_result: LocalVisibleFlowResult,
    attachment: ReadOnlyKnowledgeAttachment,
) -> LocalVisibleFlowResult:
    from runtime.local_visible_flow import LocalVisibleFlowResult

    if not isinstance(flow_result, LocalVisibleFlowResult):
        raise TypeError("flow_result must be a LocalVisibleFlowResult")
    if not is_read_only_knowledge_attachment(attachment):
        raise ValueError("attachment must be immutable read-only untrusted context")
    return replace(flow_result, knowledge_attachment=attachment)


def is_read_only_knowledge_attachment(value: Any) -> bool:
    return (
        isinstance(value, ReadOnlyKnowledgeAttachment)
        and value.trust_status == UNTRUSTED_CONTEXT
        and value.read_only is True
        and value.can_authorize is False
        and value.can_approve is False
        and value.can_write is False
        and value.canonical is False
        and value.evidence is False
        and isinstance(value.tetrad_records, tuple)
        and all(
            isinstance(record, TetradRecord) and record.read_only is True
            for record in value.tetrad_records
        )
    )


def _required_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _labels(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError("labels must be an iterable of text labels")
    normalized = []
    for value in values:
        label = _required_text("label", value)
        if label not in normalized:
            normalized.append(label)
    return tuple(normalized)


def _tetrad_records(
    values: Iterable[TetradRecord] | None,
) -> tuple[TetradRecord, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        raise TypeError("tetrad_records must be an iterable of TetradRecord values")
    records = tuple(values)
    if not all(
        isinstance(record, TetradRecord) and record.read_only is True
        for record in records
    ):
        raise TypeError("tetrad_records must contain only read-only TetradRecord values")
    return records


def _tetrad_context_projection(
    records: tuple[TetradRecord, ...],
) -> dict[str, Any]:
    return {
        "tetrad_records_present": bool(records),
        "tetrad_record_count": len(records),
        "tetrad_ids": [record.tetrad_id for record in records],
        "records": [record.to_dict() for record in records],
        "core_delta": [_tetrad_core_delta_projection(record) for record in records],
        "read_only": True,
        "advisory_only": True,
        "authoritative": False,
        "requires_human_review": True,
        "can_affect_approval": False,
        "can_affect_write": False,
        "can_affect_execution": False,
        "can_affect_gate": False,
    }


def _tetrad_core_delta_projection(record: TetradRecord) -> dict[str, Any]:
    return {
        "tetrad_id": record.tetrad_id,
        "conflicts": list(record.core.conflicts),
        "open_questions": list(record.core.open_questions),
        "read_only": True,
        "authoritative": False,
        "requires_human_review": True,
        "can_affect_approval": False,
        "can_affect_write": False,
        "can_affect_execution": False,
        "can_affect_gate": False,
    }
