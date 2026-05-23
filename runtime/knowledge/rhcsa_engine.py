from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.rhcsa_search import (
    retrieve_examples as search_examples_index,
    search_commands as search_command_index,
    search_rhcsa,
    search_workflows as search_workflow_index,
)


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
    """Retrieves local RHCSA/Linux operational memory before model calls."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.graph_path = project_dir / "knowledge" / "command_graph.json"
        self.command_graph = self._load_command_graph()

    def search_commands(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        return search_command_index(query, limit=limit)

    def search_workflows(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        return search_workflow_index(query, limit=limit)

    def retrieve_examples(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return search_examples_index(query, limit=limit)

    def retrieve_troubleshooting(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = f"{query} troubleshooting journalctl systemctl selinux recovery"
        return search_rhcsa(terms, limit=limit)

    def retrieve_related_topics(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        return search_rhcsa(query, limit=limit)

    def retrieve_operational_memory(self, query: str) -> KnowledgeHit:
        commands = self.search_commands(query)
        workflows = self.search_workflows(query)
        troubleshooting = self.retrieve_troubleshooting(query)
        examples = self.retrieve_examples(query)
        related_topics = self.retrieve_related_topics(query)
        graph_matches = self.command_graph_matches(query)
        score = self._score(commands, workflows, troubleshooting, examples, related_topics, graph_matches)
        confidence = self._confidence(score, commands, workflows, graph_matches)
        return KnowledgeHit(
            query=query,
            commands=commands,
            workflows=workflows,
            troubleshooting=troubleshooting,
            examples=examples,
            related_topics=related_topics,
            graph_matches=graph_matches,
            confidence=confidence,
            score=score,
        )

    def command_graph_matches(self, query: str) -> list[dict[str, Any]]:
        lowered = query.lower()
        query_words = {word.strip(".,:;()[]{}") for word in lowered.split() if word.strip()}
        matches: list[dict[str, Any]] = []
        nodes = self.command_graph.get("nodes", {})
        if not isinstance(nodes, dict):
            return matches
        for name, node in nodes.items():
            related = node.get("related", []) if isinstance(node, dict) else []
            aliases = {name.lower(), name.lower().replace("-cmd", "")}
            if name == "ssh":
                aliases.add("sshd")
            if name == "firewall-cmd":
                aliases.update({"firewall", "firewalld"})
            if query_words.intersection(aliases):
                matches.append(
                    {
                        "name": name,
                        "kind": node.get("kind", ""),
                        "commands": node.get("commands", []),
                        "related": related,
                    }
                )
        return matches[:5]

    def format_local_answer(self, hit: KnowledgeHit) -> str:
        lines = [
            "Local RHCSA operational memory hit.",
            f"Confidence: {hit.confidence.upper()} (score {hit.score})",
            "Gemini/API call avoided for this Linux operational request.",
            "",
        ]
        if hit.workflows:
            lines.append("Matched workflows:")
            for item in hit.workflows[:3]:
                lines.append(f"- {item.get('topic')}: {item.get('summary', '')}")
            lines.append("")
        if hit.graph_matches:
            lines.append("Command graph matches:")
            for item in hit.graph_matches[:3]:
                lines.append(f"- {item['name']} -> {', '.join(item.get('related', [])[:6])}")
                for command in item.get("commands", [])[:5]:
                    lines.append(f"  command: {command}")
            lines.append("")
        if hit.commands:
            lines.append("Reusable command patterns:")
            for item in hit.commands[:8]:
                lines.append(f"- {item.get('command')} [{item.get('topic')}]")
            lines.append("")
        if hit.troubleshooting:
            lines.append("Troubleshooting references:")
            for item in hit.troubleshooting[:3]:
                lines.append(f"- {item.get('topic')}: {item.get('summary', '')}")
            lines.append("")
        lines.append("Execution policy: commands are suggestions only. Use explicit approval before running any action.")
        return "\n".join(lines).strip()

    def _load_command_graph(self) -> dict[str, Any]:
        try:
            return json.loads(self.graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "nodes": {}}

    @staticmethod
    def _score(
        commands: list[dict[str, Any]],
        workflows: list[dict[str, Any]],
        troubleshooting: list[dict[str, Any]],
        examples: list[dict[str, Any]],
        related_topics: list[dict[str, Any]],
        graph_matches: list[dict[str, Any]],
    ) -> int:
        return (
            min(len(commands), 8) * 8
            + min(len(workflows), 3) * 25
            + min(len(troubleshooting), 4) * 8
            + min(len(examples), 2) * 6
            + min(len(related_topics), 4) * 5
            + min(len(graph_matches), 3) * 20
        )

    @staticmethod
    def _confidence(
        score: int,
        commands: list[dict[str, Any]],
        workflows: list[dict[str, Any]],
        graph_matches: list[dict[str, Any]],
    ) -> str:
        if workflows and (commands or graph_matches):
            return "high"
        if score >= 75:
            return "high"
        if score >= 30:
            return "medium"
        if score > 0:
            return "low"
        return "none"
