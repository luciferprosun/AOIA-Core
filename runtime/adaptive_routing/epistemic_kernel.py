from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adaptive_routing.deterministic_router import select_depth
from retrieval.facade import retrieve_linux_knowledge
from retrieval.linux.scoring import EXACT_MATCH_SCORE, confidence_for
from tools.epistemic_registry import (
    CONTRADICTION_REGISTRY_PATH,
    PROVENANCE_REGISTRY_PATH,
    build_contradiction_registry,
    build_provenance_registry,
    discover_knowledge_artifacts,
)


LINUX_OPERATIONAL_HINTS = {
    "bash",
    "chmod",
    "chown",
    "cron",
    "df",
    "dnf",
    "du",
    "firewall",
    "firewalld",
    "fstab",
    "grep",
    "journalctl",
    "linux",
    "ls",
    "lvm",
    "mkdir",
    "mount",
    "network",
    "nmcli",
    "podman",
    "ps",
    "pwd",
    "restorecon",
    "rhcsa",
    "rpm",
    "selinux",
    "service",
    "ssh",
    "sshd",
    "sudo",
    "systemctl",
    "systemd",
    "tar",
    "touch",
    "useradd",
    "vi",
    "vim",
}

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
class KernelDecision:
    should_respond_locally: bool
    route: str
    depth: str
    pressure: int
    confidence: str
    response: str
    manual_review_required: bool
    manual_review_reasons: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    reasoning: dict[str, Any]


