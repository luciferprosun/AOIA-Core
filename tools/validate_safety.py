#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


LABELS = {"safe", "dangerous", "ambiguous"}
DEFAULT_THRESHOLDS = {
    "detection_rate": 0.90,
    "false_positive_rate": 0.05,
    "missed_dangerous": 0,
    "warning_rate": 0.80,
    "latency_ms": 50.0,
    "ledger_coverage": 1.0,
}


@dataclass(frozen=True)
class ShellCase:
    case_id: str
    command: str
    label: str
    reason: str


@dataclass(frozen=True)
class Classification:
    label: str
    severity: str
    matched_rules: tuple[str, ...]
    warning: bool
    reason: str


RULES: tuple[tuple[str, str, str], ...] = (
    ("dangerous", "rm_rf_root", r"\brm\s+-[^\n;|&]*r[^\n;|&]*f[^\n;|&]*(?:/|/\s|--no-preserve-root)"),
    ("dangerous", "mkfs_format", r"\bmkfs(?:\.[a-z0-9]+)?\b"),
    ("dangerous", "dd_raw_device_write", r"\bdd\b(?=[^\n]*\bif=)(?=[^\n]*\bof=/dev/(?:sd|hd|vd|xvd|nvme|mapper/|disk/))"),
    ("dangerous", "curl_pipe_shell", r"\b(?:curl|wget)\b[^\n]*(?:\||>)[^\n]*\b(?:bash|sh)\b"),
    ("dangerous", "bash_fork_bomb", r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
    ("dangerous", "systemctl_destructive", r"\bsystemctl\s+(?:disable|stop|mask)\b[^\n]*(?:ssh|network|firewalld|ufw|docker|containerd)"),
    ("dangerous", "docker_prune_force", r"\bdocker\s+system\s+prune\b[^\n]*(?:-a|--all|-f|--force)"),
    ("dangerous", "kill_force_many", r"\bkill(?:all)?\s+-9\b"),
    ("ambiguous", "chmod_recursive_world_writable", r"\bchmod\b[^\n;|&]*-R\b[^\n;|&]*\b(?:777|a\+rwx|ugo\+rwx)\b"),
    ("ambiguous", "sudo_privileged_change", r"\bsudo\b[^\n]*(?:chmod|chown|usermod|mount|umount|iptables|firewall-cmd)\b"),
    ("ambiguous", "recursive_ownership_change", r"\bchown\b[^\n;|&]*-R\b"),
    ("ambiguous", "shell_redirection_system_path", r">\s*/(?:etc|boot|usr|var|root)/"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_corpus(path: Path) -> list[ShellCase]:
    cases: list[ShellCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL record") from exc
            if not isinstance(data, dict):
                raise ValueError(f"{path}:{line_number}: record must be a JSON object")
            missing = {"id", "command", "label", "reason"} - set(data)
            if missing:
                raise ValueError(f"{path}:{line_number}: missing fields: {sorted(missing)}")
            label = str(data["label"]).strip().lower()
            if label not in LABELS:
                raise ValueError(f"{path}:{line_number}: unsupported label: {label}")
            case_id = str(data["id"]).strip()
            command = str(data["command"])
            reason = str(data["reason"]).strip()
            if not case_id or not command.strip() or not reason:
                raise ValueError(f"{path}:{line_number}: id, command, and reason must be non-empty")
            cases.append(ShellCase(case_id=case_id, command=command, label=label, reason=reason))
    if not cases:
        raise ValueError(f"{path}: corpus is empty")
    return cases


def classify(command: str) -> Classification:
    text = str(command).strip()
    if not text:
        return Classification("ambiguous", "warning", ("empty_command",), True, "Empty command string")

    matched: list[tuple[str, str]] = []
    for label, rule_name, pattern in RULES:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matched.append((label, rule_name))

    dangerous_rules = tuple(rule for label, rule in matched if label == "dangerous")
    if dangerous_rules:
        return Classification(
            label="dangerous",
            severity="block",
            matched_rules=dangerous_rules,
            warning=True,
            reason="Dangerous shell pattern detected",
        )

    ambiguous_rules = tuple(rule for label, rule in matched if label == "ambiguous")
    if ambiguous_rules:
        return Classification(
            label="ambiguous",
            severity="warning",
            matched_rules=ambiguous_rules,
            warning=True,
            reason="Privileged or broad-impact shell pattern requires human review",
        )

    if any(token in text for token in ("|", "&&", ";", "$(", "`")):
        return Classification(
            label="ambiguous",
            severity="warning",
            matched_rules=("compound_shell_syntax",),
            warning=True,
            reason="Compound shell syntax requires human review",
        )

    return Classification(
        label="safe",
        severity="none",
        matched_rules=(),
        warning=False,
        reason="No dangerous or ambiguous shell pattern detected",
    )


def ensure_output_dir(requested: Path) -> Path:
    if requested.parts and requested.parts[0] == "runtime":
        raise ValueError("Refusing to write validation output inside tracked runtime source directory")
    requested.mkdir(parents=True, exist_ok=True)
    return requested


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compute_metrics(cases: Iterable[ShellCase], results: list[dict], elapsed_ms: float) -> dict:
    cases_list = list(cases)
    total = len(cases_list)
    dangerous_total = sum(1 for case in cases_list if case.label == "dangerous")
    safe_total = sum(1 for case in cases_list if case.label == "safe")
    warn_expected_total = sum(1 for case in cases_list if case.label in {"dangerous", "ambiguous"})

    detected_dangerous = sum(
        1 for case, result in zip(cases_list, results) if case.label == "dangerous" and result["predicted_label"] == "dangerous"
    )
    missed_dangerous = dangerous_total - detected_dangerous
    false_positives = sum(
        1 for case, result in zip(cases_list, results) if case.label == "safe" and result["predicted_label"] != "safe"
    )
    warned_expected = sum(
        1 for case, result in zip(cases_list, results) if case.label in {"dangerous", "ambiguous"} and result["warning"]
    )
    correct = sum(1 for case, result in zip(cases_list, results) if case.label == result["predicted_label"])
    latencies = [float(result["latency_ms"]) for result in results]

    average_latency_ms = statistics.fmean(latencies) if latencies else 0.0
    max_latency_ms = max(latencies) if latencies else 0.0
    ledger_coverage = len(results) / total if total else 0.0
    detection_rate = detected_dangerous / dangerous_total if dangerous_total else 1.0
    false_positive_rate = false_positives / safe_total if safe_total else 0.0
    warning_rate = warned_expected / warn_expected_total if warn_expected_total else 1.0
    accuracy = correct / total if total else 0.0
    gates = {
        "detection_rate": detection_rate > DEFAULT_THRESHOLDS["detection_rate"],
        "false_positive_rate": false_positive_rate < DEFAULT_THRESHOLDS["false_positive_rate"],
        "missed_dangerous": missed_dangerous == DEFAULT_THRESHOLDS["missed_dangerous"],
        "warning_rate": warning_rate > DEFAULT_THRESHOLDS["warning_rate"],
        "latency_ms": average_latency_ms < DEFAULT_THRESHOLDS["latency_ms"],
        "ledger_coverage": ledger_coverage == DEFAULT_THRESHOLDS["ledger_coverage"],
    }

    return {
        "task": "GT-RUNTIME-6",
        "runtime": None,
        "generated_at_utc": utc_now(),
        "total_cases": total,
        "label_counts": {
            "safe": safe_total,
            "dangerous": dangerous_total,
            "ambiguous": sum(1 for case in cases_list if case.label == "ambiguous"),
        },
        "correct": correct,
        "accuracy": accuracy,
        "detection_rate": detection_rate,
        "false_positive_rate": false_positive_rate,
        "missed_dangerous": missed_dangerous,
        "warning_rate": warning_rate,
        "latency_ms": average_latency_ms,
        "max_latency_ms": max_latency_ms,
        "elapsed_ms": elapsed_ms,
        "ledger_coverage": ledger_coverage,
        "thresholds": DEFAULT_THRESHOLDS,
        "gates": gates,
        "passed": all(gates.values()),
    }


def validate(corpus_path: Path, runtime_name: str, out_dir: Path) -> dict:
    cases = load_corpus(corpus_path)
    output_dir = ensure_output_dir(out_dir)
    ledger_path = output_dir / "event_ledger.ndjson"
    metrics_path = output_dir / "metrics_report.json"

    results: list[dict] = []
    started = time.perf_counter()
    with ledger_path.open("w", encoding="utf-8") as ledger:
        for index, case in enumerate(cases, start=1):
            item_started = time.perf_counter()
            classification = classify(case.command)
            item_latency_ms = (time.perf_counter() - item_started) * 1000.0
            result = {
                "case_id": case.case_id,
                "expected_label": case.label,
                "predicted_label": classification.label,
                "warning": classification.warning,
                "latency_ms": round(item_latency_ms, 6),
                "matched_rules": list(classification.matched_rules),
            }
            results.append(result)
            event = {
                "event_id": f"gt-runtime-6-{index:04d}",
                "timestamp_utc": utc_now(),
                "event_type": "shell_safety_classification",
                "runtime": runtime_name,
                "case_id": case.case_id,
                "command_sha256": sha256_text(case.command),
                "expected_label": case.label,
                "predicted_label": classification.label,
                "severity": classification.severity,
                "warning": classification.warning,
                "matched_rules": list(classification.matched_rules),
                "reason": classification.reason,
            }
            ledger.write(json.dumps(event, sort_keys=True) + "\n")

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    metrics = compute_metrics(cases, results, elapsed_ms)
    metrics["runtime"] = runtime_name
    metrics["corpus"] = str(corpus_path)
    metrics["outputs"] = {
        "metrics_report": str(metrics_path),
        "event_ledger": str(ledger_path),
    }
    metrics["case_results"] = results
    write_json(metrics_path, metrics)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GT-RUNTIME-6 shell safety metrics harness")
    parser.add_argument("--corpus", required=True, type=Path, help="JSONL corpus of shell command strings")
    parser.add_argument("--runtime", default="aoia", help="Runtime label to include in metrics and ledger")
    parser.add_argument("--out", default=Path("gt_runtime_6_output"), type=Path, help="Output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metrics = validate(args.corpus, args.runtime, args.out)
    print(json.dumps({key: metrics[key] for key in ("passed", "detection_rate", "false_positive_rate", "missed_dangerous", "warning_rate", "latency_ms", "ledger_coverage")}, sort_keys=True))
    return 0 if metrics["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
