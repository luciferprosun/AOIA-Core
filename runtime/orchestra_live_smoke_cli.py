"""Operator-only command for one controlled live Orchestra demonstration.

The command creates an inert plan preview through the existing local service.
It cannot start the live session until the operator retypes the exact preview
hash and then enters the distinct ``RUN ORCHESTRA`` action phrase.  Provider
credentials remain owned by the external user-provider store and are never
accepted, read, or rendered by this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from runtime.epistemic_orchestra.live_run_preview import (
    MAXIMUM_OUTPUT_TOKENS,
    MAXIMUM_TIMEOUT_SECONDS,
    MINIMUM_OUTPUT_TOKENS,
    MINIMUM_TIMEOUT_SECONDS,
)
from runtime.epistemic_orchestra.role_binding import OrchestraOperatorRole
from runtime.providers.orchestra_live_service import (
    DEFAULT_LIVE_MAXIMUM_OUTPUT_TOKENS,
    DEFAULT_LIVE_TIMEOUT_SECONDS,
    OrchestraLiveWebError,
    OrchestraLiveWebService,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ACTION_PHRASE = "RUN ORCHESTRA"
MAXIMUM_SOURCE_PROMPT_CHARACTERS = 20_000


class LiveSmokeCliError(ValueError):
    """A bounded command-input error that is safe to show to the operator."""


def _default_error(message: str) -> None:
    print(message, file=sys.stderr)


def _bounded_integer(name: str, minimum: int, maximum: int) -> Callable[[str], int]:
    def parse(value: str) -> int:
        try:
            parsed = int(value, 10)
        except ValueError as error:
            raise argparse.ArgumentTypeError(f"{name} must be an integer") from error
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be between {minimum} and {maximum}"
            )
        return parsed

    return parse


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m runtime.orchestra_live_smoke_cli",
        description=(
            "Preview and explicitly confirm one exact-model, no-fallback, "
            "no-retry Orchestra demonstration."
        ),
    )
    prompt_source = parser.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument("--prompt", help="bounded human source prompt")
    prompt_source.add_argument(
        "--prompt-file",
        type=Path,
        help="UTF-8 file containing the bounded human source prompt",
    )
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        metavar="MODEL_PROFILE_ID=ROLE",
        help=(
            "exact saved model profile and explicit role; repeat for two to five "
            "models (MAIN, CRITIC, AUDITOR, SYNTHESIZER)"
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=_bounded_integer(
            "timeout-seconds", MINIMUM_TIMEOUT_SECONDS, MAXIMUM_TIMEOUT_SECONDS
        ),
        default=DEFAULT_LIVE_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--maximum-output-tokens",
        type=_bounded_integer(
            "maximum-output-tokens", MINIMUM_OUTPUT_TOKENS, MAXIMUM_OUTPUT_TOKENS
        ),
        default=DEFAULT_LIVE_MAXIMUM_OUTPUT_TOKENS,
    )
    return parser


def _read_prompt(*, prompt: str | None, prompt_file: Path | None) -> str:
    if prompt_file is not None:
        with prompt_file.open("r", encoding="utf-8") as stream:
            value = stream.read(MAXIMUM_SOURCE_PROMPT_CHARACTERS + 1)
    else:
        value = prompt if prompt is not None else ""
    if not value.strip():
        raise LiveSmokeCliError("source prompt must be non-blank")
    if len(value) > MAXIMUM_SOURCE_PROMPT_CHARACTERS:
        raise LiveSmokeCliError(
            f"source prompt must not exceed {MAXIMUM_SOURCE_PROMPT_CHARACTERS} characters"
        )
    return value


def _parse_selections(values: Sequence[str]) -> list[dict[str, str]]:
    selections: list[dict[str, str]] = []
    seen_profiles: set[str] = set()
    for value in values:
        profile_id, separator, role_text = value.rpartition("=")
        if not separator or not profile_id or not role_text:
            raise LiveSmokeCliError(
                "each --model must use MODEL_PROFILE_ID=ROLE"
            )
        if profile_id.strip() != profile_id:
            raise LiveSmokeCliError("model profile IDs cannot contain outer whitespace")
        try:
            role = OrchestraOperatorRole(role_text).value
        except (TypeError, ValueError):
            raise LiveSmokeCliError("unsupported Orchestra role") from None
        if profile_id in seen_profiles:
            raise LiveSmokeCliError("a model profile may be selected only once")
        seen_profiles.add(profile_id)
        selections.append({"model_profile_id": profile_id, "role": role})
    if not 2 <= len(selections) <= 5:
        raise LiveSmokeCliError("select between two and five model profiles")
    return selections


def _mapping_field(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise LiveSmokeCliError(f"service response is missing {name}")
    return value


def _safe_plan_payload(response: Mapping[str, object]) -> dict[str, object]:
    preview = _mapping_field(response.get("preview"), "preview")
    if response.get("provider_call_permitted") is not False:
        raise LiveSmokeCliError("plan preview unexpectedly permits a provider call")
    if response.get("human_action_required") is not True:
        raise LiveSmokeCliError("plan preview does not require human action")
    if preview.get("authority_status") != "NON_AUTHORITATIVE":
        raise LiveSmokeCliError("plan preview contains an authority claim")
    preview_hash = preview.get("preview_hash")
    planned_calls = preview.get("planned_calls")
    if not isinstance(preview_hash, str) or len(preview_hash) != 64:
        raise LiveSmokeCliError("plan preview hash is malformed")
    if not isinstance(planned_calls, (list, tuple)):
        raise LiveSmokeCliError("plan preview calls are malformed")
    safe_calls: list[dict[str, object]] = []
    allowed_fields = (
        "call_index",
        "stage_id",
        "operator_role",
        "connection_id",
        "model_profile_id",
        "remote_model_id",
        "timeout_seconds",
        "maximum_output_tokens",
    )
    for item in planned_calls:
        call = _mapping_field(item, "planned call")
        safe_calls.append({name: call.get(name) for name in allowed_fields})
    return {
        "event": "ORCHESTRA_PLAN_PREVIEW",
        "preview_hash": preview_hash,
        "orchestra_run_id": preview.get("orchestra_run_id"),
        "run_hash": preview.get("run_hash"),
        "role_selection_hash": preview.get("role_selection_hash"),
        "expires_at_epoch": preview.get("expires_at_epoch"),
        "planned_calls": safe_calls,
        "provider_call_permitted": False,
        "human_action_required": True,
        "authority_status": "NON_AUTHORITATIVE",
    }


def _safe_result_payload(response: Mapping[str, object]) -> dict[str, object]:
    if response.get("authority_status") != "NON_AUTHORITATIVE":
        raise LiveSmokeCliError("live result is not explicitly NON_AUTHORITATIVE")
    if response.get("authoritative") is not False:
        raise LiveSmokeCliError("live result contains an authority claim")
    if response.get("human_review_required") is not True:
        raise LiveSmokeCliError("live result does not require human review")
    if response.get("automatic_fallback_used") is not False:
        raise LiveSmokeCliError("live result reports automatic fallback")
    if response.get("automatic_retry_used") is not False:
        raise LiveSmokeCliError("live result reports automatic retry")
    if response.get("ok") is False:
        failed = _mapping_field(response.get("failed_stage"), "failed_stage")
        allowed = (
            "reason_code",
            "stage_id",
            "call_index",
            "operator_role",
            "connection_id",
            "model_profile_id",
            "session_consumed",
            "trust_status",
            "authority_status",
            "authoritative",
            "automatic_fallback_used",
            "automatic_retry_used",
            "human_review_required",
        )
        return {
            "event": "ORCHESTRA_LIVE_STAGE_FAILED",
            "failed_stage": {name: failed.get(name) for name in allowed},
            "authoritative": False,
            "human_review_required": True,
            "automatic_fallback_used": False,
            "automatic_retry_used": False,
        }
    session = _mapping_field(response.get("session"), "session")
    return {
        "event": "ORCHESTRA_LIVE_RESULT",
        "session": dict(session),
        "final_draft": response.get("final_draft"),
        "trust_status": response.get("trust_status"),
        "authoritative": False,
        "authority_status": "NON_AUTHORITATIVE",
        "human_review_required": True,
        "automatic_fallback_used": False,
        "automatic_retry_used": False,
    }


def run_cli(
    argv: Sequence[str] | None = None,
    *,
    service: OrchestraLiveWebService | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    error_fn: Callable[[str], None] = _default_error,
) -> int:
    args = build_argument_parser().parse_args(argv)
    try:
        source_prompt = _read_prompt(prompt=args.prompt, prompt_file=args.prompt_file)
        selections = _parse_selections(args.model)
        active_service = (
            service if service is not None else OrchestraLiveWebService(PROJECT_ROOT)
        )
        preview_response = active_service.create_preview(
            {
                "source_prompt": source_prompt,
                "selections": selections,
                "timeout_seconds": args.timeout_seconds,
                "maximum_output_tokens": args.maximum_output_tokens,
            }
        )
        safe_preview = _safe_plan_payload(preview_response)
        preview_hash = str(safe_preview["preview_hash"])
        output_fn(json.dumps(safe_preview, ensure_ascii=False, sort_keys=True))
        confirmed_hash = input_fn(
            "Retype the exact preview hash to confirm this plan: "
        ).strip()
        if confirmed_hash != preview_hash:
            error_fn("ABORTED: exact preview hash confirmation did not match")
            return 2
        run_action = input_fn(f"Type {RUN_ACTION_PHRASE} to run this one session: ").strip()
        if run_action != RUN_ACTION_PHRASE:
            error_fn("ABORTED: explicit Run Orchestra action was not entered")
            return 2
        result = active_service.run_preview(
            {
                "preview_hash": preview_hash,
                "confirmation_hash": preview_hash,
                "confirmed_preview_hash": preview_hash,
                "explicit_run_action": True,
            }
        )
        safe_result = _safe_result_payload(result)
        output_fn(json.dumps(safe_result, ensure_ascii=False, sort_keys=True))
        return 1 if result.get("ok") is False else 0
    except LiveSmokeCliError as error:
        error_fn(f"ERROR: {error}")
        return 2
    except (OSError, UnicodeError, OrchestraLiveWebError):
        # Service errors are intentionally not echoed: this command owns no
        # credential with which it could verify or redact arbitrary details.
        error_fn("ERROR: controlled live Orchestra request failed closed")
        return 1
    except (EOFError, KeyboardInterrupt):
        error_fn("ABORTED: interactive operator confirmation was not completed")
        return 2


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "LiveSmokeCliError",
    "MAXIMUM_SOURCE_PROMPT_CHARACTERS",
    "PROJECT_ROOT",
    "RUN_ACTION_PHRASE",
    "build_argument_parser",
    "run_cli",
]
