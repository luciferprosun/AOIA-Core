from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from .browser_tools import (
    browser_click,
    browser_close,
    browser_current_url,
    browser_get_visible_text,
    browser_open,
    browser_press,
    browser_read_html,
    browser_screenshot,
    browser_start,
    browser_type,
    configure_browser_bridge,
)
from .filesystem_tools import (
    FilesystemContainmentError,
    append_file,
    canonical_project_root,
    create_file,
    create_folder,
    delete_file,
    move_file,
    read_file,
    resolve_path,
    search_in_project,
    write_file,
)
from .memory import MemoryStore
from .project_scanner import scan_project
from .shell_tools import (
    _legacy_shell_execution_enabled,
    shell_execute,
    shell_execution_blocked_result,
)
from .validator import classify_shell_command, validate_shell_command


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    """Runtime tool metadata used by the executor registry."""

    name: str
    handler: ToolHandler
    description: str


class ExecutionEngine:
    """Dispatch structured legacy tool actions; execution surfaces are frozen by default."""

    def __init__(self, project_dir: Path, memory_store: MemoryStore) -> None:
        self.project_dir = canonical_project_root(project_dir)
        self.memory_store = memory_store
        self.cwd = resolve_path(
            memory_store.memory.cwd,
            self.project_dir,
            self.project_dir,
            operation="runtime working-directory initialization",
        )
        self.command_log_dir = memory_store.paths.command_logs_dir
        configure_browser_bridge(
            user_data_dir=memory_store.paths.state_dir / "browser_profile",
            screenshots_dir=memory_store.paths.screenshots_dir,
            headless=True,
        )
        self.tools = self._build_tool_registry()

    def tool_names(self) -> list[str]:
        return sorted(self.tools)

    def execute(self, action: dict[str, Any], require_approval: bool = True) -> dict[str, Any]:
        """Execute one validated JSON action."""
        name = action["action"]
        tool = self.tools.get(name)
        if tool is None:
            raise ValueError(f"Unhandled action: {name}")

        needs_approval = bool(action.get("requires_confirmation", False))
        if name == "shell_execute":
            needs_approval = needs_approval or classify_shell_command(action.get("command", "")).requires_confirmation

        if require_approval and name != "respond" and needs_approval:
            approved = self._request_approval(action)
            if not approved:
                result = {
                    "success": False,
                    "cancelled": True,
                    "message": "Action rejected by user.",
                    "action": name,
                }
                self._record_execution(action, result)
                return result

        result = tool.handler(action)
        self._record_execution(action, result)
        return result

    def _build_tool_registry(self) -> dict[str, ToolSpec]:
        return {
            "respond": ToolSpec("respond", self._respond, "Return a final answer."),
            "shell_execute": ToolSpec("shell_execute", self._execute_shell_action, "Frozen legacy shell/executor surface."),
            "write_file": ToolSpec(
                "write_file",
                lambda action: write_file(
                    action["path"], action["content"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "append_file": ToolSpec(
                "append_file",
                lambda action: append_file(
                    action["path"], action["content"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "read_file": ToolSpec(
                "read_file",
                lambda action: read_file(action["path"], self.cwd, self.project_dir),
                "Read a text file.",
            ),
            "create_file": ToolSpec(
                "create_file",
                lambda action: create_file(
                    action["path"], self.cwd, action["content"], self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "create_folder": ToolSpec(
                "create_folder",
                lambda action: create_folder(action["path"], self.cwd, self.project_dir),
                "Frozen legacy filesystem surface.",
            ),
            "move_file": ToolSpec(
                "move_file",
                lambda action: move_file(
                    action["src"], action["dst"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "delete_file": ToolSpec(
                "delete_file",
                lambda action: delete_file(action["path"], self.cwd, self.project_dir),
                "Frozen legacy filesystem surface.",
            ),
            "search_in_project": ToolSpec(
                "search_in_project",
                lambda action: search_in_project(
                    action["pattern"], action["path"], self.cwd, self.project_dir
                ),
                "Search text in project files.",
            ),
            "change_directory": ToolSpec("change_directory", lambda action: self._change_directory(action["path"]), "Change runtime directory."),
            "browser_start": ToolSpec("browser_start", lambda action: browser_start(), "Frozen legacy browser surface."),
            "browser_open": ToolSpec(
                "browser_open",
                lambda action: self._browser_open(action["url"]),
                "Frozen legacy browser surface.",
            ),
            "browser_click": ToolSpec("browser_click", lambda action: browser_click(action["selector"]), "Frozen legacy browser surface."),
            "browser_type": ToolSpec("browser_type", lambda action: browser_type(action["selector"], action["text"]), "Frozen legacy browser surface."),
            "browser_press": ToolSpec("browser_press", lambda action: browser_press(action["key"]), "Frozen legacy browser surface."),
            "browser_read_html": ToolSpec("browser_read_html", lambda action: browser_read_html(), "Frozen legacy browser surface."),
            "browser_get_visible_text": ToolSpec("browser_get_visible_text", lambda action: browser_get_visible_text(), "Frozen legacy browser surface."),
            "browser_screenshot": ToolSpec(
                "browser_screenshot",
                lambda action: self._browser_screenshot(action.get("path") or None),
                "Frozen legacy browser surface.",
            ),
            "browser_close": ToolSpec("browser_close", lambda action: browser_close(), "Frozen legacy browser surface."),
            "browser_current_url": ToolSpec("browser_current_url", lambda action: browser_current_url(), "Frozen legacy browser surface."),
            "scan_project": ToolSpec(
                "scan_project",
                lambda action: scan_project(action["path"], self.cwd, self.project_dir),
                "Scan a repository or project tree.",
            ),
        }

    @staticmethod
    def _respond(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "message": action["message"],
            "confidence_label": action.get("confidence_label", "unknown"),
            "stop_loop": True,
        }

    def _execute_shell_action(self, action: dict[str, Any]) -> dict[str, Any]:
        command = action["command"]
        if not _legacy_shell_execution_enabled():
            return shell_execution_blocked_result(command, self.cwd)

        allowed, reason = validate_shell_command(command)
        if not allowed:
            return {
                "success": False,
                "command": command,
                "message": f"Command blocked by validator: {reason}",
            }

        permission = classify_shell_command(command)
        if permission.interactive:
            print("[INFO] Interactive command may ask for password or package confirmation.")

        self.memory_store.record_command(command)
        return {
            **shell_execute(command, self.cwd, interactive=permission.interactive),
            "permission_mode": permission.mode,
            "permission_reason": permission.reason,
        }

    def _request_approval(self, action: dict[str, Any]) -> bool:
        print("\nPROPOSED ACTION")
        print(f"Action: {action['action']}")
        if action.get("reason"):
            print(f"Reason: {action['reason']}")
        for field in ("command", "path", "src", "dst", "url", "selector", "key"):
            if field in action and action[field]:
                print(f"{field}: {action[field]}")
        answer = input("Press ENTER to approve, or type n/cancel to reject: ").strip().lower()
        return answer not in {"n", "no", "cancel", "reject", "stop"}

    def _change_directory(self, path_text: str) -> dict:
        target = resolve_path(
            path_text,
            self.cwd,
            self.project_dir,
            operation="change_directory",
        )
        if not target.exists() or not target.is_dir():
            return {
                "success": False,
                "path": str(target),
                "message": f"Directory does not exist: {target}",
            }
        self.cwd = target
        self.memory_store.update_cwd(target)
        return {
            "success": True,
            "path": str(target),
            "message": f"Current directory changed to {target}",
        }

    def _browser_open(self, url: str) -> dict:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "file":
            return browser_open(url)
        if parsed.netloc not in {"", "localhost"}:
            raise FilesystemContainmentError(
                "Filesystem containment blocked browser_open: unsupported file URL."
            )
        local_path = resolve_path(
            unquote(parsed.path),
            self.cwd,
            self.project_dir,
            operation="browser_open local file",
        )
        return browser_open(local_path.as_uri())

    def _browser_screenshot(self, path_text: str | None) -> dict:
        if path_text is None:
            return browser_screenshot()
        target = resolve_path(
            path_text,
            self.cwd,
            self.project_dir,
            operation="browser_screenshot",
        )
        return browser_screenshot(str(target))

    def _record_execution(self, action: dict[str, Any], result: dict[str, Any]) -> None:
        payload = {
            "timestamp": dt.datetime.now().isoformat(),
            "authority": {
                "classification": "operational_event",
                "retention": "replay_only",
                "non_authoritative": True,
                "canonical_evidence": False,
            },
            "action": action,
            "result": result,
            "cwd": str(self.cwd),
        }
        filename = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f.json")
        (self.command_log_dir / filename).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.memory_store.record_result(result)
        self.memory_store.append_history("action_result", payload)
        # AOIA Phase 2A containment boundary
        # Runtime operational outputs must NEVER become canonical evidence.
        if action["action"].startswith("browser_"):
            self.memory_store.append_browser_event(payload)
