from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.browser_ops.browser_automation_preview import (
    BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY,
    BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION,
    BrowserAutomationPreviewResult,
    compute_browser_automation_request_hash,
    compute_browser_automation_step_hash,
    create_browser_automation_preview,
)


BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_GOVERNANCE_1A"
BROWSER_AUTOMATION_GOVERNANCE_POLICY_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_GOVERNANCE_POLICY_1A"

BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY = "BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED"

BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY = "BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_STALE_EVIDENCE = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_STALE_EVIDENCE"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNSUPPORTED_ACTION = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNSUPPORTED_ACTION"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_RISK = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_RISK"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EFFECT_EVIDENCE = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EFFECT_EVIDENCE"
BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_NON_JSON_SERIALIZABLE = "BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_NON_JSON_SERIALIZABLE"

BROWSER_AUTOMATION_GOVERNANCE_RISK_LOW = "LOW"
BROWSER_AUTOMATION_GOVERNANCE_RISK_MEDIUM = "MEDIUM"
BROWSER_AUTOMATION_GOVERNANCE_RISK_HIGH = "HIGH"
BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED = "BLOCKED"

_DEFAULT_ALLOWED_PREVIEW_ACTIONS = ("click", "read_snapshot", "type", "wait_for_selector")
_DEFAULT_BLOCKED_ACTIONS = ("download", "follow_link", "navigate", "set_cookie", "set_storage", "submit", "upload")
_DEFAULT_HIGH_RISK_ACTIONS = _DEFAULT_BLOCKED_ACTIONS
_SUPPORTED_ACTIONS = frozenset((*_DEFAULT_ALLOWED_PREVIEW_ACTIONS, *_DEFAULT_BLOCKED_ACTIONS))
_LOW_RISK_ACTIONS = frozenset({"read_snapshot", "wait_for_selector"})
_MEDIUM_RISK_ACTIONS = frozenset({"click", "type"})
_KNOWN_RISK_CODES = frozenset(
    {
        "BROWSER_AUTOMATION_RISK_CLICK",
        "BROWSER_AUTOMATION_RISK_TYPE",
        "BROWSER_AUTOMATION_RISK_FORM_SUBMIT",
        "BROWSER_AUTOMATION_RISK_NAVIGATION",
        "BROWSER_AUTOMATION_RISK_DOWNLOAD",
        "BROWSER_AUTOMATION_RISK_UPLOAD",
        "BROWSER_AUTOMATION_RISK_COOKIE_MUTATION",
        "BROWSER_AUTOMATION_RISK_STORAGE_MUTATION",
        "BROWSER_AUTOMATION_RISK_WAIT",
        "BROWSER_AUTOMATION_RISK_READ_ONLY",
    }
)
_REQUIRED_FUTURE_EVIDENCE = (
    "exact_preview_hash",
    "exact_request_hash",
    "exact_governance_hash",
    "explicit_hash_bound_human_barrier",
    "controlled_browser_automation_runtime",
)
_ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "preview_id",
        "browser_read_result_hash",
        "source_hash",
        "reason",
        "requested_by",
        "created_at_tick",
        "expires_at_tick",
        "steps",
        "metadata",
        "request_hash",
    }
)
_ALLOWED_PREVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "reason_codes",
        "risk_codes",
        "preview_id",
        "browser_read_result_hash",
        "source_hash",
        "step_hashes",
        "request_hash",
        "preview_hash",
        "human_review_required",
        "future_governance_required",
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
        "gate_satisfied",
        "human_barrier_satisfied",
        "can_browse",
        "can_click",
        "can_download",
        "can_execute",
        "can_write",
        "can_call_provider",
        "can_change_gate",
        "future_browser_action_authorized",
    }
)
_ALLOWED_STEP_FIELDS = frozenset({"schema_version", "action", "target", "value", "description", "step_hash"})
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
        "can_download",
        "can_execute",
        "can_write",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "governance_passed",
        "browser_automation_allowed",
        "execution_allowed",
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
_DANGEROUS_FIELD_NAMES = frozenset(
    {
        "command",
        "commands",
        "script",
        "javascript",
        "js",
        "driver",
        "browser_driver",
        "network",
        "http",
        "headers",
        "token",
        "secret",
        "env",
    }
)
_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 1024
_MAX_COLLECTION_ITEMS = 48
_MAX_DEPTH = 5
_EXECUTABLE_TEXT_PATTERN = re.compile(
    r"(?i)(?:\b(?:selenium|playwright|webdriver|webbrowser|chromedriver|geckodriver)\b|"
    r"\b(?:fetch|xmlhttprequest|eval|exec|function\s*\(|settimeout|setinterval)\b|"
    r"\b(?:curl|wget|bash|sh|sudo|powershell|cmd\.exe)\b|"
    r"\b(?:python\s+-m|pip|npm|apt|git)\s+\w+\b|"
    r"(?:;|&&|\|\||`|\$\(|<\(|>\(|\n))"
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"safe\s+to\s+(?:browse|click|execute|download)|can\s+(?:browse|click|execute|download)|"
    r"gate\s+satisfied|authority\s+granted|governance\s+passed)\b"
)


