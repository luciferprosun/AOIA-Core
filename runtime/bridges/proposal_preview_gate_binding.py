from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from runtime.artifact_preview import ArtifactPreview, ArtifactPreviewStatus
from runtime.schemas.action_proposal import (
    ActionProposal,
    ActionProposalKind,
    ActionProposalSourceTrust,
)


PROPOSAL_PREVIEW_GATE_BINDING_READY = "PROPOSAL_PREVIEW_GATE_BINDING_READY"
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL"
)
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW"
)
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_TARGET_MISMATCH = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_TARGET_MISMATCH"
)
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_METADATA_MISMATCH = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_METADATA_MISMATCH"
)
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH"
)
PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE = (
    "PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE"
)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProposalPreviewGateBindingResult:
    status: str
    binding_valid: bool
    reason_code: str
    reason: str
    binding_hash: str | None = None
    binding_material: dict[str, Any] | None = None
    proposal_id: str | None = None
    proposal_hash: str | None = None
    proposal_kind: str | None = None
    proposal_source_trust: str | None = None
    preview_id: str | None = None
    preview_target_path: str | None = None
    preview_proposed_hash: str | None = None
    expected_packet_hash: str | None = None
    expected_artifact_hash: str | None = None
    gate_decision_id: str | None = None
    gate_audit_event_id: str | None = None
    gate_audit_event_hash: str | None = None
    can_approve: bool = False
    can_write: bool = False
    can_execute: bool = False
    can_commit: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    write_authority_granted: bool = False
    execution_authority_granted: bool = False
    provider_authority_granted: bool = False

    def __post_init__(self) -> None:
        for field_name in (
            "can_approve",
            "can_write",
            "can_execute",
            "can_commit",
            "can_push",
            "can_call_provider",
            "can_change_gate",
            "write_authority_granted",
            "execution_authority_granted",
            "provider_authority_granted",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "binding_valid": self.binding_valid,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "binding_hash": self.binding_hash,
            "binding_material": dict(self.binding_material or {}),
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposal_kind": self.proposal_kind,
            "proposal_source_trust": self.proposal_source_trust,
            "preview_id": self.preview_id,
            "preview_target_path": self.preview_target_path,
            "preview_proposed_hash": self.preview_proposed_hash,
            "expected_packet_hash": self.expected_packet_hash,
            "expected_artifact_hash": self.expected_artifact_hash,
            "gate_decision_id": self.gate_decision_id,
            "gate_audit_event_id": self.gate_audit_event_id,
            "gate_audit_event_hash": self.gate_audit_event_hash,
            "can_approve": self.can_approve,
            "can_write": self.can_write,
            "can_execute": self.can_execute,
            "can_commit": self.can_commit,
            "can_push": self.can_push,
            "can_call_provider": self.can_call_provider,
            "can_change_gate": self.can_change_gate,
            "write_authority_granted": self.write_authority_granted,
            "execution_authority_granted": self.execution_authority_granted,
            "provider_authority_granted": self.provider_authority_granted,
        }


