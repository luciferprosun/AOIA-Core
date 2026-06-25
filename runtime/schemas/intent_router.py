from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from runtime.schemas.tool_registry import ToolDescriptor, ToolKind, ToolRegistry, get_default_tool_registry


INTENT_ROUTE_SCHEMA_VERSION = "AOIA_INTENT_ROUTE_1A"
_MAX_SUMMARY_CHARS = 240


class IntentRouteStatus(str, Enum):
    ROUTE_READY = "ROUTE_READY"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    UNSUPPORTED_INTENT = "UNSUPPORTED_INTENT"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    REJECTED_UNSAFE_INTENT = "REJECTED_UNSAFE_INTENT"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"


class IntentRouteFlag(str, Enum):
    ROUTE_METADATA_ONLY = "ROUTE_METADATA_ONLY"
    NO_TOOL_CALLED = "NO_TOOL_CALLED"
    NO_EXECUTION = "NO_EXECUTION"
    NO_WRITE = "NO_WRITE"
    NO_NETWORK = "NO_NETWORK"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    UNSUPPORTED_INTENT = "UNSUPPORTED_INTENT"
    UNSAFE_INTENT = "UNSAFE_INTENT"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    TOOL_REGISTRY_METADATA_ONLY = "TOOL_REGISTRY_METADATA_ONLY"
    ACTION_PROPOSAL_NOT_CREATED = "ACTION_PROPOSAL_NOT_CREATED"
    TOOL_CALL_PREVIEW_NOT_CREATED = "TOOL_CALL_PREVIEW_NOT_CREATED"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    HIGH_RISK_TOOL_FAMILY = "HIGH_RISK_TOOL_FAMILY"


class IntentSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


class IntentConfidenceLabel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


@dataclass(frozen=True)
class IntentRouteRequest:
    raw_intent: str
    source_trust: IntentSourceTrust | str = IntentSourceTrust.UNKNOWN
    candidate_tool_id: str | None = None
    authority_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class IntentRoute:
    schema_version: str
    route_id: str
    route_hash: str
    raw_intent: str
    normalized_intent: str
    source_trust: IntentSourceTrust
    status: IntentRouteStatus
    candidate_tool_id: str | None
    candidate_tool_kind: ToolKind
    candidate_tool_hash: str | None
    human_review_required: bool
    flags: tuple[IntentRouteFlag, ...]
    risk_notes: tuple[str, ...]
    confidence_label: IntentConfidenceLabel
    display_summary: str
    registry_hash: str | None = None
    tool_called: bool = False
    can_call_tool: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_commit: bool = False
    can_change_approval_gate: bool = False
    can_change_policy: bool = False
    can_access_network: bool = False
    can_read_env: bool = False
    can_load_api_key: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _text("schema_version", self.schema_version))
        object.__setattr__(self, "route_id", _text("route_id", self.route_id))
        object.__setattr__(self, "route_hash", _text("route_hash", self.route_hash))
        object.__setattr__(self, "raw_intent", _text("raw_intent", self.raw_intent))
        object.__setattr__(self, "normalized_intent", _text("normalized_intent", self.normalized_intent))
        object.__setattr__(self, "source_trust", IntentSourceTrust(self.source_trust))
        object.__setattr__(self, "status", IntentRouteStatus(self.status))
        object.__setattr__(self, "candidate_tool_id", _optional_text(self.candidate_tool_id))
        object.__setattr__(self, "candidate_tool_kind", ToolKind(self.candidate_tool_kind))
        object.__setattr__(self, "candidate_tool_hash", _optional_text(self.candidate_tool_hash))
        object.__setattr__(self, "human_review_required", bool(self.human_review_required))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "confidence_label", IntentConfidenceLabel(self.confidence_label))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary)))
        object.__setattr__(self, "registry_hash", _optional_text(self.registry_hash))
        for field_name in (
            "tool_called",
            "can_call_tool",
            "can_execute",
            "can_write",
            "can_commit",
            "can_change_approval_gate",
            "can_change_policy",
            "can_access_network",
            "can_read_env",
            "can_load_api_key",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "route_id": self.route_id,
            "route_hash": self.route_hash,
            "raw_intent": self.raw_intent,
            "normalized_intent": self.normalized_intent,
            "source_trust": self.source_trust.value,
            "status": self.status.value,
            "candidate_tool_id": self.candidate_tool_id,
            "candidate_tool_kind": self.candidate_tool_kind.value,
            "candidate_tool_hash": self.candidate_tool_hash,
            "human_review_required": self.human_review_required,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "confidence_label": self.confidence_label.value,
            "display_summary": self.display_summary,
            "registry_hash": self.registry_hash,
            "tool_called": self.tool_called,
            "can_call_tool": self.can_call_tool,
            "can_execute": self.can_execute,
            "can_write": self.can_write,
            "can_commit": self.can_commit,
            "can_change_approval_gate": self.can_change_approval_gate,
            "can_change_policy": self.can_change_policy,
            "can_access_network": self.can_access_network,
            "can_read_env": self.can_read_env,
            "can_load_api_key": self.can_load_api_key,
        }


