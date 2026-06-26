from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from runtime.artifact_preview import ArtifactPreview, ArtifactPreviewStatus
from runtime.human_decision_gated_artifact_write import (
    BLOCKED_STALE_OR_MISMATCHED_STATE,
    BLOCKED_WRITE_KILL_SWITCH,
    ERROR_FAIL_CLOSED,
    HumanDecisionGatedArtifactWriteResult,
    write_artifact_after_human_gate,
)
from runtime.safety.write_kill_switch import check_write_kill_switch_file
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


CONTROL_WRITE_BLOCKED_INVALID_PREVIEW = "CONTROL_WRITE_BLOCKED_INVALID_PREVIEW"
CONTROL_WRITE_BLOCKED_HASH_MISMATCH = "CONTROL_WRITE_BLOCKED_HASH_MISMATCH"
CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE = "CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE"

GatedArtifactWriter = Callable[..., HumanDecisionGatedArtifactWriteResult]


@dataclass(frozen=True)
class ControlWriteContext:
    run_id: str
    sandbox_request_id: str
    sandbox_result_id: str
    requested_by: str
    dry_run_trace_id: str
    sandbox_policy_decision_id: str
    sandbox_result_state: str = "NOT_IMPLEMENTED"
    notes: str = "Step 10 Control Write 1A preview-bound artifact request"


def write_preview_artifact_after_human_gate(
    *,
    preview: ArtifactPreview,
    proposed_content_text: str,
    workspace_root: str,
    gate_result: Mapping[str, Any] | Any,
    context: ControlWriteContext,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    gated_writer: GatedArtifactWriter = write_artifact_after_human_gate,
    write_kill_switch_path: str | None = None,
    write_kill_switch_directory: str | None = None,
) -> HumanDecisionGatedArtifactWriteResult:
    del metadata
    try:
        if not isinstance(context, ControlWriteContext):
            return _blocked(
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
                "control write requires explicit human gate context",
            )
        if not isinstance(workspace_root, str) or not workspace_root.strip():
            return _blocked(
                CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
                "control write requires a workspace root",
            )
        preview_error = _preview_error(preview)
        if preview_error:
            return _blocked(CONTROL_WRITE_BLOCKED_INVALID_PREVIEW, preview_error)
        if not isinstance(proposed_content_text, str):
            return _blocked(
                CONTROL_WRITE_BLOCKED_INVALID_PREVIEW,
                "proposed content must be text",
            )

        content_hash = _sha256(proposed_content_text)
        if content_hash != preview.proposed_sha256:
            return _blocked(
                CONTROL_WRITE_BLOCKED_HASH_MISMATCH,
                "preview proposed hash does not match proposed content",
            )

        expected_artifact = expected_artifact_hash or preview.proposed_sha256
        if expected_artifact != preview.proposed_sha256:
            return _blocked(
                BLOCKED_STALE_OR_MISMATCHED_STATE,
                "expected artifact hash does not match preview hash",
            )

        gate = _gate_mapping(gate_result)
        gate_error = _gate_evidence_error(gate, expected_packet_hash, expected_artifact)
        if gate_error:
            status, reason = gate_error
            return _blocked(status, reason)

        nested_gate = _gate_mapping(gate.get("gate_result"))
        audit_event_id = _text(nested_gate.get("audit_event_id"))
        approval_decision_id = _text(nested_gate.get("approval_decision_id"))
        if audit_event_id is None or approval_decision_id is None:
            return _blocked(
                CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
                "human gate evidence lacks approval or audit binding",
            )
        if write_kill_switch_path is not None:
            kill_switch = check_write_kill_switch_file(
                write_kill_switch_path,
                allowed_switch_directory=write_kill_switch_directory,
            )
            if not kill_switch.writes_allowed:
                return _blocked(
                    BLOCKED_WRITE_KILL_SWITCH,
                    kill_switch.reason,
                )

        artifact_request = _build_artifact_request(
            preview=preview,
            proposed_content_text=proposed_content_text,
            context=context,
            audit_event_id=audit_event_id,
            approval_decision_id=approval_decision_id,
        )
        return gated_writer(
            gate_result=gate_result,
            artifact_request=artifact_request,
            workspace_root=workspace_root,
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=preview.proposed_sha256,
        )
    except Exception:
        return _blocked(ERROR_FAIL_CLOSED, "control write bridge failed closed")


