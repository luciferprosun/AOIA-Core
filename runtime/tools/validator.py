from __future__ import annotations

import json
import re
from dataclasses import dataclass
from json import JSONDecodeError


ALLOWED_ACTIONS = {
    "respond",
    "shell_execute",
    "write_file",
    "append_file",
    "read_file",
    "create_file",
    "create_folder",
    "move_file",
    "delete_file",
    "search_in_project",
    "change_directory",
    "browser_start",
    "browser_open",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_read_html",
    "browser_get_visible_text",
    "browser_screenshot",
    "browser_close",
    "browser_current_url",
    "scan_project",
}

BLOCKED_SHELL_PATTERNS = (
    "\x00",
    "$(",
    "`",
    "<<",
    "<(",
    ">(",
    ":(){ :|:& };:",
    "rm -rf /",
    "curl | bash",
    "curl|bash",
    "wget -o-",
    "wget -O-",
)

CONFIRMATION_PATTERNS = (
    "sudo ",
    "apt install",
    "apt-get install",
    "pip install",
    "pip3 install",
    "npm install",
)

DANGEROUS_PATTERNS = (
    "rm -rf /",
    ":(){ :|:& };:",
    "chmod -r /",
    "chmod -R /",
    "chown -r /",
    "chown -R /",
    "mkfs",
    "dd ",
    "shutdown",
    "reboot",
)

ALLOWED_CONFIDENCE_LABELS = {"high", "medium", "low", "unknown"}


@dataclass
class PermissionDecision:
    mode: str
    requires_confirmation: bool
    interactive: bool
    reason: str


@dataclass(frozen=True)
class RespondShellSafetyResult:
    safe: bool
    warnings: list[str]
    matched_patterns: list[str]
    sanitized_message: str


