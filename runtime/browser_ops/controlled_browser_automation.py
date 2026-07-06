from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Mapping

from runtime.browser_ops.browser_automation_governance import (
    BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY,
    evaluate_browser_automation_governance,
)
from runtime.browser_ops.browser_automation_preview import (
    BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY,
    create_browser_automation_preview,
)
from runtime.browser_ops.controlled_browser_read import (
    CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED,
    compute_browser_read_source_hash,
    compute_browser_read_text_hash,
)


CONTROLLED_BROWSER_AUTOMATION_SCHEMA_VERSION = "AOIA_CONTROLLED_BROWSER_AUTOMATION_1A"
BROWSER_AUTOMATION_EXECUTION_CONTEXT_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_EXECUTION_CONTEXT_1A"
BROWSER_AUTOMATION_HUMAN_BARRIER_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_HUMAN_BARRIER_1A"

CONTROLLED_BROWSER_AUTOMATION_SIMULATED = "CONTROLLED_BROWSER_AUTOMATION_SIMULATED"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED"

CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED = "CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MALFORMED_EVIDENCE = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MALFORMED_EVIDENCE"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_STALE_EVIDENCE = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_STALE_EVIDENCE"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MISSING_HUMAN_BARRIER = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MISSING_HUMAN_BARRIER"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_HASH_MISMATCH = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_HASH_MISMATCH"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_SCOPE_MISMATCH = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_SCOPE_MISMATCH"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_OFFLINE_CONTEXT = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_OFFLINE_CONTEXT"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_READ_NOT_READY = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_READ_NOT_READY"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSUPPORTED_ACTION = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSUPPORTED_ACTION"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_ACTION = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_ACTION"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_EFFECT_EVIDENCE = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_EFFECT_EVIDENCE"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSAFE_HTML = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSAFE_HTML"
CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_JSON_SERIALIZABLE = "CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_JSON_SERIALIZABLE"

_ALLOWED_ACTIONS = frozenset({"click", "read_snapshot", "type", "wait_for_selector"})
_BLOCKED_ACTIONS = frozenset(
    {
        "download",
        "follow_link",
        "navigate",
        "set_cookie",
        "set_storage",
        "submit",
        "submit_form",
        "upload",
    }
)
_SUPPORTED_ACTIONS = _ALLOWED_ACTIONS | _BLOCKED_ACTIONS
_HEX = frozenset("0123456789abcdef")
_MAX_HTML_CHARS = 200_000
_MAX_TEXT = 1024
_MAX_COLLECTION_ITEMS = 64
_MAX_DEPTH = 6
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "authority",
        "authority_granted",
        "human_approved",
        "can_browse",
        "can_click",
        "can_type",
        "can_submit",
        "can_navigate",
        "can_download",
        "can_upload",
        "can_execute",
        "can_write",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "human_barrier_satisfied",
        "governance_passed",
        "execution_allowed",
        "future_browser_action_authorized",
    }
)
_EFFECT_FIELD_NAMES = frozenset(
    {
        "browser_opened",
        "browser_action_performed",
        "network_called",
        "remote_resource_loaded",
        "javascript_executed",
        "link_followed",
        "navigation_performed",
        "form_submitted",
        "download_performed",
        "upload_performed",
        "cookie_mutated",
        "storage_mutated",
        "file_written",
        "provider_called",
        "git_action_performed",
        "package_installed",
        "approval_created",
    }
)
_REMOTE_OR_SPECIAL_PREFIXES = ("http://", "https://", "//", "javascript:", "data:", "file:", "about:", "chrome:")
_UNSAFE_ELEMENTS = frozenset({"script", "iframe", "object", "embed", "form", "input", "button", "select", "textarea"})
_REMOTE_RESOURCE_ATTRIBUTES = frozenset({"src", "srcset", "action", "formaction", "poster"})


