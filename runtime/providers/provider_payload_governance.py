from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION = "1A"

PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY = "PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY"
PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED = "PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED"
PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED = "PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED"

PAYLOAD_EXPANSION_OK_INERT_METADATA = "PAYLOAD_EXPANSION_OK_INERT_METADATA"
PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW = "PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW"
PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING = "PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING"
PAYLOAD_EXPANSION_BLOCKED_STREAMING = "PAYLOAD_EXPANSION_BLOCKED_STREAMING"
PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK = "PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK"
PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER = "PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER"
PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL = "PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL"
PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION = "PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION"
PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET = "PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET"
PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM = "PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM"
PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT = "PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT"
PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH = "PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH"
PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE = "PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE"
PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE = "PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE"

_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "proposal_id",
        "provider_id",
        "base_payload_hash",
        "proposed_fields",
        "rationale",
        "created_at_tick",
        "expires_at_tick",
        "proposal_hash",
    }
)
_ALLOWED_FIELDS = _REQUIRED_FIELDS
_HEX = frozenset("0123456789abcdef")
_MAX_FIELD_COUNT = 8
_MAX_FIELD_NAME_LENGTH = 80
_MAX_STRING_VALUE_LENGTH = 2048
_MAX_COLLECTION_ITEMS = 16
_MAX_NESTING_DEPTH = 3

_INERT_METADATA_FIELD_NAMES = frozenset(
    {
        "metadata",
        "request_metadata",
        "review_metadata",
        "audit_metadata",
        "labels",
        "tags",
        "trace_label",
        "review_note",
    }
)
_REVIEW_FIELD_NAMES = frozenset(
    {
        "response_format",
        "seed",
        "top_p",
        "stop",
        "presence_penalty",
        "frequency_penalty",
        "system_instruction",
        "safety_settings",
        "candidate_count",
        "logit_bias",
    }
)
_TOOL_FIELD_NAMES = frozenset(
    {
        "tool",
        "tools",
        "tool_call",
        "tool_calls",
        "tool_choice",
        "function_call",
        "function_calls",
        "functions",
    }
)
_STREAM_FIELD_NAMES = frozenset({"stream", "streaming", "stream_options"})
_RETRY_FALLBACK_FIELD_NAMES = frozenset(
    {
        "retry",
        "retries",
        "max_retries",
        "fallback",
        "fallback_provider",
        "provider_fallback",
        "provider_switch",
    }
)
_NETWORK_BROWSER_FIELD_NAMES = frozenset(
    {
        "url",
        "uri",
        "endpoint",
        "callback_url",
        "webhook",
        "http_request",
        "network_request",
        "browser",
        "browser_action",
    }
)
_PACKAGE_FIELD_NAMES = frozenset(
    {
        "package_install",
        "package_manager",
        "pip_install",
        "npm_install",
        "dependencies",
        "requirements",
    }
)
_GIT_FIELD_NAMES = frozenset({"git", "git_action", "git_operation", "commit", "push"})
_SECRET_FIELD_NAMES = frozenset(
    {
        "secret",
        "secrets",
        "token",
        "access_token",
        "credential",
        "credentials",
        "password",
        "authorization",
        "bearer",
        "env",
        "environment",
        "headers",
        "api" + "_key",
        "get" + "env",
        "os." + "environ",
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "human_approved",
        "authority_granted",
        "can_approve",
        "can_execute",
        "can_write",
        "can_push",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "gate_eligible",
        "write_eligible",
        "apply_allowed",
    }
)
_UNBOUNDED_FIELD_NAMES = frozenset(
    {
        "context",
        "full_context",
        "unbounded_context",
        "messages",
        "contents",
        "files",
        "attachments",
        "include_workspace",
        "include_repository",
    }
)
_UNSUPPORTED_FIELD_NAMES = frozenset(
    {
        "images",
        "audio",
        "video",
        "modalities",
        "parallel_tool_calls",
        "service_tier",
        "store",
    }
)

