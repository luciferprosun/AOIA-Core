from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_PREVIEW_1A"
BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_PREVIEW_REQUEST_1A"
BROWSER_AUTOMATION_PREVIEW_STEP_SCHEMA_VERSION = "AOIA_BROWSER_AUTOMATION_PREVIEW_STEP_1A"

BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY = "BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY"
BROWSER_AUTOMATION_PREVIEW_BLOCKED = "BROWSER_AUTOMATION_PREVIEW_BLOCKED"

BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY = "BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNKNOWN_FIELD = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNKNOWN_FIELD"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNSUPPORTED_ACTION = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNSUPPORTED_ACTION"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_STALE_EVIDENCE = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_STALE_EVIDENCE"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_EXECUTABLE_EVIDENCE = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_EXECUTABLE_EVIDENCE"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_NON_JSON_SERIALIZABLE = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_NON_JSON_SERIALIZABLE"
BROWSER_AUTOMATION_PREVIEW_BLOCKED_AMBIGUOUS_EVIDENCE = "BROWSER_AUTOMATION_PREVIEW_BLOCKED_AMBIGUOUS_EVIDENCE"

BROWSER_AUTOMATION_RISK_CLICK = "BROWSER_AUTOMATION_RISK_CLICK"
BROWSER_AUTOMATION_RISK_TYPE = "BROWSER_AUTOMATION_RISK_TYPE"
BROWSER_AUTOMATION_RISK_FORM_SUBMIT = "BROWSER_AUTOMATION_RISK_FORM_SUBMIT"
BROWSER_AUTOMATION_RISK_NAVIGATION = "BROWSER_AUTOMATION_RISK_NAVIGATION"
BROWSER_AUTOMATION_RISK_DOWNLOAD = "BROWSER_AUTOMATION_RISK_DOWNLOAD"
BROWSER_AUTOMATION_RISK_UPLOAD = "BROWSER_AUTOMATION_RISK_UPLOAD"
BROWSER_AUTOMATION_RISK_COOKIE_MUTATION = "BROWSER_AUTOMATION_RISK_COOKIE_MUTATION"
BROWSER_AUTOMATION_RISK_STORAGE_MUTATION = "BROWSER_AUTOMATION_RISK_STORAGE_MUTATION"
BROWSER_AUTOMATION_RISK_WAIT = "BROWSER_AUTOMATION_RISK_WAIT"
BROWSER_AUTOMATION_RISK_READ_ONLY = "BROWSER_AUTOMATION_RISK_READ_ONLY"

SUPPORTED_BROWSER_AUTOMATION_PREVIEW_ACTIONS = frozenset(
    {
        "click",
        "type",
        "submit",
        "follow_link",
        "navigate",
        "download",
        "upload",
        "set_cookie",
        "set_storage",
        "wait_for_selector",
        "read_snapshot",
    }
)

_ACTION_RISK_CODES = {
    "click": (BROWSER_AUTOMATION_RISK_CLICK,),
    "type": (BROWSER_AUTOMATION_RISK_TYPE,),
    "submit": (BROWSER_AUTOMATION_RISK_FORM_SUBMIT,),
    "follow_link": (BROWSER_AUTOMATION_RISK_NAVIGATION,),
    "navigate": (BROWSER_AUTOMATION_RISK_NAVIGATION,),
    "download": (BROWSER_AUTOMATION_RISK_DOWNLOAD,),
    "upload": (BROWSER_AUTOMATION_RISK_UPLOAD,),
    "set_cookie": (BROWSER_AUTOMATION_RISK_COOKIE_MUTATION,),
    "set_storage": (BROWSER_AUTOMATION_RISK_STORAGE_MUTATION,),
    "wait_for_selector": (BROWSER_AUTOMATION_RISK_WAIT,),
    "read_snapshot": (BROWSER_AUTOMATION_RISK_READ_ONLY,),
}

