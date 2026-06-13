from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


HUMAN_APPROVAL_REVIEW_PACKET_VERSION = "AOIA_HUMAN_APPROVAL_REVIEW_PACKET_V1"
MAX_HUMAN_APPROVAL_REVIEW_GOAL_CHARS = 4096
ALLOWED_HUMAN_REVIEW_DECISIONS = ("approve", "deny")
PENDING_DECISION_STATUS = "pending"
DEFAULT_SAFETY_BOUNDARIES = (
    "no_shell_execution",
    "no_provider_api_network",
    "no_browser_git_cloud",
    "no_db_sqlite_orm",
    "artifact_write_only",
    "durable_audit_required",
)
ALLOWED_REVIEW_ARTIFACT_EXTENSIONS = frozenset({".txt", ".md", ".json"})


@dataclass(frozen=True)
class HumanApprovalReviewPacket:
    packet_version: str
    packet_id: str
    goal: str
    proposal_id: str | None
    proposed_action_summary: str
    run_id: str | None
    artifact_relative_path: str
    artifact_destination_summary: str
    audit_context_summary: str
    durable_audit_required: bool
    decision_required: bool
    decision_status: str
    allowed_decisions: tuple[str, ...]
    safety_boundaries: tuple[str, ...]
    untrusted_inputs: tuple[str, ...]
    created_by: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "packet_version", _coerce_text("packet_version", self.packet_version))
        object.__setattr__(self, "goal", _normalize_goal(self.goal))
        object.__setattr__(self, "proposal_id", _optional_text("proposal_id", self.proposal_id))
        object.__setattr__(self, "proposed_action_summary", _require_text("proposed_action_summary", self.proposed_action_summary))
        object.__setattr__(self, "run_id", _optional_text("run_id", self.run_id))
        object.__setattr__(self, "artifact_relative_path", _validate_artifact_relative_path(self.artifact_relative_path))
        object.__setattr__(
            self,
            "artifact_destination_summary",
            _require_text("artifact_destination_summary", self.artifact_destination_summary),
        )
        object.__setattr__(self, "audit_context_summary", _require_text("audit_context_summary", self.audit_context_summary))
        if self.packet_version != HUMAN_APPROVAL_REVIEW_PACKET_VERSION:
            raise ValueError("packet_version is not supported")
        if self.durable_audit_required is not True:
            raise ValueError("durable_audit_required must be True")
        if self.decision_required is not True:
            raise ValueError("decision_required must be True")
        object.__setattr__(self, "decision_status", _require_text("decision_status", self.decision_status))
        if self.decision_status != PENDING_DECISION_STATUS:
            raise ValueError("decision_status must remain pending")
        object.__setattr__(self, "allowed_decisions", _normalize_tuple("allowed_decisions", self.allowed_decisions))
        if self.allowed_decisions != ALLOWED_HUMAN_REVIEW_DECISIONS:
            raise ValueError("allowed_decisions must be approve and deny only")
        object.__setattr__(self, "safety_boundaries", _normalize_tuple("safety_boundaries", self.safety_boundaries))
        _assert_required_boundaries(self.safety_boundaries)
        object.__setattr__(self, "untrusted_inputs", _normalize_tuple("untrusted_inputs", self.untrusted_inputs))
        object.__setattr__(self, "created_by", _require_text("created_by", self.created_by))
        expected_packet_id = _packet_id_for(self)
        packet_id = _coerce_text("packet_id", self.packet_id)
        if packet_id and packet_id != expected_packet_id:
            raise ValueError("packet_id does not match review packet content")
        object.__setattr__(self, "packet_id", expected_packet_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_version": self.packet_version,
            "packet_id": self.packet_id,
            "goal": self.goal,
            "proposal_id": self.proposal_id,
            "proposed_action_summary": self.proposed_action_summary,
            "run_id": self.run_id,
            "artifact_relative_path": self.artifact_relative_path,
            "artifact_destination_summary": self.artifact_destination_summary,
            "audit_context_summary": self.audit_context_summary,
            "durable_audit_required": self.durable_audit_required,
            "decision_required": self.decision_required,
            "decision_status": self.decision_status,
            "allowed_decisions": self.allowed_decisions,
            "safety_boundaries": self.safety_boundaries,
            "untrusted_inputs": self.untrusted_inputs,
            "created_by": self.created_by,
        }


