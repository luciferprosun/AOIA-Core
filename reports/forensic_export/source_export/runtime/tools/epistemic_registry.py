#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
PROVENANCE_REGISTRY_PATH = PROJECT_ROOT / "provenance_registry.json"
CONTRADICTION_REGISTRY_PATH = PROJECT_ROOT / "contradiction_registry.json"

FRONTMATTER_KEYS = {
    "title",
    "topic",
    "source_section",
    "source_pdf",
    "generated_from",
    "tags",
}


@dataclass(frozen=True)
class KnowledgeArtifact:
    path: Path
    artifact_type: str
    metadata: dict[str, Any]
    references: tuple[str, ...]
    commands: tuple[str, ...]
    content_hash: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_command(value: str) -> str:
    return " ".join(value.strip().split())


def _file_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return path.as_posix()


def _parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    payload: dict[str, Any] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def _parse_tags(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [item.strip() for item in text.split(",") if item.strip()]


def _extract_markdown_commands(text: str) -> list[str]:
    return [match.strip() for match in re.findall(r"^### `([^`]+)`", text, flags=re.MULTILINE) if match.strip()]


def _extract_example_commands(payload: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    command = str(payload.get("command", "")).strip()
    if command:
        commands.append(command)
    for example in payload.get("examples", []):
        if isinstance(example, dict):
            sample = str(example.get("input", "")).strip()
            if sample:
                commands.append(sample)
    return commands


def _extract_generic_json_commands(payload: Any) -> list[str]:
    commands: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"command", "commands", "related_commands"}:
                    if isinstance(value, str):
                        cleaned = value.strip()
                        if cleaned:
                            commands.append(cleaned)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and item.strip():
                                commands.append(item.strip())
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return commands


def _extract_internal_references(text: str, current_path: Path, known_paths: set[str]) -> list[str]:
    refs: set[str] = set()
    markdown_link_matches = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    code_path_matches = re.findall(r"`([^`\n]*knowledge/[^`\n]+)`", text)
    frontmatter_path_matches = re.findall(r"(?m)^(?:source_pdf|generated_from):\s+(.+)$", text)
    candidates = markdown_link_matches + code_path_matches + frontmatter_path_matches

    for candidate in candidates:
        raw = candidate.strip().strip("<>").strip()
        if not raw:
            continue
        normalized = raw.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized.startswith("../"):
            resolved = (current_path.parent / normalized).resolve()
            try:
                normalized = str(resolved.relative_to(PROJECT_ROOT)).replace("\\", "/")
            except ValueError:
                continue
        if normalized in known_paths:
            refs.add(normalized)
    return sorted(refs)


def _build_artifact(path: Path, known_paths: set[str]) -> KnowledgeArtifact:
    text = _read_text(path)
    if path.suffix == ".md":
        frontmatter = _parse_frontmatter(text)
        metadata = {key: value for key, value in frontmatter.items() if key in FRONTMATTER_KEYS}
        if "tags" in metadata:
            metadata["tags"] = _parse_tags(str(metadata["tags"]))
        metadata.setdefault("title", path.stem)
        metadata.setdefault("topic", path.parent.name)
        commands = tuple(dict.fromkeys(_extract_markdown_commands(text)))
        references = tuple(_extract_internal_references(text, path, known_paths))
        return KnowledgeArtifact(
            path=path,
            artifact_type="markdown",
            metadata=metadata,
            references=references,
            commands=commands,
            content_hash=_file_hash(text),
        )

    payload = json.loads(text)
    if isinstance(payload, dict):
        metadata = {
            "id": payload.get("id", path.stem),
            "category": payload.get("category", ""),
            "risk": payload.get("risk", ""),
            "tags": [str(item).strip() for item in payload.get("tags", []) if str(item).strip()],
        }
        commands = tuple(dict.fromkeys(_extract_example_commands(payload)))
        artifact_type = "json_example" if path.parent.name == "examples" else "json_document"
    else:
        metadata = {
            "id": path.stem,
            "category": path.parent.name,
            "risk": "",
            "tags": [],
        }
        commands = tuple(dict.fromkeys(_extract_generic_json_commands(payload)))
        artifact_type = "json_index"
    references = tuple(_extract_internal_references(text, path, known_paths))
    return KnowledgeArtifact(
        path=path,
        artifact_type=artifact_type,
        metadata=metadata,
        references=references,
        commands=commands,
        content_hash=_file_hash(text),
    )


def discover_knowledge_artifacts(root: Path = KNOWLEDGE_ROOT) -> tuple[KnowledgeArtifact, ...]:
    candidate_paths = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".md", ".json"}:
            continue
        if "__pycache__" in path.parts:
            continue
        candidate_paths.append(path)
    known_paths = {str(path.relative_to(PROJECT_ROOT)).replace("\\", "/") for path in candidate_paths}
    artifacts = [_build_artifact(path, known_paths) for path in sorted(candidate_paths)]
    return tuple(artifacts)


def build_reference_graph(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, list[str]]:
    return {
        _display_path(artifact.path): list(artifact.references)
        for artifact in artifacts
    }