_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 1024
_MAX_STEPS = 32
_MAX_COLLECTION_ITEMS = 32
_MAX_DEPTH = 5
_AUTHORITY_FLAGS = (
    "can_browse",
    "can_click",
    "can_download",
    "can_execute",
    "can_write",
    "can_call_provider",
    "can_change_gate",
    "gate_satisfied",
    "human_barrier_satisfied",
    "future_browser_action_authorized",
)
_EFFECT_FLAGS = (
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
)
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
        "browser_automation_allowed",
        "execution_allowed",
    }
)
_DANGEROUS_FIELD_NAMES = frozenset(
    {
        "command",
        "commands",
        "shell",
        "script",
        "javascript",
        "js",
        "web" + "driver",
        "driver",
        "browser_driver",
        "network",
        "http",
        "headers",
        "token",
        "secret",
        "api" + "_key",
        "env",
        "get" + "env",
        "os." + "environ",
        "sub" + "process",
    }
)
_ALLOWED_STEP_FIELDS = frozenset({"schema_version", "action", "target", "value", "description", "step_hash"})
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
_REMOTE_OR_SPECIAL_PREFIXES = ("http://", "https://", "//", "javascript:", "data:", "file:", "about:", "chrome:")
_BROWSER_TOOL_PATTERN = "|".join(
    (
        "selen" + "ium",
        "play" + "wright",
        "web" + "driver",
        "web" + "browser",
        "chrome" + "driver",
        "gecko" + "driver",
    )
)
_EXECUTABLE_TEXT_PATTERN = re.compile(
    r"(?i)(?:\b(?:" + _BROWSER_TOOL_PATTERN + r")\b|"
    r"\b(?:fetch|xmlhttprequest|eval|exec|function\s*\(|settimeout|setinterval)\b|"
    r"\b(?:curl|wget|bash|sh|sudo|powershell|cmd\.exe)\b|"
    r"\b(?:python\s+-m|pip|npm|apt|git)\s+\w+\b|"
    r"(?:;|&&|\|\||`|\$\(|<\(|>\(|\n))"
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"safe\s+to\s+(?:browse|click|execute|download)|can\s+(?:browse|click|execute|download)|"
    r"gate\s+satisfied|authority\s+granted)\b"
)


@dataclass(frozen=True)
class BrowserAutomationPreviewStep:
    schema_version: str
    action: str
    target: str
    value: str | None
    description: str
    step_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "action", _required_text("action", self.action).casefold())
        object.__setattr__(self, "target", _required_text("target", self.target))
        object.__setattr__(self, "value", _optional_text("value", self.value))
        object.__setattr__(self, "description", _required_text("description", self.description))
        object.__setattr__(self, "step_hash", _required_hash("step_hash", self.step_hash))
        if self.schema_version != BROWSER_AUTOMATION_PREVIEW_STEP_SCHEMA_VERSION:
            raise ValueError("unsupported browser automation preview step schema version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "description": self.description,
            "step_hash": self.step_hash,
        }


@dataclass(frozen=True)
class BrowserAutomationPreviewRequest:
    schema_version: str
    preview_id: str
    browser_read_result_hash: str
    source_hash: str
    reason: str
    requested_by: str
    created_at_tick: int
    expires_at_tick: int
    steps: tuple[BrowserAutomationPreviewStep, ...]
    metadata: Mapping[str, Any] | None = None
    request_hash: str | None = None


@dataclass(frozen=True)
class BrowserAutomationPreviewResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    risk_codes: tuple[str, ...]
    preview_id: str | None
    browser_read_result_hash: str | None
    source_hash: str | None
    step_hashes: tuple[str, ...]
    request_hash: str | None
    preview_hash: str
    human_review_required: bool = True
    future_governance_required: bool = True
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
    can_download: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    future_browser_action_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "risk_codes", tuple(sorted(set(self.risk_codes))))
        object.__setattr__(self, "step_hashes", tuple(self.step_hashes))
        if self.status not in {BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY, BROWSER_AUTOMATION_PREVIEW_BLOCKED}:
            raise ValueError("unsupported browser automation preview status")
        if not _sha256_like(self.preview_hash):
            raise ValueError("preview_hash must be a sha256 hex digest")
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "future_governance_required", True)
        for field_name in (*_EFFECT_FLAGS, *_AUTHORITY_FLAGS):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "risk_codes": self.risk_codes,
            "preview_id": self.preview_id,
            "browser_read_result_hash": self.browser_read_result_hash,
            "source_hash": self.source_hash,
            "step_hashes": self.step_hashes,
            "request_hash": self.request_hash,
            "preview_hash": self.preview_hash,
            "human_review_required": True,
            "future_governance_required": True,
        }
        for field_name in (*_EFFECT_FLAGS, *_AUTHORITY_FLAGS):
            data[field_name] = False
        return data


