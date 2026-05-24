from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from retrieval.facade import retrieve_linux_knowledge
from retrieval.linux.graph_loader import load_command_graph


deprecated = True


@dataclass
class KnowledgeHit:
    query: str
    commands: list[dict[str, Any]]
    workflows: list[dict[str, Any]]
    troubleshooting: list[dict[str, Any]]
    examples: list[dict[str, Any]]
    related_topics: list[dict[str, Any]]
    graph_matches: list[dict[str, Any]]
    confidence: str
    score: int

    @property
    def has_operational_memory(self) -> bool:
        return self.score > 0


class RHCSAKnowledgeEngine:
    """Deprecated compatibility wrapper over LinuxRetrievalEngine.

    Existing callers keep their import path, but RHCSA/Linux retrieval now
    delegates through the canonical deterministic facade.
    """

    deprecated = True

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.command_graph = load_command_graph(project_dir)

    def search_commands(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        return self._retrieval_results(query, limit)

    def search_workflows(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        return self._retrieval_results(query, limit)

    def retrieve_examples(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return self._retrieval_results(query, limit)

    def retrieve_troubleshooting(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        return self._retrieval_results(query, limit)

    def retrieve_related_topics(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        return self._retrieval_results(query, limit)

    def retrieve_operational_memory(self, query: str) -> KnowledgeHit:
        response = retrieve_linux_knowledge(query, project_dir=self.project_dir)
        results = [dict(item) for item in response.results]
        graph_matches = [
            item for item in results
            if item.get("file_location") == "runtime/knowledge/command_graph.json"
        ]
        return KnowledgeHit(
            query=query,
            commands=results,
            workflows=[],
            troubleshooting=[],
            examples=[],
            related_topics=results,
            graph_matches=graph_matches,
            confidence=response.confidence,
            score=response.confidence_score,
        )

    def command_graph_matches(self, query: str) -> list[dict[str, Any]]:
        response = retrieve_linux_knowledge(query, project_dir=self.project_dir)
        return [
            dict(item) for item in response.results
            if item.get("file_location") == "runtime/knowledge/command_graph.json"
        ]

    def format_local_answer(self, hit: KnowledgeHit) -> str:
        response = retrieve_linux_knowledge(hit.query, project_dir=self.project_dir)
        if response.answered:
            return response.message + "\n\nExecution policy: commands are suggestions only. Use explicit approval before running any action."
        return response.message

    def _retrieval_results(self, query: str, limit: int) -> list[dict[str, Any]]:
        response = retrieve_linux_knowledge(query, max_results=limit, project_dir=self.project_dir)
        return [dict(item) for item in response.results[:limit]]
