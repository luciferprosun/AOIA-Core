#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import hashlib
import hmac
import io
import posixpath
import socket
import sys
import time
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, local
from typing import Mapping
from urllib.parse import parse_qsl, unquote, urlparse

from model_catalog import get_static_model_catalog_payload
from memory_hat_registry import get_memory_hat_payload
from trace_context import TraceContext

try:
    from runtime.outcomes import NZOutcome, NZOutcomeStatus, outcome_from_exception
    from runtime.sensitive_redaction import (
        SensitiveValueRedactor,
        build_runtime_redactor,
    )
    from runtime.web_resource_governance import (
        BoundedExecutor,
        BoundedRateLimiter,
        ClientActivityLimiter,
        DeadlineReadTimeout,
        DeadlineSocketReader,
        DeadlineSocketWriter,
        WebResourceLimits,
        client_key,
        load_web_resource_limits,
    )
except ModuleNotFoundError:  # pragma: no cover - script launch path
    from outcomes import NZOutcome, NZOutcomeStatus, outcome_from_exception
    from sensitive_redaction import SensitiveValueRedactor, build_runtime_redactor
    from web_resource_governance import (
        BoundedExecutor,
        BoundedRateLimiter,
        ClientActivityLimiter,
        DeadlineReadTimeout,
        DeadlineSocketReader,
        DeadlineSocketWriter,
        WebResourceLimits,
        client_key,
        load_web_resource_limits,
    )


PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
if not WEB_DIR.exists():
    WEB_DIR = PROJECT_DIR.parent / "web"
HOST = os.getenv("APP2_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("APP2_WEB_PORT", "4311"))
CPT_BALANCED_MODE = "balanced_critic"
WEB_OPERATOR_TOKEN_ENV = "AOIA_WEB_OPERATOR_TOKEN"
WEB_ALLOWED_ORIGINS_ENV = "AOIA_WEB_ALLOWED_ORIGINS"
WEB_MAX_JSON_BYTES_ENV = "AOIA_WEB_MAX_JSON_BYTES"
DEFAULT_MAX_JSON_BYTES = 64 * 1024
MAX_CONFIGURED_JSON_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 32
_SENSITIVE_QUERY_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "auth",
        "authorization",
        "aoia_web_operator_token",
        "bearer",
        "credential",
        "jwt",
        "operator_token",
        "password",
        "secret",
        "token",
    }
)


class WebBoundaryConfigurationError(RuntimeError):
    reason_code = "WEB_BOUNDARY_CONFIGURATION_INVALID"


@dataclass(frozen=True)
class WebBoundaryConfig:
    operator_token: str = field(repr=False)
    allowed_origins: frozenset[str]
    max_json_bytes: int = DEFAULT_MAX_JSON_BYTES
    resource_limits: WebResourceLimits = field(default_factory=WebResourceLimits)

    def __post_init__(self) -> None:
        token = self.operator_token
        if (
            not isinstance(token, str)
            or len(token) < 16
            or len(token) > 4096
            or not token.isascii()
            or any(ord(character) < 33 or ord(character) > 126 for character in token)
        ):
            raise WebBoundaryConfigurationError(
                "AOIA web operator authentication is not safely configured."
            )
        if not isinstance(self.allowed_origins, frozenset):
            raise WebBoundaryConfigurationError("AOIA web origin policy is invalid.")
        for origin in self.allowed_origins:
            try:
                parsed = urlparse(origin)
                parsed_port = parsed.port
            except ValueError as error:
                raise WebBoundaryConfigurationError(
                    "AOIA web origin policy is invalid."
                ) from error
            if (
                not origin
                or "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.hostname is None
                or (parsed_port is not None and not 1 <= parsed_port <= 65535)
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in {"", "/"}
                or parsed.params
                or parsed.query
                or parsed.fragment
                or origin != f"{parsed.scheme}://{parsed.netloc}"
            ):
                raise WebBoundaryConfigurationError("AOIA web origin policy is invalid.")
        if (
            not isinstance(self.max_json_bytes, int)
            or isinstance(self.max_json_bytes, bool)
            or self.max_json_bytes < 2
            or self.max_json_bytes > MAX_CONFIGURED_JSON_BYTES
        ):
            raise WebBoundaryConfigurationError("AOIA web request-size policy is invalid.")
        if not isinstance(self.resource_limits, WebResourceLimits):
            raise WebBoundaryConfigurationError("AOIA web resource policy is invalid.")


def load_web_boundary_config(
    *,
    host: str = HOST,
    port: int = PORT,
    environ: Mapping[str, str] | None = None,
) -> WebBoundaryConfig:
    source = os.environ if environ is None else environ
    token = source.get(WEB_OPERATOR_TOKEN_ENV, "")
    configured_origins = source.get(WEB_ALLOWED_ORIGINS_ENV, "")
    if configured_origins.strip():
        origins = frozenset(
            item.strip().rstrip("/")
            for item in configured_origins.split(",")
            if item.strip()
        )
    elif host in {"127.0.0.1", "localhost", "::1"}:
        origins = frozenset(
            {
                f"http://127.0.0.1:{port}",
                f"http://localhost:{port}",
                f"http://[::1]:{port}",
            }
        )
    else:
        # Authentication remains mandatory on every bind.  Non-loopback binds
        # additionally require an explicit browser-origin allowlist.
        raise WebBoundaryConfigurationError(
            "AOIA web allowed origins must be configured for a non-loopback bind."
        )
    raw_limit = source.get(WEB_MAX_JSON_BYTES_ENV, str(DEFAULT_MAX_JSON_BYTES))
    try:
        limit = int(raw_limit, 10)
    except (TypeError, ValueError) as error:
        raise WebBoundaryConfigurationError(
            "AOIA web request-size policy is invalid."
        ) from error
    try:
        resources = load_web_resource_limits(source)
        return WebBoundaryConfig(
            operator_token=token,
            allowed_origins=origins,
            max_json_bytes=limit,
            resource_limits=resources,
        )
    except ValueError as error:
        raise WebBoundaryConfigurationError(
            "AOIA web resource policy is invalid."
        ) from error


class WebRuntimeService:
    """Shared runtime adapter used by the local web UI."""

    def __init__(self) -> None:
        from main import (
            DEBUG_RAW_RESPONSE,
            PROMPT_FILE,
            AgentRuntime,
            ProviderManager,
            load_prompt_template,
        )

        self.runtime = AgentRuntime(
            provider_manager=ProviderManager(PROJECT_DIR),
            prompt_template=load_prompt_template(PROMPT_FILE),
            project_dir=PROJECT_DIR,
            debug_raw=DEBUG_RAW_RESPONSE,
        )
        self.lock = Lock()

    def status_payload(self) -> dict:
        payload = self.runtime.snapshot_status()
        payload["available_models"] = self.runtime.provider_manager.available_models()
        return payload

    def switch_model(self, model_name: str) -> dict:
        with self.lock:
            selected = self.runtime.provider_manager.switch_model(model_name)
            return {
                "ok": True,
                "model": selected,
                "notice": self.runtime.provider_manager.model_notice(selected),
                "status": self.status_payload(),
            }

    def run_prompt(self, prompt: str) -> dict:
        with self.lock:
            result = self.runtime.run_text_request(prompt, ingress="WEB")
            outcome = result["outcome"]
            return {
                "ok": outcome["status"] == "SUCCESS",
                "transcript": result["transcript"],
                "status": result["status"],
                "outcome": outcome,
                "task_id": result["task_id"],
                "request_id": result["request_id"],
                "trace_id": result["trace_id"],
            }


SERVICE: WebRuntimeService | None = None
SERVICE_INIT_LOCK = Lock()


def get_service() -> WebRuntimeService:
    global SERVICE
    if SERVICE is None:
        with SERVICE_INIT_LOCK:
            if SERVICE is None:
                SERVICE = WebRuntimeService()
    return SERVICE


def build_cpt_transform_payload(prompt: str, mode: str = CPT_BALANCED_MODE) -> dict:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt is required")
    if mode != CPT_BALANCED_MODE:
        raise ValueError("mode must be balanced_critic")

    transform_prompt = _load_cpt_transformer()
    record = transform_prompt(prompt, mode=mode)
    return {
        "ok": True,
        "record": {
            "critic_mode": record.critic_mode,
            "canonical_status": record.canonical_status,
            "human_review_required": record.human_review_required,
            "provider_call_permitted": record.provider_call_permitted,
            "execution_permitted": record.execution_permitted,
            "browser_action_permitted": record.browser_action_permitted,
            "original_prompt_hash": record.original_prompt_hash,
            "transformed_prompt_hash": record.transformed_prompt_hash,
            "transformed_prompt": record.transformed_prompt,
        },
    }


