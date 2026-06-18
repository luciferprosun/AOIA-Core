from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from runtime.human_decision_approval_bridge import (
    CaptureApprovalBridgeResult,
    build_approval_decision_from_capture,
)
from runtime.human_decision_audit_handoff import (
    DurableApprovalAuditHandoff,
    create_durable_approval_audit_handoff,
)
from runtime.human_decision_capture_helper import (
    HumanDecisionCaptureIntent,
    capture_human_decision_intent,
)
from runtime.human_decision_gate_integration import (
    HumanDecisionPreArtifactGateResult,
    evaluate_human_decision_pre_artifact_gate,
)
from runtime.human_decision_gated_artifact_write import (
    HumanDecisionGatedArtifactWriteResult,
    write_artifact_after_human_gate,
)
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactType,
    create_sandbox_artifact_request,
)


DEMO_COMPLETED = "DEMO_COMPLETED"
BLOCKED_CAPTURE = "BLOCKED_CAPTURE"
BLOCKED_APPROVAL_DECISION = "BLOCKED_APPROVAL_DECISION"
BLOCKED_DURABLE_HANDOFF = "BLOCKED_DURABLE_HANDOFF"
BLOCKED_PRE_ARTIFACT_GATE = "BLOCKED_PRE_ARTIFACT_GATE"
BLOCKED_ARTIFACT_WRITE = "BLOCKED_ARTIFACT_WRITE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

CaptureFunction = Callable[..., HumanDecisionCaptureIntent]
BridgeFunction = Callable[..., CaptureApprovalBridgeResult]
HandoffFunction = Callable[..., DurableApprovalAuditHandoff]
GateFunction = Callable[..., HumanDecisionPreArtifactGateResult]
WriteFunction = Callable[..., HumanDecisionGatedArtifactWriteResult]


@dataclass(frozen=True)
class LocalApprovalArtifactDemoResult:
    status: str
    demo_completed: bool
    decision: str
    capture_created: bool
    approval_decision_created: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    write_attempted: bool
    artifact_write_occurred: bool
    artifact_path: str | None
    packet_hash: str | None
    artifact_hash: str | None
    provider_output_trusted: bool
    metadata_authority: bool
    blocking: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "demo_completed": self.demo_completed,
            "decision": self.decision,
            "capture_created": self.capture_created,
            "approval_decision_created": self.approval_decision_created,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "write_attempted": self.write_attempted,
            "artifact_write_occurred": self.artifact_write_occurred,
            "artifact_path": self.artifact_path,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "blocking": self.blocking,
            "reason": self.reason,
        }


