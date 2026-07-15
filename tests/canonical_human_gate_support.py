from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from runtime.human_decision_approval_bridge import build_approval_decision_from_capture
from runtime.human_decision_audit_handoff import create_durable_approval_audit_handoff
from runtime.human_decision_capture_helper import capture_human_decision_intent
from runtime.human_decision_gate_integration import (
    HumanDecisionPreArtifactGateResult,
    evaluate_human_decision_pre_artifact_gate,
)
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


def canonical_gate_and_artifact_request(
    *,
    relative_output_path: str,
    content_text: str,
    run_id: str = "step-12c-test-run",
    requested_by: str = "human-reviewer-step-12c",
) -> tuple[HumanDecisionPreArtifactGateResult, SandboxArtifactRequest]:
    artifact_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
    packet_hash = hashlib.sha256(
        ("step-12c-reviewed-packet\n" + relative_output_path + "\n" + content_text).encode("utf-8")
    ).hexdigest()
    capture = capture_human_decision_intent(
        decision="APPROVE",
        packet_id="packet-step-12c",
        displayed_packet_hash=packet_hash,
        current_packet_hash=packet_hash,
        displayed_artifact_hash=artifact_hash,
        current_artifact_hash=artifact_hash,
        human_actor=requested_by,
        reason="reviewed exact Step 12C artifact content",
    )
    bridge = build_approval_decision_from_capture(
        capture=capture,
        expected_packet_hash=packet_hash,
        expected_artifact_hash=artifact_hash,
    )
    with TemporaryDirectory() as audit_dir:
        handoff = create_durable_approval_audit_handoff(
            bridge_result=bridge,
            audit_dir=Path(audit_dir),
            expected_packet_hash=packet_hash,
            expected_artifact_hash=artifact_hash,
        )
    gate = evaluate_human_decision_pre_artifact_gate(
        handoff_result=handoff,
        approval_decision=bridge.approval_decision,
        expected_packet_hash=packet_hash,
        expected_artifact_hash=artifact_hash,
    )
    if (
        type(gate) is not HumanDecisionPreArtifactGateResult
        or gate.gate_result is None
        or gate.gate_result.approval_decision_id is None
        or gate.gate_result.audit_event_id is None
    ):
        raise AssertionError("canonical Step 12C test gate setup failed")
    request = create_sandbox_artifact_request(
        run_id=run_id,
        sandbox_request_id=run_id + "-sandbox-request",
        sandbox_result_id=run_id + "-sandbox-result",
        artifact_type=_artifact_type(relative_output_path),
        relative_output_path=relative_output_path,
        content_text=content_text,
        requested_by=requested_by,
        human_approved=True,
        dry_run_trace_id=run_id + "-trace",
        audit_event_id=gate.gate_result.audit_event_id,
        approval_decision_id=gate.gate_result.approval_decision_id,
        contract_audit_event_id=gate.gate_result.audit_event_id,
        notes="Step 12C canonical human-gate test artifact",
    )
    return gate, request


def _artifact_type(relative_output_path: str) -> SandboxArtifactType:
    suffix = Path(relative_output_path).suffix.casefold()
    if suffix == ".json":
        return SandboxArtifactType.JSON_SUMMARY
    return SandboxArtifactType.TEXT_REPORT