def execute_webapp_approved_model_call(**kwargs) -> dict[str, object]:
    """Compatibility bridge for red-team registry tests; not exposed as a web endpoint."""

    try:
        from runtime.model_router import execute_approved_model_call_once
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from model_router import execute_approved_model_call_once

    return execute_approved_model_call_once(**kwargs)


def get_commit_history_payload() -> dict[str, object]:
    try:
        from runtime.git_ops.git_read import GIT_READ_COMMAND_PASS, GitReadCommand, GitReadRequest, run_allowlisted_git_read
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from git_ops.git_read import GIT_READ_COMMAND_PASS, GitReadCommand, GitReadRequest, run_allowlisted_git_read

    evidence = run_allowlisted_git_read(
        GitReadRequest(workspace_root=PROJECT_DIR.parent, max_output_bytes=50_000),
        GitReadCommand.COMMIT_LOG,
    )
    if evidence.status != GIT_READ_COMMAND_PASS:
        return {
            "ok": False,
            "commits": [],
            "commit_count": 0,
            "all_commits_returned": False,
            "reason_code": evidence.reason_code,
            "can_commit": False,
            "can_push": False,
        }

    commits = _parse_commit_log_output(evidence.stdout_preview)
    return {
        "ok": True,
        "commits": commits,
        "commit_count": len(commits),
        "all_commits_returned": True,
        "reason_code": evidence.reason_code,
        "can_commit": False,
        "can_push": False,
    }


