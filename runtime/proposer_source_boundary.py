from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


LOCAL_HUMAN = "LOCAL_HUMAN"
LOCAL_TEST = "LOCAL_TEST"
LOCAL_FILELESS_DRAFT = "LOCAL_FILELESS_DRAFT"
PROVIDER_CANDIDATE = "PROVIDER_CANDIDATE"
MODEL_CANDIDATE = "MODEL_CANDIDATE"
UNKNOWN_UNTRUSTED = "UNKNOWN_UNTRUSTED"

ALLOWED_SOURCE_TYPES = frozenset(
    {
        LOCAL_HUMAN,
        LOCAL_TEST,
        LOCAL_FILELESS_DRAFT,
        PROVIDER_CANDIDATE,
        MODEL_CANDIDATE,
        UNKNOWN_UNTRUSTED,
    }
)

SOURCE_RECORD_ACCEPTED = "SOURCE_RECORD_ACCEPTED"
BLOCKED_MISSING_REQUIRED_FIELD = "BLOCKED_MISSING_REQUIRED_FIELD"
BLOCKED_INVALID_SOURCE_TYPE = "BLOCKED_INVALID_SOURCE_TYPE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"
UNTRUSTED = "UNTRUSTED"

ALLOWED_STATUSES = frozenset(
    {
        SOURCE_RECORD_ACCEPTED,
        BLOCKED_MISSING_REQUIRED_FIELD,
        BLOCKED_INVALID_SOURCE_TYPE,
        ERROR_FAIL_CLOSED,
    }
)


@dataclass(frozen=True)
class ProposerSourceRecord:
    source_record_id: str | None
    source_record_hash: str | None
    source_type: str | None
    source_label: str | None
    raw_proposer_text: str | None
    title: str | None
    intent: str | None
    summary: str | None
    proposed_artifact_path: str | None
    proposed_artifact_content: str | None
    created_at: str | None
    content_trust: str
    source_trust: str
    provider_output_trusted: bool
    metadata_authority: bool
    canonical: bool
    proposal_created: bool
    review_packet_created: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    blocking: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_record_id": self.source_record_id,
            "source_record_hash": self.source_record_hash,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "raw_proposer_text": self.raw_proposer_text,
            "title": self.title,
            "intent": self.intent,
            "summary": self.summary,
            "proposed_artifact_path": self.proposed_artifact_path,
            "proposed_artifact_content": self.proposed_artifact_content,
            "created_at": self.created_at,
            "content_trust": self.content_trust,
            "source_trust": self.source_trust,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "proposal_created": self.proposal_created,
            "review_packet_created": self.review_packet_created,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "blocking": self.blocking,
            "status": self.status,
            "reason": self.reason,
        }


def create_proposer_source_record(
    *,
    source_type: str | None = None,
    source_label: str | None = None,
    raw_proposer_text: str | None = None,
    title: str | None = None,
    intent: str | None = None,
    summary: str | None = None,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    created_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProposerSourceRecord:
    values = {
        "source_type": source_type,
        "source_label": source_label,
        "raw_proposer_text": raw_proposer_text,
        "title": title,
        "intent": intent,
        "summary": summary,
        "proposed_artifact_path": proposed_artifact_path,
        "proposed_artifact_content": proposed_artifact_content,
        "created_at": created_at,
    }
    if any(value is not None and not isinstance(value, str) for value in values.values()):
        return _result(
            values=values,
            status=ERROR_FAIL_CLOSED,
            reason="proposer source text fields must be strings or null",
        )
    if metadata is not None and not isinstance(metadata, Mapping):
        return _result(
            values=values,
            status=ERROR_FAIL_CLOSED,
            reason="metadata must be a mapping or null",
        )

    normalized = {
        name: _normalize_text(
            value,
            preserve=name in {"raw_proposer_text", "proposed_artifact_content"},
        )
        for name, value in values.items()
    }
    missing = []
    if normalized["source_type"] is None:
        missing.append("source type")
    if normalized["source_label"] is None:
        missing.append("source label")
    if not any(
        normalized[name] is not None
        for name in ("raw_proposer_text", "title", "intent", "summary")
    ):
        missing.append("raw proposer text, title, intent, or summary")
    if missing:
        return _result(
            values=normalized,
            status=BLOCKED_MISSING_REQUIRED_FIELD,
            reason="missing required field: " + ", ".join(missing),
        )
    if normalized["source_type"] not in ALLOWED_SOURCE_TYPES:
        return _result(
            values=normalized,
            status=BLOCKED_INVALID_SOURCE_TYPE,
            reason="source type is not an allowed inert proposer source label",
        )

    try:
        metadata_value = _canonical_metadata(metadata)
        material = json.dumps(
            {
                **normalized,
                "metadata": metadata_value,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        source_record_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return _result(
            values=normalized,
            status=ERROR_FAIL_CLOSED,
            reason="metadata must contain deterministic JSON values",
        )
    except Exception:
        return _result(
            values=normalized,
            status=ERROR_FAIL_CLOSED,
            reason="proposer source boundary failed closed",
        )

    return _result(
        values=normalized,
        status=SOURCE_RECORD_ACCEPTED,
        reason="proposer source accepted as inert untrusted data",
        source_record_hash=source_record_hash,
    )


def _normalize_text(value: str | None, *, preserve: bool = False) -> str | None:
    if value is None:
        return None
    if not value.strip():
        return None
    return value if preserve else value.strip()


def _canonical_metadata(metadata: Mapping[str, Any] | None) -> Any:
    if metadata is None:
        return None
    encoded = json.dumps(
        metadata,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return json.loads(encoded)


def _result(
    *,
    values: Mapping[str, Any],
    status: str,
    reason: str,
    source_record_hash: str | None = None,
) -> ProposerSourceRecord:
    if status not in ALLOWED_STATUSES:
        status = ERROR_FAIL_CLOSED
        reason = "unknown source boundary status; record failed closed"
        source_record_hash = None
    source_record_id = None
    if source_record_hash is not None:
        source_record_id = "proposer-source-" + source_record_hash[:24]
    return ProposerSourceRecord(
        source_record_id=source_record_id,
        source_record_hash=source_record_hash,
        source_type=values.get("source_type"),
        source_label=values.get("source_label"),
        raw_proposer_text=values.get("raw_proposer_text"),
        title=values.get("title"),
        intent=values.get("intent"),
        summary=values.get("summary"),
        proposed_artifact_path=values.get("proposed_artifact_path"),
        proposed_artifact_content=values.get("proposed_artifact_content"),
        created_at=values.get("created_at"),
        content_trust=UNTRUSTED,
        source_trust=UNTRUSTED,
        provider_output_trusted=False,
        metadata_authority=False,
        canonical=False,
        proposal_created=False,
        review_packet_created=False,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        blocking=True,
        status=status,
        reason=reason,
    )