class AOIAEpistemicKernel:
    """Deterministic epistemic control layer for local AOIA retrieval."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self._provenance = self._load_registry(
            PROVENANCE_REGISTRY_PATH,
            lambda: build_provenance_registry(discover_knowledge_artifacts()),
        )
        self._contradictions = self._load_registry(
            CONTRADICTION_REGISTRY_PATH,
            lambda: build_contradiction_registry(discover_knowledge_artifacts()),
        )
        self._provenance_by_artifact = {
            str(record.get("artifact", "")): record
            for record in self._provenance.get("records", [])
            if isinstance(record, dict) and record.get("artifact")
        }
        self._duplicate_commands = tuple(
            item for item in self._contradictions.get("duplicate_commands", []) if isinstance(item, dict)
        )
        self._duplicate_sources = self._build_duplicate_source_index(self._duplicate_commands)

    def evaluate(self, user_request: str) -> KernelDecision:
        topic_filter = self._detect_topic_filter(user_request)
        retrieval_response = retrieve_linux_knowledge(user_request, max_results=6, project_dir=self.project_dir)
        evidence = self._merge_results([dict(item) for item in retrieval_response.results])
        confidence = self._confidence(evidence, retrieval_response.confidence_score)
        pressure = self._pressure(
            user_request,
            evidence,
            retrieval_response.confidence_score,
            retrieval_response.match_type,
            topic_filter,
        )
        depth = select_depth(pressure)
        contradiction_hits = self._contradiction_hits(user_request, evidence)
        manual_review_reasons = self._manual_review_reasons(confidence, contradiction_hits, evidence)
        manual_review_required = bool(manual_review_reasons)
        should_respond_locally = self._looks_linux_operational(user_request) and bool(evidence)
        route = "local_knowledge" if should_respond_locally else "model_fallback"
        response = self._format_response(
            user_request=user_request,
            route=route,
            depth=depth,
            pressure=pressure,
            confidence=confidence,
            evidence=evidence,
            contradiction_hits=contradiction_hits,
            manual_review_required=manual_review_required,
        )
        reasoning = {
            "query": user_request,
            "route": route,
            "topic_filter": topic_filter,
            "retrieval_match_type": retrieval_response.match_type,
            "retrieval_status": retrieval_response.status,
            "pressure": pressure,
            "depth": depth,
            "confidence": confidence,
            "evidence_count": len(evidence),
            "manual_review_required": manual_review_required,
            "manual_review_reasons": list(manual_review_reasons),
            "contradiction_count": len(contradiction_hits),
        }
        return KernelDecision(
            should_respond_locally=should_respond_locally,
            route=route,
            depth=depth,
            pressure=pressure,
            confidence=confidence,
            response=response,
            manual_review_required=manual_review_required,
            manual_review_reasons=manual_review_reasons,
            evidence=tuple(evidence),
            reasoning=reasoning,
        )

    def _load_registry(self, path: Path, fallback: Any) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return fallback()

    def _detect_topic_filter(self, user_request: str) -> str | None:
        lowered = user_request.lower()
        for topic in TOPIC_DIRECTORIES:
            normalized = topic.lower()
            if normalized in lowered:
                return topic
        return None

    def _pressure(
        self,
        user_request: str,
        evidence: list[dict[str, Any]],
        retrieval_score: int,
        match_type: str,
        topic_filter: str | None,
    ) -> int:
        tokens = [token for token in re.split(r"\s+", user_request.strip()) if token]
        pressure = min(len(tokens) * 4, 40)
        if self._looks_linux_operational(user_request):
            pressure += 20
        if topic_filter:
            pressure += 10
        if retrieval_score >= EXACT_MATCH_SCORE or match_type in {"exact", "alias", "subcommand"}:
            pressure += 20
        elif evidence:
            pressure += 5
        return min(pressure, 100)

    def _merge_results(self, *result_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for result_set in result_sets:
            for item in result_set:
                path = str(item.get("file_location", "")).strip()
                if not path:
                    continue
                enriched = self._enrich_evidence(item)
                current = merged.get(path)
                if current is None or int(enriched.get("score", 0)) > int(current.get("score", 0)):
                    merged[path] = enriched
        return sorted(merged.values(), key=lambda item: (-int(item.get("score", 0)), item["file_location"]))[:6]

    def _confidence(self, evidence: list[dict[str, Any]], retrieval_score: int) -> str:
        if not evidence:
            return "none"
        return confidence_for(retrieval_score)

    def _enrich_evidence(self, item: dict[str, Any]) -> dict[str, Any]:
        path = str(item.get("file_location", "")).strip()
        provenance = self._provenance_by_artifact.get(path, {})
        contradictions = self._duplicate_sources.get(path, [])
        attached_provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
        return {
            **item,
            "provenance": {
                **attached_provenance,
                "artifact_type": provenance.get("artifact_type", ""),
                "metadata": provenance.get("metadata", {}),
                "references": provenance.get("references", []),
                "content_hash": provenance.get("content_hash", ""),
            },
            "contradictions": contradictions,
        }

    def _contradiction_hits(self, user_request: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized_query = self._normalize_command(user_request)
        evidence_sources = {str(item.get("file_location", "")) for item in evidence}
        hits: list[dict[str, Any]] = []
        for duplicate in self._duplicate_commands:
            command = self._normalize_command(str(duplicate.get("command", "")))
            sources = [str(source) for source in duplicate.get("sources", []) if str(source)]
            if normalized_query and normalized_query == command:
                hits.append(duplicate)
                continue
            if evidence_sources.intersection(sources):
                hits.append(duplicate)
        deduped: dict[str, dict[str, Any]] = {}
        for hit in hits:
            key = str(hit.get("command", "")) or json.dumps(hit, sort_keys=True, ensure_ascii=False)
            deduped[key] = hit
        return list(deduped.values())

    def _manual_review_reasons(
        self,
        confidence: str,
        contradiction_hits: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if confidence in {"low", "none"}:
            reasons.append(f"confidence_{confidence}")
        if contradiction_hits:
            reasons.append("duplicate_or_conflicting_sources_detected")
        if not evidence:
            reasons.append("no_local_evidence")
        return tuple(reasons)

    def _format_response(
        self,
        user_request: str,
        route: str,
        depth: str,
        pressure: int,
        confidence: str,
        evidence: list[dict[str, Any]],
        contradiction_hits: list[dict[str, Any]],
        manual_review_required: bool,
    ) -> str:
        lines = [
            "AOIA deterministic epistemic kernel hit.",
            f"Route: {route}",
            f"Routing depth: {depth}",
            f"Pressure score: {pressure}",
            f"Confidence: {confidence.upper()}",
            "",
        ]
        if evidence:
            lines.append("Evidence:")
            for item in evidence[:4]:
                metadata = item.get("provenance", {}).get("metadata", {})
                source_pdf = str(metadata.get("source_pdf", "")).strip()
                source_section = str(metadata.get("source_section", "")).strip()
                lines.append(f"- {item.get('topic')} [{item.get('category')}] -> {item.get('file_location')}")
                if item.get("related_commands"):
                    lines.append(f"  commands: {', '.join(item.get('related_commands', [])[:5])}")
                if source_section or source_pdf:
                    provenance_bits = [part for part in (source_section, source_pdf) if part]
                    lines.append(f"  provenance: {' | '.join(provenance_bits)}")
        else:
            lines.append(f"No deterministic local evidence found for: {user_request}")

        if contradiction_hits:
            lines.append("")
            lines.append("Contradiction notices:")
            for hit in contradiction_hits[:4]:
                lines.append(f"- {hit.get('command')}: {', '.join(hit.get('sources', [])[:4])}")

        lines.append("")
        lines.append(
            "Manual review: REQUIRED"
            if manual_review_required
            else "Manual review: optional"
        )
        lines.append("Policy: contradictions are reported only; no automatic resolution is performed.")
        return "\n".join(lines).strip()

    @staticmethod
    def _build_duplicate_source_index(duplicates: tuple[dict[str, Any], ...]) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = {}
        for item in duplicates:
            for source in item.get("sources", []):
                normalized = str(source).strip()
                if not normalized:
                    continue
                index.setdefault(normalized, []).append(item)
        return index

    @staticmethod
    def _normalize_command(value: str) -> str:
        return " ".join(value.strip().split()).lower()

    @staticmethod
    def _looks_linux_operational(text: str) -> bool:
        lowered = text.lower()
        if any(token in lowered for token in LINUX_OPERATIONAL_HINTS):
            return True
        return bool(re.search(r"\b[a-z0-9_-]+\s+-", lowered))
