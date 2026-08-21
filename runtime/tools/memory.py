from __future__ import annotations

import datetime as dt
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from runtime.safety.atomic_persistence import (
    DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
    StateCorruptionError,
    append_json_line,
    atomic_write_json,
    atomic_write_text,
    locked_update_text,
    read_json_snapshot,
    state_resource_lock_path,
    validate_lock_timeout_seconds,
)
from runtime.sensitive_redaction import SensitiveValueRedactor, build_runtime_redactor
from runtime_paths import runtime_state_dir


# TRANSITIONAL MEMORY MONOLITH
# NO NEW RESPONSIBILITIES.
# Pending future authority-layer split. Keep L0/L1/L2/L4 behavior explicit here
# until memory authority boundaries are enforced by separate stores.

@dataclass
class RuntimePaths:
    project_dir: Path
    state_dir: Path
    memory_dir: Path
    screenshots_dir: Path
    browser_logs_dir: Path
    session_logs_dir: Path
    command_logs_dir: Path
    error_logs_dir: Path


@dataclass
class ObsidianVaultPaths:
    vault_dir: Path
    daily_dir: Path
    sessions_dir: Path
    inbox_dir: Path
    projects_dir: Path
    logs_dir: Path
    prompts_dir: Path
    knowledge_dir: Path
    templates_dir: Path
    evidence_dir: Path
    reasoning_dir: Path


@dataclass
class AgentMemory:
    session_id: str
    cwd: str
    current_task: str = ""
    previous_commands: list[str] = field(default_factory=list)
    recent_outputs: list[dict[str, Any]] = field(default_factory=list)
    open_tabs: list[str] = field(default_factory=list)
    current_browser_page: str = ""
    screenshots: list[str] = field(default_factory=list)
    browser_active: bool = False