def run_local_approval_to_artifact_demo(
    *,
    workspace_root: str | Path,
    audit_dir: str | Path,
    decision: str,
    packet_hash: str | None,
    artifact_relative_path: str,
    artifact_content: str,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    current_packet_hash: str | None = None,
    current_artifact_hash: str | None = None,
    human_actor: str = "local-human-reviewer",
    reason: str = "explicit local approval-to-artifact demo decision",
    metadata: Mapping[str, Any] | None = None,
    capture_function: CaptureFunction = capture_human_decision_intent,
    bridge_function: BridgeFunction = build_approval_decision_from_capture,
    handoff_function: HandoffFunction = create_durable_approval_audit_handoff,
    gate_function: GateFunction = evaluate_human_decision_pre_artifact_gate,
    write_function: WriteFunction = write_artifact_after_human_gate,
) -> LocalApprovalArtifactDemoResult:
    try:
        workspace = _absolute_existing_directory("workspace_root", workspace_root)
        audit = _absolute_directory("audit_dir", audit_dir)
        content = _text("artifact_content", artifact_content)
        artifact_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        displayed_packet_hash = packet_hash
        current_packet = (
            current_packet_hash
            if current_packet_hash is not None
            else packet_hash
        )
        current_artifact = (
            current_artifact_hash
            if current_artifact_hash is not None
            else artifact_hash
        )
        packet_id = _packet_id(packet_hash, artifact_hash, artifact_relative_path)

        capture = capture_function(
            decision=decision,
            packet_id=packet_id,
            displayed_packet_hash=displayed_packet_hash,
            current_packet_hash=current_packet,
            displayed_artifact_hash=artifact_hash,
            current_artifact_hash=current_artifact,
            human_actor=human_actor,
            reason=reason,
            metadata=metadata,
        )
        if not isinstance(capture, HumanDecisionCaptureIntent) or not capture.decision_captured:
            return _blocked(
                status=BLOCKED_CAPTURE,
                decision=_result_decision(capture),
                packet_hash=_result_hash(capture, "packet_hash"),
                artifact_hash=_result_hash(capture, "artifact_hash"),
                reason=_result_reason(capture, "human decision capture failed closed"),
            )

        bridge = bridge_function(
            capture=capture,
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            review_packet_id=packet_id,
            metadata=metadata,
        )
        if (
            not isinstance(bridge, CaptureApprovalBridgeResult)
            or not bridge.approval_decision_created
            or bridge.approval_decision is None
        ):
            return _blocked(
                status=BLOCKED_APPROVAL_DECISION,
                decision=_result_decision(bridge),
                capture_created=True,
                packet_hash=_result_hash(bridge, "packet_hash"),
                artifact_hash=_result_hash(bridge, "artifact_hash"),
                reason=_result_reason(bridge, "approval decision bridge failed closed"),
            )

        handoff = handoff_function(
            bridge_result=bridge,
            audit_dir=audit,
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            metadata=metadata,
        )
        if (
            not isinstance(handoff, DurableApprovalAuditHandoff)
            or not handoff.durable_handoff_complete
        ):
            return _blocked(
                status=BLOCKED_DURABLE_HANDOFF,
                decision=_result_decision(handoff),
                capture_created=True,
                approval_decision_created=True,
                packet_hash=_result_hash(handoff, "packet_hash"),
                artifact_hash=_result_hash(handoff, "artifact_hash"),
                reason=_result_reason(handoff, "durable approval handoff failed closed"),
            )

        gate = gate_function(
            handoff_result=handoff,
            approval_decision=bridge.approval_decision,
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            metadata=metadata,
        )
        if not isinstance(gate, HumanDecisionPreArtifactGateResult):
            return _blocked(
                status=BLOCKED_PRE_ARTIFACT_GATE,
                decision="BLOCKED",
                capture_created=True,
                approval_decision_created=True,
                durable_handoff_complete=True,
                packet_hash=handoff.packet_hash,
                artifact_hash=handoff.artifact_hash,
                reason="pre-artifact gate returned a malformed result",
            )
        if not gate.pre_artifact_gate_passed:
            return _blocked(
                status=BLOCKED_PRE_ARTIFACT_GATE,
                decision=gate.decision,
                capture_created=True,
                approval_decision_created=True,
                durable_handoff_complete=True,
                packet_hash=gate.packet_hash,
                artifact_hash=gate.artifact_hash,
                reason=gate.reason,
            )

        nested_gate = gate.gate_result
        if (
            nested_gate is None
            or not nested_gate.approval_decision_id
            or not nested_gate.audit_event_id
        ):
            return _blocked(
                status=BLOCKED_PRE_ARTIFACT_GATE,
                decision="BLOCKED",
                capture_created=True,
                approval_decision_created=True,
                durable_handoff_complete=True,
                packet_hash=gate.packet_hash,
                artifact_hash=gate.artifact_hash,
                reason="passed gate lacks decision or durable audit binding",
            )

        artifact_request = create_sandbox_artifact_request(
            run_id="m6-g2-local-approval-artifact-demo",
            sandbox_request_id="sandbox-request-m6-g2",
            sandbox_result_id="sandbox-result-m6-g2",
            artifact_type=_artifact_type(artifact_relative_path),
            relative_output_path=artifact_relative_path,
            content_text=content,
            requested_by=human_actor,
            human_approved=True,
            dry_run_trace_id="local-approval-artifact-demo-m6-g2",
            audit_event_id=nested_gate.audit_event_id,
            approval_decision_id=nested_gate.approval_decision_id,
            contract_audit_event_id=nested_gate.audit_event_id,
            notes="M6-G2 deterministic local approval-to-artifact demo",
            created_at="2026-06-18T00:00:00Z",
            artifact_request_id="sandbox-artifact-request-m6-g2-"
            + hashlib.sha256(
                "\n".join(
                    (
                        packet_id,
                        artifact_relative_path,
                        artifact_hash,
                        nested_gate.approval_decision_id,
                        nested_gate.audit_event_id,
                    )
                ).encode("utf-8")
            ).hexdigest()[:24],
        )
        write_result = write_function(
            gate_result=gate,
            artifact_request=artifact_request,
            workspace_root=str(workspace),
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            metadata=metadata,
        )
        if (
            not isinstance(write_result, HumanDecisionGatedArtifactWriteResult)
            or not write_result.artifact_write_occurred
        ):
            return _blocked(
                status=BLOCKED_ARTIFACT_WRITE,
                decision=_result_decision(write_result),
                capture_created=True,
                approval_decision_created=True,
                durable_handoff_complete=True,
                pre_artifact_gate_passed=True,
                write_attempted=bool(getattr(write_result, "write_attempted", False)),
                packet_hash=_result_hash(write_result, "packet_hash"),
                artifact_hash=_result_hash(write_result, "artifact_hash"),
                reason=_result_reason(write_result, "controlled artifact write failed closed"),
            )

        return LocalApprovalArtifactDemoResult(
            status=DEMO_COMPLETED,
            demo_completed=True,
            decision="APPROVE",
            capture_created=True,
            approval_decision_created=True,
            durable_handoff_complete=True,
            pre_artifact_gate_passed=True,
            write_attempted=True,
            artifact_write_occurred=True,
            artifact_path=write_result.artifact_path,
            packet_hash=write_result.packet_hash,
            artifact_hash=write_result.artifact_hash,
            provider_output_trusted=False,
            metadata_authority=False,
            blocking=False,
            reason="local approval-to-artifact demo completed",
        )
    except (TypeError, ValueError):
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="local approval-to-artifact demo failed closed",
        )
    except Exception:
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="local approval-to-artifact demo encountered a blocked stage",
        )