def _parse_commit_log_output(output: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t", 4)
        if len(parts) != 5:
            continue
        full_sha, short_sha, committed_at, author, subject = parts
        commits.append(
            {
                "sha": full_sha,
                "short_sha": short_sha,
                "committed_at": committed_at,
                "author": author,
                "subject": subject,
            }
        )
    return commits


def _canonical_operator_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _operator_hash(value: object) -> str:
    return hashlib.sha256(_canonical_operator_json(value).encode("utf-8")).hexdigest()


def get_operator_status_payload() -> dict[str, object]:
    try:
        from runtime.git_ops.git_read import GitReadRequest, read_local_git_state
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from git_ops.git_read import GitReadRequest, read_local_git_state

    git_state = read_local_git_state(GitReadRequest(workspace_root=PROJECT_DIR.parent))
    git_payload = git_state.to_dict()
    return {
        "ok": True,
        "schema_version": "AOIA_OPERATOR_STATUS_1A",
        "app_name": "AOIA Operator Console",
        "roadmap_block": "Steps 42-54 complete",
        "prototype_freeze_status": "recorded locally if freeze commit is present",
        "safety_mode": "preview-only operator console",
        "git": {
            "status": git_payload["status"],
            "branch": git_payload["branch_name"],
            "head": git_payload["head_sha"],
            "clean": git_payload["clean"],
            "staged_paths": git_payload["staged_paths"],
            "unstaged_paths": git_payload["unstaged_paths"],
            "untracked_paths": git_payload["untracked_paths"],
            "reason_codes": git_payload["reason_codes"],
            "can_commit": False,
            "can_push": False,
            "can_write": False,
        },
        "authority": {
            "provider_output_is_authority": False,
            "metadata_is_authority": False,
            "ui_state_is_authority": False,
            "dispatcher_present": False,
            "human_review_required": True,
        },
    }


def get_boundary_map_payload() -> dict[str, object]:
    names = (
        ("package_proposal", "Package proposal"),
        ("controlled_package_install", "Controlled package install"),
        ("browser_read", "Browser read"),
        ("browser_preview", "Browser preview"),
        ("browser_governance", "Browser governance"),
        ("controlled_browser_simulation", "Controlled browser simulation"),
        ("coding_assistant_boundary", "Codex/Aider boundary"),
        ("mcp_boundary", "MCP boundary"),
        ("async_orchestration", "Async orchestration"),
        ("feedback_recovery", "Feedback/recovery"),
        ("codex_live_flow", "Codex live-flow boundary"),
        ("local_agent_loop", "Local agent loop boundary"),
        ("provider_agent_loop", "Provider agent loop boundary"),
    )
    return {
        "ok": True,
        "schema_version": "AOIA_BOUNDARY_MAP_1A",
        "boundaries": [
            {
                "id": boundary_id,
                "label": label,
                "status": "ready_metadata_only",
                "inert_metadata": True,
                "can_execute": False,
                "can_dispatch": False,
                "requires_human_review": True,
                "reason_codes": ("AOIA_METADATA_ONLY", "AOIA_NO_AUTHORITY"),
            }
            for boundary_id, label in names
        ],
    }


def get_router_status_payload() -> dict[str, object]:
    try:
        from provider_config import get_provider_config_status
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from runtime.provider_config import get_provider_config_status

    config = get_provider_config_status()
    catalog = get_static_model_catalog_payload()
    provider_configured = {
        "kimi": bool(config.get("kimi_configured")),
        "kimi_chat": bool(config.get("kimi_configured")),
        "gemini": bool(config.get("gemini_configured")),
        "gemini_chat": bool(config.get("gemini_configured")),
        "openrouter": bool(config.get("openrouter_configured")),
        "openrouter_chat": bool(config.get("openrouter_configured")),
        "local": False,
        "disabled": False,
    }
    manual_chat_available = bool(config.get("kimi_configured"))
    return {
        "ok": True,
        "schema_version": "AOIA_ROUTER_STATUS_1A",
        "status": "manual_live_available" if manual_chat_available else "provider_key_missing",
        "provider_call_disabled": not manual_chat_available,
        "provider_call_permitted": manual_chat_available,
        "connection_callable": manual_chat_available,
        "human_approval_required": True,
        "human_barrier_connected": False,
        "reason": (
            "Kimi key detected; manual chat can call the controlled Provider Runtime 1A gateway."
            if manual_chat_available
            else "Kimi provider key is not configured."
        ),
        "safe_next_step": "Use Chat Send for one manual non-streaming provider call; output remains untrusted.",
        "provider_configured": provider_configured,
        "models": catalog["models"],
        "notice": "No automatic fallback, streaming, tools, dispatch, or execution is connected.",
    }


def build_router_preview_payload(payload: dict[str, object]) -> dict[str, object]:
    try:
        from model_router import create_model_selection_proposal, evaluate_model_selection_policy
    except ModuleNotFoundError:  # pragma: no cover - package import path
        from runtime.model_router import create_model_selection_proposal, evaluate_model_selection_policy

    provider_id = str(payload.get("provider_id", "")).strip()
    model_id = str(payload.get("model_id", "")).strip()
    task_sensitivity = str(payload.get("task_sensitivity", "PUBLIC_DEV")).strip() or "PUBLIC_DEV"
    user_prompt = str(payload.get("user_prompt", ""))
    if not provider_id or not model_id:
        raise ValueError("provider_id and model_id are required")

    request_material = {
        "provider_id": provider_id,
        "model_id": model_id,
        "task_sensitivity": task_sensitivity,
        "prompt_hash": _operator_hash({"prompt": user_prompt}),
    }
    proposal = create_model_selection_proposal(
        provider_id=provider_id,
        model_id=model_id,
        task_sensitivity=task_sensitivity,
        user_prompt=user_prompt,
    )
    decision = evaluate_model_selection_policy(proposal=proposal)
    preview_material = {
        "request_hash": _operator_hash(request_material),
        "proposal": proposal,
        "decision": decision,
        "provider_call_permitted": False,
        "call_made": False,
        "output_trusted": False,
    }
    blocked_reason = decision.get("reason") or "Preview only - no controlled execution path connected."
    return {
        "ok": True,
        "schema_version": "AOIA_ROUTER_PREVIEW_1A",
        "request_hash": preview_material["request_hash"],
        "preview_hash": _operator_hash(preview_material),
        "proposal_hash": _operator_hash(proposal),
        "decision_hash": _operator_hash(decision),
        "proposal": proposal,
        "decision": decision,
        "status": "blocked_preview_only",
        "provider_call_permitted": False,
        "provider_call_disabled": True,
        "call_made": False,
        "output_trusted": False,
        "human_barrier_connected": False,
        "disabled_reason": f"Blocked: {blocked_reason}",
        "safe_next_step": "Preview only - no controlled execution path connected.",
        "reason_codes": (
            "AOIA_ROUTER_PREVIEW_ONLY",
            "AOIA_PROVIDER_CALL_DISABLED",
            "AOIA_HUMAN_BARRIER_NOT_CONNECTED",
        ),
    }


def get_evidence_sample_payload() -> dict[str, object]:
    missing = "missing"
    evidence = {
        "request_hash": missing,
        "preview_hash": missing,
        "governance_hash": missing,
        "barrier_hash": missing,
        "result_hash": missing,
        "status": "missing",
        "reason_codes": ("AOIA_EVIDENCE_NOT_SELECTED", "AOIA_HASH_BOUND_APPROVAL_REQUIRED"),
        "risk_codes": ("AOIA_PREVIEW_ONLY",),
    }
    return {
        "ok": True,
        "schema_version": "AOIA_EVIDENCE_INSPECTOR_1A",
        "evidence": evidence,
        "can_execute": False,
        "can_dispatch": False,
    }


def get_agent_loop_status_payload() -> dict[str, object]:
    return {
        "ok": True,
        "schema_version": "AOIA_AGENT_LOOP_STATUS_1A",
        "local_loop": {
            "objective_summary": "No live objective selected.",
            "candidates": [],
            "selected_candidate": None,
            "blocked_candidates": [],
            "risk_tier": "metadata_only",
            "reason_codes": ("LOCAL_AGENT_LOOP_NON_AUTHORITY",),
            "requires_human_review": True,
            "requires_controlled_path": True,
            "can_execute": False,
        },
        "provider_loop": {
            "objective_summary": "Provider output is untrusted metadata only.",
            "candidates": [],
            "selected_candidate": None,
            "blocked_candidates": [],
            "risk_tier": "metadata_only",
            "reason_codes": ("PROVIDER_AGENT_LOOP_PROVIDER_OUTPUT_UNTRUSTED",),
            "requires_human_review": True,
            "requires_controlled_path": True,
            "can_execute": False,
        },
    }


def get_audit_status_payload() -> dict[str, object]:
    return {
        "ok": True,
        "schema_version": "AOIA_AUDIT_STATUS_1A",
        "messages": (
            "Operator console supports manual controlled provider chat when a key is configured.",
            "Provider output is never authority.",
            "UI checkbox is not a hash-bound human barrier.",
            "Provider requests are only sent by explicit Chat Send.",
            "No execution or dispatch endpoint is connected.",
        ),
        "can_execute": False,
        "can_dispatch": False,
        "can_call_provider": False,
    }


def build_operator_chat_payload(payload: dict[str, object]) -> dict[str, object]:
    try:
        from runtime.providers.contracts import LIVE_SUCCESS, ProviderActivationStatus
        from runtime.providers.selector import run_selected_provider
        from runtime.runtime_paths import runtime_state_dir
        from runtime.task_checkpoints import (
            ApprovalState,
            DurableTaskCheckpointStore,
            TaskPhase,
            TaskState,
            safe_context_metadata,
        )
        from runtime.task_recovery import RecoveryPurpose, TaskRecoveryService
        from runtime.tools.provenance import (
            AppendOnlyProvenanceStore,
            RuntimeProvenanceEventType,
            new_runtime_provenance_event,
        )
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from providers.contracts import LIVE_SUCCESS, ProviderActivationStatus
        from providers.selector import run_selected_provider
        from runtime_paths import runtime_state_dir
        from task_checkpoints import (
            ApprovalState,
            DurableTaskCheckpointStore,
            TaskPhase,
            TaskState,
            safe_context_metadata,
        )
        from task_recovery import RecoveryPurpose, TaskRecoveryService
        from tools.provenance import (
            AppendOnlyProvenanceStore,
            RuntimeProvenanceEventType,
            new_runtime_provenance_event,
        )

    provider_id = str(payload.get("provider_id", "kimi_chat")).strip() or "kimi_chat"
    model_id = str(payload.get("model_id", "moonshot-v1-8k")).strip() or "moonshot-v1-8k"
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
    trace_context = TraceContext.new_request()
    model_call = trace_context.new_model_call()
    provenance_store = AppendOnlyProvenanceStore(
        runtime_state_dir(PROJECT_DIR) / "state"
    )
    task_checkpoint_store = DurableTaskCheckpointStore(
        runtime_state_dir(PROJECT_DIR) / "state",
        project_dir=PROJECT_DIR,
        provenance_store=provenance_store,
    )
    checkpoint = task_checkpoint_store.create_task(
        trace_context,
        max_steps=1,
        retry_budget=1,
        safe_context=safe_context_metadata(prompt),
    )
    recovery_service = TaskRecoveryService(
        runtime_state_dir(PROJECT_DIR) / "state",
        project_dir=PROJECT_DIR,
        checkpoint_store=task_checkpoint_store,
        provenance_store=provenance_store,
    )
    step_reservation = None

    def terminalize_model_and_task(succeeded: bool) -> None:
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
                ingress="OPERATOR_API",
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
            result = run_selected_provider(
                provider_id=provider_id,
                model_id=model_id,
                prompt=prompt,
                max_tokens=512,
                live=True,
                acknowledge_live_provider_test=True,
                activation_status=ProviderActivationStatus.LIVE_ALLOWED_FOR_MANUAL_TEST,
                selected_by="operator",
                created_at="operator-chat-manual",
            )
        except Exception as provider_error:
            try:
                terminalize_model_and_task(False)
                provenance_store.append_terminal(
                    new_runtime_provenance_event(
                        RuntimeProvenanceEventType.REQUEST_COMPLETED,
                        trace_context=trace_context,
                        ingress="OPERATOR_API",
                        success=False,
                        reason_code="REQUEST_FAILED",
                    )
                )
            except Exception as provenance_error:
                try:
                    provider_error.add_note(
                        "Operator provider failure provenance is pending or degraded; "
                        f"secondary failure type: {type(provenance_error).__name__}."
                    )
                except AttributeError:  # pragma: no cover
                    pass
            raise
        provider_succeeded = result.status == LIVE_SUCCESS
        terminalize_model_and_task(provider_succeeded)
        provenance_store.append_terminal(
            new_runtime_provenance_event(
                RuntimeProvenanceEventType.REQUEST_COMPLETED,
                trace_context=trace_context,
                ingress="OPERATOR_API",
                success=provider_succeeded,
                reason_code=(
                    "REQUEST_COMPLETED" if provider_succeeded else "REQUEST_FAILED"
                ),
            )
        )
        result_payload = result.to_dict()
        return {
            "ok": result.status == LIVE_SUCCESS,
            "schema_version": "AOIA_OPERATOR_CHAT_1A",
            "provider_id": result.provider_id,
            "model_id": result.model_id,
            "call_made": result.status == LIVE_SUCCESS,
            "status": result.status,
            "response_text": result.response_text or "",
            "error": result.error_message or "",
            "output_trusted": False,
            "automatic_fallback_used": False,
            "streaming_used": False,
            "tool_call_used": False,
            "execution_triggered": False,
            "dispatch_triggered": False,
            "trust_status": result_payload["trust_status"],
            "reason_code": result.reason_code,
            "outcome": result_payload["outcome"],
            **model_call.identity_fields(),
        }


def route_get_payload(path: str) -> tuple[HTTPStatus, dict[str, object]] | None:
    if path == "/api/status":
        return HTTPStatus.OK, get_service().status_payload()
    if path == "/api/models":
        service = get_service()
        return HTTPStatus.OK, {
            "current_model": service.runtime.provider_manager.describe(),
            "available_models": service.runtime.provider_manager.available_models(),
        }
    if path == "/api/model-catalog":
        return HTTPStatus.OK, get_static_model_catalog_payload()
    if path == "/api/memory-hats":
        return HTTPStatus.OK, get_memory_hat_payload()
    if path == "/api/provider-config-status":
        from provider_config import get_provider_config_status

        return HTTPStatus.OK, get_provider_config_status()
    if path == "/api/commits":
        return HTTPStatus.OK, get_commit_history_payload()
    if path == "/api/operator/status":
        return HTTPStatus.OK, get_operator_status_payload()
    if path == "/api/boundaries":
        return HTTPStatus.OK, get_boundary_map_payload()
    if path == "/api/router/status":
        return HTTPStatus.OK, get_router_status_payload()
    if path == "/api/evidence/sample":
        return HTTPStatus.OK, get_evidence_sample_payload()
    if path == "/api/agent-loop/status":
        return HTTPStatus.OK, get_agent_loop_status_payload()
    if path == "/api/audit/status":
        return HTTPStatus.OK, get_audit_status_payload()
    return None


def route_post_payload(path: str, payload: dict[str, object]) -> tuple[HTTPStatus, dict[str, object]]:
    if path == "/api/chat":
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": "prompt is required"}
        return HTTPStatus.OK, get_service().run_prompt(prompt)
    if path == "/api/operator/chat":
        try:
            response = build_operator_chat_payload(payload)
            return HTTPStatus.OK if response["ok"] else HTTPStatus.BAD_GATEWAY, response
        except (TypeError, ValueError) as error:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)}
    if path == "/api/router/preview":
        try:
            return HTTPStatus.OK, build_router_preview_payload(payload)
        except (TypeError, ValueError) as error:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)}
    return HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"}


