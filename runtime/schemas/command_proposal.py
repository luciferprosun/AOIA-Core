from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class CommandRiskLevel(str, Enum):
    SAFE = "SAFE"
    AMBIGUOUS = "AMBIGUOUS"
    DANGEROUS = "DANGEROUS"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CommandProposal:
    command: str
    risk_level: CommandRiskLevel | str
    reason: str
    requires_human_approval: bool
    source: str
    created_by: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    proposal_id: str | None = None

    def __post_init__(self) -> None:
        normalized_risk = self._normalize_risk_level(self.risk_level)
        object.__setattr__(self, "risk_level", normalized_risk)
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.proposal_id is None:
            object.__setattr__(self, "proposal_id", uuid4().hex)
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

    def validate(self) -> None:
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

    def to_dict(self) -> dict[str, Any]:
        return {
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
            command=payload.get("command", ""),
            risk_level=payload.get("risk_level", CommandRiskLevel.UNKNOWN.value),
            reason=payload.get("reason", ""),
            requires_human_approval=payload.get("requires_human_approval", False),
            source=payload.get("source", ""),
            created_by=payload.get("created_by", ""),
            metadata=payload.get("metadata", {}),
            proposal_id=payload.get("proposal_id"),
        )
