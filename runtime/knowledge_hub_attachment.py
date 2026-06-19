from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Iterable

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
        }


def create_read_only_knowledge_attachment(
    *,
    title: str,
    source_label: str,
    content_summary: str,
    labels: Iterable[str] = (),
) -> ReadOnlyKnowledgeAttachment:
    normalized_title = _required_text("title", title)
    normalized_source = _required_text("source_label", source_label)
    normalized_summary = _required_text("content_summary", content_summary)
    normalized_labels = _labels(labels)
    material = json.dumps(
        {
            "title": normalized_title,
            "source_label": normalized_source,
            "content_summary": normalized_summary,
            "labels": normalized_labels,
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
