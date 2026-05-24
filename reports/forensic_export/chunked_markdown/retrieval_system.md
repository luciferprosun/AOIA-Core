# Retrieval System

Deterministic Linux/RHCSA retrieval implementation and RHCSA search bridge.

Commit: `04adfbdb5a6b34d2969d67ac7e84c704c8e0915a`

Files in this chunk: 8

## `runtime/knowledge/rhcsa_engine.py`

- size: 6688 bytes
- sha256: `e1d74213a5385685b994f2d86ed8fa6eaf908aeeca7c51deca541bae08ec4a2f`
- category: knowledge

```python
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
```

## `runtime/retrieval/__init__.py`

- size: 38 bytes
- sha256: `924b2a8b8864997fe39b737b68c9430aecd24946d737269c042e46ad069e458f`
- category: retrieval

```python
"""Deterministic retrieval layers."""
```

## `runtime/retrieval/linux/__init__.py`

- size: 188 bytes
- sha256: `8ceed4f9a1f9266e9be5fad884dcc89aefbadd09a00b8fc17ae40f1c1539fcd8`
- category: retrieval

```python
"""Linux/RHCSA deterministic retrieval engine."""

from .retrieval_engine import LinuxRetrievalEngine, LinuxRetrievalResponse

__all__ = ["LinuxRetrievalEngine", "LinuxRetrievalResponse"]
```

## `runtime/retrieval/linux/provenance_attach.py`

- size: 2690 bytes
- sha256: `f8d2ffed5044217825aead5d328a02ef29123c68f75e2a00cc5fc823b543fbbf`
- category: retrieval

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
MANIFEST_PATH = KNOWLEDGE_ROOT / "manifests" / "library_manifest.yaml"
LEGACY_SOURCE = "runtime/knowledge/source/RHCSA_Command_Library (1).pdf"


@dataclass(frozen=True)
class Provenance:
    source_file: str
    source_page: int | None
    canonical_source: str
    confidence_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_page": self.source_page,
            "canonical_source": self.canonical_source,
            "confidence_score": self.confidence_score,
        }


def _manifest_value(key: str) -> str | None:
    try:
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}:"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


@lru_cache(maxsize=1)
def canonical_source() -> str:
    return _manifest_value("canonical_source") or LEGACY_SOURCE


@lru_cache(maxsize=1)
def section_source_map() -> dict[str, str]:
    path = KNOWLEDGE_ROOT / "canonical" / "rhcsa_commands.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    mapping: dict[str, str] = {}
    if not isinstance(payload, list):
        return mapping
    for item in payload:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command", "")).strip()
        source_section = str(item.get("source_section", "")).strip()
        if command and source_section:
            mapping[command] = source_section
    return mapping


def attach_provenance(result: dict[str, Any], confidence_score: int) -> dict[str, Any]:
    source_file = (
        result.get("source_file")
        or result.get("file_location")
        or result.get("source")
        or "runtime/knowledge/canonical/rhcsa_commands.json"
    )
    enriched = dict(result)
    enriched["provenance"] = Provenance(
        source_file=str(source_file),
        source_page=_coerce_page(result.get("source_page")),
        canonical_source=canonical_source(),
        confidence_score=confidence_score,
    ).to_dict()
    return enriched


