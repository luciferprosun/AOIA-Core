#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import hashlib
import ipaddress
import re
import sys
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

from model_catalog import get_static_model_catalog_payload
from memory_hat_registry import get_memory_hat_payload


PROJECT_DIR = Path(__file__).resolve().parent
WEB_DIR = PROJECT_DIR / "web"
if not WEB_DIR.exists():
    WEB_DIR = PROJECT_DIR.parent / "web"
HOST = os.getenv("APP2_WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("APP2_WEB_PORT", "4311"))
CPT_BALANCED_MODE = "balanced_critic"


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
            result = self.runtime.run_text_request(prompt)
            return {
                "ok": True,
                "transcript": result["transcript"],
                "status": result["status"],
            }


SERVICE: WebRuntimeService | None = None
SERVICE_INIT_LOCK = Lock()
ORCHESTRA_SERVICE = None
ORCHESTRA_SERVICE_INIT_LOCK = Lock()
MAXIMUM_JSON_BODY_BYTES = 256 * 1024
SENSITIVE_ORCHESTRA_API_PATHS = frozenset(
    {
        "/api/provider-connections",
        "/api/provider-connections/disable",
        "/api/provider-connections/test",
        "/api/model-profiles",
        "/api/model-profiles/disable",
        "/api/orchestra/preview",
        "/api/orchestra/run",
    }
)
SENSITIVE_ORCHESTRA_GET_PATHS = frozenset(
    {
        "/api/provider-connections",
        "/api/model-profiles",
        "/api/orchestra/models",
    }
)
ORCHESTRA_SESSION_API_ROOT = "/api/orchestra/sessions"
ORCHESTRA_HUMAN_REVIEW_SUFFIX = "/human-review"
_ORCHESTRA_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


def _is_sensitive_orchestra_get_path(path: str) -> bool:
    return path in SENSITIVE_ORCHESTRA_GET_PATHS or (
        path == ORCHESTRA_SESSION_API_ROOT
        or path.startswith(f"{ORCHESTRA_SESSION_API_ROOT}/")
    )


def _session_id_from_api_path(path: str) -> str | None:
    if not (
        path == ORCHESTRA_SESSION_API_ROOT
        or path.startswith(f"{ORCHESTRA_SESSION_API_ROOT}/")
    ):
        return None
    prefix = f"{ORCHESTRA_SESSION_API_ROOT}/"
    candidate = path[len(prefix) :] if path.startswith(prefix) else ""
    if (
        not candidate
        or "/" in candidate
        or "%" in candidate
        or not _ORCHESTRA_SESSION_ID.fullmatch(candidate)
    ):
        raise ValueError("session identifier is malformed")
    return candidate


def _human_review_session_id_from_api_path(path: str) -> str | None:
    prefix = f"{ORCHESTRA_SESSION_API_ROOT}/"
    if not path.startswith(prefix) or not path.endswith(ORCHESTRA_HUMAN_REVIEW_SUFFIX):
        return None
    candidate = path[len(prefix) : -len(ORCHESTRA_HUMAN_REVIEW_SUFFIX)]
    if (
        not candidate
        or "/" in candidate
        or "%" in candidate
        or not _ORCHESTRA_SESSION_ID.fullmatch(candidate)
    ):
        raise ValueError("session identifier is malformed")
    return candidate


def get_service() -> WebRuntimeService:
    global SERVICE
    if SERVICE is None:
        with SERVICE_INIT_LOCK:
            if SERVICE is None:
                SERVICE = WebRuntimeService()
    return SERVICE


def get_orchestra_service():
    """Lazily construct the local user-provider/Orchestra service.

    Importing ``runtime.webapp`` remains inert: no state directory, credential,
    provider adapter, or network gateway is touched until an operator calls one
    of the new configuration or Orchestra endpoints.
    """

    global ORCHESTRA_SERVICE
    if ORCHESTRA_SERVICE is None:
        with ORCHESTRA_SERVICE_INIT_LOCK:
            if ORCHESTRA_SERVICE is None:
                project_parent = str(PROJECT_DIR.parent)
                if project_parent not in sys.path:
                    sys.path.insert(0, project_parent)
                from runtime.providers.orchestra_live_service import OrchestraLiveWebService

                ORCHESTRA_SERVICE = OrchestraLiveWebService(PROJECT_DIR.parent)
    return ORCHESTRA_SERVICE


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
    except ModuleNotFoundError:  # pragma: no cover - script launch path
        from providers.contracts import LIVE_SUCCESS, ProviderActivationStatus
        from providers.selector import run_selected_provider

    provider_id = str(payload.get("provider_id", "kimi_chat")).strip() or "kimi_chat"
    model_id = str(payload.get("model_id", "moonshot-v1-8k")).strip() or "moonshot-v1-8k"
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")
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
    }


