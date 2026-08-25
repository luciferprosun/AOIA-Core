"""Deterministic, non-authoritative comparison for one bounded scenario."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from typing import Any

from .scenario import bundled_scenario

AUTHORITY_MARKER = "METADATA_ONLY_NO_AUTHORITY"
DECISION_STATE = "HUMAN_REVIEW_REQUIRED"
MAX_ANSWER_CHARS = 20_000

_EURO_AMOUNT = re.compile(
    r"(?<!\d)(\d{1,3}(?:[.,]\d{2}))\s*(?:€|euros?)(?![a-z])",
    re.IGNORECASE,
)
_TEMPORAL_MARKERS = re.compile(
    r"\b(?:2026|juli|aktuell|derzeit|gegenwärtig|seit\s+dem|stand[: ]|as\s+of|current(?:ly)?)\b",
    re.IGNORECASE,
)
_SOURCE_MARKERS = re.compile(
    r"(?:https?://|bmas|gesetze-im-internet|milov5|mindestlohnanpassungsverordnung)",
    re.IGNORECASE,
)


class ReviewInputError(ValueError):
    """Fail-closed validation error for evidence-review input."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalise_amount(raw: str) -> str:
    return f"{float(raw.replace(',', '.')):.2f}"


def _extract_amounts(answer: str) -> list[str]:
    return sorted({_normalise_amount(match) for match in _EURO_AMOUNT.findall(answer)})


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    detail: str,
    evidence_ids: Iterable[str] = (),
) -> dict[str, object]:
    return {
        "id": finding_id,
        "severity": severity,
        "title": title,
        "detail": detail,
        "evidence_ids": list(evidence_ids),
    }


