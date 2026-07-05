from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping


CONTROLLED_BROWSER_READ_SCHEMA_VERSION = "AOIA_CONTROLLED_BROWSER_READ_1A"
BROWSER_READ_REQUEST_SCHEMA_VERSION = "AOIA_BROWSER_READ_REQUEST_1A"
BROWSER_READ_CONTEXT_SCHEMA_VERSION = "AOIA_BROWSER_READ_CONTEXT_1A"
BROWSER_READ_HUMAN_BARRIER_SCHEMA_VERSION = "AOIA_BROWSER_READ_HUMAN_BARRIER_1A"

CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED = "CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED"
CONTROLLED_BROWSER_READ_BLOCKED = "CONTROLLED_BROWSER_READ_BLOCKED"

CONTROLLED_BROWSER_READ_REASON_SNAPSHOT_CREATED = "CONTROLLED_BROWSER_READ_REASON_SNAPSHOT_CREATED"
CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE = "CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE"
CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH = "CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH"
CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE = "CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE"
CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_SOURCE = "CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_SOURCE"
CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE = "CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE"
CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML = "CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML"
CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_EXTRACTOR = "CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_EXTRACTOR"
CONTROLLED_BROWSER_READ_BLOCKED_MISSING_HUMAN_BARRIER = "CONTROLLED_BROWSER_READ_BLOCKED_MISSING_HUMAN_BARRIER"
CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH = "CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH"
CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_SCOPE_MISMATCH = "CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_SCOPE_MISMATCH"
CONTROLLED_BROWSER_READ_BLOCKED_AUTHORITY_CLAIM = "CONTROLLED_BROWSER_READ_BLOCKED_AUTHORITY_CLAIM"
CONTROLLED_BROWSER_READ_BLOCKED_NON_OFFLINE_CONTEXT = "CONTROLLED_BROWSER_READ_BLOCKED_NON_OFFLINE_CONTEXT"

SOURCE_KIND_INLINE_HTML = "inline_html"
SOURCE_KIND_SANDBOX_FILE = "sandbox_file"
ALLOWED_EXTRACTORS = frozenset({"title", "text_hash", "links"})

_HEX = frozenset("0123456789abcdef")
_MAX_HTML_CHARS = 200_000
_MAX_TEXT_CHARS = 40_000
_MAX_LINKS = 64
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
        "browser_opened",
        "network_called",
    }
)
_UNSAFE_ELEMENTS = frozenset(
    {
        "script",
        "iframe",
        "object",
        "embed",
        "form",
        "input",
        "button",
        "select",
        "textarea",
        "video",
        "audio",
        "source",
    }
)
_REMOTE_RESOURCE_ATTRIBUTES = frozenset({"src", "srcset", "action", "formaction", "poster"})
_REMOTE_PREFIXES = ("http://", "https://", "//")
_UNSAFE_URI_PREFIXES = ("javascript:", "data:", "file:", "about:", "chrome:")


@dataclass(frozen=True)
class ControlledBrowserReadRequest:
    schema_version: str
    source_kind: str
    source_locator: str
    expected_source_hash: str
    reason: str
    requested_by: str
    requested_at: int
    expires_at: int
    allowed_extractors: tuple[str, ...]
    request_hash: str
    can_browse: bool = False
    can_click: bool = False
    can_download: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    future_browser_action_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "source_kind", _required_text("source_kind", self.source_kind).casefold())
        object.__setattr__(self, "source_locator", _required_text("source_locator", self.source_locator))
        object.__setattr__(self, "expected_source_hash", _required_hash("expected_source_hash", self.expected_source_hash))
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(self, "requested_by", _required_text("requested_by", self.requested_by))
        object.__setattr__(self, "requested_at", _nonnegative_int("requested_at", self.requested_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "allowed_extractors", _text_tuple("allowed_extractors", self.allowed_extractors))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        for field_name in _AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)
        if self.schema_version != BROWSER_READ_REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported browser read request schema version")
        if self.expires_at < self.requested_at:
            raise ValueError("browser read request TTL is inverted")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_kind": self.source_kind,
            "source_locator": self.source_locator,
            "expected_source_hash": self.expected_source_hash,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "allowed_extractors": self.allowed_extractors,
            "request_hash": self.request_hash,
            "can_browse": False,
            "can_click": False,
            "can_download": False,
            "can_execute": False,
            "can_write": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "future_browser_action_authorized": False,
        }