def _build_artifact_request(
    *,
    preview: ArtifactPreview,
    proposed_content_text: str,
    context: ControlWriteContext,
    audit_event_id: str,
    approval_decision_id: str,
) -> SandboxArtifactRequest:
    return create_sandbox_artifact_request(
        run_id=context.run_id,
        sandbox_request_id=context.sandbox_request_id,
        sandbox_result_id=context.sandbox_result_id,
        artifact_type=_artifact_type(preview),
        relative_output_path=preview.target_path,
        content_text=proposed_content_text,
        requested_by=context.requested_by,
        human_approved=True,
        dry_run_trace_id=context.dry_run_trace_id,
        audit_event_id=audit_event_id,
        notes=context.notes,
        artifact_write_allowed=True,
        approval_decision_id=approval_decision_id,
        sandbox_policy_decision_id=context.sandbox_policy_decision_id,
        sandbox_result_state=context.sandbox_result_state,
        contract_audit_event_id=audit_event_id,
    )


def _preview_error(preview: ArtifactPreview) -> str:
    if not isinstance(preview, ArtifactPreview):
        return "control write requires an ArtifactPreview"
    if preview.status != ArtifactPreviewStatus.PREVIEW_READY:
        return "artifact preview is not ready for human-gated write"
    inert_flags = (
        ("write_performed", preview.write_performed),
        ("can_write", preview.can_write),
        ("can_execute", preview.can_execute),
        ("can_commit", preview.can_commit),
        ("can_change_gate", preview.can_change_gate),
    )
    for field_name, value in inert_flags:
        if value is not False:
            return f"artifact preview inert authority field {field_name} was not false"
    if not _full_hash(preview.proposed_sha256):
        return "artifact preview proposed hash is malformed"
    if not _text(preview.target_path):
        return "artifact preview target path is malformed"
    return ""


def _gate_evidence_error(
    gate: Mapping[str, Any],
    expected_packet_hash: str | None,
    expected_artifact_hash: str,
) -> tuple[str, str] | None:
    packet_hash = _full_hash(gate.get("packet_hash"))
    artifact_hash = _full_hash(gate.get("artifact_hash"))
    expected_packet = _optional_hash(expected_packet_hash)
    expected_artifact = _optional_hash(expected_artifact_hash)
    if packet_hash is None:
        return (
            CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "human gate evidence lacks packet hash binding",
        )
    if artifact_hash is None:
        return (
            CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "human gate evidence lacks artifact hash binding",
        )
    if expected_packet is not None and packet_hash != expected_packet:
        return (
            BLOCKED_STALE_OR_MISMATCHED_STATE,
            "human gate packet hash does not match expected packet hash",
        )
    if artifact_hash != expected_artifact:
        return (
            BLOCKED_STALE_OR_MISMATCHED_STATE,
            "human gate artifact hash does not match preview hash",
        )
    if (
        gate.get("decision") != "APPROVE"
        or gate.get("pre_artifact_gate_passed") is not True
        or gate.get("durable_handoff_complete") is not True
        or gate.get("artifact_write_occurred") is not False
        or gate.get("provider_output_trusted") is not False
        or gate.get("metadata_authority") is not False
    ):
        return (
            CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "human gate evidence is not a valid passed approval gate",
        )
    try:
        nested_gate = _gate_mapping(gate.get("gate_result"))
    except TypeError:
        return (
            CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "human gate evidence lacks nested pre-artifact gate result",
        )
    if (
        nested_gate.get("allowed") is not True
        or nested_gate.get("approval_decision_type") != "APPROVE"
        or _text(nested_gate.get("approval_decision_id")) is None
        or _text(nested_gate.get("audit_event_id")) is None
        or _full_hash(nested_gate.get("audit_event_hash")) is None
    ):
        return (
            CONTROL_WRITE_BLOCKED_MISSING_HUMAN_GATE,
            "human gate evidence lacks approval and audit proof",
        )
    return None


def _artifact_type(preview: ArtifactPreview) -> SandboxArtifactType:
    kind = preview.artifact_kind.strip().casefold()
    if kind == "json" or preview.target_path.casefold().endswith(".json"):
        return SandboxArtifactType.JSON_SUMMARY
    return SandboxArtifactType.TEXT_REPORT


def _gate_mapping(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    raise TypeError("human gate evidence must be a mapping or to_dict object")


def _blocked(status: str, reason: str) -> HumanDecisionGatedArtifactWriteResult:
    return HumanDecisionGatedArtifactWriteResult(
        status=status,
        write_attempted=False,
        artifact_write_occurred=False,
        artifact_path=None,
        decision="BLOCKED",
        blocking=True,
        durable_handoff_complete=False,
        pre_artifact_gate_passed=False,
        provider_output_trusted=False,
        metadata_authority=False,
        packet_hash=None,
        artifact_hash=None,
        reason=reason,
        artifact_result=None,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _full_hash(value)
    if normalized is None:
        raise ValueError("expected hash must be a full SHA-256 value")
    return normalized


def _full_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        return None
    return text


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