def create_human_approval_review_packet(
    *,
    goal: str,
    artifact_relative_path: str,
    artifact_destination_summary: str,
    audit_context_summary: str,
    proposal_id: str | None = None,
    proposed_action_summary: str = "workspace-bound artifact request",
    run_id: str | None = None,
    created_by: str = "aoia-human-approval-review",
    untrusted_inputs: tuple[str, ...] = (),
) -> HumanApprovalReviewPacket:
    return HumanApprovalReviewPacket(
        packet_version=HUMAN_APPROVAL_REVIEW_PACKET_VERSION,
        packet_id="",
        goal=goal,
        proposal_id=proposal_id,
        proposed_action_summary=proposed_action_summary,
        run_id=run_id,
        artifact_relative_path=artifact_relative_path,
        artifact_destination_summary=artifact_destination_summary,
        audit_context_summary=audit_context_summary,
        durable_audit_required=True,
        decision_required=True,
        decision_status=PENDING_DECISION_STATUS,
        allowed_decisions=ALLOWED_HUMAN_REVIEW_DECISIONS,
        safety_boundaries=DEFAULT_SAFETY_BOUNDARIES,
        untrusted_inputs=untrusted_inputs,
        created_by=created_by,
    )


def render_human_approval_review_packet_markdown(packet: HumanApprovalReviewPacket) -> str:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    return "\n".join(
        (
            "# Human Approval Review Packet",
            "",
            f"Packet version: {packet.packet_version}",
            f"Packet id: {packet.packet_id}",
            f"Decision status: {packet.decision_status}",
            f"Allowed decisions: {', '.join(packet.allowed_decisions)}",
            "",
            "## Goal",
            packet.goal,
            "",
            "## Proposed Action",
            f"Proposal id: {packet.proposal_id or 'not provided'}",
            f"Action summary: {packet.proposed_action_summary}",
            "",
            "## Run Context",
            f"Run id: {packet.run_id or 'not provided'}",
            f"Artifact relative path: {packet.artifact_relative_path}",
            f"Artifact destination: {packet.artifact_destination_summary}",
            f"Audit context: {packet.audit_context_summary}",
            "",
            "## Safety Boundaries",
            "\n".join(f"- {boundary}" for boundary in packet.safety_boundaries),
            "",
            "## Untrusted Inputs",
            "\n".join(f"- {item}" for item in packet.untrusted_inputs) if packet.untrusted_inputs else "- none declared",
            "",
            "## Human Decision Required",
            "This packet is not an approval. A separate human decision is required.",
            "",
        )
    )


def human_approval_review_packet_to_dict(packet: HumanApprovalReviewPacket) -> dict[str, Any]:
    if not isinstance(packet, HumanApprovalReviewPacket):
        raise TypeError("packet must be a HumanApprovalReviewPacket")
    return packet.to_dict()


def _packet_id_for(packet: HumanApprovalReviewPacket) -> str:
    material = "\n".join(
        (
            packet.packet_version,
            packet.goal,
            packet.proposal_id or "",
            packet.proposed_action_summary,
            packet.run_id or "",
            packet.artifact_relative_path,
            packet.artifact_destination_summary,
            packet.audit_context_summary,
            "|".join(packet.allowed_decisions),
            "|".join(packet.safety_boundaries),
            "|".join(packet.untrusted_inputs),
            packet.created_by,
        )
    )
    return "human-approval-review-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _normalize_goal(goal: str) -> str:
    value = _require_text("goal", goal)
    if len(value) > MAX_HUMAN_APPROVAL_REVIEW_GOAL_CHARS:
        raise ValueError("goal is too long for human approval review")
    for character in value:
        codepoint = ord(character)
        if (codepoint < 32 and character not in ("\n", "\t")) or codepoint == 127:
            raise ValueError("goal contains a blocked control character")
    return value


def _validate_artifact_relative_path(relative_path: str) -> str:
    value = _require_text("artifact_relative_path", relative_path)
    if "\\" in value:
        raise ValueError("artifact_relative_path must not contain backslashes")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise ValueError("artifact_relative_path must be relative")
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError("artifact_relative_path contains an unsafe path component")
    if any(part == ".git" for part in parts):
        raise ValueError("artifact_relative_path must not target .git")
    if path.suffix.lower() not in ALLOWED_REVIEW_ARTIFACT_EXTENSIONS:
        raise ValueError("artifact_relative_path extension is not allowed")
    return value


def _assert_required_boundaries(boundaries: tuple[str, ...]) -> None:
    missing = set(DEFAULT_SAFETY_BOUNDARIES).difference(boundaries)
    if missing:
        raise ValueError("safety_boundaries is missing required entries")


def _normalize_tuple(name: str, values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    normalized = tuple(_require_text(name, value) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} must not contain duplicates")
    return normalized


def _optional_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    text = _coerce_text(name, value).strip()
    return text or None


def _require_text(name: str, value: str) -> str:
    text = _coerce_text(name, value).strip()
    if not text:
        raise ValueError(f"{name} must not be empty")
    return text


def _coerce_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value