def canonical_binding_json(value: Any) -> str:
    return json.dumps(_stable_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_proposal_preview_gate_binding_hash(binding_material: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_binding_json(binding_material).encode("utf-8")).hexdigest()


def build_proposal_preview_gate_binding(
    *,
    proposal: ActionProposal,
    preview: ArtifactPreview,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
    gate_result: Mapping[str, Any] | Any | None = None,
    require_proposal_hash: bool = True,
    require_gate_audit_hash: bool = True,
) -> ProposalPreviewGateBindingResult:
    proposal_context = _proposal_context(proposal)
    preview_context = _preview_context(preview)

    proposal_error = _proposal_error(proposal, require_proposal_hash)
    if proposal_error:
        return _blocked(PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PROPOSAL, proposal_error, **proposal_context)

    preview_error = _preview_error(preview)
    if preview_error:
        return _blocked(
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_INVALID_PREVIEW,
            preview_error,
            **proposal_context,
            **preview_context,
        )

    target_error = _target_consistency_error(proposal, preview)
    if target_error:
        return _blocked(
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_TARGET_MISMATCH,
            target_error,
            **proposal_context,
            **preview_context,
        )

    metadata_error = _metadata_consistency_error(proposal, preview)
    if metadata_error:
        return _blocked(
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_METADATA_MISMATCH,
            metadata_error,
            **proposal_context,
            **preview_context,
        )

    if gate_result is not None and not _full_hash(expected_artifact_hash):
        return _blocked(
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate binding requires an expected artifact hash",
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=expected_artifact_hash,
            **proposal_context,
            **preview_context,
        )

    artifact_hash = expected_artifact_hash or preview.proposed_sha256
    if not _full_hash(artifact_hash) or artifact_hash != preview.proposed_sha256:
        return _blocked(
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "expected artifact hash must match preview proposed hash",
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=artifact_hash,
            **proposal_context,
            **preview_context,
        )

    gate_fields: dict[str, str | None] = {
        "gate_decision_id": None,
        "gate_audit_event_id": None,
        "gate_audit_event_hash": None,
    }
    if gate_result is not None:
        gate, gate_error = _validate_gate_result(
            gate_result=gate_result,
            proposal=proposal,
            preview=preview,
            expected_packet_hash=expected_packet_hash,
            expected_artifact_hash=artifact_hash,
            require_gate_audit_hash=require_gate_audit_hash,
        )
        if gate_error:
            return _blocked(
                gate_error[0],
                gate_error[1],
                expected_packet_hash=expected_packet_hash,
                expected_artifact_hash=artifact_hash,
                **proposal_context,
                **preview_context,
            )
        gate_fields = gate

    binding_material = {
        "schema_version": "AOIA_PROPOSAL_PREVIEW_GATE_BINDING_1A",
        "proposal_id": proposal.proposal_id,
        "proposal_hash": proposal.proposal_hash,
        "proposal_kind": proposal.action_kind.value,
        "proposal_source_trust": proposal.source_trust.value,
        "preview_id": preview.preview_id,
        "preview_target_path": preview.target_path,
        "preview_proposed_hash": preview.proposed_sha256,
        "expected_packet_hash": expected_packet_hash,
        "expected_artifact_hash": artifact_hash,
        "gate_decision_id": gate_fields["gate_decision_id"],
        "gate_audit_event_id": gate_fields["gate_audit_event_id"],
        "gate_audit_event_hash": gate_fields["gate_audit_event_hash"],
    }
    binding_hash = compute_proposal_preview_gate_binding_hash(binding_material)
    return ProposalPreviewGateBindingResult(
        status=PROPOSAL_PREVIEW_GATE_BINDING_READY,
        binding_valid=True,
        reason_code=PROPOSAL_PREVIEW_GATE_BINDING_READY,
        reason="proposal, preview, artifact, packet, and gate metadata are bound as evidence only",
        binding_hash=binding_hash,
        binding_material=binding_material,
        proposal_id=proposal.proposal_id,
        proposal_hash=proposal.proposal_hash,
        proposal_kind=proposal.action_kind.value,
        proposal_source_trust=proposal.source_trust.value,
        preview_id=preview.preview_id,
        preview_target_path=preview.target_path,
        preview_proposed_hash=preview.proposed_sha256,
        expected_packet_hash=expected_packet_hash,
        expected_artifact_hash=artifact_hash,
        gate_decision_id=gate_fields["gate_decision_id"],
        gate_audit_event_id=gate_fields["gate_audit_event_id"],
        gate_audit_event_hash=gate_fields["gate_audit_event_hash"],
    )


def _validate_gate_result(
    *,
    gate_result: Mapping[str, Any] | Any,
    proposal: ActionProposal,
    preview: ArtifactPreview,
    expected_packet_hash: str | None,
    expected_artifact_hash: str,
    require_gate_audit_hash: bool,
) -> tuple[dict[str, str | None], tuple[str, str] | None]:
    try:
        gate = _mapping(gate_result)
    except TypeError:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE,
            "gate evidence must be a mapping or to_dict object",
        )
    if not _full_hash(expected_packet_hash):
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate binding requires an expected packet hash",
        )
    if not _full_hash(expected_artifact_hash):
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate binding requires an expected artifact hash",
        )
    if gate.get("metadata_authority") is not False:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE,
            "metadata authority cannot satisfy binding evidence",
        )
    if gate.get("provider_output_trusted") is not False:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE,
            "trusted provider output cannot satisfy binding evidence",
        )
    if gate.get("artifact_write_occurred") is not False:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_UNSAFE,
            "binding evidence must be pre-write",
        )
    if gate.get("decision") != "APPROVE" or gate.get("pre_artifact_gate_passed") is not True:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence is not a passed APPROVE gate",
        )
    if gate.get("durable_handoff_complete") is not True:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence lacks durable handoff completion",
        )
    if gate.get("packet_hash") != expected_packet_hash:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate packet hash does not match expected packet hash",
        )
    if gate.get("artifact_hash") != expected_artifact_hash or gate.get("artifact_hash") != preview.proposed_sha256:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate artifact hash does not match preview proposed hash",
        )

    optional_mismatch = _optional_gate_metadata_mismatch(gate, proposal, preview)
    if optional_mismatch:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            optional_mismatch,
        )

    try:
        nested = _mapping(gate.get("gate_result"))
    except TypeError:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence lacks nested approval proof",
        )
    decision_id = _text(nested.get("approval_decision_id"))
    audit_event_id = _text(nested.get("audit_event_id"))
    audit_event_hash = _full_hash(nested.get("audit_event_hash"))
    if decision_id is None:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence lacks approval decision id",
        )
    if audit_event_id is None:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence lacks audit event id",
        )
    if require_gate_audit_hash and audit_event_hash is None:
        return {}, (
            PROPOSAL_PREVIEW_GATE_BINDING_BLOCKED_GATE_MISMATCH,
            "gate evidence lacks audit event hash",
        )
    return {
        "gate_decision_id": decision_id,
        "gate_audit_event_id": audit_event_id,
        "gate_audit_event_hash": audit_event_hash,
    }, None