@dataclass(frozen=True)
class BrowserAutomationGovernancePolicy:
    schema_version: str
    policy_id: str
    allowed_preview_actions: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    high_risk_actions: tuple[str, ...]
    max_steps: int
    requires_human_review: bool
    requires_step47_controlled_execution: bool
    policy_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "policy_id", _required_text("policy_id", self.policy_id))
        object.__setattr__(self, "allowed_preview_actions", _text_tuple("allowed_preview_actions", self.allowed_preview_actions))
        object.__setattr__(self, "blocked_actions", _text_tuple("blocked_actions", self.blocked_actions))
        object.__setattr__(self, "high_risk_actions", _text_tuple("high_risk_actions", self.high_risk_actions))
        object.__setattr__(self, "max_steps", _positive_int("max_steps", self.max_steps))
        object.__setattr__(self, "policy_hash", _required_hash("policy_hash", self.policy_hash))
        if self.schema_version != BROWSER_AUTOMATION_GOVERNANCE_POLICY_SCHEMA_VERSION:
            raise ValueError("unsupported browser automation governance policy schema version")
        for field_name in ("requires_human_review", "requires_step47_controlled_execution"):
            if getattr(self, field_name) is not True:
                raise ValueError(f"{field_name} must be true")
        if set(self.allowed_preview_actions) & set(self.blocked_actions):
            raise ValueError("allowed and blocked browser automation actions must be disjoint")
        if set(self.high_risk_actions) - set(self.blocked_actions):
            raise ValueError("high risk browser automation actions must be blocked in this policy")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "allowed_preview_actions": self.allowed_preview_actions,
            "blocked_actions": self.blocked_actions,
            "high_risk_actions": self.high_risk_actions,
            "max_steps": self.max_steps,
            "requires_human_review": True,
            "requires_step47_controlled_execution": True,
            "policy_hash": self.policy_hash,
        }


