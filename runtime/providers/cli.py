from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from runtime.providers.contracts import (
    LIVE_SUCCESS,
    ProviderActivationStatus,
)
from runtime.providers.payloads import build_provider_envelope
from runtime.providers.selector import (
    create_provider_selection,
    list_available_providers,
    run_selected_provider,
)
from runtime.runtime_paths import runtime_state_dir
from runtime.provenance_lifecycle import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import TraceContext


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AOIA controlled provider selector (dry-run by default; output is UNTRUSTED)."
    )
    parser.add_argument("--list", action="store_true", help="list runtime provider metadata")
    parser.add_argument("--provider", help="known provider identifier")
    parser.add_argument("--model", help="explicit model identifier")
    parser.add_argument("--prompt", help="explicit prompt text")
    parser.add_argument("--max-tokens", type=int, help="explicit output token cap")
    parser.add_argument("--live", action="store_true", help="request controlled live policy")
    parser.add_argument(
        "--acknowledge-live-provider-test",
        action="store_true",
        help="acknowledge a manual live provider test",
    )
    parser.add_argument(
        "--activate-manual-live-test",
        action="store_true",
        help="explicitly activate one manually requested live test",
    )
    parser.add_argument(
        "--created-at",
        default="cli-manual-run",
        help="caller-supplied audit timestamp or label",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        print(json.dumps([item.to_dict() for item in list_available_providers()], sort_keys=True))
        return 0
    provider_id = args.provider or ""
    model_id = args.model or ""
    prompt = args.prompt or ""
    activation = (
        ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST
        if args.activate_manual_live_test
        else ProviderActivationStatus.DRY_RUN_ONLY
    )
    live_attempt = bool(
        args.live
        and args.acknowledge_live_provider_test
        and args.activate_manual_live_test
    )
    provenance_store = None
    trace_context = None
    model_call = None
    if live_attempt:
        try:
            # Complete deterministic input validation before claiming that a
            # live model-call attempt started. These helpers perform no I/O.
            selection = create_provider_selection(
                provider_id=provider_id,
                model_id=model_id,
                max_tokens=args.max_tokens,
                live=True,
                selected_by="manual",
                created_at=args.created_at,
            )
            build_provider_envelope(
                provider_id=selection.provider_id,
                model_id=selection.model_id,
                prompt=prompt,
                params=(
                    {}
                    if selection.max_tokens is None
                    else {"max_tokens": selection.max_tokens}
                ),
                dry_run=False,
                created_at=selection.created_at,
            )
            trace_context = TraceContext.new_request()
            model_call = trace_context.new_model_call()
            provenance_store = AppendOnlyProvenanceStore(
                runtime_state_dir(Path(__file__).resolve().parents[1]) / "state"
            )
            provenance_store.append_runtime_event(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.REQUEST_STARTED,
                    trace_context=trace_context,
                    ingress="CLI",
                    request_length=len(prompt),
                    slash_command=False,
                )
            )
            provenance_store.append_runtime_event(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.MODEL_CALL_STARTED,
                    model_call=model_call,
                    requested_provider=provider_id,
                    requested_model=model_id,
                    retry_attempt=1,
                    provider_attempt=1,
                )
            )
        except ValueError as error:
            print(
                json.dumps(
                    {"status": "invalid", "error_message": str(error)},
                    sort_keys=True,
                )
            )
            return 2
    try:
        result = run_selected_provider(
            provider_id=provider_id,
            model_id=model_id,
            prompt=prompt,
            max_tokens=args.max_tokens,
            live=args.live,
            acknowledge_live_provider_test=args.acknowledge_live_provider_test,
            activation_status=activation,
            selected_by="manual",
            created_at=args.created_at,
        )
    except ValueError as error:
        if provenance_store is not None and trace_context is not None and model_call is not None:
            provenance_store.append_terminal(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.MODEL_CALL_FAILED,
                    model_call=model_call,
                    requested_provider=provider_id,
                    requested_model=model_id,
                    retry_attempt=1,
                    provider_attempt=1,
                    success=False,
                )
            )
            provenance_store.append_terminal(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.REQUEST_COMPLETED,
                    trace_context=trace_context,
                    ingress="CLI",
                    success=False,
                    reason_code="REQUEST_FAILED",
                )
            )
        print(json.dumps({"status": "invalid", "error_message": str(error)}, sort_keys=True))
        return 2
    if provenance_store is not None and trace_context is not None and model_call is not None:
        succeeded = result.status == LIVE_SUCCESS
        provenance_store.append_terminal(
            new_runtime_provenance_event(
                (
                    RuntimeProvenanceEventType.MODEL_CALL_COMPLETED
                    if succeeded
                    else RuntimeProvenanceEventType.MODEL_CALL_FAILED
                ),
                model_call=model_call,
                requested_provider=provider_id,
                requested_model=model_id,
                retry_attempt=1,
                provider_attempt=1,
                success=succeeded,
            )
        )
        provenance_store.append_terminal(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_COMPLETED,
                trace_context=trace_context,
                ingress="CLI",
                success=succeeded,
                reason_code=(
                    "REQUEST_COMPLETED" if succeeded else "REQUEST_FAILED"
                ),
            )
        )
    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0 if result.status in {"dry_run_preview", "live_success"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