def _load_cpt_transformer():
    project_parent = str(PROJECT_DIR.parent)
    if project_parent not in sys.path:
        sys.path.insert(0, project_parent)
    from runtime.cpt.transformer import transform_prompt

    return transform_prompt


PUBLIC_HEALTH_PATHS = frozenset({"/api/health"})
AUTHENTICATED_READ_PATHS = frozenset(
    {
        "/api/status",
        "/api/models",
        "/api/model-catalog",
        "/api/memory-hats",
        "/api/provider-config-status",
        "/api/commits",
        "/api/operator/status",
        "/api/boundaries",
        "/api/router/status",
        "/api/evidence/sample",
        "/api/agent-loop/status",
        "/api/audit/status",
    }
)
AUTHENTICATED_MUTATION_PATHS = frozenset(
    {
        "/api/chat",
        "/api/operator/chat",
        "/api/router/preview",
        "/api/cpt/transform",
        "/api/model",
        "/api/model-selection/propose",
    }
)

# The authentication source remains the process environment.  Changing a
# parent shell's environment cannot atomically update a running process, so
# P1.1 deliberately retains restart-only rotation instead of adding a second
# secret source or an HTTP credential mutation endpoint.
WEB_TOKEN_ROTATION_MODE = "restart_required"


@dataclass(frozen=True)
class _PendingWebResponse:
    writer: str
    status: HTTPStatus
    payload: Mapping[str, object]


class _RequestDeadlineBeforeDispatch(TimeoutError):
    pass


_OPERATION_REJECTED = object()
_WEB_DEADLINE_ENVELOPE_REASONS = frozenset(
    {
        "WEB_HEADER_TIMEOUT",
        "WEB_BODY_TIMEOUT",
        "WEB_REQUEST_DEADLINE_EXCEEDED",
        "WEB_REQUEST_DEADLINE_UNKNOWN",
    }
)


class _DispatchGate:
    """Atomically fence deadline cancellation against mutation dispatch."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = "pending"

    def begin(self, *, now: float, deadline: float) -> bool:
        with self._lock:
            if self._state != "pending" or now >= deadline:
                return False
            self._state = "started"
            return True

    def cancel_if_pending(self) -> bool:
        with self._lock:
            if self._state != "pending":
                return False
            self._state = "cancelled"
            return True


class AOIAWebServer(ThreadingHTTPServer):
    """Single-operator server with bounded admission and route execution."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class,
        *,
        boundary_config: WebBoundaryConfig,
        monotonic_clock=time.monotonic,
    ) -> None:
        self.web_boundary_config = boundary_config
        limits = boundary_config.resource_limits
        # TCPServer.server_activate reads this instance value during super().
        # Setting it first makes the kernel accept backlog explicit and finite.
        self.request_queue_size = limits.listen_backlog
        self.monotonic_clock = monotonic_clock
        self.output_redactor = build_runtime_redactor(
            environ=os.environ,
            additional_values=(boundary_config.operator_token,),
        )
        self.operator_mutation_lock = Lock()
        self.request_executor = BoundedExecutor(
            max_workers=limits.max_concurrent_requests,
            max_queue=limits.max_queued_requests,
            thread_name_prefix="aoia-web-request",
        )
        self.operation_executor = BoundedExecutor(
            max_workers=limits.max_concurrent_requests,
            max_queue=limits.max_queued_requests,
            thread_name_prefix="aoia-web-operation",
        )
        total_capacity = limits.max_concurrent_requests + limits.max_queued_requests
        self.client_activity = ClientActivityLimiter(
            max_clients=max(1, total_capacity),
            max_per_client=limits.max_client_requests,
        )
        self.rate_limiter = BoundedRateLimiter(
            max_entries=limits.rate_max_entries,
            ttl_seconds=limits.rate_ttl_seconds,
            clock=monotonic_clock,
        )
        self._resource_close_lock = Lock()
        self._resources_closed = False
        self._request_timing = local()
        try:
            super().__init__(server_address, handler_class)
        except BaseException:
            self.request_executor.shutdown(wait=False)
            self.operation_executor.shutdown(wait=False)
            raise

    def process_request(self, request, client_address) -> None:
        accepted_at = float(self.monotonic_clock())
        key = client_key(client_address)
        if not self.client_activity.acquire(key):
            self._reject_busy(request)
            return
        try:
            future = self.request_executor.submit(
                self._run_request,
                request,
                client_address,
                key,
                accepted_at,
                accepted_at
                + self.web_boundary_config.resource_limits.request_deadline_seconds,
            )
        except BaseException:
            self.client_activity.release(key)
            self._reject_busy(request)
            return
        if future is None:
            self.client_activity.release(key)
            self._reject_busy(request)

    def _run_request(
        self,
        request,
        client_address,
        key: bytes,
        accepted_at: float,
        deadline: float,
    ) -> None:
        self._request_timing.value = (accepted_at, deadline)
        try:
            self.process_request_thread(request, client_address)
        finally:
            self._request_timing.value = None
            self.client_activity.release(key)

    def current_request_timing(self) -> tuple[float, float] | None:
        value = getattr(self._request_timing, "value", None)
        return value if isinstance(value, tuple) and len(value) == 2 else None

    def submit_operation(self, function):
        return self.operation_executor.submit(function)

    def handle_error(self, request, client_address) -> None:
        # Expected disconnects and bounded client timeouts must not emit raw
        # tracebacks, filesystem paths, request data, or addresses to stderr.
        return

    def _reject_busy(self, request) -> None:
        trace_context = TraceContext.new_request()
        payload = _safe_http_error_payload(
            outcome_status=NZOutcomeStatus.BLOCKED,
            reason_code="WEB_SERVER_BUSY",
            message_safe="The local operator service is at its resource limit.",
            trace_context=trace_context,
        )
        safe_payload = self.output_redactor.redact(payload)
        if not isinstance(safe_payload, dict):
            safe_payload = {"ok": False, "message_safe": "The response is unavailable."}
        body = json.dumps(safe_payload, ensure_ascii=False).encode("utf-8")
        response = (
            b"HTTP/1.1 503 Service Unavailable\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"Cache-Control: no-store\r\n"
            + b"X-Content-Type-Options: nosniff\r\n"
            + b"Referrer-Policy: no-referrer\r\n"
            + b"Connection: close\r\n\r\n"
            + body
        )
        try:
            request.settimeout(
                min(0.25, self.web_boundary_config.resource_limits.write_timeout_seconds)
            )
            request.sendall(response)
        except (OSError, TimeoutError, ValueError):
            pass
        finally:
            self.shutdown_request(request)

    def server_close(self) -> None:
        with self._resource_close_lock:
            if self._resources_closed:
                return
            self._resources_closed = True
        super().server_close()
        # Header/body/write stages are bounded, so request workers can drain.
        self.request_executor.shutdown(wait=True)
        # Route work may have crossed an HTTP deadline.  It remains bounded by
        # P0 task/provider controls, but closing the listener must not claim to
        # terminate or synchronously wait for that already-running work.
        self.operation_executor.shutdown(wait=False)


def _safe_http_error_payload(
    *,
    outcome_status: NZOutcomeStatus,
    reason_code: str,
    message_safe: str,
    trace_context: TraceContext,
) -> dict[str, object]:
    outcome = NZOutcome.build(
        outcome_status,
        reason_code,
        message_safe=message_safe,
        request_id=trace_context.request_id,
        trace_id=trace_context.trace_id,
    ).to_dict()
    return {
        "ok": False,
        "status": outcome["status"],
        "reason_code": outcome["reason_code"],
        "message_safe": outcome["message_safe"],
        # Compatibility alias.  It is always identical to the bounded safe text.
        "error": outcome["message_safe"],
        "request_id": trace_context.request_id,
        "trace_id": trace_context.trace_id,
        "outcome": outcome,
    }


def _safe_exception_payload(
    error: BaseException,
    trace_context: TraceContext,
) -> dict[str, object]:
    outcome = outcome_from_exception(
        error,
        request_id=trace_context.request_id,
        trace_id=trace_context.trace_id,
    ).to_dict()
    return {
        "ok": False,
        "status": outcome["status"],
        "reason_code": outcome["reason_code"],
        "message_safe": outcome["message_safe"],
        "error": outcome["message_safe"],
        "request_id": trace_context.request_id,
        "trace_id": trace_context.trace_id,
        "outcome": outcome,
    }


def _safe_projected_outcome_payload(
    source: NZOutcome,
    trace_context: TraceContext,
) -> dict[str, object]:
    """Rebuild an error outcome without copying upstream text, data, or identities."""

    outcome = NZOutcome.build(
        source.status,
        source.reason_code,
        request_id=trace_context.request_id,
        trace_id=trace_context.trace_id,
        replayed=source.replayed,
        degraded=source.degraded,
    ).to_dict()
    return {
        "ok": False,
        "status": outcome["status"],
        "reason_code": outcome["reason_code"],
        "message_safe": outcome["message_safe"],
        "error": outcome["message_safe"],
        "request_id": trace_context.request_id,
        "trace_id": trace_context.trace_id,
        "outcome": outcome,
    }


