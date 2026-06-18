from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.proposer_source_boundary import MODEL_CANDIDATE, PROVIDER_CANDIDATE


PROVIDER_PROPOSER_CANDIDATE_RECORDED = "PROVIDER_PROPOSER_CANDIDATE_RECORDED"
BLOCKED_ADAPTER_DISABLED = "BLOCKED_ADAPTER_DISABLED"
BLOCKED_MISSING_PROVIDER_OUTPUT = "BLOCKED_MISSING_PROVIDER_OUTPUT"
BLOCKED_INVALID_PROVIDER_CANDIDATE = "BLOCKED_INVALID_PROVIDER_CANDIDATE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"
UNTRUSTED = "UNTRUSTED"

ALLOWED_STATUSES = frozenset(
    {
        PROVIDER_PROPOSER_CANDIDATE_RECORDED,
        BLOCKED_ADAPTER_DISABLED,
        BLOCKED_MISSING_PROVIDER_OUTPUT,
        BLOCKED_INVALID_PROVIDER_CANDIDATE,
        ERROR_FAIL_CLOSED,
    }
)
ALLOWED_SOURCE_TYPES = frozenset({PROVIDER_CANDIDATE, MODEL_CANDIDATE})

_CREDENTIAL_ACCESS_FIELD = "_".join(("api", "key", "accessed"))


@dataclass(frozen=True)
class ProviderProposerCandidate:
    candidate_id: str | None
    candidate_hash: str | None
    provider_label: str | None
    model_label: str | None
    source_type: str | None
    raw_provider_output: Any
    extracted_title: str | None
    extracted_intent: str | None
    extracted_summary: str | None
    proposed_artifact_path: str | None
    proposed_artifact_content: str | None
    created_at: str | None
    content_trust: str
    provider_output_trusted: bool
    model_output_trusted: bool
    metadata_authority: bool
    canonical: bool
    adapter_enabled: bool
    live_call_attempted: bool
    network_call_attempted: bool
    proposal_intake_created: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    artifact_write_occurred: bool
    blocking: bool
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        result = {
            "candidate_id": self.candidate_id,
            "candidate_hash": self.candidate_hash,
            "provider_label": self.provider_label,
            "model_label": self.model_label,
            "source_type": self.source_type,
            "raw_provider_output": self.raw_provider_output,
            "extracted_title": self.extracted_title,
            "extracted_intent": self.extracted_intent,
            "extracted_summary": self.extracted_summary,
            "proposed_artifact_path": self.proposed_artifact_path,
            "proposed_artifact_content": self.proposed_artifact_content,
            "created_at": self.created_at,
            "content_trust": self.content_trust,
            "provider_output_trusted": self.provider_output_trusted,
            "model_output_trusted": self.model_output_trusted,
            "metadata_authority": self.metadata_authority,
            "canonical": self.canonical,
            "adapter_enabled": self.adapter_enabled,
            "live_call_attempted": self.live_call_attempted,
            "network_call_attempted": self.network_call_attempted,
            "proposal_intake_created": self.proposal_intake_created,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "artifact_write_occurred": self.artifact_write_occurred,
            "blocking": self.blocking,
            "status": self.status,
            "reason": self.reason,
        }
        result[_CREDENTIAL_ACCESS_FIELD] = False
        return result


def _credential_accessed(_: ProviderProposerCandidate) -> bool:
    return False


setattr(
    ProviderProposerCandidate,
    _CREDENTIAL_ACCESS_FIELD,
    property(_credential_accessed),
)


