from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

CLASSIFICATION_LABELS = frozenset({"safe", "ambiguous", "dangerous", "unknown"})
APPROVAL_STATES = frozenset(
    {"not_required", "requires_human_review", "approved", "denied"}
)


class CommandRiskLevel(str, Enum):
    SAFE = "SAFE"
    AMBIGUOUS = "AMBIGUOUS"
    DANGEROUS = "DANGEROUS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, init=False)
class CommandProposal:
    raw_command: str
    normalized_command: str
    tokens: tuple[str, ...]
    classification: str
    approval_state: str
    dry_run: bool
    command: str
    risk_level: CommandRiskLevel
    reason: str
    requires_human_approval: bool
    source: str
    created_by: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    proposal_id: str | None = None

    def __init__(
        self,
        *,
        raw_command: str | None = None,
        normalized_command: str | None = None,
        tokens: tuple[str, ...] | list[str] | None = None,
        classification: str | None = None,
        approval_state: str | None = None,
        reason: str,
        source: str,
        dry_run: bool = True,
        command: str | None = None,
        risk_level: CommandRiskLevel | str | None = None,
        requires_human_approval: bool | None = None,
        created_by: str = "unknown",
        metadata: Mapping[str, Any] | None = None,
        proposal_id: str | None = None,
    ) -> None:
        candidate_raw = raw_command if raw_command is not None else command
        if candidate_raw is None:
            raise ValueError("raw_command or command is required")
        if normalized_command is None:
            normalized_command = " ".join(candidate_raw.split())
        if classification is None:
            if risk_level is None:
                classification = "unknown"
            else:
                classification = self._classification_from_risk(risk_level)
        normalized_classification = self._normalize_classification(classification)
        normalized_risk = self._normalize_risk_level(
            risk_level if risk_level is not None else normalized_classification
        )
        if approval_state is None:
            if requires_human_approval is None:
                approval_state = (
                    "not_required"
                    if normalized_classification == "safe"
                    else "requires_human_review"
                )
            else:
                approval_state = (
                    "requires_human_review"
                    if requires_human_approval
                    else "not_required"
                )
        normalized_approval = self._normalize_approval_state(approval_state)
        approval_required = (
            normalized_approval == "requires_human_review"
            if requires_human_approval is None
            else requires_human_approval
        )
        token_tuple = self._normalize_tokens(tokens)
        metadata_payload: Mapping[str, Any] = {} if metadata is None else metadata
        if not isinstance(metadata_payload, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "raw_command", candidate_raw)
        object.__setattr__(self, "normalized_command", normalized_command)
        object.__setattr__(self, "tokens", token_tuple)
        object.__setattr__(self, "classification", normalized_classification)
        object.__setattr__(self, "approval_state", normalized_approval)
        object.__setattr__(self, "dry_run", dry_run)
        object.__setattr__(self, "command", command if command is not None else candidate_raw)
        object.__setattr__(self, "risk_level", normalized_risk)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "requires_human_approval", approval_required)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "created_by", created_by)
        object.__setattr__(self, "metadata", dict(metadata_payload))
        object.__setattr__(self, "proposal_id", proposal_id if proposal_id is not None else uuid4().hex)
        self.validate()

    @staticmethod
    def _normalize_risk_level(value: CommandRiskLevel | str) -> CommandRiskLevel:
        if isinstance(value, CommandRiskLevel):
            return value
        if not isinstance(value, str):
            raise TypeError("risk_level must be a string or CommandRiskLevel")
        try:
            return CommandRiskLevel(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"Unsupported risk_level: {value!r}") from exc

    @staticmethod
    def _classification_from_risk(value: CommandRiskLevel | str) -> str:
        if isinstance(value, CommandRiskLevel):
            return value.value.lower()
        if not isinstance(value, str):
            raise TypeError("risk_level must be a string or CommandRiskLevel")
        return value.strip().lower()

    @staticmethod
    def _normalize_classification(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("classification must be a string")
        normalized = value.strip().lower()
        if normalized not in CLASSIFICATION_LABELS:
            raise ValueError(f"Unsupported classification: {value!r}")
        return normalized

    @staticmethod
    def _normalize_approval_state(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("approval_state must be a string")
        normalized = value.strip().lower()
        if normalized not in APPROVAL_STATES:
            raise ValueError(f"Unsupported approval_state: {value!r}")
        return normalized

    @staticmethod
    def _normalize_tokens(value: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, (tuple, list)):
            raise TypeError("tokens must be a tuple or list of strings")
        if not all(isinstance(token, str) for token in value):
            raise TypeError("tokens must contain only strings")
        return tuple(value)

    def validate(self) -> None:
        if not isinstance(self.raw_command, str):
            raise TypeError("raw_command must be a string")
        if not isinstance(self.normalized_command, str):
            raise TypeError("normalized_command must be a string")
        if self.classification not in CLASSIFICATION_LABELS:
            raise ValueError("classification must be one of the allowed values")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError("approval_state must be one of the allowed values")
        if not isinstance(self.dry_run, bool):
            raise TypeError("dry_run must be bool")
        if not isinstance(self.command, str) or not self.command.strip():
            raise ValueError("command must be a non-empty string")
        if not isinstance(self.risk_level, CommandRiskLevel):
            raise ValueError("risk_level must be one of the allowed values")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")
        if not isinstance(self.requires_human_approval, bool):
            raise TypeError("requires_human_approval must be bool")
        if not isinstance(self.source, str):
            raise TypeError("source must be a string")
        if not isinstance(self.created_by, str):
            raise TypeError("created_by must be a string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        if not isinstance(self.proposal_id, str) or not self.proposal_id.strip():
            raise ValueError("proposal_id must be a nonblank string")

    def is_approval_required(self) -> bool:
        return self.requires_human_approval

    def is_risky_or_ambiguous(self) -> bool:
        return self.classification in {"ambiguous", "dangerous", "unknown"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_command": self.raw_command,
            "normalized_command": self.normalized_command,
            "tokens": list(self.tokens),
            "classification": self.classification,
            "approval_state": self.approval_state,
            "dry_run": self.dry_run,
            "command": self.command,
            "risk_level": self.risk_level.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "source": self.source,
            "created_by": self.created_by,
            "metadata": dict(self.metadata),
            "proposal_id": self.proposal_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CommandProposal":
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            raw_command=payload.get("raw_command", payload.get("command", "")),
            normalized_command=payload.get("normalized_command"),
            tokens=payload.get("tokens"),
            classification=payload.get("classification"),
            approval_state=payload.get("approval_state"),
            dry_run=payload.get("dry_run", True),
            command=payload.get("command", ""),
            risk_level=payload.get("risk_level", CommandRiskLevel.UNKNOWN.value),
            reason=payload.get("reason", ""),
            requires_human_approval=payload.get("requires_human_approval", False),
            source=payload.get("source", ""),
            created_by=payload.get("created_by", ""),
            metadata=payload.get("metadata", {}),
            proposal_id=payload.get("proposal_id"),
        )