@dataclass(frozen=True)
class BrowserAutomationGovernanceResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    risk_tier: str
    preview_id: str | None
    preview_hash: str | None
    request_hash: str | None
    browser_read_result_hash: str | None
    source_hash: str | None
    step_hashes: tuple[str, ...]
    risk_codes: tuple[str, ...]
    action_labels: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    allowed_for_future_review_actions: tuple[str, ...]
    required_future_evidence: tuple[str, ...]
    policy_hash: str
    governance_hash: str
    human_review_required: bool = True
    requires_step47_controlled_execution: bool = True
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
    governance_passed: bool = False
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
        object.__setattr__(self, "schema_version", BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "step_hashes", tuple(self.step_hashes))
        object.__setattr__(self, "risk_codes", tuple(sorted(set(self.risk_codes))))
        object.__setattr__(self, "action_labels", tuple(sorted(set(self.action_labels))))
        object.__setattr__(self, "blocked_actions", tuple(sorted(set(self.blocked_actions))))
        object.__setattr__(
            self,
            "allowed_for_future_review_actions",
            tuple(sorted(set(self.allowed_for_future_review_actions))),
        )
        object.__setattr__(self, "required_future_evidence", tuple(sorted(set(self.required_future_evidence))))
        if self.status not in {
            BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY,
            BROWSER_AUTOMATION_GOVERNANCE_BLOCKED,
        }:
            raise ValueError("unsupported browser automation governance status")
        if self.risk_tier not in {
            BROWSER_AUTOMATION_GOVERNANCE_RISK_LOW,
            BROWSER_AUTOMATION_GOVERNANCE_RISK_MEDIUM,
            BROWSER_AUTOMATION_GOVERNANCE_RISK_HIGH,
            BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED,
        }:
            raise ValueError("unsupported browser automation governance risk tier")
        object.__setattr__(self, "policy_hash", _required_hash("policy_hash", self.policy_hash))
        object.__setattr__(self, "governance_hash", _required_hash("governance_hash", self.governance_hash))
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "requires_step47_controlled_execution", True)
        for field_name in (*_EFFECT_FIELD_NAMES, *_AUTHORITY_FIELD_NAMES, "can_type", "can_submit", "can_navigate"):
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "risk_tier": self.risk_tier,
            "preview_id": self.preview_id,
            "preview_hash": self.preview_hash,
            "request_hash": self.request_hash,
            "browser_read_result_hash": self.browser_read_result_hash,
            "source_hash": self.source_hash,
            "step_hashes": self.step_hashes,
            "risk_codes": self.risk_codes,
            "action_labels": self.action_labels,
            "blocked_actions": self.blocked_actions,
            "allowed_for_future_review_actions": self.allowed_for_future_review_actions,
            "required_future_evidence": self.required_future_evidence,
            "policy_hash": self.policy_hash,
            "governance_hash": self.governance_hash,
            "human_review_required": True,
            "requires_step47_controlled_execution": True,
        }
        for field_name in (
            *_EFFECT_FIELD_NAMES,
            "gate_satisfied",
            "human_barrier_satisfied",
            "governance_passed",
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


def create_browser_automation_governance_policy(
    *,
    policy_id: str = "browser-automation-governance-1a",
    allowed_preview_actions: tuple[str, ...] = _DEFAULT_ALLOWED_PREVIEW_ACTIONS,
    blocked_actions: tuple[str, ...] = _DEFAULT_BLOCKED_ACTIONS,
    high_risk_actions: tuple[str, ...] = _DEFAULT_HIGH_RISK_ACTIONS,
    max_steps: int = 8,
) -> BrowserAutomationGovernancePolicy:
    material = {
        "schema_version": BROWSER_AUTOMATION_GOVERNANCE_POLICY_SCHEMA_VERSION,
        "policy_id": _required_text("policy_id", policy_id),
        "allowed_preview_actions": _text_tuple("allowed_preview_actions", allowed_preview_actions),
        "blocked_actions": _text_tuple("blocked_actions", blocked_actions),
        "high_risk_actions": _text_tuple("high_risk_actions", high_risk_actions),
        "max_steps": _positive_int("max_steps", max_steps),
        "requires_human_review": True,
        "requires_step47_controlled_execution": True,
    }
    return BrowserAutomationGovernancePolicy(**material, policy_hash=_stable_hash(material))


def evaluate_browser_automation_governance(
    *,
    preview_result: object,
    preview_request: object,
    now_tick: object,
    policy: BrowserAutomationGovernancePolicy | None = None,
) -> BrowserAutomationGovernanceResult:
    active_policy = policy or create_browser_automation_governance_policy()
    reason_codes: list[str] = []
    try:
        tick = _nonnegative_int("now_tick", now_tick)
    except (TypeError, ValueError):
        return _blocked(active_policy, (BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE,))

    try:
        request_data = _coerce_mapping(preview_request)
        preview_data = _coerce_preview_mapping(preview_result)
        input_fingerprint = _json_fingerprint({"preview_result": preview_data, "preview_request": request_data})
    except TypeError:
        return _blocked(active_policy, (BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_NON_JSON_SERIALIZABLE,))

    request_unknown = sorted(str(field) for field in request_data if field not in _ALLOWED_REQUEST_FIELDS)
    preview_unknown = sorted(str(field) for field in preview_data if field not in _ALLOWED_PREVIEW_FIELDS)
    if request_unknown or preview_unknown:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_FIELD)

    try:
        preview_hash = _required_hash("preview_hash", preview_data.get("preview_hash"))
        request_hash = _required_hash("request_hash", preview_data.get("request_hash"))
        browser_read_result_hash = _required_hash("browser_read_result_hash", preview_data.get("browser_read_result_hash"))
        source_hash = _required_hash("source_hash", preview_data.get("source_hash"))
        preview_id = _required_text("preview_id", preview_data.get("preview_id"))
        step_hashes = _hash_tuple("step_hashes", preview_data.get("step_hashes"))
        risk_codes = _raw_text_tuple("risk_codes", preview_data.get("risk_codes"))
        created_at_tick = _nonnegative_int("created_at_tick", request_data.get("created_at_tick"))
        expires_at_tick = _nonnegative_int("expires_at_tick", request_data.get("expires_at_tick"))
        request_steps = _coerce_steps(request_data.get("steps"))
    except (TypeError, ValueError):
        return _blocked(
            active_policy,
            tuple(reason_codes or (BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE,)),
            input_fingerprint=input_fingerprint,
        )

    action_labels = tuple(step["action"] for step in request_steps)
    if request_data.get("schema_version") != BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_MALFORMED_EVIDENCE)
    if created_at_tick > tick or expires_at_tick < tick or expires_at_tick < created_at_tick:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_STALE_EVIDENCE)
    if len(request_steps) > active_policy.max_steps:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION)
    if _has_key(request_data, _AUTHORITY_FIELD_NAMES) or _authority_claim_present(preview_data):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM)
    if _has_authority_text(request_data) or _has_authority_text(preview_data):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_AUTHORITY_CLAIM)
    if _has_key(request_data, _DANGEROUS_FIELD_NAMES) or _has_key(preview_data, _DANGEROUS_FIELD_NAMES):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE)
    if _has_executable_text(request_data) or _has_executable_text(preview_data):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EXECUTABLE_EVIDENCE)
    if _effect_claim_present(preview_data):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_EFFECT_EVIDENCE)

    recomputed_preview = create_browser_automation_preview(request_data, now_tick=tick)
    if recomputed_preview.status != BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY)
    if preview_data.get("status") != BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_PREVIEW_NOT_READY)
    if preview_hash != recomputed_preview.preview_hash:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if request_hash != compute_browser_automation_request_hash(request_data):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if request_hash != recomputed_preview.request_hash:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if browser_read_result_hash != recomputed_preview.browser_read_result_hash or source_hash != recomputed_preview.source_hash:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if step_hashes != recomputed_preview.step_hashes:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if tuple(sorted(risk_codes)) != recomputed_preview.risk_codes:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    if any(code not in _KNOWN_RISK_CODES for code in risk_codes):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNKNOWN_RISK)

    computed_step_hashes = tuple(compute_browser_automation_step_hash(step) for step in request_steps)
    if computed_step_hashes != tuple(step["step_hash"] for step in request_steps):
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_HASH_MISMATCH)
    unsupported_actions = tuple(action for action in action_labels if action not in _SUPPORTED_ACTIONS)
    if unsupported_actions:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_UNSUPPORTED_ACTION)
    policy_blocked_actions = tuple(action for action in action_labels if action in active_policy.blocked_actions)
    if policy_blocked_actions:
        reason_codes.append(BROWSER_AUTOMATION_GOVERNANCE_BLOCKED_POLICY_ACTION)

    allowed_for_future_review = tuple(
        action for action in action_labels if action in active_policy.allowed_preview_actions and action not in policy_blocked_actions
    )
    blocked_actions = tuple(sorted(set((*unsupported_actions, *policy_blocked_actions))))
    if not reason_codes:
        reason_codes = [BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY]

    status = BROWSER_AUTOMATION_GOVERNANCE_BLOCKED
    if reason_codes == [BROWSER_AUTOMATION_GOVERNANCE_REASON_FUTURE_REVIEW_METADATA_ONLY]:
        status = BROWSER_AUTOMATION_GOVERNANCE_FUTURE_REVIEW_METADATA_ONLY
    risk_tier = _risk_tier(action_labels, blocked_actions)
    material = {
        "schema_version": BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": risk_tier,
        "preview_id": preview_id,
        "preview_hash": preview_hash,
        "request_hash": request_hash,
        "browser_read_result_hash": browser_read_result_hash,
        "source_hash": source_hash,
        "step_hashes": step_hashes,
        "risk_codes": tuple(sorted(set(risk_codes))),
        "action_labels": tuple(sorted(set(action_labels))),
        "blocked_actions": blocked_actions,
        "allowed_for_future_review_actions": tuple(sorted(set(allowed_for_future_review))),
        "required_future_evidence": _REQUIRED_FUTURE_EVIDENCE,
        "policy_hash": active_policy.policy_hash,
        "human_review_required": True,
        "requires_step47_controlled_execution": True,
        "input_fingerprint": input_fingerprint,
    }
    return BrowserAutomationGovernanceResult(
        schema_version=BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION,
        status=status,
        reason_codes=tuple(reason_codes),
        risk_tier=risk_tier,
        preview_id=preview_id,
        preview_hash=preview_hash,
        request_hash=request_hash,
        browser_read_result_hash=browser_read_result_hash,
        source_hash=source_hash,
        step_hashes=step_hashes,
        risk_codes=risk_codes,
        action_labels=action_labels,
        blocked_actions=blocked_actions,
        allowed_for_future_review_actions=allowed_for_future_review,
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        policy_hash=active_policy.policy_hash,
        governance_hash=_stable_hash(material),
    )


