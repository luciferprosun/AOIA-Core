from __future__ import annotations

from typing import Any

from textual.widgets import Static


class RuntimeStatusBar(Static):
    """Persistent compact runtime status bar."""

    def render_status_bar(self, status: dict[str, Any]) -> str:
        knowledge = status.get("knowledge_routing", {})
        safeguards = status.get("epistemic_safeguards", {})
        return " | ".join(
            [
                f"provider={status.get('model', '(unknown)')}",
                f"retrieval={'on' if knowledge.get('enabled') else 'off'}",
                "approval=operator",
                f"cwd={status.get('cwd', '(unknown)')}",
                f"log={status.get('session_log', '(unknown)')}",
                f"model_disabled={safeguards.get('disable_model')}",
            ]
        )

    def update_status(self, status: dict[str, Any]) -> None:
        self.update(self.render_status_bar(status))