@dataclass(frozen=True)
class ControlledBrowserReadContext:
    schema_version: str
    current_tick: int
    sandbox_root: str
    offline_mode: bool
    network_disabled: bool
    browser_launch_disabled: bool
    javascript_disabled: bool
    storage_mutation_disabled: bool
    context_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "current_tick", _nonnegative_int("current_tick", self.current_tick))
        object.__setattr__(self, "sandbox_root", _required_text("sandbox_root", self.sandbox_root))
        object.__setattr__(self, "context_hash", _required_hash("context_hash", self.context_hash))
        if self.schema_version != BROWSER_READ_CONTEXT_SCHEMA_VERSION:
            raise ValueError("unsupported browser read context schema version")
        for field_name in (
            "offline_mode",
            "network_disabled",
            "browser_launch_disabled",
            "javascript_disabled",
            "storage_mutation_disabled",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise TypeError(f"{field_name} must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "current_tick": self.current_tick,
            "sandbox_root": self.sandbox_root,
            "offline_mode": True,
            "network_disabled": True,
            "browser_launch_disabled": True,
            "javascript_disabled": True,
            "storage_mutation_disabled": True,
            "context_hash": self.context_hash,
        }


@dataclass(frozen=True)
class BrowserReadHumanBarrier:
    schema_version: str
    request_hash: str
    context_hash: str
    source_hash: str
    source_kind: str
    approved_extractors: tuple[str, ...]
    approved_by: str
    approval_reason: str
    approved_at: int
    expires_at: int
    barrier_hash: str
    can_browse: bool = False
    can_click: bool = False
    can_download: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    future_browser_action_authorized: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text("schema_version", self.schema_version))
        object.__setattr__(self, "request_hash", _required_hash("request_hash", self.request_hash))
        object.__setattr__(self, "context_hash", _required_hash("context_hash", self.context_hash))
        object.__setattr__(self, "source_hash", _required_hash("source_hash", self.source_hash))
        object.__setattr__(self, "source_kind", _required_text("source_kind", self.source_kind).casefold())
        object.__setattr__(self, "approved_extractors", _text_tuple("approved_extractors", self.approved_extractors))
        object.__setattr__(self, "approved_by", _required_text("approved_by", self.approved_by))
        object.__setattr__(self, "approval_reason", _required_text("approval_reason", self.approval_reason))
        object.__setattr__(self, "approved_at", _nonnegative_int("approved_at", self.approved_at))
        object.__setattr__(self, "expires_at", _nonnegative_int("expires_at", self.expires_at))
        object.__setattr__(self, "barrier_hash", _required_hash("barrier_hash", self.barrier_hash))
        for field_name in _AUTHORITY_FLAGS:
            object.__setattr__(self, field_name, False)
        if self.schema_version != BROWSER_READ_HUMAN_BARRIER_SCHEMA_VERSION:
            raise ValueError("unsupported browser read human barrier schema version")
        if self.expires_at < self.approved_at:
            raise ValueError("browser read human barrier TTL is inverted")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_hash": self.request_hash,
            "context_hash": self.context_hash,
            "source_hash": self.source_hash,
            "source_kind": self.source_kind,
            "approved_extractors": self.approved_extractors,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "barrier_hash": self.barrier_hash,
            "can_browse": False,
            "can_click": False,
            "can_download": False,
            "can_execute": False,
            "can_write": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "future_browser_action_authorized": False,
        }


