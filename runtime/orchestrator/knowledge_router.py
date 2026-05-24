from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from retrieval.facade import retrieve_linux_knowledge


LINUX_OPERATIONAL_HINTS = {
    "bash",
    "boot",
    "chmod",
    "chown",
    "cron",
    "dnf",
    "firewall",
    "firewalld",
    "fstab",
    "journalctl",
    "linux",
    "lvm",
    "mount",
    "network",
    "nginx",
    "nmcli",
    "podman",
    "rhel",
    "rhcsa",
    "root password",
    "selinux",
    "service",
    "ssh",
    "sshd",
    "systemctl",
    "systemd",
    "useradd",
}


@dataclass
class KnowledgeDecision:
    should_handle_locally: bool
    confidence: str
    reason: str
    response: str
    hit: Any | None


class KnowledgeRouter:
    """Decides whether local RHCSA memory can answer before API reasoning."""

    def __init__(
        self,
        project_dir: Path,
        engine: Any | None = None,
        retriever: Callable[[str], Any] | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.engine = engine
        if retriever is not None:
            self.retrieve = retriever
        elif engine is not None and hasattr(engine, "retrieve_operational_memory"):
            self.retrieve = engine.retrieve_operational_memory
        else:
            self.retrieve = lambda query: retrieve_linux_knowledge(query, max_results=6, project_dir=project_dir)
        self.report_path = project_dir / "state" / "token_savings_report.json"
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_report()

    def route(self, user_request: str, active_hat: dict[str, Any] | None = None) -> KnowledgeDecision:
        if not self._looks_linux_operational(user_request, active_hat):
            return KnowledgeDecision(False, "none", "not_linux_operational", "", None)

        hit = self.retrieve(user_request)
        prefer_local = self._hat_prefers_local(active_hat)
        threshold = {"linux": "low", "coding": "medium", "research": "high"}.get(
            str((active_hat or {}).get("name", "")).lower(),
            "medium",
        )
        if prefer_local:
            threshold = "low"

        if self._meets_threshold(hit.confidence, threshold):
            response = self._format_hit_response(hit)
            self.record_local_hit(hit, avoided_reason="local_rhcsa_memory")
            return KnowledgeDecision(True, hit.confidence, "local_rhcsa_memory", response, hit)

        self.record_miss(user_request, hit.confidence)
        return KnowledgeDecision(False, hit.confidence, "low_confidence_local_memory", "", hit)

    def record_local_hit(self, hit: Any, avoided_reason: str) -> None:
        report = self._read_report()
        report["api_calls_avoided"] = int(report.get("api_calls_avoided", 0)) + 1
        report["local_retrieval_hits"] = int(report.get("local_retrieval_hits", 0)) + 1
        report["command_reuse_frequency"] = int(report.get("command_reuse_frequency", 0)) + self._hit_count(hit)
        report["workflow_reuse"] = int(report.get("workflow_reuse", 0)) + len(getattr(hit, "workflows", ()))
        report["last_hit"] = {
            "timestamp": dt.datetime.now().isoformat(),
            "query": getattr(hit, "query", ""),
            "confidence": getattr(hit, "confidence", "none"),
            "score": getattr(hit, "confidence_score", getattr(hit, "score", 0)),
            "reason": avoided_reason,
        }
        self._write_report(report)

    def record_miss(self, query: str, confidence: str) -> None:
        report = self._read_report()
        report["local_retrieval_misses"] = int(report.get("local_retrieval_misses", 0)) + 1
        report["last_miss"] = {
            "timestamp": dt.datetime.now().isoformat(),
            "query": query,
            "confidence": confidence,
        }
        self._write_report(report)

    def _looks_linux_operational(self, text: str, active_hat: dict[str, Any] | None) -> bool:
        lowered = text.lower()
        if self._hat_prefers_local(active_hat):
            return any(token in lowered for token in LINUX_OPERATIONAL_HINTS)
        return any(token in lowered for token in LINUX_OPERATIONAL_HINTS)

    @staticmethod
    def _hat_prefers_local(active_hat: dict[str, Any] | None) -> bool:
        if not active_hat:
            return False
        name = str(active_hat.get("name", "")).lower()
        role = str(active_hat.get("role", "")).lower()
        instructions = str(active_hat.get("instructions", "")).lower()
        return "linux" in name or "linux" in role or "rhcsa" in instructions

    @staticmethod
    def _meets_threshold(confidence: str, threshold: str) -> bool:
        rank = {"none": 0, "low": 1, "medium": 2, "high": 3}
        return rank.get(confidence, 0) >= rank.get(threshold, 2)

    def _format_hit_response(self, hit: Any) -> str:
        message = getattr(hit, "message", "")
        if message:
            return message
        if self.engine is not None and hasattr(self.engine, "format_local_answer"):
            return self.engine.format_local_answer(hit)
        return ""

    @staticmethod
    def _hit_count(hit: Any) -> int:
        results = getattr(hit, "results", None)
        if results is not None:
            return len(results)
        return len(getattr(hit, "commands", ()))

    def _ensure_report(self) -> None:
        if self.report_path.exists():
            return
        self._write_report(
            {
                "created_at": dt.datetime.now().isoformat(),
                "api_calls_avoided": 0,
                "local_retrieval_hits": 0,
                "local_retrieval_misses": 0,
                "command_reuse_frequency": 0,
                "workflow_reuse": 0,
            }
        )

    def _read_report(self) -> dict[str, Any]:
        try:
            return json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_report(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = dt.datetime.now().isoformat()
        self.report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