@dataclass(frozen=True)
class ControlledBrowserAutomationContext:
    schema_version: str
    current_tick: int
    sandbox_root: str
    offline_mode: bool
    network_disabled: bool
    browser_launch_disabled: bool
    javascript_disabled: bool
    storage_mutation_disabled: bool
    file_write_disabled: bool
    live_navigation_disabled: bool
    download_upload_disabled: bool
    context_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "current_tick", _nonnegative_int("current_tick", self.current_tick))
        object.__setattr__(self, "sandbox_root", _required_text("sandbox_root", self.sandbox_root))
        object.__setattr__(self, "context_hash", _required_hash("context_hash", self.context_hash))
        if self.schema_version != BROWSER_AUTOMATION_EXECUTION_CONTEXT_SCHEMA_VERSION:
            raise ValueError("unsupported controlled browser automation context schema version")
        for field_name in (
            "offline_mode",
            "network_disabled",
            "browser_launch_disabled",
            "javascript_disabled",
            "storage_mutation_disabled",
            "file_write_disabled",
            "live_navigation_disabled",
            "download_upload_disabled",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "current_tick": self.current_tick,
            "sandbox_root": self.sandbox_root,
            "offline_mode": self.offline_mode,
            "network_disabled": self.network_disabled,
            "browser_launch_disabled": self.browser_launch_disabled,
            "javascript_disabled": self.javascript_disabled,
            "storage_mutation_disabled": self.storage_mutation_disabled,
            "file_write_disabled": self.file_write_disabled,
            "live_navigation_disabled": self.live_navigation_disabled,
            "download_upload_disabled": self.download_upload_disabled,
            "context_hash": self.context_hash,
        }