def _blocked(
    *,
    status: str,
    reason: str,
    decision: str = "BLOCKED",
    capture_created: bool = False,
    approval_decision_created: bool = False,
    durable_handoff_complete: bool = False,
    pre_artifact_gate_passed: bool = False,
    write_attempted: bool = False,
    packet_hash: str | None = None,
    artifact_hash: str | None = None,
) -> LocalApprovalArtifactDemoResult:
    return LocalApprovalArtifactDemoResult(
        status=status,
        demo_completed=False,
        decision=decision if decision in {"APPROVE", "REJECT"} else "BLOCKED",
        capture_created=capture_created,
        approval_decision_created=approval_decision_created,
        durable_handoff_complete=durable_handoff_complete,
        pre_artifact_gate_passed=pre_artifact_gate_passed,
        write_attempted=write_attempted,
        artifact_write_occurred=False,
        artifact_path=None,
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        provider_output_trusted=False,
        metadata_authority=False,
        blocking=True,
        reason=reason,
    )


def _absolute_existing_directory(name: str, value: str | Path) -> Path:
    path = _absolute_directory(name, value)
    if not path.is_dir():
        raise ValueError(f"{name} must be an existing directory")
    return path


def _absolute_directory(name: str, value: str | Path) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str):
        path = Path(value)
    else:
        raise TypeError(f"{name} must be a string or Path")
    if not str(path).strip() or not path.is_absolute():
        raise ValueError(f"{name} must be an explicit absolute path")
    return path


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _packet_id(
    packet_hash: str | None,
    artifact_hash: str,
    artifact_relative_path: str,
) -> str:
    material = "\n".join((packet_hash or "", artifact_hash, artifact_relative_path))
    return "m6-g2-packet-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _artifact_type(relative_path: str) -> SandboxArtifactType:
    if isinstance(relative_path, str) and relative_path.lower().endswith(".json"):
        return SandboxArtifactType.JSON_SUMMARY
    return SandboxArtifactType.TEXT_REPORT


def _result_decision(value: Any) -> str:
    decision = getattr(value, "decision", None)
    return decision if decision in {"APPROVE", "REJECT"} else "BLOCKED"


def _result_hash(value: Any, name: str) -> str | None:
    result = getattr(value, name, None)
    return result if isinstance(result, str) else None


def _result_reason(value: Any, fallback: str) -> str:
    reason = getattr(value, "reason", None)
    if isinstance(reason, str) and reason:
        return reason
    messages = getattr(value, "messages", ())
    if messages:
        return str(messages[0])
    return fallback