def _blocked(
    status: str,
    reason: str,
    *,
    proposal_id: str | None = None,
    proposal_hash: str | None = None,
    proposal_kind: str | None = None,
    proposal_source_trust: str | None = None,
    preview_id: str | None = None,
    preview_target_path: str | None = None,
    preview_proposed_hash: str | None = None,
    expected_packet_hash: str | None = None,
    expected_artifact_hash: str | None = None,
) -> ProposalPreviewGateBindingResult:
    return ProposalPreviewGateBindingResult(
        status=status,
        binding_valid=False,
        reason_code=status,
        reason=reason,
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        proposal_kind=proposal_kind,
        proposal_source_trust=proposal_source_trust,
        preview_id=preview_id,
        preview_target_path=preview_target_path,
        preview_proposed_hash=preview_proposed_hash,
        expected_packet_hash=expected_packet_hash,
        expected_artifact_hash=expected_artifact_hash,
    )


def _proposal_error(proposal: object, require_proposal_hash: bool) -> str:
    if not isinstance(proposal, ActionProposal):
        return "binding requires an ActionProposal"
    if proposal.action_kind is not ActionProposalKind.FILE_WRITE:
        return "binding accepts only FILE_WRITE action proposals"
    if require_proposal_hash and not _full_hash(proposal.proposal_hash):
        return "binding requires a full proposal hash"
    if len(proposal.target_refs) != 1:
        return "binding requires exactly one proposal target"
    return ""