def create_browser_automation_preview_step(
    *,
    action: str,
    target: str,
    value: str | None = None,
    description: str,
) -> BrowserAutomationPreviewStep:
    material = {
        "schema_version": BROWSER_AUTOMATION_PREVIEW_STEP_SCHEMA_VERSION,
        "action": _required_text("action", action).casefold(),
        "target": _required_text("target", target),
        "value": _optional_text("value", value),
        "description": _required_text("description", description),
    }
    return BrowserAutomationPreviewStep(**material, step_hash=compute_browser_automation_step_hash(material))


def create_browser_automation_preview(request: object, *, now_tick: object) -> BrowserAutomationPreviewResult:
    reason_codes: list[str] = []
    risk_codes: list[str] = []
    try:
        tick = _nonnegative_int("now_tick", now_tick)
    except (TypeError, ValueError):
        return _blocked((BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE,))

    try:
        data = _coerce_request_mapping(request)
        input_fingerprint = _json_fingerprint(data)
    except TypeError:
        return _blocked((BROWSER_AUTOMATION_PREVIEW_BLOCKED_NON_JSON_SERIALIZABLE,))

    unknown_fields = sorted(str(field) for field in data if field not in _ALLOWED_REQUEST_FIELDS)
    if unknown_fields:
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNKNOWN_FIELD)
    if data.get("schema_version") != BROWSER_AUTOMATION_PREVIEW_REQUEST_SCHEMA_VERSION:
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE)

    try:
        preview_id = _required_text("preview_id", data.get("preview_id"))
        browser_read_result_hash = _required_hash("browser_read_result_hash", data.get("browser_read_result_hash"))
        source_hash = _required_hash("source_hash", data.get("source_hash"))
        reason = _required_text("reason", data.get("reason"))
        requested_by = _required_text("requested_by", data.get("requested_by"))
        created_at_tick = _nonnegative_int("created_at_tick", data.get("created_at_tick"))
        expires_at_tick = _nonnegative_int("expires_at_tick", data.get("expires_at_tick"))
        steps = _coerce_steps(data.get("steps"))
        metadata = _optional_mapping("metadata", data.get("metadata")) or {}
        request_hash = _optional_hash("request_hash", data.get("request_hash"))
    except (TypeError, ValueError):
        return _blocked(
            tuple(reason_codes or (BROWSER_AUTOMATION_PREVIEW_BLOCKED_MALFORMED_EVIDENCE,)),
            input_fingerprint=input_fingerprint,
        )

    if created_at_tick > tick or expires_at_tick < tick or expires_at_tick < created_at_tick:
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_STALE_EVIDENCE)
    if _has_key(data, _AUTHORITY_FIELD_NAMES) or _has_authority_text(data):
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_AUTHORITY_CLAIM)
    if _has_key(data, _DANGEROUS_FIELD_NAMES) or _has_executable_text(data):
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_EXECUTABLE_EVIDENCE)

    normalized_steps: list[dict[str, Any]] = []
    for step in steps:
        step_mapping = step.to_dict()
        normalized_steps.append(step_mapping)
        if step.action not in SUPPORTED_BROWSER_AUTOMATION_PREVIEW_ACTIONS:
            reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_UNSUPPORTED_ACTION)
        if _looks_remote_or_special(step.target) or _looks_remote_or_special(step.value or ""):
            reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_REMOTE_OR_SPECIAL_TARGET)
        expected_step_hash = compute_browser_automation_step_hash(_step_hash_material(step))
        if step.step_hash != expected_step_hash:
            reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH)
        risk_codes.extend(_ACTION_RISK_CODES.get(step.action, ()))

    normalized_metadata = _json_fingerprint(metadata)
    material_for_request_hash = dict(input_fingerprint)
    material_for_request_hash.pop("request_hash", None)
    computed_request_hash = _stable_hash(material_for_request_hash)
    if request_hash is not None and request_hash != computed_request_hash:
        reason_codes.append(BROWSER_AUTOMATION_PREVIEW_BLOCKED_HASH_MISMATCH)
    request_hash = request_hash or computed_request_hash

    if not reason_codes:
        reason_codes = [BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY]

    status = BROWSER_AUTOMATION_PREVIEW_BLOCKED
    if reason_codes == [BROWSER_AUTOMATION_PREVIEW_REASON_READY_METADATA_ONLY]:
        status = BROWSER_AUTOMATION_PREVIEW_READY_METADATA_ONLY

    material = {
        "schema_version": BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "risk_codes": tuple(sorted(set(risk_codes))),
        "preview_id": preview_id,
        "browser_read_result_hash": browser_read_result_hash,
        "source_hash": source_hash,
        "reason": reason,
        "requested_by": requested_by,
        "created_at_tick": created_at_tick,
        "expires_at_tick": expires_at_tick,
        "steps": normalized_steps,
        "metadata": normalized_metadata,
        "request_hash": request_hash,
        "human_review_required": True,
        "future_governance_required": True,
    }
    return BrowserAutomationPreviewResult(
        schema_version=BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION,
        status=status,
        reason_codes=tuple(reason_codes),
        risk_codes=tuple(risk_codes),
        preview_id=preview_id,
        browser_read_result_hash=browser_read_result_hash,
        source_hash=source_hash,
        step_hashes=tuple(step.step_hash for step in steps),
        request_hash=request_hash,
        preview_hash=_stable_hash(material),
    )