def extract_json_object(raw_text: str) -> dict:
    """Extract one JSON object from model output."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data
    except JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(raw_text[index:])
        except JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data

    raise ValueError(f"Invalid JSON action payload: {raw_text}")


def validate_action(action: dict) -> dict:
    """Validate and normalize model-generated actions."""
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object.")

    name = str(action.get("action") or action.get("type") or "").strip()
    if name == "terminal_command":
        name = "shell_execute"
    if name not in ALLOWED_ACTIONS:
        raise ValueError(f"Unsupported action: {name}")

    normalized = dict(action)
    normalized["action"] = name
    normalized["reason"] = str(action.get("reason", "")).strip()
    normalized["requires_confirmation"] = bool(action.get("requires_confirmation", False))
    confidence = str(action.get("confidence", action.get("confidence_label", "unknown"))).strip().lower()
    normalized["confidence_label"] = confidence if confidence in ALLOWED_CONFIDENCE_LABELS else "unknown"

    if name == "respond":
        normalized["message"] = str(action.get("message", "")).strip()
        if not normalized["message"]:
            raise ValueError("respond requires a non-empty message.")
        return normalized

    if name == "shell_execute":
        normalized["command"] = str(action.get("command", "")).strip()
        if not normalized["command"]:
            raise ValueError("shell_execute requires a command.")
        return normalized

    if name in {"write_file", "append_file", "create_file"}:
        normalized["path"] = str(action.get("path", "")).strip()
        normalized["content"] = str(action.get("content", ""))
        if not normalized["path"]:
            raise ValueError(f"{name} requires a path.")
        return normalized

    if name in {"read_file", "create_folder", "delete_file", "change_directory"}:
        normalized["path"] = str(action.get("path", "")).strip()
        if not normalized["path"]:
            raise ValueError(f"{name} requires a path.")
        return normalized

    if name == "move_file":
        normalized["src"] = str(action.get("src", "")).strip()
        normalized["dst"] = str(action.get("dst", "")).strip()
        if not normalized["src"] or not normalized["dst"]:
            raise ValueError("move_file requires src and dst.")
        return normalized

    if name == "search_in_project":
        normalized["path"] = str(action.get("path", ".")).strip() or "."
        normalized["pattern"] = str(action.get("pattern", "")).strip()
        if not normalized["pattern"]:
            raise ValueError("search_in_project requires pattern.")
        return normalized

    if name == "scan_project":
        normalized["path"] = str(action.get("path", ".")).strip() or "."
        return normalized

    if name == "browser_open":
        normalized["url"] = str(action.get("url", "")).strip()
        if not normalized["url"]:
            raise ValueError("browser_open requires url.")
        return normalized

    if name in {"browser_click"}:
        normalized["selector"] = str(action.get("selector", "")).strip()
        if not normalized["selector"]:
            raise ValueError(f"{name} requires selector.")
        return normalized

    if name in {"browser_type"}:
        normalized["selector"] = str(action.get("selector", "")).strip()
        normalized["text"] = str(action.get("text", ""))
        if not normalized["selector"]:
            raise ValueError("browser_type requires selector.")
        return normalized

    if name in {"browser_press"}:
        normalized["key"] = str(action.get("key", "")).strip()
        if not normalized["key"]:
            raise ValueError("browser_press requires key.")
        return normalized

    if name in {"browser_screenshot"}:
        normalized["path"] = str(action.get("path", "")).strip()
        return normalized

    return normalized


def validate_shell_command(command: str) -> tuple[bool, str]:
    """Allow multi-step commands while blocking dangerous shell constructs."""
    stripped = command.strip()
    if not stripped:
        return False, "Empty command."
    if "\r" in stripped or "\x00" in stripped:
        return False, "Control characters are not allowed."
    if "\n" in stripped:
        return False, "Multiline commands are not allowed."

    lowered = stripped.lower()
    for pattern in BLOCKED_SHELL_PATTERNS:
        if pattern.lower() in lowered:
            return False, f"Blocked shell pattern: {pattern}"

    return True, "OK"


def classify_shell_command(command: str) -> PermissionDecision:
    """Classify commands into safe, advanced, and dangerous execution modes."""
    lowered = command.lower().strip()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in lowered:
            return PermissionDecision(
                mode="dangerous",
                requires_confirmation=True,
                interactive="sudo" in lowered,
                reason=f"Dangerous pattern detected: {pattern}",
            )

    for pattern in CONFIRMATION_PATTERNS:
        if pattern in lowered:
            return PermissionDecision(
                mode="advanced",
                requires_confirmation=True,
                interactive="sudo" in lowered or "apt " in lowered or "apt-get " in lowered,
                reason=f"Confirmation required for: {pattern}",
            )

    if any(operator in command for operator in ("&&", ";", "|")):
        return PermissionDecision(
            mode="advanced",
            requires_confirmation=True,
            interactive=False,
            reason="Multi-step command requires confirmation",
        )

    return PermissionDecision(
        mode="safe",
        requires_confirmation=False,
        interactive=False,
        reason="Safe command",
    )


def inspect_respond_shell_safety(message: str) -> RespondShellSafetyResult:
    """Detect shell advice that is risky even when the runtime will not execute it."""
    text = str(message)
    lowered = text.lower()
    warnings: list[str] = []
    matched_patterns: list[str] = []

    def add(pattern: str, warning: str) -> None:
        if pattern not in matched_patterns:
            matched_patterns.append(pattern)
        if warning not in warnings:
            warnings.append(warning)

    has_find_print0_substitution = "$(" in lowered and "find" in lowered and "-print0" in lowered
    if has_find_print0_substitution:
        add(
            "find_print0_command_substitution",
            (
                "Do not place NUL-delimited find -print0 output inside shell command "
                "substitution. Use a NUL-safe pipeline such as find ... -print0 | "
                "tar --null --files-from=-."
            ),
        )

    if "tar" in lowered and has_find_print0_substitution:
        add(
            "tar_find_print0_command_substitution",
            "tar archives should consume NUL-delimited input with --null and --files-from=-.",
        )

    if re.search(r"\brm\s+-[^\n;|&]*r[^\n;|&]*f[^\n;|&]*(?:/|\*)", lowered):
        add("rm_rf_destructive_target", "This response contains rm -rf targeting / or *.")

    if re.search(r"\bmkfs(?:\.[a-z0-9]+)?\b", lowered):
        add("mkfs_filesystem_format", "mkfs formats filesystems and can destroy data.")

    if re.search(r"\bdd\b(?=[^\n]*\bif=)(?=[^\n]*\bof=)", lowered):
        add("dd_if_of_raw_copy", "dd with both if= and of= can overwrite disks or files.")

    if "sudo" in lowered and re.search(r"\b(rm\s+-[^\n;|&]*r[^\n;|&]*f|mkfs(?:\.[a-z0-9]+)?|dd\b)", lowered):
        add("sudo_destructive_command", "sudo combined with destructive commands raises system-level risk.")

    if "$(" in lowered and re.search(r"\$\([^)]*(?:rm\s+-|mkfs(?:\.[a-z0-9]+)?|dd\b|find\b|ls\b)[^)]*\)", lowered):
        add(
            "risky_command_substitution",
            "Command substitution around destructive or file-listing commands can be unsafe to copy-paste.",
        )

    if not warnings:
        return RespondShellSafetyResult(
            safe=True,
            warnings=[],
            matched_patterns=[],
            sanitized_message=text,
        )

    prefix_lines = [
        "AOIA shell-safety warning: this response contains command text that may be unsafe to copy-paste.",
        *warnings,
        "",
    ]
    return RespondShellSafetyResult(
        safe=False,
        warnings=warnings,
        matched_patterns=matched_patterns,
        sanitized_message="\n".join(prefix_lines) + text,
    )
