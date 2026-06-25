from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


TOOL_CALL_PREVIEW_SCHEMA_VERSION = "AOIA_TOOL_CALL_PREVIEW_1A"
_MAX_ARGUMENT_PREVIEW_CHARS = 1200


class ToolCallPreviewStatus(str, Enum):
    PREVIEW_READY = "PREVIEW_READY"
    INVALID_TOOL_NAME = "INVALID_TOOL_NAME"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    BLOCKED_UNSAFE_TOOL_NAME = "BLOCKED_UNSAFE_TOOL_NAME"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ToolCallPreviewFlag(str, Enum):
    PREVIEW_ONLY = "PREVIEW_ONLY"
    NO_TOOL_CALLED = "NO_TOOL_CALLED"
    NO_EXECUTION = "NO_EXECUTION"
    NO_WRITE = "NO_WRITE"
    NO_NETWORK = "NO_NETWORK"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    UNKNOWN_TOOL_NAME = "UNKNOWN_TOOL_NAME"
    UNSAFE_TOOL_NAME = "UNSAFE_TOOL_NAME"
    SUSPICIOUS_ARGUMENTS = "SUSPICIOUS_ARGUMENTS"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    CRITIC_WARNING_PRESENT = "CRITIC_WARNING_PRESENT"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"


@dataclass(frozen=True)
class ToolCallPreviewRequest:
    proposed_tool_name: str
    proposed_arguments: Any = None
    proposed_tool_namespace: str = ""
    source_action_proposal_id: str | None = None
    source_action_proposal_hash: str | None = None
    provider_output_trust: str | None = None
    critic_verdict: str | None = None
    authority_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ToolCallPreview:
    schema_version: str
    preview_id: str
    preview_hash: str
    proposed_tool_name: str
    proposed_tool_namespace: str
    proposed_arguments: Any
    argument_hash: str
    source_action_proposal_id: str | None
    source_action_proposal_hash: str | None
    provider_output_trust: str | None
    critic_verdict: str | None
    human_review_required: bool
    status: ToolCallPreviewStatus
    flags: tuple[ToolCallPreviewFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    bounded_argument_preview: str
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
        object.__setattr__(self, "preview_id", _text("preview_id", self.preview_id))
        object.__setattr__(self, "preview_hash", _text("preview_hash", self.preview_hash))
        object.__setattr__(self, "proposed_tool_name", _text("proposed_tool_name", self.proposed_tool_name))
        object.__setattr__(self, "proposed_tool_namespace", _text("proposed_tool_namespace", self.proposed_tool_namespace))
        object.__setattr__(self, "proposed_arguments", _stable_json_value(self.proposed_arguments))
        object.__setattr__(self, "argument_hash", _text("argument_hash", self.argument_hash))
        object.__setattr__(self, "source_action_proposal_id", _optional_text(self.source_action_proposal_id))
        object.__setattr__(self, "source_action_proposal_hash", _optional_text(self.source_action_proposal_hash))
        object.__setattr__(self, "provider_output_trust", _optional_text(self.provider_output_trust))
        object.__setattr__(self, "critic_verdict", _optional_text(self.critic_verdict))
        object.__setattr__(self, "human_review_required", bool(self.human_review_required))
        object.__setattr__(self, "status", ToolCallPreviewStatus(self.status))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _text("display_summary", self.display_summary))
        object.__setattr__(self, "bounded_argument_preview", _text("bounded_argument_preview", self.bounded_argument_preview))
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
            "preview_id": self.preview_id,
            "preview_hash": self.preview_hash,
            "proposed_tool_name": self.proposed_tool_name,
            "proposed_tool_namespace": self.proposed_tool_namespace,
            "proposed_arguments": self.proposed_arguments,
            "argument_hash": self.argument_hash,
            "source_action_proposal_id": self.source_action_proposal_id,
            "source_action_proposal_hash": self.source_action_proposal_hash,
            "provider_output_trust": self.provider_output_trust,
            "critic_verdict": self.critic_verdict,
            "human_review_required": self.human_review_required,
            "status": self.status.value,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "bounded_argument_preview": self.bounded_argument_preview,
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


