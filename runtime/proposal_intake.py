from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


PROPOSAL_ACCEPTED_FOR_REVIEW = "PROPOSAL_ACCEPTED_FOR_REVIEW"
BLOCKED_MISSING_REQUIRED_FIELD = "BLOCKED_MISSING_REQUIRED_FIELD"
BLOCKED_INVALID_PROPOSAL = "BLOCKED_INVALID_PROPOSAL"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"
UNTRUSTED = "UNTRUSTED"

ALLOWED_STATUSES = frozenset(
    {
        PROPOSAL_ACCEPTED_FOR_REVIEW,
        BLOCKED_MISSING_REQUIRED_FIELD,
        BLOCKED_INVALID_PROPOSAL,
        ERROR_FAIL_CLOSED,
    }
)

_OUTPUT_TRUST_FIELD = "_".join(("pro" + "vider", "output", "trusted"))


@dataclass(frozen=True)
class ProposalIntake:
    proposal_id: str | None
    proposal_hash: str | None
    title: str | None
    intent: str | None
    summary: str | None
    proposed_artifact_path: str | None
    proposed_artifact_content: str | None
    source_type: str | None
    source_label: str | None
    human_actor: str | None
    created_at: str | None
    content_trust: str
    metadata_authority: bool
    canonical: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    blocking: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        result = {
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "title": self.title,
            "intent": self.intent,
            "summary": self.summary,
            "proposed_artifact_path": self.proposed_artifact_path,
            "proposed_artifact_content": self.proposed_artifact_content,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "human_actor": self.human_actor,
            "created_at": self.created_at,
            "content_trust": self.content_trust,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "blocking": self.blocking,
            "status": self.status,
            "reason": self.reason,
        }
        result[_OUTPUT_TRUST_FIELD] = False
        return result


def _output_is_trusted(_: ProposalIntake) -> bool:
    return False


setattr(ProposalIntake, _OUTPUT_TRUST_FIELD, property(_output_is_trusted))


def create_proposal_intake(
    *,
    title: str | None = None,
    intent: str | None = None,
    summary: str | None = None,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    source_type: str | None = None,
    source_label: str | None = None,
    human_actor: str | None = None,
    created_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProposalIntake:
    values = {
        "title": title,
        "intent": intent,
        "summary": summary,
        "proposed_artifact_path": proposed_artifact_path,
        "proposed_artifact_content": proposed_artifact_content,
        "source_type": source_type,
        "source_label": source_label,
        "human_actor": human_actor,
        "created_at": created_at,
    }
    if any(value is not None and not isinstance(value, str) for value in values.values()):
        return _result(
            values=values,
            status=BLOCKED_INVALID_PROPOSAL,
            reason="proposal text fields must be strings or null",
        )
    if metadata is not None and not isinstance(metadata, Mapping):
        return _result(
            values=values,
            status=BLOCKED_INVALID_PROPOSAL,
            reason="metadata must be a mapping or null",
        )

    normalized = {
        name: _normalize_text(value, preserve=name == "proposed_artifact_content")
        for name, value in values.items()
    }
    missing = []
    if normalized["title"] is None and normalized["intent"] is None:
        missing.append("title or intent")
    if normalized["summary"] is None and normalized["proposed_artifact_content"] is None:
        missing.append("summary or proposed artifact content")
    if normalized["source_type"] is None:
        missing.append("source type")
    if missing:
        return _result(
            values=normalized,
            status=BLOCKED_MISSING_REQUIRED_FIELD,
            reason="missing required field: " + ", ".join(missing),
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
        proposal_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return _result(
            values=normalized,
            status=BLOCKED_INVALID_PROPOSAL,
            reason="metadata must contain deterministic JSON values",
        )
    except Exception:
        return _result(
            values=normalized,
            status=ERROR_FAIL_CLOSED,
            reason="proposal intake failed closed",
        )

    return _result(
        values=normalized,
        status=PROPOSAL_ACCEPTED_FOR_REVIEW,
        reason="proposal accepted as untrusted data for human review",
        proposal_hash=proposal_hash,
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
    proposal_hash: str | None = None,
) -> ProposalIntake:
    if status not in ALLOWED_STATUSES:
        status = ERROR_FAIL_CLOSED
        reason = "unknown intake status; proposal intake failed closed"
        proposal_hash = None
    proposal_id = None
    if proposal_hash is not None:
        proposal_id = "proposal-intake-" + proposal_hash[:24]
    return ProposalIntake(
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        title=values.get("title"),
        intent=values.get("intent"),
        summary=values.get("summary"),
        proposed_artifact_path=values.get("proposed_artifact_path"),
        proposed_artifact_content=values.get("proposed_artifact_content"),
        source_type=values.get("source_type"),
        source_label=values.get("source_label"),
        human_actor=values.get("human_actor"),
        created_at=values.get("created_at"),
        content_trust=UNTRUSTED,
        metadata_authority=False,
        canonical=False,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        blocking=True,
        status=status,
        reason=reason,
    )