def build_runtime_paths(project_dir: Path) -> RuntimePaths:
    """Create and return the directory layout for memory, browser, and logs."""
    root = runtime_state_dir(project_dir)
    paths = RuntimePaths(
        project_dir=project_dir,
        state_dir=root / "state",
        memory_dir=root / "memory",
        screenshots_dir=root / "screenshots",
        browser_logs_dir=root / "logs" / "browser",
        session_logs_dir=root / "logs" / "sessions",
        command_logs_dir=root / "logs" / "commands",
        error_logs_dir=root / "logs" / "errors",
    )
    for path in asdict(paths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    return paths


def build_obsidian_vault_paths(project_dir: Path) -> ObsidianVaultPaths:
    runtime_root = runtime_state_dir(project_dir)
    state_dir = runtime_root / "state"
    vault_dir = runtime_root / "obsidian_vault"
    paths = ObsidianVaultPaths(
        vault_dir=vault_dir,
        daily_dir=vault_dir / "Daily",
        sessions_dir=vault_dir / "Sessions",
        inbox_dir=vault_dir / "Inbox",
        projects_dir=vault_dir / "Projects",
        logs_dir=vault_dir / "Logs",
        prompts_dir=vault_dir / "Prompts",
        knowledge_dir=vault_dir / "Knowledge",
        templates_dir=vault_dir / "Templates",
        evidence_dir=vault_dir / "Evidence",
        reasoning_dir=vault_dir / "Reasoning",
    )
    for path in asdict(paths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    obsidian_config = vault_dir / ".obsidian"
    obsidian_config.mkdir(parents=True, exist_ok=True)
    app_json = obsidian_config / "app.json"
    if not app_json.exists():
        atomic_write_json(
            app_json,
            {
                "theme": "obsidian",
                "baseFontSize": 16,
                "accentColor": "",
            },
            lock_path=state_resource_lock_path(state_dir, app_json),
        )
    start_here = vault_dir / "00_START_HERE.md"
    if not start_here.exists():
        atomic_write_text(
            start_here,
            "\n".join(
                [
                    "# Obsidian Vault",
                    "",
                    "This vault stores lightweight runtime memory for the local-first agent.",
                    "",
                    "## Layout",
                    "- Daily: append-only day notes",
                    "- Sessions: append-only JSONL session records",
                    "- Inbox: manual captures",
                    "- Projects: active notes",
                ]
            ),
            lock_path=state_resource_lock_path(state_dir, start_here),
        )
    return paths


class MemoryStore:
    """Persist lightweight runtime state to disk after each step."""

    ALLOWED_EVIDENCE_KIND = "aoia_kernel_evidence"
    ALLOWED_EVIDENCE_SOURCES = {
        "aoia_kernel",
        "knowledge_router",
        "external_evidence_source",
    }

    def __init__(
        self,
        project_dir: Path,
        cwd: Path,
        *,
        initialize_vault: bool = True,
        persist_on_init: bool = True,
        record_session_start: bool = True,
        state_lock_timeout_seconds: object = DEFAULT_STATE_LOCK_TIMEOUT_SECONDS,
        redactor: SensitiveValueRedactor | None = None,
    ) -> None:
        self.redactor = redactor or build_runtime_redactor(environ=os.environ)
        self.state_lock_timeout_seconds = validate_lock_timeout_seconds(
            state_lock_timeout_seconds
        )
        self.paths = build_runtime_paths(project_dir)
        self.vault_dir = runtime_state_dir(project_dir) / "obsidian_vault"
        self.vault_paths: ObsidianVaultPaths | None = None
        if initialize_vault:
            self.ensure_obsidian_vault()
        session_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.state_file = self.paths.state_dir / "agent_state.json"
        self.history_file = self.paths.memory_dir / "history.jsonl"
        self.evidence_file = self.paths.memory_dir / "evidence_memory.jsonl"
        self.reasoning_file = self.paths.memory_dir / "reasoning_trace.jsonl"
        self.browser_log_file = self.paths.browser_logs_dir / f"browser_{session_id}.jsonl"
        self.memory = AgentMemory(session_id=session_id, cwd=str(cwd))
        # Existing snapshots are validated before a new session can replace
        # them. A malformed file is never treated as a missing/empty state.
        self.load()
        if persist_on_init:
            self.save()
        if record_session_start:
            self.append_vault_note(
                "session_start",
                {
                    "session_id": session_id,
                    "cwd": str(cwd),
                },
            )

    def ensure_obsidian_vault(self) -> ObsidianVaultPaths:
        if self.vault_paths is None:
            self.vault_paths = build_obsidian_vault_paths(self.paths.project_dir)
            self.vault_dir = self.vault_paths.vault_dir
        return self.vault_paths

    def load(self) -> AgentMemory | None:
        payload = read_json_snapshot(self.state_file)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise StateCorruptionError(
                "AOIA agent state snapshot must contain one JSON object.",
                target_path=self.state_file,
            )
        try:
            memory = AgentMemory(**payload)
            self._validate_loaded_memory(memory)
            return memory
        except (TypeError, ValueError) as exc:
            raise StateCorruptionError(
                "AOIA agent state snapshot does not match the runtime schema.",
                target_path=self.state_file,
            ) from exc

    def save(self, *, lock_timeout_seconds: object | None = None) -> None:
        timeout = (
            self.state_lock_timeout_seconds
            if lock_timeout_seconds is None
            else validate_lock_timeout_seconds(lock_timeout_seconds)
        )
        atomic_write_json(
            self.state_file,
            self.redactor.redact(asdict(self.memory)),
            lock_path=self._lock_for(self.state_file),
            lock_timeout_seconds=timeout,
        )

    def append_history(self, kind: str, payload: dict[str, Any]) -> None:
        safe_payload = self._safe_payload(payload)
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": safe_payload,
        }
        append_json_line(
            self.history_file,
            record,
            lock_path=self._lock_for(self.history_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        self.append_vault_note(kind, safe_payload)

    def append_evidence(self, kind: str, payload: dict[str, Any]) -> None:
        vault_paths = self.ensure_obsidian_vault()
        self._validate_evidence_payload(kind, payload)
        safe_payload = self._safe_payload(payload)
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": safe_payload,
        }
        append_json_line(
            self.evidence_file,
            record,
            lock_path=self._lock_for(self.evidence_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        self._append_channel_note(vault_paths.evidence_dir, kind, safe_payload)

    def _validate_evidence_payload(self, kind: str, payload: dict[str, Any]) -> None:
        if kind != self.ALLOWED_EVIDENCE_KIND:
            raise ValueError(
                f"Evidence writes are restricted to {self.ALLOWED_EVIDENCE_KIND}; got {kind}"
            )
        if not isinstance(payload, dict):
            raise TypeError("Evidence payload must be a dictionary")
        source = payload.get("source")
        fingerprint = payload.get("fingerprint")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Evidence payload must include a non-empty source identifier")
        if source.strip() not in self.ALLOWED_EVIDENCE_SOURCES:
            raise ValueError(f"Evidence source is not allowed: {source}")
        if not isinstance(fingerprint, str) or not fingerprint.strip():
            raise ValueError("Evidence payload must include a non-empty fingerprint")

    def append_reasoning(self, kind: str, payload: dict[str, Any]) -> None:
        vault_paths = self.ensure_obsidian_vault()
        safe_payload = self._safe_payload(payload)
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": safe_payload,
        }
        append_json_line(
            self.reasoning_file,
            record,
            lock_path=self._lock_for(self.reasoning_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        self._append_channel_note(vault_paths.reasoning_dir, kind, safe_payload)

    def append_browser_event(self, payload: dict[str, Any]) -> None:
        safe_payload = self._safe_payload(payload)
        append_json_line(
            self.browser_log_file,
            {
                "timestamp": dt.datetime.now().isoformat(),
                "payload": safe_payload,
            },
            lock_path=self._lock_for(self.browser_log_file),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        self.append_vault_note("browser_event", safe_payload)

    def set_current_task(self, task: str) -> None:
        self.memory.current_task = self.redactor.redact_text(task)
        self.save()

    def update_cwd(self, cwd: Path) -> None:
        self.memory.cwd = self.redactor.redact_text(cwd)
        self.save()

    def record_command(self, command: str) -> None:
        self.memory.previous_commands.append(self.redactor.redact_text(command))
        self.memory.previous_commands = self.memory.previous_commands[-20:]
        self.save()

    def record_result(self, result: dict[str, Any]) -> None:
        safe_result = self._safe_payload(result)
        compact = {
            "success": safe_result.get("success", False),
            "message": safe_result.get("message", ""),
            "path": safe_result.get("path"),
            "current_url": safe_result.get("current_url"),
            "exit_code": safe_result.get("exit_code"),
        }
        self.memory.recent_outputs.append(compact)
        self.memory.recent_outputs = self.memory.recent_outputs[-20:]

        if "current_url" in safe_result:
            self.memory.current_browser_page = safe_result.get("current_url", "")
        if "open_tabs" in safe_result:
            self.memory.open_tabs = safe_result.get("open_tabs", [])
            self.memory.browser_active = bool(self.memory.open_tabs or self.memory.current_browser_page)
        if "screenshot_path" in safe_result:
            self.memory.screenshots.append(safe_result["screenshot_path"])
            self.memory.screenshots = self.memory.screenshots[-20:]

        self.save()

    def append_vault_note(self, kind: str, payload: dict[str, Any]) -> None:
        vault_paths = self.ensure_obsidian_vault()
        safe_payload = self._safe_payload(payload)
        day = dt.datetime.now().strftime("%Y-%m-%d")
        note_path = vault_paths.daily_dir / f"{day}.md"
        session_path = vault_paths.sessions_dir / f"{self.memory.session_id}.jsonl"
        block = self._vault_block(kind, safe_payload)
        locked_update_text(
            note_path,
            lambda current: current + block,
            default_text=f"# {day}\n\n",
            lock_path=self._lock_for(note_path),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )
        append_json_line(
            session_path,
            {
                "timestamp": dt.datetime.now().isoformat(),
                "kind": kind,
                "payload": safe_payload,
                "cwd": self.redactor.redact_text(self.memory.cwd),
                "task": self.redactor.redact_text(self.memory.current_task),
            },
            lock_path=self._lock_for(session_path),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )

    def _append_channel_note(self, directory: Path, kind: str, payload: dict[str, Any]) -> None:
        safe_payload = self._safe_payload(payload)
        note_path = directory / f"{self.memory.session_id}.md"
        header = f"# {directory.name} {self.memory.session_id}\n\n"
        block = self._vault_block(kind, safe_payload)
        locked_update_text(
            note_path,
            lambda current: current + block,
            default_text=header,
            lock_path=self._lock_for(note_path),
            lock_timeout_seconds=self.state_lock_timeout_seconds,
        )

    def _lock_for(self, resource_path: Path) -> Path:
        return state_resource_lock_path(self.paths.state_dir, resource_path)

    def _safe_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        redacted = self.redactor.redact(payload)
        if not isinstance(redacted, dict):  # defensive type boundary
            raise TypeError("Memory payload must remain a dictionary")
        return redacted

    @staticmethod
    def _validate_loaded_memory(memory: AgentMemory) -> None:
        text_fields = (
            memory.session_id,
            memory.cwd,
            memory.current_task,
            memory.current_browser_page,
        )
        if any(not isinstance(value, str) for value in text_fields):
            raise TypeError("agent state text fields must be strings")
        string_lists = (
            memory.previous_commands,
            memory.open_tabs,
            memory.screenshots,
        )
        if any(
            not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for values in string_lists
        ):
            raise TypeError("agent state string-list fields are invalid")
        if not isinstance(memory.recent_outputs, list) or any(
            not isinstance(value, dict) for value in memory.recent_outputs
        ):
            raise TypeError("agent state recent_outputs must be a list of objects")
        if not isinstance(memory.browser_active, bool):
            raise TypeError("agent state browser_active must be boolean")

    def _vault_block(self, kind: str, payload: dict[str, Any]) -> str:
        summary = payload.get("message") or payload.get("summary") or payload.get("error") or ""
        return "\n".join(
            [
                f"## {dt.datetime.now().isoformat()} - {kind}",
                f"- cwd: {self.redactor.redact_text(self.memory.cwd)}",
                f"- task: {self.redactor.redact_text(self.memory.current_task) or '(none)'}",
                f"- note: {self.redactor.redact_text(summary).strip()[:600] or '(empty)'}",
                "",
            ]
        )