def build_tool_call_preview(request: ToolCallPreviewRequest) -> ToolCallPreview:
    if not isinstance(request, ToolCallPreviewRequest):
        return _build_preview(
            proposed_tool_name="",
            proposed_tool_namespace="",
            proposed_arguments={},
            source_action_proposal_id=None,
            source_action_proposal_hash=None,
            provider_output_trust=None,
            critic_verdict=None,
            status=ToolCallPreviewStatus.INVALID_ARGUMENTS,
            flags={
                ToolCallPreviewFlag.SUSPICIOUS_ARGUMENTS,
                ToolCallPreviewFlag.HUMAN_REVIEW_REQUIRED,
            },
            risk_notes=("Malformed ToolCallPreviewRequest input.",),
        )

    tool_name = _clean_text(request.proposed_tool_name)
    namespace = _clean_text(request.proposed_tool_namespace)
    provider_trust = _optional_text(request.provider_output_trust)
    critic_verdict = _optional_text(request.critic_verdict)
    source_id = _optional_text(request.source_action_proposal_id)
    source_hash = _optional_text(request.source_action_proposal_hash)
    flags: set[ToolCallPreviewFlag] = set()
    risk_notes: list[str] = []

    try:
        normalized_arguments = _stable_json_value(request.proposed_arguments)
    except (TypeError, ValueError):
        normalized_arguments = {}
        status = ToolCallPreviewStatus.INVALID_ARGUMENTS
        flags.add(ToolCallPreviewFlag.SUSPICIOUS_ARGUMENTS)
        risk_notes.append("Arguments were not deterministic JSON data.")
    else:
        status = ToolCallPreviewStatus.PREVIEW_READY

    if not tool_name:
        status = ToolCallPreviewStatus.INVALID_TOOL_NAME
        flags.add(ToolCallPreviewFlag.UNSAFE_TOOL_NAME)
        risk_notes.append("Tool name is empty or malformed.")
    elif _unsafe_tool_name(tool_name):
        status = ToolCallPreviewStatus.BLOCKED_UNSAFE_TOOL_NAME
        flags.add(ToolCallPreviewFlag.UNSAFE_TOOL_NAME)
        risk_notes.append("Tool name resembles an executable command, path, URL, or traversal.")
    else:
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.UNKNOWN_TOOL_NAME)
        risk_notes.append("Tool name was preserved as unknown metadata; no registry lookup was performed.")

    if _suspicious_arguments(normalized_arguments):
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.SUSPICIOUS_ARGUMENTS)
        risk_notes.append("Arguments contain suspicious command, network, secret, or environment-looking literals.")
    if provider_trust and provider_trust.strip().casefold() in {"untrusted", "untrusted_provider_output", "provider_untrusted"}:
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.PROVIDER_OUTPUT_UNTRUSTED)
        risk_notes.append("Provider output is untrusted metadata only.")
    if critic_verdict and _critic_warns(critic_verdict):
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.CRITIC_WARNING_PRESENT)
        risk_notes.append("Critic verdict contains warning, block, or reject metadata.")
    if _authority_claims_present(request.authority_claims):
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        risk_notes.append("Input authority claims were ignored and preserved no authority.")
    if _tool_category_requires_review(tool_name):
        status = _review_status(status)
        flags.add(ToolCallPreviewFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Tool name category appears shell, browser, network, package, provider, or git related.")

    return _build_preview(
        proposed_tool_name=tool_name,
        proposed_tool_namespace=namespace,
        proposed_arguments=normalized_arguments,
        source_action_proposal_id=source_id,
        source_action_proposal_hash=source_hash,
        provider_output_trust=provider_trust,
        critic_verdict=critic_verdict,
        status=status,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _build_preview(
    *,
    proposed_tool_name: str,
    proposed_tool_namespace: str,
    proposed_arguments: Any,
    source_action_proposal_id: str | None,
    source_action_proposal_hash: str | None,
    provider_output_trust: str | None,
    critic_verdict: str | None,
    status: ToolCallPreviewStatus,
    flags: set[ToolCallPreviewFlag],
    risk_notes: tuple[str, ...],
) -> ToolCallPreview:
    base_flags = {
        ToolCallPreviewFlag.PREVIEW_ONLY,
        ToolCallPreviewFlag.NO_TOOL_CALLED,
        ToolCallPreviewFlag.NO_EXECUTION,
        ToolCallPreviewFlag.NO_WRITE,
        ToolCallPreviewFlag.NO_NETWORK,
        ToolCallPreviewFlag.NO_ENV_ACCESS,
        ToolCallPreviewFlag.NO_API_KEY_ACCESS,
        ToolCallPreviewFlag.ACTION_PROPOSAL_METADATA_ONLY,
    }
    all_flags = set(flags) | base_flags
    if status is not ToolCallPreviewStatus.PREVIEW_READY or flags:
        all_flags.add(ToolCallPreviewFlag.HUMAN_REVIEW_REQUIRED)
    human_review_required = ToolCallPreviewFlag.HUMAN_REVIEW_REQUIRED in all_flags
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    normalized_arguments = _stable_json_value(proposed_arguments)
    argument_preview = _bounded_text(_canonical_json(normalized_arguments), _MAX_ARGUMENT_PREVIEW_CHARS)
    argument_hash = _hash_text(_canonical_json(normalized_arguments))
    preview_hash = _hash_text(
        _canonical_json(
            {
                "schema_version": TOOL_CALL_PREVIEW_SCHEMA_VERSION,
                "proposed_tool_name": proposed_tool_name,
                "proposed_tool_namespace": proposed_tool_namespace,
                "proposed_arguments": normalized_arguments,
                "argument_hash": argument_hash,
                "source_action_proposal_id": source_action_proposal_id,
                "source_action_proposal_hash": source_action_proposal_hash,
                "provider_output_trust": provider_output_trust,
                "critic_verdict": critic_verdict,
                "human_review_required": human_review_required,
                "status": status.value,
                "flags": [flag.value for flag in ordered_flags],
                "risk_notes": list(risk_notes),
            }
        )
    )
    display_summary = f"Tool call preview for {proposed_tool_name or '<invalid>'}: {status.value}."
    return ToolCallPreview(
        schema_version=TOOL_CALL_PREVIEW_SCHEMA_VERSION,
        preview_id="tool-call-preview-" + preview_hash[:24],
        preview_hash=preview_hash,
        proposed_tool_name=proposed_tool_name,
        proposed_tool_namespace=proposed_tool_namespace,
        proposed_arguments=normalized_arguments,
        argument_hash=argument_hash,
        source_action_proposal_id=source_action_proposal_id,
        source_action_proposal_hash=source_action_proposal_hash,
        provider_output_trust=provider_output_trust,
        critic_verdict=critic_verdict,
        human_review_required=human_review_required,
        status=status,
        flags=ordered_flags,
        risk_notes=risk_notes,
        display_summary=display_summary,
        bounded_argument_preview=argument_preview,
    )


def _review_status(status: ToolCallPreviewStatus) -> ToolCallPreviewStatus:
    if status is ToolCallPreviewStatus.PREVIEW_READY:
        return ToolCallPreviewStatus.REVIEW_REQUIRED
    return status


def _unsafe_tool_name(tool_name: str) -> bool:
    folded = tool_name.strip().casefold()
    if "/" in folded or "\\" in folded or ".." in folded:
        return True
    if "://" in folded:
        return True
    if folded in {"sh", "bash", "zsh", "python", "python3", "curl", "wget", "rm"}:
        return True
    unsafe_fragments = ("rm -rf", "python -c", "curl ", "wget ", "http://", "https://")
    return any(fragment in folded for fragment in unsafe_fragments)


def _suspicious_arguments(value: Any) -> bool:
    text = _canonical_json(value).casefold()
    patterns = (
        "rm -rf",
        "curl",
        "wget",
        "sub" + "process",
        "os" + "." + "system",
        "$" + "openai" + "_" + "api" + "_" + "key",
        "api" + "_" + "key",
        "secret",
        "token",
    )
    return any(pattern in text for pattern in patterns)


def _critic_warns(value: str) -> bool:
    folded = value.strip().casefold()
    return any(marker in folded for marker in ("warn", "block", "reject"))


def _authority_claims_present(value: Mapping[str, Any] | None) -> bool:
    if not value:
        return False
    suspicious_keys = {
        "can_execute",
        "tool_allowed",
        "approval_granted",
        "can_call_tool",
        "can_write",
        "can_commit",
        "can_change_approval_gate",
    }
    return any(key in suspicious_keys and bool(flag_value) for key, flag_value in value.items())


def _tool_category_requires_review(tool_name: str) -> bool:
    folded = tool_name.strip().casefold()
    markers = (
        "shell",
        "command",
        "browser",
        "http",
        "network",
        "package",
        "install",
        "provider",
        "g" + "it",
        "commit",
        "push",
    )
    return any(marker in folded for marker in markers)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_json_value(value: Any) -> Any:
    if value is None:
        return {}
    return json.loads(_canonical_json(value))


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "... truncated ..."


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    return text or None


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    return value


def _text_tuple(name: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list of text")
    return tuple(_text(name, value) for value in values)


def _flag_tuple(values: Any) -> tuple[ToolCallPreviewFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("flags must be a tuple or list")
    return tuple(ToolCallPreviewFlag(value) for value in values)
