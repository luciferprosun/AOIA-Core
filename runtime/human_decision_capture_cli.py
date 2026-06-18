from __future__ import annotations

import argparse
import json
from typing import Sequence

from runtime.human_decision_capture_helper import (
    BLOCKED_INVALID_DECISION,
    BLOCKED_MISSING_PACKET_HASH,
    BLOCKED_STALE_OR_MISMATCHED_PACKET,
    CAPTURED_APPROVE,
    CAPTURED_REJECT,
    HumanDecisionCaptureIntent,
    capture_human_decision_intent,
)


EXIT_CAPTURED_APPROVE = 0
EXIT_CAPTURED_REJECT = 20
EXIT_STALE_OR_MISMATCHED = 30
EXIT_INVALID_INPUT = 40
EXIT_FAIL_CLOSED = 50


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Capture an explicit local human decision intent.",
        allow_abbrev=False,
    )
    parser.add_argument("--decision", required=True, choices=("APPROVE", "REJECT"))
    parser.add_argument("--displayed-packet-hash", required=True)
    parser.add_argument("--current-packet-hash", required=True)
    parser.add_argument("--packet-id")
    parser.add_argument("--displayed-artifact-hash")
    parser.add_argument("--current-artifact-hash")
    parser.add_argument("--human-actor")
    parser.add_argument("--reason")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        result = capture_human_decision_intent(
            decision=args.decision,
            displayed_packet_hash=args.displayed_packet_hash,
            current_packet_hash=args.current_packet_hash,
            packet_id=args.packet_id,
            displayed_artifact_hash=args.displayed_artifact_hash,
            current_artifact_hash=args.current_artifact_hash,
            human_actor=args.human_actor,
            reason=args.reason,
        )
        payload = _capture_payload(result)
        exit_code = _exit_code(result.outcome_state)
    except (TypeError, ValueError) as exc:
        payload = _fail_closed_payload(
            outcome_state=BLOCKED_INVALID_DECISION,
            message=f"invalid command-line input: {exc}",
        )
        exit_code = EXIT_INVALID_INPUT
    except Exception:
        payload = _fail_closed_payload(
            outcome_state="ERROR_FAIL_CLOSED",
            message="unexpected error; capture failed closed",
        )
        exit_code = EXIT_FAIL_CLOSED

    print(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    return exit_code


def _capture_payload(result: HumanDecisionCaptureIntent) -> dict[str, object]:
    payload = result.to_dict()
    payload.update(
        {
            "result_type": "HumanDecisionCaptureIntent",
            "approval_decision_required": True,
            "approval_decision_status": "REQUIRED_NOT_CREATED",
            "authority_notice": "Capture intent is not approval authority.",
        }
    )
    return payload


def _fail_closed_payload(*, outcome_state: str, message: str) -> dict[str, object]:
    return {
        "result_type": "HumanDecisionCaptureIntent",
        "outcome_state": outcome_state,
        "decision": None,
        "decision_captured": False,
        "blocking": True,
        "is_approval_authority": False,
        "approval_decision_required": True,
        "approval_decision_status": "REQUIRED_NOT_CREATED",
        "durable_audit_handoff_required": True,
        "pre_artifact_gate_passed": False,
        "artifact_write_occurred": False,
        "authority_notice": "Capture intent is not approval authority.",
        "messages": [message],
    }


def _exit_code(outcome_state: str) -> int:
    if outcome_state == CAPTURED_APPROVE:
        return EXIT_CAPTURED_APPROVE
    if outcome_state == CAPTURED_REJECT:
        return EXIT_CAPTURED_REJECT
    if outcome_state == BLOCKED_STALE_OR_MISMATCHED_PACKET:
        return EXIT_STALE_OR_MISMATCHED
    if outcome_state in {BLOCKED_INVALID_DECISION, BLOCKED_MISSING_PACKET_HASH}:
        return EXIT_INVALID_INPUT
    return EXIT_FAIL_CLOSED


if __name__ == "__main__":
    raise SystemExit(main())