_TOOL_PATTERN = re.compile(r"(?i)\b(?:tool[_ -]?calls?|function[_ -]?calls?|tool[_ -]?choice)\b")
_STREAM_PATTERN = re.compile(r"(?i)\b(?:stream|streaming)\b")
_RETRY_FALLBACK_PATTERN = re.compile(r"(?i)\b(?:retry|fallback|switch\s+(?:the\s+)?provider)\b")
_NETWORK_BROWSER_PATTERN = re.compile(
    r"(?i)(?:https?://|\burl\b|\bendpoint\b|\bwebhook\b|open\s+(?:the\s+)?browser|browser\s+action)"
)
_PACKAGE_PATTERN = re.compile(r"(?i)\b(?:pip\s+install|npm\s+install|package\s+install|requirements)\b")
_GIT_PATTERN = re.compile(r"(?i)\bgit\s+(?:push|commit|checkout|reset|merge)\b")
_SECRET_PATTERN = re.compile(
    r"(?i)(?:\bsecret\b|\btoken\b|\bcredential\b|\bpassword\b|authorization\s*:|"
    r"\bbearer\b|" + ("api" + r"[_ -]?key") + "|" + ("get" + "env") + "|" + ("os" + r"\." + "environ") + ")"
)
_AUTHORITY_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"authorization\s+granted|safe\s+to\s+(?:execute|write|push|call)|gate\s+satisfied|"
    r"can[_ -]?(?:approve|execute|write|push|call)|human[_ -]?approved|gate[_ -]?satisfied)\b"
)
_UNBOUNDED_PATTERN = re.compile(
    r"(?i)\b(?:full\s+context|entire\s+(?:workspace|repository)|unbounded\s+context|"
    r"include\s+(?:all\s+)?files|whole\s+repo)\b"
)

_BLOCKING_CATEGORIES = frozenset(
    {
        PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING,
        PAYLOAD_EXPANSION_BLOCKED_STREAMING,
        PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK,
        PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER,
        PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL,
        PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION,
        PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET,
        PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM,
        PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT,
        PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH,
        PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,
        PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE,
    }
)


@dataclass(frozen=True)
class ProviderPayloadExpansionGovernanceResult:
    schema_version: str
    status: str
    provider_id: str | None
    proposal_id: str | None
    base_payload_hash: str | None
    proposal_hash: str | None
    categories: tuple[str, ...]
    proposed_field_names: tuple[str, ...]
    governance_hash: str
    human_review_required: bool = True
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False
    payload_expansion_applied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION)
        if self.status not in {
            PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY,
            PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED,
            PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED,
        }:
            raise ValueError("unsupported payload governance status")
        object.__setattr__(self, "categories", tuple(sorted(set(self.categories))))
        object.__setattr__(self, "proposed_field_names", tuple(sorted(set(self.proposed_field_names))))
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "can_approve", False)
        object.__setattr__(self, "can_execute", False)
        object.__setattr__(self, "can_write", False)
        object.__setattr__(self, "can_push", False)
        object.__setattr__(self, "can_call_provider", False)
        object.__setattr__(self, "can_change_gate", False)
        object.__setattr__(self, "gate_satisfied", False)
        object.__setattr__(self, "payload_expansion_applied", False)
        if not _sha256_like(self.governance_hash):
            raise ValueError("governance_hash must be a sha256 hex digest")
        for value_name, value in (
            ("base_payload_hash", self.base_payload_hash),
            ("proposal_hash", self.proposal_hash),
        ):
            if value is not None and not _sha256_like(value):
                raise ValueError(f"{value_name} must be a sha256 hex digest or None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
            "status": self.status,
            "provider_id": self.provider_id,
            "proposal_id": self.proposal_id,
            "base_payload_hash": self.base_payload_hash,
            "proposal_hash": self.proposal_hash,
            "categories": self.categories,
            "proposed_field_names": self.proposed_field_names,
            "governance_hash": self.governance_hash,
            "human_review_required": True,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
            "payload_expansion_applied": False,
        }