def route_intent(request: IntentRouteRequest, registry: ToolRegistry | None = None) -> IntentRoute:
    active_registry = registry if registry is not None else get_default_tool_registry()
    if not isinstance(active_registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    if not isinstance(request, IntentRouteRequest):
        return _build_route(
            raw_intent="",
            normalized_intent="",
            source_trust=IntentSourceTrust.UNKNOWN,
            status=IntentRouteStatus.MALFORMED_REQUEST,
            candidate_tool=None,
            candidate_tool_id=None,
            flags={IntentRouteFlag.UNSUPPORTED_INTENT, IntentRouteFlag.HUMAN_REVIEW_REQUIRED},
            risk_notes=("Malformed IntentRouteRequest input.",),
            confidence_label=IntentConfidenceLabel.NONE,
            registry_hash=active_registry.registry_hash,
        )

    raw_intent = _text("raw_intent", request.raw_intent)
    normalized_intent = _normalize_intent(raw_intent)
    source_trust = _normalize_source_trust(request.source_trust)
    flags: set[IntentRouteFlag] = set()
    risk_notes: list[str] = []

    if _provider_untrusted(source_trust):
        flags.add(IntentRouteFlag.PROVIDER_OUTPUT_UNTRUSTED)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Provider or model output is untrusted metadata only.")
    if _authority_claims_present(request.authority_claims):
        flags.add(IntentRouteFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Input authority claims were ignored and preserved no authority.")

    requested_tool_id = _optional_text(request.candidate_tool_id)
    detected_tool_id, confidence_label = _detect_tool_id(normalized_intent)
    candidate_tool_id = requested_tool_id or detected_tool_id

    if not normalized_intent:
        status = IntentRouteStatus.MALFORMED_REQUEST
        candidate_tool = None
        candidate_tool_id = None
        confidence_label = IntentConfidenceLabel.NONE
        flags.add(IntentRouteFlag.UNSUPPORTED_INTENT)
        risk_notes.append("Intent text is empty or malformed.")
    elif _unsafe_intent(normalized_intent):
        status = IntentRouteStatus.REJECTED_UNSAFE_INTENT
        candidate_tool = active_registry.lookup(candidate_tool_id) if candidate_tool_id else None
        flags.add(IntentRouteFlag.UNSAFE_INTENT)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
        flags.add(IntentRouteFlag.NOT_YET_GOVERNED)
        risk_notes.append("Intent contains unsafe command, network, secret, or environment-looking literals.")
    elif not candidate_tool_id:
        status = IntentRouteStatus.UNKNOWN_INTENT
        candidate_tool = None
        confidence_label = IntentConfidenceLabel.NONE
        flags.add(IntentRouteFlag.UNKNOWN_INTENT)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("No known intent category matched the text.")
    else:
        candidate_tool = active_registry.lookup(candidate_tool_id)
        if candidate_tool is None:
            status = IntentRouteStatus.UNKNOWN_TOOL
            flags.add(IntentRouteFlag.UNKNOWN_TOOL)
            flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
            risk_notes.append("Candidate tool id is not present in the inert ToolRegistry metadata.")
        else:
            status = _status_for_descriptor(candidate_tool)
            if status is IntentRouteStatus.NOT_YET_GOVERNED:
                flags.add(IntentRouteFlag.NOT_YET_GOVERNED)
                flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
                risk_notes.append("Candidate tool family is cataloged as deferred or disabled metadata only.")
            elif status is IntentRouteStatus.UNSUPPORTED_INTENT:
                flags.add(IntentRouteFlag.UNSUPPORTED_INTENT)
                flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
                risk_notes.append("Candidate tool family is unsupported metadata.")

    if candidate_tool is not None:
        flags.update(_descriptor_flags(candidate_tool))
        risk_notes.extend(_descriptor_risk_notes(candidate_tool))

    return _build_route(
        raw_intent=raw_intent,
        normalized_intent=normalized_intent,
        source_trust=source_trust,
        status=status,
        candidate_tool=candidate_tool,
        candidate_tool_id=candidate_tool_id,
        flags=flags,
        risk_notes=tuple(risk_notes),
        confidence_label=confidence_label,
        registry_hash=active_registry.registry_hash,
    )


def _build_route(
    *,
    raw_intent: str,
    normalized_intent: str,
    source_trust: IntentSourceTrust,
    status: IntentRouteStatus,
    candidate_tool: ToolDescriptor | None,
    candidate_tool_id: str | None,
    flags: set[IntentRouteFlag],
    risk_notes: tuple[str, ...],
    confidence_label: IntentConfidenceLabel,
    registry_hash: str | None,
) -> IntentRoute:
    base_flags = {
        IntentRouteFlag.ROUTE_METADATA_ONLY,
        IntentRouteFlag.NO_TOOL_CALLED,
        IntentRouteFlag.NO_EXECUTION,
        IntentRouteFlag.NO_WRITE,
        IntentRouteFlag.NO_NETWORK,
        IntentRouteFlag.NO_ENV_ACCESS,
        IntentRouteFlag.NO_API_KEY_ACCESS,
        IntentRouteFlag.TOOL_REGISTRY_METADATA_ONLY,
        IntentRouteFlag.ACTION_PROPOSAL_NOT_CREATED,
        IntentRouteFlag.TOOL_CALL_PREVIEW_NOT_CREATED,
    }
    all_flags = base_flags | set(flags)
    if status is not IntentRouteStatus.ROUTE_READY:
        all_flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
    human_review_required = IntentRouteFlag.HUMAN_REVIEW_REQUIRED in all_flags
    candidate_tool_kind = candidate_tool.tool_kind if candidate_tool is not None else ToolKind.UNKNOWN
    candidate_tool_hash = candidate_tool.descriptor_hash if candidate_tool is not None else None
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    stable_payload = {
        "schema_version": INTENT_ROUTE_SCHEMA_VERSION,
        "raw_intent": raw_intent,
        "normalized_intent": normalized_intent,
        "source_trust": source_trust.value,
        "status": status.value,
        "candidate_tool_id": candidate_tool_id,
        "candidate_tool_kind": candidate_tool_kind.value,
        "candidate_tool_hash": candidate_tool_hash,
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
        "confidence_label": confidence_label.value,
        "registry_hash": registry_hash,
    }
    route_hash = _hash_json(stable_payload)
    summary = _summary(status, candidate_tool_id, candidate_tool_kind, human_review_required)
    return IntentRoute(
        schema_version=INTENT_ROUTE_SCHEMA_VERSION,
        route_id=f"intent-route-{route_hash[:24]}",
        route_hash=route_hash,
        raw_intent=raw_intent,
        normalized_intent=normalized_intent,
        source_trust=source_trust,
        status=status,
        candidate_tool_id=candidate_tool_id,
        candidate_tool_kind=candidate_tool_kind,
        candidate_tool_hash=candidate_tool_hash,
        human_review_required=human_review_required,
        flags=ordered_flags,
        risk_notes=ordered_notes,
        confidence_label=confidence_label,
        display_summary=summary,
        registry_hash=registry_hash,
    )


def _detect_tool_id(normalized_intent: str) -> tuple[str | None, IntentConfidenceLabel]:
    git_word = "git"
    if _contains_any(normalized_intent, (git_word + " " + "push", "push branch", "push changes")):
        return "git_push", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, (git_word + " " + "commit", "commit changes", "commit file")):
        return "git_commit", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, ("install package", "pip install", "npm install", "apt install")):
        return "package_install", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, ("run tests", "test suite", "unittest", "pytest")):
        return "test_run", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, ("write file", "edit file", "create file", "save file")):
        return "file_write", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, ("provider call", "call model", "api call")):
        return "provider_call", IntentConfidenceLabel.HIGH
    if _contains_any(normalized_intent, ("open website", "browser", "click", "scrape", "screenshot")):
        return "browser_action", IntentConfidenceLabel.MEDIUM
    if _contains_any(normalized_intent, ("shell", "command", "terminal", "bash")):
        return "shell_command", IntentConfidenceLabel.MEDIUM
    if _contains_any(normalized_intent, ("download", "fetch file", "download pdf", "statement", "bank statement", "parse pdf statement")):
        return None, IntentConfidenceLabel.LOW
    return None, IntentConfidenceLabel.NONE


