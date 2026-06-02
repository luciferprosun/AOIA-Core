from __future__ import annotations

from dataclasses import dataclass

from runtime.schemas.command_proposal import APPROVAL_STATES


@dataclass(frozen=True)
class ApprovalDecision:
    allowed: bool
    approval_state: str
    reason: str
    dry_run: bool
    requires_human_review: bool
    execution_permitted: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.allowed, bool):
            raise TypeError("allowed must be bool")
        if self.approval_state not in APPROVAL_STATES:
            raise ValueError("approval_state must be one of the allowed values")
        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")
        if not isinstance(self.dry_run, bool):
            raise TypeError("dry_run must be bool")
        if not isinstance(self.requires_human_review, bool):
            raise TypeError("requires_human_review must be bool")
        if not isinstance(self.execution_permitted, bool):
            raise TypeError("execution_permitted must be bool")
        if self.execution_permitted:
            raise ValueError("execution_permitted must remain False in GT-RUNTIME-8E")
        if (
            self.approval_state == "not_required"
            and self.requires_human_review
        ):
            raise ValueError(
                "requires_human_review must be False when approval_state is not_required"
            )
        if (
            self.approval_state == "requires_human_review"
            and not self.requires_human_review
        ):
            raise ValueError(
                "requires_human_review must be True when approval_state is requires_human_review"
            )
