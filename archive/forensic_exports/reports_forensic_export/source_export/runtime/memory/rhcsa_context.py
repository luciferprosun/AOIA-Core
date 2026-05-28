from __future__ import annotations

from typing import Any

from tools.rhcsa_search import retrieve_examples, search_commands


def inject_linux_context(query: str, max_chars: int = 6000) -> str:
    """Return deterministic RHCSA context for prompt injection."""
    commands = retrieve_command_patterns(query, limit=8)
    examples = retrieve_operational_examples(query, limit=4)
    lines: list[str] = []
    if commands:
        lines.append("Command patterns:")
        for item in commands:
            command = item.get("command") or item.get("command_name") or ""
            topic = item.get("topic") or ""
            summary = item.get("summary") or ""
            lines.append(f"- {command} [{topic}] {summary}".strip())
    if examples:
        lines.append("Operational examples:")
        for item in examples:
            topic = item.get("topic") or ""
            summary = item.get("summary") or ""
            commands_text = ", ".join(str(command) for command in item.get("commands", [])[:5])
            lines.append(f"- {topic}: {summary} {commands_text}".strip())
    text = "\n".join(lines).strip()
    return text[:max_chars]


def retrieve_command_patterns(query: str, limit: int = 8) -> list[dict[str, Any]]:
    return search_commands(query, limit=limit)


def retrieve_operational_examples(query: str, limit: int = 3) -> list[dict[str, Any]]:
    return retrieve_examples(query, limit=limit)