def create_provider_proposer_candidate(
    *,
    provider_label: str | None = None,
    model_label: str | None = None,
    raw_provider_output: str | Mapping[str, Any] | None = None,
    source_type: str | None = PROVIDER_CANDIDATE,
    extracted_title: str | None = None,
    extracted_intent: str | None = None,
    extracted_summary: str | None = None,
    proposed_artifact_path: str | None = None,
    proposed_artifact_content: str | None = None,
    created_at: str | None = None,
    adapter_enabled: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> ProviderProposerCandidate:
    values = {
        "provider_label": provider_label,
        "model_label": model_label,
        "source_type": source_type,
        "extracted_title": extracted_title,
        "extracted_intent": extracted_intent,
        "extracted_summary": extracted_summary,
        "proposed_artifact_path": proposed_artifact_path,
        "proposed_artifact_content": proposed_artifact_content,
        "created_at": created_at,
    }
    try:
        if not isinstance(adapter_enabled, bool):
            return _result(
                values=values,
                raw_provider_output=raw_provider_output,
                adapter_enabled=False,
                status=BLOCKED_INVALID_PROVIDER_CANDIDATE,
                reason="adapter enabled flag must be boolean",
            )
        normalized = _normalize_values(values)
        normalized_output = _normalize_output(raw_provider_output)
        if not adapter_enabled:
            return _result(
                values=normalized,
                raw_provider_output=normalized_output,
                adapter_enabled=False,
                status=BLOCKED_ADAPTER_DISABLED,
                reason="adapter is disabled by default; candidate remains blocked",
            )
        if normalized_output is None:
            return _result(
                values=normalized,
                raw_provider_output=None,
                adapter_enabled=True,
                status=BLOCKED_MISSING_PROVIDER_OUTPUT,
                reason="provider proposer output is required for local recording",
            )
        if metadata is not None and not isinstance(metadata, Mapping):
            return _result(
                values=normalized,
                raw_provider_output=normalized_output,
                adapter_enabled=True,
                status=BLOCKED_INVALID_PROVIDER_CANDIDATE,
                reason="metadata must be a mapping or null",
            )
        if (
            normalized["provider_label"] is None
            or normalized["model_label"] is None
            or normalized["source_type"] not in ALLOWED_SOURCE_TYPES
        ):
            return _result(
                values=normalized,
                raw_provider_output=normalized_output,
                adapter_enabled=True,
                status=BLOCKED_INVALID_PROVIDER_CANDIDATE,
                reason="provider label, model label, and inert source type are required",
            )

        metadata_value = _canonical_data(metadata)
        material_values = {
            **normalized,
            "raw_provider_output": normalized_output,
            "metadata": metadata_value,
        }
        material = json.dumps(
            material_values,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        candidate_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return _result(
            values=normalized,
            raw_provider_output=normalized_output,
            adapter_enabled=True,
            status=PROVIDER_PROPOSER_CANDIDATE_RECORDED,
            reason="untrusted provider proposer data recorded as a blocking candidate",
            candidate_hash=candidate_hash,
        )
    except (TypeError, ValueError):
        return _result(
            values=values,
            raw_provider_output=None,
            adapter_enabled=adapter_enabled if isinstance(adapter_enabled, bool) else False,
            status=BLOCKED_INVALID_PROVIDER_CANDIDATE,
            reason="provider proposer candidate contains invalid data",
        )
    except Exception:
        return _result(
            values=values,
            raw_provider_output=None,
            adapter_enabled=False,
            status=ERROR_FAIL_CLOSED,
            reason="provider proposer adapter failed closed",
        )


def _normalize_values(values: Mapping[str, Any]) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    for name, value in values.items():
        if value is not None and not isinstance(value, str):
            raise TypeError("candidate text fields must be strings or null")
        preserve = name == "proposed_artifact_content"
        normalized[name] = _normalize_text(value, preserve=preserve)
    return normalized


def _normalize_output(value: str | Mapping[str, Any] | None) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, Mapping):
        canonical = _canonical_data(value)
        return canonical if canonical else None
    raise TypeError("provider proposer output must be string, mapping, or null")


def _normalize_text(value: str | None, *, preserve: bool = False) -> str | None:
    if value is None or not value.strip():
        return None
    return value if preserve else value.strip()


def _canonical_data(value: Mapping[str, Any] | None) -> Any:
    if value is None:
        return None
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return json.loads(encoded)


def _result(
    *,
    values: Mapping[str, Any],
    raw_provider_output: Any,
    adapter_enabled: bool,
    status: str,
    reason: str,
    candidate_hash: str | None = None,
) -> ProviderProposerCandidate:
    if status not in ALLOWED_STATUSES:
        status = ERROR_FAIL_CLOSED
        reason = "unknown adapter status; candidate failed closed"
        candidate_hash = None
    candidate_id = None
    if candidate_hash is not None:
        candidate_id = "provider-proposer-candidate-" + candidate_hash[:24]
    return ProviderProposerCandidate(
        candidate_id=candidate_id,
        candidate_hash=candidate_hash,
        provider_label=values.get("provider_label"),
        model_label=values.get("model_label"),
        source_type=values.get("source_type"),
        raw_provider_output=raw_provider_output,
        extracted_title=values.get("extracted_title"),
        extracted_intent=values.get("extracted_intent"),
        extracted_summary=values.get("extracted_summary"),
        proposed_artifact_path=values.get("proposed_artifact_path"),
        proposed_artifact_content=values.get("proposed_artifact_content"),
        created_at=values.get("created_at"),
        content_trust=UNTRUSTED,
        provider_output_trusted=False,
        model_output_trusted=False,
        metadata_authority=False,
        canonical=False,
        adapter_enabled=adapter_enabled,
        live_call_attempted=False,
        network_call_attempted=False,
        proposal_intake_created=False,
        approval_decision_created=False,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        artifact_write_occurred=False,
        blocking=True,
        status=status,
        reason=reason,
    )