def route_get_payload(path: str) -> tuple[HTTPStatus, dict[str, object]] | None:
    try:
        human_review_session_id = _human_review_session_id_from_api_path(path)
    except ValueError:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "session identifier is malformed",
        }
    if human_review_session_id is not None:
        try:
            from runtime.epistemic_orchestra.session_view import (
                OrchestraSessionNotFoundError,
            )
        except ModuleNotFoundError:  # pragma: no cover - script launch path
            from epistemic_orchestra.session_view import OrchestraSessionNotFoundError
        try:
            return (
                HTTPStatus.OK,
                get_orchestra_service().get_orchestra_human_review_workspace(
                    human_review_session_id
                ),
            )
        except OrchestraSessionNotFoundError:
            return HTTPStatus.NOT_FOUND, {
                "ok": False,
                "error": "Orchestra session was not found",
            }
        except (TypeError, ValueError, RuntimeError):
            return HTTPStatus.CONFLICT, {
                "ok": False,
                "error": "Orchestra human review evidence is unavailable",
            }
    try:
        session_id = _session_id_from_api_path(path)
    except ValueError:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "error": "session identifier is malformed",
        }
    if session_id is not None:
        try:
            from runtime.epistemic_orchestra.session_view import (
                OrchestraSessionNotFoundError,
            )
        except ModuleNotFoundError:  # pragma: no cover - script launch path
            from epistemic_orchestra.session_view import OrchestraSessionNotFoundError
        try:
            return HTTPStatus.OK, get_orchestra_service().get_orchestra_session_view(
                session_id
            )
        except OrchestraSessionNotFoundError:
            return HTTPStatus.NOT_FOUND, {
                "ok": False,
                "error": "Orchestra session was not found",
            }
        except (TypeError, ValueError, RuntimeError):
            return HTTPStatus.CONFLICT, {
                "ok": False,
                "error": "Orchestra session evidence is unavailable",
            }
    if path == "/api/provider-connections":
        return HTTPStatus.OK, get_orchestra_service().list_connections()
    if path == "/api/model-profiles":
        return HTTPStatus.OK, get_orchestra_service().list_model_profiles()
    if path == "/api/orchestra/models":
        return HTTPStatus.OK, get_orchestra_service().list_orchestra_models()
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
    if path in SENSITIVE_ORCHESTRA_API_PATHS:
        try:
            service = get_orchestra_service()
            if path == "/api/provider-connections":
                return HTTPStatus.CREATED, service.create_connection(payload)
            if path == "/api/provider-connections/disable":
                return HTTPStatus.OK, service.disable_connection(payload)
            if path == "/api/provider-connections/test":
                return HTTPStatus.OK, service.test_connection(payload)
            if path == "/api/model-profiles":
                return HTTPStatus.CREATED, service.create_model_profile(payload)
            if path == "/api/model-profiles/disable":
                return HTTPStatus.OK, service.disable_model_profile(payload)
            if path == "/api/orchestra/preview":
                return HTTPStatus.OK, service.create_preview(payload)
            if path == "/api/orchestra/run":
                return HTTPStatus.OK, service.run_preview(payload)
        except (TypeError, ValueError, RuntimeError) as error:
            try:
                from runtime.providers.redaction import redact_provider_text
            except ModuleNotFoundError:  # pragma: no cover - script launch path
                from providers.redaction import redact_provider_text

            return HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": redact_provider_text(error)[:500],
            }
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