def _http_status_for_outcome(status: NZOutcomeStatus) -> HTTPStatus:
    if status in {NZOutcomeStatus.PARTIAL, NZOutcomeStatus.DEGRADED}:
        return HTTPStatus.OK
    if status is NZOutcomeStatus.BLOCKED:
        return HTTPStatus.FORBIDDEN
    if status is NZOutcomeStatus.TIMEOUT:
        return HTTPStatus.GATEWAY_TIMEOUT
    if status is NZOutcomeStatus.FAILED:
        return HTTPStatus.BAD_GATEWAY
    return HTTPStatus.CONFLICT


def _with_http_identity(
    payload: Mapping[str, object],
    trace_context: TraceContext,
) -> dict[str, object]:
    response = dict(payload)
    response.setdefault("request_id", trace_context.request_id)
    response.setdefault("trace_id", trace_context.trace_id)
    return response


def _strict_json_object(raw_body: bytes) -> dict[str, object]:
    try:
        text = raw_body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("WEB_JSON_INVALID") from error

    def reject_constant(_value: str) -> object:
        raise ValueError("WEB_JSON_INVALID")

    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("WEB_JSON_DUPLICATE_FIELD")
            result[key] = value
        return result

    try:
        payload = json.loads(
            text,
            object_pairs_hook=unique_pairs,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, ValueError, RecursionError) as error:
        raise ValueError("WEB_JSON_INVALID") from error
    if not isinstance(payload, dict):
        raise ValueError("WEB_JSON_OBJECT_REQUIRED")
    stack: list[tuple[object, int]] = [(payload, 1)]
    while stack:
        value, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ValueError("WEB_JSON_DEPTH_EXCEEDED")
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    return payload


