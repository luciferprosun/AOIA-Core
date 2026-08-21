from __future__ import annotations

import datetime as dt
import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.parse import unquote, urlparse

from trace_context import (
    ActionContext,
    TraceContext,
    TraceIdentityError,
    strip_untrusted_identity_fields,
)
from runtime.safety.atomic_persistence import (
    PersistenceError,
    atomic_write_json,
    state_resource_lock_path,
)
from runtime.sensitive_redaction import SensitiveValueRedactor
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    SafeResumeClassification,
    StepReservation,
    TaskCheckpoint,
    TaskPhase,
    TaskState,
    TERMINAL_TASK_STATES,
)
from runtime.task_recovery import (
    RecoveryClassification,
    RecoveryClaimConflictError,
    RecoveryDirective,
    RecoveryExecutionToken,
    RecoveryFencedError,
    RecoveryPurpose,
    TaskRecoveryService,
)
from runtime.outcomes import attach_outcome

from .browser_tools import (
    browser_click,
    browser_close,
    browser_current_url,
    browser_get_visible_text,
    browser_open,
    browser_press,
    browser_read_html,
    browser_screenshot,
    browser_start,
    browser_type,
    configure_browser_bridge,
)
from .capability_policy import (
    ActionPolicyDecision,
    CapabilityClass,
    evaluate_action_policy,
)
from .filesystem_tools import (
    FilesystemContainmentError,
    append_file,
    canonical_project_root,
    create_file,
    create_folder,
    delete_file,
    move_file,
    read_file,
    resolve_path,
    search_in_project,
    write_file,
)
from .idempotency import (
    ACTION_SEMANTIC_FIELDS,
    IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
    DurableIdempotencyStore,
    IdempotencyRecord,
    IdempotencyResolution,
    IdempotencyResolutionKind,
    IdempotencyState,
    IDEMPOTENCY_STATE_REASON_CODES,
    OperationContext,
    build_safe_result_receipt,
    canonical_action_fingerprint,
    project_scope_fingerprint,
)
from .memory import MemoryStore
from .project_scanner import scan_project
from .provenance import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from .shell_tools import (
    _legacy_shell_execution_enabled,
    shell_execute,
    shell_execution_blocked_result,
)
from .validator import classify_shell_command, validate_action, validate_shell_command


ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    """Runtime tool metadata used by the executor registry."""

    name: str
    handler: ToolHandler
    description: str


