from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.memory_hats.unix_hat import (
    UnixHatDescriptor,
    UnixRouteProposal,
    UnixRouteRequest,
    propose_unix_route as _propose_unix_route_metadata,
)
from runtime_paths import runtime_state_dir


ROUTE_SCHEMA_VERSION = "knowledge-route-proposal-1a"
RETRIEVAL_REQUEST_SCHEMA_VERSION = "knowledge-retrieval-request-1a"
REPORT_SCHEMA_VERSION = "token-savings-report-inert-1a"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"

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


@dataclass(frozen=True, slots=True)
class RouteConfidenceMetadata:
    label: str
    score: int
    basis: str

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "score": self.score,
            "basis": self.basis,
        }


@dataclass(frozen=True, slots=True)
class RetrievalRequestMetadata:
    schema_version: str
    request_id: str
    query: str
    query_hash: str
    route_id: str
    hat_id: str
    max_results: int
    execution_allowed: bool
    requires_explicit_caller: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "query": self.query,
            "query_hash": self.query_hash,
            "route_id": self.route_id,
            "hat_id": self.hat_id,
            "max_results": self.max_results,
            "execution_allowed": self.execution_allowed,
            "requires_explicit_caller": self.requires_explicit_caller,
        }


@dataclass(frozen=True, slots=True)
class TokenSavingsReportData:
    schema_version: str
    request_id: str
    route_status: str
    retrieval_executed: bool
    filesystem_persisted: bool
    api_calls_avoided: int
    authority_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "route_status": self.route_status,
            "retrieval_executed": self.retrieval_executed,
            "filesystem_persisted": self.filesystem_persisted,
            "api_calls_avoided": self.api_calls_avoided,
            "authority_status": self.authority_status,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeRouteProposal:
    """Immutable, non-authoritative routing metadata.

    The proposal deliberately contains no retrieval result, callback, module,
    writer, or execution capability. A caller may inspect ``retrieval_request``
    and separately invoke the read-only retrieval facade.
    """

    schema_version: str
    request_id: str
    normalized_query: str
    query_hash: str
    selected_route_id: str | None
    selected_hat_id: str | None
    route_status: str
    route_rationale: str
    confidence_metadata: RouteConfidenceMetadata
    retrieval_request: RetrievalRequestMetadata | None
    report_data: TokenSavingsReportData
    authority_status: str
    warnings: tuple[str, ...]

    @property
    def should_handle_locally(self) -> bool:
        """Compatibility field: routing never handles or retrieves locally."""
        return False

    @property
    def confidence(self) -> str:
        return self.confidence_metadata.label

    @property
    def reason(self) -> str:
        return self.route_rationale

    @property
    def response(self) -> str:
        return ""

    @property
    def hit(self) -> None:
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "normalized_query": self.normalized_query,
            "query_hash": self.query_hash,
            "selected_route_id": self.selected_route_id,
            "selected_hat_id": self.selected_hat_id,
            "route_status": self.route_status,
            "route_rationale": self.route_rationale,
            "confidence_metadata": self.confidence_metadata.to_dict(),
            "retrieval_request": (
                self.retrieval_request.to_dict()
                if self.retrieval_request is not None
                else None
            ),
            "report_data": self.report_data.to_dict(),
            "authority_status": self.authority_status,
            "warnings": list(self.warnings),
        }


# Compatibility import name. The object is now an inert route proposal.
KnowledgeDecision = KnowledgeRouteProposal


