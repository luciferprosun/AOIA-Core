from __future__ import annotations

from pathlib import Path
from typing import Any

from retrieval.linux import LinuxRetrievalEngine, LinuxRetrievalResponse


def retrieve_linux_knowledge(
    query: str,
    max_results: int = 5,
    project_dir: Path | None = None,
) -> LinuxRetrievalResponse:
    """Read-only canonical facade for Linux/RHCSA retrieval."""
    return LinuxRetrievalEngine(project_dir=project_dir, max_results=max_results).retrieve(query)


def linux_library_status() -> dict[str, Any]:
    from tools.rhcsa_search import library_status

    return library_status()


def linux_load_topic(topic: str, max_chars: int = 12000) -> str:
    from tools.rhcsa_search import load_topic

    return load_topic(topic, max_chars=max_chars)


def linux_low_level_results(mode: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Compatibility access for CLI-style RHCSA commands.

    Coordinator code should call this facade instead of importing
    tools.rhcsa_search directly.
    """
    from tools import rhcsa_search

    if mode == "search":
        return rhcsa_search.search_rhcsa(query, limit=limit)
    if mode == "tag":
        return rhcsa_search.search_by_tag(query, limit=limit)
    if mode == "exact":
        return rhcsa_search.exact_command_lookup(query, limit=limit)
    if mode == "grep":
        return rhcsa_search.grep_rhcsa(query, limit=limit)
    if mode == "command_search":
        return rhcsa_search.search_commands(query, limit=limit)
    if mode == "commands":
        return rhcsa_search.suggest_related_commands(query, limit=limit)
    if mode == "workflows":
        return rhcsa_search.search_workflows(query, limit=limit)
    if mode == "examples":
        return rhcsa_search.retrieve_examples(query, limit=limit)
    raise ValueError(f"Unsupported Linux retrieval mode: {mode}")


def linux_filter_by_topic(topic: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    from tools.rhcsa_search import filter_by_topic

    return filter_by_topic(topic, query, limit=limit)