def _is_api_path(path: str) -> bool:
    try:
        decoded = unquote(path, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        decoded = path
    raw_absolute = "/" + path.lstrip("/")
    decoded_absolute = "/" + decoded.lstrip("/")
    if (
        raw_absolute == "/api"
        or raw_absolute.startswith("/api/")
        or decoded_absolute == "/api"
        or decoded_absolute.startswith("/api/")
    ):
        return True
    canonical = posixpath.normpath("/" + decoded.lstrip("/"))
    return canonical == "/api" or canonical.startswith("/api/")


class CodexStyleHandler(SimpleHTTPRequestHandler):
    """Serve the static UI and a small JSON API."""

    def setup(self) -> None:
        self.connection = self.request
        server = getattr(self, "server", None)
        config = getattr(server, "web_boundary_config", None)
        limits = (
            config.resource_limits
            if isinstance(config, WebBoundaryConfig)
            else WebResourceLimits()
        )
        clock = getattr(server, "monotonic_clock", time.monotonic)
        timing_getter = getattr(server, "current_request_timing", None)
        timing = timing_getter() if callable(timing_getter) else None
        if timing is None:
            self._request_started_at = float(clock())
            self._request_deadline = (
                self._request_started_at + limits.request_deadline_seconds
            )
        else:
            self._request_started_at, self._request_deadline = timing
        remaining_request_time = max(
            0.000001,
            self._request_deadline - float(clock()),
        )
        if self.disable_nagle_algorithm:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._deadline_reader = DeadlineSocketReader(
            self.connection,
            timeout_seconds=min(
                limits.header_timeout_seconds,
                remaining_request_time,
            ),
            clock=clock,
        )
        self.rfile = io.BufferedReader(self._deadline_reader, buffer_size=8192)
        self._deadline_writer = DeadlineSocketWriter(
            self.connection,
            timeout_seconds=limits.write_timeout_seconds,
            deadline=self._request_deadline,
            clock=clock,
        )
        self.wfile = io.BufferedWriter(self._deadline_writer, buffer_size=8192)
        self._response_started = False

    def handle_one_request(self) -> None:
        """Stdlib request handling with an explicit safe slow-client result."""

        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ""
                self.request_version = ""
                self.command = ""
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            method_name = "do_" + self.command
            if not hasattr(self, method_name):
                self.send_error(
                    HTTPStatus.NOT_IMPLEMENTED,
                    "Unsupported method (%r)" % self.command,
                )
                return
            getattr(self, method_name)()
            self.wfile.flush()
        except TimeoutError:
            self.close_connection = True
            if not getattr(self, "_response_started", False):
                self.requestline = getattr(self, "requestline", "")
                self.request_version = getattr(self, "request_version", "")
                self.command = getattr(self, "command", "")
                try:
                    self._write_error(
                        HTTPStatus.REQUEST_TIMEOUT,
                        NZOutcomeStatus.TIMEOUT,
                        "WEB_HEADER_TIMEOUT",
                        "The request headers exceeded the enforced deadline.",
                        TraceContext.new_request(),
                    )
                except (OSError, TimeoutError, ValueError):
                    pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        trace_context = TraceContext.new_request()
        if self._request_deadline_expired():
            self._write_request_deadline(trace_context, uncertain=False)
            return
        try:
            parsed = urlparse(self.path)
        except ValueError:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_PATH_INVALID",
                "The request target is invalid.",
                trace_context,
            )
            return
        api_namespace = _is_api_path(parsed.path) or _is_api_path(
            self.path.split("?", 1)[0]
        )
        if self._reject_query(parsed, api_namespace, trace_context):
            return

        if parsed.path in PUBLIC_HEALTH_PATHS:
            if not self._rate_allowed("health", trace_context):
                return
            outcome = NZOutcome.build(
                NZOutcomeStatus.SUCCESS,
                request_id=trace_context.request_id,
                trace_id=trace_context.trace_id,
            ).to_dict()
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "aoia-local-web",
                    "status": outcome["status"],
                    "request_id": trace_context.request_id,
                    "trace_id": trace_context.trace_id,
                    "outcome": outcome,
                },
            )
            return

        if api_namespace:
            if not self._rate_allowed("auth", trace_context):
                return
            config = self._resolve_boundary_config(trace_context)
            if config is None or not self._authenticate(config, trace_context):
                return
            if not self._rate_allowed("read", trace_context):
                return
            if parsed.path not in AUTHENTICATED_READ_PATHS:
                self._write_error(
                    HTTPStatus.NOT_FOUND,
                    NZOutcomeStatus.BLOCKED,
                    "WEB_ROUTE_NOT_FOUND",
                    "The requested API route does not exist.",
                    trace_context,
                )
                return
            try:
                routed = self._execute_operation(
                    lambda: route_get_payload(parsed.path),
                    trace_context,
                    mutation=False,
                )
                if routed is _OPERATION_REJECTED:
                    return
                if routed is None:
                    self._write_error(
                        HTTPStatus.NOT_FOUND,
                        NZOutcomeStatus.BLOCKED,
                        "WEB_ROUTE_NOT_FOUND",
                        "The requested API route does not exist.",
                        trace_context,
                    )
                    return
                status, payload = routed
                self._write_routed_json(status, payload, trace_context)
            except Exception as error:  # safe HTTP boundary; raw details stay local
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    _safe_exception_payload(error, trace_context),
                )
            return

        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
        if self._request_deadline_expired():
            self._write_request_deadline(trace_context, uncertain=False)
            return
        server = getattr(self, "server", None)
        config = getattr(server, "web_boundary_config", None)
        connection = getattr(self, "connection", None)
        if isinstance(config, WebBoundaryConfig) and connection is not None:
            if not self._prepare_response_writer(
                config,
                allow_expired_grace=False,
            ):
                self._write_request_deadline(trace_context, uncertain=False)
                return
        self._response_started = True
        self.close_connection = True
        return super().do_GET()

    def do_POST(self) -> None:
        trace_context = TraceContext.new_request()
        if self._request_deadline_expired():
            self._write_request_deadline(trace_context, uncertain=False)
            return
        try:
            parsed = urlparse(self.path)
        except ValueError:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_PATH_INVALID",
                "The request target is invalid.",
                trace_context,
            )
            return
        api_namespace = _is_api_path(parsed.path) or _is_api_path(
            self.path.split("?", 1)[0]
        )
        if self._reject_query(parsed, api_namespace, trace_context):
            return
        if not api_namespace:
            self._write_error(
                HTTPStatus.NOT_FOUND,
                NZOutcomeStatus.BLOCKED,
                "WEB_ROUTE_NOT_FOUND",
                "The requested API route does not exist.",
                trace_context,
            )
            return
        config = self._resolve_boundary_config(trace_context)
        if not self._rate_allowed("auth", trace_context):
            return
        if config is None or not self._authenticate(config, trace_context):
            return
        if parsed.path not in AUTHENTICATED_MUTATION_PATHS:
            self._write_error(
                HTTPStatus.NOT_FOUND,
                NZOutcomeStatus.BLOCKED,
                "WEB_ROUTE_NOT_FOUND",
                "The requested API route does not exist.",
                trace_context,
            )
            return
        if not self._origin_allowed(config, trace_context):
            return
        if not self._rate_allowed("mutation", trace_context):
            return
        payload = self._read_json_body(config, trace_context)
        if payload is None:
            return
        if not self._validate_known_field_types(parsed.path, payload, trace_context):
            return

        try:
            pending = self._execute_operation(
                lambda: self._build_pending_post(parsed.path, payload),
                trace_context,
                mutation=True,
            )
            if pending is _OPERATION_REJECTED:
                return
            self._emit_pending_response(pending, trace_context)
        except Exception as error:  # raw exception text and tracebacks never cross HTTP
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _safe_exception_payload(error, trace_context),
            )

    def _dispatch_post(
        self,
        parsed,
        payload: dict[str, object],
        trace_context: TraceContext,
    ) -> None:
        path = parsed.path
        if not self._validate_known_field_types(path, payload, trace_context):
            return
        self._emit_pending_response(
            self._build_pending_post(path, payload),
            trace_context,
        )

    def _build_pending_post(
        self,
        path: str,
        payload: dict[str, object],
    ) -> _PendingWebResponse:
        """Execute route logic without writing to the client socket.

        Real servers run this function in the bounded operation executor.  A
        deadline response can therefore close the HTTP lifecycle without a
        late worker ever writing a second response to the same socket.
        """

        if path == "/api/router/preview":
            status, response = route_post_payload(path, payload)
            return _PendingWebResponse("routed", status, response)

        if path == "/api/operator/chat":
            status, response = route_post_payload(path, payload)
            return _PendingWebResponse("routed", status, response)

        if path == "/api/cpt/transform":
            prompt = payload.get("prompt", "")
            mode = payload.get("mode", CPT_BALANCED_MODE)
            if mode is None:
                mode = CPT_BALANCED_MODE
            try:
                response = build_cpt_transform_payload(prompt=prompt, mode=mode)
            except (TypeError, ValueError) as error:
                message = str(error)
                if message not in {"prompt is required", "mode must be balanced_critic"}:
                    message = "The JSON request is invalid."
                return _PendingWebResponse(
                    "error",
                    HTTPStatus.BAD_REQUEST,
                    {
                        "outcome_status": NZOutcomeStatus.BLOCKED,
                        "reason_code": "WEB_REQUEST_INVALID",
                        "message_safe": message,
                    },
                )
            return _PendingWebResponse("json", HTTPStatus.OK, response)

        if path == "/api/chat":
            status, response = route_post_payload(path, payload)
            return _PendingWebResponse("routed", status, response)

        if path == "/api/model":
            model_name = str(payload.get("model", "")).strip()
            if not model_name:
                return _PendingWebResponse(
                    "error",
                    HTTPStatus.BAD_REQUEST,
                    {
                        "outcome_status": NZOutcomeStatus.BLOCKED,
                        "reason_code": "WEB_REQUEST_INVALID",
                        "message_safe": "model is required",
                    },
                )
            response = get_service().switch_model(model_name)
            return _PendingWebResponse("json", HTTPStatus.OK, response)

        if path == "/api/model-selection/propose":
            from model_router import create_model_selection_proposal, evaluate_model_selection_policy

            provider_id = str(payload.get("provider_id", "")).strip()
            model_id = str(payload.get("model_id", "")).strip()
            task_sensitivity = str(payload.get("task_sensitivity", "")).strip()
            user_prompt = str(payload.get("user_prompt", ""))
            if not provider_id or not model_id or not task_sensitivity:
                return _PendingWebResponse(
                    "error",
                    HTTPStatus.BAD_REQUEST,
                    {
                        "outcome_status": NZOutcomeStatus.BLOCKED,
                        "reason_code": "WEB_REQUEST_INVALID",
                        "message_safe": "provider_id, model_id, and task_sensitivity are required",
                    },
                )
            proposal = create_model_selection_proposal(
                provider_id=provider_id,
                model_id=model_id,
                task_sensitivity=task_sensitivity,
                user_prompt=user_prompt,
            )
            decision = evaluate_model_selection_policy(proposal=proposal)
            return _PendingWebResponse(
                "json",
                HTTPStatus.OK,
                {
                    "ok": True,
                    "proposal": proposal,
                    "decision": decision,
                    "human_approval_required": True,
                    "provider_call_permitted": False,
                    "output_trusted": False,
                },
            )

        return _PendingWebResponse(
            "error",
            HTTPStatus.NOT_FOUND,
            {
                "outcome_status": NZOutcomeStatus.BLOCKED,
                "reason_code": "WEB_ROUTE_NOT_FOUND",
                "message_safe": "The requested API route does not exist.",
            },
        )

    def _emit_pending_response(
        self,
        pending: _PendingWebResponse,
        trace_context: TraceContext,
    ) -> None:
        if pending.writer == "routed":
            self._write_routed_json(pending.status, pending.payload, trace_context)
            return
        if pending.writer == "json":
            self._write_json(
                pending.status,
                _with_http_identity(pending.payload, trace_context),
            )
            return
        if pending.writer == "error":
            self._write_error(
                pending.status,
                pending.payload["outcome_status"],  # type: ignore[arg-type]
                str(pending.payload["reason_code"]),
                str(pending.payload["message_safe"]),
                trace_context,
            )
            return
        raise RuntimeError("unsupported internal web response writer")

    def log_message(self, format: str, *args) -> None:
        return

    def _rate_allowed(self, scope: str, trace_context: TraceContext) -> bool:
        server = getattr(self, "server", None)
        limiter = getattr(server, "rate_limiter", None)
        config = getattr(server, "web_boundary_config", None)
        address = getattr(self, "client_address", None)
        if (
            not isinstance(limiter, BoundedRateLimiter)
            or not isinstance(config, WebBoundaryConfig)
            or address is None
        ):
            # Direct unit-boundary invocation has no socket/server resource to
            # consume; real HTTP requests always take the governed path.
            return True
        limits = config.resource_limits
        capacity = {
            "auth": limits.read_rate_limit,
            "health": limits.health_rate_limit,
            "read": limits.read_rate_limit,
            "mutation": limits.mutation_rate_limit,
        }[scope]
        if limiter.allow(
            scope,
            client_key(address),
            capacity=capacity,
            window_seconds=limits.rate_window_seconds,
        ):
            return True
        self._write_error(
            HTTPStatus.TOO_MANY_REQUESTS,
            NZOutcomeStatus.BLOCKED,
            "WEB_RATE_LIMITED",
            "The local request rate limit has been reached.",
            trace_context,
        )
        return False

    def _execute_operation(
        self,
        function,
        trace_context: TraceContext,
        *,
        mutation: bool,
    ):
        server = getattr(self, "server", None)
        submit = getattr(server, "submit_operation", None)
        if not callable(submit):
            return function()

        clock = getattr(server, "monotonic_clock", time.monotonic)
        config = getattr(server, "web_boundary_config", None)
        if not isinstance(config, WebBoundaryConfig):
            return function()
        deadline = getattr(
            self,
            "_request_deadline",
            float(clock()) + config.resource_limits.request_deadline_seconds,
        )
        dispatch_gate = _DispatchGate()

        def governed_operation():
            if not mutation:
                if not dispatch_gate.begin(now=float(clock()), deadline=deadline):
                    raise _RequestDeadlineBeforeDispatch()
                return function()
            mutation_lock = getattr(server, "operator_mutation_lock", None)
            if mutation_lock is None:
                raise _RequestDeadlineBeforeDispatch()
            remaining = deadline - float(clock())
            if remaining <= 0 or not mutation_lock.acquire(timeout=remaining):
                raise _RequestDeadlineBeforeDispatch()
            try:
                if not dispatch_gate.begin(now=float(clock()), deadline=deadline):
                    raise _RequestDeadlineBeforeDispatch()
                return function()
            finally:
                mutation_lock.release()

        remaining = deadline - float(clock())
        if remaining <= 0:
            self._write_request_deadline(trace_context, uncertain=False)
            return _OPERATION_REJECTED
        future = submit(governed_operation)
        if future is None:
            self._write_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                NZOutcomeStatus.BLOCKED,
                "WEB_SERVER_BUSY",
                "The local operator service is at its resource limit.",
                trace_context,
            )
            return _OPERATION_REJECTED
        try:
            result = future.result(timeout=max(0.001, deadline - float(clock())))
            if float(clock()) >= deadline:
                self._write_request_deadline(trace_context, uncertain=False)
                return _OPERATION_REJECTED
            return result
        except _RequestDeadlineBeforeDispatch:
            self._write_request_deadline(trace_context, uncertain=False)
            return _OPERATION_REJECTED
        except FutureTimeoutError:
            if future.done():
                result = future.result()
                if float(clock()) >= deadline:
                    self._write_request_deadline(trace_context, uncertain=False)
                    return _OPERATION_REJECTED
                return result
            prevented_dispatch = dispatch_gate.cancel_if_pending()
            future.cancel()
            self._write_request_deadline(
                trace_context,
                uncertain=mutation and not prevented_dispatch,
            )
            return _OPERATION_REJECTED

    def _write_request_deadline(
        self,
        trace_context: TraceContext,
        *,
        uncertain: bool,
    ) -> None:
        if uncertain:
            self._write_error(
                HTTPStatus.GATEWAY_TIMEOUT,
                NZOutcomeStatus.UNKNOWN_OUTCOME,
                "WEB_REQUEST_DEADLINE_UNKNOWN",
                "The HTTP deadline expired after work began; completion is not claimed.",
                trace_context,
            )
            return
        self._write_error(
            HTTPStatus.GATEWAY_TIMEOUT,
            NZOutcomeStatus.TIMEOUT,
            "WEB_REQUEST_DEADLINE_EXCEEDED",
            "The request exceeded its enforced execution deadline.",
            trace_context,
        )

    def _header_values(self, name: str) -> list[str]:
        get_all = getattr(self.headers, "get_all", None)
        if callable(get_all):
            return [str(value) for value in (get_all(name, []) or [])]
        value = self.headers.get(name)
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return [str(value)]

    def _resolve_boundary_config(
        self,
        trace_context: TraceContext,
    ) -> WebBoundaryConfig | None:
        direct = getattr(self, "web_boundary_config", None)
        server = getattr(self, "server", None)
        config = direct or getattr(server, "web_boundary_config", None)
        if isinstance(config, WebBoundaryConfig):
            return config
        try:
            return load_web_boundary_config()
        except WebBoundaryConfigurationError:
            self._write_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                NZOutcomeStatus.BLOCKED,
                "WEB_BOUNDARY_CONFIGURATION_INVALID",
                "Local operator authentication is unavailable.",
                trace_context,
            )
            return None

    def _authenticate(
        self,
        config: WebBoundaryConfig,
        trace_context: TraceContext,
    ) -> bool:
        values = self._header_values("Authorization")
        candidate = ""
        if len(values) == 1:
            scheme, separator, supplied = values[0].partition(" ")
            if separator and scheme.casefold() == "bearer" and supplied and not supplied.isspace():
                candidate = supplied
        authenticated = hmac.compare_digest(
            candidate.encode("utf-8", errors="surrogatepass"),
            config.operator_token.encode("ascii"),
        )
        if authenticated:
            return True
        self._write_error(
            HTTPStatus.UNAUTHORIZED,
            NZOutcomeStatus.BLOCKED,
            "WEB_AUTHENTICATION_REQUIRED",
            "Valid local operator authentication is required.",
            trace_context,
        )
        return False

    def _reject_query(
        self,
        parsed,
        api_namespace: bool,
        trace_context: TraceContext,
    ) -> bool:
        try:
            fields = parse_qsl(
                parsed.query,
                keep_blank_values=True,
                strict_parsing=False,
                max_num_fields=64,
            )
        except ValueError:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_QUERY_INVALID",
                "The request query is invalid.",
                trace_context,
            )
            return True
        if any(name.casefold() in _SENSITIVE_QUERY_NAMES for name, _value in fields):
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_AUTH_QUERY_REJECTED",
                "Authentication data is not accepted in request URLs.",
                trace_context,
            )
            return True
        if api_namespace and parsed.query:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_QUERY_UNSUPPORTED",
                "API query parameters are not supported.",
                trace_context,
            )
            return True
        return False

    def _origin_allowed(
        self,
        config: WebBoundaryConfig,
        trace_context: TraceContext,
    ) -> bool:
        origins = self._header_values("Origin")
        if not origins:
            return True  # Non-browser bearer clients do not normally send Origin.
        if len(origins) == 1 and origins[0] in config.allowed_origins:
            return True
        self._write_error(
            HTTPStatus.FORBIDDEN,
            NZOutcomeStatus.BLOCKED,
            "WEB_ORIGIN_REJECTED",
            "The request origin is not permitted.",
            trace_context,
        )
        return False

    def _read_json_body(
        self,
        config: WebBoundaryConfig,
        trace_context: TraceContext,
    ) -> dict[str, object] | None:
        transfer_encoding = self._header_values("Transfer-Encoding")
        if transfer_encoding:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_TRANSFER_ENCODING_UNSUPPORTED",
                "Transfer-encoded request bodies are not supported.",
                trace_context,
            )
            return None

        content_types = self._header_values("Content-Type")
        if len(content_types) != 1 or not self._valid_json_content_type(content_types[0]):
            self._write_error(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                NZOutcomeStatus.BLOCKED,
                "WEB_CONTENT_TYPE_UNSUPPORTED",
                "A UTF-8 application/json request body is required.",
                trace_context,
            )
            return None

        lengths = self._header_values("Content-Length")
        if not lengths:
            self._write_error(
                HTTPStatus.LENGTH_REQUIRED,
                NZOutcomeStatus.BLOCKED,
                "WEB_CONTENT_LENGTH_REQUIRED",
                "A bounded Content-Length header is required.",
                trace_context,
            )
            return None
        if len(lengths) != 1:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_CONTENT_LENGTH_INVALID",
                "The Content-Length header is invalid.",
                trace_context,
            )
            return None
        raw_length = lengths[0].strip()
        if (
            not raw_length
            or len(raw_length) > 10
            or not raw_length.isascii()
            or not raw_length.isdigit()
        ):
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_CONTENT_LENGTH_INVALID",
                "The Content-Length header is invalid.",
                trace_context,
            )
            return None
        length = int(raw_length, 10)
        if length <= 0:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_JSON_INVALID",
                "The JSON request body is invalid.",
                trace_context,
            )
            return None
        if length > config.max_json_bytes:
            self._write_error(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                NZOutcomeStatus.BLOCKED,
                "WEB_REQUEST_TOO_LARGE",
                "The JSON request body exceeds the configured limit.",
                trace_context,
            )
            return None

        reader = getattr(self, "_deadline_reader", None)
        if isinstance(reader, DeadlineSocketReader):
            server = getattr(self, "server", None)
            clock = getattr(server, "monotonic_clock", time.monotonic)
            request_deadline = getattr(self, "_request_deadline", None)
            phase_timeout = config.resource_limits.body_timeout_seconds
            if isinstance(request_deadline, (int, float)):
                remaining = float(request_deadline) - float(clock())
                if remaining <= 0:
                    self._write_request_deadline(trace_context, uncertain=False)
                    return None
                phase_timeout = min(phase_timeout, remaining)
            reader.set_phase_timeout(phase_timeout)
        try:
            raw_body = self.rfile.read(length)
        except DeadlineReadTimeout:
            self._write_error(
                HTTPStatus.REQUEST_TIMEOUT,
                NZOutcomeStatus.TIMEOUT,
                "WEB_BODY_TIMEOUT",
                "The JSON request body exceeded the enforced read deadline.",
                trace_context,
            )
            return None
        except (OSError, ValueError):
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_BODY_INCOMPLETE",
                "The JSON request body is incomplete.",
                trace_context,
            )
            return None
        if not isinstance(raw_body, bytes) or len(raw_body) != length:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_BODY_INCOMPLETE",
                "The JSON request body is incomplete.",
                trace_context,
            )
            return None
        try:
            return _strict_json_object(raw_body)
        except ValueError:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_JSON_INVALID",
                "The JSON request body is invalid.",
                trace_context,
            )
            return None

    @staticmethod
    def _valid_json_content_type(value: str) -> bool:
        parts = [part.strip() for part in value.split(";")]
        if not parts or parts[0].casefold() != "application/json":
            return False
        seen_charset = False
        for parameter in parts[1:]:
            if not parameter or "=" not in parameter:
                return False
            name, raw_value = parameter.split("=", 1)
            if name.strip().casefold() != "charset" or seen_charset:
                return False
            charset = raw_value.strip().strip('"').casefold()
            if charset not in {"utf-8", "utf8"}:
                return False
            seen_charset = True
        return True

    def _validate_known_field_types(
        self,
        path: str,
        payload: Mapping[str, object],
        trace_context: TraceContext,
    ) -> bool:
        optional_none = {"mode"} if path == "/api/cpt/transform" else set()
        known_fields = {
            "/api/chat": ("prompt",),
            "/api/operator/chat": ("provider_id", "model_id", "prompt"),
            "/api/router/preview": ("provider_id", "model_id", "task_sensitivity", "user_prompt"),
            "/api/cpt/transform": ("prompt", "mode"),
            "/api/model": ("model",),
            "/api/model-selection/propose": (
                "provider_id",
                "model_id",
                "task_sensitivity",
                "user_prompt",
            ),
        }[path]
        invalid = any(
            name in payload
            and not isinstance(payload[name], str)
            and not (name in optional_none and payload[name] is None)
            for name in known_fields
        )
        if invalid:
            self._write_error(
                HTTPStatus.BAD_REQUEST,
                NZOutcomeStatus.BLOCKED,
                "WEB_REQUEST_INVALID",
                "The JSON request fields are invalid.",
                trace_context,
            )
            return False
        return True

    def _write_routed_json(
        self,
        status: HTTPStatus,
        payload: Mapping[str, object],
        trace_context: TraceContext,
    ) -> None:
        source_outcome: NZOutcome | None = None
        if "outcome" in payload:
            try:
                source_outcome = NZOutcome.from_dict(payload["outcome"])  # type: ignore[arg-type]
            except (TypeError, ValueError, RuntimeError):
                self._write_error(
                    HTTPStatus.BAD_GATEWAY,
                    NZOutcomeStatus.FAILED,
                    "WEB_OUTCOME_INVALID",
                    "The runtime returned an invalid outcome.",
                    trace_context,
                )
                return
        if source_outcome is not None and source_outcome.status is not NZOutcomeStatus.SUCCESS:
            self._write_json(
                _http_status_for_outcome(source_outcome.status),
                _safe_projected_outcome_payload(source_outcome, trace_context),
            )
            return
        if status >= HTTPStatus.BAD_REQUEST or payload.get("ok") is False:
            if source_outcome is not None:
                self._write_error(
                    HTTPStatus.BAD_GATEWAY,
                    NZOutcomeStatus.FAILED,
                    "WEB_OUTCOME_CONFLICT",
                    "The runtime returned conflicting outcome state.",
                    trace_context,
                )
                return
            raw_message = payload.get("error")
            message = (
                raw_message
                if raw_message in {"prompt is required", "provider_id and model_id are required"}
                else "The JSON request is invalid."
            )
            if status >= HTTPStatus.INTERNAL_SERVER_ERROR or status < HTTPStatus.BAD_REQUEST:
                self._write_error(
                    HTTPStatus.BAD_GATEWAY,
                    NZOutcomeStatus.FAILED,
                    "WEB_OPERATION_FAILED",
                    "The runtime could not complete the operation.",
                    trace_context,
                )
                return
            self._write_error(
                status,
                NZOutcomeStatus.BLOCKED,
                "WEB_REQUEST_INVALID",
                str(message),
                trace_context,
            )
            return
        self._write_json(status, _with_http_identity(payload, trace_context))

    def _write_error(
        self,
        http_status: HTTPStatus,
        outcome_status: NZOutcomeStatus,
        reason_code: str,
        message_safe: str,
        trace_context: TraceContext,
    ) -> None:
        previous_authorization = getattr(
            self,
            "_deadline_envelope_authorized",
            False,
        )
        self._deadline_envelope_authorized = (
            reason_code in _WEB_DEADLINE_ENVELOPE_REASONS
        )
        try:
            self._write_json(
                http_status,
                _safe_http_error_payload(
                    outcome_status=outcome_status,
                    reason_code=reason_code,
                    message_safe=message_safe,
                    trace_context=trace_context,
                ),
            )
        finally:
            self._deadline_envelope_authorized = previous_authorization

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        deadline_envelope = getattr(
            self,
            "_deadline_envelope_authorized",
            False,
        ) is True
        if not deadline_envelope and self._request_deadline_expired():
            trace_context = self._trace_from_http_payload(payload)
            status = HTTPStatus.GATEWAY_TIMEOUT
            payload = _safe_http_error_payload(
                outcome_status=NZOutcomeStatus.TIMEOUT,
                reason_code="WEB_REQUEST_DEADLINE_EXCEEDED",
                message_safe="The request exceeded its enforced execution deadline.",
                trace_context=trace_context,
            )
            deadline_envelope = True
        safe_payload = self._response_redactor().redact(payload)
        if not isinstance(safe_payload, dict):  # defensive JSON boundary
            safe_payload = {"ok": False, "message_safe": "The response is unavailable."}
        body = json.dumps(safe_payload, ensure_ascii=False).encode("utf-8")
        server = getattr(self, "server", None)
        config = getattr(server, "web_boundary_config", None)
        connection = getattr(self, "connection", None)
        if isinstance(config, WebBoundaryConfig) and connection is not None:
            prepared = self._prepare_response_writer(
                config,
                allow_expired_grace=deadline_envelope,
            )
            if not prepared:
                trace_context = self._trace_from_http_payload(payload)
                status = HTTPStatus.GATEWAY_TIMEOUT
                payload = _safe_http_error_payload(
                    outcome_status=NZOutcomeStatus.TIMEOUT,
                    reason_code="WEB_REQUEST_DEADLINE_EXCEEDED",
                    message_safe="The request exceeded its enforced execution deadline.",
                    trace_context=trace_context,
                )
                safe_payload = self._response_redactor().redact(payload)
                if not isinstance(safe_payload, dict):
                    safe_payload = {
                        "ok": False,
                        "message_safe": "The response is unavailable.",
                    }
                body = json.dumps(safe_payload, ensure_ascii=False).encode("utf-8")
                self._prepare_response_writer(
                    config,
                    allow_expired_grace=True,
                )
        self._response_started = True
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _request_deadline_expired(self) -> bool:
        deadline = getattr(self, "_request_deadline", None)
        if not isinstance(deadline, (int, float)):
            return False
        server = getattr(self, "server", None)
        clock = getattr(server, "monotonic_clock", time.monotonic)
        return float(clock()) >= float(deadline)

    @staticmethod
    def _trace_from_http_payload(payload: Mapping[str, object]) -> TraceContext:
        try:
            return TraceContext(
                request_id=str(payload.get("request_id")),
                trace_id=str(payload.get("trace_id")),
            )
        except (TypeError, ValueError, RuntimeError):
            return TraceContext.new_request()

    def _response_redactor(self) -> SensitiveValueRedactor:
        server = getattr(self, "server", None)
        configured = getattr(server, "output_redactor", None)
        boundary = getattr(self, "web_boundary_config", None) or getattr(
            server,
            "web_boundary_config",
            None,
        )
        additional_values = (
            (boundary.operator_token,)
            if isinstance(boundary, WebBoundaryConfig)
            else ()
        )
        current = build_runtime_redactor(
            environ=os.environ,
            additional_values=additional_values,
        )
        return (
            current.combining(configured)
            if isinstance(configured, SensitiveValueRedactor)
            else current
        )

    def _response_write_timeout(self, config: WebBoundaryConfig) -> float:
        timeout = config.resource_limits.write_timeout_seconds
        server = getattr(self, "server", None)
        clock = getattr(server, "monotonic_clock", time.monotonic)
        deadline = getattr(self, "_request_deadline", None)
        if isinstance(deadline, (int, float)):
            remaining = float(deadline) - float(clock())
            if remaining > 0:
                return max(0.000001, min(timeout, remaining))
            # A bounded grace allows the explicit 408/504 envelope itself to
            # be emitted after the deadline fired without holding a worker.
            return min(0.25, timeout)
        return timeout

    def _prepare_response_writer(
        self,
        config: WebBoundaryConfig,
        *,
        allow_expired_grace: bool,
    ) -> bool:
        timeout = self._response_write_timeout(config)
        server = getattr(self, "server", None)
        clock = getattr(server, "monotonic_clock", time.monotonic)
        now = float(clock())
        request_deadline = getattr(self, "_request_deadline", now + timeout)
        if float(request_deadline) <= now and not allow_expired_grace:
            return False
        deadline = (
            float(request_deadline)
            if float(request_deadline) > now
            else now + timeout
        )
        writer = getattr(self, "_deadline_writer", None)
        if isinstance(writer, DeadlineSocketWriter):
            writer.set_deadline(deadline=deadline, timeout_seconds=timeout)
        connection = getattr(self, "connection", None)
        if connection is not None:
            connection.settimeout(timeout)
        return True


def main() -> None:
    try:
        boundary_config = load_web_boundary_config(host=HOST, port=PORT)
    except WebBoundaryConfigurationError as error:
        print(f"AOIA web server refused to start: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    server = AOIAWebServer(
        (HOST, PORT),
        CodexStyleHandler,
        boundary_config=boundary_config,
    )
    print(f"App222 web UI running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