class KnowledgeRouter:
    """Classify a request and return inert route metadata only."""

    def __init__(
        self,
        project_dir: Path,
        engine: Any | None = None,
        retriever: Any | None = None,
    ) -> None:
        # Compatibility arguments are intentionally neither stored nor invoked.
        # Their field values cannot influence route selection or authority.
        del engine, retriever
        self.project_dir = Path(project_dir)
        self.report_path = (
            runtime_state_dir(self.project_dir)
            / "state"
            / "token_savings_report.json"
        )

    def route(
        self,
        user_request: str,
        active_hat: dict[str, Any] | None = None,
    ) -> KnowledgeRouteProposal:
        # Hat/provider/pheromone metadata cannot force routing. The parameter is
        # retained for API compatibility but is deliberately not inspected.
        del active_hat
        normalized_query, warnings = self._normalize_query(user_request)
        query_hash = hashlib.sha256(
            normalized_query.encode("utf-8")
        ).hexdigest()
        request_id = f"knowledge-route-{query_hash[:20]}"
        matched_hints = self._matched_linux_hints(normalized_query)

        if not normalized_query or not matched_hints:
            route_status = "NO_ROUTE"
            route_id = None
            hat_id = None
            rationale = "not_linux_operational"
            confidence = RouteConfidenceMetadata(
                label="none",
                score=0,
                basis="no_supported_route_match",
            )
        elif self._is_ambiguous(normalized_query, matched_hints):
            route_status = "REVIEW_NEEDED"
            route_id = None
            hat_id = None
            rationale = "ambiguous_linux_route_request"
            confidence = RouteConfidenceMetadata(
                label="low",
                score=25,
                basis="linux_hint_without_operational_context",
            )
        else:
            route_status = "ROUTE_PROPOSED"
            route_id = "linux_rhcsa_retrieval_v1"
            hat_id = "hat_002"
            rationale = "linux_operational_route_proposed"
            confidence = RouteConfidenceMetadata(
                label="medium",
                score=60,
                basis="deterministic_linux_operational_hint_match",
            )

        retrieval_request = None
        if route_id is not None and hat_id is not None:
            retrieval_request = RetrievalRequestMetadata(
                schema_version=RETRIEVAL_REQUEST_SCHEMA_VERSION,
                request_id=request_id,
                query=normalized_query,
                query_hash=query_hash,
                route_id=route_id,
                hat_id=hat_id,
                max_results=6,
                execution_allowed=False,
                requires_explicit_caller=True,
            )

        report_data = TokenSavingsReportData(
            schema_version=REPORT_SCHEMA_VERSION,
            request_id=request_id,
            route_status=route_status,
            retrieval_executed=False,
            filesystem_persisted=False,
            api_calls_avoided=0,
            authority_status=NON_AUTHORITATIVE,
        )
        return KnowledgeRouteProposal(
            schema_version=ROUTE_SCHEMA_VERSION,
            request_id=request_id,
            normalized_query=normalized_query,
            query_hash=query_hash,
            selected_route_id=route_id,
            selected_hat_id=hat_id,
            route_status=route_status,
            route_rationale=rationale,
            confidence_metadata=confidence,
            retrieval_request=retrieval_request,
            report_data=report_data,
            authority_status=NON_AUTHORITATIVE,
            warnings=warnings,
        )

    @staticmethod
    def propose_unix_route(
        request: UnixRouteRequest,
        descriptor: UnixHatDescriptor,
    ) -> UnixRouteProposal:
        """Return canonical UNIX route metadata without invoking retrieval."""

        return _propose_unix_route_metadata(request, descriptor)

    @staticmethod
    def _normalize_query(user_request: str) -> tuple[str, tuple[str, ...]]:
        if not isinstance(user_request, str):
            return "", ("invalid_query_type",)
        return " ".join(user_request.split()).casefold(), ()

    @staticmethod
    def _matched_linux_hints(normalized_query: str) -> tuple[str, ...]:
        return tuple(
            hint
            for hint in sorted(LINUX_OPERATIONAL_HINTS)
            if hint in normalized_query
        )

    @staticmethod
    def _is_ambiguous(
        normalized_query: str,
        matched_hints: tuple[str, ...],
    ) -> bool:
        return len(normalized_query.split()) < 2 or normalized_query in matched_hints

    @staticmethod
    def render_token_savings_report(
        proposal: KnowledgeRouteProposal | None = None,
    ) -> dict[str, object]:
        """Render report metadata without filesystem persistence."""
        if proposal is None:
            return {
                "schema_version": REPORT_SCHEMA_VERSION,
                "request_id": "",
                "route_status": "NOT_EVALUATED",
                "retrieval_executed": False,
                "filesystem_persisted": False,
                "api_calls_avoided": 0,
                "authority_status": NON_AUTHORITATIVE,
            }
        return proposal.report_data.to_dict()

    def write_token_savings_report(
        self,
        proposal: KnowledgeRouteProposal | None = None,
    ) -> dict[str, object]:
        """Compatibility method returning inert data; it performs no write."""
        return self.render_token_savings_report(proposal)