def _coerce_page(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None
```

## `runtime/retrieval/linux/query_normalizer.py`

- size: 3874 bytes
- sha256: `c043066633377fdf9085f91f89199fa8312df21a7b55e6424f2b4f7138e703c8`
- category: retrieval

```python
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


COMMAND_STOPWORDS = {
    "a",
    "about",
    "command",
    "commands",
    "for",
    "how",
    "jak",
    "komenda",
    "komendy",
    "linux",
    "mi",
    "of",
    "o",
    "poka",
    "pokaz",
    "pokaż",
    "rhcsa",
    "rhce",
    "show",
    "the",
    "to",
    "w",
}

ALIASES = {
    "apache": "httpd",
    "apachectl": "httpd",
    "cron": "crontab",
    "firewall": "firewall-cmd",
    "firewalld": "firewall-cmd",
    "grep extended": "grep -E",
    "list": "ls",
    "services": "systemctl",
    "ssh daemon": "sshd",
    "ssh service": "sshd",
}


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    normalized: str
    tokens: tuple[str, ...]
    candidate_command: str
    alias_target: str | None
    category_hint: str | None


def normalize_text(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9_+./$-]+", " ", normalized).strip()


def normalize_command(value: str) -> str:
    return " ".join(value.strip().split())


def command_key(value: str) -> str:
    command = normalize_command(value)
    if " " not in command:
        return command.lower()
    binary, rest = command.split(" ", 1)
    return f"{binary.lower()} {rest}"


def tokenize(value: str) -> tuple[str, ...]:
    return tuple(token for token in normalize_text(value).split() if token)


def detect_category(tokens: tuple[str, ...]) -> str | None:
    joined = " ".join(tokens)
    categories = {
        "bash": {"bash", "shell", "script", "skrypt", "zmienna"},
        "filesystem": {"file", "files", "folder", "katalog", "plik", "directory", "copy", "delete"},
        "lvm": {"lvm", "lv", "vg", "pv", "volume"},
        "networking": {"network", "ip", "dns", "firewall", "port", "ssh", "routing", "sieci"},
        "permissions": {"chmod", "chown", "permission", "acl", "uprawnienia"},
        "podman": {"podman", "container", "kontener"},
        "selinux": {"selinux", "semanage", "restorecon", "context"},
        "storage": {"disk", "mount", "xfs", "ext4", "swap", "storage", "dysk"},
        "systemd": {"systemd", "systemctl", "journalctl", "service", "timer", "usluga", "usługa"},
        "troubleshooting": {"debug", "diagnose", "problem", "troubleshoot", "log", "logs"},
        "users": {"user", "group", "passwd", "uzytkownik", "użytkownik", "grupa"},
    }
    for category, words in categories.items():
        if words.intersection(tokens) or category in joined:
            return category
    return None


def extract_candidate_command(query: str) -> str:
    quoted = re.findall(r"`([^`]+)`", query)
    if quoted:
        return normalize_command(quoted[0])

    tokens = list(tokenize(query))
    meaningful = [token for token in tokens if token not in COMMAND_STOPWORDS]
    if not meaningful:
        return ""

    if len(meaningful) >= 2:
        two = " ".join(meaningful[:2])
        if two in ALIASES:
            return two
        if meaningful[1].startswith("-") or meaningful[0] in {"dnf", "git", "ip", "ls", "systemctl", "journalctl"}:
            return normalize_command(" ".join(meaningful[:3]))
    return meaningful[0]


def normalize_query(query: str) -> NormalizedQuery:
    normalized = normalize_text(query)
    tokens = tokenize(query)
    candidate = extract_candidate_command(query)
    alias_target = ALIASES.get(candidate.lower()) if candidate else None
    if not alias_target:
        alias_target = ALIASES.get(normalized)
    return NormalizedQuery(
        original=query,
        normalized=normalized,
        tokens=tokens,
        candidate_command=candidate,
        alias_target=alias_target,
        category_hint=detect_category(tokens),
    )
```

## `runtime/retrieval/linux/retrieval_engine.py`

- size: 12165 bytes
- sha256: `e1a03e6b861188195d88e8e4e6ddf1788c066cdd4ec33459230b60b14db8530e`
- category: retrieval

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from retrieval.linux.provenance_attach import attach_provenance
from retrieval.linux.query_normalizer import command_key, normalize_query, normalize_text
from retrieval.linux.scoring import (
    ALIAS_MATCH_SCORE,
    CATEGORY_MATCH_SCORE,
    EXACT_MATCH_SCORE,
    FAMILY_MATCH_SCORE,
    KEYWORD_MATCH_SCORE,
    LOW_CONFIDENCE_SCORE,
    SUBCOMMAND_MATCH_SCORE,
    ScoreDecision,
    score_decision,
    should_refuse,
)
from tools.rhcsa_search import exact_command_lookup, search_by_tag, search_commands, search_rhcsa


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
GENERIC_QUERY_TOKENS = {
    "a",
    "about",
    "command",
    "commands",
    "for",
    "how",
    "jak",
    "linux",
    "mi",
    "not",
    "o",
    "rhcsa",
    "rhce",
    "show",
    "the",
    "to",
    "use",
    "w",
}


@dataclass(frozen=True)
class LinuxRetrievalResponse:
    query: str
    normalized_query: str
    status: str
    match_type: str
    confidence: str
    confidence_score: int
    results: tuple[dict[str, Any], ...]
    message: str

    @property
    def answered(self) -> bool:
        return self.status == "answered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "status": self.status,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "results": list(self.results),
            "message": self.message,
        }


class LinuxRetrievalEngine:
    """Deterministic evidence-backed Linux/RHCSA retrieval.

    This is an infrastructure layer: it does not call models, does not infer
    missing commands, and refuses low-confidence queries.
    """

    def __init__(self, project_dir: Path | None = None, max_results: int = 5) -> None:
        self.project_dir = project_dir or PROJECT_ROOT
        self.max_results = max_results

    def retrieve(self, query: str) -> LinuxRetrievalResponse:
        normalized = normalize_query(query)
        if not normalized.normalized:
            return self._refusal(query, "", "unresolved", 0)

        candidates: list[dict[str, Any]]
        decision: ScoreDecision

        if normalized.candidate_command:
            exact = self._exact_lookup(normalized.candidate_command)
            if exact:
                decision = score_decision("exact", EXACT_MATCH_SCORE, len(exact))
                return self._answer(query, normalized.normalized, exact, decision)

        if normalized.alias_target:
            alias = self._exact_lookup(normalized.alias_target)
            if alias:
                decision = score_decision("alias", ALIAS_MATCH_SCORE, len(alias))
                return self._answer(query, normalized.normalized, alias, decision)

        if normalized.candidate_command:
            subcommand = self._subcommand_lookup(normalized.candidate_command)
            if subcommand:
                decision = score_decision("subcommand", SUBCOMMAND_MATCH_SCORE, len(subcommand))
                return self._answer(query, normalized.normalized, subcommand, decision)

        if normalized.category_hint:
            category = search_by_tag(normalized.category_hint, limit=self.max_results)
            if not category:
                category = search_rhcsa(normalized.category_hint, limit=self.max_results, topic_filter=normalized.category_hint)
            if category:
                decision = score_decision("category", CATEGORY_MATCH_SCORE, len(category))
                return self._answer(query, normalized.normalized, category, decision)

        family = self._family_lookup(normalized.candidate_command)
        if family:
            decision = score_decision("command_family", FAMILY_MATCH_SCORE, len(family))
            return self._answer(query, normalized.normalized, family, decision)

        keyword_query = self._keyword_query(normalized.tokens)
        if not keyword_query:
            return self._refusal(query, normalized.normalized, "unresolved", 0)

        candidates = search_rhcsa(keyword_query, limit=self.max_results)
        if candidates:
            decision = score_decision("keyword", KEYWORD_MATCH_SCORE, len(candidates))
            return self._answer(query, normalized.normalized, candidates, decision)

        weak = search_commands(keyword_query, limit=1)
        if weak:
            decision = score_decision("low_confidence", LOW_CONFIDENCE_SCORE, len(weak))
            if should_refuse(decision.score):
                return self._refusal(query, normalized.normalized, decision.match_type, decision.score)
            return self._answer(query, normalized.normalized, weak, decision)

        return self._refusal(query, normalized.normalized, "unresolved", 0)

    def _exact_lookup(self, command: str) -> list[dict[str, Any]]:
        results = exact_command_lookup(command, limit=self.max_results)
        if results:
            return results
        command_record = self.command_records_by_key.get(command_key(command))
        if not command_record:
            return []
        return [self._command_record_result(command_record)]

    def _subcommand_lookup(self, command: str) -> list[dict[str, Any]]:
        key = command_key(command)
        if " " not in key:
            return []
        results = [
            self._command_record_result(record)
            for record_key, record in self.command_records_by_key.items()
            if record_key.startswith(f"{key} ") or key.startswith(f"{record_key} ")
        ]
        return self._dedupe(results)[: self.max_results]

    def _family_lookup(self, command: str) -> list[dict[str, Any]]:
        if not command:
            return []
        family = command.split()[0].lower()
        graph_node = self.command_graph.get("nodes", {}).get(family)
        results: list[dict[str, Any]] = []
        if isinstance(graph_node, dict):
            results.append(
                {
                    "topic": family,
                    "category": graph_node.get("kind", "command_family"),
                    "file_location": "runtime/knowledge/command_graph.json",
                    "summary": f"Command graph family for {family}.",
                    "related_commands": graph_node.get("commands", [])[:8],
                    "tags": graph_node.get("related", [])[:8],
                    "preview": ", ".join(graph_node.get("commands", [])[:5]),
                    "score": FAMILY_MATCH_SCORE,
                }
            )
        for item in search_commands(family, limit=self.max_results):
            if item.get("command_name", "").lower() == family:
                results.append(item)
        return self._dedupe(results)[: self.max_results]

    def _answer(
        self,
        query: str,
        normalized_query: str,
        raw_results: list[dict[str, Any]],
        decision: ScoreDecision,
    ) -> LinuxRetrievalResponse:
        if should_refuse(decision.score):
            return self._refusal(query, normalized_query, decision.match_type, decision.score)
        bounded = self._dedupe(raw_results)[: self.max_results]
        results = tuple(attach_provenance(result, decision.score) for result in bounded)
        return LinuxRetrievalResponse(
            query=query,
            normalized_query=normalized_query,
            status="answered",
            match_type=decision.match_type,
            confidence=decision.confidence,
            confidence_score=decision.score,
            results=results,
            message=self._format_message(results, decision),
        )

    def _refusal(
        self,
        query: str,
        normalized_query: str,
        match_type: str,
        score: int,
    ) -> LinuxRetrievalResponse:
        return LinuxRetrievalResponse(
            query=query,
            normalized_query=normalized_query,
            status="refused",
            match_type=match_type,
            confidence="none",
            confidence_score=score,
            results=(),
            message=(
                "I do not have enough local RHCSA/Linux evidence to answer deterministically. "
                "Please clarify the command, category, or Linux task."
            ),
        )

    @staticmethod
    def _format_message(results: tuple[dict[str, Any], ...], decision: ScoreDecision) -> str:
        lines = [
            "Local Linux/RHCSA retrieval hit.",
            f"Match: {decision.match_type}",
            f"Confidence: {decision.confidence} ({decision.score})",
            "Evidence-backed results:",
        ]
        for result in results:
            topic = result.get("topic") or result.get("command") or "unknown"
            source = result.get("provenance", {}).get("source_file", "")
            commands = result.get("related_commands") or result.get("commands") or []
            command_text = ", ".join(str(item) for item in commands[:5])
            lines.append(f"- {topic}: {command_text}".rstrip())
            lines.append(f"  source: {source}")
        return "\n".join(lines)

    @staticmethod
    def _dedupe(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for result in results:
            key = "|".join(
                str(result.get(part, ""))
                for part in ("file_location", "source_file", "topic", "command", "summary")
            )
            deduped.setdefault(key, result)
        return list(deduped.values())

    @staticmethod
    def _keyword_query(tokens: tuple[str, ...]) -> str:
        meaningful = [
            token
            for token in tokens
            if token not in GENERIC_QUERY_TOKENS and not token.startswith("zzzz")
        ]
        if not meaningful:
            return ""
        if len(meaningful) == 1 and "-" in meaningful[0] and meaningful[0].count("-") >= 3:
            return ""
        return " ".join(meaningful[:4])

    @cached_property
    def command_records_by_key(self) -> dict[str, dict[str, Any]]:
        path = KNOWLEDGE_ROOT / "canonical" / "rhcsa_commands.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        records: dict[str, dict[str, Any]] = {}
        if not isinstance(payload, list):
            return records
        for item in payload:
            if not isinstance(item, dict):
                continue
            command = str(item.get("command", "")).strip()
            if not command:
                continue
            records.setdefault(command_key(command), item)
        return records

    @cached_property
    def command_graph(self) -> dict[str, Any]:
        path = KNOWLEDGE_ROOT / "command_graph.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "nodes": {}}
        return payload if isinstance(payload, dict) else {"version": 1, "nodes": {}}

    @staticmethod
    def _command_record_result(record: dict[str, Any]) -> dict[str, Any]:
        command = str(record.get("command", "")).strip()
        category = str(record.get("category", "")).strip() or "canonical"
        source_section = str(record.get("source_section", "")).strip()
        examples = [str(item).strip() for item in record.get("examples", []) if str(item).strip()]
        return {
            "topic": source_section or category,
            "category": category,
            "file_location": "runtime/knowledge/canonical/rhcsa_commands.json",
            "summary": str(record.get("description", "")).strip() or command,
            "related_commands": [command, *examples][:8],
            "tags": [normalize_text(category), normalize_text(source_section)],
            "preview": command,
            "score": EXACT_MATCH_SCORE,
        }
```

## `runtime/retrieval/linux/scoring.py`

- size: 961 bytes
- sha256: `b91a43ceec3ff2b1e3c0b65e808fafdfcce89a640fbfda011b2bd1e21f4a79ad`
- category: retrieval

```python
from __future__ import annotations

from dataclasses import dataclass


EXACT_MATCH_SCORE = 100
ALIAS_MATCH_SCORE = 92
SUBCOMMAND_MATCH_SCORE = 84
CATEGORY_MATCH_SCORE = 65
FAMILY_MATCH_SCORE = 58
KEYWORD_MATCH_SCORE = 45
LOW_CONFIDENCE_SCORE = 20
REFUSAL_THRESHOLD = 30


@dataclass(frozen=True)
class ScoreDecision:
    score: int
    confidence: str
    match_type: str


def confidence_for(score: int) -> str:
    if score >= 90:
        return "high"
    if score >= 60:
        return "medium"
    if score >= REFUSAL_THRESHOLD:
        return "low"
    return "none"


def score_decision(match_type: str, base_score: int, result_count: int = 1) -> ScoreDecision:
    bounded_count_bonus = min(max(result_count - 1, 0), 3) * 2
    score = min(100, base_score + bounded_count_bonus)
    return ScoreDecision(score=score, confidence=confidence_for(score), match_type=match_type)


def should_refuse(score: int) -> bool:
    return score < REFUSAL_THRESHOLD
```

## `runtime/tools/rhcsa_search.py`

- size: 22225 bytes
- sha256: `03c39471df39f7c6079a3df055f0b50bf9460c4e75ada8bb52700692db069457`
- category: tooling

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
TOPIC_DIRECTORIES = (
    "filesystem",
    "networking",
    "users",
    "permissions",
    "selinux",
    "systemd",
    "storage",
    "lvm",
    "podman",
    "bash",
    "troubleshooting",
)


@dataclass(frozen=True)
class KnowledgeModule:
    title: str
    topic: str
    source_section: str
    file_path: Path
    tags: tuple[str, ...]
    summary: str
    commands: tuple[str, ...]
    examples: tuple[str, ...]
    content: str


@dataclass(frozen=True)
class ExampleEntry:
    entry_id: str
    command: str
    category: str
    tags: tuple[str, ...]
    risk: str
    notes: str
    related_commands: tuple[str, ...]
    examples: tuple[str, ...]
    file_path: Path


def detect_rhcsa_library() -> Path:
    """Return the deterministic local RHCSA knowledge root."""
    return KNOWLEDGE_ROOT


def _normalize_text(value: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def _tokenize(value: str) -> list[str]:
    return [token for token in _normalize_text(value).split() if token]


def _normalized_command(value: str) -> str:
    return " ".join(value.strip().split())


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw_frontmatter = parts[1]
    body = parts[2].lstrip("\n")
    payload: dict[str, str] = {}
    for line in raw_frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload, body


def _parse_tags(raw: str) -> tuple[str, ...]:
    text = raw.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return tuple(tag.strip() for tag in text.split(",") if tag.strip())


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_summary(body: str) -> str:
    match = re.search(r"^# .+\n\n(.*?)(?=^## |\Z)", body, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def _extract_commands(body: str) -> tuple[str, ...]:
    matches = re.findall(r"^### `([^`]+)`", body, flags=re.MULTILINE)
    return tuple(dict.fromkeys(match.strip() for match in matches if match.strip()))


def _extract_examples(body: str) -> tuple[str, ...]:
    section = _extract_section(body, "Examples")
    matches = re.findall(r"- `([^`]+)`", section)
    return tuple(dict.fromkeys(match.strip() for match in matches if match.strip()))


def _snippet(text: str, pattern: str, max_chars: int = 280) -> str:
    if not pattern:
        return " ".join(text.split())[:max_chars]
    lowered_text = text.lower()
    lowered_pattern = pattern.lower()
    position = lowered_text.find(lowered_pattern)
    if position < 0:
        return " ".join(text.split())[:max_chars]
    start = max(0, position - 120)
    end = min(len(text), position + max_chars)
    return " ".join(text[start:end].split())


@lru_cache(maxsize=1)
def _module_index() -> tuple[KnowledgeModule, ...]:
    modules: list[KnowledgeModule] = []
    for topic in TOPIC_DIRECTORIES:
        directory = KNOWLEDGE_ROOT / topic
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name == "README.md":
                continue
            text = path.read_text(encoding="utf-8")
            frontmatter, body = _parse_frontmatter(text)
            module = KnowledgeModule(
                title=frontmatter.get("title", path.stem),
                topic=frontmatter.get("topic", topic).strip() or topic,
                source_section=frontmatter.get("source_section", frontmatter.get("title", path.stem)),
                file_path=path,
                tags=_parse_tags(frontmatter.get("tags", "")),
                summary=_extract_summary(body),
                commands=_extract_commands(body),
                examples=_extract_examples(body),
                content=text,
            )
            modules.append(module)
    return tuple(modules)


@lru_cache(maxsize=1)
def _example_index() -> tuple[ExampleEntry, ...]:
    entries: list[ExampleEntry] = []
    examples_root = KNOWLEDGE_ROOT / "examples"
    for path in sorted(examples_root.glob("*.json")):
        payload = _read_json(path, {})
        if not isinstance(payload, dict):
            continue
        example_inputs = []
        for example in payload.get("examples", []):
            if isinstance(example, dict):
                value = str(example.get("input", "")).strip()
                if value:
                    example_inputs.append(value)
        entries.append(
            ExampleEntry(
                entry_id=str(payload.get("id", path.stem)).strip() or path.stem,
                command=str(payload.get("command", "")).strip(),
                category=str(payload.get("category", "")).strip(),
                tags=tuple(str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()),
                risk=str(payload.get("risk", "")).strip(),
                notes=str(payload.get("notes", "")).strip(),
                related_commands=tuple(
                    str(item).strip() for item in payload.get("related_commands", []) if str(item).strip()
                ),
                examples=tuple(example_inputs),
                file_path=path,
            )
        )
    return tuple(entries)


def _keyword_score(query: str, module: KnowledgeModule) -> int:
    normalized_query = _normalize_text(query)
    tokens = _tokenize(query)
    if not normalized_query or not tokens:
        return 0

    title = _normalize_text(module.title)
    topic = _normalize_text(module.topic)
    tags = {_normalize_text(tag) for tag in module.tags}
    summary = _normalize_text(module.summary)
    commands = [_normalize_text(command) for command in module.commands]
    examples = [_normalize_text(example) for example in module.examples]

    score = 0
    if normalized_query in title:
        score += 35
    if normalized_query in topic:
        score += 30
    if any(normalized_query == tag for tag in tags):
        score += 28
    if any(normalized_query == command for command in commands):
        score += 40

    for token in tokens:
        if token in title.split():
            score += 12
        if token == topic:
            score += 10
        if token in tags:
            score += 10
        if any(token in command.split() for command in commands):
            score += 8
        if any(token in example.split() for example in examples):
            score += 5
        if token in summary.split():
            score += 4
    return score


def _module_result(module: KnowledgeModule, score: int, preview_seed: str) -> dict[str, Any]:
    return {
        "score": score,
        "topic": module.title,
        "category": module.topic,
        "file_location": str(module.file_path.relative_to(PROJECT_ROOT)),
        "summary": module.summary,
        "related_commands": list(module.commands[:8]),
        "tags": list(module.tags),
        "preview": _snippet(module.content, preview_seed),
    }


def _example_result(entry: ExampleEntry, score: int) -> dict[str, Any]:
    preview_source = entry.notes or (entry.examples[0] if entry.examples else entry.command)
    return {
        "score": score,
        "topic": entry.entry_id,
        "category": entry.category or "examples",
        "file_location": str(entry.file_path.relative_to(PROJECT_ROOT)),
        "summary": entry.notes or entry.command,
        "related_commands": [entry.command, *entry.related_commands][:8],
        "tags": list(entry.tags),
        "preview": _snippet(preview_source, entry.command or entry.entry_id),
    }


def _topic_filter_match(topic_filter: str | None, module_topic: str) -> bool:
    if not topic_filter:
        return True
    return _normalize_text(topic_filter) == _normalize_text(module_topic)


def search_rhcsa(query: str, limit: int = 10, topic_filter: str | None = None) -> list[dict[str, Any]]:
    """Deterministic keyword search over the local markdown RHCSA knowledge base."""
    query = query.strip()
    if not query:
        return []

    results: list[dict[str, Any]] = []
    for module in _module_index():
        if not _topic_filter_match(topic_filter, module.topic):
            continue
        score = _keyword_score(query, module)
        if score:
            results.append(_module_result(module, score, query))

    for entry in _example_index():
        if topic_filter and _normalize_text(topic_filter) != _normalize_text(entry.category):
            continue
        search_space = " ".join([entry.entry_id, entry.command, entry.category, " ".join(entry.tags), entry.notes])
        token_hits = 0
        normalized_search_space = _normalize_text(search_space)
        normalized_query = _normalize_text(query)
        if normalized_query and normalized_query in normalized_search_space:
            token_hits += 20
        for token in _tokenize(query):
            if token in normalized_search_space.split():
                token_hits += 6
        if token_hits:
            results.append(_example_result(entry, token_hits))

    deduped: dict[str, dict[str, Any]] = {}
    for result in sorted(results, key=lambda item: (-item["score"], item["file_location"])):
        deduped.setdefault(result["file_location"], result)
    return list(deduped.values())[:limit]


def search_by_tag(tag: str, limit: int = 20, topic_filter: str | None = None) -> list[dict[str, Any]]:
    """Exact tag search without semantic expansion."""
    normalized_tag = _normalize_text(tag)
    if not normalized_tag:
        return []

    results: list[dict[str, Any]] = []
    for module in _module_index():
        if not _topic_filter_match(topic_filter, module.topic):
            continue
        if normalized_tag in {_normalize_text(item) for item in module.tags}:
            results.append(_module_result(module, 50, tag))

    for entry in _example_index():
        if topic_filter and _normalize_text(topic_filter) != _normalize_text(entry.category):
            continue
        if normalized_tag in {_normalize_text(item) for item in entry.tags}:
            results.append(_example_result(entry, 45))

    return sorted(results, key=lambda item: (-item["score"], item["file_location"]))[:limit]


def exact_command_lookup(command: str, limit: int = 20) -> list[dict[str, Any]]:
    """Match commands by exact normalized string only."""
    normalized_query = _normalized_command(command)
    if not normalized_query:
        return []

    results: list[dict[str, Any]] = []
    for module in _module_index():
        for candidate in module.commands:
            if _normalized_command(candidate) == normalized_query:
                results.append(_module_result(module, 100, candidate))
                break

    for entry in _example_index():
        if _normalized_command(entry.command) == normalized_query:
            results.append(_example_result(entry, 95))

    deduped: dict[str, dict[str, Any]] = {}
    for result in results:
        deduped.setdefault(result["file_location"], result)
    return list(deduped.values())[:limit]


def grep_rhcsa(pattern: str, limit: int = 20, topic_filter: str | None = None) -> list[dict[str, Any]]:
    """Literal grep-style retrieval over markdown content."""
    pattern = pattern.strip()
    if not pattern:
        return []
    lowered = pattern.lower()

    results: list[dict[str, Any]] = []
    for module in _module_index():
        if not _topic_filter_match(topic_filter, module.topic):
            continue
        match_count = module.content.lower().count(lowered)
        if match_count:
            result = _module_result(module, match_count * 10, pattern)
            result["match_count"] = match_count
            results.append(result)

    return sorted(results, key=lambda item: (-item["score"], item["file_location"]))[:limit]


def filter_by_topic(topic: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Keyword search restricted to one topic directory."""
    return search_rhcsa(query, limit=limit, topic_filter=topic)


def load_topic(topic: str, max_chars: int = 12000) -> str:
    """Load markdown for an exact topic directory or exact module title."""
    normalized_query = _normalize_text(topic)
    if not normalized_query:
        return ""

    if normalized_query in {_normalize_text(topic_name) for topic_name in TOPIC_DIRECTORIES}:
        topic_name = next(
            topic_name for topic_name in TOPIC_DIRECTORIES
            if _normalize_text(topic_name) == normalized_query
        )
        readme_path = KNOWLEDGE_ROOT / topic_name / "README.md"
        chunks: list[str] = []
        if readme_path.exists():
            chunks.append(readme_path.read_text(encoding="utf-8"))
        for module in _module_index():
            if module.topic == topic_name:
                chunks.append(module.content)
        text = "\n\n".join(chunks)
        return text if len(text) <= max_chars else text[:max_chars] + "\n...[truncated]...\n"

    exact_modules = [
        module for module in _module_index()
        if normalized_query in {
            _normalize_text(module.topic),
            _normalize_text(module.title),
            _normalize_text(module.source_section),
            _normalize_text(module.file_path.stem),
        }
    ]
    if exact_modules:
        text = "\n\n".join(module.content for module in exact_modules)
        return text if len(text) <= max_chars else text[:max_chars] + "\n...[truncated]...\n"
    return ""


def suggest_related_commands(query: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Deterministic command list filtered by exact token matches."""
    normalized_query = _normalize_text(query or "")
    tokens = set(_tokenize(query or ""))
    results: list[dict[str, Any]] = []

    seen_commands: set[tuple[str, str]] = set()
    for module in _module_index():
        for command in module.commands:
            command_norm = _normalize_text(command)
            if normalized_query:
                if normalized_query != command_norm and normalized_query not in command_norm:
                    if not tokens.intersection(command_norm.split()):
                        continue
            key = (command, module.title)
            if key in seen_commands:
                continue
            seen_commands.add(key)
            results.append(
                {
                    "command_name": command.split()[0],
                    "command": command,
                    "topic": module.title,
                    "file_location": str(module.file_path.relative_to(PROJECT_ROOT)),
                    "summary": module.summary,
                }
            )

    for entry in _example_index():
        command_norm = _normalize_text(entry.command)
        if normalized_query:
            if normalized_query != command_norm and normalized_query not in command_norm:
                if not tokens.intersection(command_norm.split()):
                    continue
        key = (entry.command, entry.entry_id)
        if key in seen_commands:
            continue
        seen_commands.add(key)
        results.append(
            {
                "command_name": entry.command.split()[0],
                "command": entry.command,
                "topic": entry.entry_id,
                "file_location": str(entry.file_path.relative_to(PROJECT_ROOT)),
                "summary": entry.notes,
            }
        )
    return results[:limit]


def search_commands(query: str = "", limit: int = 20) -> list[dict[str, Any]]:
    return suggest_related_commands(query, limit=limit)


def search_workflows(query: str = "", limit: int = 10) -> list[dict[str, Any]]:
    """Return module-level operational flows as deterministic workflow results."""
    query = query.strip()
    results: list[dict[str, Any]] = []
    for module in _module_index():
        if query and _keyword_score(query, module) == 0:
            continue
        results.append(
            {
                "topic": module.title,
                "summary": module.summary,
                "commands": list(module.commands[:8]),
                "keywords": list(module.tags),
                "source_file": str(module.file_path.relative_to(PROJECT_ROOT)),
                "score": _keyword_score(query, module) if query else 1,
            }
        )
    return sorted(results, key=lambda item: (-item["score"], item["source_file"]))[:limit]


def retrieve_examples(query: str = "", limit: int = 10) -> list[dict[str, Any]]:
    """Return deterministic example entries from local JSON examples."""
    query = query.strip()
    results: list[dict[str, Any]] = []
    for entry in _example_index():
        searchable = " ".join([entry.entry_id, entry.command, entry.category, " ".join(entry.tags), entry.notes])
        score = 1 if not query else 0
        if query:
            normalized_query = _normalize_text(query)
            normalized_searchable = _normalize_text(searchable)
            if normalized_query and normalized_query in normalized_searchable:
                score += 20
            for token in _tokenize(query):
                if token in normalized_searchable.split():
                    score += 6
        if score:
            results.append(
                {
                    "topic": entry.entry_id,
                    "summary": entry.notes or entry.command,
                    "commands": [entry.command, *entry.related_commands][:8],
                    "keywords": list(entry.tags),
                    "source_file": str(entry.file_path.relative_to(PROJECT_ROOT)),
                    "score": score,
                }
            )
    return sorted(results, key=lambda item: (-item["score"], item["source_file"]))[:limit]


def library_status() -> dict[str, Any]:
    library = detect_rhcsa_library()
    files = [path for path in library.rglob("*") if path.is_file()] if library.exists() else []
    modules = _module_index()
    examples = _example_index()
    unique_commands = {command.split()[0] for module in modules for command in module.commands if command.strip()}
    command_examples = sum(len(module.commands) for module in modules) + len(examples)
    return {
        "path": str(library),
        "exists": library.exists(),
        "files": len(files),
        "indexed_topics": len(modules),
        "indexed_command_names": len(unique_commands),
        "indexed_command_examples": command_examples,
        "indexed_workflows": len(modules),
        "indexed_examples": len(examples),
        "size_bytes": sum(path.stat().st_size for path in files),
    }


def _format_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No RHCSA results found."
    lines: list[str] = []
    for result in results:
        lines.append(f"{result['topic']} [{result['category']}]")
        lines.append(f"  file: {result['file_location']}")
        if result.get("tags"):
            lines.append(f"  tags: {', '.join(result['tags'][:10])}")
        if result.get("related_commands"):
            lines.append(f"  commands: {', '.join(result['related_commands'][:8])}")
        if result.get("summary"):
            lines.append(f"  summary: {result['summary']}")
        if result.get("preview"):
            lines.append(f"  preview: {result['preview']}")
        lines.append("")
    return "\n".join(lines).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local deterministic RHCSA knowledge base.")
    parser.add_argument(
        "mode",
        choices=[
            "status",
            "search",
            "topic",
            "commands",
            "workflows",
            "examples",
            "tag",
            "exact",
            "grep",
            "filter",
        ],
    )
    parser.add_argument("query", nargs="*", help="Search query or topic name")
    args = parser.parse_args()
    query = " ".join(args.query)

    if args.mode == "status":
        print(json.dumps(library_status(), indent=2, ensure_ascii=False))
    elif args.mode == "search":
        print(_format_results(search_rhcsa(query)))
    elif args.mode == "topic":
        print(load_topic(query) or "Topic not found.")
    elif args.mode == "commands":
        print(json.dumps(suggest_related_commands(query), indent=2, ensure_ascii=False))
    elif args.mode == "workflows":
        print(json.dumps(search_workflows(query), indent=2, ensure_ascii=False))
    elif args.mode == "examples":
        print(json.dumps(retrieve_examples(query), indent=2, ensure_ascii=False))
    elif args.mode == "tag":
        print(_format_results(search_by_tag(query)))
    elif args.mode == "exact":
        print(_format_results(exact_command_lookup(query)))
    elif args.mode == "grep":
        print(_format_results(grep_rhcsa(query)))
    elif args.mode == "filter":
        parts = query.split(maxsplit=1)
        if len(parts) != 2:
            print("Usage: rhcsa_search.py filter TOPIC QUERY")
        else:
            print(_format_results(filter_by_topic(parts[0], parts[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

