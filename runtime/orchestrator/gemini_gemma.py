from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from memory.rhcsa_context import (
    inject_linux_context,
    retrieve_command_patterns,
    retrieve_operational_examples,
)
from tools.memory_hats import MemoryHatStore
from tools.validator import extract_json_object, validate_action


class GeminiGemmaOrchestrator:
    """Delegates strategic planning to Gemini and action generation to Gemma."""

    def __init__(
        self,
        provider_manager: Any,
        worker_memory: Any,
        hat_store: MemoryHatStore,
        project_dir: Path,
        desktop_dir: Path,
        max_steps: int = 8,
    ) -> None:
        self.provider_manager = provider_manager
        self.worker_memory = worker_memory
        self.hat_store = hat_store
        self.project_dir = project_dir
        self.desktop_dir = desktop_dir
        self.max_steps = max_steps
        self.gemma_provider = None

    def create_plan(self, user_request: str, runtime_status: dict[str, Any]) -> dict[str, Any]:
        self.worker_memory.record_gemini_call()
        prompt = self._build_gemini_planner_prompt(user_request, runtime_status)
        raw = self.provider_manager.generate_with_fallback(prompt)
        payload = extract_json_object(raw)
        raw_steps = payload.get("steps", payload.get("plan", []))
        if not isinstance(raw_steps, list):
            raw_steps = []
        steps = [str(step).strip() for step in raw_steps if str(step).strip()][: self.max_steps]
        if not steps and payload.get("message"):
            steps = [f"respond to user: {payload['message']}"]
        return {
            "strategy": str(payload.get("strategy", "")).strip(),
            "steps": steps,
            "raw": raw,
        }

    def action_for_step(
        self,
        user_request: str,
        step: str,
        runtime_status: dict[str, Any],
        previous_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if self.gemma_provider is None:
            raise RuntimeError("Gemma/Ollama/HuggingFace worker is disabled in this terminal build.")
        self.worker_memory.record_gemma_call()
        prompt = self._build_gemma_worker_prompt(user_request, step, runtime_status, previous_results)
        raw = self.gemma_provider.generate(prompt)
        action = validate_action(extract_json_object(raw))
        self.worker_memory.remember_step(
            delegated_step=step,
            action=action,
            result=None,
            gemini_instruction=runtime_status.get("current_task", user_request),
        )
        return action

    def fallback_action_for_step(
        self,
        user_request: str,
        step: str,
        previous_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a conservative action if Gemma is unavailable."""
        lower = step.lower()
        if "scan" in lower or "inspect" in lower or "repository" in lower or "project" in lower:
            return {
                "action": "scan_project",
                "path": str(self.project_dir),
                "reason": f"Fallback action for delegated step: {step}",
            }
        if "folder" in lower and "desktop" in lower:
            return {
                "action": "create_folder",
                "path": str(self.desktop_dir / "AI_PROJECT"),
                "reason": f"Fallback action for delegated step: {step}",
            }
        repeated_step = bool(previous_results and step == previous_results[-1].get("step", ""))
        if "respond" in lower or repeated_step:
            return {
                "action": "respond",
                "message": "Delegated plan step completed as far as the available tools allowed.",
                "reason": f"Fallback response for delegated step: {step}",
            }
        return {
            "action": "respond",
            "message": f"Gemma worker is unavailable. Planned step needs manual follow-up: {step}",
            "reason": "Fallback response because no worker model produced a valid JSON action.",
        }

    def record_result(self, step: str, action: dict[str, Any], result: dict[str, Any]) -> None:
        self.worker_memory.remember_step(
            delegated_step=step,
            action=action,
            result=result,
            gemini_instruction=self.worker_memory.last_gemini_instruction,
        )

    def error_payload(self, error: Exception) -> dict[str, str]:
        return {
            "error": str(error),
            "traceback": traceback.format_exc(),
        }

    def _build_gemini_planner_prompt(self, user_request: str, runtime_status: dict[str, Any]) -> str:
        hat = self.hat_store.prompt_block()
        payload = {
            "role": "Gemini Brain / Teacher / Planner",
            "task": user_request,
            "runtime_status": {
                "cwd": runtime_status.get("cwd"),
                "desktop_dir": runtime_status.get("desktop_dir"),
                "active_memory_hat": hat,
                "rhcsa_context": inject_linux_context(user_request, max_chars=3000),
                "recent_outputs": runtime_status.get("recent_outputs", [])[-4:],
            },
            "instruction": (
                "Create a short strategic plan. Do not generate executable JSON actions. "
                "Return JSON only: {\"strategy\":\"...\",\"steps\":[\"step 1\", \"step 2\"]}. "
                "Gemma worker will convert one step at a time into approved executable actions."
            ),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def _build_gemma_worker_prompt(
        self,
        user_request: str,
        step: str,
        runtime_status: dict[str, Any],
        previous_results: list[dict[str, Any]],
    ) -> str:
        payload = {
            "role": "Gemma Worker / Executor JSON Action Generator",
            "user_request": user_request,
            "delegated_step": step,
            "worker_memory": self.worker_memory.summarize_worker_state(),
            "operational_command_patterns": retrieve_command_patterns(
                f"{user_request} {step}",
                limit=8,
            ),
            "operational_examples": retrieve_operational_examples(
                f"{user_request} {step}",
                limit=3,
            ),
            "runtime": {
                "cwd": runtime_status.get("cwd"),
                "desktop_dir": runtime_status.get("desktop_dir"),
                "project_dir": str(self.project_dir),
                "tools": runtime_status.get("tools", []),
            },
            "previous_results": previous_results[-3:],
            "instruction": (
                "Convert the delegated step into exactly one valid action JSON object. "
                "Use only the available tool names. Do not explain. Do not use markdown. "
                "Runtime capability policy independently decides whether human ENTER approval "
                "is required; you may request more confirmation but cannot reduce that policy."
            ),
            "examples": [
                {"action": "scan_project", "path": str(self.project_dir), "reason": "Inspect repository structure."},
                {"action": "create_folder", "path": str(self.desktop_dir / "test_ai"), "reason": "Create requested folder."},
                {"action": "respond", "message": "Task complete.", "reason": "No more actions are required."},
            ],
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
