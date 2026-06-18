from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from runtime.human_decision_gate_integration import (
    GATE_PASSED,
    HumanDecisionPreArtifactGateResult,
)
from runtime.safety.approval_artifact_gate import PreArtifactApprovalGateResult
from runtime.safety.sandbox_artifact_runner import write_sandbox_artifact
from runtime.schemas.sandbox_artifact import (
    SandboxArtifactRequest,
    SandboxArtifactResult,
)


ARTIFACT_WRITTEN = "ARTIFACT_WRITTEN"
BLOCKED_REJECT = "BLOCKED_REJECT"
BLOCKED_GATE_NOT_PASSED = "BLOCKED_GATE_NOT_PASSED"
BLOCKED_INVALID_GATE_RESULT = "BLOCKED_INVALID_GATE_RESULT"
BLOCKED_MISSING_PACKET_HASH = "BLOCKED_MISSING_PACKET_HASH"
BLOCKED_STALE_OR_MISMATCHED_STATE = "BLOCKED_STALE_OR_MISMATCHED_STATE"
BLOCKED_ARTIFACT_REQUEST_MISMATCH = "BLOCKED_ARTIFACT_REQUEST_MISMATCH"
BLOCKED_CONTROLLED_WRITE = "BLOCKED_CONTROLLED_WRITE"
ERROR_FAIL_CLOSED = "ERROR_FAIL_CLOSED"

ArtifactWriter = Callable[..., SandboxArtifactResult]


@dataclass(frozen=True)
class HumanDecisionGatedArtifactWriteResult:
    status: str
    write_attempted: bool
    artifact_write_occurred: bool
    artifact_path: str | None
    decision: str
    blocking: bool
    durable_handoff_complete: bool
    pre_artifact_gate_passed: bool
    provider_output_trusted: bool
    metadata_authority: bool
    packet_hash: str | None
    artifact_hash: str | None
    reason: str
    artifact_result: SandboxArtifactResult | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "write_attempted": self.write_attempted,
            "artifact_write_occurred": self.artifact_write_occurred,
            "artifact_path": self.artifact_path,
            "decision": self.decision,
            "blocking": self.blocking,
            "durable_handoff_complete": self.durable_handoff_complete,
            "pre_artifact_gate_passed": self.pre_artifact_gate_passed,
            "provider_output_trusted": self.provider_output_trusted,
            "metadata_authority": self.metadata_authority,
            "packet_hash": self.packet_hash,
            "artifact_hash": self.artifact_hash,
            "reason": self.reason,
            "artifact_result": (
                self.artifact_result.to_dict()
                if self.artifact_result is not None
                else None
            ),
        }


def write_artifact_after_human_gate(
    *,
    gate_result: HumanDecisionPreArtifactGateResult | Mapping[str, Any],
    artifact_request: SandboxArtifactRequest,
    workspace_root: str,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    artifact_writer: ArtifactWriter = write_sandbox_artifact,
) -> HumanDecisionGatedArtifactWriteResult:
    del metadata
    try:
        gate = _gate_mapping(gate_result)
        packet_hash = _full_hash(gate.get("packet_hash"))
        artifact_hash = _full_hash(gate.get("artifact_hash"))
        expected_packet = _optional_expected_hash(expected_packet_hash)
        expected_artifact = _optional_expected_hash(expected_artifact_hash)

        if packet_hash is None:
            return _blocked(
                status=BLOCKED_MISSING_PACKET_HASH,
                reason="passed gate result must contain a full packet hash",
            )
        if expected_packet is not None and packet_hash != expected_packet:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="gate packet hash does not match expected packet hash",
            )
        if expected_artifact is not None and artifact_hash != expected_artifact:
            return _blocked(
                status=BLOCKED_STALE_OR_MISMATCHED_STATE,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="gate artifact hash does not match expected artifact hash",
            )

        decision = gate.get("decision")
        if decision == "REJECT":
            return _blocked(
                status=BLOCKED_REJECT,
                decision="REJECT",
                durable_handoff_complete=gate.get("durable_handoff_complete") is True,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="human REJECT remains blocking and cannot write an artifact",
            )
        if not _gate_boundary_flags_are_safe(gate):
            return _blocked(
                status=BLOCKED_GATE_NOT_PASSED,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason="artifact write requires a completed durable handoff and passed gate",
            )

        nested_gate = _pre_artifact_gate_result(gate.get("gate_result"))
        _validate_gate_evidence(gate, nested_gate)
        _validate_artifact_request(
            artifact_request=artifact_request,
            nested_gate=nested_gate,
            artifact_hash=artifact_hash,
        )

        artifact_result = artifact_writer(artifact_request, workspace_root)
        if not isinstance(artifact_result, SandboxArtifactResult):
            raise TypeError("artifact writer must return SandboxArtifactResult")
        if not artifact_result.write_completed:
            return HumanDecisionGatedArtifactWriteResult(
                status=BLOCKED_CONTROLLED_WRITE,
                write_attempted=artifact_result.write_attempted,
                artifact_write_occurred=False,
                artifact_path=None,
                decision="APPROVE",
                blocking=True,
                durable_handoff_complete=True,
                pre_artifact_gate_passed=True,
                provider_output_trusted=False,
                metadata_authority=False,
                packet_hash=packet_hash,
                artifact_hash=artifact_hash,
                reason=artifact_result.blocked_reason or "controlled artifact write blocked",
                artifact_result=artifact_result,
            )

        if (
            artifact_result.artifact_request_id != artifact_request.artifact_request_id
            or artifact_result.content_hash != artifact_request.content_hash
            or not artifact_result.resolved_output_path
        ):
            raise ValueError("controlled writer result does not match artifact request")
        return HumanDecisionGatedArtifactWriteResult(
            status=ARTIFACT_WRITTEN,
            write_attempted=True,
            artifact_write_occurred=True,
            artifact_path=artifact_result.resolved_output_path,
            decision="APPROVE",
            blocking=False,
            durable_handoff_complete=True,
            pre_artifact_gate_passed=True,
            provider_output_trusted=False,
            metadata_authority=False,
            packet_hash=packet_hash,
            artifact_hash=artifact_hash,
            reason="controlled workspace artifact write completed after passed human gate",
            artifact_result=artifact_result,
        )
    except (TypeError, ValueError):
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="gated artifact write integration failed closed",
        )
    except Exception:
        return _blocked(
            status=ERROR_FAIL_CLOSED,
            reason="controlled artifact writer failed closed",
        )