def detect_self_references(graph: dict[str, list[str]]) -> list[dict[str, Any]]:
    findings = []
    for node, refs in sorted(graph.items()):
        if node in refs:
            findings.append(
                {
                    "type": "self_reference",
                    "artifact": node,
                    "reference": node,
                    "status": "unresolved",
                }
            )
    return findings


def detect_circular_references(graph: dict[str, list[str]]) -> list[dict[str, Any]]:
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue
            if neighbor in path:
                cycle = path[path.index(neighbor):] + [neighbor]
                normalized_cycle = _normalize_cycle(cycle)
                cycles.add(normalized_cycle)
                continue
            visit(neighbor, path + [neighbor])

    for node in sorted(graph):
        visit(node, [node])

    findings = []
    for cycle in sorted(cycles):
        findings.append(
            {
                "type": "circular_reference",
                "cycle": list(cycle),
                "status": "unresolved",
            }
        )
    return findings


def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
    if len(cycle) <= 1:
        return tuple(cycle)
    ring = cycle[:-1]
    rotations = [tuple(ring[index:] + ring[:index] + [ring[index]]) for index in range(len(ring))]
    return min(rotations)


def detect_duplicate_commands(artifacts: tuple[KnowledgeArtifact, ...]) -> list[dict[str, Any]]:
    command_map: dict[str, list[str]] = defaultdict(list)
    for artifact in artifacts:
        if artifact.artifact_type not in {"markdown", "json_example"}:
            continue
        rel_path = _display_path(artifact.path)
        for command in artifact.commands:
            normalized = _normalize_command(command)
            if normalized:
                command_map[normalized].append(rel_path)

    findings = []
    for command, sources in sorted(command_map.items()):
        unique_sources = sorted(dict.fromkeys(sources))
        if len(unique_sources) > 1:
            findings.append(
                {
                    "type": "duplicate_command",
                    "command": command,
                    "sources": unique_sources,
                    "status": "unresolved",
                }
            )
    return findings


def detect_duplicate_artifacts(artifacts: tuple[KnowledgeArtifact, ...]) -> list[dict[str, Any]]:
    hash_map: dict[str, list[str]] = defaultdict(list)
    for artifact in artifacts:
        rel_path = _display_path(artifact.path)
        hash_map[artifact.content_hash].append(rel_path)

    findings = []
    for content_hash, sources in sorted(hash_map.items()):
        unique_sources = sorted(dict.fromkeys(sources))
        if len(unique_sources) > 1:
            findings.append(
                {
                    "type": "duplicate_content",
                    "content_hash": content_hash,
                    "sources": unique_sources,
                    "status": "unresolved",
                }
            )
    return findings


def build_provenance_registry(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, Any]:
    records = []
    for artifact in artifacts:
        rel_path = _display_path(artifact.path)
        record = {
            "artifact": rel_path,
            "artifact_type": artifact.artifact_type,
            "metadata": artifact.metadata,
            "references": list(artifact.references),
            "command_count": len(artifact.commands),
            "content_hash": artifact.content_hash,
        }
        records.append(record)
    return {
        "generated_at": dt.datetime.now().isoformat(),
        "root": "knowledge",
        "artifact_count": len(records),
        "records": records,
    }


def build_contradiction_registry(artifacts: tuple[KnowledgeArtifact, ...]) -> dict[str, Any]:
    graph = build_reference_graph(artifacts)
    self_references = detect_self_references(graph)
    circular_references = detect_circular_references(graph)
    duplicate_commands = detect_duplicate_commands(artifacts)
    duplicate_artifacts = detect_duplicate_artifacts(artifacts)
    return {
        "generated_at": dt.datetime.now().isoformat(),
        "root": "knowledge",
        "policy": {
            "automatic_resolution": False,
            "note": "Contradictions and epistemic conflicts are reported only. No automatic resolution is performed.",
        },
        "summary": {
            "self_reference_count": len(self_references),
            "circular_reference_count": len(circular_references),
            "duplicate_command_count": len(duplicate_commands),
            "duplicate_artifact_count": len(duplicate_artifacts),
        },
        "reference_graph": graph,
        "self_references": self_references,
        "circular_references": circular_references,
        "duplicate_commands": duplicate_commands,
        "duplicate_artifacts": duplicate_artifacts,
    }


def write_registries(
    provenance_path: Path = PROVENANCE_REGISTRY_PATH,
    contradiction_path: Path = CONTRADICTION_REGISTRY_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    artifacts = discover_knowledge_artifacts()
    provenance = build_provenance_registry(artifacts)
    contradictions = build_contradiction_registry(artifacts)
    provenance_path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    contradiction_path.write_text(json.dumps(contradictions, indent=2, ensure_ascii=False), encoding="utf-8")
    return provenance, contradictions


def main() -> int:
    provenance, contradictions = write_registries()
    print(
        json.dumps(
            {
                "provenance_registry": str(PROVENANCE_REGISTRY_PATH.relative_to(PROJECT_ROOT)),
                "contradiction_registry": str(CONTRADICTION_REGISTRY_PATH.relative_to(PROJECT_ROOT)),
                "artifact_count": provenance["artifact_count"],
                "duplicate_command_count": contradictions["summary"]["duplicate_command_count"],
                "circular_reference_count": contradictions["summary"]["circular_reference_count"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