def evaluate_provider_payload_expansion_governance(
    proposal: object,
    *,
    current_tick: int,
    expected_provider_id: str | None = None,
    expected_base_payload_hash: str | None = None,
) -> ProviderPayloadExpansionGovernanceResult:
    categories: list[str] = []
    provider_id: str | None = None
    proposal_id: str | None = None
    base_payload_hash: str | None = None
    proposal_hash: str | None = None
    proposed_field_names: tuple[str, ...] = ()
    normalized_fields: dict[str, Any] | None = None
    input_fingerprint = _fingerprint(proposal)

    try:
        tick = _nonnegative_int("current_tick", current_tick)
        expected_provider = _optional_text("expected_provider_id", expected_provider_id)
        expected_base_hash = _optional_hash("expected_base_payload_hash", expected_base_payload_hash)
    except (TypeError, ValueError):
        return _result(
            status=PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED,
            provider_id=None,
            proposal_id=None,
            base_payload_hash=None,
            proposal_hash=None,
            categories=(PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,),
            proposed_field_names=(),
            input_fingerprint=input_fingerprint,
            current_tick=None,
            expected_provider_id=None,
            expected_base_payload_hash=None,
        )

    if not isinstance(proposal, Mapping):
        return _result(
            status=PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED,
            provider_id=None,
            proposal_id=None,
            base_payload_hash=None,
            proposal_hash=None,
            categories=(PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE,),
            proposed_field_names=(),
            input_fingerprint=input_fingerprint,
            current_tick=tick,
            expected_provider_id=expected_provider,
            expected_base_payload_hash=expected_base_hash,
        )

    data = dict(proposal)
    if any(field not in data for field in _REQUIRED_FIELDS):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)
    if any(field not in _ALLOWED_FIELDS for field in data):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)

    if data.get("schema_version") != PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION:
        categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)

    try:
        provider_id = _required_text("provider_id", data.get("provider_id"))
        proposal_id = _required_text("proposal_id", data.get("proposal_id"))
        base_payload_hash = _optional_hash("base_payload_hash", data.get("base_payload_hash"))
        proposal_hash = _optional_hash("proposal_hash", data.get("proposal_hash"))
        rationale = _required_text("rationale", data.get("rationale"))
        created_at_tick = _nonnegative_int("created_at_tick", data.get("created_at_tick"))
        expires_at_tick = _nonnegative_int("expires_at_tick", data.get("expires_at_tick"))
        normalized_fields = _normalize_proposed_fields(data.get("proposed_fields"))
        proposed_field_names = tuple(normalized_fields)
    except (TypeError, ValueError):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE)
        rationale = ""
        created_at_tick = None
        expires_at_tick = None

    if provider_id is not None and expected_provider is not None and provider_id != expected_provider:
        categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)
    if base_payload_hash is not None and expected_base_hash is not None and base_payload_hash != expected_base_hash:
        categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)
    if created_at_tick is not None and expires_at_tick is not None:
        if created_at_tick > tick or expires_at_tick < tick or expires_at_tick < created_at_tick:
            categories.append(PAYLOAD_EXPANSION_BLOCKED_STALE_EVIDENCE)

    if normalized_fields is not None:
        categories.extend(_classify_proposed_fields(normalized_fields, rationale))
        if (
            proposal_id is not None
            and provider_id is not None
            and base_payload_hash is not None
            and proposal_hash is not None
            and created_at_tick is not None
            and expires_at_tick is not None
        ):
            computed_hash = compute_provider_payload_expansion_hash(
                proposal_id=proposal_id,
                provider_id=provider_id,
                base_payload_hash=base_payload_hash,
                proposed_fields=normalized_fields,
                rationale=rationale,
                created_at_tick=created_at_tick,
                expires_at_tick=expires_at_tick,
            )
            if proposal_hash != computed_hash:
                categories.append(PAYLOAD_EXPANSION_BLOCKED_SCHEMA_MISMATCH)

    deduped = tuple(sorted(set(categories)))
    if any(category in _BLOCKING_CATEGORIES for category in deduped):
        status = PAYLOAD_EXPANSION_GOVERNANCE_BLOCKED
    elif PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW in deduped:
        status = PAYLOAD_EXPANSION_GOVERNANCE_REVIEW_REQUIRED
    else:
        status = PAYLOAD_EXPANSION_GOVERNANCE_ALLOWED_METADATA_ONLY
        deduped = (PAYLOAD_EXPANSION_OK_INERT_METADATA,)

    return _result(
        status=status,
        provider_id=provider_id,
        proposal_id=proposal_id,
        base_payload_hash=base_payload_hash,
        proposal_hash=proposal_hash,
        categories=deduped,
        proposed_field_names=proposed_field_names,
        input_fingerprint=input_fingerprint,
        current_tick=tick,
        expected_provider_id=expected_provider,
        expected_base_payload_hash=expected_base_hash,
    )


