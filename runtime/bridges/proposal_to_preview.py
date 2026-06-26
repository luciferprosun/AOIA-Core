from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from runtime.artifact_preview import (
    ArtifactPreview,
    ArtifactPreviewRequest,
    ArtifactPreviewStatus,
    build_artifact_preview,
)
from runtime.schemas.action_proposal import (
    ActionProposal,
    ActionProposalKind,
    ActionProposalSourceTrust,
    ActionProposalStatus,
)


PROPOSAL_PREVIEW_READY = "PROPOSAL_PREVIEW_READY"
PROPOSAL_PREVIEW_BLOCKED_INVALID_PROPOSAL = "PROPOSAL_PREVIEW_BLOCKED_INVALID_PROPOSAL"
PROPOSAL_PREVIEW_BLOCKED_UNSUPPORTED_KIND = "PROPOSAL_PREVIEW_BLOCKED_UNSUPPORTED_KIND"
PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET = "PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET"
PROPOSAL_PREVIEW_BLOCKED_TARGET_MISMATCH = "PROPOSAL_PREVIEW_BLOCKED_TARGET_MISMATCH"
PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET = "PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET"
PROPOSAL_PREVIEW_BLOCKED_INVALID_CONTENT = "PROPOSAL_PREVIEW_BLOCKED_INVALID_CONTENT"


@dataclass(frozen=True)
class ProposalToPreviewBridgeResult:
    status: str
    preview_ready: bool
    reason_code: str
    reason: str
    proposal_id: str | None = None
    proposal_hash: str | None = None
    proposal_kind: str | None = None
    proposal_source_trust: str | None = None
    target_path: str | None = None
    preview_id: str | None = None
    preview_proposed_hash: str | None = None
    artifact_preview: ArtifactPreview | None = None
    binding_metadata: dict[str, Any] | None = None
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
            "preview_ready": self.preview_ready,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "proposal_id": self.proposal_id,
            "proposal_hash": self.proposal_hash,
            "proposal_kind": self.proposal_kind,
            "proposal_source_trust": self.proposal_source_trust,
            "target_path": self.target_path,
            "preview_id": self.preview_id,
            "preview_proposed_hash": self.preview_proposed_hash,
            "binding_metadata": dict(self.binding_metadata or {}),
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


def build_preview_from_action_proposal(
    *,
    proposal: ActionProposal,
    proposed_content_text: str,
    original_content_text: str | None = None,
    expected_target_path: str | None = None,
    artifact_kind: str = "text",
) -> ProposalToPreviewBridgeResult:
    proposal_context = _proposal_context(proposal)
    if not isinstance(proposal, ActionProposal):
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_INVALID_PROPOSAL,
            "bridge requires an ActionProposal",
            **proposal_context,
        )
    if proposal.action_kind is not ActionProposalKind.FILE_WRITE:
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_UNSUPPORTED_KIND,
            "bridge accepts only FILE_WRITE action proposals",
            **proposal_context,
        )
    if proposal.status is not ActionProposalStatus.PROPOSAL_READY:
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_INVALID_PROPOSAL,
            "bridge requires a ready ActionProposal",
            **proposal_context,
        )
    if not isinstance(proposed_content_text, str):
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_INVALID_CONTENT,
            "bridge requires proposed content text",
            **proposal_context,
        )

    target_refs = proposal.target_refs
    if len(target_refs) != 1:
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET,
            "bridge requires exactly one target reference",
            **proposal_context,
        )

    target_path, target_error = _safe_relative_target(target_refs[0])
    if target_error:
        return _blocked(target_error, "bridge target path is unsafe", **proposal_context)

    if expected_target_path is not None:
        expected_path, expected_error = _safe_relative_target(expected_target_path)
        if expected_error:
            return _blocked(expected_error, "expected target path is unsafe", **proposal_context)
        if expected_path != target_path:
            return _blocked(
                PROPOSAL_PREVIEW_BLOCKED_TARGET_MISMATCH,
                "proposal target does not match expected preview target",
                **proposal_context,
            )

    preview = build_artifact_preview(
        ArtifactPreviewRequest(
            target_path=target_path,
            proposed_content=proposed_content_text,
            original_content=original_content_text,
            artifact_kind=artifact_kind,
            reason=proposal.summary,
            provider_id=proposal.proposed_by if proposal.provider_generated else None,
            provider_output_trust=_preview_source_trust(proposal),
        )
    )
    if preview.status != ArtifactPreviewStatus.PREVIEW_READY:
        return _blocked(
            PROPOSAL_PREVIEW_BLOCKED_INVALID_PROPOSAL,
            "artifact preview builder did not produce a ready preview",
            **proposal_context,
        )

    binding_metadata = {
        "proposal_id": proposal.proposal_id,
        "proposal_hash": proposal.proposal_hash,
        "proposal_kind": proposal.action_kind.value,
        "proposal_source_trust": proposal.source_trust.value,
        "proposal_human_review_required": proposal.human_review_required,
        "preview_id": preview.preview_id,
        "preview_proposed_hash": preview.proposed_sha256,
        "preview_target_path": preview.target_path,
    }
    return ProposalToPreviewBridgeResult(
        status=PROPOSAL_PREVIEW_READY,
        preview_ready=True,
        reason_code=PROPOSAL_PREVIEW_READY,
        reason="proposal was converted to preview evidence only",
        proposal_id=proposal.proposal_id,
        proposal_hash=proposal.proposal_hash,
        proposal_kind=proposal.action_kind.value,
        proposal_source_trust=proposal.source_trust.value,
        target_path=preview.target_path,
        preview_id=preview.preview_id,
        preview_proposed_hash=preview.proposed_sha256,
        artifact_preview=preview,
        binding_metadata=binding_metadata,
    )


def _blocked(
    status: str,
    reason: str,
    *,
    proposal_id: str | None = None,
    proposal_hash: str | None = None,
    proposal_kind: str | None = None,
    proposal_source_trust: str | None = None,
) -> ProposalToPreviewBridgeResult:
    return ProposalToPreviewBridgeResult(
        status=status,
        preview_ready=False,
        reason_code=status,
        reason=reason,
        proposal_id=proposal_id,
        proposal_hash=proposal_hash,
        proposal_kind=proposal_kind,
        proposal_source_trust=proposal_source_trust,
    )


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


def _safe_relative_target(value: object) -> tuple[str, str | None]:
    if not isinstance(value, str):
        return "", PROPOSAL_PREVIEW_BLOCKED_MISSING_TARGET
    candidate = value.strip()
    if not candidate or "\x00" in candidate:
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    if "\\" in candidate:
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    if PurePosixPath(candidate).is_absolute() or PureWindowsPath(candidate).is_absolute():
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    path = PurePosixPath(candidate)
    if ".." in path.parts:
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    if ".git" in path.parts:
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    normalized = path.as_posix()
    if normalized in ("", "."):
        return "", PROPOSAL_PREVIEW_BLOCKED_UNSAFE_TARGET
    return normalized, None


def _preview_source_trust(proposal: ActionProposal) -> str | None:
    if proposal.source_trust is ActionProposalSourceTrust.PROVIDER_UNTRUSTED:
        return "untrusted"
    return None