@dataclass(frozen=True)
class ControlledBrowserReadResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    request_hash: str | None
    context_hash: str | None
    barrier_hash: str | None
    source_kind: str | None
    source_hash: str | None
    title: str | None
    text_hash: str | None
    links: tuple[str, ...]
    result_hash: str
    inline_html_read: bool = False
    local_file_read: bool = False
    snapshot_created: bool = False
    browser_opened: bool = False
    browser_action_performed: bool = False
    network_called: bool = False
    remote_resource_loaded: bool = False
    javascript_executed: bool = False
    link_followed: bool = False
    form_submitted: bool = False
    download_performed: bool = False
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
        object.__setattr__(self, "schema_version", CONTROLLED_BROWSER_READ_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "links", tuple(self.links))
        if self.status not in {CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED, CONTROLLED_BROWSER_READ_BLOCKED}:
            raise ValueError("unsupported controlled browser read status")
        if not _sha256_like(self.result_hash):
            raise ValueError("result_hash must be a sha256 hex digest")
        object.__setattr__(self, "snapshot_created", self.status == CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED)
        for field_name in (
            "browser_opened",
            "browser_action_performed",
            "network_called",
            "remote_resource_loaded",
            "javascript_executed",
            "link_followed",
            "form_submitted",
            "download_performed",
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
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTROLLED_BROWSER_READ_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "request_hash": self.request_hash,
            "context_hash": self.context_hash,
            "barrier_hash": self.barrier_hash,
            "source_kind": self.source_kind,
            "source_hash": self.source_hash,
            "title": self.title,
            "text_hash": self.text_hash,
            "links": self.links,
            "result_hash": self.result_hash,
            "inline_html_read": self.inline_html_read,
            "local_file_read": self.local_file_read,
            "snapshot_created": self.snapshot_created,
            "browser_opened": False,
            "browser_action_performed": False,
            "network_called": False,
            "remote_resource_loaded": False,
            "javascript_executed": False,
            "link_followed": False,
            "form_submitted": False,
            "download_performed": False,
            "cookie_mutated": False,
            "storage_mutated": False,
            "file_written": False,
            "provider_called": False,
            "git_action_performed": False,
            "package_installed": False,
            "approval_created": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "can_browse": False,
            "can_click": False,
            "can_download": False,
            "can_execute": False,
            "can_write": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "future_browser_action_authorized": False,
        }


