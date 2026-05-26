from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


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
    paths = RuntimePaths(
        project_dir=project_dir,
        state_dir=project_dir / "state",
        memory_dir=project_dir / "memory",
        screenshots_dir=project_dir / "screenshots",
        browser_logs_dir=project_dir / "logs" / "browser",
        session_logs_dir=project_dir / "logs" / "sessions",
        command_logs_dir=project_dir / "logs" / "commands",
        error_logs_dir=project_dir / "logs" / "errors",
    )
    for path in asdict(paths).values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    return paths


def build_obsidian_vault_paths(project_dir: Path) -> ObsidianVaultPaths:
    vault_dir = project_dir / "obsidian_vault"
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
        app_json.write_text(
            json.dumps(
                {
                    "theme": "obsidian",
                    "baseFontSize": 16,
                    "accentColor": "",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    start_here = vault_dir / "00_START_HERE.md"
    if not start_here.exists():
        start_here.write_text(
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
            encoding="utf-8",
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

    def __init__(self, project_dir: Path, cwd: Path) -> None:
        self.paths = build_runtime_paths(project_dir)
        self.vault_paths = build_obsidian_vault_paths(project_dir)
        self.vault_dir = self.vault_paths.vault_dir
        session_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.state_file = self.paths.state_dir / "agent_state.json"
        self.history_file = self.paths.memory_dir / "history.jsonl"
        self.evidence_file = self.paths.memory_dir / "evidence_memory.jsonl"
        self.reasoning_file = self.paths.memory_dir / "reasoning_trace.jsonl"
        self.browser_log_file = self.paths.browser_logs_dir / f"browser_{session_id}.jsonl"
        self.memory = AgentMemory(session_id=session_id, cwd=str(cwd))
        self.save()
        self.append_vault_note(
            "session_start",
            {
                "session_id": session_id,
                "cwd": str(cwd),
            },
        )

    def save(self) -> None:
        self.state_file.write_text(
            json.dumps(asdict(self.memory), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def append_history(self, kind: str, payload: dict[str, Any]) -> None:
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.history_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.append_vault_note(kind, payload)

    def append_evidence(self, kind: str, payload: dict[str, Any]) -> None:
        self._validate_evidence_payload(kind, payload)
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.evidence_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._append_channel_note(self.vault_paths.evidence_dir, kind, payload)

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
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.reasoning_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._append_channel_note(self.vault_paths.reasoning_dir, kind, payload)

    def append_browser_event(self, payload: dict[str, Any]) -> None:
        with self.browser_log_file.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp": dt.datetime.now().isoformat(),
                        "payload": payload,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        self.append_vault_note("browser_event", payload)

    def set_current_task(self, task: str) -> None:
        self.memory.current_task = task
        self.save()

    def update_cwd(self, cwd: Path) -> None:
        self.memory.cwd = str(cwd)
        self.save()

    def record_command(self, command: str) -> None:
        self.memory.previous_commands.append(command)
        self.memory.previous_commands = self.memory.previous_commands[-20:]
        self.save()

    def record_result(self, result: dict[str, Any]) -> None:
        compact = {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "path": result.get("path"),
            "current_url": result.get("current_url"),
            "exit_code": result.get("exit_code"),
        }
        self.memory.recent_outputs.append(compact)
        self.memory.recent_outputs = self.memory.recent_outputs[-20:]

        if "current_url" in result:
            self.memory.current_browser_page = result.get("current_url", "")
        if "open_tabs" in result:
            self.memory.open_tabs = result.get("open_tabs", [])
            self.memory.browser_active = bool(self.memory.open_tabs or self.memory.current_browser_page)
        if "screenshot_path" in result:
            self.memory.screenshots.append(result["screenshot_path"])
            self.memory.screenshots = self.memory.screenshots[-20:]

        self.save()

    def append_vault_note(self, kind: str, payload: dict[str, Any]) -> None:
        day = dt.datetime.now().strftime("%Y-%m-%d")
        note_path = self.vault_paths.daily_dir / f"{day}.md"
        session_path = self.vault_paths.sessions_dir / f"{self.memory.session_id}.jsonl"
        block = self._vault_block(kind, payload)
        note_path.write_text(
            (note_path.read_text(encoding="utf-8") if note_path.exists() else f"# {day}\n\n")
            + block,
            encoding="utf-8",
        )
        with session_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp": dt.datetime.now().isoformat(),
                        "kind": kind,
                        "payload": payload,
                        "cwd": self.memory.cwd,
                        "task": self.memory.current_task,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def _append_channel_note(self, directory: Path, kind: str, payload: dict[str, Any]) -> None:
        note_path = directory / f"{self.memory.session_id}.md"
        header = f"# {directory.name} {self.memory.session_id}\n\n"
        note_path.write_text(
            (note_path.read_text(encoding="utf-8") if note_path.exists() else header)
            + self._vault_block(kind, payload),
            encoding="utf-8",
        )

    def _vault_block(self, kind: str, payload: dict[str, Any]) -> str:
        summary = payload.get("message") or payload.get("summary") or payload.get("error") or ""
        return "\n".join(
            [
                f"## {dt.datetime.now().isoformat()} - {kind}",
                f"- cwd: {self.memory.cwd}",
                f"- task: {self.memory.current_task or '(none)'}",
                f"- note: {str(summary).strip()[:600] or '(empty)'}",
                "",
            ]
        )