def review_candidate(candidate_answer: str) -> dict[str, Any]:
    """Compare one answer with the bundled, dated evidence registry.

    The module detects one known stale value plus missing temporal and source
    attribution. It always returns a human-review state and never approval.
    """

    if not isinstance(candidate_answer, str):
        raise ReviewInputError("candidate_answer must be text")
    candidate_answer = candidate_answer.strip()
    if not candidate_answer:
        raise ReviewInputError("candidate_answer must not be empty")
    if len(candidate_answer) > MAX_ANSWER_CHARS:
        raise ReviewInputError(f"candidate_answer exceeds {MAX_ANSWER_CHARS} characters")

    scenario = bundled_scenario()
    evidence = scenario["evidence"]
    assert isinstance(evidence, list)
    evidence_digest = _digest(evidence)
    snapshot = {
        "scenario_id": scenario["id"],
        "as_of_date": scenario["as_of_date"],
        "prompt": scenario["prompt"],
        "candidate_answer": candidate_answer,
        "evidence_digest": evidence_digest,
    }
    snapshot_hash = _digest(snapshot)

    amounts = _extract_amounts(candidate_answer)
    current_value = str(scenario["expected_current_value"])
    previous_value = str(scenario["known_previous_value"])
    has_current = current_value in amounts
    has_previous = previous_value in amounts
    findings: list[dict[str, object]] = []

    if has_previous and not has_current:
        value_status = "STALE_VALUE_DETECTED"
        findings.append(
            _finding(
                "STALE_STATUTORY_RATE",
                "critical",
                "The answer repeats the 2025 rate",
                (
                    "EUR 12.82 is listed for 2025. The dated 2026 evidence sets the "
                    "general statutory rate at EUR 13.90 from 1 January 2026."
                ),
                (
                    "DE-BMAS-MINIMUM-WAGE-HISTORY",
                    "DE-BMAS-MINDESTLOHN-OVERVIEW-2026",
                    "DE-MILOV5-2025",
                ),
            )
        )
    elif has_previous and has_current:
        value_status = "CONFLICTING_VALUES_DETECTED"
        findings.append(
            _finding(
                "CONFLICTING_RATE_VALUES",
                "critical",
                "The answer contains both the previous and current rates",
                "The answer must clearly separate the 2025 rate from the rate effective in 2026.",
                ("DE-BMAS-MINIMUM-WAGE-HISTORY", "DE-MILOV5-2025"),
            )
        )
    elif has_current:
        value_status = "CURRENT_VALUE_CORROBORATED"
        findings.append(
            _finding(
                "CURRENT_RATE_PRESENT",
                "info",
                "The current rate matches the dated evidence",
                (
                    "EUR 13.90 appears in the answer and in the official evidence "
                    "effective from 1 January 2026."
                ),
                ("DE-BMAS-MINDESTLOHN-OVERVIEW-2026", "DE-MILOV5-2025"),
            )
        )
    else:
        value_status = "CURRENT_VALUE_NOT_ESTABLISHED"
        findings.append(
            _finding(
                "RATE_NOT_CORROBORATED",
                "critical",
                "The current statutory rate is not established",
                "The answer does not state the evidence-registry value of EUR 13.90 for July 2026.",
                ("DE-BMAS-MINDESTLOHN-OVERVIEW-2026", "DE-MILOV5-2025"),
            )
        )

    if not _TEMPORAL_MARKERS.search(candidate_answer):
        findings.append(
            _finding(
                "TEMPORAL_SCOPE_MISSING",
                "warning",
                "No effective date or currency marker",
                "Time-sensitive legal amounts should be bound to a date before a person relies on them.",
                ("DE-BMAS-MINIMUM-WAGE-HISTORY",),
            )
        )

    if not _SOURCE_MARKERS.search(candidate_answer):
        findings.append(
            _finding(
                "OFFICIAL_SOURCE_MISSING",
                "warning",
                "No official source is identified",
                (
                    "The answer makes a high-stakes legal claim without pointing the "
                    "reader to current official evidence."
                ),
                ("DE-BMAS-MINDESTLOHN-OVERVIEW-2026", "DE-MILOV5-2025"),
            )
        )

    counts = {
        severity: sum(1 for item in findings if item["severity"] == severity)
        for severity in ("critical", "warning", "info")
    }
    return {
        "review_id": f"review-{snapshot_hash[:12]}",
        "scenario_id": scenario["id"],
        "as_of_date": scenario["as_of_date"],
        "risk_domain": scenario["risk_domain"],
        "decision_state": DECISION_STATE,
        "authority": AUTHORITY_MARKER,
        "legal_advice": False,
        "network_used": False,
        "value_status": value_status,
        "detected_euro_values": amounts,
        "expected_current_value": current_value,
        "severity_counts": counts,
        "findings": findings,
        "evidence": evidence,
        "evidence_digest": evidence_digest,
        "snapshot_hash": snapshot_hash,
        "operator_next_step": (
            "Inspect the cited official sources, confirm scope and exceptions for the real situation, "
            "and obtain qualified advice when needed."
        ),
        "limitations": [
            "Focused deterministic review, not a general legal reasoning system.",
            "A matching amount does not prove the whole answer is correct or applicable.",
            "The review is metadata only and cannot approve, execute, or decide anything.",
        ],
    }


def format_review_summary(result: dict[str, Any]) -> str:
    """Render a compact, operator-facing summary for the AOIA CLI."""

    counts = result["severity_counts"]
    detected = ", ".join(result["detected_euro_values"]) or "(none)"
    lines = [
        "Dated evidence review:",
        f"  review_id: {result['review_id']}",
        f"  status: {result['value_status']}",
        f"  decision: {result['decision_state']}",
        f"  authority: {result['authority']}",
        f"  detected EUR values: {detected}",
        f"  expected current value: {result['expected_current_value']}",
        (
            "  findings: "
            f"{counts['critical']} critical, {counts['warning']} warning, {counts['info']} info"
        ),
    ]
    for finding in result["findings"]:
        lines.append(f"  - [{str(finding['severity']).upper()}] {finding['title']}")
        lines.append(f"    {finding['detail']}")
    lines.extend(
        [
            f"  evidence digest: {result['evidence_digest']}",
            f"  snapshot hash: {result['snapshot_hash']}",
            f"  next step: {result['operator_next_step']}",
        ]
    )
    return "\n".join(lines)