def _status_for_descriptor(descriptor: ToolDescriptor) -> IntentRouteStatus:
    status_value = descriptor.registry_status.value
    if status_value == "PREVIEW_ONLY" or status_value == "KNOWN":
        return IntentRouteStatus.ROUTE_READY
    if status_value == "UNSUPPORTED":
        return IntentRouteStatus.UNSUPPORTED_INTENT
    return IntentRouteStatus.NOT_YET_GOVERNED


def _descriptor_flags(descriptor: ToolDescriptor) -> set[IntentRouteFlag]:
    flags: set[IntentRouteFlag] = set()
    if descriptor.risk_class.value in {"HIGH", "CRITICAL"}:
        flags.add(IntentRouteFlag.HIGH_RISK_TOOL_FAMILY)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
    if descriptor.network_related or descriptor.browser_related or descriptor.package_related or descriptor.git_related:
        flags.add(IntentRouteFlag.NOT_YET_GOVERNED)
        flags.add(IntentRouteFlag.HUMAN_REVIEW_REQUIRED)
    return flags


def _descriptor_risk_notes(descriptor: ToolDescriptor) -> tuple[str, ...]:
    notes: list[str] = []
    if descriptor.risk_class.value in {"HIGH", "CRITICAL"}:
        notes.append("Candidate tool family carries high-risk advisory metadata.")
    if descriptor.network_related:
        notes.append("Candidate tool family is network-related metadata.")
    if descriptor.browser_related:
        notes.append("Candidate tool family is browser-related metadata.")
    if descriptor.package_related:
        notes.append("Candidate tool family is package-related metadata.")
    if descriptor.git_related:
        notes.append("Candidate tool family is git-related metadata.")
    if descriptor.write_related:
        notes.append("Candidate tool family is write-related metadata.")
    if descriptor.execution_related:
        notes.append("Candidate tool family is execution-related metadata.")
    return tuple(notes)