def compute_browser_automation_step_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("step_hash", None)
    return _stable_hash(_json_fingerprint(data))


def compute_browser_automation_request_hash(value: object) -> str:
    data = _coerce_request_mapping(value)
    fingerprint = _json_fingerprint(data)
    if isinstance(fingerprint, dict):
        fingerprint.pop("request_hash", None)
    return _stable_hash(fingerprint)


def canonical_browser_automation_preview_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _coerce_request_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, BrowserAutomationPreviewRequest):
        return {
            "schema_version": value.schema_version,
            "preview_id": value.preview_id,
            "browser_read_result_hash": value.browser_read_result_hash,
            "source_hash": value.source_hash,
            "reason": value.reason,
            "requested_by": value.requested_by,
            "created_at_tick": value.created_at_tick,
            "expires_at_tick": value.expires_at_tick,
            "steps": tuple(item.to_dict() for item in value.steps),
            "metadata": value.metadata or {},
            "request_hash": value.request_hash,
        }
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("browser automation preview request must be mapping evidence")


def _coerce_steps(value: object) -> tuple[BrowserAutomationPreviewStep, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError("steps must be a non-empty sequence")
    if len(value) > _MAX_STEPS:
        raise ValueError("too many browser automation preview steps")
    steps: list[BrowserAutomationPreviewStep] = []
    for item in value:
        if isinstance(item, BrowserAutomationPreviewStep):
            steps.append(item)
            continue
        if not isinstance(item, Mapping):
            raise TypeError("browser automation preview step must be mapping evidence")
        unknown_fields = sorted(str(field) for field in item if field not in _ALLOWED_STEP_FIELDS)
        if unknown_fields:
            raise ValueError("browser automation preview step has unknown fields")
        steps.append(BrowserAutomationPreviewStep(**dict(item)))
    return tuple(steps)


def _step_hash_material(step: BrowserAutomationPreviewStep) -> dict[str, Any]:
    data = step.to_dict()
    data.pop("step_hash", None)
    return data


def _blocked(
    reason_codes: tuple[str, ...],
    *,
    input_fingerprint: Any | None = None,
) -> BrowserAutomationPreviewResult:
    material = {
        "schema_version": BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION,
        "status": BROWSER_AUTOMATION_PREVIEW_BLOCKED,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
        "future_governance_required": True,
    }
    return BrowserAutomationPreviewResult(
        schema_version=BROWSER_AUTOMATION_PREVIEW_SCHEMA_VERSION,
        status=BROWSER_AUTOMATION_PREVIEW_BLOCKED,
        reason_codes=reason_codes,
        risk_codes=(),
        preview_id=None,
        browser_read_result_hash=None,
        source_hash=None,
        step_hashes=(),
        request_hash=None,
        preview_hash=_stable_hash(material),
    )


def _looks_remote_or_special(value: str) -> bool:
    lowered = value.strip().casefold()
    return lowered.startswith(_REMOTE_OR_SPECIAL_PREFIXES)


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
        raise TypeError("browser automation preview evidence is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000_000:
            raise TypeError("integer evidence is excessive")
        return value
    if isinstance(value, float):
        raise TypeError("floating point browser automation preview evidence is ambiguous")
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
    raise TypeError("browser automation preview evidence must be JSON serializable")


def _optional_mapping(name: str, value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return dict(value)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_TEXT:
        raise ValueError(f"{name} is too long")
    return value.strip()


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_hash(name, value)


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_browser_automation_preview_json(value).encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