def create_controlled_browser_read_request(
    *,
    source_kind: str,
    source_locator: str,
    expected_source_hash: str,
    reason: str,
    requested_by: str,
    requested_at: int,
    expires_at: int,
    allowed_extractors: tuple[str, ...],
) -> ControlledBrowserReadRequest:
    material = {
        "schema_version": BROWSER_READ_REQUEST_SCHEMA_VERSION,
        "source_kind": _required_text("source_kind", source_kind).casefold(),
        "source_locator": _required_text("source_locator", source_locator),
        "expected_source_hash": _required_hash("expected_source_hash", expected_source_hash),
        "reason": _required_text("reason", reason),
        "requested_by": _required_text("requested_by", requested_by),
        "requested_at": _nonnegative_int("requested_at", requested_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
        "allowed_extractors": _text_tuple("allowed_extractors", allowed_extractors),
    }
    return ControlledBrowserReadRequest(**material, request_hash=compute_browser_read_request_hash(material))


def create_controlled_browser_read_context(
    *,
    current_tick: int,
    sandbox_root: str,
    offline_mode: bool = True,
    network_disabled: bool = True,
    browser_launch_disabled: bool = True,
    javascript_disabled: bool = True,
    storage_mutation_disabled: bool = True,
) -> ControlledBrowserReadContext:
    material = {
        "schema_version": BROWSER_READ_CONTEXT_SCHEMA_VERSION,
        "current_tick": _nonnegative_int("current_tick", current_tick),
        "sandbox_root": _required_text("sandbox_root", sandbox_root),
        "offline_mode": bool(offline_mode),
        "network_disabled": bool(network_disabled),
        "browser_launch_disabled": bool(browser_launch_disabled),
        "javascript_disabled": bool(javascript_disabled),
        "storage_mutation_disabled": bool(storage_mutation_disabled),
    }
    return ControlledBrowserReadContext(**material, context_hash=compute_browser_read_context_hash(material))


def create_browser_read_human_barrier(
    *,
    request_hash: str,
    context_hash: str,
    source_hash: str,
    source_kind: str,
    approved_extractors: tuple[str, ...],
    approved_by: str,
    approval_reason: str,
    approved_at: int,
    expires_at: int,
) -> BrowserReadHumanBarrier:
    material = {
        "schema_version": BROWSER_READ_HUMAN_BARRIER_SCHEMA_VERSION,
        "request_hash": _required_hash("request_hash", request_hash),
        "context_hash": _required_hash("context_hash", context_hash),
        "source_hash": _required_hash("source_hash", source_hash),
        "source_kind": _required_text("source_kind", source_kind).casefold(),
        "approved_extractors": _text_tuple("approved_extractors", approved_extractors),
        "approved_by": _required_text("approved_by", approved_by),
        "approval_reason": _required_text("approval_reason", approval_reason),
        "approved_at": _nonnegative_int("approved_at", approved_at),
        "expires_at": _nonnegative_int("expires_at", expires_at),
    }
    return BrowserReadHumanBarrier(**material, barrier_hash=compute_browser_read_barrier_hash(material))


def execute_controlled_browser_read(
    *,
    request: object,
    context: object,
    human_barrier: object,
) -> ControlledBrowserReadResult:
    try:
        read_request = _coerce_request(request)
        read_context = _coerce_context(context)
        barrier = _coerce_barrier(human_barrier)
        request_hash = compute_browser_read_request_hash(_request_hash_material(read_request))
        context_hash = compute_browser_read_context_hash(_context_hash_material(read_context))
    except (TypeError, ValueError):
        return _blocked((CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE,))

    reason_codes: list[str] = []
    if request_hash != read_request.request_hash or context_hash != read_context.context_hash:
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH)
    if read_context.current_tick < read_request.requested_at or read_context.current_tick > read_request.expires_at:
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE)
    if not _context_is_offline(read_context):
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_NON_OFFLINE_CONTEXT)
    if read_request.source_kind not in {SOURCE_KIND_INLINE_HTML, SOURCE_KIND_SANDBOX_FILE}:
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_SOURCE)
    if not read_request.allowed_extractors or any(item not in ALLOWED_EXTRACTORS for item in read_request.allowed_extractors):
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_UNSUPPORTED_EXTRACTOR)
    if _authority_claim_present(request) or _authority_claim_present(human_barrier):
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_AUTHORITY_CLAIM)

    html_text: str | None = None
    actual_source_hash: str | None = None
    if read_request.source_kind == SOURCE_KIND_INLINE_HTML:
        html_text = read_request.source_locator
        actual_source_hash = compute_browser_read_source_hash(html_text)
    elif read_request.source_kind == SOURCE_KIND_SANDBOX_FILE:
        html_text, actual_source_hash, source_error = _read_sandbox_file(read_request.source_locator, read_context.sandbox_root)
        if source_error is not None:
            reason_codes.append(source_error)

    if actual_source_hash is not None and actual_source_hash != read_request.expected_source_hash:
        reason_codes.append(CONTROLLED_BROWSER_READ_BLOCKED_HASH_MISMATCH)

    reason_codes.extend(
        _barrier_reason_codes(
            barrier=barrier,
            request_hash=request_hash,
            context_hash=context_hash,
            source_hash=actual_source_hash or read_request.expected_source_hash,
            source_kind=read_request.source_kind,
            approved_extractors=read_request.allowed_extractors,
            current_tick=read_context.current_tick,
        )
    )

    parsed: _SnapshotParser | None = None
    if html_text is not None and not reason_codes:
        html_reason = _unsafe_html_reason(html_text)
        if html_reason is not None:
            reason_codes.append(html_reason)
        else:
            parsed = _parse_snapshot(html_text)

    if reason_codes or parsed is None or actual_source_hash is None:
        return _result(
            status=CONTROLLED_BROWSER_READ_BLOCKED,
            reason_codes=tuple(reason_codes or (CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE,)),
            request_hash=request_hash,
            context_hash=context_hash,
            barrier_hash=barrier.barrier_hash,
            source_kind=read_request.source_kind,
            source_hash=actual_source_hash,
            inline_html_read=False,
            local_file_read=False,
        )

    title = parsed.title if "title" in read_request.allowed_extractors else None
    text_hash = compute_browser_read_text_hash(parsed.visible_text) if "text_hash" in read_request.allowed_extractors else None
    links = parsed.links if "links" in read_request.allowed_extractors else ()
    return _result(
        status=CONTROLLED_BROWSER_READ_SNAPSHOT_CREATED,
        reason_codes=(CONTROLLED_BROWSER_READ_REASON_SNAPSHOT_CREATED,),
        request_hash=request_hash,
        context_hash=context_hash,
        barrier_hash=barrier.barrier_hash,
        source_kind=read_request.source_kind,
        source_hash=actual_source_hash,
        title=title,
        text_hash=text_hash,
        links=links,
        inline_html_read=read_request.source_kind == SOURCE_KIND_INLINE_HTML,
        local_file_read=read_request.source_kind == SOURCE_KIND_SANDBOX_FILE,
    )


def compute_browser_read_source_hash(html_text: str) -> str:
    return _stable_hash(_required_text("html_text", html_text))


def compute_browser_read_text_hash(text: str) -> str:
    return _stable_hash(_normalize_space(text))


def compute_browser_read_request_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("request_hash", None)
    return _stable_hash(_fingerprint(data))