def _gate_mapping(
    gate_result: HumanDecisionPreArtifactGateResult | Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(gate_result, HumanDecisionPreArtifactGateResult):
        return gate_result.to_dict()
    if isinstance(gate_result, Mapping):
        return dict(gate_result)
    raise TypeError("gate_result must be a HumanDecisionPreArtifactGateResult or mapping")


def _gate_boundary_flags_are_safe(gate: Mapping[str, Any]) -> bool:
    return (
        gate.get("status") == GATE_PASSED
        and gate.get("gate_evaluated") is True
        and gate.get("decision") == "APPROVE"
        and gate.get("blocking") is False
        and gate.get("durable_handoff_complete") is True
        and gate.get("pre_artifact_gate_passed") is True
        and gate.get("artifact_write_occurred") is False
        and gate.get("provider_output_trusted") is False
        and gate.get("metadata_authority") is False
    )


def _pre_artifact_gate_result(value: Any) -> PreArtifactApprovalGateResult:
    if isinstance(value, PreArtifactApprovalGateResult):
        return PreArtifactApprovalGateResult(**value.to_dict())
    if isinstance(value, Mapping):
        return PreArtifactApprovalGateResult(**dict(value))
    raise TypeError("gate result lacks existing pre-artifact gate evidence")


def _validate_gate_evidence(
    gate: Mapping[str, Any],
    nested_gate: PreArtifactApprovalGateResult,
) -> None:
    if nested_gate.allowed is not True:
        raise ValueError("existing pre-artifact gate did not pass")
    if nested_gate.approval_decision_type != "APPROVE":
        raise ValueError("existing pre-artifact gate decision is not APPROVE")
    if not _nonempty_text(nested_gate.approval_decision_id):
        raise ValueError("existing pre-artifact gate lacks decision binding")
    if not _nonempty_text(nested_gate.audit_event_id):
        raise ValueError("existing pre-artifact gate lacks durable audit event binding")
    if _full_hash(nested_gate.audit_event_hash) is None:
        raise ValueError("existing pre-artifact gate lacks durable audit hash binding")
    if gate.get("artifact_write_occurred") is not False:
        raise ValueError("gate result already claims an artifact write")


def _validate_artifact_request(
    *,
    artifact_request: SandboxArtifactRequest,
    nested_gate: PreArtifactApprovalGateResult,
    artifact_hash: str | None,
) -> None:
    if not isinstance(artifact_request, SandboxArtifactRequest):
        raise TypeError("artifact_request must be a SandboxArtifactRequest")
    if artifact_request.human_approved is not True:
        raise ValueError("artifact request must preserve explicit human approval")
    if artifact_request.artifact_write_allowed is not True:
        raise ValueError("artifact request contract does not allow controlled write")
    if artifact_request.approval_decision_id != nested_gate.approval_decision_id:
        raise ValueError("artifact request approval decision does not match gate")
    if artifact_request.audit_event_id != nested_gate.audit_event_id:
        raise ValueError("artifact request audit event does not match gate")
    if artifact_request.contract_audit_event_id != nested_gate.audit_event_id:
        raise ValueError("artifact request contract audit event does not match gate")
    if artifact_hash is not None and artifact_request.content_hash != artifact_hash:
        raise ValueError("artifact request content hash does not match reviewed artifact hash")


def _blocked(
    *,
    status: str,
    reason: str,
    decision: str = "BLOCKED",
    durable_handoff_complete: bool = False,
    packet_hash: str | None = None,
    artifact_hash: str | None = None,
) -> HumanDecisionGatedArtifactWriteResult:
    return HumanDecisionGatedArtifactWriteResult(
        status=status,
        write_attempted=False,
        artifact_write_occurred=False,
        artifact_path=None,
        decision=decision,
        blocking=True,
        durable_handoff_complete=durable_handoff_complete,
        pre_artifact_gate_passed=False,
        provider_output_trusted=False,
        metadata_authority=False,
        packet_hash=packet_hash,
        artifact_hash=artifact_hash,
        reason=reason,
        artifact_result=None,
    )


def _optional_expected_hash(value: str | None) -> str | None:
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


def _nonempty_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
