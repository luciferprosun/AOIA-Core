from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from runtime.providers.contracts import (
    LIVE_SUCCESS,
    ProviderActivationStatus,
)
from runtime.providers.errors import provider_reason_code
from runtime.providers.gateway import build_provider_output_redactor
from runtime.providers.payloads import build_provider_envelope
from runtime.providers.selector import (
    create_provider_selection,
    list_available_providers,
    run_selected_provider,
)
from runtime.runtime_paths import runtime_state_dir
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    TaskPhase,
    TaskState,
    safe_context_metadata,
)
from runtime.task_recovery import RecoveryPurpose, TaskRecoveryService
from runtime.provenance_lifecycle import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from runtime.trace_context import TraceContext
def _emit_json(payload: object) -> None:
    safe_payload = build_provider_output_redactor().redact(payload)
    print(json.dumps(safe_payload, sort_keys=True))


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
        _emit_json([item.to_dict() for item in list_available_providers()])
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
    def invoke_provider():
        return run_selected_provider(
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

    if not live_attempt:
        try:
            result = invoke_provider()
        except ValueError as error:
            _emit_json(
                {
                    "status": "invalid",
                    "error_message": str(error),
                }
            )
            return 2
        _emit_json(result.to_dict())
        return 0 if result.status in {"dry_run_preview", "live_success"} else 2

    try:
        # Complete deterministic input validation before creating a durable
        # live task. These helpers perform no provider I/O.
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
    except ValueError as error:
        _emit_json(
            {"status": "invalid", "error_message": str(error)}
        )
        return 2

    trace_context = TraceContext.new_request()
    model_call = trace_context.new_model_call()
    project_dir = Path(__file__).resolve().parents[1]
    state_dir = runtime_state_dir(project_dir) / "state"
    provenance_store = AppendOnlyProvenanceStore(state_dir)
    task_checkpoint_store = DurableTaskCheckpointStore(
        state_dir,
        project_dir=project_dir,
        provenance_store=provenance_store,
    )
    checkpoint = task_checkpoint_store.create_task(
        trace_context,
        max_steps=1,
        retry_budget=1,
        safe_context=safe_context_metadata(prompt),
    )
    recovery_service = TaskRecoveryService(
        state_dir,
        project_dir=project_dir,
        checkpoint_store=task_checkpoint_store,
        provenance_store=provenance_store,
    )
    step_reservation = None

    def terminalize_live_attempt(succeeded: bool) -> None:
        assert step_reservation is not None
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
        checkpoint = task_checkpoint_store.load(trace_context.task_id)
        assert checkpoint is not None
        task_checkpoint_store.transition(
            trace_context.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=(
                TaskPhase.AFTER_MODEL_CALL
                if succeeded
                else TaskPhase.BEFORE_MODEL_CALL
            ),
            reason_code=(
                "TASK_MODEL_CALL_COMPLETED"
                if succeeded
                else "TASK_MODEL_CALL_FAILED"
            ),
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            current_model_call_id=model_call.model_call_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
        )
        task_checkpoint_store.close_step_reservation(step_reservation)
        checkpoint = task_checkpoint_store.load(trace_context.task_id)
        assert checkpoint is not None
        task_checkpoint_store.transition(
            trace_context.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.COMPLETED if succeeded else TaskState.FAILED,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_COMPLETED" if succeeded else "TASK_FAILED",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
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

    with recovery_service.execution_guard(
        trace_context.task_id,
        purpose=RecoveryPurpose.LIVE,
        expected_checkpoint_hash=checkpoint.checkpoint_hash,
    ) as recovery_token:
        task_checkpoint_store.transition(
            trace_context.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_STARTED",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
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
        step_reservation = task_checkpoint_store.reserve_step(trace_context.task_id)
        task_checkpoint_store.consume_provider_attempt(
            model_call,
            step_reservation=step_reservation,
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
        try:
            recovery_service.classify_under_claim(
                trace_context.task_id,
                recovery_token,
            )
            result = invoke_provider()
        except ValueError as error:
            terminalize_live_attempt(False)
            _emit_json(
                {"status": "invalid", "error_message": str(error)}
            )
            return 2
        except Exception as provider_error:
            try:
                terminalize_live_attempt(False)
            except Exception as lifecycle_error:
                try:
                    provider_error.add_note(
                        "CLI provider failure lifecycle is pending or degraded; "
                        f"secondary failure type: {type(lifecycle_error).__name__}."
                    )
                except AttributeError:  # pragma: no cover
                    pass
            raise
        terminalize_live_attempt(result.status == LIVE_SUCCESS)
        _emit_json(
            {**result.to_dict(), **model_call.identity_fields()}
        )
        return 0 if result.status in {"dry_run_preview", "live_success"} else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        _emit_json(
            {
                "status": "error",
                "reason_code": provider_reason_code(error),
                "message_safe": "The provider request could not be completed.",
            }
        )
        raise SystemExit(2)