def compute_browser_read_context_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("context_hash", None)
    return _stable_hash(_fingerprint(data))


def compute_browser_read_barrier_hash(value: Mapping[str, Any]) -> str:
    data = dict(value)
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return _stable_hash(_fingerprint(data))


def _request_hash_material(request: ControlledBrowserReadRequest) -> dict[str, Any]:
    data = request.to_dict()
    data.pop("request_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _context_hash_material(context: ControlledBrowserReadContext) -> dict[str, Any]:
    data = context.to_dict()
    data.pop("context_hash", None)
    return data


def _barrier_hash_material(barrier: BrowserReadHumanBarrier) -> dict[str, Any]:
    data = barrier.to_dict()
    data.pop("barrier_hash", None)
    for field_name in _AUTHORITY_FLAGS:
        data.pop(field_name, None)
    return data


def _barrier_reason_codes(
    *,
    barrier: BrowserReadHumanBarrier,
    request_hash: str,
    context_hash: str,
    source_hash: str,
    source_kind: str,
    approved_extractors: tuple[str, ...],
    current_tick: int,
) -> tuple[str, ...]:
    codes: list[str] = []
    if barrier is None:
        return (CONTROLLED_BROWSER_READ_BLOCKED_MISSING_HUMAN_BARRIER,)
    try:
        if barrier.barrier_hash != compute_browser_read_barrier_hash(_barrier_hash_material(barrier)):
            codes.append(CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH)
    except (TypeError, ValueError):
        codes.append(CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_HASH_MISMATCH)
    if current_tick < barrier.approved_at or current_tick > barrier.expires_at:
        codes.append(CONTROLLED_BROWSER_READ_BLOCKED_STALE_EVIDENCE)
    if (
        barrier.request_hash != request_hash
        or barrier.context_hash != context_hash
        or barrier.source_hash != source_hash
        or barrier.source_kind != source_kind
        or tuple(sorted(barrier.approved_extractors)) != tuple(sorted(approved_extractors))
    ):
        codes.append(CONTROLLED_BROWSER_READ_BLOCKED_BARRIER_SCOPE_MISMATCH)
    return tuple(codes)


def _read_sandbox_file(source_locator: str, sandbox_root: str) -> tuple[str | None, str | None, str | None]:
    if _looks_remote_or_special(source_locator):
        return None, None, CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE
    try:
        root = Path(sandbox_root).resolve(strict=True)
        path = Path(source_locator).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None, None, CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE
    if not _is_relative_to(path, root) or not path.is_file() or path.suffix.casefold() not in {".html", ".htm"}:
        return None, None, CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_SOURCE
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return None, None, CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE
    return text, compute_browser_read_source_hash(text), None


def _unsafe_html_reason(html_text: str) -> str | None:
    if len(html_text) > _MAX_HTML_CHARS:
        return CONTROLLED_BROWSER_READ_BLOCKED_MALFORMED_EVIDENCE
    parser = _SafetyParser()
    try:
        parser.feed(html_text)
        parser.close()
    except ValueError:
        return CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML
    return CONTROLLED_BROWSER_READ_BLOCKED_UNSAFE_HTML if parser.unsafe else None


def _parse_snapshot(html_text: str) -> "_SnapshotParser":
    parser = _SnapshotParser()
    parser.feed(html_text)
    parser.close()
    return parser


class _SafetyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.unsafe = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._check(tag, attrs)

    def _check(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in _UNSAFE_ELEMENTS:
            self.unsafe = True
        for name, value in attrs:
            attr_name = name.casefold()
            attr_value = (value or "").strip().casefold()
            if attr_name.startswith("on") or attr_name in {"style", "http-equiv"}:
                self.unsafe = True
            if attr_name in _REMOTE_RESOURCE_ATTRIBUTES and (
                attr_value.startswith(_REMOTE_PREFIXES) or attr_value.startswith(_UNSAFE_URI_PREFIXES)
            ):
                self.unsafe = True
            if attr_name in {"href", "xlink:href"} and attr_value.startswith(("javascript:", "data:")):
                self.unsafe = True


class _SnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._links: list[str] = []

    @property
    def title(self) -> str:
        return _normalize_space(" ".join(self._title_parts))

    @property
    def visible_text(self) -> str:
        return _normalize_space(" ".join(self._text_parts))[:_MAX_TEXT_CHARS]

    @property
    def links(self) -> tuple[str, ...]:
        return tuple(self._links[:_MAX_LINKS])

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag == "title":
            self._in_title = True
        if normalized_tag == "a":
            for name, value in attrs:
                if name.casefold() == "href" and value is not None:
                    self._links.append(value.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        self._text_parts.append(data)


def _context_is_offline(context: ControlledBrowserReadContext) -> bool:
    return (
        context.offline_mode is True
        and context.network_disabled is True
        and context.browser_launch_disabled is True
        and context.javascript_disabled is True
        and context.storage_mutation_disabled is True
    )


def _coerce_request(value: object) -> ControlledBrowserReadRequest:
    if isinstance(value, ControlledBrowserReadRequest):
        return value
    if isinstance(value, Mapping):
        return ControlledBrowserReadRequest(**dict(value))
    if hasattr(value, "to_dict"):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            return ControlledBrowserReadRequest(**dict(mapped))
    raise TypeError("controlled browser read request is required")


def _coerce_context(value: object) -> ControlledBrowserReadContext:
    if isinstance(value, ControlledBrowserReadContext):
        return value
    if isinstance(value, Mapping):
        return ControlledBrowserReadContext(**dict(value))
    raise TypeError("controlled browser read context is required")


def _coerce_barrier(value: object) -> BrowserReadHumanBarrier:
    if isinstance(value, BrowserReadHumanBarrier):
        return value
    if isinstance(value, Mapping):
        return BrowserReadHumanBarrier(**dict(value))
    raise TypeError("browser read human barrier is required")


def _authority_claim_present(value: object) -> bool:
    if isinstance(value, (ControlledBrowserReadRequest, BrowserReadHumanBarrier)):
        value = value.to_dict()
    elif hasattr(value, "to_dict"):
        value = value.to_dict()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in _AUTHORITY_FIELD_NAMES and item is not False:
                return True
            if _authority_claim_present(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_authority_claim_present(item) for item in value)
    return False


def _blocked(reason_codes: tuple[str, ...]) -> ControlledBrowserReadResult:
    return _result(
        status=CONTROLLED_BROWSER_READ_BLOCKED,
        reason_codes=reason_codes,
        request_hash=None,
        context_hash=None,
        barrier_hash=None,
        source_kind=None,
        source_hash=None,
        inline_html_read=False,
        local_file_read=False,
    )


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    request_hash: str | None,
    context_hash: str | None,
    barrier_hash: str | None,
    source_kind: str | None,
    source_hash: str | None,
    title: str | None = None,
    text_hash: str | None = None,
    links: tuple[str, ...] = (),
    inline_html_read: bool,
    local_file_read: bool,
) -> ControlledBrowserReadResult:
    material = {
        "schema_version": CONTROLLED_BROWSER_READ_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "request_hash": request_hash,
        "context_hash": context_hash,
        "barrier_hash": barrier_hash,
        "source_kind": source_kind,
        "source_hash": source_hash,
        "title": title,
        "text_hash": text_hash,
        "links": tuple(links),
        "inline_html_read": inline_html_read,
        "local_file_read": local_file_read,
    }
    return ControlledBrowserReadResult(
        schema_version=CONTROLLED_BROWSER_READ_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        request_hash=request_hash,
        context_hash=context_hash,
        barrier_hash=barrier_hash,
        source_kind=source_kind,
        source_hash=source_hash,
        title=title,
        text_hash=text_hash,
        links=links,
        result_hash=_stable_hash(material),
        inline_html_read=inline_html_read,
        local_file_read=local_file_read,
    )


def _looks_remote_or_special(value: str) -> bool:
    lowered = value.strip().casefold()
    return lowered.startswith(_REMOTE_PREFIXES) or lowered.startswith(_UNSAFE_URI_PREFIXES)


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _required_hash(name: str, value: object) -> str:
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _text_tuple(name: str, values: object) -> tuple[str, ...]:
    if isinstance(values, str) or not isinstance(values, (tuple, list)) or not values:
        raise ValueError(f"{name} must be a non-empty tuple or list")
    return tuple(sorted(_required_text(name, item).casefold() for item in values))


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: object) -> str:
    material = json.dumps(_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        raise TypeError("floating point evidence is ambiguous")
    if isinstance(value, Mapping):
        return {str(key): _fingerprint(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list)):
        return tuple(_fingerprint(item) for item in value)
    return {"unsupported_type": type(value).__name__}