def canonical_browser_automation_governance_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _coerce_preview_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, BrowserAutomationPreviewResult):
        return value.to_dict()
    return _coerce_mapping(value)


def _coerce_mapping(value: object) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        if isinstance(candidate, Mapping):
            return dict(candidate)
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("browser automation governance evidence must be mapping evidence")


def _coerce_steps(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("browser automation governance requires step evidence")
    steps: list[dict[str, Any]] = []
    for item in value:
        if hasattr(item, "to_dict"):
            item = item.to_dict()
        if not isinstance(item, Mapping):
            raise TypeError("browser automation governance step must be mapping evidence")
        if any(field not in _ALLOWED_STEP_FIELDS for field in item):
            raise ValueError("browser automation governance step has unknown fields")
        step = dict(item)
        step["action"] = _required_text("action", step.get("action")).casefold()
        step["target"] = _required_text("target", step.get("target"))
        if step.get("value") is not None:
            step["value"] = _required_text("value", step.get("value"))
        step["description"] = _required_text("description", step.get("description"))
        step["step_hash"] = _required_hash("step_hash", step.get("step_hash"))
        steps.append(step)
    return tuple(steps)


def _risk_tier(action_labels: tuple[str, ...], blocked_actions: tuple[str, ...]) -> str:
    if blocked_actions:
        return BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED
    if any(action in _DEFAULT_HIGH_RISK_ACTIONS for action in action_labels):
        return BROWSER_AUTOMATION_GOVERNANCE_RISK_HIGH
    if any(action in _MEDIUM_RISK_ACTIONS for action in action_labels):
        return BROWSER_AUTOMATION_GOVERNANCE_RISK_MEDIUM
    if any(action in _LOW_RISK_ACTIONS for action in action_labels):
        return BROWSER_AUTOMATION_GOVERNANCE_RISK_LOW
    return BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED


def _blocked(
    policy: BrowserAutomationGovernancePolicy,
    reason_codes: tuple[str, ...],
    *,
    input_fingerprint: Any | None = None,
) -> BrowserAutomationGovernanceResult:
    material = {
        "schema_version": BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION,
        "status": BROWSER_AUTOMATION_GOVERNANCE_BLOCKED,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_tier": BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED,
        "policy_hash": policy.policy_hash,
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
        "requires_step47_controlled_execution": True,
    }
    return BrowserAutomationGovernanceResult(
        schema_version=BROWSER_AUTOMATION_GOVERNANCE_SCHEMA_VERSION,
        status=BROWSER_AUTOMATION_GOVERNANCE_BLOCKED,
        reason_codes=reason_codes,
        risk_tier=BROWSER_AUTOMATION_GOVERNANCE_RISK_BLOCKED,
        preview_id=None,
        preview_hash=None,
        request_hash=None,
        browser_read_result_hash=None,
        source_hash=None,
        step_hashes=(),
        risk_codes=(),
        action_labels=(),
        blocked_actions=(),
        allowed_for_future_review_actions=(),
        required_future_evidence=_REQUIRED_FUTURE_EVIDENCE,
        policy_hash=policy.policy_hash,
        governance_hash=_stable_hash(material),
    )


def _has_key(value: object, names: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in names:
                return True
            if _has_key(item, names):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_has_key(item, names) for item in value)
    return False


def _effect_claim_present(value: Mapping[str, Any]) -> bool:
    return any(value.get(field_name) is True for field_name in _EFFECT_FIELD_NAMES)


def _authority_claim_present(value: Mapping[str, Any]) -> bool:
    return any(value.get(field_name) is True for field_name in _AUTHORITY_FIELD_NAMES)


def _has_executable_text(value: object) -> bool:
    return any(_EXECUTABLE_TEXT_PATTERN.search(item) for item in _text_values(value))


def _has_authority_text(value: object) -> bool:
    return any(_AUTHORITY_TEXT_PATTERN.search(item) for item in _text_values(value))


def _text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_text_values(item))
        return tuple(values)
    if isinstance(value, (tuple, list)):
        values = []
        for item in value:
            values.extend(_text_values(item))
        return tuple(values)
    return ()


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("browser automation governance evidence is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000_000:
            raise TypeError("integer evidence is excessive")
        return value
    if isinstance(value, float):
        raise TypeError("floating point browser automation governance evidence is ambiguous")
    if isinstance(value, str):
        if len(value) > _MAX_TEXT:
            raise TypeError("text evidence is excessive")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("mapping evidence is excessive")
        normalized: dict[str, Any] = {}
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            if not isinstance(key, str) or not key.strip():
                raise TypeError("mapping evidence keys must be non-empty text")
            normalized[key.strip()] = _json_fingerprint(item, depth=depth + 1)
        return normalized
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("sequence evidence is excessive")
        return tuple(_json_fingerprint(item, depth=depth + 1) for item in value)
    raise TypeError("browser automation governance evidence must be JSON serializable")


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_TEXT:
        raise ValueError(f"{name} is too long")
    return value.strip()


def _text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    normalized = tuple(_required_text(name, item).casefold() for item in value)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return tuple(sorted(set(normalized)))


def _raw_text_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a sequence")
    normalized = tuple(_required_text(name, item) for item in value)
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return tuple(sorted(set(normalized)))


def _hash_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise TypeError(f"{name} must be a non-empty sequence")
    return tuple(_required_hash(name, item) for item in value)


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_browser_automation_governance_json(value).encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