def compute_provider_payload_expansion_hash(
    *,
    proposal_id: str,
    provider_id: str,
    base_payload_hash: str,
    proposed_fields: Mapping[str, Any],
    rationale: str,
    created_at_tick: int,
    expires_at_tick: int,
) -> str:
    material = {
        "schema_version": PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
        "proposal_id": _required_text("proposal_id", proposal_id),
        "provider_id": _required_text("provider_id", provider_id),
        "base_payload_hash": _optional_hash("base_payload_hash", base_payload_hash),
        "proposed_fields": _normalize_proposed_fields(proposed_fields),
        "rationale": _required_text("rationale", rationale),
        "created_at_tick": _nonnegative_int("created_at_tick", created_at_tick),
        "expires_at_tick": _nonnegative_int("expires_at_tick", expires_at_tick),
    }
    return _stable_hash(material)


def _classify_proposed_fields(fields: Mapping[str, Any], rationale: str) -> tuple[str, ...]:
    categories: list[str] = []
    field_names = tuple(fields)
    text_values = (*_field_text_values(fields), rationale)
    lowered_field_names = tuple(name.casefold() for name in field_names)

    if any(_matches_name(name, _TOOL_FIELD_NAMES) for name in lowered_field_names) or any(_TOOL_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_TOOL_CALLING)
    if any(_matches_name(name, _STREAM_FIELD_NAMES) for name in lowered_field_names) or any(_STREAM_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_STREAMING)
    if any(_matches_name(name, _RETRY_FALLBACK_FIELD_NAMES) for name in lowered_field_names) or any(_RETRY_FALLBACK_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_RETRY_FALLBACK)
    if any(_matches_name(name, _NETWORK_BROWSER_FIELD_NAMES) for name in lowered_field_names) or any(_NETWORK_BROWSER_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_NETWORK_OR_BROWSER)
    if any(_matches_name(name, _PACKAGE_FIELD_NAMES) for name in lowered_field_names) or any(_PACKAGE_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_PACKAGE_INSTALL)
    if any(_matches_name(name, _GIT_FIELD_NAMES) for name in lowered_field_names) or any(_GIT_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_GIT_ACTION)
    if any(_matches_name(name, _SECRET_FIELD_NAMES) for name in lowered_field_names) or any(_SECRET_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_ENV_OR_SECRET)
    if any(_matches_name(name, _AUTHORITY_FIELD_NAMES) for name in lowered_field_names) or any(_AUTHORITY_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_AUTHORITY_CLAIM)
    if any(_matches_name(name, _UNBOUNDED_FIELD_NAMES) for name in lowered_field_names) or any(_UNBOUNDED_PATTERN.search(value) for value in text_values):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_UNBOUNDED_CONTEXT)
    if any(_matches_name(name, _UNSUPPORTED_FIELD_NAMES) for name in lowered_field_names):
        categories.append(PAYLOAD_EXPANSION_BLOCKED_AMBIGUOUS_EVIDENCE)
    if any(_matches_name(name, _REVIEW_FIELD_NAMES) for name in lowered_field_names):
        categories.append(PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW)

    if not categories and all(_matches_name(name, _INERT_METADATA_FIELD_NAMES) for name in lowered_field_names):
        categories.append(PAYLOAD_EXPANSION_OK_INERT_METADATA)
    elif not categories:
        categories.append(PAYLOAD_EXPANSION_REQUIRES_HUMAN_REVIEW)
    return tuple(categories)


