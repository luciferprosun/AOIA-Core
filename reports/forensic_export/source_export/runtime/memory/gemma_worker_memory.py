from __future__ import annotations

from pathlib import Path
from typing import Any


class GemmaWorkerMemory:
    """Small runtime continuity store for the optional Gemma worker path."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.gemini_calls = 0
        self.gemma_calls = 0
        self.steps: list[dict[str, Any]] = []
        self.last_gemini_instruction = ""

    def record_gemini_call(self) -> None:
        self.gemini_calls += 1

    def record_gemma_call(self) -> None:
        self.gemma_calls += 1

    def remember_step(
        self,
        delegated_step: str,
        action: dict[str, Any],
        result: dict[str, Any] | None,
        gemini_instruction: str,
    ) -> None:
        self.last_gemini_instruction = gemini_instruction
        self.steps.append(
            {
                "delegated_step": delegated_step,
                "action": action,
                "result": result,
            }
        )
        self.steps = self.steps[-20:]

    def summarize_worker_state(self) -> dict[str, Any]:
        return {
            "gemini_calls": self.gemini_calls,
            "gemma_calls": self.gemma_calls,
            "last_gemini_instruction": self.last_gemini_instruction,
            "recent_steps": self.steps[-5:],
        }

