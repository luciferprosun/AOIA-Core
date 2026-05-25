from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.widgets import Static


SAFE_EVENT_KINDS = {
    "action_result",
    "local_route_result",
    "knowledge_route_hit",
    "knowledge_route_miss",
    "aoia_kernel_hit",
    "external_link_review",
    "external_repository_review",
    "planned_step_result",
    "step_result",
    "orchestrated_step_result",
    "tui_operator_request",
    "tui_approval_decision",
}


class LogPanel(Static):
    """Replay-only operational log panel.

    This intentionally excludes raw prompts, model internals, and reasoning
    traces. It displays only safe operational telemetry from session logs.
    """

    max_lines = 14

    def safe_tail(self, session_log: str | Path | None) -> str:
        if not session_log:
            return "No session log selected."
        path = Path(session_log)
        if not path.exists():
            return f"Waiting for session log: {path}"

        rows: list[str] = []
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-80:]:
            try:
                payload: dict[str, Any] = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            kind = str(payload.get("kind", ""))
            if kind not in SAFE_EVENT_KINDS:
                continue
            timestamp = str(payload.get("timestamp", ""))[:19]
            event_payload = payload.get("payload", {})
            if not isinstance(event_payload, dict):
                event_payload = {}
            summary = self._summarize_event(kind, event_payload)
            rows.append(f"{timestamp} {kind}: {summary}")
        return "\n".join(rows[-self.max_lines :]) if rows else "No safe operational events yet."

    def update_from_status(self, status: dict[str, Any]) -> None:
        self.update(self.safe_tail(status.get("session_log")))

    @staticmethod
    def _summarize_event(kind: str, payload: dict[str, Any]) -> str:
        if "confidence" in payload:
            return f"confidence={payload.get('confidence')} reason={payload.get('reason', '')}"
        if kind == "tui_operator_request":
            return f"length={payload.get('length')} slash_command={payload.get('slash_command')}"
        if kind == "tui_approval_decision":
            return f"action={payload.get('action')} approved={payload.get('approved')}"
        action = payload.get("action", {})
        result = payload.get("result", {})
        if isinstance(action, dict) or isinstance(result, dict):
            action_name = action.get("action", "(unknown)") if isinstance(action, dict) else "(unknown)"
            success = result.get("success", "?") if isinstance(result, dict) else "?"
            message = result.get("message", "") if isinstance(result, dict) else ""
            return f"action={action_name} success={success} {message}".strip()
        return kind
