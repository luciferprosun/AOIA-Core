from __future__ import annotations

from typing import Any

from textual.widgets import Static


class ApprovalPanel(Static):
    """Visible operator approval state for risky runtime actions."""

    def render_idle(self) -> str:
        return "Approval: idle. Risky actions require explicit operator approval."

    def render_pending(self, action: dict[str, Any], timeout_seconds: int) -> str:
        lines = [
            "Approval required",
            f"action: {action.get('action', '(unknown)')}",
            f"timeout: {timeout_seconds}s",
        ]
        if action.get("reason"):
            lines.append(f"reason: {action['reason']}")
        for field in ("command", "path", "src", "dst", "url", "selector", "key"):
            value = action.get(field)
            if value:
                lines.append(f"{field}: {value}")
        lines.append("Ctrl+A approve, Ctrl+X reject")
        return "\n".join(lines)

    def set_idle(self) -> None:
        self.update(self.render_idle())

    def set_pending(self, action: dict[str, Any], timeout_seconds: int) -> None:
        self.update(self.render_pending(action, timeout_seconds))