def _preview_error(preview: object) -> str:
    if not isinstance(preview, ArtifactPreview):
        return "binding requires an ArtifactPreview"
    if preview.status != ArtifactPreviewStatus.PREVIEW_READY:
        return "preview must be ready"
    if not _full_hash(preview.proposed_sha256):
        return "preview proposed hash is malformed"
    _, path_error = _safe_relative_target(preview.target_path)
    if path_error:
        return "preview target path is unsafe"
    return ""


def _target_consistency_error(proposal: ActionProposal, preview: ArtifactPreview) -> str:
    proposal_target, proposal_error = _safe_relative_target(proposal.target_refs[0])
    preview_target, preview_error = _safe_relative_target(preview.target_path)
    if proposal_error or preview_error:
        return "proposal or preview target is unsafe"
    if proposal_target != preview_target:
        return "proposal target path does not match preview target path"
    return ""


def _metadata_consistency_error(proposal: ActionProposal, preview: ArtifactPreview) -> str:
    preview_trust = (preview.provider_output_trust or "").strip().casefold()
    if proposal.source_trust is ActionProposalSourceTrust.PROVIDER_UNTRUSTED and preview_trust != "untrusted":
        return "provider-untrusted proposal must remain untrusted in preview metadata"
    if proposal.source_trust is not ActionProposalSourceTrust.PROVIDER_UNTRUSTED and preview_trust == "untrusted":
        return "preview untrusted provider metadata does not match proposal source trust"
    return ""


def _optional_gate_metadata_mismatch(
    gate: Mapping[str, Any],
    proposal: ActionProposal,
    preview: ArtifactPreview,
) -> str:
    comparisons = (
        ("proposal_id", proposal.proposal_id, "gate proposal id does not match proposal"),
        ("proposal_hash", proposal.proposal_hash, "gate proposal hash does not match proposal"),
        ("preview_id", preview.preview_id, "gate preview id does not match preview"),
        ("preview_proposed_hash", preview.proposed_sha256, "gate preview hash does not match preview"),
    )
    for field_name, expected, message in comparisons:
        value = gate.get(field_name)
        if value is not None and value != expected:
            return message
    return ""


def _safe_relative_target(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", "target must be text"
    candidate = value.strip()
    if not candidate or "\x00" in candidate:
        return "", "target is empty or malformed"
    if "\\" in candidate:
        return "", "backslash target traversal is unsafe"
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return "", "absolute target is unsafe"
    path = PurePosixPath(candidate)
    if ".." in path.parts:
        return "", "parent traversal target is unsafe"
    if ".git" in path.parts:
        return "", "git metadata target is unsafe"
    normalized = path.as_posix()
    if normalized in ("", "."):
        return "", "target is empty or malformed"
    return normalized, None


def _proposal_context(proposal: object) -> dict[str, str | None]:
    if not isinstance(proposal, ActionProposal):
        return {
            "proposal_id": None,
            "proposal_hash": None,
            "proposal_kind": None,
            "proposal_source_trust": None,
        }
    return {
        "proposal_id": proposal.proposal_id,
        "proposal_hash": proposal.proposal_hash,
        "proposal_kind": proposal.action_kind.value,
        "proposal_source_trust": proposal.source_trust.value,
    }


def _preview_context(preview: object) -> dict[str, str | None]:
    if not isinstance(preview, ArtifactPreview):
        return {
            "preview_id": None,
            "preview_target_path": None,
            "preview_proposed_hash": None,
        }
    return {
        "preview_id": preview.preview_id,
        "preview_target_path": preview.target_path,
        "preview_proposed_hash": preview.proposed_sha256,
    }


def _mapping(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    raise TypeError("value must be a mapping or to_dict object")


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _full_hash(value: Any) -> str | None:
    if isinstance(value, str) and _SHA256_HEX.fullmatch(value):
        return value
    return None


def _stable_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