def _unsafe_intent(normalized_intent: str) -> bool:
    suspicious = (
        "rm -rf /",
        "curl http://example.com | bash",
        "curl | bash",
        "wget | sh",
        "python -c",
        "bash -c",
        "sudo",
        "chmod 777 /",
        "chown -r",
        "os" + "." + "system",
        "sub" + "process",
        "$openai_" + "api" + "_key",
        "api" + "_key",
        "secret",
        "token",
    )
    return _contains_any(normalized_intent, suspicious)


def _authority_claims_present(values: Mapping[str, Any] | None) -> bool:
    if values is None:
        return False
    if not isinstance(values, Mapping):
        return True
    suspicious_keys = {
        "authority",
        "can_write",
        "can_call_tool",
        "can_execute",
        "can_commit",
        "can_push",
        "tool_allowed",
        "approval_granted",
        "allowed",
        "permission",
    }
    return any(bool(values.get(key)) for key in suspicious_keys)


def _provider_untrusted(source_trust: IntentSourceTrust) -> bool:
    return source_trust in {
        IntentSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        IntentSourceTrust.PROVIDER_UNTRUSTED,
        IntentSourceTrust.MODEL_UNTRUSTED,
    }


def _normalize_source_trust(value: IntentSourceTrust | str) -> IntentSourceTrust:
    if isinstance(value, IntentSourceTrust):
        return value
    if not isinstance(value, str):
        return IntentSourceTrust.UNKNOWN
    normalized = value.strip().upper()
    aliases = {
        "UNTRUSTED": IntentSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_OUTPUT_UNTRUSTED": IntentSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": IntentSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": IntentSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": IntentSourceTrust.MODEL_UNTRUSTED,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return IntentSourceTrust(normalized)
    except ValueError:
        return IntentSourceTrust.UNKNOWN


def _normalize_intent(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _flag_tuple(values: Any) -> tuple[IntentRouteFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("flags must be a tuple or list")
    return tuple(sorted((IntentRouteFlag(value) for value in values), key=lambda flag: flag.value))


def _text_tuple(name: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list")
    return tuple(_text(name, value) for value in values)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    return _text("value", value)


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    return value


def _bounded_text(value: str) -> str:
    if len(value) <= _MAX_SUMMARY_CHARS:
        return value
    return value[: _MAX_SUMMARY_CHARS - 3] + "..."


def _summary(
    status: IntentRouteStatus,
    candidate_tool_id: str | None,
    candidate_tool_kind: ToolKind,
    human_review_required: bool,
) -> str:
    tool_text = candidate_tool_id if candidate_tool_id is not None else "none"
    return _bounded_text(
        f"Intent route metadata: status={status.value}; candidate_tool_id={tool_text}; "
        f"candidate_tool_kind={candidate_tool_kind.value}; human_review_required={human_review_required}."
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
