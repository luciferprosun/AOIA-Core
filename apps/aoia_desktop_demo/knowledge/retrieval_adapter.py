"""Narrow, read-only retrieval adapter.

This reuses the AOIA-Core production runtime's existing deterministic,
evidence-backed Linux/RHCSA retrieval facade
(``runtime/retrieval/facade.py`` -> ``retrieve_linux_knowledge``), because
that facade is already a safe, read-only, non-executing, non-network
lookup over a committed local index (see repository inspection notes in
the implementation report).

This adapter deliberately:
- never imports the production runtime's provider, execution, patch,
  git, browser, or package-installation modules;
- never calls anything that rebuilds, mutates, or ingests new files into
  the index;
- never executes text found in a retrieved document;
- bounds the number of retrieved items;
- degrades to "no evidence available" on any import or lookup failure,
  rather than raising into the UI.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


class KnowledgeRetrievalUnavailable(Exception):
    """Raised (and caught internally) when the read-only facade cannot be
    reached. Callers should treat this the same as "no evidence found"."""


@dataclass(frozen=True)
class EvidenceItem:
    source_id: str
    title: str
    path: str
    score: int | None
    snippet: str


def _runtime_dir(repo_root: Path) -> Path:
    return repo_root / "runtime"


def _ensure_runtime_on_path(repo_root: Path) -> None:
    """Insert the cloned repo's ``runtime/`` directory at the front of
    ``sys.path`` so the facade's internal ``import retrieval...`` /
    ``import tools...`` statements resolve to the intended package, not
    the unrelated placeholder top-level ``retrieval/`` directory that
    also exists at the repo root."""
    runtime_dir = str(_runtime_dir(repo_root))
    if runtime_dir not in sys.path:
        sys.path.insert(0, runtime_dir)


def retrieve_linux_evidence(repo_root: Path, query: str, max_results: int = 5) -> list[EvidenceItem]:
    """Read-only lookup. Returns an empty list if the index/module is
    unavailable or the query yields no confident match — never raises to
    the UI layer."""
    query = (query or "").strip()
    if not query:
        return []

    try:
        _ensure_runtime_on_path(repo_root)
        from retrieval.facade import retrieve_linux_knowledge  # type: ignore  # noqa: PLC0415
    except Exception:
        return []

    try:
        response = retrieve_linux_knowledge(query, max_results=max_results, project_dir=_runtime_dir(repo_root))
    except Exception:
        return []

    if not getattr(response, "answered", False):
        return []

    evidence: list[EvidenceItem] = []
    for index, result in enumerate(response.results[:max_results]):
        if not isinstance(result, dict):
            continue
        provenance = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
        source_file = str(provenance.get("source_file") or result.get("file_location") or "unknown")
        title = str(result.get("topic") or result.get("command") or f"result-{index}")
        summary = str(result.get("summary") or "")
        preview = str(result.get("preview") or "")
        snippet = summary or preview
        evidence.append(
            EvidenceItem(
                source_id=f"linux_unix:{index}",
                title=title,
                path=source_file,
                score=result.get("score") if isinstance(result.get("score"), int) else None,
                snippet=snippet[:800],
            )
        )
    return evidence