class CodexStyleHandler(SimpleHTTPRequestHandler):
    """Serve the static UI and a small JSON API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if _is_sensitive_orchestra_get_path(parsed.path) and not self._local_request_allowed():
            self._write_json(
                HTTPStatus.FORBIDDEN,
                {"ok": False, "error": "Loopback-local request required"},
            )
            return
        if parsed.path == "/api/memory-hats":
            self._write_json(HTTPStatus.OK, get_memory_hat_payload())
            return
        routed = route_get_payload(parsed.path)
        if routed is not None:
            status, payload = routed
            self._write_json(status, payload)
            return
        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        sensitive_request = parsed.path in SENSITIVE_ORCHESTRA_API_PATHS
        if sensitive_request:
            if not self._local_request_allowed() or not self._same_origin_request_allowed():
                self._write_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "error": "Same-origin local request required"},
                )
                return
            content_type = self.headers.get("Content-Type", "")
            if content_type.split(";", 1)[0].strip().casefold() != "application/json":
                self._write_json(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                    {"ok": False, "error": "Content-Type must be application/json"},
                )
                return
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            if parsed.path == "/api/router/preview":
                status, response = route_post_payload(parsed.path, payload)
                self._write_json(status, response)
                return

            if parsed.path == "/api/operator/chat":
                status, response = route_post_payload(parsed.path, payload)
                self._write_json(status, response)
                return

            if sensitive_request:
                status, response = route_post_payload(parsed.path, payload)
                self._write_json(status, response)
                return

            if parsed.path == "/api/cpt/transform":
                prompt = payload.get("prompt", "")
                mode = payload.get("mode", CPT_BALANCED_MODE)
                if mode is None:
                    mode = CPT_BALANCED_MODE
                try:
                    response = build_cpt_transform_payload(prompt=prompt, mode=mode)
                except (TypeError, ValueError) as error:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
                    return
                self._write_json(HTTPStatus.OK, response)
                return

            if parsed.path == "/api/chat":
                prompt = str(payload.get("prompt", "")).strip()
                if not prompt:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "prompt is required"})
                    return
                self._write_json(HTTPStatus.OK, get_service().run_prompt(prompt))
                return

            if parsed.path == "/api/model":
                model_name = str(payload.get("model", "")).strip()
                if not model_name:
                    self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "model is required"})
                    return
                self._write_json(HTTPStatus.OK, get_service().switch_model(model_name))
                return

            if parsed.path == "/api/model-selection/propose":
                from model_router import create_model_selection_proposal, evaluate_model_selection_policy

                provider_id = str(payload.get("provider_id", "")).strip()
                model_id = str(payload.get("model_id", "")).strip()
                task_sensitivity = str(payload.get("task_sensitivity", "")).strip()
                user_prompt = str(payload.get("user_prompt", ""))
                if not provider_id or not model_id or not task_sensitivity:
                    self._write_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "provider_id, model_id, and task_sensitivity are required"},
                    )
                    return
                proposal = create_model_selection_proposal(
                    provider_id=provider_id,
                    model_id=model_id,
                    task_sensitivity=task_sensitivity,
                    user_prompt=user_prompt,
                )
                decision = evaluate_model_selection_policy(proposal=proposal)
                self._write_json(
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
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})
        except Exception as error:  # pragma: no cover - local debugging path
            if sensitive_request:
                self._write_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "error": "Sensitive request failed safely"},
                )
                return
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "error": str(error),
                    "traceback": traceback.format_exc(),
                },
            )

    def log_message(self, format: str, *args) -> None:
        return

    def _read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except (TypeError, ValueError):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "Invalid Content-Length"},
            )
            return None
        if length < 0 or length > MAXIMUM_JSON_BODY_BYTES:
            self._write_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"ok": False, "error": "JSON request body is too large"},
            )
            return None
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Invalid JSON body"})
            return None
        if not isinstance(payload, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "JSON request body must be an object"},
            )
            return None
        return payload

    def _same_origin_request_allowed(self) -> bool:
        fetch_site = self.headers.get("Sec-Fetch-Site", "")
        if fetch_site and fetch_site.casefold() != "same-origin":
            return False
        origin = self.headers.get("Origin", "")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        parsed_origin = urlparse(origin)
        return (
            parsed_origin.scheme in {"http", "https"}
            and bool(host)
            and parsed_origin.netloc.casefold() == host.casefold()
            and self._loopback_host_allowed(host)
            and not parsed_origin.username
            and not parsed_origin.password
        )

    def _local_request_allowed(self) -> bool:
        try:
            client_host = self.client_address[0]
        except (AttributeError, IndexError, TypeError):
            return False
        try:
            if not ipaddress.ip_address(client_host).is_loopback:
                return False
        except ValueError:
            return False
        return self._loopback_host_allowed(self.headers.get("Host", ""))

    @staticmethod
    def _loopback_host_allowed(host_header: str) -> bool:
        if not isinstance(host_header, str) or not host_header.strip():
            return False
        value = host_header.strip()
        if value.startswith("["):
            closing = value.find("]")
            if closing < 0:
                return False
            hostname = value[1:closing]
            suffix = value[closing + 1 :]
            if suffix and (not suffix.startswith(":") or not suffix[1:].isdigit()):
                return False
        else:
            if value.count(":") > 1:
                return False
            hostname, separator, port = value.rpartition(":")
            if not separator:
                hostname = value
            elif not hostname or not port.isdigit():
                return False
        normalized = hostname.rstrip(".").casefold()
        if normalized == "localhost":
            return True
        try:
            return ipaddress.ip_address(normalized).is_loopback
        except ValueError:
            return False

    def _write_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), CodexStyleHandler)
    print(f"App222 web UI running on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