def _result(
    *,
    status: str,
    provider_id: str | None,
    proposal_id: str | None,
    base_payload_hash: str | None,
    proposal_hash: str | None,
    categories: tuple[str, ...],
    proposed_field_names: tuple[str, ...],
    input_fingerprint: Any,
    current_tick: int | None,
    expected_provider_id: str | None,
    expected_base_payload_hash: str | None,
) -> ProviderPayloadExpansionGovernanceResult:
    canonical_categories = tuple(sorted(set(categories)))
    canonical_field_names = tuple(sorted(set(proposed_field_names)))
    material = {
        "schema_version": PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
        "status": status,
        "provider_id": provider_id,
        "proposal_id": proposal_id,
        "base_payload_hash": base_payload_hash,
        "proposal_hash": proposal_hash,
        "categories": canonical_categories,
        "proposed_field_names": canonical_field_names,
        "input_fingerprint": input_fingerprint,
        "current_tick": current_tick,
        "expected_provider_id": expected_provider_id,
        "expected_base_payload_hash": expected_base_payload_hash,
        "human_review_required": True,
        "can_approve": False,
        "can_execute": False,
        "can_write": False,
        "can_push": False,
        "can_call_provider": False,
        "can_change_gate": False,
        "gate_satisfied": False,
        "payload_expansion_applied": False,
    }
    return ProviderPayloadExpansionGovernanceResult(
        schema_version=PROVIDER_PAYLOAD_GOVERNANCE_SCHEMA_VERSION,
        status=status,
        provider_id=provider_id,
        proposal_id=proposal_id,
        base_payload_hash=base_payload_hash,
        proposal_hash=proposal_hash,
        categories=canonical_categories,
        proposed_field_names=canonical_field_names,
        governance_hash=_stable_hash(material),
    )


def _normalize_proposed_fields(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError("proposed_fields must be a non-empty mapping")
    if len(value) > _MAX_FIELD_COUNT:
        raise ValueError("proposed_fields contains too many fields")
    normalized: dict[str, Any] = {}
    for key in sorted(value):
        name = _required_text("proposed field name", key)
        if len(name) > _MAX_FIELD_NAME_LENGTH:
            raise ValueError("proposed field name is too long")
        normalized[name] = _normalize_payload_value(value[key], depth=0)
    return normalized


def _normalize_payload_value(value: object, *, depth: int) -> Any:
    if depth > _MAX_NESTING_DEPTH:
        raise ValueError("proposed field value is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000:
            raise ValueError("numeric proposed field value is excessive")
        return value
    if isinstance(value, float):
        if abs(value) > 1_000_000:
            raise ValueError("numeric proposed field value is excessive")
        return value
    if isinstance(value, str):
        if len(value) > _MAX_STRING_VALUE_LENGTH:
            raise ValueError("string proposed field value is excessive")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ValueError("mapping proposed field value is excessive")
        return {
            _required_text("proposed nested field name", key): _normalize_payload_value(item, depth=depth + 1)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise ValueError("sequence proposed field value is excessive")
        return tuple(_normalize_payload_value(item, depth=depth + 1) for item in value)
    raise TypeError("proposed field contains unsupported value")


def _field_text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_field_text_values(item))
        return tuple(values)
    if isinstance(value, (tuple, list)):
        values = []
        for item in value:
            values.extend(_field_text_values(item))
        return tuple(values)
    return ()


def _matches_name(name: str, names: frozenset[str]) -> bool:
    normalized = name.strip().casefold()
    return normalized in names or any(normalized.endswith("." + item) for item in names)


def _fingerprint(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _fingerprint(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return tuple(_fingerprint(item) for item in value)
    return {"unsupported_type": type(value).__name__}


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    if not _sha256_like(value):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return str(value).lower()


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: Mapping[str, Any]) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