@dataclass(frozen=True)
class BrowserAutomationHumanBarrier:
    schema_version: str
    browser_read_result_hash: str
    preview_hash: str
    request_hash: str
    governance_hash: str
    context_hash: str
    source_hash: str
    approved_step_hashes: tuple[str, ...]
    approved_actions: tuple[str, ...]
    approved_by: str
    approval_reason: str
    approved_at: int
    expires_at: int
    barrier_hash: str
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_browse: bool = False
    can_click: bool = False
    can_type: bool = False
    can_submit: bool = False
    can_navigate: bool = False
    can_download: bool = False
    can_upload: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    future_browser_action_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "browser_read_result_hash", _required_hash("browser_read_result_hash", self.browser_read_result_hash))
        object.__setattr__(self, "preview_hash", _required_hash("preview_hash", self.preview_hash))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "governance_hash", _required_hash("governance_hash", self.governance_hash))
        object.__setattr__(self, "context_hash", _required_hash("context_hash", self.context_hash))
        object.__setattr__(self, "source_hash", _required_hash("source_hash", self.source_hash))
        object.__setattr__(self, "approved_step_hashes", _hash_tuple("approved_step_hashes", self.approved_step_hashes))
        object.__setattr__(self, "approved_actions", _text_tuple("approved_actions", self.approved_actions))
        object.__setattr__(self, "approved_by", _required_text("approved_by", self.approved_by))
        object.__setattr__(self, "approval_reason", _required_text("approval_reason", self.approval_reason))
        object.__setattr__(self, "approved_at", _nonnegative_int("approved_at", self.approved_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "barrier_hash", _required_hash("barrier_hash", self.barrier_hash))
        if self.schema_version != BROWSER_AUTOMATION_HUMAN_BARRIER_SCHEMA_VERSION:
            raise ValueError("unsupported browser automation human barrier schema version")
        if self.expires_at < self.approved_at:
            raise ValueError("browser automation human barrier TTL is inverted")
        for field_name in (
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_browse",
            "can_click",
            "can_type",
            "can_submit",
            "can_navigate",
            "can_download",
            "can_upload",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "browser_read_result_hash": self.browser_read_result_hash,
            "preview_hash": self.preview_hash,
            "request_hash": self.request_hash,
            "governance_hash": self.governance_hash,
            "context_hash": self.context_hash,
            "source_hash": self.source_hash,
            "approved_step_hashes": self.approved_step_hashes,
            "approved_actions": self.approved_actions,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "barrier_hash": self.barrier_hash,
        }
        for field_name in (
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_browse",
            "can_click",
            "can_type",
            "can_submit",
            "can_navigate",
            "can_download",
            "can_upload",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            data[field_name] = False
        return data


@dataclass(frozen=True)
class ControlledBrowserAutomationResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    browser_read_result_hash: str | None
    preview_hash: str | None
    request_hash: str | None
    governance_hash: str | None
    context_hash: str | None
    barrier_hash: str | None
    source_hash: str | None
    step_hashes: tuple[str, ...]
    action_labels: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    selected_link_targets: tuple[str, ...]
    typed_fields: tuple[tuple[str, str], ...]
    selected_options: tuple[tuple[str, str], ...]
    selector_checks: tuple[tuple[str, bool], ...]
    text_hash: str | None
    links: tuple[str, ...]
    before_state_hash: str | None
    after_state_hash: str | None
    result_hash: str
    simulation_performed: bool = False
    browser_opened: bool = False
    browser_action_performed: bool = False
    network_called: bool = False
    remote_resource_loaded: bool = False
    javascript_executed: bool = False
    link_followed: bool = False
    navigation_performed: bool = False
    form_submitted: bool = False
    download_performed: bool = False
    upload_performed: bool = False
    cookie_mutated: bool = False
    storage_mutated: bool = False
    file_written: bool = False
    provider_called: bool = False
    git_action_performed: bool = False
    package_installed: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_browse: bool = False
    can_click: bool = False
    can_type: bool = False
    can_submit: bool = False
    can_navigate: bool = False
    can_download: bool = False
    can_upload: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    future_browser_action_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", CONTROLLED_BROWSER_AUTOMATION_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "step_hashes", tuple(self.step_hashes))
        object.__setattr__(self, "action_labels", tuple(self.action_labels))
        object.__setattr__(self, "blocked_actions", tuple(sorted(set(self.blocked_actions))))
        object.__setattr__(self, "selected_link_targets", tuple(self.selected_link_targets))
        object.__setattr__(self, "typed_fields", tuple(tuple(item) for item in self.typed_fields))
        object.__setattr__(self, "selected_options", tuple(tuple(item) for item in self.selected_options))
        object.__setattr__(self, "selector_checks", tuple(tuple(item) for item in self.selector_checks))
        object.__setattr__(self, "links", tuple(self.links))
        if self.status not in {CONTROLLED_BROWSER_AUTOMATION_SIMULATED, CONTROLLED_BROWSER_AUTOMATION_BLOCKED}:
            raise ValueError("unsupported controlled browser automation status")
        if not _sha256_like(self.result_hash):
            raise ValueError("result_hash must be a sha256 hex digest")
        object.__setattr__(self, "simulation_performed", self.status == CONTROLLED_BROWSER_AUTOMATION_SIMULATED)
        for field_name in (*_EFFECT_FIELD_NAMES, *_AUTHORITY_FIELD_NAMES, "can_type", "can_submit", "can_navigate", "can_upload"):
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": CONTROLLED_BROWSER_AUTOMATION_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "browser_read_result_hash": self.browser_read_result_hash,
            "preview_hash": self.preview_hash,
            "request_hash": self.request_hash,
            "governance_hash": self.governance_hash,
            "context_hash": self.context_hash,
            "barrier_hash": self.barrier_hash,
            "source_hash": self.source_hash,
            "step_hashes": self.step_hashes,
            "action_labels": self.action_labels,
            "blocked_actions": self.blocked_actions,
            "selected_link_targets": self.selected_link_targets,
            "typed_fields": self.typed_fields,
            "selected_options": self.selected_options,
            "selector_checks": self.selector_checks,
            "text_hash": self.text_hash,
            "links": self.links,
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "result_hash": self.result_hash,
            "simulation_performed": self.simulation_performed,
        }
        for field_name in (
            *_EFFECT_FIELD_NAMES,
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_browse",
            "can_click",
            "can_type",
            "can_submit",
            "can_navigate",
            "can_download",
            "can_upload",
            "can_execute",
            "can_write",
            "can_call_provider",
            "can_change_gate",
            "future_browser_action_authorized",
        ):
            data[field_name] = False
        return data


def create_controlled_browser_automation_context(
    *,
    current_tick: int,
    sandbox_root: str,
    offline_mode: bool = True,
    network_disabled: bool = True,
    browser_launch_disabled: bool = True,
    javascript_disabled: bool = True,
    storage_mutation_disabled: bool = True,
    file_write_disabled: bool = True,
    live_navigation_disabled: bool = True,
    download_upload_disabled: bool = True,
) -> ControlledBrowserAutomationContext:
    material = {
        "schema_version": BROWSER_AUTOMATION_EXECUTION_CONTEXT_SCHEMA_VERSION,
        "current_tick": _nonnegative_int("current_tick", current_tick),
        "sandbox_root": _required_text("sandbox_root", sandbox_root),
        "offline_mode": bool(offline_mode),
        "network_disabled": bool(network_disabled),
        "browser_launch_disabled": bool(browser_launch_disabled),
        "javascript_disabled": bool(javascript_disabled),
        "storage_mutation_disabled": bool(storage_mutation_disabled),
        "file_write_disabled": bool(file_write_disabled),
        "live_navigation_disabled": bool(live_navigation_disabled),
        "download_upload_disabled": bool(download_upload_disabled),
    }
    return ControlledBrowserAutomationContext(**material, context_hash=compute_controlled_browser_automation_context_hash(material))


def create_browser_automation_human_barrier(
    *,
    browser_read_result_hash: str,
    preview_hash: str,
    request_hash: str,
    governance_hash: str,
    context_hash: str,
    source_hash: str,
    approved_step_hashes: tuple[str, ...],
    approved_actions: tuple[str, ...],
    approved_by: str,
    approval_reason: str,
    approved_at: int,
    expires_at: int,
) -> BrowserAutomationHumanBarrier:
    material = {
        "schema_version": BROWSER_AUTOMATION_HUMAN_BARRIER_SCHEMA_VERSION,
        "browser_read_result_hash": _required_hash("browser_read_result_hash", browser_read_result_hash),
        "preview_hash": _required_hash("preview_hash", preview_hash),
        "request_hash": _required_hash("request_hash", request_hash),
        "governance_hash": _required_hash("governance_hash", governance_hash),
        "context_hash": _required_hash("context_hash", context_hash),
        "source_hash": _required_hash("source_hash", source_hash),
        "approved_step_hashes": _hash_tuple("approved_step_hashes", approved_step_hashes),
        "approved_actions": _text_tuple("approved_actions", approved_actions),
        "approved_by": _required_text("approved_by", approved_by),
        "approval_reason": _required_text("approval_reason", approval_reason),
        "approved_at": _nonnegative_int("approved_at", approved_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return BrowserAutomationHumanBarrier(**material, barrier_hash=compute_browser_automation_barrier_hash(material))


def execute_controlled_browser_automation(
    *,
    browser_read_result: object,
    preview_result: object,
    preview_request: object,
    governance_result: object,
    context: object,
    human_barrier: object,
    html_snapshot: object,
) -> ControlledBrowserAutomationResult:
    if human_barrier is None:
        return _blocked((CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MISSING_HUMAN_BARRIER,))
    try:
        html_text = _html_snapshot_text(html_snapshot)
        read_data = _coerce_mapping(browser_read_result)
        preview_data = _coerce_mapping(preview_result)
        request_data = _coerce_mapping(preview_request)
        governance_data = _coerce_mapping(governance_result)
        automation_context = _coerce_context(context)
        barrier = _coerce_barrier(human_barrier)
        input_fingerprint = _json_fingerprint(
            {
                "browser_read_result": read_data,
                "preview_result": preview_data,
                "preview_request": request_data,
                "governance_result": governance_data,
                "context": automation_context.to_dict(),
                "human_barrier": barrier.to_dict(),
                "source_hash": compute_browser_read_source_hash(html_text),
            }
        )
    except TypeError:
        return _blocked((CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_JSON_SERIALIZABLE,))
    except (ValueError, AttributeError):
        return _blocked((CONTROLLED_BROWSER_AUTOMATION_BLOCKED_MALFORMED_EVIDENCE,))

    reason_codes: list[str] = []
    source_hash = compute_browser_read_source_hash(html_text)
    context_hash = compute_controlled_browser_automation_context_hash(_context_hash_material(automation_context))
    action_labels = _action_labels(request_data)
    step_hashes = _hashes_from_request(request_data)
    blocked_actions = tuple(action for action in action_labels if action in _BLOCKED_ACTIONS)
    unsupported_actions = tuple(action for action in action_labels if action not in _SUPPORTED_ACTIONS)
    if blocked_actions:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_ACTION)
    if unsupported_actions:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSUPPORTED_ACTION)
    if not _context_is_offline(automation_context):
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_NON_OFFLINE_CONTEXT)
    if context_hash != automation_context.context_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if _authority_claim_present(read_data) or _authority_claim_present(preview_data) or _authority_claim_present(governance_data):
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_AUTHORITY_CLAIM)
    if _effect_claim_present(read_data) or _effect_claim_present(preview_data) or _effect_claim_present(governance_data):
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_EFFECT_EVIDENCE)

    if read_data.get("status") != CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED or read_data.get("snapshot_created") is not True:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_READ_NOT_READY)
    if read_data.get("source_hash") != source_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if preview_data.get("status") != BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY)
    if governance_data.get("status") != BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY)

    parsed = _parse_snapshot(html_text)
    if parsed.unsafe:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_UNSAFE_HTML)
    if read_data.get("text_hash") is not None and read_data.get("text_hash") != parsed.text_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if tuple(read_data.get("links") or ()) != parsed.links:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)

    recomputed_preview = create_browser_automation_preview(request_data, now_tick=automation_context.current_tick)
    recomputed_governance = evaluate_browser_automation_governance(
        preview_result=preview_data,
        preview_request=request_data,
        now_tick=automation_context.current_tick,
    )
    if preview_data.get("preview_hash") != recomputed_preview.preview_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if governance_data.get("governance_hash") != recomputed_governance.governance_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if recomputed_preview.status != BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_PREVIEW_NOT_READY)
    if recomputed_governance.status != BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_GOVERNANCE_NOT_READY)
    if preview_data.get("request_hash") != request_data.get("request_hash"):
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if preview_data.get("browser_read_result_hash") != read_data.get("result_hash"):
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if preview_data.get("source_hash") != source_hash or governance_data.get("source_hash") != source_hash:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)
    if tuple(preview_data.get("step_hashes") or ()) != step_hashes or tuple(governance_data.get("step_hashes") or ()) != step_hashes:
        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_HASH_MISMATCH)

    reason_codes.extend(
        _barrier_reason_codes(
            barrier=barrier,
            browser_read_result_hash=_optional_hash("read result hash", read_data.get("result_hash")),
            preview_hash=_optional_hash("preview hash", preview_data.get("preview_hash")),
            request_hash=_optional_hash("request hash", request_data.get("request_hash")),
            governance_hash=_optional_hash("governance hash", governance_data.get("governance_hash")),
            context_hash=context_hash,
            source_hash=source_hash,
            step_hashes=step_hashes,
            action_labels=action_labels,
            current_tick=automation_context.current_tick,
        )
    )

    before_state = {
        "source_hash": source_hash,
        "text_hash": parsed.text_hash,
        "links": parsed.links,
        "form_state": (),
        "selected_link_targets": (),
    }
    before_state_hash = _stable_hash(before_state)
    selected_link_targets: list[str] = []
    typed_fields: list[tuple[str, str]] = []
    selected_options: list[tuple[str, str]] = []
    selector_checks: list[tuple[str, bool]] = []
    if not reason_codes:
        for step in _steps_from_request(request_data):
            action = step["action"]
            target = step["target"]
            value = step.get("value")
            if action == "click":
                found = parsed.has_selector(target)
                selector_checks.append((target, found))
                if not found:
                    reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND)
                    continue
                href = parsed.link_target(target)
                if href is not None:
                    selected_link_targets.append(href)
            elif action == "type":
                field = parsed.control(target)
                if field is None or value is None:
                    reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND)
                    continue
                if field.control_kind == "select":
                    if value not in field.option_values:
                        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND)
                    else:
                        selected_options.append((field.control_name, value))
                else:
                    typed_fields.append((field.control_name, value))
            elif action == "wait_for_selector":
                found = parsed.has_selector(target)
                selector_checks.append((target, found))
                if not found:
                    reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND)
            elif action == "read_snapshot":
                if target not in {"document", "snapshot"}:
                    found = parsed.has_selector(target)
                    selector_checks.append((target, found))
                    if not found:
                        reason_codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_SELECTOR_NOT_FOUND)

    after_state = {
        "source_hash": source_hash,
        "text_hash": parsed.text_hash,
        "links": parsed.links,
        "typed_fields": tuple(typed_fields),
        "selected_options": tuple(selected_options),
        "selected_link_targets": tuple(selected_link_targets),
        "selector_checks": tuple(selector_checks),
    }
    after_state_hash = _stable_hash(after_state)
    if not reason_codes:
        reason_codes = [CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED]
    status = CONTROLLED_BROWSER_AUTOMATION_SIMULATED
    if reason_codes != [CONTROLLED_BROWSER_AUTOMATION_REASON_SIMULATED]:
        status = CONTROLLED_BROWSER_AUTOMATION_BLOCKED
    return _result(
        status=status,
        reason_codes=tuple(reason_codes),
        browser_read_result_hash=_optional_hash("browser_read_result_hash", read_data.get("result_hash")),
        preview_hash=_optional_hash("preview_hash", preview_data.get("preview_hash")),
        request_hash=_optional_hash("request_hash", request_data.get("request_hash")),
        governance_hash=_optional_hash("governance_hash", governance_data.get("governance_hash")),
        context_hash=context_hash,
        barrier_hash=barrier.barrier_hash,
        source_hash=source_hash,
        step_hashes=step_hashes,
        action_labels=action_labels,
        blocked_actions=tuple(blocked_actions + unsupported_actions),
        selected_link_targets=tuple(selected_link_targets),
        typed_fields=tuple(typed_fields),
        selected_options=tuple(selected_options),
        selector_checks=tuple(selector_checks),
        text_hash=parsed.text_hash,
        links=parsed.links,
        before_state_hash=before_state_hash,
        after_state_hash=after_state_hash,
        input_fingerprint=input_fingerprint,
    )


