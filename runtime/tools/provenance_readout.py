from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from tools.provenance import ProvenanceVerificationResult, verify_provenance_chain


def _result_label(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _has_issue(result: ProvenanceVerificationResult, marker: str) -> bool:
    return any(marker in issue for issue in result.issues)


def render_integrity_report(
    log_path: Path,
    result: ProvenanceVerificationResult,
    deterministic: bool,
) -> str:
    prev_hash_ok = not (
        _has_issue(result, "prev_hash mismatch")
        or _has_issue(result, "first entry prev_hash")
        or _has_issue(result, "missing prev_hash")
    )
    payload_hash_ok = not _has_issue(result, "payload_hash mismatch")
    first_failure = result.issues[0] if result.issues else "none"

    lines = [
        "AOIA Provenance Integrity Report",
        f"file: {log_path}",
        f"status: {_result_label(result.ok and deterministic)}",
        f"total_records: {result.entry_count}",
        f"prev_hash_continuity: {_result_label(prev_hash_ok)}",
        f"payload_hash_verification: {_result_label(payload_hash_ok)}",
        f"deterministic_verification: {_result_label(deterministic)}",
        f"terminal_hash: {result.terminal_hash}",
        f"first_failure: {first_failure}",
    ]
    if result.issues:
        lines.append("issues:")
        lines.extend(f"- {issue}" for issue in result.issues)
    return "\n".join(lines)


def verify_file(log_path: Path) -> tuple[ProvenanceVerificationResult, bool]:
    first = verify_provenance_chain(log_path)
    second = verify_provenance_chain(log_path)
    return first, first == second


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify an AOIA append-only provenance chain and print a concise integrity report."
    )
    parser.add_argument("log_path", type=Path, help="Path to provenance_log.jsonl")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result, deterministic = verify_file(args.log_path)
    print(render_integrity_report(args.log_path, result, deterministic))
    return 0 if result.ok and deterministic else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
