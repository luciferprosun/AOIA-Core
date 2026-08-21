from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from runtime.sensitive_redaction import (
    SensitiveValueRedactor,
    build_current_runtime_redactor,
)


class GemmaWorkerMemory:
    """Small runtime continuity store for the optional Gemma worker path."""

    def __init__(
        self,
        project_dir: Path,
        *,
        redactor: SensitiveValueRedactor | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.redactor = redactor or build_current_runtime_redactor(environ=os.environ)
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
        self.last_gemini_instruction = self.redactor.redact_text(gemini_instruction)
        safe_step = self.redactor.redact(
            {
                "delegated_step": delegated_step,
                "action": action,
                "result": result,
            }
        )
        if not isinstance(safe_step, dict):
            raise TypeError("Worker memory step must remain a dictionary")
        self.steps.append(safe_step)
        self.steps = self.steps[-20:]

    def summarize_worker_state(self) -> dict[str, Any]:
        summary = {
            "gemini_calls": self.gemini_calls,
            "gemma_calls": self.gemma_calls,
            "last_gemini_instruction": self.last_gemini_instruction,
            "recent_steps": self.steps[-5:],
        }
        redacted = self.redactor.redact(summary)
        if not isinstance(redacted, dict):
            raise TypeError("Worker memory summary must remain a dictionary")
        return redacted