class ExecutionEngine:
    """Dispatch structured legacy tool actions; execution surfaces are frozen by default."""

    def __init__(
        self,
        project_dir: Path,
        memory_store: MemoryStore,
        *,
        provenance_store: AppendOnlyProvenanceStore | None = None,
        task_checkpoint_store: DurableTaskCheckpointStore | None = None,
        task_recovery_service: TaskRecoveryService | None = None,
        redactor: SensitiveValueRedactor | None = None,
    ) -> None:
        self.project_dir = canonical_project_root(project_dir)
        self.memory_store = memory_store
        self.redactor = redactor or memory_store.redactor
        self.cwd = resolve_path(
            memory_store.memory.cwd,
            self.project_dir,
            self.project_dir,
            operation="runtime working-directory initialization",
        )
        self.command_log_dir = memory_store.paths.command_logs_dir
        configure_browser_bridge(
            user_data_dir=memory_store.paths.state_dir / "browser_profile",
            screenshots_dir=memory_store.paths.screenshots_dir,
            headless=True,
        )
        self.tools = self._build_tool_registry()
        self.idempotency_store = DurableIdempotencyStore(
            memory_store.paths.state_dir,
            lock_timeout_seconds=memory_store.state_lock_timeout_seconds,
        )
        self.provenance_store = provenance_store or AppendOnlyProvenanceStore(
            memory_store.paths.state_dir,
            lock_timeout_seconds=memory_store.state_lock_timeout_seconds,
        )
        self.task_checkpoint_store = task_checkpoint_store or DurableTaskCheckpointStore(
            memory_store.paths.state_dir,
            project_dir=self.project_dir,
            provenance_store=self.provenance_store,
            lock_timeout_seconds=memory_store.state_lock_timeout_seconds,
        )
        self.task_recovery_service = task_recovery_service
        self._recovery_sensitive_persistence: ContextVar[bool] = ContextVar(
            f"aoia_executor_recovery_sensitive_{id(self)}",
            default=False,
        )

    @contextmanager
    def recovery_sensitive_persistence(self) -> Iterator[None]:
        """Redact non-authoritative executor logs during trusted recovery."""

        binding = self._recovery_sensitive_persistence.set(True)
        try:
            yield
        finally:
            self._recovery_sensitive_persistence.reset(binding)

    @staticmethod
    def _recovery_sensitive_summary(value: object) -> dict[str, object]:
        """Return bounded metadata without retaining recoverable raw content."""

        try:
            serialized = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=lambda item: f"<{type(item).__name__}>",
            )
        except (TypeError, ValueError, RecursionError):
            serialized = f"<{type(value).__name__}>"
        encoded = serialized.encode("utf-8", errors="replace")
        return {
            "redacted": True,
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "utf8_length": len(encoded),
        }

    def tool_names(self) -> list[str]:
        return sorted(self.tools)

    def execute(
        self,
        action: dict[str, Any],
        require_approval: bool = True,
        *,
        action_context: ActionContext | None = None,
        operation_context: OperationContext | None = None,
        step_reservation: StepReservation | None = None,
        recovery_token: RecoveryExecutionToken | None = None,
    ) -> dict[str, Any]:
        """Execute with complete persistence-error correlation."""

        authoritative_context = (
            action_context or TraceContext.new_request().new_action()
        )
        try:
            guarded_context = self._execution_context_for_guard(
                authoritative_context,
                operation_context=operation_context,
                step_reservation=step_reservation,
            )
            service = self._get_task_recovery_service()
            if recovery_token is not None:
                self._validate_recovery_token(
                    guarded_context.task_id,
                    recovery_token,
                )
                if recovery_token.purpose is not RecoveryPurpose.LIVE:
                    service.validate_dispatch_authorization(
                        recovery_token,
                        frozenset({RecoveryDirective.RESUME_MODEL}),
                    )
                result = self._execute(
                    action,
                    require_approval=require_approval,
                    action_context=authoritative_context,
                    operation_context=operation_context,
                    step_reservation=step_reservation,
                    recovery_token=recovery_token,
                )
                return self._redact_result(
                    self._attach_authoritative_outcome(result, guarded_context)
                )

            existing_operation = (
                self.idempotency_store.load(operation_context)
                if operation_context is not None
                else None
            )
            preexisting_checkpoint = self.task_checkpoint_store.load(
                guarded_context.task_id
            )
            checkpoint = self.task_checkpoint_store.ensure_for_action(
                guarded_context
            )
            entered_guard = False
            try:
                with service.execution_guard(
                    guarded_context.task_id,
                    purpose=RecoveryPurpose.LIVE,
                    # A known P0.7 record may queue behind the current owner and
                    # replay/conflict from the final canonical record. A genuinely
                    # new operation is instead bound to the exact pre-guard task
                    # checkpoint so recovery cannot terminalize the task in the
                    # ensure-for-action -> execution-lock window and then let this
                    # caller mint a late RESERVED record under a terminal task.
                    expected_checkpoint_hash=(
                        None
                        if existing_operation is not None
                        else checkpoint.checkpoint_hash
                    ),
                ) as live_token:
                    entered_guard = True
                    if existing_operation is None:
                        current = self.task_checkpoint_store.load(
                            guarded_context.task_id
                        )
                        if (
                            current is None
                            or current.checkpoint_hash != checkpoint.checkpoint_hash
                            or current.state in TERMINAL_TASK_STATES
                        ):
                            raise RecoveryFencedError(
                                "Task changed before a new operation could enter policy evaluation."
                            )
                        if preexisting_checkpoint is not None:
                            if step_reservation is None:
                                raise RecoveryFencedError(
                                    "An existing task cannot be adopted by an unguarded live action."
                                )
                            reserved_checkpoint = (
                                self.task_checkpoint_store.validate_step_reservation(
                                    step_reservation,
                                    task_id=guarded_context.task_id,
                                )
                            )
                            if (
                                reserved_checkpoint.state is not TaskState.RUNNING
                                or not (
                                    (
                                        reserved_checkpoint.phase
                                        is TaskPhase.BEFORE_MODEL_CALL
                                        and reserved_checkpoint.safe_resume_classification
                                        is SafeResumeClassification.SAFE_TO_RESUME
                                    )
                                    or (
                                        reserved_checkpoint.phase
                                        is TaskPhase.AFTER_MODEL_CALL
                                        and reserved_checkpoint.safe_resume_classification
                                        is SafeResumeClassification.MANUAL_REVIEW_REQUIRED
                                        and guarded_context.model_call_id
                                        == reserved_checkpoint.current_model_call_id
                                    )
                                )
                            ):
                                raise RecoveryFencedError(
                                    "The live step reservation no longer proves a safe task phase."
                                )
                    result = self._execute(
                        action,
                        require_approval=require_approval,
                        action_context=authoritative_context,
                        operation_context=operation_context,
                        step_reservation=step_reservation,
                        recovery_token=live_token,
                    )
                    return self._redact_result(
                        self._attach_authoritative_outcome(result, guarded_context)
                    )
            except RecoveryClaimConflictError:
                if entered_guard or operation_context is None:
                    raise
                # The exact-checkpoint claim may lose a legitimate first-writer
                # race. Queue without a checkpoint hash only after P0.7 now proves
                # that this logical operation already exists; otherwise recovery
                # changed the task and the new operation remains fenced.
                raced_record = self.idempotency_store.load(operation_context)
                if raced_record is None:
                    raise
                with service.execution_guard(
                    guarded_context.task_id,
                    purpose=RecoveryPurpose.LIVE,
                    expected_checkpoint_hash=None,
                ) as replay_token:
                    result = self._execute(
                        action,
                        require_approval=require_approval,
                        action_context=authoritative_context,
                        operation_context=operation_context,
                        step_reservation=step_reservation,
                        recovery_token=replay_token,
                    )
                    return self._redact_result(
                        self._attach_authoritative_outcome(result, guarded_context)
                    )
        except PersistenceError as exc:
            raise exc.attach_correlation(
                authoritative_context.identity_fields()
            )

    def resume_reserved_action(
        self,
        action: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Resume only a proven pre-dispatch P0.7 RESERVED operation.

        The action payload is merely a candidate for revalidation. Durable
        checkpoint/P0.7 identities remain authoritative, the original operation
        key is retained, and no task step or new P0.7 reservation is minted.
        """

        task_id = recovery_token.task_id
        decision_under_claim = self._get_task_recovery_service().classify_under_claim(
            task_id, recovery_token
        )
        if decision_under_claim.classification not in {
            RecoveryClassification.SAFE_TO_RESUME,
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        }:
            raise RecoveryFencedError(
                "Recovery classification does not authorize reserved-action resume."
            )
        checkpoint = self.task_checkpoint_store.load(task_id)
        if checkpoint is None:
            raise RecoveryFencedError(
                "Reserved-action recovery checkpoint is missing."
            )
        if (
            recovery_token.checkpoint_hash is None
            or recovery_token.checkpoint_hash != checkpoint.checkpoint_hash
        ):
            raise RecoveryFencedError(
                "Reserved-action recovery token is stale."
            )

        self._require_reserved_checkpoint(checkpoint)

        operation = OperationContext(checkpoint.current_idempotency_key or "")
        record = self.idempotency_store.load(operation)
        if record is None:
            raise RecoveryFencedError(
                "Reserved-action recovery lacks its P0.7 record."
            )
        authoritative_context = ActionContext(
            request_id=record.request_id,
            trace_id=record.trace_id,
            task_id=record.task_id or "",
            action_id=record.action_id,
            model_call_id=record.model_call_id,
        )
        authoritative_action = validate_action(
            strip_untrusted_identity_fields(action)
        )
        candidate_fingerprint = canonical_action_fingerprint(
            authoritative_action,
            project_dir=self.project_dir,
            capability_class=record.capability_class,
        )
        self._require_reserved_record_binding(
            checkpoint,
            record,
            authoritative_context,
            operation,
            action_name=str(authoritative_action.get("action", "")),
            action_fingerprint=candidate_fingerprint,
        )
        self._require_pristine_reserved_provenance(checkpoint, record)

        current_decision = evaluate_action_policy(
            authoritative_action, authoritative_context
        )
        if (
            current_decision.action_name != checkpoint.current_action_name
            or current_decision.capability_class.value != record.capability_class
            or current_decision.capability_class.value
            != checkpoint.current_capability_class
        ):
            raise RecoveryFencedError(
                "Current action policy no longer matches the reserved operation."
            )
        self._record_capability_decision(
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
        )

        if not current_decision.allowed:
            return self._terminalize_existing_reservation(
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
                checkpoint,
                record,
                IdempotencyState.BLOCKED,
                self._blocked_policy_result(current_decision),
                recovery_token=recovery_token,
            )

        tool = self.tools.get(current_decision.action_name)
        if tool is None:
            blocked_result = {
                **self._decision_fields(current_decision),
                "success": False,
                "allowed": False,
                "blocked": True,
                "cancelled": False,
                "policy_allowed": True,
                "policy_reason_code": "ACTION_HANDLER_MISSING",
                "message": "Runtime capability policy blocked an action without a handler.",
            }
            return self._terminalize_existing_reservation(
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
                checkpoint,
                record,
                IdempotencyState.BLOCKED,
                blocked_result,
                recovery_token=recovery_token,
            )

        needs_fresh_approval = (
            current_decision.requires_confirmation
            or checkpoint.approval_state is not ApprovalState.NOT_REQUIRED
        )
        if needs_fresh_approval:
            approved = self._request_approval(
                authoritative_action,
                current_decision,
                authoritative_context,
            )
            self._record_approval_decision(
                approved,
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
            )
            if not approved:
                cancelled_result = {
                    **self._decision_fields(current_decision),
                    "success": False,
                    "allowed": False,
                    "blocked": True,
                    "cancelled": True,
                    "policy_allowed": current_decision.allowed,
                    "dispatched": False,
                    "result_reason_code": "HUMAN_APPROVAL_DECLINED",
                    "message": "Action rejected by fresh approval before recovery dispatch.",
                }
                return self._terminalize_existing_reservation(
                    authoritative_action,
                    current_decision,
                    authoritative_context,
                    operation,
                    checkpoint,
                    record,
                    IdempotencyState.CANCELLED,
                    cancelled_result,
                    recovery_token=recovery_token,
                )

        self._require_pristine_reserved_provenance(checkpoint, record)
        standalone_task = bool(
            checkpoint.transitions
            and checkpoint.transitions[0].reason_code
            == "STANDALONE_ACTION_TASK_CREATED"
        )
        return self._dispatch_reserved_operation(
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
            record,
            checkpoint,
            tool,
            recovery_token=recovery_token,
            standalone_task=standalone_task,
            require_pristine_reserved_provenance=True,
            fresh_approval_required=needs_fresh_approval,
            recovery_resume=True,
        )

    def resume_pre_dispatch_action(
        self,
        action: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Resume an exact WAITING/BEFORE_DISPATCH action before P0.7 exists."""

        task_id = recovery_token.task_id
        classification = self._get_task_recovery_service().classify_under_claim(
            task_id, recovery_token
        ).classification
        if classification not in {
            RecoveryClassification.SAFE_TO_RESUME,
            RecoveryClassification.WAITING_FOR_FRESH_APPROVAL,
        }:
            raise RecoveryFencedError(
                "Recovery classification does not authorize pre-dispatch resume."
            )
        checkpoint = self.task_checkpoint_store.load(task_id)
        if checkpoint is None:
            raise RecoveryFencedError(
                "Pre-dispatch recovery checkpoint is missing."
            )
        if (
            recovery_token.checkpoint_hash is None
            or recovery_token.checkpoint_hash != checkpoint.checkpoint_hash
        ):
            raise RecoveryFencedError(
                "Pre-dispatch recovery token is stale."
            )
        self._require_pre_dispatch_checkpoint(checkpoint)
        operation = OperationContext(checkpoint.current_idempotency_key or "")
        if self.idempotency_store.load(operation) is not None:
            raise RecoveryFencedError(
                "Pre-dispatch recovery found an unexpected P0.7 record."
            )
        authoritative_context = self._checkpoint_action_context(checkpoint)
        authoritative_action = validate_action(
            strip_untrusted_identity_fields(action)
        )
        fingerprint = canonical_action_fingerprint(
            authoritative_action,
            project_dir=self.project_dir,
            capability_class=checkpoint.current_capability_class or "",
        )
        if (
            authoritative_action.get("action") != checkpoint.current_action_name
            or fingerprint != checkpoint.current_action_fingerprint
        ):
            raise RecoveryFencedError(
                "Recovery action does not match the pre-dispatch checkpoint."
            )
        self._require_pristine_pre_dispatch_provenance(
            checkpoint, authoritative_context, operation
        )

        current_decision = evaluate_action_policy(
            authoritative_action, authoritative_context
        )
        if (
            current_decision.action_name != checkpoint.current_action_name
            or current_decision.capability_class.value
            != checkpoint.current_capability_class
        ):
            raise RecoveryFencedError(
                "Current policy classification no longer matches the checkpoint."
            )
        self._record_capability_decision(
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
        )
        if not current_decision.allowed:
            return self._terminalize_new_pre_dispatch_operation(
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
                checkpoint,
                IdempotencyState.BLOCKED,
                self._blocked_policy_result(current_decision),
                recovery_token=recovery_token,
            )

        tool = self.tools.get(current_decision.action_name)
        if tool is None:
            blocked_result = {
                **self._decision_fields(current_decision),
                "success": False,
                "allowed": False,
                "blocked": True,
                "cancelled": False,
                "policy_allowed": True,
                "policy_reason_code": "ACTION_HANDLER_MISSING",
                "message": "Runtime capability policy blocked an action without a handler.",
            }
            return self._terminalize_new_pre_dispatch_operation(
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
                checkpoint,
                IdempotencyState.BLOCKED,
                blocked_result,
                recovery_token=recovery_token,
            )

        # Recovery never reuses a pre-crash approval, including a durable
        # GRANTED_IN_PROCESS marker. This callback is the existing P0.3 boundary.
        approved = self._request_approval(
            authoritative_action,
            current_decision,
            authoritative_context,
        )
        self._record_approval_decision(
            approved,
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
        )
        if not approved:
            cancelled_result = {
                **self._decision_fields(current_decision),
                "success": False,
                "allowed": False,
                "blocked": True,
                "cancelled": True,
                "policy_allowed": current_decision.allowed,
                "dispatched": False,
                "result_reason_code": "HUMAN_APPROVAL_DECLINED",
                "message": "Action rejected by fresh approval before recovery dispatch.",
            }
            return self._terminalize_new_pre_dispatch_operation(
                authoritative_action,
                current_decision,
                authoritative_context,
                operation,
                checkpoint,
                IdempotencyState.CANCELLED,
                cancelled_result,
                recovery_token=recovery_token,
            )

        if checkpoint.phase is TaskPhase.WAITING_FOR_APPROVAL:
            checkpoint = self._checkpoint_task(
                checkpoint,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=current_decision.action_name,
                action_fingerprint=fingerprint,
                capability_class=current_decision.capability_class.value,
                policy_reason_code=current_decision.reason_code,
                approval_state=ApprovalState.GRANTED_IN_PROCESS,
                safe_resume_classification=(
                    SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL
                ),
                checkpoint_recovery_token=recovery_token,
            )

        self._validate_recovery_token(task_id, recovery_token)
        if self.idempotency_store.load(operation) is not None:
            raise RecoveryFencedError(
                "P0.7 state appeared before the recovered reservation."
            )
        reservation = self._reserve_operation(
            operation,
            authoritative_context,
            current_decision,
            fingerprint,
        )
        resolution_event_id = self._after_idempotency_resolution(
            reservation,
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
        )
        if not reservation.dispatch_allowed:
            raise RecoveryFencedError(
                "Recovered pre-dispatch operation lost its P0.7 reservation race."
            )
        checkpoint = self._checkpoint_task(
            checkpoint,
            state=TaskState.RUNNING,
            phase=TaskPhase.IDEMPOTENCY_RESERVED,
            reason_code="TASK_IDEMPOTENCY_RESERVED",
            action_context=authoritative_context,
            operation_context=operation,
            action_name=current_decision.action_name,
            action_fingerprint=fingerprint,
            capability_class=current_decision.capability_class.value,
            policy_reason_code=current_decision.reason_code,
            idempotency_state=reservation.record.state.value,
            latest_provenance_event_id=resolution_event_id,
            approval_state=ApprovalState.FRESH_APPROVAL_REQUIRED,
            checkpoint_recovery_token=recovery_token,
        )
        standalone_task = bool(
            checkpoint.transitions
            and checkpoint.transitions[0].reason_code
            == "STANDALONE_ACTION_TASK_CREATED"
        )
        return self._dispatch_reserved_operation(
            authoritative_action,
            current_decision,
            authoritative_context,
            operation,
            reservation.record,
            checkpoint,
            tool,
            recovery_token=recovery_token,
            standalone_task=standalone_task,
            require_pristine_reserved_provenance=True,
            fresh_approval_required=True,
            recovery_resume=True,
        )

    def resume_recoverable_action(
        self,
        action: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Route one explicitly classified action recovery without guessing."""

        checkpoint = self.task_checkpoint_store.load(recovery_token.task_id)
        if checkpoint is None:
            raise RecoveryFencedError("Recoverable action checkpoint is missing.")
        record: IdempotencyRecord | None = None
        if checkpoint.current_idempotency_key is not None:
            try:
                operation = OperationContext(checkpoint.current_idempotency_key)
            except ValueError as exc:
                raise RecoveryFencedError(
                    "Recoverable action operation identity is invalid."
                ) from exc
            record = self.idempotency_store.load(operation)
        if record is not None:
            if record.state is not IdempotencyState.RESERVED:
                raise RecoveryFencedError(
                    "Existing P0.7 state does not authorize action resume."
                )
            return self._redact_result(
                self._attach_recovery_outcome(
                    self.resume_reserved_action(action, recovery_token=recovery_token),
                    checkpoint,
                )
            )
        if checkpoint.phase is TaskPhase.IDEMPOTENCY_RESERVED:
            return self._redact_result(
                self._attach_recovery_outcome(
                    self.resume_reserved_action(action, recovery_token=recovery_token),
                    checkpoint,
                )
            )
        if checkpoint.phase in {
            TaskPhase.WAITING_FOR_APPROVAL,
            TaskPhase.BEFORE_DISPATCH,
        }:
            return self._redact_result(
                self._attach_recovery_outcome(
                    self.resume_pre_dispatch_action(action, recovery_token=recovery_token),
                    checkpoint,
                )
            )
        raise RecoveryFencedError(
            "Task phase is not an explicitly recoverable action boundary."
        )

    def cancel_recoverable_action(
        self,
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Cancel only proven pre-dispatch work; uncertainty remains immutable."""

        task_id = recovery_token.task_id
        self._validate_recovery_token(task_id, recovery_token)
        checkpoint = self.task_checkpoint_store.load(task_id)
        if checkpoint is None:
            raise RecoveryFencedError("Recoverable action checkpoint is missing.")
        if (
            recovery_token.checkpoint_hash is None
            or recovery_token.checkpoint_hash != checkpoint.checkpoint_hash
        ):
            raise RecoveryFencedError("Recovery cancellation token is stale.")
        if checkpoint.phase not in {
            TaskPhase.WAITING_FOR_APPROVAL,
            TaskPhase.BEFORE_DISPATCH,
            TaskPhase.IDEMPOTENCY_RESERVED,
        }:
            raise RecoveryFencedError(
                "Task phase cannot be cancelled without fabricating certainty."
            )
        decision = self._checkpoint_policy_decision(checkpoint)
        operation = OperationContext(checkpoint.current_idempotency_key or "")
        result = {
            **self._decision_fields(decision),
            "success": False,
            "allowed": False,
            "blocked": True,
            "cancelled": True,
            "policy_allowed": decision.allowed,
            "dispatched": False,
            "result_reason_code": "OPERATOR_RECOVERY_CANCELLED",
            "message": "Operator cancelled recoverable work before dispatch.",
        }
        if checkpoint.phase is TaskPhase.IDEMPOTENCY_RESERVED:
            record = self.idempotency_store.load(operation)
            if record is None:
                raise RecoveryFencedError(
                    "Reserved cancellation lacks its P0.7 record."
                )
            context = ActionContext(
                request_id=record.request_id,
                trace_id=record.trace_id,
                task_id=record.task_id or "",
                action_id=record.action_id,
                model_call_id=record.model_call_id,
            )
            terminal_result = self._terminalize_existing_reservation(
                {},
                decision,
                context,
                operation,
                checkpoint,
                record,
                IdempotencyState.CANCELLED,
                result,
                recovery_token=recovery_token,
            )
            return self._redact_result(
                self._attach_recovery_outcome(terminal_result, checkpoint)
            )
        self._require_pre_dispatch_checkpoint(checkpoint)
        context = self._checkpoint_action_context(checkpoint)
        self._require_pristine_pre_dispatch_provenance(
            checkpoint, context, operation
        )
        if self.idempotency_store.load(operation) is not None:
            raise RecoveryFencedError(
                "Pre-dispatch cancellation found unexpected P0.7 state."
            )
        cancelled_result = self._cancel_new_pre_dispatch_operation(
            checkpoint,
            context,
            operation,
            decision,
            result,
            recovery_token=recovery_token,
        )
        return self._redact_result(
            self._attach_recovery_outcome(cancelled_result, checkpoint)
        )

    @staticmethod
    def _attach_authoritative_outcome(
        result: dict[str, Any],
        action_context: ActionContext,
    ) -> dict[str, Any]:
        return attach_outcome(
            result,
            request_id=action_context.request_id,
            trace_id=action_context.trace_id,
            task_id=action_context.task_id,
            model_call_id=action_context.model_call_id,
            action_id=action_context.action_id,
        )

    @staticmethod
    def _attach_recovery_outcome(
        result: dict[str, Any],
        checkpoint: TaskCheckpoint,
    ) -> dict[str, Any]:
        return attach_outcome(
            result,
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            task_id=checkpoint.task_id,
            model_call_id=checkpoint.current_model_call_id,
            action_id=checkpoint.current_action_id,
        )

    def _get_task_recovery_service(self) -> TaskRecoveryService:
        service = self.task_recovery_service
        if service is None:
            service = TaskRecoveryService(
                self.memory_store.paths.state_dir,
                project_dir=self.project_dir,
                checkpoint_store=self.task_checkpoint_store,
                idempotency_store=self.idempotency_store,
                provenance_store=self.provenance_store,
                lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            )
            self.task_recovery_service = service
        return service

    def _redact_result(self, result: dict[str, Any]) -> dict[str, Any]:
        redacted = self.redactor.redact(result)
        if not isinstance(redacted, dict):
            raise TypeError("Executor result must remain a dictionary")
        return redacted

    def _execution_context_for_guard(
        self,
        action_context: ActionContext,
        *,
        operation_context: OperationContext | None,
        step_reservation: StepReservation | None,
    ) -> ActionContext:
        if operation_context is None or step_reservation is not None:
            return action_context
        existing = self.idempotency_store.load(operation_context)
        if existing is not None and existing.task_id is None:
            raise RuntimeError(
                "Legacy operation is not bound to an authoritative task."
            )
        task_id = (
            existing.task_id
            if existing is not None
            else operation_context.runtime_task_id()
        )
        if action_context.model_call_id is not None and action_context.task_id != task_id:
            raise TraceIdentityError(
                "A model-derived action cannot be rebound to another task."
            )
        return ActionContext(
            request_id=action_context.request_id,
            trace_id=action_context.trace_id,
            task_id=task_id,
            action_id=action_context.action_id,
            model_call_id=action_context.model_call_id,
        )

    def _validate_recovery_token(
        self,
        task_id: str,
        token: RecoveryExecutionToken,
    ) -> None:
        if token.task_id != task_id:
            raise RecoveryFencedError(
                "Execution token does not match the action task."
            )
        # Temporary strict adapter until TaskRecoveryService exposes a lighter
        # public token-validation method.
        self._get_task_recovery_service().classify_under_claim(task_id, token)

    def _execute(
        self,
        action: dict[str, Any],
        require_approval: bool = True,
        *,
        action_context: ActionContext,
        operation_context: OperationContext | None = None,
        step_reservation: StepReservation | None = None,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Evaluate runtime policy, obtain approval when required, then dispatch.

        ``require_approval`` remains for call-site compatibility but cannot disable
        the runtime-owned capability policy. A caller or model may only make the
        final decision more restrictive. ``operation_context`` is a trusted
        runtime retry identity; model fields with the same name are stripped.
        """
        _ = require_approval
        authoritative_context = action_context
        authoritative_action = strip_untrusted_identity_fields(action)
        operation = operation_context or OperationContext.new_operation()
        direct_operation_compatibility = (
            operation_context is not None and step_reservation is None
        )
        preflight_decision: ActionPolicyDecision | None = None
        preflight_fingerprint: str | None = None
        preflight_reservation: IdempotencyResolution | None = None
        preflight_resolution_event_id: str | None = None
        preflight_approval_granted = False
        initial_task_checkpoint: TaskCheckpoint | None = None

        # The legacy/direct API has no caller-owned StepReservation.  Resolve its
        # trusted operation key atomically before minting task-step budget.  The
        # deterministic binding is runtime-derived from the trusted key, never
        # accepted from model JSON.  Thus two processes racing the same first
        # request contend on one P0.7 owner and only the dispatch winner debits a
        # step.  A model call from another task cannot be re-parented this way.
        if direct_operation_compatibility:
            existing_operation = self.idempotency_store.load(operation)
            if existing_operation is not None and existing_operation.task_id is None:
                raise RuntimeError(
                    "Legacy operation is not bound to an authoritative task."
                )
            bound_task_id = (
                existing_operation.task_id
                if existing_operation is not None
                else operation.runtime_task_id()
            )
            if (
                authoritative_context.model_call_id is not None
                and authoritative_context.task_id != bound_task_id
            ):
                raise TraceIdentityError(
                    "A model-derived action cannot be rebound to another task."
                )
            authoritative_context = ActionContext(
                request_id=authoritative_context.request_id,
                trace_id=authoritative_context.trace_id,
                task_id=bound_task_id,
                action_id=authoritative_context.action_id,
                model_call_id=authoritative_context.model_call_id,
            )
            try:
                # Anchor the stable task before P0.7 can persist RESERVED.  It
                # remains CREATED and consumes no step until this process wins
                # the atomic dispatch reservation.
                initial_task_checkpoint = (
                    self.task_checkpoint_store.ensure_for_action(
                        authoritative_context
                    )
                )
            except PersistenceError as exc:
                raise exc.attach_correlation(
                    authoritative_context.identity_fields()
                )
            preflight_decision = evaluate_action_policy(
                authoritative_action, authoritative_context
            )
            self._record_capability_decision(
                authoritative_action,
                preflight_decision,
                authoritative_context,
                operation,
            )
            if not preflight_decision.allowed:
                blocked_result = self._blocked_policy_result(preflight_decision)
                if initial_task_checkpoint.state not in TERMINAL_TASK_STATES:
                    self._checkpoint_task(
                        initial_task_checkpoint,
                        state=TaskState.BLOCKED,
                        phase=TaskPhase.TERMINAL,
                        reason_code="TASK_BLOCKED",
                        action_context=authoritative_context,
                        operation_context=operation,
                        action_name="unknown_action",
                        policy_reason_code=preflight_decision.reason_code,
                        approval_state=ApprovalState.NOT_APPLICABLE,
                    )
                return blocked_result
            preflight_tool = self.tools.get(preflight_decision.action_name)
            if preflight_tool is None:
                if initial_task_checkpoint.state not in TERMINAL_TASK_STATES:
                    self._checkpoint_task(
                        initial_task_checkpoint,
                        state=TaskState.BLOCKED,
                        phase=TaskPhase.TERMINAL,
                        reason_code="TASK_BLOCKED",
                        action_context=authoritative_context,
                        operation_context=operation,
                        action_name=(
                            preflight_decision.action_name or "unknown_action"
                        ),
                        policy_reason_code="ACTION_HANDLER_MISSING",
                        approval_state=ApprovalState.NOT_APPLICABLE,
                    )
                return {
                    **self._decision_fields(preflight_decision),
                    "success": False,
                    "allowed": False,
                    "blocked": True,
                    "cancelled": False,
                    "policy_allowed": preflight_decision.allowed,
                    "policy_reason_code": "ACTION_HANDLER_MISSING",
                    "message": "Runtime capability policy blocked an action without a handler.",
                }
            preflight_fingerprint = canonical_action_fingerprint(
                authoritative_action,
                project_dir=self.project_dir,
                capability_class=preflight_decision.capability_class,
            )
            if preflight_decision.requires_confirmation:
                preflight_approval_granted = self._request_approval(
                    authoritative_action,
                    preflight_decision,
                    authoritative_context,
                )
                self._record_approval_decision(
                    preflight_approval_granted,
                    authoritative_action,
                    preflight_decision,
                    authoritative_context,
                    operation,
                )
                if not preflight_approval_granted:
                    cancelled_result = {
                        **self._decision_fields(preflight_decision),
                        "success": False,
                        "allowed": False,
                        "blocked": True,
                        "cancelled": True,
                        "dispatched": False,
                        "result_reason_code": "HUMAN_APPROVAL_DECLINED",
                    }
                    return self._record_without_dispatch(
                        authoritative_action,
                        preflight_decision,
                        authoritative_context,
                        operation,
                        IdempotencyState.CANCELLED,
                        cancelled_result,
                        task_checkpoint=initial_task_checkpoint,
                    )
            preflight_reservation = self._reserve_operation(
                operation,
                authoritative_context,
                preflight_decision,
                preflight_fingerprint,
            )
            preflight_resolution_event_id = self._after_idempotency_resolution(
                preflight_reservation,
                authoritative_action,
                preflight_decision,
                authoritative_context,
                operation,
            )
            if not preflight_reservation.dispatch_allowed:
                result = self._resolution_result(
                    preflight_reservation,
                    authoritative_context,
                    operation,
                )
                self._record_execution(
                    authoritative_action,
                    result,
                    authoritative_context,
                    operation_context=operation,
                )
                return result
        if initial_task_checkpoint is None:
            try:
                initial_task_checkpoint = (
                    self.task_checkpoint_store.ensure_for_action(
                        authoritative_context
                    )
                )
            except PersistenceError as exc:
                raise exc.attach_correlation(
                    authoritative_context.identity_fields()
                )
        standalone_task = (
            initial_task_checkpoint.reason_code
            == "STANDALONE_ACTION_TASK_CREATED"
        )
        if step_reservation is None:
            try:
                step_reservation = self.task_checkpoint_store.reserve_step(
                    authoritative_context.task_id
                )
            except PersistenceError as exc:
                raise exc.attach_correlation(
                    authoritative_context.identity_fields()
                )
        try:
            task_checkpoint = self.task_checkpoint_store.consume_step_reservation(
                step_reservation,
                task_id=authoritative_context.task_id,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(authoritative_context.identity_fields())
        task_checkpoint = self._checkpoint_task(
            task_checkpoint,
            state=TaskState.RUNNING,
            phase=TaskPhase.BEFORE_ACTION_POLICY,
            reason_code="TASK_BEFORE_ACTION_POLICY",
            action_context=authoritative_context,
            operation_context=operation,
            action_name=(
                authoritative_action["action"]
                if isinstance(authoritative_action.get("action"), str)
                and authoritative_action["action"] in ACTION_SEMANTIC_FIELDS
                else "unknown_action"
            ),
            approval_state=ApprovalState.NOT_APPLICABLE,
            safe_resume_classification=SafeResumeClassification.MANUAL_REVIEW_REQUIRED,
        )
        decision = preflight_decision or evaluate_action_policy(
            authoritative_action, authoritative_context
        )
        name = decision.action_name
        if preflight_decision is None:
            self._record_capability_decision(
                authoritative_action,
                decision,
                authoritative_context,
                operation,
            )

        if not decision.allowed:
            blocked_result = self._blocked_policy_result(decision)
            if name not in ACTION_SEMANTIC_FIELDS:
                self._checkpoint_task(
                    task_checkpoint,
                    state=TaskState.BLOCKED,
                    phase=TaskPhase.TERMINAL,
                    reason_code="TASK_BLOCKED",
                    action_context=authoritative_context,
                    operation_context=operation,
                    action_name="unknown_action",
                    policy_reason_code=decision.reason_code,
                    approval_state=ApprovalState.NOT_APPLICABLE,
                )
                return blocked_result
            return self._record_without_dispatch(
                authoritative_action,
                decision,
                authoritative_context,
                operation,
                IdempotencyState.BLOCKED,
                blocked_result,
                task_checkpoint=task_checkpoint,
            )

        tool = self.tools.get(name)
        if tool is None:
            self._checkpoint_task(
                task_checkpoint,
                state=TaskState.BLOCKED,
                phase=TaskPhase.TERMINAL,
                reason_code="TASK_BLOCKED",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name or "unknown_action",
                policy_reason_code="ACTION_HANDLER_MISSING",
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
            return {
                **self._decision_fields(decision),
                "success": False,
                "allowed": False,
                "blocked": True,
                "cancelled": False,
                "policy_allowed": decision.allowed,
                "policy_reason_code": "ACTION_HANDLER_MISSING",
                "message": "Runtime capability policy blocked an action without a handler.",
            }

        fingerprint = preflight_fingerprint or canonical_action_fingerprint(
            authoritative_action,
            project_dir=self.project_dir,
            capability_class=decision.capability_class,
        )
        if decision.requires_confirmation and not preflight_approval_granted:
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.WAITING_FOR_APPROVAL,
                phase=TaskPhase.WAITING_FOR_APPROVAL,
                reason_code="TASK_WAITING_FOR_APPROVAL",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                approval_state=ApprovalState.WAITING,
                safe_resume_classification=SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            )
            approved = self._request_approval(
                authoritative_action,
                decision,
                authoritative_context,
            )
            self._record_approval_decision(
                approved,
                authoritative_action,
                decision,
                authoritative_context,
                operation,
            )
            if not approved:
                cancelled_result = {
                    **self._decision_fields(decision),
                    "success": False,
                    "allowed": False,
                    "blocked": True,
                    "cancelled": True,
                    "policy_allowed": decision.allowed,
                    "result_reason_code": "HUMAN_APPROVAL_DECLINED",
                    "message": "Action rejected by user before tool dispatch.",
                }
                return self._record_without_dispatch(
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                    IdempotencyState.CANCELLED,
                    cancelled_result,
                    task_checkpoint=task_checkpoint,
                )
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                approval_state=ApprovalState.GRANTED_IN_PROCESS,
                safe_resume_classification=SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            )
        elif decision.requires_confirmation:
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_APPROVAL_GRANTED_IN_PROCESS",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                approval_state=ApprovalState.GRANTED_IN_PROCESS,
                safe_resume_classification=SafeResumeClassification.WAITING_FOR_FRESH_APPROVAL,
            )
        else:
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.RUNNING,
                phase=TaskPhase.BEFORE_DISPATCH,
                reason_code="TASK_BEFORE_DISPATCH",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                approval_state=ApprovalState.NOT_REQUIRED,
                safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
            )
        reservation = preflight_reservation or self._reserve_operation(
            operation,
            authoritative_context,
            decision,
            fingerprint,
        )
        resolution_event_id = preflight_resolution_event_id
        if resolution_event_id is None:
            resolution_event_id = self._after_idempotency_resolution(
                reservation,
                authoritative_action,
                decision,
                authoritative_context,
                operation,
            )
        if not reservation.dispatch_allowed:
            result = self._resolution_result(
                reservation,
                authoritative_context,
                operation,
            )
            self._record_execution(
                authoritative_action,
                result,
                authoritative_context,
                operation_context=operation,
            )
            resolved_state, resolved_reason = self._task_truth_for_resolution(
                reservation
            )
            self._checkpoint_task(
                task_checkpoint,
                state=resolved_state,
                phase=(
                    TaskPhase.IDEMPOTENCY_RESERVED
                    if resolved_state is TaskState.RECOVERY_REQUIRED
                    else TaskPhase.TERMINAL
                ),
                reason_code=resolved_reason,
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                idempotency_state=(
                    IdempotencyState.CONFLICT.value
                    if getattr(reservation.kind, "value", reservation.kind)
                    == IdempotencyResolutionKind.CONFLICT.value
                    else reservation.record.state.value
                ),
                latest_provenance_event_id=resolution_event_id,
                approval_state=(
                    ApprovalState.FRESH_APPROVAL_REQUIRED
                    if resolved_state is TaskState.RECOVERY_REQUIRED
                    and decision.requires_confirmation
                    else ApprovalState.NOT_REQUIRED
                    if resolved_state is TaskState.RECOVERY_REQUIRED
                    else ApprovalState.NOT_APPLICABLE
                ),
            )
            return result

        task_checkpoint = self._checkpoint_task(
            task_checkpoint,
            state=TaskState.RUNNING,
            phase=TaskPhase.IDEMPOTENCY_RESERVED,
            reason_code="TASK_IDEMPOTENCY_RESERVED",
            action_context=authoritative_context,
            operation_context=operation,
            action_name=name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=reservation.record.state.value,
            latest_provenance_event_id=resolution_event_id,
            approval_state=(
                ApprovalState.FRESH_APPROVAL_REQUIRED
                if decision.requires_confirmation
                else ApprovalState.NOT_REQUIRED
            ),
        )

        return self._dispatch_reserved_operation(
            authoritative_action,
            decision,
            authoritative_context,
            operation,
            reservation.record,
            task_checkpoint,
            tool,
            recovery_token=recovery_token,
            standalone_task=standalone_task,
            require_pristine_reserved_provenance=False,
            fresh_approval_required=decision.requires_confirmation,
            recovery_resume=False,
        )

    def _dispatch_reserved_operation(
        self,
        authoritative_action: dict[str, Any],
        decision: ActionPolicyDecision,
        authoritative_context: ActionContext,
        operation: OperationContext,
        idempotency_record: IdempotencyRecord,
        task_checkpoint: TaskCheckpoint,
        tool: ToolSpec,
        *,
        recovery_token: RecoveryExecutionToken,
        standalone_task: bool,
        require_pristine_reserved_provenance: bool,
        fresh_approval_required: bool,
        recovery_resume: bool,
    ) -> dict[str, Any]:
        """Run the sole post-RESERVED dispatch tail for live and recovery paths."""

        fingerprint = idempotency_record.action_fingerprint
        name = decision.action_name
        checkpoint_recovery_token = recovery_token if recovery_resume else None
        self._validate_recovery_token(
            authoritative_context.task_id,
            recovery_token,
        )
        current_record = self.idempotency_store.load(operation)
        if current_record is None:
            raise RecoveryFencedError(
                "Reserved operation disappeared before dispatch."
            )
        self._require_reserved_record_binding(
            task_checkpoint,
            current_record,
            authoritative_context,
            operation,
            action_name=name,
            action_fingerprint=fingerprint,
        )
        if current_record != idempotency_record:
            raise RecoveryFencedError(
                "Reserved operation changed before dispatch."
            )
        if require_pristine_reserved_provenance:
            self._require_pristine_reserved_provenance(
                task_checkpoint, current_record
            )

        # The synchronous, fsynced provenance start is the final dispatch gate.
        # Never put this event in the outbox: recovery must not later claim a
        # dispatch started when the handler was actually blocked.
        self._validate_recovery_token(
            authoritative_context.task_id,
            recovery_token,
        )
        try:
            dispatch_start_event_id = self._before_tool_dispatch(
                authoritative_action,
                decision,
                authoritative_context,
                operation,
                idempotency_record,
            )
        except Exception as start_error:
            try:
                failed_record = self._transition_operation(
                    operation,
                    authoritative_context,
                    fingerprint,
                    IdempotencyState.FAILED_BEFORE_DISPATCH,
                    IDEMPOTENCY_STATE_REASON_CODES[
                        IdempotencyState.FAILED_BEFORE_DISPATCH
                    ],
                    terminal_receipt={
                        "receipt_schema_version": "AOIA_IDEMPOTENCY_RECEIPT_1A",
                        "success": False,
                    },
                )
                terminal_event_id = self._after_idempotency_transition(
                    failed_record,
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                )
            except Exception as cleanup_error:
                self._attach_secondary_failure(
                    start_error,
                    cleanup_error,
                    "Pre-dispatch provenance failed and durable failure terminalization also failed.",
                )
            raise

        # Once P0.8 durably says dispatch started, any later persistence fault is
        # an uncertain crash window. Do not rewrite P0.7 to
        # FAILED_BEFORE_DISPATCH: recovery must observe the start evidence and
        # refuse automatic redispatch even though the handler was not yet called.
        task_checkpoint = self._checkpoint_task(
            task_checkpoint,
            state=TaskState.RUNNING,
            phase=TaskPhase.PROVENANCE_DISPATCH_RECORDED,
            reason_code="TASK_PROVENANCE_DISPATCH_RECORDED",
            action_context=authoritative_context,
            operation_context=operation,
            action_name=name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=idempotency_record.state.value,
            latest_provenance_event_id=dispatch_start_event_id,
            approval_state=(
                ApprovalState.FRESH_APPROVAL_REQUIRED
                if fresh_approval_required
                else ApprovalState.NOT_REQUIRED
            ),
            safe_resume_classification=SafeResumeClassification.MANUAL_REVIEW_REQUIRED,
            checkpoint_recovery_token=checkpoint_recovery_token,
        )

        try:
            dispatch_record = self._transition_operation(
                operation,
                authoritative_context,
                fingerprint,
                IdempotencyState.DISPATCH_STARTED,
                "IDEMPOTENCY_DISPATCH_STARTED",
            )
        except Exception as transition_error:
            try:
                self._record_persistence_failure(
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                    idempotency_state=IdempotencyState.RESERVED,
                    dispatched=False,
                    reason_code="IDEMPOTENCY_TRANSITION_FAILED",
                    action_fingerprint=fingerprint,
                )
            except Exception as provenance_error:
                self._attach_secondary_failure(
                    transition_error,
                    provenance_error,
                    "Idempotency dispatch transition and persistence-failure provenance both failed.",
                )
            raise
        self._after_idempotency_transition(
            dispatch_record,
            authoritative_action,
            decision,
            authoritative_context,
            operation,
        )
        task_checkpoint = self._checkpoint_task(
            task_checkpoint,
            state=TaskState.RUNNING,
            phase=TaskPhase.DISPATCH_IN_FLIGHT,
            reason_code="TASK_DISPATCH_IN_FLIGHT",
            action_context=authoritative_context,
            operation_context=operation,
            action_name=name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=dispatch_record.state.value,
            approval_state=(
                ApprovalState.FRESH_APPROVAL_REQUIRED
                if fresh_approval_required
                else ApprovalState.NOT_REQUIRED
            ),
            safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
            checkpoint_recovery_token=checkpoint_recovery_token,
        )
        try:
            self._validate_recovery_token(
                authoritative_context.task_id,
                recovery_token,
            )
            result = self._correlate_result(
                tool.handler(authoritative_action),
                authoritative_context,
            )
        except Exception as handler_error:
            # Once DISPATCH_STARTED is durable, an exception cannot prove that
            # no effect occurred. Never make the key retryable automatically.
            try:
                unknown_record = self._transition_operation(
                    operation,
                    authoritative_context,
                    fingerprint,
                    IdempotencyState.UNKNOWN_OUTCOME,
                    IDEMPOTENCY_UNKNOWN_OUTCOME_REASON_CODE,
                    terminal_receipt={
                        "receipt_schema_version": "AOIA_IDEMPOTENCY_RECEIPT_1A",
                        "success": False,
                        "unknown_outcome": True,
                    },
                )
                terminal_event_id = self._after_idempotency_transition(
                    unknown_record,
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                )
                self._checkpoint_task(
                    task_checkpoint,
                    state=TaskState.RECOVERY_REQUIRED,
                    phase=TaskPhase.DISPATCH_IN_FLIGHT,
                    reason_code="TASK_ACTION_UNKNOWN_OUTCOME",
                    action_context=authoritative_context,
                    operation_context=operation,
                    action_name=name,
                    action_fingerprint=fingerprint,
                    capability_class=decision.capability_class.value,
                    policy_reason_code=decision.reason_code,
                    idempotency_state=unknown_record.state.value,
                    latest_provenance_event_id=terminal_event_id,
                    approval_state=(
                        ApprovalState.FRESH_APPROVAL_REQUIRED
                        if fresh_approval_required
                        else ApprovalState.NOT_REQUIRED
                    ),
                    safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
                    checkpoint_recovery_token=checkpoint_recovery_token,
                )
            except Exception as transition_error:
                self._attach_secondary_failure(
                    handler_error,
                    transition_error,
                    "Handler failure could not be durably terminalized; operation may remain DISPATCH_STARTED and provenance may be pending.",
                )
            raise

        terminal_state, terminal_reason = self._terminal_state_for_result(result)
        try:
            terminal_record = self._transition_operation(
                operation,
                authoritative_context,
                fingerprint,
                terminal_state,
                terminal_reason,
                terminal_receipt=build_safe_result_receipt(result),
            )
        except Exception as transition_error:
            try:
                self._record_persistence_failure(
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                    idempotency_state=IdempotencyState.DISPATCH_STARTED,
                    dispatched=True,
                    reason_code="IDEMPOTENCY_TRANSITION_FAILED",
                    action_fingerprint=fingerprint,
                )
            except Exception as provenance_error:
                self._attach_secondary_failure(
                    transition_error,
                    provenance_error,
                    "Terminal idempotency transition and persistence-failure provenance both failed.",
                )
            raise
        terminal_event_id = self._after_idempotency_transition(
            terminal_record,
            authoritative_action,
            decision,
            authoritative_context,
            operation,
        )
        if terminal_state in {
            IdempotencyState.TIMED_OUT_OR_UNKNOWN,
            IdempotencyState.UNKNOWN_OUTCOME,
        }:
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.RECOVERY_REQUIRED,
                phase=TaskPhase.DISPATCH_IN_FLIGHT,
                reason_code="TASK_ACTION_UNKNOWN_OUTCOME",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                idempotency_state=terminal_record.state.value,
                latest_provenance_event_id=terminal_event_id,
                approval_state=(
                    ApprovalState.FRESH_APPROVAL_REQUIRED
                    if fresh_approval_required
                    else ApprovalState.NOT_REQUIRED
                ),
                safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
                checkpoint_recovery_token=checkpoint_recovery_token,
            )
        else:
            task_checkpoint = self._checkpoint_task(
                task_checkpoint,
                state=TaskState.RUNNING,
                phase=TaskPhase.AFTER_ACTION,
                reason_code="TASK_ACTION_COMPLETED",
                action_context=authoritative_context,
                operation_context=operation,
                action_name=name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                idempotency_state=terminal_record.state.value,
                latest_provenance_event_id=terminal_event_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
                safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
                checkpoint_recovery_token=checkpoint_recovery_token,
            )
            if standalone_task:
                standalone_state = (
                    TaskState.COMPLETED
                    if terminal_state is IdempotencyState.SUCCEEDED
                    else TaskState.FAILED
                )
                task_checkpoint = self._checkpoint_task(
                    task_checkpoint,
                    state=standalone_state,
                    phase=TaskPhase.TERMINAL,
                    reason_code=(
                        "TASK_COMPLETED"
                        if standalone_state is TaskState.COMPLETED
                        else "TASK_FAILED"
                    ),
                    action_context=authoritative_context,
                    operation_context=operation,
                    action_name=name,
                    action_fingerprint=fingerprint,
                    capability_class=decision.capability_class.value,
                    policy_reason_code=decision.reason_code,
                    idempotency_state=terminal_record.state.value,
                    latest_provenance_event_id=terminal_event_id,
                    approval_state=ApprovalState.NOT_APPLICABLE,
                    checkpoint_recovery_token=checkpoint_recovery_token,
                )
        result = self._with_idempotency_fields(
            result,
            operation,
            terminal_record,
            replayed=False,
            dispatched=True,
        )
        try:
            self._record_execution(
                authoritative_action,
                result,
                authoritative_context,
                operation_context=operation,
            )
        except PersistenceError as operational_error:
            try:
                self._record_persistence_failure(
                    authoritative_action,
                    decision,
                    authoritative_context,
                    operation,
                    idempotency_state=terminal_record.state,
                    dispatched=True,
                    reason_code="OPERATIONAL_LOG_PERSISTENCE_FAILED",
                    action_fingerprint=terminal_record.action_fingerprint,
                )
            except Exception as provenance_error:
                self._attach_secondary_failure(
                    operational_error,
                    provenance_error,
                    "Operational logging and persistence-failure provenance both failed.",
                )
            raise
        return result

    @staticmethod
    def _require_pre_dispatch_checkpoint(checkpoint: TaskCheckpoint) -> None:
        waiting = (
            checkpoint.state is TaskState.WAITING_FOR_APPROVAL
            and checkpoint.phase is TaskPhase.WAITING_FOR_APPROVAL
            and checkpoint.reason_code == "TASK_WAITING_FOR_APPROVAL"
            and checkpoint.approval_state is ApprovalState.WAITING
        )
        before_dispatch = (
            checkpoint.state is TaskState.RUNNING
            and checkpoint.phase is TaskPhase.BEFORE_DISPATCH
            and checkpoint.reason_code
            in {"TASK_BEFORE_DISPATCH", "TASK_APPROVAL_GRANTED_IN_PROCESS"}
            and checkpoint.approval_state
            in {
                ApprovalState.NOT_REQUIRED,
                ApprovalState.GRANTED_IN_PROCESS,
                ApprovalState.FRESH_APPROVAL_REQUIRED,
            }
        )
        if (
            not (waiting or before_dispatch)
            or checkpoint.current_action_id is None
            or checkpoint.current_idempotency_key is None
            or checkpoint.current_action_fingerprint is None
            or checkpoint.current_action_name is None
            or checkpoint.current_action_name == "unknown_action"
            or checkpoint.current_capability_class is None
            or checkpoint.current_policy_reason_code is None
            or checkpoint.current_idempotency_state is not None
        ):
            raise RecoveryFencedError(
                "Task is not at an exact recoverable pre-P0.7 action boundary."
            )

    @staticmethod
    def _checkpoint_action_context(checkpoint: TaskCheckpoint) -> ActionContext:
        if checkpoint.current_action_id is None:
            raise RecoveryFencedError(
                "Recoverable action checkpoint lacks its action identity."
            )
        return ActionContext(
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            task_id=checkpoint.task_id,
            action_id=checkpoint.current_action_id,
            model_call_id=checkpoint.current_model_call_id,
        )

    def _checkpoint_policy_decision(
        self, checkpoint: TaskCheckpoint
    ) -> ActionPolicyDecision:
        if (
            checkpoint.current_action_name is None
            or checkpoint.current_capability_class is None
            or checkpoint.current_policy_reason_code is None
            or checkpoint.current_action_id is None
        ):
            raise RecoveryFencedError(
                "Recoverable action lacks durable policy identity."
            )
        try:
            capability = CapabilityClass(checkpoint.current_capability_class)
        except ValueError as exc:
            raise RecoveryFencedError(
                "Recoverable action capability is not canonical."
            ) from exc
        approval_required = (
            checkpoint.approval_state is not ApprovalState.NOT_REQUIRED
        )
        return ActionPolicyDecision(
            action_name=checkpoint.current_action_name,
            capability_class=capability,
            allowed=True,
            requires_confirmation=approval_required,
            reason_code=checkpoint.current_policy_reason_code,
            reason="Durable runtime policy bound to operator cancellation.",
            runtime_requires_confirmation=approval_required,
            model_requests_confirmation=False,
            request_id=checkpoint.latest_request_id,
            trace_id=checkpoint.latest_trace_id,
            task_id=checkpoint.task_id,
            action_id=checkpoint.current_action_id,
            model_call_id=checkpoint.current_model_call_id,
        )

    def _require_pristine_pre_dispatch_provenance(
        self,
        checkpoint: TaskCheckpoint,
        action_context: ActionContext,
        operation: OperationContext,
    ) -> None:
        records = self.provenance_store.read_runtime_all()
        matching = [
            item
            for item in records
            if item.get("task_id") == checkpoint.task_id
            and item.get("operation_key") == operation.operation_key
            and item.get("action_id") == checkpoint.current_action_id
        ]
        capability_events = [
            item
            for item in matching
            if item.get("event_type")
            == RuntimeProvenanceEventType.CAPABILITY_DECISION.value
            and item.get("request_id") == action_context.request_id
            and item.get("trace_id") == action_context.trace_id
            and item.get("model_call_id") == action_context.model_call_id
            and item.get("action_name") == checkpoint.current_action_name
            and item.get("capability_class")
            == checkpoint.current_capability_class
            and item.get("reason_code") == checkpoint.current_policy_reason_code
        ]
        if not capability_events:
            raise RecoveryFencedError(
                "Pre-dispatch checkpoint lacks its exact P0.8 policy evidence."
            )
        if checkpoint.reason_code == "TASK_APPROVAL_GRANTED_IN_PROCESS" and not any(
            item.get("event_type")
            == RuntimeProvenanceEventType.APPROVAL_GRANTED.value
            and item.get("request_id") == action_context.request_id
            and item.get("trace_id") == action_context.trace_id
            and item.get("model_call_id") == action_context.model_call_id
            and item.get("action_name") == checkpoint.current_action_name
            and item.get("capability_class")
            == checkpoint.current_capability_class
            and item.get("success") is True
            for item in matching
        ):
            raise RecoveryFencedError(
                "Granted-in-process checkpoint lacks its original P0.8 approval evidence."
            )
        unsafe_types = {
            RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED.value,
            RuntimeProvenanceEventType.IDEMPOTENCY_REPLAYED.value,
            RuntimeProvenanceEventType.IDEMPOTENCY_CONFLICT.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_SUCCEEDED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_FAILED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_TIMED_OUT.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_BLOCKED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_CANCELLED.value,
            RuntimeProvenanceEventType.UNKNOWN_OUTCOME_DETECTED.value,
            RuntimeProvenanceEventType.PERSISTENCE_FAILURE.value,
            RuntimeProvenanceEventType.RECOVERY_TERMINAL_RECONCILED.value,
        }
        if any(item.get("event_type") in unsafe_types for item in matching):
            raise RecoveryFencedError(
                "Pre-dispatch recovery found P0.7/P0.8 dispatch or terminal evidence."
            )

    def _terminalize_new_pre_dispatch_operation(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation: OperationContext,
        checkpoint: TaskCheckpoint,
        terminal_state: IdempotencyState,
        result: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        if terminal_state not in {
            IdempotencyState.BLOCKED,
            IdempotencyState.CANCELLED,
        }:
            raise ValueError("Pre-dispatch terminal state is not safely supported.")
        self._validate_recovery_token(checkpoint.task_id, recovery_token)
        self._require_pre_dispatch_checkpoint(checkpoint)
        self._require_pristine_pre_dispatch_provenance(
            checkpoint, action_context, operation
        )
        if self.idempotency_store.load(operation) is not None:
            raise RecoveryFencedError(
                "P0.7 state appeared before safe pre-dispatch terminalization."
            )
        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project_dir,
            capability_class=decision.capability_class,
        )
        if fingerprint != checkpoint.current_action_fingerprint:
            raise RecoveryFencedError(
                "Pre-dispatch terminalization action fingerprint changed."
            )
        reservation = self._reserve_operation(
            operation,
            action_context,
            decision,
            fingerprint,
        )
        self._after_idempotency_resolution(
            reservation,
            action,
            decision,
            action_context,
            operation,
        )
        if not reservation.dispatch_allowed:
            raise RecoveryFencedError(
                "Pre-dispatch terminalization lost its P0.7 reservation race."
            )
        terminal_record = self._transition_operation(
            operation,
            action_context,
            fingerprint,
            terminal_state,
            IDEMPOTENCY_STATE_REASON_CODES[terminal_state],
            terminal_receipt=build_safe_result_receipt(result),
        )
        terminal_event_id = self._after_idempotency_transition(
            terminal_record,
            action,
            decision,
            action_context,
            operation,
        )
        task_state = (
            TaskState.CANCELLED
            if terminal_state is IdempotencyState.CANCELLED
            else TaskState.BLOCKED
        )
        self._checkpoint_task(
            checkpoint,
            state=task_state,
            phase=TaskPhase.TERMINAL,
            reason_code=(
                "TASK_ACTION_CANCELLED"
                if task_state is TaskState.CANCELLED
                else "TASK_ACTION_BLOCKED"
            ),
            action_context=action_context,
            operation_context=operation,
            action_name=decision.action_name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=terminal_record.state.value,
            latest_provenance_event_id=terminal_event_id,
            approval_state=(
                ApprovalState.DENIED
                if task_state is TaskState.CANCELLED
                else ApprovalState.NOT_APPLICABLE
            ),
            safe_resume_classification=(
                SafeResumeClassification.TERMINAL_NO_RESUME
                if task_state is TaskState.CANCELLED
                else SafeResumeClassification.BLOCKED
            ),
            checkpoint_recovery_token=recovery_token,
        )
        return self._with_idempotency_fields(
            {**result, **action_context.identity_fields()},
            operation,
            terminal_record,
            replayed=False,
            dispatched=False,
        )

    def _after_checkpoint_idempotency_reservation(
        self,
        resolution: IdempotencyResolution,
        checkpoint: TaskCheckpoint,
        action_context: ActionContext,
        operation: OperationContext,
        decision: ActionPolicyDecision,
    ) -> str:
        if (
            not resolution.dispatch_allowed
            or resolution.kind is not IdempotencyResolutionKind.RESERVED
            or resolution.record.state is not IdempotencyState.RESERVED
        ):
            raise RecoveryFencedError(
                "Operator cancellation did not obtain the original P0.7 reservation."
            )
        event = new_runtime_provenance_event(
            RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED,
            action_context=action_context,
            operation_context=operation,
            action_name=checkpoint.current_action_name,
            action_fingerprint=checkpoint.current_action_fingerprint,
            capability_class=decision.capability_class,
            idempotency_state=IdempotencyState.RESERVED,
            replayed=False,
            dispatched=False,
            reason_code=resolution.reason_code,
        )
        self.provenance_store.append_runtime_event(event)
        return event.event_id

    def _cancel_new_pre_dispatch_operation(
        self,
        checkpoint: TaskCheckpoint,
        action_context: ActionContext,
        operation: OperationContext,
        decision: ActionPolicyDecision,
        result: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        self._validate_recovery_token(checkpoint.task_id, recovery_token)
        if self.idempotency_store.load(operation) is not None:
            raise RecoveryFencedError(
                "P0.7 state appeared before operator cancellation."
            )
        fingerprint = checkpoint.current_action_fingerprint
        if fingerprint is None:
            raise RecoveryFencedError(
                "Operator cancellation lacks an action fingerprint."
            )
        reservation = self._reserve_operation(
            operation,
            action_context,
            decision,
            fingerprint,
        )
        self._after_checkpoint_idempotency_reservation(
            reservation,
            checkpoint,
            action_context,
            operation,
            decision,
        )
        terminal_record = self._transition_operation(
            operation,
            action_context,
            fingerprint,
            IdempotencyState.CANCELLED,
            IDEMPOTENCY_STATE_REASON_CODES[IdempotencyState.CANCELLED],
            terminal_receipt=build_safe_result_receipt(result),
        )
        terminal_event_id = self._after_idempotency_transition(
            terminal_record,
            {},
            decision,
            action_context,
            operation,
        )
        self._checkpoint_task(
            checkpoint,
            state=TaskState.CANCELLED,
            phase=TaskPhase.TERMINAL,
            reason_code="TASK_ACTION_CANCELLED",
            action_context=action_context,
            operation_context=operation,
            action_name=decision.action_name,
            action_fingerprint=fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=terminal_record.state.value,
            latest_provenance_event_id=terminal_event_id,
            approval_state=ApprovalState.DENIED,
            safe_resume_classification=(
                SafeResumeClassification.TERMINAL_NO_RESUME
            ),
            checkpoint_recovery_token=recovery_token,
        )
        return self._with_idempotency_fields(
            {**result, **action_context.identity_fields()},
            operation,
            terminal_record,
            replayed=False,
            dispatched=False,
        )

    @staticmethod
    def _require_reserved_checkpoint(checkpoint: TaskCheckpoint) -> None:
        if (
            checkpoint.state is not TaskState.RUNNING
            or checkpoint.phase is not TaskPhase.IDEMPOTENCY_RESERVED
            or checkpoint.reason_code != "TASK_IDEMPOTENCY_RESERVED"
            or checkpoint.current_idempotency_state
            != IdempotencyState.RESERVED.value
            or checkpoint.current_action_id is None
            or checkpoint.current_idempotency_key is None
            or checkpoint.current_action_fingerprint is None
            or checkpoint.current_action_name is None
            or checkpoint.current_capability_class is None
            or checkpoint.current_policy_reason_code is None
            or checkpoint.causal_provenance_event_id is None
        ):
            raise RecoveryFencedError(
                "Task is not at an explicit pre-dispatch RESERVED checkpoint."
            )

    def _require_reserved_record_binding(
        self,
        checkpoint: TaskCheckpoint,
        record: IdempotencyRecord,
        action_context: ActionContext,
        operation: OperationContext,
        *,
        action_name: str,
        action_fingerprint: str,
    ) -> None:
        self._require_reserved_checkpoint(checkpoint)
        expected_scope = project_scope_fingerprint(self.project_dir)
        if (
            record.state is not IdempotencyState.RESERVED
            or record.operation_key != operation.operation_key
            or record.project_scope != expected_scope
            or checkpoint.project_scope != expected_scope
            or record.task_id != checkpoint.task_id
            or record.task_id != action_context.task_id
            or record.request_id != action_context.request_id
            or record.trace_id != action_context.trace_id
            or record.action_id != action_context.action_id
            or record.model_call_id != action_context.model_call_id
            or checkpoint.current_action_id != record.action_id
            or checkpoint.current_model_call_id != record.model_call_id
            or checkpoint.current_idempotency_key != record.operation_key
            or checkpoint.current_action_fingerprint != record.action_fingerprint
            or record.action_fingerprint != action_fingerprint
            or checkpoint.current_action_name != action_name
            or checkpoint.current_capability_class != record.capability_class
        ):
            raise RecoveryFencedError(
                "Reserved action does not exactly match checkpoint and P0.7 authority."
            )

    def _require_pristine_reserved_provenance(
        self,
        checkpoint: TaskCheckpoint,
        record: IdempotencyRecord,
    ) -> None:
        records = self.provenance_store.read_runtime_all()
        matching = [
            item
            for item in records
            if item.get("task_id") == record.task_id
            and item.get("operation_key") == record.operation_key
            and item.get("action_id") == record.action_id
            and item.get("action_fingerprint") == record.action_fingerprint
        ]
        reservations = [
            item
            for item in matching
            if item.get("event_type")
            == RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED.value
            and item.get("idempotency_state") == IdempotencyState.RESERVED.value
            and item.get("replayed") is False
            and item.get("dispatched") is False
        ]
        if (
            len(reservations) != 1
            or reservations[0].get("event_id")
            != checkpoint.causal_provenance_event_id
        ):
            raise RecoveryFencedError(
                "Reserved action lacks one exact causal P0.8 reservation event."
            )
        unsafe_event_types = {
            RuntimeProvenanceEventType.IDEMPOTENCY_REPLAYED.value,
            RuntimeProvenanceEventType.IDEMPOTENCY_CONFLICT.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_SUCCEEDED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_FAILED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_TIMED_OUT.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_BLOCKED.value,
            RuntimeProvenanceEventType.ACTION_DISPATCH_CANCELLED.value,
            RuntimeProvenanceEventType.UNKNOWN_OUTCOME_DETECTED.value,
            RuntimeProvenanceEventType.PERSISTENCE_FAILURE.value,
            RuntimeProvenanceEventType.RECOVERY_TERMINAL_RECONCILED.value,
        }
        if any(item.get("event_type") in unsafe_event_types for item in matching):
            raise RecoveryFencedError(
                "P0.8 evidence shows dispatch, terminal, conflict, or uncertainty."
            )

    def _terminalize_existing_reservation(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation: OperationContext,
        checkpoint: TaskCheckpoint,
        expected_record: IdempotencyRecord,
        terminal_state: IdempotencyState,
        result: dict[str, Any],
        *,
        recovery_token: RecoveryExecutionToken,
    ) -> dict[str, Any]:
        """Finish the existing RESERVED record without reserving or dispatching."""

        if terminal_state not in {
            IdempotencyState.BLOCKED,
            IdempotencyState.CANCELLED,
        }:
            raise ValueError("Reserved recovery terminal state is not pre-dispatch safe.")
        self._validate_recovery_token(checkpoint.task_id, recovery_token)
        current_record = self.idempotency_store.load(operation)
        if current_record is None:
            raise RecoveryFencedError(
                "Reserved operation disappeared before safe terminalization."
            )
        self._require_reserved_record_binding(
            checkpoint,
            current_record,
            action_context,
            operation,
            action_name=decision.action_name,
            action_fingerprint=expected_record.action_fingerprint,
        )
        if current_record != expected_record:
            raise RecoveryFencedError(
                "Reserved operation changed before safe terminalization."
            )
        self._require_pristine_reserved_provenance(checkpoint, current_record)
        terminal_record = self._transition_operation(
            operation,
            action_context,
            current_record.action_fingerprint,
            terminal_state,
            IDEMPOTENCY_STATE_REASON_CODES[terminal_state],
            terminal_receipt=build_safe_result_receipt(result),
        )
        terminal_event_id = self._after_idempotency_transition(
            terminal_record,
            action,
            decision,
            action_context,
            operation,
        )
        task_state = (
            TaskState.CANCELLED
            if terminal_state is IdempotencyState.CANCELLED
            else TaskState.BLOCKED
        )
        self._checkpoint_task(
            checkpoint,
            state=task_state,
            phase=TaskPhase.TERMINAL,
            reason_code=(
                "TASK_ACTION_CANCELLED"
                if task_state is TaskState.CANCELLED
                else "TASK_ACTION_BLOCKED"
            ),
            action_context=action_context,
            operation_context=operation,
            action_name=decision.action_name,
            action_fingerprint=terminal_record.action_fingerprint,
            capability_class=decision.capability_class.value,
            policy_reason_code=decision.reason_code,
            idempotency_state=terminal_record.state.value,
            latest_provenance_event_id=terminal_event_id,
            approval_state=(
                ApprovalState.DENIED
                if task_state is TaskState.CANCELLED
                else ApprovalState.NOT_APPLICABLE
            ),
            safe_resume_classification=(
                SafeResumeClassification.TERMINAL_NO_RESUME
                if task_state is TaskState.CANCELLED
                else SafeResumeClassification.BLOCKED
            ),
            checkpoint_recovery_token=recovery_token,
        )
        return self._with_idempotency_fields(
            {**result, **action_context.identity_fields()},
            operation,
            terminal_record,
            replayed=False,
            dispatched=False,
        )

    def _record_without_dispatch(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation: OperationContext,
        terminal_state: IdempotencyState,
        result: dict[str, Any],
        *,
        task_checkpoint: TaskCheckpoint,
    ) -> dict[str, Any]:
        """Persist BLOCKED/CANCELLED truth without entering DISPATCH_STARTED."""

        fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project_dir,
            capability_class=decision.capability_class,
        )
        reservation = self._reserve_operation(
            operation,
            action_context,
            decision,
            fingerprint,
        )
        resolution_event_id = self._after_idempotency_resolution(
            reservation,
            action,
            decision,
            action_context,
            operation,
        )
        if not reservation.dispatch_allowed:
            # Current denial still wins over a previous record: never replay an
            # operation after the human/policy denied this attempt.
            if task_checkpoint.state not in TERMINAL_TASK_STATES:
                self._checkpoint_task(
                    task_checkpoint,
                    state=(
                        TaskState.CANCELLED
                        if terminal_state is IdempotencyState.CANCELLED
                        else TaskState.BLOCKED
                    ),
                    phase=TaskPhase.TERMINAL,
                    reason_code=(
                        "TASK_CANCELLED"
                        if terminal_state is IdempotencyState.CANCELLED
                        else "TASK_BLOCKED"
                    ),
                    action_context=action_context,
                    operation_context=operation,
                    action_name=decision.action_name,
                    action_fingerprint=fingerprint,
                    capability_class=decision.capability_class.value,
                    policy_reason_code=decision.reason_code,
                    idempotency_state=reservation.record.state.value,
                    latest_provenance_event_id=resolution_event_id,
                    approval_state=(
                        ApprovalState.DENIED
                        if terminal_state is IdempotencyState.CANCELLED
                        else ApprovalState.NOT_APPLICABLE
                    ),
                    safe_resume_classification=SafeResumeClassification.TERMINAL_NO_RESUME,
                )
            return {
                **result,
                **action_context.identity_fields(),
                "operation_key": operation.operation_key,
                "idempotency_state": reservation.record.state.value,
                "idempotency_reason_code": reservation.reason_code,
                "replayed": False,
                "dispatched": False,
            }
        terminal_record = self._transition_operation(
            operation,
            action_context,
            fingerprint,
            terminal_state,
            IDEMPOTENCY_STATE_REASON_CODES[terminal_state],
            terminal_receipt=build_safe_result_receipt(result),
        )
        terminal_event_id = self._after_idempotency_transition(
            terminal_record,
            action,
            decision,
            action_context,
            operation,
        )
        if task_checkpoint.state not in TERMINAL_TASK_STATES:
            self._checkpoint_task(
                task_checkpoint,
                state=(
                    TaskState.CANCELLED
                    if terminal_state is IdempotencyState.CANCELLED
                    else TaskState.BLOCKED
                ),
                phase=TaskPhase.TERMINAL,
                reason_code=(
                    "TASK_CANCELLED"
                    if terminal_state is IdempotencyState.CANCELLED
                    else "TASK_BLOCKED"
                ),
                action_context=action_context,
                operation_context=operation,
                action_name=decision.action_name,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class.value,
                policy_reason_code=decision.reason_code,
                idempotency_state=terminal_record.state.value,
                latest_provenance_event_id=terminal_event_id,
                approval_state=(
                    ApprovalState.DENIED
                    if terminal_state is IdempotencyState.CANCELLED
                    else ApprovalState.NOT_APPLICABLE
                ),
                safe_resume_classification=SafeResumeClassification.TERMINAL_NO_RESUME,
            )
        return self._with_idempotency_fields(
            {**result, **action_context.identity_fields()},
            operation,
            terminal_record,
            replayed=False,
            dispatched=False,
        )

    def _reserve_operation(
        self,
        operation: OperationContext,
        action_context: ActionContext,
        decision: ActionPolicyDecision,
        fingerprint: str,
    ) -> IdempotencyResolution:
        try:
            return self.idempotency_store.reserve(
                operation,
                action_context=action_context,
                action_fingerprint=fingerprint,
                capability_class=decision.capability_class,
                project_scope=project_scope_fingerprint(self.project_dir),
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(action_context.identity_fields())

    def _transition_operation(
        self,
        operation: OperationContext,
        action_context: ActionContext,
        fingerprint: str,
        state: IdempotencyState,
        reason_code: str,
        *,
        terminal_receipt: dict[str, Any] | None = None,
    ) -> IdempotencyRecord:
        try:
            return self.idempotency_store.transition(
                operation,
                owner_action_id=action_context.action_id,
                action_fingerprint=fingerprint,
                to_state=state,
                reason_code=reason_code,
                terminal_receipt=terminal_receipt,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(action_context.identity_fields())

    @staticmethod
    def _terminal_state_for_result(
        result: dict[str, Any],
    ) -> tuple[IdempotencyState, str]:
        if result.get("timed_out") is True or result.get("unknown_outcome") is True:
            return (
                IdempotencyState.TIMED_OUT_OR_UNKNOWN,
                IDEMPOTENCY_STATE_REASON_CODES[
                    IdempotencyState.TIMED_OUT_OR_UNKNOWN
                ],
            )
        if result.get("success") is True:
            return (
                IdempotencyState.SUCCEEDED,
                IDEMPOTENCY_STATE_REASON_CODES[IdempotencyState.SUCCEEDED],
            )
        return (
            IdempotencyState.FAILED_REPORTED,
            IDEMPOTENCY_STATE_REASON_CODES[IdempotencyState.FAILED_REPORTED],
        )

    @staticmethod
    def _with_idempotency_fields(
        result: dict[str, Any],
        operation: OperationContext,
        record: IdempotencyRecord,
        *,
        replayed: bool,
        dispatched: bool,
    ) -> dict[str, Any]:
        return {
            **result,
            "operation_key": operation.operation_key,
            "action_fingerprint": record.action_fingerprint,
            "idempotency_state": record.state.value,
            "idempotency_reason_code": record.reason_code,
            "replayed": replayed,
            "dispatched": dispatched,
        }

    @staticmethod
    def _resolution_result(
        resolution: IdempotencyResolution,
        action_context: ActionContext,
        operation: OperationContext,
    ) -> dict[str, Any]:
        record = resolution.record
        receipt = dict(record.terminal_receipt or {})
        if resolution.kind is IdempotencyResolutionKind.CONFLICT:
            state = IdempotencyState.CONFLICT.value
            success = False
            blocked = True
            message = "Operation key conflicts with different semantic action input."
        elif resolution.kind is IdempotencyResolutionKind.IN_PROGRESS:
            state = record.state.value
            success = False
            blocked = True
            message = "Operation is already reserved; automatic duplicate dispatch was blocked."
        elif resolution.kind is IdempotencyResolutionKind.UNKNOWN_OUTCOME:
            state = IdempotencyState.UNKNOWN_OUTCOME.value
            success = False
            blocked = True
            message = "Prior dispatch outcome is uncertain; manual review is required."
        else:
            state = record.state.value
            success = bool(receipt.get("success", False))
            blocked = record.state in {
                IdempotencyState.BLOCKED,
                IdempotencyState.CANCELLED,
                IdempotencyState.FAILED_BEFORE_DISPATCH,
                IdempotencyState.FAILED_REPORTED,
            }
            message = "Stored terminal operation receipt replayed without tool dispatch."

        return {
            **receipt,
            **action_context.identity_fields(),
            "success": success,
            "blocked": blocked,
            "cancelled": record.state is IdempotencyState.CANCELLED,
            "unknown_outcome": resolution.kind
            is IdempotencyResolutionKind.UNKNOWN_OUTCOME,
            "manual_review_required": resolution.kind
            in {
                IdempotencyResolutionKind.IN_PROGRESS,
                IdempotencyResolutionKind.UNKNOWN_OUTCOME,
            },
            "idempotency_conflict": resolution.kind
            is IdempotencyResolutionKind.CONFLICT,
            "result_reason_code": resolution.reason_code,
            "operation_key": operation.operation_key,
            "action_fingerprint": record.action_fingerprint,
            "idempotency_state": state,
            "idempotency_reason_code": resolution.reason_code,
            "replayed": resolution.replayed,
            "dispatched": False,
            "original_request_id": record.request_id,
            "original_trace_id": record.trace_id,
            "original_action_id": record.action_id,
            "original_model_call_id": record.model_call_id,
            "message": message,
        }

    @staticmethod
    def _task_truth_for_resolution(
        resolution: IdempotencyResolution,
    ) -> tuple[TaskState, str]:
        """Map every non-dispatch P0.7 outcome to explicit task truth."""

        if resolution.kind in {
            IdempotencyResolutionKind.IN_PROGRESS,
            IdempotencyResolutionKind.UNKNOWN_OUTCOME,
        }:
            return TaskState.RECOVERY_REQUIRED, "TASK_RECOVERY_REQUIRED"
        if resolution.kind is IdempotencyResolutionKind.CONFLICT:
            return TaskState.BLOCKED, "TASK_IDEMPOTENCY_CONFLICT"
        if resolution.kind is not IdempotencyResolutionKind.REPLAYED:
            raise RuntimeError("Unsupported non-dispatch idempotency resolution.")
        fixed = {
            IdempotencyState.SUCCEEDED: (TaskState.COMPLETED, "TASK_COMPLETED"),
            IdempotencyState.BLOCKED: (TaskState.BLOCKED, "TASK_ACTION_BLOCKED"),
            IdempotencyState.CANCELLED: (
                TaskState.CANCELLED,
                "TASK_ACTION_CANCELLED",
            ),
            IdempotencyState.FAILED_BEFORE_DISPATCH: (
                TaskState.FAILED,
                "TASK_FAILED",
            ),
            IdempotencyState.FAILED_REPORTED: (
                TaskState.FAILED,
                "TASK_FAILED",
            ),
        }
        try:
            return fixed[resolution.record.state]
        except KeyError as exc:
            raise RuntimeError(
                "Unsupported replayed idempotency terminal state."
            ) from exc

    def _checkpoint_task(
        self,
        checkpoint: TaskCheckpoint,
        *,
        state: TaskState,
        phase: TaskPhase,
        reason_code: str,
        action_context: ActionContext,
        operation_context: OperationContext,
        action_name: str,
        action_fingerprint: str | None = None,
        capability_class: str | None = None,
        policy_reason_code: str | None = None,
        idempotency_state: str | None = None,
        latest_provenance_event_id: str | None = None,
        approval_state: ApprovalState = ApprovalState.NOT_APPLICABLE,
        safe_resume_classification: SafeResumeClassification = SafeResumeClassification.MANUAL_REVIEW_REQUIRED,
        checkpoint_recovery_token: RecoveryExecutionToken | None = None,
    ) -> TaskCheckpoint:
        """Advance one task checkpoint using only runtime-owned action metadata."""

        if (
            checkpoint_recovery_token is not None
            and checkpoint_recovery_token.task_id != checkpoint.task_id
        ):
            raise RecoveryFencedError(
                "Checkpoint recovery identity does not match the action task."
            )
        if checkpoint_recovery_token is not None:
            self._validate_recovery_token(
                checkpoint.task_id,
                checkpoint_recovery_token,
            )
        latest_request_id = (
            checkpoint_recovery_token.request_id
            if checkpoint_recovery_token is not None
            else action_context.request_id
        )
        latest_trace_id = (
            checkpoint_recovery_token.trace_id
            if checkpoint_recovery_token is not None
            else action_context.trace_id
        )
        try:
            return self.task_checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=state,
                phase=phase,
                reason_code=reason_code,
                latest_request_id=latest_request_id,
                latest_trace_id=latest_trace_id,
                recovery_attempt_id=(
                    checkpoint_recovery_token.recovery_attempt_id
                    if checkpoint_recovery_token is not None
                    else None
                ),
                current_model_call_id=action_context.model_call_id,
                current_action_id=action_context.action_id,
                current_idempotency_key=operation_context.operation_key,
                current_action_fingerprint=action_fingerprint,
                current_idempotency_state=idempotency_state,
                causal_provenance_event_id=latest_provenance_event_id,
                current_action_name=action_name,
                current_capability_class=capability_class,
                current_policy_reason_code=policy_reason_code,
                approval_state=approval_state,
                safe_resume_classification=safe_resume_classification,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(action_context.identity_fields())

    def _before_tool_dispatch(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
        idempotency_record: IdempotencyRecord,
    ) -> str:
        """Commit dispatch-start truth before idempotency dispatch and handler."""

        event = new_runtime_provenance_event(
                RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED,
                action_context=action_context,
                operation_context=operation_context,
                action_name=decision.action_name,
                action_fingerprint=idempotency_record.action_fingerprint,
                capability_class=decision.capability_class,
                idempotency_state=idempotency_record.state,
                replayed=False,
                dispatched=True,
                reason_code=RuntimeProvenanceEventType.ACTION_DISPATCH_STARTED.value,
        )
        self.provenance_store.append_runtime_event(event)
        return event.event_id

    def _after_idempotency_resolution(
        self,
        resolution: IdempotencyResolution,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
    ) -> None:
        """Record reservation/replay/conflict truth after the P0.7 boundary."""

        attempted_fingerprint = canonical_action_fingerprint(
            action,
            project_dir=self.project_dir,
            capability_class=decision.capability_class,
        )
        kind = getattr(resolution.kind, "value", resolution.kind)
        if kind == IdempotencyResolutionKind.RESERVED.value:
            event_type = RuntimeProvenanceEventType.IDEMPOTENCY_RESERVED
            terminal = False
            success = None
        elif kind == IdempotencyResolutionKind.REPLAYED.value:
            event_type = RuntimeProvenanceEventType.IDEMPOTENCY_REPLAYED
            terminal = False
            success = bool((resolution.record.terminal_receipt or {}).get("success", False))
        elif kind == IdempotencyResolutionKind.CONFLICT.value:
            event_type = RuntimeProvenanceEventType.IDEMPOTENCY_CONFLICT
            terminal = False
            success = False
        elif kind in {
            IdempotencyResolutionKind.IN_PROGRESS.value,
            IdempotencyResolutionKind.UNKNOWN_OUTCOME.value,
        }:
            event_type = RuntimeProvenanceEventType.UNKNOWN_OUTCOME_DETECTED
            terminal = True
            success = False
        else:  # pragma: no cover - P0.7 enum is closed
            raise RuntimeError("Unsupported idempotency resolution kind.")
        event = new_runtime_provenance_event(
            event_type,
            action_context=action_context,
            operation_context=operation_context,
            action_name=decision.action_name,
            action_fingerprint=attempted_fingerprint,
            capability_class=decision.capability_class,
            idempotency_state=(
                IdempotencyState.CONFLICT
                if kind == IdempotencyResolutionKind.CONFLICT.value
                else resolution.record.state
            ),
            replayed=resolution.replayed,
            dispatched=False,
            success=success,
            reason_code=resolution.reason_code,
        )
        if terminal:
            self.provenance_store.append_terminal(event)
        else:
            self.provenance_store.append_runtime_event(event)
        return event.event_id

    def _after_idempotency_transition(
        self,
        record: IdempotencyRecord,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
    ) -> str | None:
        """Append terminal action truth only after P0.7 made it durable."""

        _ = action
        state = getattr(record.state, "value", record.state)
        mapping = {
            IdempotencyState.SUCCEEDED.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_SUCCEEDED,
                True,
                True,
            ),
            IdempotencyState.BLOCKED.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_BLOCKED,
                False,
                False,
            ),
            IdempotencyState.CANCELLED.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_CANCELLED,
                False,
                False,
            ),
            IdempotencyState.FAILED_BEFORE_DISPATCH.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_FAILED,
                False,
                False,
            ),
            IdempotencyState.FAILED_REPORTED.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_FAILED,
                False,
                True,
            ),
            IdempotencyState.TIMED_OUT_OR_UNKNOWN.value: (
                RuntimeProvenanceEventType.ACTION_DISPATCH_TIMED_OUT,
                False,
                True,
            ),
            IdempotencyState.UNKNOWN_OUTCOME.value: (
                RuntimeProvenanceEventType.UNKNOWN_OUTCOME_DETECTED,
                False,
                True,
            ),
        }
        terminal = mapping.get(state)
        if terminal is None:
            # DISPATCH_STARTED has already been recorded at the synchronous
            # provenance gate. RESERVED is represented by its resolution event.
            return None
        event_type, success, dispatched = terminal
        event = new_runtime_provenance_event(
                event_type,
                action_context=action_context,
                operation_context=operation_context,
                action_name=decision.action_name,
                action_fingerprint=record.action_fingerprint,
                capability_class=decision.capability_class,
                idempotency_state=state,
                replayed=False,
                dispatched=dispatched,
                success=success,
                reason_code=record.reason_code,
            )
        self.provenance_store.append_terminal(event)
        return event.event_id

    def _record_capability_decision(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
    ) -> None:
        _ = action
        self.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.CAPABILITY_DECISION,
                action_context=action_context,
                operation_context=operation_context,
                action_name=(
                    decision.action_name
                    if decision.action_name in ACTION_SEMANTIC_FIELDS
                    else "unknown_action"
                ),
                capability_class=decision.capability_class,
                policy_allowed=decision.allowed,
                approval_required=decision.requires_confirmation,
                reason_code=decision.reason_code,
            )
        )

    def _record_approval_decision(
        self,
        approved: bool,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
    ) -> None:
        _ = action
        self.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                (
                    RuntimeProvenanceEventType.APPROVAL_GRANTED
                    if approved
                    else RuntimeProvenanceEventType.APPROVAL_DENIED
                ),
                action_context=action_context,
                operation_context=operation_context,
                action_name=decision.action_name,
                capability_class=decision.capability_class,
                approval_required=True,
                success=approved,
            )
        )

    def _record_persistence_failure(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
        operation_context: OperationContext,
        *,
        idempotency_state: IdempotencyState,
        dispatched: bool,
        reason_code: str,
        action_fingerprint: str | None = None,
    ) -> None:
        _ = action
        self.provenance_store.append_terminal(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.PERSISTENCE_FAILURE,
                action_context=action_context,
                operation_context=operation_context,
                action_name=decision.action_name,
                action_fingerprint=action_fingerprint,
                capability_class=decision.capability_class,
                idempotency_state=idempotency_state,
                dispatched=dispatched,
                success=False,
                reason_code=reason_code,
            )
        )

    @staticmethod
    def _attach_secondary_failure(
        primary_error: BaseException,
        secondary_error: BaseException,
        message: str,
    ) -> None:
        note = (
            f"{message} Secondary failure type: "
            f"{type(secondary_error).__name__}."
        )
        try:
            primary_error.add_note(note)
        except AttributeError:  # pragma: no cover - supported Python has add_note
            pass

    @staticmethod
    def _decision_fields(decision: ActionPolicyDecision) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "action": decision.action_name,
            "capability_class": decision.capability_class.value,
            "allowed": decision.allowed,
            "requires_confirmation": decision.requires_confirmation,
            "runtime_requires_confirmation": decision.runtime_requires_confirmation,
            "model_requests_confirmation": decision.model_requests_confirmation,
            "policy_reason_code": decision.reason_code,
        }
        for field in (
            "task_id",
            "request_id",
            "trace_id",
            "action_id",
            "model_call_id",
        ):
            value = getattr(decision, field)
            if value is not None:
                fields[field] = value
        return fields

    def _blocked_policy_result(self, decision: ActionPolicyDecision) -> dict[str, Any]:
        return {
            **self._decision_fields(decision),
            "success": False,
            "blocked": True,
            "cancelled": False,
            "message": decision.reason,
        }

    def _build_tool_registry(self) -> dict[str, ToolSpec]:
        return {
            "respond": ToolSpec("respond", self._respond, "Return a final answer."),
            "shell_execute": ToolSpec("shell_execute", self._execute_shell_action, "Frozen legacy shell/executor surface."),
            "write_file": ToolSpec(
                "write_file",
                lambda action: write_file(
                    action["path"], action["content"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "append_file": ToolSpec(
                "append_file",
                lambda action: append_file(
                    action["path"], action["content"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "read_file": ToolSpec(
                "read_file",
                lambda action: read_file(action["path"], self.cwd, self.project_dir),
                "Read a text file.",
            ),
            "create_file": ToolSpec(
                "create_file",
                lambda action: create_file(
                    action["path"], self.cwd, action["content"], self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "create_folder": ToolSpec(
                "create_folder",
                lambda action: create_folder(action["path"], self.cwd, self.project_dir),
                "Frozen legacy filesystem surface.",
            ),
            "move_file": ToolSpec(
                "move_file",
                lambda action: move_file(
                    action["src"], action["dst"], self.cwd, self.project_dir
                ),
                "Frozen legacy filesystem surface.",
            ),
            "delete_file": ToolSpec(
                "delete_file",
                lambda action: delete_file(action["path"], self.cwd, self.project_dir),
                "Frozen legacy filesystem surface.",
            ),
            "search_in_project": ToolSpec(
                "search_in_project",
                lambda action: search_in_project(
                    action["pattern"], action["path"], self.cwd, self.project_dir
                ),
                "Search text in project files.",
            ),
            "change_directory": ToolSpec("change_directory", lambda action: self._change_directory(action["path"]), "Change runtime directory."),
            "browser_start": ToolSpec("browser_start", lambda action: browser_start(), "Frozen legacy browser surface."),
            "browser_open": ToolSpec(
                "browser_open",
                lambda action: self._browser_open(action["url"]),
                "Frozen legacy browser surface.",
            ),
            "browser_click": ToolSpec("browser_click", lambda action: browser_click(action["selector"]), "Frozen legacy browser surface."),
            "browser_type": ToolSpec("browser_type", lambda action: browser_type(action["selector"], action["text"]), "Frozen legacy browser surface."),
            "browser_press": ToolSpec("browser_press", lambda action: browser_press(action["key"]), "Frozen legacy browser surface."),
            "browser_read_html": ToolSpec("browser_read_html", lambda action: browser_read_html(), "Frozen legacy browser surface."),
            "browser_get_visible_text": ToolSpec("browser_get_visible_text", lambda action: browser_get_visible_text(), "Frozen legacy browser surface."),
            "browser_screenshot": ToolSpec(
                "browser_screenshot",
                lambda action: self._browser_screenshot(action.get("path") or None),
                "Frozen legacy browser surface.",
            ),
            "browser_close": ToolSpec("browser_close", lambda action: browser_close(), "Frozen legacy browser surface."),
            "browser_current_url": ToolSpec("browser_current_url", lambda action: browser_current_url(), "Frozen legacy browser surface."),
            "scan_project": ToolSpec(
                "scan_project",
                lambda action: scan_project(action["path"], self.cwd, self.project_dir),
                "Scan a repository or project tree.",
            ),
        }

    @staticmethod
    def _respond(action: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "message": action["message"],
            "confidence_label": action.get("confidence_label", "unknown"),
            "stop_loop": True,
        }

    def _execute_shell_action(self, action: dict[str, Any]) -> dict[str, Any]:
        command = action["command"]
        if not _legacy_shell_execution_enabled():
            return shell_execution_blocked_result(command, self.cwd)

        allowed, reason = validate_shell_command(command)
        if not allowed:
            return {
                "success": False,
                "command": command,
                "message": f"Command blocked by validator: {reason}",
            }

        permission = classify_shell_command(command)
        if permission.interactive:
            print("[INFO] Interactive command may ask for password or package confirmation.")

        self.memory_store.record_command(
            command
            if not self._recovery_sensitive_persistence.get()
            else json.dumps(
                {
                    "recovery_sensitive": True,
                    **self._recovery_sensitive_summary(command),
                },
                sort_keys=True,
            )
        )
        return {
            **shell_execute(command, self.cwd, interactive=permission.interactive),
            "permission_mode": permission.mode,
            "permission_reason": permission.reason,
        }

    def _request_approval(
        self,
        action: dict[str, Any],
        decision: ActionPolicyDecision,
        action_context: ActionContext,
    ) -> bool:
        print("\nPROPOSED ACTION")
        print(f"Action: {action['action']}")
        print(f"Action ID: {action_context.action_id}")
        print(f"Capability: {decision.capability_class.value}")
        print(f"Runtime policy: {decision.reason_code}")
        if action.get("reason"):
            print(f"Reason: {self.redactor.redact_text(action['reason'])}")
        for field in ("command", "path", "src", "dst", "url", "selector", "key"):
            if field in action and action[field]:
                print(f"{field}: {self.redactor.redact_text(action[field])}")
        answer = input("Press ENTER to approve, or type n/cancel to reject: ").strip().lower()
        return answer not in {"n", "no", "cancel", "reject", "stop"}

    def _change_directory(self, path_text: str) -> dict:
        target = resolve_path(
            path_text,
            self.cwd,
            self.project_dir,
            operation="change_directory",
        )
        if not target.exists() or not target.is_dir():
            return {
                "success": False,
                "path": str(target),
                "message": f"Directory does not exist: {target}",
            }
        self.cwd = target
        self.memory_store.update_cwd(target)
        return {
            "success": True,
            "path": str(target),
            "message": f"Current directory changed to {target}",
        }

    def _browser_open(self, url: str) -> dict:
        parsed = urlparse(url)
        if parsed.scheme.lower() != "file":
            return browser_open(url)
        if parsed.netloc not in {"", "localhost"}:
            raise FilesystemContainmentError(
                "Filesystem containment blocked browser_open: unsupported file URL."
            )
        local_path = resolve_path(
            unquote(parsed.path),
            self.cwd,
            self.project_dir,
            operation="browser_open local file",
        )
        return browser_open(local_path.as_uri())

    def _browser_screenshot(self, path_text: str | None) -> dict:
        if path_text is None:
            return browser_screenshot()
        target = resolve_path(
            path_text,
            self.cwd,
            self.project_dir,
            operation="browser_screenshot",
        )
        return browser_screenshot(str(target))

    @staticmethod
    def _correlate_result(
        result: dict[str, Any],
        action_context: ActionContext,
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise TypeError("Tool handlers must return a dictionary result.")
        return {
            **result,
            **action_context.identity_fields(),
        }

    def _record_execution(
        self,
        action: dict[str, Any],
        result: dict[str, Any],
        action_context: ActionContext,
        *,
        operation_context: OperationContext | None = None,
    ) -> None:
        identity = action_context.identity_fields()
        for field in ("task_id", "request_id", "trace_id", "action_id"):
            if not identity.get(field) or result.get(field) != identity[field]:
                raise TraceIdentityError(
                    "Operational execution records require authoritative request, trace, and action identity."
                )
        if action_context.model_call_id is not None and (
            result.get("model_call_id") != action_context.model_call_id
        ):
            raise TraceIdentityError(
                "Operational execution model-call identity does not match its action context."
            )
        if operation_context is not None and (
            result.get("operation_key") != operation_context.operation_key
        ):
            raise TraceIdentityError(
                "Operational execution operation key does not match its runtime context."
            )
        sensitive = self._recovery_sensitive_persistence.get()
        logged_action: dict[str, Any]
        logged_result: dict[str, Any]
        if sensitive:
            action_name = action.get("action")
            logged_action = {
                "action": (
                    action_name
                    if isinstance(action_name, str)
                    and action_name in ACTION_SEMANTIC_FIELDS
                    else "unknown_action"
                ),
                **self._recovery_sensitive_summary(action),
            }
            logged_result = {
                "success": result.get("success") is True,
                "dispatched": result.get("dispatched") is True,
                "replayed": result.get("replayed") is True,
                **self._recovery_sensitive_summary(result),
            }
        else:
            logged_action = action
            logged_result = result
        payload = {
            "timestamp": dt.datetime.now().isoformat(),
            **identity,
            "authority": {
                "classification": "operational_event",
                "retention": "replay_only",
                "non_authoritative": True,
                "canonical_evidence": False,
            },
            "action": logged_action,
            "result": logged_result,
            "cwd": str(self.cwd),
        }
        if operation_context is not None:
            payload["operation_key"] = operation_context.operation_key
        safe_payload = self._redact_result(payload)
        filename = (
            dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            + f"_{action_context.action_id}.json"
        )
        command_log_path = self.command_log_dir / filename
        try:
            atomic_write_json(
                command_log_path,
                safe_payload,
                lock_path=state_resource_lock_path(
                    self.memory_store.paths.state_dir,
                    command_log_path,
                ),
                lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            )
            safe_result = safe_payload.get("result", {})
            if not isinstance(safe_result, dict):
                raise TypeError("Operational executor result must remain a dictionary")
            self.memory_store.record_result(safe_result)
            self.memory_store.append_history("action_result", safe_payload)
            # AOIA Phase 2A containment boundary
            # Runtime operational outputs must NEVER become canonical evidence.
            if str(action.get("action", "")).startswith("browser_"):
                self.memory_store.append_browser_event(safe_payload)
        except PersistenceError as exc:
            raise exc.attach_correlation(identity)