def compute_controlled_browser_automation_context_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("context_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_browser_automation_barrier_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FIELD_NAMES:
        data.pop(field_name, None)
    return _stable_hash(_json_fingerprint(data))


def canonical_controlled_browser_automation_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _barrier_reason_codes(
    *,
    barrier: BrowserAutomationHumanBarrier,
    browser_read_result_hash: str | None,
    preview_hash: str | None,
    request_hash: str | None,
    governance_hash: str | None,
    context_hash: str,
    source_hash: str,
    step_hashes: tuple[str, ...],
    action_labels: tuple[str, ...],
    current_tick: int,
) -> tuple[str, ...]:
    codes: list[str] = []
    if barrier.barrier_hash != compute_browser_automation_barrier_hash(_barrier_hash_material(barrier)):
        codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_HASH_MISMATCH)
    if current_tick < barrier.approved_at or current_tick > barrier.expires_at:
        codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_STALE_EVIDENCE)
    if (
        barrier.browser_read_result_hash != browser_read_result_hash
        or barrier.preview_hash != preview_hash
        or barrier.request_hash != request_hash
        or barrier.governance_hash != governance_hash
        or barrier.context_hash != context_hash
        or barrier.source_hash != source_hash
        or barrier.approved_step_hashes != step_hashes
        or barrier.approved_actions != tuple(sorted(set(action_labels)))
    ):
        codes.append(CONTROLLED_BROWSER_AUTOMATION_BLOCKED_BARRIER_SCOPE_MISMATCH)
    return tuple(codes)


