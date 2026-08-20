from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
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
from .capability_policy import ActionPolicyDecision, evaluate_action_policy
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
from .validator import classify_shell_command, validate_shell_command


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
    ) -> None:
        self.project_dir = canonical_project_root(project_dir)
        self.memory_store = memory_store
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
    ) -> dict[str, Any]:
        """Execute with complete persistence-error correlation."""

        authoritative_context = (
            action_context or TraceContext.new_request().new_action()
        )
        try:
            return self._execute(
                action,
                require_approval=require_approval,
                action_context=authoritative_context,
                operation_context=operation_context,
                step_reservation=step_reservation,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(
                authoritative_context.identity_fields()
            )

    def _execute(
        self,
        action: dict[str, Any],
        require_approval: bool = True,
        *,
        action_context: ActionContext,
        operation_context: OperationContext | None = None,
        step_reservation: StepReservation | None = None,
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

        # The synchronous, fsynced provenance start is the final dispatch gate.
        # Never put this event in the outbox: recovery must not later claim a
        # dispatch started when the handler was actually blocked.
        try:
            dispatch_start_event_id = self._before_tool_dispatch(
                authoritative_action,
                decision,
                authoritative_context,
                operation,
                reservation.record,
            )
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
                idempotency_state=reservation.record.state.value,
                latest_provenance_event_id=dispatch_start_event_id,
                approval_state=(
                    ApprovalState.FRESH_APPROVAL_REQUIRED
                    if decision.requires_confirmation
                    else ApprovalState.NOT_REQUIRED
                ),
                safe_resume_classification=SafeResumeClassification.MANUAL_REVIEW_REQUIRED,
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
                if decision.requires_confirmation
                else ApprovalState.NOT_REQUIRED
            ),
            safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
        )
        try:
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
                        if decision.requires_confirmation
                        else ApprovalState.NOT_REQUIRED
                    ),
                    safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
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
                    if decision.requires_confirmation
                    else ApprovalState.NOT_REQUIRED
                ),
                safe_resume_classification=SafeResumeClassification.UNKNOWN_OUTCOME,
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
    ) -> TaskCheckpoint:
        """Advance one task checkpoint using only runtime-owned action metadata."""

        try:
            return self.task_checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=state,
                phase=phase,
                reason_code=reason_code,
                latest_request_id=action_context.request_id,
                latest_trace_id=action_context.trace_id,
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

        self.memory_store.record_command(command)
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
            print(f"Reason: {action['reason']}")
        for field in ("command", "path", "src", "dst", "url", "selector", "key"):
            if field in action and action[field]:
                print(f"{field}: {action[field]}")
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
        payload = {
            "timestamp": dt.datetime.now().isoformat(),
            **identity,
            "authority": {
                "classification": "operational_event",
                "retention": "replay_only",
                "non_authoritative": True,
                "canonical_evidence": False,
            },
            "action": action,
            "result": result,
            "cwd": str(self.cwd),
        }
        if operation_context is not None:
            payload["operation_key"] = operation_context.operation_key
        filename = (
            dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            + f"_{action_context.action_id}.json"
        )
        command_log_path = self.command_log_dir / filename
        try:
            atomic_write_json(
                command_log_path,
                payload,
                lock_path=state_resource_lock_path(
                    self.memory_store.paths.state_dir,
                    command_log_path,
                ),
                lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            )
            self.memory_store.record_result(result)
            self.memory_store.append_history("action_result", payload)
            # AOIA Phase 2A containment boundary
            # Runtime operational outputs must NEVER become canonical evidence.
            if str(action.get("action", "")).startswith("browser_"):
                self.memory_store.append_browser_event(payload)
        except PersistenceError as exc:
            raise exc.attach_correlation(identity)
