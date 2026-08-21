#!/usr/bin/env python3
"""
Local runtime components for proposal inspection, controlled routing, and audit-oriented workflows.

Architecture:
USER -> LLM -> structured JSON action -> executor -> result -> LLM -> final response
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import re
import time
import traceback
from contextlib import contextmanager, redirect_stdout
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import parse_qs, unquote, urlparse

from commands import build_command_registry
from adaptive_routing.epistemic_kernel import AOIAEpistemicKernel
from memory.rhcsa_context import inject_linux_context
from orchestrator import GeminiGemmaOrchestrator
from orchestrator.knowledge_router import KnowledgeRouter
from providers import ProviderManager
from providers.errors import (
    ModelResponseMalformedError,
    provider_reason_code,
    typed_provider_error,
    validate_model_response_text,
)
from router import LocalRouter
from runtime.outcomes import (
    NZOutcome,
    NZOutcomeStatus,
    NZReasonCode,
    outcome_from_task_state,
    without_outcome_identities,
)
from runtime.safety.atomic_persistence import (
    PersistenceError,
    append_json_line,
    atomic_write_json,
    atomic_write_text,
    state_resource_lock_path,
)
from runtime.sensitive_redaction import (
    SensitiveValueRedactor,
    build_current_runtime_redactor,
)
from runtime.task_checkpoints import (
    ApprovalState,
    DurableTaskCheckpointStore,
    ModelContinuation,
    SafeResumeClassification,
    StepReservation,
    TaskCheckpoint,
    TaskCheckpointError,
    TaskPhase,
    TaskStepReservationError,
    TaskState,
    TERMINAL_TASK_STATES,
    safe_context_metadata,
)
from runtime.task_recovery import (
    MAX_RECOVERY_DISCOVERY_BATCH,
    RecoveryDecision,
    RecoveryDirective,
    RecoveryExecutionToken,
    RecoveryFencedError,
    RecoveryOperationResult,
    RecoveryPurpose,
    TaskRecoveryService,
)
from tools.executor import ExecutionEngine
from tools.provenance import (
    AppendOnlyProvenanceStore,
    RuntimeProvenanceEventType,
    new_runtime_provenance_event,
)
from memory.gemma_worker_memory import GemmaWorkerMemory
from tools.memory_hats import MemoryHatStore
from tools.memory import MemoryStore
from tools.system_info import detect_desktop_dir
from tools.validator import extract_json_object, inspect_respond_shell_safety, validate_action
from trace_context import (
    ActionContext,
    ModelCallContext,
    TraceContext,
    TracedModelOutput,
    strip_untrusted_identity_fields,
)


PROJECT_DIR = Path(__file__).resolve().parent
PROMPT_FILE = PROJECT_DIR / "prompts" / "system_prompt.txt"
MAX_AGENT_STEPS = 8
DEBUG_RAW_RESPONSE = os.getenv("AGENT_DEBUG", "0") == "1"
MODEL_RETRY_DELAYS = (1.0, 2.0, 4.0)
OPERATIONAL_LOG_AUTHORITY = {
    "classification": "operational_event",
    "retention": "replay_only",
    "non_authoritative": True,
    "canonical_evidence": False,
}
EXTERNAL_URL_RE = re.compile(r"\bhttps?://\S+", re.IGNORECASE)
REPOSITORY_HOST_RE = re.compile(r"\b(?:github\.com|gitlab\.com)(?:/|\b)", re.IGNORECASE)
REPOSITORY_INTENT_RE = re.compile(
    r"\b(?:check|analy[sz]e|describe|review|inspect|sprawdz|sprawdź|przeanalizuj|opisz)\b"
    r".*\b(?:github|gitlab|repo|repository|repozytorium|projekt)\b"
    r"|\b(?:github|gitlab|repo|repository|repozytorium|projekt)\b"
    r".*\b(?:check|analy[sz]e|describe|review|inspect|sprawdz|sprawdź|przeanalizuj|opisz)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EpistemicSafeguards:
    kill_switch: bool
    disable_model: bool
    disable_knowledge: bool
    disable_memory_hats: bool
    reasoning_trace_enabled: bool
    prefer_unknown: bool


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_epistemic_safeguards() -> EpistemicSafeguards:
    return EpistemicSafeguards(
        kill_switch=_env_flag("EPISTEMIC_KILL_SWITCH", False),
        disable_model=_env_flag("EPISTEMIC_DISABLE_MODEL", False),
        disable_knowledge=_env_flag("EPISTEMIC_DISABLE_KNOWLEDGE_ROUTE", False),
        disable_memory_hats=_env_flag("EPISTEMIC_DISABLE_MEMORY_HATS", False),
        reasoning_trace_enabled=not _env_flag("EPISTEMIC_DISABLE_REASONING_TRACE", False),
        prefer_unknown=not _env_flag("EPISTEMIC_DISABLE_UNKNOWN_FALLBACK", False),
    )


def load_prompt_template(prompt_path: Path) -> str:
    """Read the editable runtime system prompt from disk."""
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def summarize_text(text: str, limit: int = 4000) -> str:
    """Trim long results before sending them back to the model."""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def extract_first_url(text: str) -> str | None:
    """Extract the first HTTP(S) URL from free-form user text."""
    match = re.search(r"(?:https?|file)://\S+", text)
    if not match:
        return None
    return match.group(0).rstrip(").,!?\"'")


def normalize_external_url(raw_url: str) -> str:
    """Unwrap common redirect wrappers so the browser opens the real target."""
    parsed = urlparse(raw_url)
    host = parsed.netloc.lower()

    if host in {"l.facebook.com", "lm.facebook.com", "www.facebook.com", "facebook.com"}:
        query = parse_qs(parsed.query)
        target = query.get("u", [])
        if target:
            return unquote(target[0])

    return raw_url


def classify_external_review_request(user_input: str) -> str | None:
    """Deterministically keep external links out of local RHCSA retrieval."""
    if REPOSITORY_HOST_RE.search(user_input) or REPOSITORY_INTENT_RE.search(user_input):
        return "external_repository_review"
    if EXTERNAL_URL_RE.search(user_input):
        return "external_link_review"
    return None


def is_quota_exhausted_error(error: Exception) -> bool:
    """Detect provider quota exhaustion to avoid useless retries."""
    if getattr(error, "reason_code", None) == NZReasonCode.MODEL_QUOTA.value:
        return True
    text = str(error)
    return "RESOURCE_EXHAUSTED" in text or "quota exceeded" in text.lower()


def is_daily_quota_error(error: Exception) -> bool:
    """Detect daily free-tier exhaustion where short retries will not help."""
    text = str(error)
    return "PerDay" in text or "free_tier_requests" in text


class AgentRuntime:
    """Main runtime loop coordinating model planning and local execution."""

    def __init__(
        self,
        provider_manager: Any,
        prompt_template: str,
        project_dir: Path,
        debug_raw: bool = False,
        max_steps: int = MAX_AGENT_STEPS,
    ) -> None:
        self.provider_manager = provider_manager
        self.prompt_template = prompt_template
        self.project_dir = project_dir
        self.debug_raw = debug_raw
        self.max_steps = max_steps
        self.safeguards = load_epistemic_safeguards()
        current_redactor = build_current_runtime_redactor()
        manager_redactor = getattr(provider_manager, "output_redactor", None)
        self.redactor = (
            current_redactor.combining(manager_redactor)
            if isinstance(manager_redactor, SensitiveValueRedactor)
            else current_redactor
        )
        self.memory_store = MemoryStore(
            project_dir,
            project_dir,
            initialize_vault=False,
            persist_on_init=False,
            record_session_start=False,
            redactor=self.redactor,
        )
        self.hat_store = MemoryHatStore(project_dir, initialize_defaults=False)
        self.worker_memory = GemmaWorkerMemory(project_dir, redactor=self.redactor)
        self.provenance_store = AppendOnlyProvenanceStore(
            self.memory_store.paths.state_dir,
            lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
        )
        self.task_checkpoint_store = DurableTaskCheckpointStore(
            self.memory_store.paths.state_dir,
            project_dir=project_dir,
            provenance_store=self.provenance_store,
            lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
        )
        self.executor = ExecutionEngine(
            project_dir,
            self.memory_store,
            provenance_store=self.provenance_store,
            task_checkpoint_store=self.task_checkpoint_store,
            redactor=self.redactor,
        )
        self.task_recovery_service = TaskRecoveryService(
            self.memory_store.paths.state_dir,
            project_dir=project_dir,
            checkpoint_store=self.task_checkpoint_store,
            idempotency_store=self.executor.idempotency_store,
            provenance_store=self.provenance_store,
            lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            dispatcher=self,
        )
        self.executor.task_recovery_service = self.task_recovery_service
        self._task_execution_token: ContextVar[
            RecoveryExecutionToken | None
        ] = ContextVar(
            f"aoia_task_execution_token_{id(self)}",
            default=None,
        )
        self._recovery_step_reservation: ContextVar[
            StepReservation | None
        ] = ContextVar(
            f"aoia_recovery_step_reservation_{id(self)}",
            default=None,
        )
        self._recovery_sensitive_persistence: ContextVar[bool] = ContextVar(
            f"aoia_recovery_sensitive_persistence_{id(self)}",
            default=False,
        )
        self._request_outcome_hint: ContextVar[
            tuple[NZOutcomeStatus, str] | None
        ] = ContextVar(
            f"aoia_request_outcome_hint_{id(self)}",
            default=None,
        )
        # Startup recovery discovery is deliberately bounded and read-only.
        # Decisions are exposed to local operator surfaces; startup never
        # reconciles or resumes a task automatically.
        self.recovery_discovery = self.task_recovery_service.discover(
            limit=MAX_RECOVERY_DISCOVERY_BATCH
        )
        self.desktop_dir = detect_desktop_dir(Path.home())
        self.local_router = LocalRouter(self.desktop_dir)
        self.knowledge_router = KnowledgeRouter(project_dir)
        self.aoia_kernel = AOIAEpistemicKernel(project_dir)
        self.command_registry = build_command_registry()
        self.use_orchestrator = False
        self.orchestrator: GeminiGemmaOrchestrator | None = None
        self.session_log = (
            self.memory_store.paths.session_logs_dir
            / f"session_{self.memory_store.memory.session_id}.jsonl"
        )

    @staticmethod
    def _recovery_sensitive_summary(value: object) -> dict[str, object]:
        """Produce bounded, non-reversible metadata for recovery-only logs."""

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
            "recovery_sensitive": True,
            "redacted": True,
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "utf8_length": len(encoded),
        }

    def _recovery_persistence_payload(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not self._recovery_sensitive_persistence.get():
            return self._redact_mapping(payload)
        return self._recovery_sensitive_summary(payload)

    def _sync_sensitive_redactor(self) -> SensitiveValueRedactor:
        current = build_current_runtime_redactor()
        manager = getattr(self.provider_manager, "output_redactor", None)
        redactor = (
            current.combining(manager)
            if isinstance(manager, SensitiveValueRedactor)
            else current
        )
        self.redactor = redactor
        self.memory_store.redactor = redactor
        self.executor.redactor = redactor
        self.worker_memory.redactor = redactor
        if self.orchestrator is not None:
            self.orchestrator.redactor = redactor
        return redactor

    def _redact_mapping(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        redacted = self.redactor.redact(payload)
        if not isinstance(redacted, dict):
            raise TypeError("Runtime output must remain a dictionary")
        return redacted

    def safe_text(self, value: object) -> str:
        return self.redactor.redact_text(value)

    def _recovery_task_marker(self, request_text: str) -> str:
        summary = self._recovery_sensitive_summary(request_text)
        return (
            "RECOVERY_SENSITIVE_REQUEST_REDACTED:"
            f"sha256={summary['sha256']}:utf8_length={summary['utf8_length']}"
        )

    def list_recovery_tasks(
        self,
        *,
        limit: int = MAX_RECOVERY_DISCOVERY_BATCH,
    ) -> tuple[RecoveryDecision, ...]:
        """List bounded, metadata-only recovery decisions for local operators."""

        return self.task_recovery_service.list_incomplete_tasks(limit=limit)

    def show_recovery_task(self, task_id: str) -> RecoveryDecision:
        """Show one metadata-only recovery decision without changing it."""

        return self.task_recovery_service.show(task_id)

    def resume_recovery_task(
        self,
        task_id: str,
        *,
        request_text: str | None = None,
        action: Mapping[str, Any] | None = None,
    ) -> RecoveryOperationResult:
        """Bind exact caller input, then resume through the trusted dispatcher."""

        trusted_input = self.task_recovery_service.bind_trusted_input(
            task_id,
            request_text=request_text,
            action=action,
        )
        return self.task_recovery_service.resume(task_id, trusted_input)

    def request_fresh_recovery_approval(
        self,
        task_id: str,
        *,
        action: Mapping[str, Any],
    ) -> RecoveryOperationResult:
        """Revalidate an exact pending action and invoke the existing approval gate."""

        return self.resume_recovery_task(task_id, action=action)

    def cancel_recovery_task(
        self,
        task_id: str,
    ) -> RecoveryOperationResult:
        """Cancel only work the recovery service proves has not dispatched."""

        return self.task_recovery_service.cancel(task_id)

    def acknowledge_recovery_task(
        self,
        task_id: str,
    ) -> RecoveryOperationResult:
        """Acknowledge manual review without altering canonical task truth."""

        return self.task_recovery_service.acknowledge_manual_review(task_id)

    def render_system_prompt(self) -> str:
        prompt = self.prompt_template
        replacements = {
            "__HOME_DIR__": str(Path.home()),
            "__DESKTOP_DIR__": str(self.desktop_dir),
            "__CURRENT_PROJECT__": str(self.project_dir),
            "__CURRENT_CWD__": self.memory_store.memory.cwd,
        }
        for key, value in replacements.items():
            prompt = prompt.replace(key, value)
        return self.safe_text(prompt)

    def build_model_request(
        self,
        user_input: str,
        request_trace: list[dict[str, Any]],
    ) -> str:
        memory = self.memory_store.memory
        state_payload = {
            "session_id": memory.session_id,
            "cwd": memory.cwd,
            "current_task": memory.current_task,
            "previous_commands": memory.previous_commands[-10:],
            "recent_outputs": memory.recent_outputs[-6:],
            "browser_active": memory.browser_active,
            "current_browser_page": memory.current_browser_page,
            "open_tabs": memory.open_tabs[-10:],
            "screenshots": memory.screenshots[-10:],
            "desktop_dir": str(self.desktop_dir),
            "active_model": self.provider_manager.describe(),
            "fallback_chain": self._provider_fallback_chain(),
            "active_memory_hat": {} if self.safeguards.disable_memory_hats else self.hat_store.prompt_block(),
            "rhcsa_context": inject_linux_context(user_input),
            "obsidian_vault": str(self.memory_store.vault_dir),
            "tools": self.executor.tool_names(),
            "epistemic_safeguards": {
                "kill_switch": self.safeguards.kill_switch,
                "disable_model": self.safeguards.disable_model,
                "disable_knowledge": self.safeguards.disable_knowledge,
                "disable_memory_hats": self.safeguards.disable_memory_hats,
                "prefer_unknown": self.safeguards.prefer_unknown,
            },
            "local_fast_routes": [
                "slash commands",
                "date/status",
                "pwd/ls/curl version",
                "simple desktop folder creation",
                "URL browser bootstrap",
            ],
        }
        request_payload = {
            "user_request": user_input,
            "request_trace": request_trace,
            "instruction": (
                "Return exactly one JSON object and no markdown. "
                "Choose the next proposed action. The runtime independently classifies "
                "the action and requests human ENTER approval when its capability policy "
                "requires it. You may request additional confirmation but cannot remove a "
                "runtime requirement or authorize a blocked action. "
                "Include confidence as high, medium, low, or unknown. "
                'If you do not have enough evidence, respond with "I DO NOT KNOW".'
            ),
        }

        safe_state = self.redactor.redact(state_payload)
        safe_request = self.redactor.redact(request_payload)
        return self.safe_text("\n".join(
            [
                "SYSTEM PROMPT:",
                self.render_system_prompt(),
                "",
                "RUNTIME STATE JSON:",
                json.dumps(safe_state, indent=2, ensure_ascii=False),
                "",
                "REQUEST JSON:",
                json.dumps(safe_request, indent=2, ensure_ascii=False),
            ]
        ))

    def snapshot_status(self) -> dict[str, Any]:
        """Return the current runtime status for CLI and web callers."""
        memory = self.memory_store.memory
        return self._redact_mapping({
            "session_id": memory.session_id,
            "cwd": memory.cwd,
            "current_task": memory.current_task,
            "desktop_dir": str(self.desktop_dir),
            "model": self.provider_manager.describe(),
            "browser_active": memory.browser_active,
            "current_url": memory.current_browser_page,
            "open_tabs": memory.open_tabs[-10:],
            "recent_outputs": memory.recent_outputs[-10:],
            "previous_commands": memory.previous_commands[-10:],
            "session_log": str(self.session_log),
            "vault_dir": str(self.memory_store.vault_dir),
            "tools": self.executor.tool_names(),
            "active_memory_hat": self.hat_store.prompt_block(),
            "fallback_chain": self._provider_fallback_chain(),
            "provider_status": self._provider_status(),
            "orchestrator_enabled": self.use_orchestrator,
            "worker_memory": self.worker_memory.summarize_worker_state(),
            "knowledge_routing": {
                "enabled": not self.safeguards.disable_knowledge,
                "token_savings_report": str(self.knowledge_router.report_path),
                "aoia_kernel": "deterministic_local_epistemic_kernel_v0_1",
            },
            "epistemic_safeguards": {
                "kill_switch": self.safeguards.kill_switch,
                "disable_model": self.safeguards.disable_model,
                "disable_knowledge": self.safeguards.disable_knowledge,
                "disable_memory_hats": self.safeguards.disable_memory_hats,
                "reasoning_trace_enabled": self.safeguards.reasoning_trace_enabled,
                "prefer_unknown": self.safeguards.prefer_unknown,
            },
        })

    def _provider_fallback_chain(self) -> list[str]:
        method = getattr(self.provider_manager, "active_fallback_chain", None)
        if callable(method):
            return method()
        return []

    def _provider_status(self) -> list[dict[str, Any]]:
        method = getattr(self.provider_manager, "provider_status", None)
        if callable(method):
            return method()
        return []

    def _task_step_budget(self) -> int:
        """Bound the whole request, including local bootstrap and planned actions."""

        return max(1, self.max_steps + 8)

    def _task_retry_budget(self) -> int:
        provider_count = max(1, len(self._provider_fallback_chain()))
        return self._task_step_budget() * len(MODEL_RETRY_DELAYS) * provider_count

    def _set_outcome_hint(
        self,
        status: NZOutcomeStatus,
        reason_code: str,
    ) -> None:
        """Retain the strongest process-local degradation for this request."""

        priority = {
            NZOutcomeStatus.SUCCESS: 0,
            NZOutcomeStatus.DEGRADED: 10,
            NZOutcomeStatus.PARTIAL: 20,
            NZOutcomeStatus.MANUAL_REVIEW_REQUIRED: 30,
            NZOutcomeStatus.BLOCKED: 40,
            NZOutcomeStatus.CANCELLED: 50,
            NZOutcomeStatus.FAILED: 60,
            NZOutcomeStatus.TIMEOUT: 70,
            NZOutcomeStatus.CONFLICT: 80,
            NZOutcomeStatus.UNKNOWN_OUTCOME: 90,
        }
        current = self._request_outcome_hint.get()
        if current is None or priority[status] >= priority[current[0]]:
            self._request_outcome_hint.set((status, reason_code))

    def _note_result_outcome(self, result: Mapping[str, Any]) -> None:
        raw_outcome = result.get("outcome")
        if not isinstance(raw_outcome, Mapping):
            return
        try:
            projected = NZOutcome.from_dict(raw_outcome)
        except (TypeError, ValueError):
            return
        if projected.status is NZOutcomeStatus.SUCCESS:
            return
        reason_code = projected.reason_code or NZReasonCode.ACTION_FAILED.value
        self._set_outcome_hint(projected.status, reason_code)

    def _outcome_for_checkpoint(
        self,
        checkpoint: TaskCheckpoint,
        trace_context: TraceContext,
    ) -> NZOutcome:
        reason: str | None = None
        if checkpoint.state is TaskState.BLOCKED:
            reason = (
                checkpoint.current_policy_reason_code
                or NZReasonCode.TASK_BLOCKED.value
            )
        elif checkpoint.state is TaskState.CANCELLED:
            reason = (
                NZReasonCode.HUMAN_APPROVAL_DECLINED.value
                if checkpoint.approval_state is ApprovalState.DENIED
                else NZReasonCode.TASK_CANCELLED.value
            )
        base = outcome_from_task_state(
            checkpoint.state.value,
            reason_code=reason,
            request_id=trace_context.request_id,
            trace_id=trace_context.trace_id,
            task_id=trace_context.task_id,
        )
        hint = self._request_outcome_hint.get()
        if hint is None:
            return base
        hint_status, hint_reason = hint
        # Durable non-success truth normally dominates process-local hints.  A
        # fresh, observed hard timeout remains TIMEOUT even though P0.7 keeps the
        # underlying effect record conservative for restart reconciliation.
        if base.status is NZOutcomeStatus.UNKNOWN_OUTCOME:
            if hint_status is not NZOutcomeStatus.TIMEOUT:
                return base
        elif (
            base.status is NZOutcomeStatus.FAILED
            and hint_status is NZOutcomeStatus.DEGRADED
            and hint_reason == NZReasonCode.BROWSER_FALLBACK_UNVERIFIED.value
        ):
            # The legacy fallback explicitly performed no verified browser
            # interaction.  Its legacy ``success=False`` is not an independent
            # execution failure and must project as DEGRADED, never SUCCESS.
            pass
        elif base.status is not NZOutcomeStatus.SUCCESS:
            if base.status is not hint_status:
                return base
        return NZOutcome.build(
            hint_status,
            hint_reason,
            request_id=trace_context.request_id,
            trace_id=trace_context.trace_id,
            task_id=trace_context.task_id,
            degraded=hint_status is NZOutcomeStatus.DEGRADED,
        )

    def _validate_task_execution_token(
        self,
        task_id: str,
        token: RecoveryExecutionToken | None = None,
    ) -> RecoveryExecutionToken:
        active = token if token is not None else self._task_execution_token.get()
        if active is None or active.task_id != task_id:
            raise RecoveryFencedError(
                "A matching live task execution token is required."
            )
        # Temporary strict adapter until the recovery service exposes a lighter
        # public token-validation method.
        self.task_recovery_service.classify_under_claim(task_id, active)
        return active

    def _current_task_execution_token(
        self,
        task_id: str,
    ) -> RecoveryExecutionToken | None:
        token = self._task_execution_token.get()
        if token is None:
            return None
        return self._validate_task_execution_token(task_id, token)

    def _validate_recovery_dispatch_identity(
        self,
        trace_context: TraceContext,
        recovery_token: RecoveryExecutionToken,
    ) -> None:
        if (
            trace_context.task_id != recovery_token.task_id
            or trace_context.request_id != recovery_token.request_id
            or trace_context.trace_id != recovery_token.trace_id
        ):
            raise RecoveryFencedError(
                "Recovery dispatch trace does not match its execution token."
            )
        self._validate_task_execution_token(
            trace_context.task_id,
            recovery_token,
        )

    @contextmanager
    def _recovery_dispatch_scope(
        self,
        trace_context: TraceContext,
        recovery_token: RecoveryExecutionToken,
        *,
        allowed_directives: frozenset[RecoveryDirective],
        step_reservation: StepReservation | None = None,
    ) -> Iterator[None]:
        self._validate_recovery_dispatch_identity(
            trace_context,
            recovery_token,
        )
        self.task_recovery_service.validate_dispatch_authorization(
            recovery_token,
            allowed_directives,
        )
        current = self._task_execution_token.get()
        if current is not None and current is not recovery_token:
            raise RecoveryFencedError(
                "Another task execution token is already bound to this context."
            )
        token_binding = self._task_execution_token.set(recovery_token)
        reservation_binding = self._recovery_step_reservation.set(
            step_reservation
        )
        sensitive_binding = self._recovery_sensitive_persistence.set(True)
        try:
            with self.executor.recovery_sensitive_persistence():
                yield
        finally:
            if step_reservation is not None:
                self._close_task_step(step_reservation)
            self._recovery_sensitive_persistence.reset(sensitive_binding)
            self._recovery_step_reservation.reset(reservation_binding)
            self._task_execution_token.reset(token_binding)

    @contextmanager
    def _live_task_execution_guard(
        self,
        trace_context: TraceContext,
        request_text: str = "",
    ) -> Iterator[RecoveryExecutionToken]:
        nested = self._task_execution_token.get()
        if nested is not None:
            yield self._validate_task_execution_token(
                trace_context.task_id,
                nested,
            )
            return
        checkpoint = self._ensure_task_checkpoint(trace_context, request_text)
        with self.task_recovery_service.execution_guard(
            trace_context.task_id,
            purpose=RecoveryPurpose.LIVE,
            expected_checkpoint_hash=checkpoint.checkpoint_hash,
        ) as token:
            reset_token = self._task_execution_token.set(token)
            try:
                yield token
            finally:
                self._task_execution_token.reset(reset_token)

    def _ensure_task_checkpoint(
        self,
        trace_context: TraceContext,
        request_text: str = "",
    ) -> TaskCheckpoint:
        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is not None:
            return checkpoint
        return self.task_checkpoint_store.create_task(
            trace_context,
            max_steps=self._task_step_budget(),
            retry_budget=self._task_retry_budget(),
            safe_context=safe_context_metadata(request_text),
        )

    def _reserve_task_step(
        self,
        trace_context: TraceContext,
        request_text: str = "",
    ) -> StepReservation:
        recovery_reservation = self._recovery_step_reservation.get()
        if recovery_reservation is not None:
            self.task_checkpoint_store.validate_step_reservation(
                recovery_reservation,
                task_id=trace_context.task_id,
            )
            self._recovery_step_reservation.set(None)
            return recovery_reservation
        self._ensure_task_checkpoint(trace_context, request_text)
        return self.task_checkpoint_store.reserve_step(trace_context.task_id)

    def _start_task(
        self,
        trace_context: TraceContext,
        request_text: str = "",
    ) -> TaskCheckpoint:
        checkpoint = self._ensure_task_checkpoint(trace_context, request_text)
        if checkpoint.state is not TaskState.CREATED:
            return checkpoint
        return self.task_checkpoint_store.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_STARTED",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
            safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
        )

    def _close_task_step(self, reservation: StepReservation) -> None:
        """Release only the in-process capability; durable budget stays consumed."""

        try:
            self.task_checkpoint_store.close_step_reservation(reservation)
        except TaskStepReservationError:
            # The executor consumes a successful action token. Cleanup callers
            # may therefore observe that the capability is already gone.
            return

    def _finish_task(
        self,
        trace_context: TraceContext,
        state: TaskState,
    ) -> TaskCheckpoint:
        checkpoint = self._ensure_task_checkpoint(trace_context)
        if checkpoint.state in TERMINAL_TASK_STATES:
            return checkpoint
        # Unknown action outcome is durable truth and must never be flattened
        # into a normal request completion or a retryable failure.
        if checkpoint.state is TaskState.RECOVERY_REQUIRED:
            return checkpoint
        reasons = {
            TaskState.COMPLETED: "TASK_COMPLETED",
            TaskState.PARTIAL: "TASK_PARTIAL",
            TaskState.BLOCKED: "TASK_BLOCKED",
            TaskState.CANCELLED: "TASK_CANCELLED",
            TaskState.FAILED: "TASK_FAILED",
        }
        try:
            reason_code = reasons[state]
        except KeyError as exc:
            raise ValueError("Unsupported terminal task state.") from exc
        return self.task_checkpoint_store.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=state,
            phase=TaskPhase.TERMINAL,
            reason_code=reason_code,
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            approval_state=(
                ApprovalState.DENIED
                if state is TaskState.CANCELLED
                else ApprovalState.NOT_APPLICABLE
            ),
        )

    def _mark_task_between_steps(
        self,
        trace_context: TraceContext,
    ) -> TaskCheckpoint:
        checkpoint = self._ensure_task_checkpoint(trace_context)
        if checkpoint.state in TERMINAL_TASK_STATES or checkpoint.state is TaskState.RECOVERY_REQUIRED:
            return checkpoint
        if checkpoint.phase is TaskPhase.BETWEEN_STEPS:
            return checkpoint
        if checkpoint.phase is not TaskPhase.AFTER_ACTION:
            raise TaskCheckpointError(
                "Task cannot advance between steps from its current durable phase."
            )
        return self.task_checkpoint_store.transition(
            checkpoint.task_id,
            expected_version=checkpoint.checkpoint_version,
            state=TaskState.RUNNING,
            phase=TaskPhase.BETWEEN_STEPS,
            reason_code="TASK_BETWEEN_STEPS",
            latest_request_id=trace_context.request_id,
            latest_trace_id=trace_context.trace_id,
            approval_state=ApprovalState.NOT_APPLICABLE,
            safe_resume_classification=SafeResumeClassification.SAFE_TO_RESUME,
        )

    def ask_model(
        self,
        prompt: str,
        trace_context: TraceContext,
        *,
        step_reservation: StepReservation | None = None,
        model_continuation: ModelContinuation | None = None,
        recovery_token: RecoveryExecutionToken | None = None,
    ) -> TracedModelOutput:
        """Request model output while identifying every actual provider attempt."""
        active_token = recovery_token or self._task_execution_token.get()
        if active_token is None:
            # Preserve direct-call compatibility while keeping the provider
            # attempt inside a live execution claim.
            with self._live_task_execution_guard(trace_context, prompt) as token:
                return self.ask_model(
                    prompt,
                    trace_context,
                    step_reservation=step_reservation,
                    model_continuation=model_continuation,
                    recovery_token=token,
                )
        recovery_token = self._validate_task_execution_token(
            trace_context.task_id,
            active_token,
        )
        if self.safeguards.disable_model:
            raise RuntimeError("Model planning is disabled by EPISTEMIC_DISABLE_MODEL.")
        owns_step_reservation = step_reservation is None
        if step_reservation is None:
            step_reservation = self._reserve_task_step(trace_context, prompt)
        pending_continuation = model_continuation
        provider_prompt = self._sync_sensitive_redactor().redact_text(prompt)

        def log_attempt(
            status: str,
            model_call: ModelCallContext,
            provider: str,
            model: str,
            retry_attempt: int,
            provider_attempt: int,
        ) -> None:
            nonlocal pending_continuation
            continuation = pending_continuation if status == "started" else None
            self._log_model_attempt(
                status=status,
                model_call=model_call,
                provider=provider,
                model=model,
                retry_attempt=retry_attempt,
                provider_attempt=provider_attempt,
                step_reservation=step_reservation,
                model_continuation=continuation,
                recovery_token=recovery_token,
            )
            # A continuation is an unforgeable one-shot capability.  Later
            # provider retries remain part of this step, but start from the
            # durable BEFORE_MODEL_CALL phase and must not reuse the proof.
            if status == "started":
                pending_continuation = None

        last_error: Exception | None = None
        for retry_attempt, delay_seconds in enumerate(MODEL_RETRY_DELAYS, start=1):
            try:
                traced_generate = getattr(self.provider_manager, "generate_traced", None)
                if callable(traced_generate):
                    raw_result = traced_generate(
                        provider_prompt,
                        trace_context,
                        on_attempt=lambda status, call, provider, model, provider_attempt: log_attempt(
                            status,
                            call,
                            provider,
                            model,
                            retry_attempt,
                            provider_attempt,
                        ),
                    )
                else:
                    model_call = trace_context.new_model_call()
                    model_name = str(self.provider_manager.describe())
                    provider_name = model_name.split("/", 1)[0]
                    log_attempt(
                        "started",
                        model_call,
                        provider_name,
                        model_name,
                        retry_attempt,
                        1,
                    )
                    try:
                        raw_text = validate_model_response_text(
                            self.provider_manager.generate(provider_prompt)
                        )
                    except Exception:
                        log_attempt(
                            "failed",
                            model_call,
                            provider_name,
                            model_name,
                            retry_attempt,
                            1,
                        )
                        raise
                    log_attempt(
                        "succeeded",
                        model_call,
                        provider_name,
                        model_name,
                        retry_attempt,
                        1,
                    )
                    raw_result = TracedModelOutput(
                        text=raw_text,
                        model_call=model_call,
                        provider=provider_name,
                        model=model_name,
                    )
                if not isinstance(raw_result, TracedModelOutput):
                    raise ModelResponseMalformedError(
                        "Provider manager returned an invalid traced response."
                    )
                if not isinstance(raw_result.model_call, ModelCallContext):
                    raise ModelResponseMalformedError(
                        "Provider response lacked a valid model-call identity."
                    )
                if (
                    raw_result.model_call.request_id != trace_context.request_id
                    or raw_result.model_call.trace_id != trace_context.trace_id
                    or raw_result.model_call.task_id != trace_context.task_id
                ):
                    raise ModelResponseMalformedError(
                        "Provider response identity did not match the active request."
                    )
                validate_model_response_text(raw_result.text)
                redactor = self._sync_sensitive_redactor()
                raw_result = TracedModelOutput(
                    text=redactor.redact_text(raw_result.text),
                    model_call=raw_result.model_call,
                    provider=redactor.redact_text(raw_result.provider),
                    model=redactor.redact_text(raw_result.model),
                )
                if self.debug_raw and not self._recovery_sensitive_persistence.get():
                    print("\n[DEBUG] RAW MODEL OUTPUT:")
                    print(self.safe_text(raw_result.text))
                if owns_step_reservation:
                    self._close_task_step(step_reservation)
                    self._finish_task(trace_context, TaskState.COMPLETED)
                return raw_result
            except PersistenceError as persistence_error:
                if pending_continuation is not None:
                    try:
                        self.task_checkpoint_store.close_model_continuation(
                            pending_continuation
                        )
                        pending_continuation = None
                    except Exception as close_error:
                        try:
                            persistence_error.add_note(
                                "Unused model-continuation cleanup failed; "
                                f"secondary failure type: {type(close_error).__name__}."
                            )
                        except AttributeError:  # pragma: no cover
                            pass
                raise
            except Exception as error:
                self._sync_sensitive_redactor()
                last_error = error
                if is_daily_quota_error(error):
                    break
                if retry_attempt == len(MODEL_RETRY_DELAYS):
                    break
                print(
                    self.safe_text(
                        f"\n[WARN] Model request failed (attempt {retry_attempt}/{len(MODEL_RETRY_DELAYS)}): {error}"
                    )
                )
                print(f"[WARN] Retrying in {delay_seconds:.0f}s...")
                time.sleep(delay_seconds)

        assert last_error is not None
        if pending_continuation is not None:
            try:
                self.task_checkpoint_store.close_model_continuation(
                    pending_continuation
                )
                pending_continuation = None
            except Exception as close_error:
                try:
                    last_error.add_note(
                        "Unused model-continuation cleanup failed; "
                        f"secondary failure type: {type(close_error).__name__}."
                    )
                except AttributeError:  # pragma: no cover
                    pass
        if owns_step_reservation:
            self._close_task_step(step_reservation)
            self._finish_task(trace_context, TaskState.FAILED)
        if isinstance(last_error, PersistenceError):
            raise last_error
        terminal_error = typed_provider_error(last_error)
        terminal_error.args = ("Model request failed after retries.",)
        raise terminal_error from last_error

    def _log_model_attempt(
        self,
        *,
        status: str,
        model_call: ModelCallContext,
        provider: str,
        model: str,
        retry_attempt: int,
        provider_attempt: int,
        step_reservation: StepReservation,
        model_continuation: ModelContinuation | None = None,
        recovery_token: RecoveryExecutionToken | None = None,
    ) -> None:
        if status == "started":
            self._validate_task_execution_token(
                model_call.task_id,
                recovery_token,
            )
        event_types = {
            "started": RuntimeProvenanceEventType.MODEL_CALL_STARTED,
            "succeeded": RuntimeProvenanceEventType.MODEL_CALL_COMPLETED,
            "failed": RuntimeProvenanceEventType.MODEL_CALL_FAILED,
        }
        event_type = event_types.get(status)
        if event_type is None:
            raise ValueError("Unsupported runtime model-call lifecycle status.")
        if status == "started":
            self.task_checkpoint_store.consume_provider_attempt(
                model_call,
                step_reservation=step_reservation,
                model_continuation=model_continuation,
            )
        event = new_runtime_provenance_event(
            event_type,
            model_call=model_call,
            requested_provider=provider,
            requested_model=model,
            retry_attempt=retry_attempt,
            provider_attempt=provider_attempt,
            success=(
                None
                if status == "started"
                else status == "succeeded"
            ),
            reason_code=event_type.value,
        )
        if status == "started":
            self.provenance_store.append_runtime_event(event)
        else:
            self.provenance_store.append_terminal(event)
            checkpoint = self.task_checkpoint_store.load(model_call.task_id)
            if checkpoint is None:
                raise TaskCheckpointError(
                    "Model-call lifecycle has no durable task checkpoint."
                )
            self.task_checkpoint_store.transition(
                checkpoint.task_id,
                expected_version=checkpoint.checkpoint_version,
                state=TaskState.RUNNING,
                phase=(
                    TaskPhase.AFTER_MODEL_CALL
                    if status == "succeeded"
                    else TaskPhase.BEFORE_MODEL_CALL
                ),
                reason_code=(
                    "TASK_MODEL_CALL_COMPLETED"
                    if status == "succeeded"
                    else "TASK_MODEL_CALL_FAILED"
                ),
                latest_request_id=model_call.request_id,
                latest_trace_id=model_call.trace_id,
                current_model_call_id=model_call.model_call_id,
                approval_state=ApprovalState.NOT_APPLICABLE,
            )
        self.log_session_event(
            "model_call_attempt",
            {
                "provider": provider,
                "model": model,
                "retry_attempt": retry_attempt,
                "provider_attempt": provider_attempt,
                "status": status,
            },
            trace_context=TraceContext(
                request_id=model_call.request_id,
                trace_id=model_call.trace_id,
                task_id=model_call.task_id,
            ),
            model_call=model_call,
        )

    def handle_user_request(
        self,
        user_input: str,
        trace_context: TraceContext | None = None,
        *,
        resume_before_model_call: bool = False,
    ) -> None:
        """Run the bounded action loop for one user request."""
        trace_context = trace_context or TraceContext.new_request()
        self._start_task(trace_context, user_input)
        self.memory_store.set_current_task(
            self._recovery_task_marker(user_input)
            if self._recovery_sensitive_persistence.get()
            else user_input
        )
        if (
            not resume_before_model_call
            and user_input.strip().lower() in {"help", "?"}
        ):
            result = self.command_registry.execute("/help", self, trace_context)
            if result.handled and result.message:
                print(self.safe_text(f"\nAgent> {result.message}"))
            self._finish_task(trace_context, TaskState.COMPLETED)
            return
        if self.safeguards.kill_switch:
            self.emit_epistemic_unknown(
                "Epistemic kill switch is enabled.",
                trace_context,
            )
            self._finish_task(trace_context, TaskState.COMPLETED)
            return

        if (
            not resume_before_model_call
            and self.handle_external_review_route(user_input, trace_context)
        ):
            self._finish_task(trace_context, TaskState.COMPLETED)
            return

        if (
            not resume_before_model_call
            and self.handle_local_route(user_input, trace_context)
        ):
            self._finish_task(trace_context, TaskState.COMPLETED)
            return

        if (
            not resume_before_model_call
            and self.handle_knowledge_route(user_input, trace_context)
        ):
            self._finish_task(trace_context, TaskState.COMPLETED)
            return

        if self.use_orchestrator:
            self.handle_orchestrated_request(user_input, trace_context)
            return

        request_trace = (
            []
            if resume_before_model_call
            else self.bootstrap_local_context(user_input, trace_context)
        )
        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is None:
            raise TaskCheckpointError("Request lost its task checkpoint.")
        if checkpoint.state in TERMINAL_TASK_STATES or checkpoint.state is TaskState.RECOVERY_REQUIRED:
            return
        planner_reservation = self._reserve_task_step(trace_context, user_input)
        planned_actions, planner_call = self.create_plan(
            user_input,
            request_trace,
            trace_context,
            step_reservation=planner_reservation,
        )
        if planned_actions:
            self.execute_planned_actions(
                planned_actions,
                request_trace,
                trace_context,
                planner_call,
                first_step_reservation=planner_reservation,
            )
            return
        self._run_reactive_fallback(
            user_input,
            request_trace,
            trace_context,
            initial_step_reservation=planner_reservation,
            planner_call=planner_call,
        )

    def _run_reactive_fallback(
        self,
        user_input: str,
        request_trace: list[dict[str, Any]],
        trace_context: TraceContext,
        *,
        initial_step_reservation: StepReservation,
        planner_call: ModelCallContext | None,
    ) -> None:
        """Preserve the bounded reactive route with durable step capabilities."""

        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is None:
            raise TaskCheckpointError("Reactive fallback lost its task checkpoint.")
        initial_continuation: ModelContinuation | None = None
        if checkpoint.phase is TaskPhase.AFTER_MODEL_CALL:
            if planner_call is None:
                self._close_task_step(initial_step_reservation)
                raise TaskCheckpointError(
                    "Reactive fallback lacks the completed planner identity."
                )
            initial_continuation = (
                self.task_checkpoint_store.authorize_model_continuation(
                    initial_step_reservation,
                    completed_model_call=planner_call,
                )
            )
        elif checkpoint.phase is not TaskPhase.BEFORE_MODEL_CALL:
            self._close_task_step(initial_step_reservation)
            raise TaskCheckpointError(
                "Reactive fallback cannot start from its durable task phase."
            )

        for step in range(1, self.max_steps + 1):
            step_reservation = (
                initial_step_reservation
                if step == 1
                else self._reserve_task_step(trace_context)
            )
            continuation = initial_continuation if step == 1 else None
            prompt = self.build_model_request(user_input, request_trace)
            self.log_reasoning_trace(
                "model_request",
                {
                    "step": step,
                    "user_request": user_input,
                    "prompt_preview": summarize_text(prompt, 1200),
                },
                trace_context=trace_context,
            )
            try:
                model_output = self.ask_model(
                    prompt,
                    trace_context,
                    step_reservation=step_reservation,
                    model_continuation=continuation,
                )
                raw_output = model_output.text
            except PersistenceError:
                raise
            except Exception as error:
                self._close_task_step(step_reservation)
                self._set_outcome_hint(
                    NZOutcomeStatus.PARTIAL if request_trace else NZOutcomeStatus.FAILED,
                    provider_reason_code(error),
                )
                self.log_error(
                    {
                        "step": step,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                        "prompt_preview": summarize_text(prompt, 1200),
                    },
                    trace_context=trace_context,
                )
                self.handle_model_unavailable(request_trace, error)
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace else TaskState.FAILED,
                )
                return

            self.log_session_event(
                "model_output",
                {
                    "step": step,
                    "prompt_preview": summarize_text(prompt, 1200),
                    "raw_output": raw_output,
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
            )

            try:
                action = strip_untrusted_identity_fields(
                    validate_action(extract_json_object(raw_output))
                )
            except PersistenceError:
                raise
            except Exception as error:
                self._close_task_step(step_reservation)
                self._set_outcome_hint(
                    NZOutcomeStatus.PARTIAL if request_trace else NZOutcomeStatus.FAILED,
                    NZReasonCode.MODEL_RESPONSE_MALFORMED.value,
                )
                self.log_error(
                    {
                        "step": step,
                        "raw_output": raw_output,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    },
                    trace_context=trace_context,
                    model_call=model_output.model_call,
                )
                print("\n[ERROR] Invalid action JSON from model.")
                print(self.safe_text(error))
                if self.safeguards.prefer_unknown:
                    self.emit_epistemic_unknown(
                        "The model returned invalid structured output.",
                        trace_context,
                        model_output.model_call,
                    )
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace else TaskState.FAILED,
                )
                return

            self.print_action(action, step)
            action_context = trace_context.new_action(model_output.model_call)
            try:
                result = self.executor.execute(
                    action,
                    action_context=action_context,
                    step_reservation=step_reservation,
                    recovery_token=self._current_task_execution_token(
                        trace_context.task_id
                    ),
                )
            except PersistenceError:
                raise
            except Exception as error:
                self._close_task_step(step_reservation)
                self.log_error(
                    {
                        "step": step,
                        "action": action,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    },
                    trace_context=trace_context,
                    model_call=model_output.model_call,
                    action_context=action_context,
                )
                print("\n[ERROR] Action execution failed.")
                print(self.safe_text(error))
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace else TaskState.FAILED,
                )
                return

            self.print_result(result)
            self.log_session_event(
                "step_result",
                {
                    "step": step,
                    "action": action,
                    "result": self.result_for_model(result),
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
                action_context=action_context,
            )

            checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
            if checkpoint is None:
                raise TaskCheckpointError(
                    "Reactive action lost its task checkpoint."
                )
            if (
                checkpoint.state in TERMINAL_TASK_STATES
                or checkpoint.state is TaskState.RECOVERY_REQUIRED
            ):
                return
            request_trace.append(
                {
                    "step": step,
                    "action": action,
                    "result": self.result_for_model(result),
                }
            )
            if not result.get("success"):
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace[:-1] else TaskState.FAILED,
                )
                return
            if action["action"] == "respond" or result.get("stop_loop"):
                self._finish_task(trace_context, TaskState.COMPLETED)
                return
            if result.get("cancelled"):
                self._finish_task(trace_context, TaskState.CANCELLED)
                return
            self._mark_task_between_steps(trace_context)

        print("\nAgent> Agent stopped after reaching the maximum step limit.")
        self._set_outcome_hint(
            NZOutcomeStatus.PARTIAL,
            NZReasonCode.STEP_BUDGET_EXHAUSTED.value,
        )
        self._finish_task(trace_context, TaskState.PARTIAL)

    def handle_external_review_route(
        self,
        user_input: str,
        trace_context: TraceContext,
    ) -> bool:
        """Keep external URLs and repository requests out of RHCSA retrieval."""
        route = classify_external_review_request(user_input)
        if route is None:
            return False

        raw_url = extract_first_url(user_input)
        if raw_url:
            normalized_url = normalize_external_url(raw_url)
            open_result: dict[str, Any] | None = None
            try:
                open_context = trace_context.new_action()
                open_result = self.executor.execute(
                    {"action": "browser_open", "url": normalized_url},
                    require_approval=True,
                    action_context=open_context,
                    step_reservation=self._reserve_task_step(trace_context),
                    recovery_token=self._current_task_execution_token(
                        trace_context.task_id
                    ),
                )
                self.print_result(open_result)
                visible_context: ActionContext | None = None
                if open_result.get("success"):
                    self._mark_task_between_steps(trace_context)
                    visible_context = trace_context.new_action()
                    visible_text = self.executor.execute(
                        {"action": "browser_get_visible_text"},
                        require_approval=True,
                        action_context=visible_context,
                        step_reservation=self._reserve_task_step(trace_context),
                        recovery_token=self._current_task_execution_token(
                            trace_context.task_id
                        ),
                    )
                    self.print_result(visible_text)
                    if not visible_text.get("success"):
                        self._finish_task(trace_context, TaskState.PARTIAL)
                else:
                    self._finish_task(trace_context, TaskState.FAILED)
                self.log_session_event(
                    route,
                    {
                        "user_request": user_input,
                        "routing_boundary": "no_rhcsa_local_knowledge",
                        "browser_handled": True,
                        "opened_url": normalized_url,
                        "action_ids": [
                            context.action_id
                            for context in (open_context, visible_context)
                            if context is not None
                        ],
                    },
                    trace_context=trace_context,
                )
                return True
            except PersistenceError:
                raise
            except Exception as error:
                self.log_error(
                    {
                        "user_request": user_input,
                        "route": route,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    },
                    trace_context=trace_context,
                )
                self.log_session_event(
                    route,
                    {
                        "user_request": user_input,
                        "routing_boundary": "no_rhcsa_local_knowledge",
                        "browser_handled": False,
                        "opened_url": normalized_url,
                        "error": str(error),
                    },
                    trace_context=trace_context,
                )
                print("\nAgent> External URL detected. Browser inspection path available but browser handoff failed.")
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL
                    if open_result and open_result.get("success")
                    else TaskState.FAILED,
                )
                return True

        message = (
            "External repository inspection path detected. Browser inspection path available."
            if route == "external_repository_review"
            else "External URL detected. Browser inspection path available."
        )
        self.log_session_event(
            route,
            {
                "user_request": user_input,
                "routing_boundary": "no_rhcsa_local_knowledge",
                "browser_handled": False,
            },
            trace_context=trace_context,
        )
        print(self.safe_text(f"\nAgent> {message}"))
        return True

    def enable_orchestrator(self, enabled: bool = True) -> None:
        self.use_orchestrator = enabled
        if enabled and self.orchestrator is None:
            self.orchestrator = GeminiGemmaOrchestrator(
                provider_manager=self.provider_manager,
                worker_memory=self.worker_memory,
                hat_store=self.hat_store,
                project_dir=self.project_dir,
                desktop_dir=self.desktop_dir,
                max_steps=self.max_steps,
                redactor=self._sync_sensitive_redactor(),
            )

    def handle_orchestrated_request(
        self,
        user_input: str,
        trace_context: TraceContext,
    ) -> None:
        """Run Gemini brain -> Gemma worker -> approval -> executor flow."""
        self.enable_orchestrator(True)
        assert self.orchestrator is not None
        planner_reservation = self._reserve_task_step(trace_context, user_input)
        try:
            plan, planner_call = self.orchestrator.create_traced_plan(
                user_input,
                self.snapshot_status(),
                trace_context,
                on_attempt=lambda status, call, provider, model, provider_attempt: self._log_model_attempt(
                    status=status,
                    model_call=call,
                    provider=provider,
                    model=model,
                    retry_attempt=1,
                    provider_attempt=provider_attempt,
                    step_reservation=planner_reservation,
                ),
            )
        except PersistenceError:
            self._close_task_step(planner_reservation)
            raise
        except Exception as error:
            self._close_task_step(planner_reservation)
            self._set_outcome_hint(
                NZOutcomeStatus.FAILED,
                provider_reason_code(error),
            )
            self.log_error(
                {
                    "kind": "orchestrator_planner_error",
                    **self.orchestrator.error_payload(error),
                },
                trace_context=trace_context,
            )
            print("\n[ERROR] Gemini planner failed.")
            print(self.safe_text(error))
            self._finish_task(trace_context, TaskState.FAILED)
            return

        strategy = plan.get("strategy", "")
        steps = plan.get("steps", [])
        print("\n[GEMINI PLAN]")
        if strategy:
            print(self.safe_text(strategy))
        for index, step in enumerate(steps, start=1):
            print(self.safe_text(f"{index}. {step}"))
        self.log_session_event(
            "orchestrator_plan",
            {
                "strategy": strategy,
                "step_count": len(steps),
            },
            trace_context=trace_context,
            model_call=planner_call,
        )
        if not steps:
            self._close_task_step(planner_reservation)
            self._finish_task(trace_context, TaskState.COMPLETED)
            return
        model_continuation = self.task_checkpoint_store.authorize_model_continuation(
            planner_reservation,
            completed_model_call=planner_call,
        )
        previous_results: list[dict[str, Any]] = []
        for index, step in enumerate(steps[: self.max_steps], start=1):
            step_reservation = (
                planner_reservation
                if index == 1
                else self._reserve_task_step(trace_context)
            )
            pending_continuation = model_continuation if index == 1 else None

            def worker_attempt_observer(
                status: str,
                call: ModelCallContext,
                provider: str,
                model: str,
                provider_attempt: int,
            ) -> None:
                nonlocal pending_continuation
                continuation = (
                    pending_continuation if status == "started" else None
                )
                self._log_model_attempt(
                    status=status,
                    model_call=call,
                    provider=provider,
                    model=model,
                    retry_attempt=1,
                    provider_attempt=provider_attempt,
                    step_reservation=step_reservation,
                    model_continuation=continuation,
                )
                if status == "started":
                    pending_continuation = None

            def close_unused_worker_continuation(error: Exception) -> None:
                nonlocal pending_continuation
                if pending_continuation is None:
                    return
                try:
                    self.task_checkpoint_store.close_model_continuation(
                        pending_continuation
                    )
                    pending_continuation = None
                except Exception as close_error:
                    try:
                        error.add_note(
                            "Unused worker-continuation cleanup failed; "
                            f"secondary failure type: {type(close_error).__name__}."
                        )
                    except AttributeError:  # pragma: no cover
                        pass

            try:
                action, worker_call = self.orchestrator.action_for_step_traced(
                    user_request=user_input,
                    step=step,
                    runtime_status=self.snapshot_status(),
                    previous_results=previous_results,
                    trace_context=trace_context,
                    on_attempt=worker_attempt_observer,
                )
                if pending_continuation is not None:
                    missing_attempt = TaskCheckpointError(
                        "Worker returned without a durable provider attempt."
                    )
                    close_unused_worker_continuation(missing_attempt)
                    raise missing_attempt
                action = strip_untrusted_identity_fields(action)
            except PersistenceError as persistence_error:
                close_unused_worker_continuation(persistence_error)
                self._close_task_step(step_reservation)
                raise
            except Exception as error:
                close_unused_worker_continuation(error)
                self._close_task_step(step_reservation)
                self._set_outcome_hint(
                    NZOutcomeStatus.PARTIAL if previous_results else NZOutcomeStatus.FAILED,
                    provider_reason_code(error),
                )
                self.log_error(
                    {
                        "kind": "gemma_worker_error",
                        "step": step,
                        **self.orchestrator.error_payload(error),
                    },
                    trace_context=trace_context,
                )
                print("\n[ERROR] Gemma worker failed to produce a valid action.")
                print(self.safe_text(error))
                print("Agent> Worker model is not available or did not return valid JSON. Use /worker status and /setup.")
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if previous_results else TaskState.FAILED,
                )
                return

            self.print_action(action, index)
            action_context = trace_context.new_action(worker_call)
            try:
                result = self.executor.execute(
                    action,
                    action_context=action_context,
                    step_reservation=step_reservation,
                    recovery_token=self._current_task_execution_token(
                        trace_context.task_id
                    ),
                )
            except PersistenceError:
                raise
            except Exception as error:
                self._close_task_step(step_reservation)
                self._set_outcome_hint(
                    NZOutcomeStatus.PARTIAL if previous_results else NZOutcomeStatus.FAILED,
                    NZReasonCode.ACTION_FAILED.value,
                )
                self.log_error(
                    {
                        "kind": "orchestrated_execution_error",
                        "step": step,
                        "action": action,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    },
                    trace_context=trace_context,
                    model_call=worker_call,
                    action_context=action_context,
                )
                print("\n[ERROR] Orchestrated action execution failed.")
                print(self.safe_text(error))
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if previous_results else TaskState.FAILED,
                )
                return

            self.print_result(result)
            self.orchestrator.record_result(step, action, result)
            previous_results.append(
                {
                    "step": step,
                    "action": action,
                    "result": self.result_for_model(result),
                }
            )
            self.log_session_event(
                "orchestrated_step_result",
                previous_results[-1],
                trace_context=trace_context,
                model_call=worker_call,
                action_context=action_context,
            )
            checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
            if checkpoint is None:
                raise TaskCheckpointError(
                    "Orchestrated action lost its task checkpoint."
                )
            if checkpoint.state in TERMINAL_TASK_STATES or checkpoint.state is TaskState.RECOVERY_REQUIRED:
                return
            if not result.get("success"):
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if previous_results[:-1] else TaskState.FAILED,
                )
                return
            if action["action"] == "respond" or result.get("stop_loop"):
                self._finish_task(trace_context, TaskState.COMPLETED)
                return
            self._mark_task_between_steps(trace_context)
        self._set_outcome_hint(
            NZOutcomeStatus.PARTIAL,
            (
                NZReasonCode.STEP_BUDGET_EXHAUSTED.value
                if len(steps) >= self.max_steps
                else NZReasonCode.TASK_PARTIAL.value
            ),
        )
        self._finish_task(trace_context, TaskState.PARTIAL)

    def create_plan(
        self,
        user_input: str,
        request_trace: list[dict[str, Any]],
        trace_context: TraceContext,
        *,
        step_reservation: StepReservation,
    ) -> tuple[list[dict[str, Any]], ModelCallContext | None]:
        """Ask the model for a short action plan before the reactive loop."""
        prompt = self.build_plan_request(user_input, request_trace)
        self.log_reasoning_trace(
            "planner_request",
            {
                "user_request": user_input,
                "prompt_preview": summarize_text(prompt, 1200),
            },
            trace_context=trace_context,
        )
        model_output: TracedModelOutput | None = None
        try:
            model_output = self.ask_model(
                prompt,
                trace_context,
                step_reservation=step_reservation,
            )
            raw_output = model_output.text
            payload = extract_json_object(raw_output)
        except PersistenceError:
            raise
        except Exception as error:
            reason_code = (
                NZReasonCode.MODEL_RESPONSE_MALFORMED.value
                if model_output is not None
                else provider_reason_code(error)
            )
            self._set_outcome_hint(NZOutcomeStatus.DEGRADED, reason_code)
            self.log_error(
                {
                    "kind": "planner_error",
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                    "prompt_preview": summarize_text(prompt, 1200),
                },
                trace_context=trace_context,
            )
            return [], (
                model_output.model_call if model_output is not None else None
            )

        if "plan" not in payload and "action" not in payload:
            self._set_outcome_hint(
                NZOutcomeStatus.DEGRADED,
                NZReasonCode.MODEL_RESPONSE_MALFORMED.value,
            )
            self.log_error(
                {
                    "kind": "planner_action_error",
                    "error": "Planner output omitted both plan and action.",
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
            )
            return [], model_output.model_call

        raw_plan = payload.get("plan", [])
        if "plan" not in payload and "action" in payload:
            try:
                return [
                    strip_untrusted_identity_fields(validate_action(payload))
                ], model_output.model_call
            except PersistenceError:
                raise
            except Exception as error:
                self._set_outcome_hint(
                    NZOutcomeStatus.DEGRADED,
                    NZReasonCode.MODEL_RESPONSE_MALFORMED.value,
                )
                self.log_error(
                    {
                        "kind": "planner_action_error",
                        "error": str(error),
                    },
                    trace_context=trace_context,
                    model_call=model_output.model_call,
                )
                return [], model_output.model_call
        if not isinstance(raw_plan, list):
            self._set_outcome_hint(
                NZOutcomeStatus.DEGRADED,
                NZReasonCode.MODEL_RESPONSE_MALFORMED.value,
            )
            self.log_error(
                {
                    "kind": "planner_action_error",
                    "error": "Planner output did not contain a plan list.",
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
            )
            return [], model_output.model_call

        planned_actions: list[dict[str, Any]] = []
        for raw_action in raw_plan[: self.max_steps]:
            try:
                planned_actions.append(
                    strip_untrusted_identity_fields(validate_action(raw_action))
                )
            except PersistenceError:
                raise
            except Exception as error:
                self._set_outcome_hint(
                    NZOutcomeStatus.DEGRADED,
                    NZReasonCode.MODEL_RESPONSE_MALFORMED.value,
                )
                self.log_error(
                    {
                        "kind": "planner_action_error",
                        "raw_action": raw_action,
                        "error": str(error),
                    },
                    trace_context=trace_context,
                    model_call=model_output.model_call,
                )
                return [], model_output.model_call

        if planned_actions:
            self.log_reasoning_trace(
                "planner_actions",
                {
                    "user_request": user_input,
                    "planned_actions": planned_actions,
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
            )
            self.log_session_event(
                "planner_output",
                {
                    "raw_output": raw_output,
                    "planned_actions": planned_actions,
                },
                trace_context=trace_context,
                model_call=model_output.model_call,
            )
        return planned_actions, model_output.model_call

    def build_plan_request(
        self,
        user_input: str,
        request_trace: list[dict[str, Any]],
    ) -> str:
        payload = {
            "user_request": user_input,
            "request_trace": request_trace[-4:],
            "runtime": self.snapshot_status(),
            "rhcsa_context": inject_linux_context(user_input, max_chars=3000),
            "instruction": (
                "Return exactly one JSON object with a plan array. "
                "Each plan item must be one allowed action JSON object. "
                "Keep the plan minimal and include a final respond action when the task can be completed. "
                "Do not execute anything. Runtime capability policy independently decides "
                "which tools require human ENTER approval; a model flag can only add approval."
            ),
        }
        safe_payload = self.redactor.redact(payload)
        return self.safe_text("\n".join(
            [
                "SYSTEM PROMPT:",
                self.render_system_prompt(),
                "",
                "PLANNER REQUEST JSON:",
                json.dumps(safe_payload, indent=2, ensure_ascii=False),
                "",
                'EXPECTED FORMAT: {"plan":[{"action":"respond","message":"...","reason":"..."}]}',
            ]
        ))

    def execute_planned_actions(
        self,
        planned_actions: list[dict[str, Any]],
        request_trace: list[dict[str, Any]],
        trace_context: TraceContext,
        planner_call: ModelCallContext | None,
        *,
        first_step_reservation: StepReservation,
    ) -> None:
        print(f"\n[PLAN] {len(planned_actions)} proposed step(s).")
        last_result: dict[str, Any] | None = None
        for step, action in enumerate(planned_actions, start=1):
            step_reservation = (
                first_step_reservation
                if step == 1
                else self._reserve_task_step(trace_context)
            )
            self.print_action(action, step)
            action_context = trace_context.new_action(planner_call)
            try:
                result = self.executor.execute(
                    action,
                    action_context=action_context,
                    step_reservation=step_reservation,
                    recovery_token=self._current_task_execution_token(
                        trace_context.task_id
                    ),
                )
            except PersistenceError:
                raise
            except Exception as error:
                self._close_task_step(step_reservation)
                self.log_error(
                    {
                        "step": step,
                        "action": action,
                        "error": str(error),
                        "traceback": traceback.format_exc(),
                    },
                    trace_context=trace_context,
                    model_call=planner_call,
                    action_context=action_context,
                )
                print("\n[ERROR] Planned action execution failed.")
                print(self.safe_text(error))
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace else TaskState.FAILED,
                )
                return

            self.print_result(result)
            last_result = result
            self.log_session_event(
                "planned_step_result",
                {
                    "step": step,
                    "action": action,
                    "result": self.result_for_model(result),
                },
                trace_context=trace_context,
                model_call=planner_call,
                action_context=action_context,
            )
            request_trace.append(
                {
                    "step": step,
                    "action": action,
                    "result": self.result_for_model(result),
                }
            )
            checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
            if checkpoint is None:
                raise TaskCheckpointError("Planned action lost its task checkpoint.")
            if checkpoint.state in TERMINAL_TASK_STATES or checkpoint.state is TaskState.RECOVERY_REQUIRED:
                return
            if not result.get("success"):
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if request_trace[:-1] else TaskState.FAILED,
                )
                return
            if action["action"] == "respond" or result.get("stop_loop"):
                self._finish_task(trace_context, TaskState.COMPLETED)
                return
            self._mark_task_between_steps(trace_context)
        if last_result and last_result.get("success"):
            print("Agent> Część operacji została już wykonana poprawnie.")
            self._set_outcome_hint(
                NZOutcomeStatus.PARTIAL,
                (
                    NZReasonCode.STEP_BUDGET_EXHAUSTED.value
                    if len(planned_actions) >= self.max_steps
                    else NZReasonCode.TASK_PARTIAL.value
                ),
            )
            self._finish_task(trace_context, TaskState.PARTIAL)

    def execute_action(
        self,
        action: dict[str, Any],
        trace_context: TraceContext,
        model_call: ModelCallContext | None = None,
        *,
        require_approval: bool = True,
        step_reservation: StepReservation | None = None,
    ) -> dict[str, Any]:
        """Assign an action identity before crossing the executor boundary."""

        reservation = step_reservation or self._reserve_task_step(trace_context)
        action_context = trace_context.new_action(model_call)
        result = self.executor.execute(
            strip_untrusted_identity_fields(action),
            require_approval=require_approval,
            action_context=action_context,
            step_reservation=reservation,
            recovery_token=self._current_task_execution_token(
                trace_context.task_id
            ),
        )
        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if (
            checkpoint is not None
            and checkpoint.state not in TERMINAL_TASK_STATES
            and checkpoint.state is not TaskState.RECOVERY_REQUIRED
            and checkpoint.phase is TaskPhase.AFTER_ACTION
        ):
            self._mark_task_between_steps(trace_context)
        return result

    def resume_model(
        self,
        request_text: str,
        *,
        trace_context: TraceContext,
        step_reservation: StepReservation | None,
        recovery_token: RecoveryExecutionToken,
    ) -> Mapping[str, Any]:
        """Continue one operator-authorized model recovery under its claim."""

        reminted_attempt = (
            None
            if step_reservation is None
            else step_reservation.recovery_attempt_id
        )
        if (
            reminted_attempt is not None
            and reminted_attempt != recovery_token.recovery_attempt_id
        ):
            raise RecoveryFencedError(
                "Recovered step reservation does not match the recovery claim."
            )
        hint_binding = self._request_outcome_hint.set(None)
        try:
            with self._recovery_dispatch_scope(
                trace_context,
                recovery_token,
                allowed_directives=frozenset({RecoveryDirective.RESUME_MODEL}),
                step_reservation=step_reservation,
            ):
                self._dispatch_text_request_guarded(
                    request_text,
                    trace_context,
                    ingress="OPERATOR_API",
                    resume_before_model_call=reminted_attempt is not None,
                )
        finally:
            self._request_outcome_hint.reset(hint_binding)
        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is None:
            raise TaskCheckpointError(
                "Recovered request lost its durable task checkpoint."
            )
        return {
            **trace_context.identity_fields(),
            "success": True,
            "task_state": checkpoint.state.value,
            "task_phase": checkpoint.phase.value,
            "outcome": outcome_from_task_state(
                checkpoint.state.value,
                request_id=trace_context.request_id,
                trace_id=trace_context.trace_id,
                task_id=trace_context.task_id,
                recovery_attempt_id=recovery_token.recovery_attempt_id,
            ).to_dict(),
        }

    def resume_reserved_action(
        self,
        action: Mapping[str, Any],
        *,
        trace_context: TraceContext,
        recovery_token: RecoveryExecutionToken,
    ) -> Mapping[str, Any]:
        """Dispatch an exact recoverable action through the guarded executor."""

        with self._recovery_dispatch_scope(
            trace_context,
            recovery_token,
            allowed_directives=frozenset(
                {
                    RecoveryDirective.REVALIDATE_ACTION,
                    RecoveryDirective.REQUIRE_FRESH_APPROVAL,
                }
            ),
        ):
            self.executor.resume_recoverable_action(
                dict(action),
                recovery_token=recovery_token,
            )
            checkpoint = self._terminalize_recovered_action(
                action,
                trace_context,
            )
        return {
            **trace_context.identity_fields(),
            "success": True,
            "task_state": checkpoint.state.value,
            "task_phase": checkpoint.phase.value,
            "outcome": outcome_from_task_state(
                checkpoint.state.value,
                request_id=trace_context.request_id,
                trace_id=trace_context.trace_id,
                task_id=trace_context.task_id,
                recovery_attempt_id=recovery_token.recovery_attempt_id,
            ).to_dict(),
        }

    def resume_waiting_action(
        self,
        action: Mapping[str, Any],
        *,
        trace_context: TraceContext,
        recovery_token: RecoveryExecutionToken,
    ) -> Mapping[str, Any]:
        """Revalidate an approval-waiting action under the same guard."""

        with self._recovery_dispatch_scope(
            trace_context,
            recovery_token,
            allowed_directives=frozenset(
                {
                    RecoveryDirective.REVALIDATE_ACTION,
                    RecoveryDirective.REQUIRE_FRESH_APPROVAL,
                }
            ),
        ):
            self.executor.resume_recoverable_action(
                dict(action),
                recovery_token=recovery_token,
            )
            checkpoint = self._terminalize_recovered_action(
                action,
                trace_context,
            )
        return {
            **trace_context.identity_fields(),
            "success": True,
            "task_state": checkpoint.state.value,
            "task_phase": checkpoint.phase.value,
            "outcome": outcome_from_task_state(
                checkpoint.state.value,
                request_id=trace_context.request_id,
                trace_id=trace_context.trace_id,
                task_id=trace_context.task_id,
                recovery_attempt_id=recovery_token.recovery_attempt_id,
            ).to_dict(),
        }

    def _terminalize_recovered_action(
        self,
        action: Mapping[str, Any],
        trace_context: TraceContext,
    ) -> TaskCheckpoint:
        """Atomically close recovered work whose continuation was not durable."""

        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is None:
            raise TaskCheckpointError(
                "Recovered action lost its durable task checkpoint."
            )
        if checkpoint.state in TERMINAL_TASK_STATES:
            return checkpoint
        if checkpoint.state is TaskState.RECOVERY_REQUIRED:
            raise TaskCheckpointError(
                "Recovered action ended with an unknown durable outcome."
            ).attach_correlation(trace_context.identity_fields())
        if checkpoint.phase is not TaskPhase.AFTER_ACTION:
            raise TaskCheckpointError(
                "Recovered action did not reach a terminalizable durable phase."
            ).attach_correlation(trace_context.identity_fields())
        outcome = checkpoint.current_idempotency_state
        if outcome == "SUCCEEDED":
            terminal_state = (
                TaskState.COMPLETED
                if action.get("action") == "respond"
                or checkpoint.max_steps <= 1
                or checkpoint.remaining_steps <= 0
                else TaskState.PARTIAL
            )
        else:
            try:
                terminal_state = {
                    "BLOCKED": TaskState.BLOCKED,
                    "CANCELLED": TaskState.CANCELLED,
                    "FAILED_BEFORE_DISPATCH": TaskState.FAILED,
                    "FAILED_REPORTED": TaskState.FAILED,
                }[outcome or ""]
            except KeyError as exc:
                raise TaskCheckpointError(
                    "Recovered action has no canonical terminal outcome."
                ).attach_correlation(trace_context.identity_fields()) from exc
        return self._finish_task(trace_context, terminal_state)

    def cancel_recoverable_action(
        self,
        *,
        trace_context: TraceContext,
        recovery_token: RecoveryExecutionToken,
    ) -> Mapping[str, Any]:
        """Cancel only executor-proven work that has not crossed dispatch."""

        with self._recovery_dispatch_scope(
            trace_context,
            recovery_token,
            allowed_directives=frozenset({RecoveryDirective.CANCEL_TASK}),
        ):
            self.executor.cancel_recoverable_action(
                recovery_token=recovery_token,
            )
        checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
        if checkpoint is None:
            raise TaskCheckpointError(
                "Recovered cancellation lost its durable task checkpoint."
            )
        return {
            **trace_context.identity_fields(),
            "success": True,
            "task_state": checkpoint.state.value,
            "task_phase": checkpoint.phase.value,
            "outcome": outcome_from_task_state(
                checkpoint.state.value,
                request_id=trace_context.request_id,
                trace_id=trace_context.trace_id,
                task_id=trace_context.task_id,
                recovery_attempt_id=recovery_token.recovery_attempt_id,
            ).to_dict(),
        }

    def dispatch_text_request(
        self,
        user_input: str,
        trace_context: TraceContext,
        *,
        ingress: str = "RUNTIME",
    ) -> NZOutcome:
        """Dispatch one already-identified CLI, TUI, or web request."""

        hint_binding = self._request_outcome_hint.set(None)
        try:
            with self._live_task_execution_guard(trace_context, user_input):
                return self._dispatch_text_request_guarded(
                    user_input,
                    trace_context,
                    ingress=ingress,
                )
        finally:
            self._request_outcome_hint.reset(hint_binding)

    def _dispatch_text_request_guarded(
        self,
        user_input: str,
        trace_context: TraceContext,
        *,
        ingress: str,
        resume_before_model_call: bool = False,
    ) -> NZOutcome:
        """Run a request while its one live execution claim remains held."""

        # The checkpoint preparation/snapshot/checkpointed triplet is durable
        # before the request lifecycle can claim that work started.
        self._start_task(trace_context, user_input)
        self.provenance_store.append_runtime_event(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_STARTED,
                trace_context=trace_context,
                ingress=ingress,
                request_length=len(user_input),
                slash_command=user_input.strip().startswith("/"),
            )
        )
        self.log_session_event(
            "request_started",
            {
                "input_length": len(user_input),
                "slash_command": user_input.strip().startswith("/"),
            },
            trace_context=trace_context,
        )
        try:
            if resume_before_model_call:
                self.handle_user_request(
                    user_input,
                    trace_context,
                    resume_before_model_call=True,
                )
            else:
                command_result = self.command_registry.execute(
                    user_input,
                    self,
                    trace_context,
                )
                if command_result.handled:
                    if command_result.message:
                        print(self.safe_text(f"\nAgent> {command_result.message}"))
                else:
                    self.handle_user_request(user_input, trace_context)
        except Exception as request_error:
            try:
                self._finish_task(trace_context, TaskState.FAILED)
            except Exception as checkpoint_error:
                try:
                    request_error.add_note(
                        "Request task terminalization is pending or degraded; "
                        f"secondary failure type: {type(checkpoint_error).__name__}."
                    )
                except AttributeError:  # pragma: no cover
                    pass
            try:
                self.provenance_store.append_terminal(
                    new_runtime_provenance_event(
                        RuntimeProvenanceEventType.REQUEST_COMPLETED,
                        trace_context=trace_context,
                        ingress=ingress,
                        success=False,
                        reason_code="REQUEST_FAILED",
                    )
                )
            except Exception as terminal_error:
                try:
                    request_error.add_note(
                        "Request failure provenance is pending or degraded; "
                        f"secondary failure type: {type(terminal_error).__name__}."
                    )
                except AttributeError:  # pragma: no cover
                    pass
            self.log_session_event(
                "request_completed",
                {"status": "failed"},
                trace_context=trace_context,
            )
            raise
        checkpoint = self._finish_task(trace_context, TaskState.COMPLETED)
        request_outcome = self._outcome_for_checkpoint(checkpoint, trace_context)
        request_succeeded = request_outcome.status is NZOutcomeStatus.SUCCESS
        if checkpoint.state is TaskState.RECOVERY_REQUIRED:
            self.provenance_store.append_terminal(
                new_runtime_provenance_event(
                    RuntimeProvenanceEventType.REQUEST_COMPLETED,
                    trace_context=trace_context,
                    ingress=ingress,
                    success=False,
                    reason_code="REQUEST_FAILED",
                )
            )
            self.log_session_event(
                "request_completed",
                {"status": "failed"},
                trace_context=trace_context,
            )
            raise TaskCheckpointError(
                "Request ended with a durable unknown action outcome."
            ).attach_correlation(trace_context.identity_fields())
        self.provenance_store.append_terminal(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_COMPLETED,
                trace_context=trace_context,
                ingress=ingress,
                success=request_succeeded,
                reason_code=(
                    "REQUEST_COMPLETED" if request_succeeded else "REQUEST_FAILED"
                ),
            )
        )
        self.log_session_event(
            "request_completed",
            {"status": request_outcome.status.value.lower()},
            trace_context=trace_context,
        )
        return request_outcome

    def run_text_request(
        self,
        user_input: str,
        trace_context: TraceContext | None = None,
        *,
        ingress: str = "RUNTIME",
    ) -> dict[str, Any]:
        """Execute one text request and capture the textual transcript."""
        trace_context = trace_context or TraceContext.new_request()
        transcript_buffer = io.StringIO()
        with redirect_stdout(transcript_buffer):
            outcome = self.dispatch_text_request(
                user_input,
                trace_context,
                ingress=ingress,
            )
        transcript = self.safe_text(transcript_buffer.getvalue().strip())
        return self._redact_mapping({
            "transcript": transcript,
            "status": self.snapshot_status(),
            "outcome": outcome.to_dict(),
            **trace_context.identity_fields(),
        })

    def handle_local_route(
        self,
        user_input: str,
        trace_context: TraceContext,
    ) -> bool:
        """Execute obvious local tasks before calling the model."""
        route = self.local_router.route(user_input)
        if route is None:
            return False

        if not route.actions:
            if route.final_message:
                print(self.safe_text(f"\nAgent> {route.final_message}"))
            return True

        last_result: dict[str, Any] | None = None
        for index, raw_action in enumerate(route.actions, start=1):
            action = validate_action(raw_action)
            self.print_action(action, index)
            action_context = trace_context.new_action()
            result = self.executor.execute(
                action,
                action_context=action_context,
                step_reservation=self._reserve_task_step(trace_context),
                recovery_token=self._current_task_execution_token(
                    trace_context.task_id
                ),
            )
            last_result = result
            self.print_result(result)
            self.log_session_event(
                "local_route_result",
                {
                    "step": index,
                    "action": action,
                    "result": self.result_for_model(result),
                },
                trace_context=trace_context,
                action_context=action_context,
            )
            checkpoint = self.task_checkpoint_store.load(trace_context.task_id)
            if checkpoint is None:
                raise TaskCheckpointError("Local action lost its task checkpoint.")
            if checkpoint.state in TERMINAL_TASK_STATES or checkpoint.state is TaskState.RECOVERY_REQUIRED:
                return True
            if not result.get("success"):
                self._finish_task(
                    trace_context,
                    TaskState.PARTIAL if index > 1 else TaskState.FAILED,
                )
                return True
            self._mark_task_between_steps(trace_context)

        if route.final_message:
            print(self.safe_text(f"\nAgent> {route.final_message}"))
        elif last_result and last_result.get("message"):
            print(self.safe_text(f"\nAgent> {last_result['message']}"))
        return True

    def handle_knowledge_route(
        self,
        user_input: str,
        trace_context: TraceContext,
    ) -> bool:
        """Answer Linux/RHCSA operational requests from local memory first."""
        if self.safeguards.disable_knowledge:
            self.log_reasoning_trace(
                "knowledge_route_disabled",
                {"user_request": user_input},
                trace_context=trace_context,
            )
            return False
        kernel_decision = self.aoia_kernel.evaluate(user_input)
        self.log_reasoning_trace(
            "aoia_kernel_decision",
            kernel_decision.reasoning,
            trace_context=trace_context,
        )
        if kernel_decision.evidence:
            self.log_reasoning_trace(
                "aoia_kernel_evidence_reference",
                {
                    "query": user_input,
                    "route": kernel_decision.route,
                    "confidence": kernel_decision.confidence,
                    "manual_review_required": kernel_decision.manual_review_required,
                    "artifacts": [item.get("file_location") for item in kernel_decision.evidence],
                },
                trace_context=trace_context,
            )
        if kernel_decision.should_respond_locally:
            result = {
                "success": True,
                "message": kernel_decision.response,
                "confidence_label": kernel_decision.confidence,
                "manual_review_required": kernel_decision.manual_review_required,
                "manual_review_reasons": list(kernel_decision.manual_review_reasons),
                "stop_loop": True,
            }
            self.print_result(result)
            self.log_session_event(
                "aoia_kernel_hit",
                {
                    "confidence": kernel_decision.confidence,
                    "depth": kernel_decision.depth,
                    "pressure": kernel_decision.pressure,
                    "manual_review_required": kernel_decision.manual_review_required,
                    "evidence_count": len(kernel_decision.evidence),
                },
                trace_context=trace_context,
            )
            return True
        decision = self.knowledge_router.route(user_input, self.hat_store.prompt_block())
        if not decision.should_handle_locally:
            self.log_session_event(
                "knowledge_route_miss",
                {
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
                trace_context=trace_context,
            )
            return False

        print(
            self.safe_text(
                f"\nAgent> [CONFIDENCE: {decision.confidence.upper()}] {decision.response}"
            )
        )
        self.log_session_event(
            "knowledge_route_hit",
            {
                "confidence": decision.confidence,
                "reason": decision.reason,
                "score": getattr(decision.hit, "confidence_score", getattr(decision.hit, "score", 0)) if decision.hit else 0,
            },
            trace_context=trace_context,
        )
        return True

    def emit_epistemic_unknown(
        self,
        reason: str,
        trace_context: TraceContext,
        model_call: ModelCallContext | None = None,
    ) -> None:
        result = {
            "success": True,
            "message": "I DO NOT KNOW",
            "confidence_label": "UNKNOWN",
            "epistemic_note": reason,
            "stop_loop": True,
        }
        self.log_reasoning_trace(
            "unknown_response",
            {
                "reason": reason,
                "message": result["message"],
            },
            trace_context=trace_context,
            model_call=model_call,
        )
        self.print_result(result)

    def handle_model_unavailable(
        self,
        request_trace: list[dict[str, Any]],
        error: Exception,
    ) -> None:
        """Avoid hard-crashing after partial success."""
        if is_quota_exhausted_error(error):
            print("\n[WARN] Provider quota is exhausted for the current key.")
        if request_trace:
            last_result = request_trace[-1]["result"]
            print("\n[WARN] Model became unavailable before the next planning step.")
            print(self.safe_text(f"[WARN] {error}"))
            if last_result.get("success"):
                print("Agent> Część operacji została już wykonana poprawnie.")
                if last_result.get("message"):
                    print(
                        self.safe_text(
                            f"Agent> Ostatni zakończony krok: {last_result['message']}"
                        )
                    )
                if last_result.get("current_url"):
                    print(self.safe_text(f"Agent> Aktywny URL: {last_result['current_url']}"))
                print("Agent> Uruchom polecenie jeszcze raz, aby dokończyć kolejne kroki.")
                return

        print("\n[ERROR] Model is unavailable right now.")
        print(self.safe_text(error))
        print("Agent> Configure a working free cloud API with /setup, or switch provider with /model.")

    def bootstrap_local_context(
        self,
        user_input: str,
        trace_context: TraceContext | None = None,
    ) -> list[dict[str, Any]]:
        """Perform obvious local setup without spending model quota.

        This is intentionally narrow:
        - unwrap Facebook redirect links
        - start the browser if the request contains a URL
        - open the URL directly
        - optionally capture visible text for later analysis

        The goal is to save model requests for interpretation rather than for
        trivial browser setup.
        """
        trace_context = trace_context or TraceContext.new_request()
        request_trace: list[dict[str, Any]] = []
        raw_url = extract_first_url(user_input)
        if not raw_url:
            return request_trace

        normalized_url = normalize_external_url(raw_url)
        if normalized_url != raw_url:
            print(self.safe_text(f"\n[INFO] Redirect URL unwrapped to: {normalized_url}"))

        start_action = {"action": "browser_start", "reason": "Local URL bootstrap."}
        start_context = trace_context.new_action()
        start_result = self.executor.execute(
            start_action,
            require_approval=True,
            action_context=start_context,
            step_reservation=self._reserve_task_step(trace_context),
            recovery_token=self._current_task_execution_token(
                trace_context.task_id
            ),
        )
        self.print_result(start_result)
        request_trace.append(
            {
                "step": 0,
                "action": start_action,
                "result": self.result_for_model(start_result),
            }
        )
        if not start_result.get("success"):
            self._finish_task(trace_context, TaskState.FAILED)
            return request_trace
        self._mark_task_between_steps(trace_context)

        open_action = {
            "action": "browser_open",
            "url": normalized_url,
            "reason": "Local URL bootstrap.",
        }
        open_context = trace_context.new_action()
        open_result = self.executor.execute(
            open_action,
            require_approval=True,
            action_context=open_context,
            step_reservation=self._reserve_task_step(trace_context),
            recovery_token=self._current_task_execution_token(
                trace_context.task_id
            ),
        )
        self.print_result(open_result)
        request_trace.append(
            {
                "step": 0,
                "action": open_action,
                "result": self.result_for_model(open_result),
            }
        )
        if not open_result.get("success"):
            self._finish_task(trace_context, TaskState.PARTIAL)
            return request_trace
        self._mark_task_between_steps(trace_context)

        lowered = user_input.lower()
        if any(token in lowered for token in ("analiz", "analy", "paper", "praca", "read", "przeczy")):
            text_action = {
                "action": "browser_get_visible_text",
                "reason": "Capture visible page text before analysis.",
            }
            text_context = trace_context.new_action()
            text_result = self.executor.execute(
                text_action,
                require_approval=True,
                action_context=text_context,
                step_reservation=self._reserve_task_step(trace_context),
                recovery_token=self._current_task_execution_token(
                    trace_context.task_id
                ),
            )
            self.print_result(text_result)
            snapshot_path = self.save_page_text_snapshot(normalized_url, text_result)
            if snapshot_path is not None:
                text_result["snapshot_path"] = str(snapshot_path)
                print(self.safe_text(f"Result: Saved text snapshot to {snapshot_path}"))
            request_trace.append(
                {
                    "step": 0,
                    "action": text_action,
                    "result": self.result_for_model(text_result),
                }
            )
            if not text_result.get("success"):
                self._finish_task(trace_context, TaskState.PARTIAL)
                return request_trace
            self._mark_task_between_steps(trace_context)

        return request_trace

    def save_page_text_snapshot(self, url: str, result: dict[str, Any]) -> Path | None:
        """Persist locally captured page text so quota failures do not lose context."""
        if self._recovery_sensitive_persistence.get():
            return None
        text = self.safe_text(result.get("text", "")).strip()
        if not text:
            return None

        parsed = urlparse(url)
        safe_hostname = self.safe_text(parsed.hostname or "")
        slug = re.sub(r"[^A-Za-z0-9_-]+", "_", safe_hostname).strip("_")[:64]
        if not slug:
            slug = "page"
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_path = self.memory_store.paths.memory_dir / f"{slug}_{timestamp}.txt"
        atomic_write_text(
            snapshot_path,
            text,
            lock_path=state_resource_lock_path(
                self.memory_store.paths.state_dir,
                snapshot_path,
            ),
            lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
        )
        return snapshot_path

    def result_for_model(self, result: dict[str, Any]) -> dict[str, Any]:
        payload = dict(result)
        for field in ("request_id", "trace_id", "task_id", "model_call_id", "action_id"):
            payload.pop(field, None)
        if isinstance(payload.get("outcome"), Mapping):
            payload["outcome"] = without_outcome_identities(payload["outcome"])
        if "stdout" in payload:
            payload["stdout"] = summarize_text(str(payload["stdout"]), 2500)
        if "stderr" in payload:
            payload["stderr"] = summarize_text(str(payload["stderr"]), 2500)
        if "content" in payload:
            payload["content"] = summarize_text(str(payload["content"]), 2500)
        if "text" in payload:
            payload["text"] = summarize_text(str(payload["text"]), 2500)
        if "html" in payload:
            payload["html"] = summarize_text(str(payload["html"]), 2500)
        if "matches" in payload:
            payload["matches"] = payload["matches"][:20]
        return self._redact_mapping(payload)

    @staticmethod
    def _event_identity_fields(
        trace_context: TraceContext | None = None,
        model_call: ModelCallContext | None = None,
        action_context: ActionContext | None = None,
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        if trace_context is not None:
            fields.update(trace_context.identity_fields())
        if model_call is not None:
            if fields and (
                fields.get("request_id") != model_call.request_id
                or fields.get("trace_id") != model_call.trace_id
                or fields.get("task_id") != model_call.task_id
            ):
                raise ValueError("Model-call identity does not match the event trace.")
            fields.update(model_call.identity_fields())
        if action_context is not None:
            if fields and (
                fields.get("request_id") != action_context.request_id
                or fields.get("trace_id") != action_context.trace_id
                or fields.get("task_id") != action_context.task_id
            ):
                raise ValueError("Action identity does not match the event trace.")
            if (
                model_call is not None
                and action_context.model_call_id != model_call.model_call_id
            ):
                raise ValueError("Action identity does not match the event model call.")
            fields.update(action_context.identity_fields())
        return fields

    def log_session_event(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        trace_context: TraceContext | None = None,
        model_call: ModelCallContext | None = None,
        action_context: ActionContext | None = None,
    ) -> None:
        identity = self._event_identity_fields(
            trace_context,
            model_call,
            action_context,
        )
        record = {
            "timestamp": dt.datetime.now().isoformat(),
            "kind": kind,
            **identity,
            "authority": dict(OPERATIONAL_LOG_AUTHORITY),
            "payload": self._recovery_persistence_payload(payload),
        }
        try:
            append_json_line(
                self.session_log,
                record,
                lock_path=state_resource_lock_path(
                    self.memory_store.paths.state_dir,
                    self.session_log,
                ),
                lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(identity)

    def log_reasoning_trace(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        trace_context: TraceContext | None = None,
        model_call: ModelCallContext | None = None,
        action_context: ActionContext | None = None,
    ) -> None:
        if not self.safeguards.reasoning_trace_enabled:
            return
        identity = self._event_identity_fields(
            trace_context,
            model_call,
            action_context,
        )
        try:
            self.memory_store.append_reasoning(
                kind,
                {
                    **identity,
                    **self._recovery_persistence_payload(payload),
                },
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(identity)

    def log_error(
        self,
        payload: dict[str, Any],
        *,
        trace_context: TraceContext | None = None,
        model_call: ModelCallContext | None = None,
        action_context: ActionContext | None = None,
    ) -> None:
        identity = self._event_identity_fields(
            trace_context,
            model_call,
            action_context,
        )
        error_file = (
            self.memory_store.paths.error_logs_dir
            / f"error_{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        )
        try:
            atomic_write_json(
                error_file,
                {
                    **identity,
                    **self._recovery_persistence_payload(payload),
                },
                lock_path=state_resource_lock_path(
                    self.memory_store.paths.state_dir,
                    error_file,
                ),
                lock_timeout_seconds=self.memory_store.state_lock_timeout_seconds,
            )
        except PersistenceError as exc:
            raise exc.attach_correlation(identity)

    def print_action(self, action: dict[str, Any], step: int) -> None:
        safe_action = self._redact_mapping(action)
        print(self.safe_text(f"\n[STEP {step}] action={safe_action['action']}"))
        if safe_action.get("reason"):
            print(self.safe_text(f"Reason: {safe_action['reason']}"))
        for field in ("command", "path", "url", "selector", "key"):
            if field in safe_action and safe_action[field]:
                print(self.safe_text(f"{field}: {safe_action[field]}"))

    def print_result(self, result: dict[str, Any]) -> None:
        self._note_result_outcome(result)
        safe_result = self._redact_mapping(result)
        if safe_result.get("confidence_label"):
            print(self.safe_text(f"[CONFIDENCE: {str(safe_result['confidence_label']).upper()}]"))
        if safe_result.get("manual_review_required"):
            print("[MANUAL REVIEW: REQUIRED]")
            reasons = safe_result.get("manual_review_reasons") or []
            if reasons:
                print(self.safe_text(f"Review reasons: {', '.join(str(reason) for reason in reasons)}"))
        if safe_result.get("message"):
            prefix = "Agent>" if safe_result.get("stop_loop") else "Result:"
            message = str(safe_result["message"])
            if safe_result.get("stop_loop"):
                message = inspect_respond_shell_safety(message).sanitized_message
            print(self.safe_text(f"{prefix} {message}"))
        if safe_result.get("epistemic_note"):
            print(self.safe_text(f"Epistemic note: {safe_result['epistemic_note']}"))

        if "stdout" in safe_result:
            print("\n--- STDOUT ---")
            stdout = str(safe_result["stdout"])
            print(self.safe_text(stdout if stdout.strip() else "(empty)"))

        if "stderr" in safe_result:
            print("\n--- STDERR ---")
            stderr = str(safe_result["stderr"])
            print(self.safe_text(stderr if stderr.strip() else "(empty)"))

        if "content" in safe_result:
            print("\n--- FILE CONTENT ---")
            print(self.safe_text(safe_result["content"]))

        if "text" in safe_result:
            print("\n--- PAGE TEXT ---")
            print(self.safe_text(safe_result["text"]))

        if "current_url" in safe_result and safe_result["current_url"]:
            print(self.safe_text(f"\nCurrent URL: {safe_result['current_url']}"))

        if "screenshot_path" in safe_result:
            print(self.safe_text(f"Screenshot: {safe_result['screenshot_path']}"))

        if "exit_code" in safe_result:
            print(self.safe_text(f"\nExit code: {safe_result['exit_code']}"))


def print_banner(runtime: AgentRuntime) -> None:
    print("########################################################")
    print("###  flAmeBornLLC  |  LLM Academy                   ###")
    print("###  LOCAL AI TERMINAL + BROWSER AGENT              ###")
    print("########################################################")
    print(runtime.safe_text(f"[INFO] Desktop directory detected: {runtime.desktop_dir}"))
    print(runtime.safe_text(f"[INFO] Current working directory: {runtime.memory_store.memory.cwd}"))
    print(runtime.safe_text(f"[INFO] Active model: {runtime.provider_manager.describe()}"))
    print(runtime.safe_text(f"[INFO] Session log: {runtime.session_log}"))
    print(runtime.safe_text(f"[INFO] Obsidian vault: {runtime.memory_store.vault_dir} (lazy)"))


def main() -> None:
    provider_manager = ProviderManager(PROJECT_DIR)
    prompt_template = load_prompt_template(PROMPT_FILE)
    runtime = AgentRuntime(
        provider_manager=provider_manager,
        prompt_template=prompt_template,
        project_dir=PROJECT_DIR,
        debug_raw=DEBUG_RAW_RESPONSE,
    )

    print_banner(runtime)

    while True:
        trace_context: TraceContext | None = None
        try:
            user_input = input("\nYou> ").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "q"}:
                print("Exiting agent...")
                break

            trace_context = TraceContext.new_request()
            runtime.dispatch_text_request(user_input, trace_context, ingress="CLI")
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            break
        except Exception as error:
            runtime.log_error(
                {
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                },
                trace_context=trace_context,
            )
            print(runtime.safe_text(f"\n[FATAL ERROR] {error}"))
            break


if __name__ == "__main__":
    main()