def _context_is_offline(context: ControlledBrowserAutomationContext) -> bool:
    return (
        context.offline_mode is True
        and context.network_disabled is True
        and context.browser_launch_disabled is True
        and context.javascript_disabled is True
        and context.storage_mutation_disabled is True
        and context.file_write_disabled is True
        and context.live_navigation_disabled is True
        and context.download_upload_disabled is True
    )


def _context_hash_material(context: ControlledBrowserAutomationContext) -> dict[str, Any]:
    data = context.to_dict()
    data.pop("context_hash", None)
    return data


def _barrier_hash_material(barrier: BrowserAutomationHumanBarrier) -> dict[str, Any]:
    data = barrier.to_dict()
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FIELD_NAMES:
        data.pop(field_name, None)
    return data


def _steps_from_request(request_data: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    steps = request_data.get("steps")
    if not isinstance(steps, (tuple, list)) or not steps:
        raise ValueError("controlled browser automation requires step evidence")
    normalized: list[dict[str, Any]] = []
    for item in steps:
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            raise TypeError("controlled browser automation step must be mapping evidence")
        action = _required_text("action", item.get("action")).casefold()
        target = _required_text("target", item.get("target"))
        value = item.get("value")
        normalized.append(
            {
                "action": action,
                "target": target,
                "value": None if value is None else _required_text("value", value),
                "step_hash": _required_hash("step_hash", item.get("step_hash")),
            }
        )
    return tuple(normalized)


def _action_labels(request_data: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(step["action"] for step in _steps_from_request(request_data))


def _hashes_from_request(request_data: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(step["step_hash"] for step in _steps_from_request(request_data))


def _parse_snapshot(html_text: str) -> "_AutomationSnapshotParser":
    parser = _AutomationSnapshotParser()
    parser.feed(html_text)
    parser.close()
    return parser


@dataclass(frozen=True)
class _ControlElement:
    control_name: str
    control_kind: str
    option_values: tuple[str, ...]


class _AutomationSnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.unsafe = False
        self._text_parts: list[str] = []
        self._links: list[str] = []
        self._selectors: set[str] = set()
        self._link_targets: dict[str, str] = {}
        self._controls: dict[str, _ControlElement] = {}

    @property
    def visible_text(self) -> str:
        return _normalize_space(" ".join(self._text_parts))

    @property
    def text_hash(self) -> str:
        return compute_browser_read_text_hash(self.visible_text)

    @property
    def links(self) -> tuple[str, ...]:
        return tuple(self._links[:64])

    def has_selector(self, selector: str) -> bool:
        normalized = _selector_key(selector)
        return normalized in self._selectors

    def link_target(self, selector: str) -> str | None:
        return self._link_targets.get(_selector_key(selector))

    def control(self, selector: str) -> _ControlElement | None:
        return self._controls.get(_selector_key(selector))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_element(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_element(tag, attrs)

    def handle_data(self, data: str) -> None:
        self._text_parts.append(data)

    def _handle_element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        attr_map = {name.casefold(): (value or "").strip() for name, value in attrs}
        if normalized_tag in _UNSAFE_ELEMENTS:
            self.unsafe = True
        for name, value in attr_map.items():
            attr_value = value.casefold()
            if name.startswith("on") or name in {"style", "http-equiv"}:
                self.unsafe = True
            if name in _REMOTE_RESOURCE_ATTRIBUTES and attr_value.startswith(_REMOTE_OR_SPECIAL_PREFIXES):
                self.unsafe = True
            if name in {"href", "xlink:href"} and attr_value.startswith(("javascript:", "data:")):
                self.unsafe = True
        selector_names = _selector_names(attr_map)
        self._selectors.update(selector_names)
        if normalized_tag == "a" and attr_map.get("href"):
            href = attr_map["href"]
            self._links.append(href)
            if href.strip().casefold().startswith(_REMOTE_OR_SPECIAL_PREFIXES):
                self.unsafe = True
            for selector in selector_names:
                self._link_targets[selector] = href
        control_kind = attr_map.get("data-aoia-control", "").casefold()
        if control_kind in {"field", "input", "select", "textarea"} and selector_names:
            control_name = attr_map.get("data-aoia-name") or attr_map.get("name") or attr_map.get("id") or tuple(sorted(selector_names))[0]
            option_values = tuple(
                value.strip()
                for value in attr_map.get("data-aoia-options", "").split(",")
                if value.strip()
            )
            element = _ControlElement(
                control_name=control_name,
                control_kind="select" if control_kind == "select" else "field",
                option_values=option_values,
            )
            for selector in selector_names:
                self._controls[selector] = element


def _selector_names(attrs: Mapping[str, str]) -> set[str]:
    selectors: set[str] = set()
    element_id = attrs.get("id")
    if element_id:
        selectors.add(f"#{element_id}")
        selectors.add(element_id)
    for name in ("name", "data-aoia-name", "data-testid"):
        value = attrs.get(name)
        if value:
            selectors.add(value)
            selectors.add(f'[{name}="{value}"]')
    return selectors


def _selector_key(selector: str) -> str:
    return _required_text("selector", selector)


def _html_snapshot_text(value: object) -> str:
    text = _required_text("html_snapshot", value)
    if len(text) > _MAX_HTML_CHARS:
        raise ValueError("html snapshot is too long")
    return text


def _coerce_context(value: object) -> ControlledBrowserAutomationContext:
    if isinstance(value, ControlledBrowserAutomationContext):
        return value
    if isinstance(value, Mapping):
        return ControlledBrowserAutomationContext(**dict(value))
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return ControlledBrowserAutomationContext(**dict(data))
    raise TypeError("controlled browser automation context is required")


def _coerce_barrier(value: object) -> BrowserAutomationHumanBarrier:
    if isinstance(value, BrowserAutomationHumanBarrier):
        return value
    if isinstance(value, Mapping):
        return BrowserAutomationHumanBarrier(**dict(value))
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return BrowserAutomationHumanBarrier(**dict(data))
    raise TypeError("browser automation human barrier is required")


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("controlled browser automation evidence must be mapping evidence")


def _authority_claim_present(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FIELD_NAMES and item is not False:
                return True
            if _authority_claim_present(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_authority_claim_present(item) for item in value)
    return False


def _effect_claim_present(value: Mapping[str, Any]) -> bool:
    return any(value.get(field_name) is True for field_name in _EFFECT_FIELD_NAMES)


def _blocked(reason_codes: tuple[str, ...]) -> ControlledBrowserAutomationResult:
    return _result(
        status=CONTROLLED_BROWSER_AUTOMATION_BLOCKED,
        reason_codes=reason_codes,
        browser_read_result_hash=None,
        preview_hash=None,
        request_hash=None,
        governance_hash=None,
        context_hash=None,
        barrier_hash=None,
        source_hash=None,
        step_hashes=(),
        action_labels=(),
        blocked_actions=(),
        selected_link_targets=(),
        typed_fields=(),
        selected_options=(),
        selector_checks=(),
        text_hash=None,
        links=(),
        before_state_hash=None,
        after_state_hash=None,
        input_fingerprint=None,
    )


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    browser_read_result_hash: str | None,
    preview_hash: str | None,
    request_hash: str | None,
    governance_hash: str | None,
    context_hash: str | None,
    barrier_hash: str | None,
    source_hash: str | None,
    step_hashes: tuple[str, ...],
    action_labels: tuple[str, ...],
    blocked_actions: tuple[str, ...],
    selected_link_targets: tuple[str, ...],
    typed_fields: tuple[tuple[str, str], ...],
    selected_options: tuple[tuple[str, str], ...],
    selector_checks: tuple[tuple[str, bool], ...],
    text_hash: str | None,
    links: tuple[str, ...],
    before_state_hash: str | None,
    after_state_hash: str | None,
    input_fingerprint: Any | None,
) -> ControlledBrowserAutomationResult:
    material = {
        "schema_version": CONTROLLED_BROWSER_AUTOMATION_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "browser_read_result_hash": browser_read_result_hash,
        "preview_hash": preview_hash,
        "request_hash": request_hash,
        "governance_hash": governance_hash,
        "context_hash": context_hash,
        "barrier_hash": barrier_hash,
        "source_hash": source_hash,
        "step_hashes": step_hashes,
        "action_labels": action_labels,
        "blocked_actions": tuple(sorted(set(blocked_actions))),
        "selected_link_targets": selected_link_targets,
        "typed_fields": typed_fields,
        "selected_options": selected_options,
        "selector_checks": selector_checks,
        "text_hash": text_hash,
        "links": links,
        "before_state_hash": before_state_hash,
        "after_state_hash": after_state_hash,
        "input_fingerprint": input_fingerprint,
    }
    return ControlledBrowserAutomationResult(
        schema_version=CONTROLLED_BROWSER_AUTOMATION_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        browser_read_result_hash=browser_read_result_hash,
        preview_hash=preview_hash,
        request_hash=request_hash,
        governance_hash=governance_hash,
        context_hash=context_hash,
        barrier_hash=barrier_hash,
        source_hash=source_hash,
        step_hashes=step_hashes,
        action_labels=action_labels,
        blocked_actions=blocked_actions,
        selected_link_targets=selected_link_targets,
        typed_fields=typed_fields,
        selected_options=selected_options,
        selector_checks=selector_checks,
        text_hash=text_hash,
        links=links,
        before_state_hash=before_state_hash,
        after_state_hash=after_state_hash,
        result_hash=_stable_hash(material),
    )


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_hash(name, value)


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _hash_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(_required_hash(name, item) for item in value)


def _text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(_required_text(name, item).casefold() for item in value)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_TEXT and name != "html_snapshot":
        raise ValueError(f"{name} is too long")
    return value.strip()


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


def _stable_hash(value: object) -> str:
    material = json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("controlled browser automation evidence is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000_000:
            raise TypeError("integer evidence is excessive")
        return value
    if isinstance(value, float):
        raise TypeError("floating point evidence is ambiguous")
    if isinstance(value, str):
        if len(value) > _MAX_HTML_CHARS:
            raise TypeError("text evidence is excessive")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("mapping evidence is excessive")
        return {str(key): _json_fingerprint(item, depth=depth + 1) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("sequence evidence is excessive")
        return tuple(_json_fingerprint(item, depth=depth + 1) for item in value)
    raise TypeError("controlled browser automation evidence must be JSON serializable")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
