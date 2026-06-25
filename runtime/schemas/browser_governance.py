from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


BROWSER_GOVERNANCE_SCHEMA_VERSION = "AOIA_BROWSER_GOVERNANCE_1A"
_MAX_SUMMARY_CHARS = 420


class BrowserGovernanceStatus(str, Enum):
    BROWSER_GOVERNANCE_CHECK_READY = "BROWSER_GOVERNANCE_CHECK_READY"
    BROWSER_REVIEW_REQUIRED = "BROWSER_REVIEW_REQUIRED"
    READ_ONLY_BROWSER_REVIEW_REQUIRED = "READ_ONLY_BROWSER_REVIEW_REQUIRED"
    BLOCKED_UNSAFE_BROWSER_URL = "BLOCKED_UNSAFE_BROWSER_URL"
    BLOCKED_ACTIVE_BROWSER_ACTION = "BLOCKED_ACTIVE_BROWSER_ACTION"
    BLOCKED_FORM_SUBMISSION = "BLOCKED_FORM_SUBMISSION"
    BLOCKED_LOGIN_OR_CREDENTIAL_RISK = "BLOCKED_LOGIN_OR_CREDENTIAL_RISK"
    BLOCKED_COOKIE_OR_SESSION_RISK = "BLOCKED_COOKIE_OR_SESSION_RISK"
    BLOCKED_DOWNLOAD_OR_UPLOAD = "BLOCKED_DOWNLOAD_OR_UPLOAD"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"


class BrowserGovernanceFlag(str, Enum):
    BROWSER_GOVERNANCE_METADATA_ONLY = "BROWSER_GOVERNANCE_METADATA_ONLY"
    NO_BROWSER_OPENED = "NO_BROWSER_OPENED"
    NO_BROWSER_ACTION = "NO_BROWSER_ACTION"
    NO_PAGE_FETCHED = "NO_PAGE_FETCHED"
    NO_PAGE_READ = "NO_PAGE_READ"
    NO_SCREENSHOT = "NO_SCREENSHOT"
    NO_CLICK = "NO_CLICK"
    NO_TYPING = "NO_TYPING"
    NO_SCROLL = "NO_SCROLL"
    NO_FORM_SUBMIT = "NO_FORM_SUBMIT"
    NO_DOWNLOAD = "NO_DOWNLOAD"
    NO_UPLOAD = "NO_UPLOAD"
    NO_COOKIE_ACCESS = "NO_COOKIE_ACCESS"
    NO_SESSION_ACCESS = "NO_SESSION_ACCESS"
    NO_CREDENTIAL_USE = "NO_CREDENTIAL_USE"
    NO_NETWORK = "NO_NETWORK"
    NO_PROVIDER_CALL = "NO_PROVIDER_CALL"
    NO_EXECUTION = "NO_EXECUTION"
    NO_WRITE = "NO_WRITE"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    READ_ONLY_BROWSER_METADATA = "READ_ONLY_BROWSER_METADATA"
    ACTIVE_BROWSER_ACTION_BLOCKED = "ACTIVE_BROWSER_ACTION_BLOCKED"
    FORM_SUBMIT_BLOCKED = "FORM_SUBMIT_BLOCKED"
    LOGIN_BLOCKED = "LOGIN_BLOCKED"
    COOKIE_BLOCKED = "COOKIE_BLOCKED"
    SESSION_BLOCKED = "SESSION_BLOCKED"
    CREDENTIAL_BLOCKED = "CREDENTIAL_BLOCKED"
    DOWNLOAD_BLOCKED = "DOWNLOAD_BLOCKED"
    UPLOAD_BLOCKED = "UPLOAD_BLOCKED"
    UNSAFE_URL = "UNSAFE_URL"
    SUSPICIOUS_URL = "SUSPICIOUS_URL"
    EXTERNAL_URL_REVIEW_REQUIRED = "EXTERNAL_URL_REVIEW_REQUIRED"
    LOCALHOST_BLOCKED = "LOCALHOST_BLOCKED"
    METADATA_SERVICE_BLOCKED = "METADATA_SERVICE_BLOCKED"
    FILE_URL_BLOCKED = "FILE_URL_BLOCKED"
    JAVASCRIPT_URL_BLOCKED = "JAVASCRIPT_URL_BLOCKED"
    DATA_URL_BLOCKED = "DATA_URL_BLOCKED"
    CHROME_URL_BLOCKED = "CHROME_URL_BLOCKED"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    SECRET_OR_TOKEN_PATTERN = "SECRET_OR_TOKEN_PATTERN"
    INCONSISTENT_HASH_METADATA = "INCONSISTENT_HASH_METADATA"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"
    TOOL_CALL_PREVIEW_METADATA_ONLY = "TOOL_CALL_PREVIEW_METADATA_ONLY"
    TOOL_REGISTRY_METADATA_ONLY = "TOOL_REGISTRY_METADATA_ONLY"
    INTENT_ROUTE_METADATA_ONLY = "INTENT_ROUTE_METADATA_ONLY"
    LOCAL_POLICY_METADATA_ONLY = "LOCAL_POLICY_METADATA_ONLY"
    TEST_RUNNER_METADATA_ONLY = "TEST_RUNNER_METADATA_ONLY"
    DOWNLOAD_GOVERNANCE_METADATA_ONLY = "DOWNLOAD_GOVERNANCE_METADATA_ONLY"
    STATEMENT_GOVERNANCE_METADATA_ONLY = "STATEMENT_GOVERNANCE_METADATA_ONLY"


class BrowserActionKind(str, Enum):
    READ_ONLY_VIEW = "READ_ONLY_VIEW"
    URL_REVIEW = "URL_REVIEW"
    SCREENSHOT_REQUEST = "SCREENSHOT_REQUEST"
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    FORM_SUBMIT = "FORM_SUBMIT"
    DOWNLOAD = "DOWNLOAD"
    UPLOAD = "UPLOAD"
    LOGIN = "LOGIN"
    COOKIE_ACCESS = "COOKIE_ACCESS"
    SESSION_ACCESS = "SESSION_ACCESS"
    UNKNOWN = "UNKNOWN"


class BrowserSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BrowserGovernanceRequest:
    action_kind: BrowserActionKind | str
    target_url: str
    source_trust: BrowserSourceTrust | str = BrowserSourceTrust.UNKNOWN
    source_action_proposal_id: str | None = None
    source_action_proposal_hash: str | None = None
    source_tool_call_preview_id: str | None = None
    source_tool_call_preview_hash: str | None = None
    source_intent_route_id: str | None = None
    source_intent_route_hash: str | None = None
    source_policy_check_id: str | None = None
    source_policy_check_hash: str | None = None
    source_test_runner_control_id: str | None = None
    source_test_runner_control_hash: str | None = None
    source_download_governance_id: str | None = None
    source_download_governance_hash: str | None = None
    source_statement_governance_id: str | None = None
    source_statement_governance_hash: str | None = None
    source_statuses: tuple[str, ...] | list[str] = ()
    source_flags: tuple[str, ...] | list[str] = ()
    metadata: Mapping[str, Any] | None = None
    authority_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class BrowserGovernanceCheck:
    schema_version: str
    browser_governance_id: str
    browser_governance_hash: str
    status: BrowserGovernanceStatus
    action_kind: BrowserActionKind
    target_url: str
    normalized_target_url: str
    target_url_hash: str
    source_trust: BrowserSourceTrust
    source_action_proposal_id: str | None
    source_action_proposal_hash: str | None
    source_tool_call_preview_id: str | None
    source_tool_call_preview_hash: str | None
    source_intent_route_id: str | None
    source_intent_route_hash: str | None
    source_policy_check_id: str | None
    source_policy_check_hash: str | None
    source_test_runner_control_id: str | None
    source_test_runner_control_hash: str | None
    source_download_governance_id: str | None
    source_download_governance_hash: str | None
    source_statement_governance_id: str | None
    source_statement_governance_hash: str | None
    human_review_required: bool
    flags: tuple[BrowserGovernanceFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    browser_opened: bool = False
    browser_action_performed: bool = False
    page_fetched: bool = False
    page_read: bool = False
    screenshot_taken: bool = False
    click_performed: bool = False
    typing_performed: bool = False
    scroll_performed: bool = False
    form_submitted: bool = False
    download_performed: bool = False
    upload_performed: bool = False
    cookie_accessed: bool = False
    session_accessed: bool = False
    credential_used: bool = False
    network_called: bool = False
    provider_called: bool = False
    approval_created: bool = False
    gate_changed: bool = False
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
        object.__setattr__(self, "browser_governance_id", _text("browser_governance_id", self.browser_governance_id))
        object.__setattr__(self, "browser_governance_hash", _text("browser_governance_hash", self.browser_governance_hash))
        object.__setattr__(self, "status", BrowserGovernanceStatus(self.status))
        object.__setattr__(self, "action_kind", BrowserActionKind(self.action_kind))
        object.__setattr__(self, "target_url", _text("target_url", self.target_url))
        object.__setattr__(self, "normalized_target_url", _text("normalized_target_url", self.normalized_target_url))
        object.__setattr__(self, "target_url_hash", _text("target_url_hash", self.target_url_hash))
        object.__setattr__(self, "source_trust", BrowserSourceTrust(self.source_trust))
        object.__setattr__(self, "source_action_proposal_id", _optional_text(self.source_action_proposal_id))
        object.__setattr__(self, "source_action_proposal_hash", _optional_text(self.source_action_proposal_hash))
        object.__setattr__(self, "source_tool_call_preview_id", _optional_text(self.source_tool_call_preview_id))
        object.__setattr__(self, "source_tool_call_preview_hash", _optional_text(self.source_tool_call_preview_hash))
        object.__setattr__(self, "source_intent_route_id", _optional_text(self.source_intent_route_id))
        object.__setattr__(self, "source_intent_route_hash", _optional_text(self.source_intent_route_hash))
        object.__setattr__(self, "source_policy_check_id", _optional_text(self.source_policy_check_id))
        object.__setattr__(self, "source_policy_check_hash", _optional_text(self.source_policy_check_hash))
        object.__setattr__(self, "source_test_runner_control_id", _optional_text(self.source_test_runner_control_id))
        object.__setattr__(self, "source_test_runner_control_hash", _optional_text(self.source_test_runner_control_hash))
        object.__setattr__(self, "source_download_governance_id", _optional_text(self.source_download_governance_id))
        object.__setattr__(self, "source_download_governance_hash", _optional_text(self.source_download_governance_hash))
        object.__setattr__(self, "source_statement_governance_id", _optional_text(self.source_statement_governance_id))
        object.__setattr__(self, "source_statement_governance_hash", _optional_text(self.source_statement_governance_hash))
        object.__setattr__(self, "human_review_required", bool(self.human_review_required))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary)))
        for field_name in (
            "browser_opened",
            "browser_action_performed",
            "page_fetched",
            "page_read",
            "screenshot_taken",
            "click_performed",
            "typing_performed",
            "scroll_performed",
            "form_submitted",
            "download_performed",
            "upload_performed",
            "cookie_accessed",
            "session_accessed",
            "credential_used",
            "network_called",
            "provider_called",
            "approval_created",
            "gate_changed",
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
            "browser_governance_id": self.browser_governance_id,
            "browser_governance_hash": self.browser_governance_hash,
            "status": self.status.value,
            "action_kind": self.action_kind.value,
            "target_url": self.target_url,
            "normalized_target_url": self.normalized_target_url,
            "target_url_hash": self.target_url_hash,
            "source_trust": self.source_trust.value,
            "source_action_proposal_id": self.source_action_proposal_id,
            "source_action_proposal_hash": self.source_action_proposal_hash,
            "source_tool_call_preview_id": self.source_tool_call_preview_id,
            "source_tool_call_preview_hash": self.source_tool_call_preview_hash,
            "source_intent_route_id": self.source_intent_route_id,
            "source_intent_route_hash": self.source_intent_route_hash,
            "source_policy_check_id": self.source_policy_check_id,
            "source_policy_check_hash": self.source_policy_check_hash,
            "source_test_runner_control_id": self.source_test_runner_control_id,
            "source_test_runner_control_hash": self.source_test_runner_control_hash,
            "source_download_governance_id": self.source_download_governance_id,
            "source_download_governance_hash": self.source_download_governance_hash,
            "source_statement_governance_id": self.source_statement_governance_id,
            "source_statement_governance_hash": self.source_statement_governance_hash,
            "human_review_required": self.human_review_required,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "browser_opened": self.browser_opened,
            "browser_action_performed": self.browser_action_performed,
            "page_fetched": self.page_fetched,
            "page_read": self.page_read,
            "screenshot_taken": self.screenshot_taken,
            "click_performed": self.click_performed,
            "typing_performed": self.typing_performed,
            "scroll_performed": self.scroll_performed,
            "form_submitted": self.form_submitted,
            "download_performed": self.download_performed,
            "upload_performed": self.upload_performed,
            "cookie_accessed": self.cookie_accessed,
            "session_accessed": self.session_accessed,
            "credential_used": self.credential_used,
            "network_called": self.network_called,
            "provider_called": self.provider_called,
            "approval_created": self.approval_created,
            "gate_changed": self.gate_changed,
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


def build_browser_governance_check(request: BrowserGovernanceRequest) -> BrowserGovernanceCheck:
    if not isinstance(request, BrowserGovernanceRequest):
        return _build_check(
            request_data=_empty_request_data(),
            status=BrowserGovernanceStatus.MALFORMED_REQUEST,
            action_kind=BrowserActionKind.UNKNOWN,
            source_trust=BrowserSourceTrust.UNKNOWN,
            flags={BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED, BrowserGovernanceFlag.SUSPICIOUS_URL},
            risk_notes=("Malformed BrowserGovernanceRequest input.",),
        )

    source_trust = _normalize_source_trust(request.source_trust)
    try:
        action_kind = _normalize_action_kind(request.action_kind)
        request_data = _request_data(request, source_trust, action_kind)
    except (TypeError, ValueError):
        return _build_check(
            request_data=_empty_request_data(),
            status=BrowserGovernanceStatus.MALFORMED_REQUEST,
            action_kind=BrowserActionKind.UNKNOWN,
            source_trust=source_trust,
            flags={BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED, BrowserGovernanceFlag.SUSPICIOUS_URL},
            risk_notes=("Request metadata was not deterministic JSON data.",),
        )

    flags, risk_notes = _classify_action(action_kind)
    url_flags, url_notes = _url_flags(request_data["normalized_target_url"])
    flags.update(url_flags)
    risk_notes.extend(url_notes)
    combined_text = _combined_text(request_data)

    if _provider_untrusted(source_trust):
        flags.add(BrowserGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED)
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Provider or model output is untrusted metadata only.")
    if _unsafe_metadata(combined_text):
        flags.add(BrowserGovernanceFlag.SECRET_OR_TOKEN_PATTERN)
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Credential, cookie, session, form, token, or authority-looking metadata was ignored as authority.")
    if _authority_claims_present(request.authority_claims):
        flags.add(BrowserGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Authority or browser-completion claims were ignored.")
    if _inconsistent_hash_metadata(request_data):
        flags.add(BrowserGovernanceFlag.INCONSISTENT_HASH_METADATA)
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source IDs and hashes are missing, malformed, or inconsistent.")
    if _source_metadata_not_yet_governed(request_data):
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source metadata is not yet governed.")

    status = _status_for(flags, action_kind, request_data)
    return _build_check(
        request_data=request_data,
        status=status,
        action_kind=action_kind,
        source_trust=source_trust,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _build_check(
    *,
    request_data: dict[str, Any],
    status: BrowserGovernanceStatus,
    action_kind: BrowserActionKind,
    source_trust: BrowserSourceTrust,
    flags: set[BrowserGovernanceFlag],
    risk_notes: tuple[str, ...],
) -> BrowserGovernanceCheck:
    base_flags = {
        BrowserGovernanceFlag.BROWSER_GOVERNANCE_METADATA_ONLY,
        BrowserGovernanceFlag.NO_BROWSER_OPENED,
        BrowserGovernanceFlag.NO_BROWSER_ACTION,
        BrowserGovernanceFlag.NO_PAGE_FETCHED,
        BrowserGovernanceFlag.NO_PAGE_READ,
        BrowserGovernanceFlag.NO_SCREENSHOT,
        BrowserGovernanceFlag.NO_CLICK,
        BrowserGovernanceFlag.NO_TYPING,
        BrowserGovernanceFlag.NO_SCROLL,
        BrowserGovernanceFlag.NO_FORM_SUBMIT,
        BrowserGovernanceFlag.NO_DOWNLOAD,
        BrowserGovernanceFlag.NO_UPLOAD,
        BrowserGovernanceFlag.NO_COOKIE_ACCESS,
        BrowserGovernanceFlag.NO_SESSION_ACCESS,
        BrowserGovernanceFlag.NO_CREDENTIAL_USE,
        BrowserGovernanceFlag.NO_NETWORK,
        BrowserGovernanceFlag.NO_PROVIDER_CALL,
        BrowserGovernanceFlag.NO_EXECUTION,
        BrowserGovernanceFlag.NO_WRITE,
        BrowserGovernanceFlag.NO_ENV_ACCESS,
        BrowserGovernanceFlag.NO_API_KEY_ACCESS,
        BrowserGovernanceFlag.ACTION_PROPOSAL_METADATA_ONLY,
        BrowserGovernanceFlag.TOOL_CALL_PREVIEW_METADATA_ONLY,
        BrowserGovernanceFlag.TOOL_REGISTRY_METADATA_ONLY,
        BrowserGovernanceFlag.INTENT_ROUTE_METADATA_ONLY,
        BrowserGovernanceFlag.LOCAL_POLICY_METADATA_ONLY,
        BrowserGovernanceFlag.TEST_RUNNER_METADATA_ONLY,
        BrowserGovernanceFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY,
        BrowserGovernanceFlag.STATEMENT_GOVERNANCE_METADATA_ONLY,
    }
    all_flags = base_flags | set(flags)
    if status is not BrowserGovernanceStatus.BROWSER_GOVERNANCE_CHECK_READY:
        all_flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    target_url_hash = _hash_json({"normalized_target_url": request_data["normalized_target_url"]})
    human_review_required = BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED in all_flags
    stable_payload = {
        "schema_version": BROWSER_GOVERNANCE_SCHEMA_VERSION,
        "status": status.value,
        "action_kind": action_kind.value,
        "target_url": request_data["target_url"],
        "normalized_target_url": request_data["normalized_target_url"],
        "target_url_hash": target_url_hash,
        "source_trust": source_trust.value,
        "source_action_proposal_id": request_data["source_action_proposal_id"],
        "source_action_proposal_hash": request_data["source_action_proposal_hash"],
        "source_tool_call_preview_id": request_data["source_tool_call_preview_id"],
        "source_tool_call_preview_hash": request_data["source_tool_call_preview_hash"],
        "source_intent_route_id": request_data["source_intent_route_id"],
        "source_intent_route_hash": request_data["source_intent_route_hash"],
        "source_policy_check_id": request_data["source_policy_check_id"],
        "source_policy_check_hash": request_data["source_policy_check_hash"],
        "source_test_runner_control_id": request_data["source_test_runner_control_id"],
        "source_test_runner_control_hash": request_data["source_test_runner_control_hash"],
        "source_download_governance_id": request_data["source_download_governance_id"],
        "source_download_governance_hash": request_data["source_download_governance_hash"],
        "source_statement_governance_id": request_data["source_statement_governance_id"],
        "source_statement_governance_hash": request_data["source_statement_governance_hash"],
        "source_statuses": request_data["source_statuses"],
        "source_flags": request_data["source_flags"],
        "metadata": request_data["metadata"],
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
        "human_review_required": human_review_required,
    }
    governance_hash = _hash_json(stable_payload)
    return BrowserGovernanceCheck(
        schema_version=BROWSER_GOVERNANCE_SCHEMA_VERSION,
        browser_governance_id=f"browser-governance-{governance_hash[:24]}",
        browser_governance_hash=governance_hash,
        status=status,
        action_kind=action_kind,
        target_url=request_data["target_url"],
        normalized_target_url=request_data["normalized_target_url"],
        target_url_hash=target_url_hash,
        source_trust=source_trust,
        source_action_proposal_id=request_data["source_action_proposal_id"],
        source_action_proposal_hash=request_data["source_action_proposal_hash"],
        source_tool_call_preview_id=request_data["source_tool_call_preview_id"],
        source_tool_call_preview_hash=request_data["source_tool_call_preview_hash"],
        source_intent_route_id=request_data["source_intent_route_id"],
        source_intent_route_hash=request_data["source_intent_route_hash"],
        source_policy_check_id=request_data["source_policy_check_id"],
        source_policy_check_hash=request_data["source_policy_check_hash"],
        source_test_runner_control_id=request_data["source_test_runner_control_id"],
        source_test_runner_control_hash=request_data["source_test_runner_control_hash"],
        source_download_governance_id=request_data["source_download_governance_id"],
        source_download_governance_hash=request_data["source_download_governance_hash"],
        source_statement_governance_id=request_data["source_statement_governance_id"],
        source_statement_governance_hash=request_data["source_statement_governance_hash"],
        human_review_required=human_review_required,
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status, action_kind, human_review_required),
    )


def _request_data(
    request: BrowserGovernanceRequest,
    source_trust: BrowserSourceTrust,
    action_kind: BrowserActionKind,
) -> dict[str, Any]:
    target_url = _text("target_url", request.target_url)
    return {
        "action_kind": action_kind.value,
        "target_url": target_url,
        "normalized_target_url": _normalize_url(target_url),
        "source_trust": source_trust.value,
        "source_action_proposal_id": _optional_text(request.source_action_proposal_id),
        "source_action_proposal_hash": _optional_text(request.source_action_proposal_hash),
        "source_tool_call_preview_id": _optional_text(request.source_tool_call_preview_id),
        "source_tool_call_preview_hash": _optional_text(request.source_tool_call_preview_hash),
        "source_intent_route_id": _optional_text(request.source_intent_route_id),
        "source_intent_route_hash": _optional_text(request.source_intent_route_hash),
        "source_policy_check_id": _optional_text(request.source_policy_check_id),
        "source_policy_check_hash": _optional_text(request.source_policy_check_hash),
        "source_test_runner_control_id": _optional_text(request.source_test_runner_control_id),
        "source_test_runner_control_hash": _optional_text(request.source_test_runner_control_hash),
        "source_download_governance_id": _optional_text(request.source_download_governance_id),
        "source_download_governance_hash": _optional_text(request.source_download_governance_hash),
        "source_statement_governance_id": _optional_text(request.source_statement_governance_id),
        "source_statement_governance_hash": _optional_text(request.source_statement_governance_hash),
        "source_statuses": tuple(value.upper() for value in _text_tuple("source_statuses", request.source_statuses)),
        "source_flags": tuple(value.upper() for value in _text_tuple("source_flags", request.source_flags)),
        "metadata": _stable_json_mapping(request.metadata),
    }


def _empty_request_data() -> dict[str, Any]:
    return {
        "action_kind": BrowserActionKind.UNKNOWN.value,
        "target_url": "",
        "normalized_target_url": "",
        "source_trust": BrowserSourceTrust.UNKNOWN.value,
        "source_action_proposal_id": None,
        "source_action_proposal_hash": None,
        "source_tool_call_preview_id": None,
        "source_tool_call_preview_hash": None,
        "source_intent_route_id": None,
        "source_intent_route_hash": None,
        "source_policy_check_id": None,
        "source_policy_check_hash": None,
        "source_test_runner_control_id": None,
        "source_test_runner_control_hash": None,
        "source_download_governance_id": None,
        "source_download_governance_hash": None,
        "source_statement_governance_id": None,
        "source_statement_governance_hash": None,
        "source_statuses": (),
        "source_flags": (),
        "metadata": {},
    }


def _classify_action(action_kind: BrowserActionKind) -> tuple[set[BrowserGovernanceFlag], list[str]]:
    flags: set[BrowserGovernanceFlag] = {BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED}
    notes: list[str] = []
    if action_kind in {BrowserActionKind.READ_ONLY_VIEW, BrowserActionKind.URL_REVIEW}:
        flags.add(BrowserGovernanceFlag.READ_ONLY_BROWSER_METADATA)
        notes.append("Read-only browser action metadata requires review and does not open a browser.")
    elif action_kind is BrowserActionKind.SCREENSHOT_REQUEST:
        flags.add(BrowserGovernanceFlag.READ_ONLY_BROWSER_METADATA)
        notes.append("Screenshot request is metadata only and not yet governed for execution.")
    elif action_kind in {BrowserActionKind.CLICK, BrowserActionKind.TYPE, BrowserActionKind.SCROLL}:
        flags.add(BrowserGovernanceFlag.ACTIVE_BROWSER_ACTION_BLOCKED)
        notes.append("Active browser interaction metadata is blocked in Browser Governance 1A.")
    elif action_kind is BrowserActionKind.FORM_SUBMIT:
        flags.add(BrowserGovernanceFlag.FORM_SUBMIT_BLOCKED)
        notes.append("Form submission metadata is blocked.")
    elif action_kind is BrowserActionKind.DOWNLOAD:
        flags.add(BrowserGovernanceFlag.DOWNLOAD_BLOCKED)
        notes.append("Browser download metadata is blocked here and belongs to separate governance.")
    elif action_kind is BrowserActionKind.UPLOAD:
        flags.add(BrowserGovernanceFlag.UPLOAD_BLOCKED)
        notes.append("Browser upload metadata is blocked.")
    elif action_kind is BrowserActionKind.LOGIN:
        flags.add(BrowserGovernanceFlag.LOGIN_BLOCKED)
        flags.add(BrowserGovernanceFlag.CREDENTIAL_BLOCKED)
        notes.append("Login and credential metadata is blocked.")
    elif action_kind is BrowserActionKind.COOKIE_ACCESS:
        flags.add(BrowserGovernanceFlag.COOKIE_BLOCKED)
        notes.append("Cookie access metadata is blocked.")
    elif action_kind is BrowserActionKind.SESSION_ACCESS:
        flags.add(BrowserGovernanceFlag.SESSION_BLOCKED)
        notes.append("Session access metadata is blocked.")
    else:
        notes.append("Browser action kind is unknown or not yet governed.")
    return flags, notes


def _url_flags(normalized_url: str) -> tuple[set[BrowserGovernanceFlag], tuple[str, ...]]:
    flags: set[BrowserGovernanceFlag] = set()
    notes: list[str] = []
    if not normalized_url:
        flags.add(BrowserGovernanceFlag.SUSPICIOUS_URL)
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Target URL is empty or malformed.")
        return flags, tuple(notes)
    if normalized_url.startswith("javascript:"):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.JAVASCRIPT_URL_BLOCKED})
        notes.append("JavaScript URL metadata is blocked.")
    elif normalized_url.startswith("data:"):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.DATA_URL_BLOCKED})
        notes.append("Data URL metadata is blocked.")
    elif normalized_url.startswith("file:"):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.FILE_URL_BLOCKED})
        notes.append("File URL metadata is blocked.")
    elif normalized_url.startswith("chrome:") or normalized_url.startswith("about:"):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.CHROME_URL_BLOCKED})
        notes.append("Browser-internal URL metadata is blocked.")
    elif normalized_url.startswith("ftp:"):
        flags.add(BrowserGovernanceFlag.UNSAFE_URL)
        notes.append("FTP URL metadata is blocked.")
    elif _contains_any(normalized_url, ("169.254.169.254", "metadata.google.internal")):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.METADATA_SERVICE_BLOCKED})
        notes.append("Metadata service URL metadata is blocked.")
    elif _contains_any(normalized_url, ("localhost", "127.0.0.1")):
        flags.update({BrowserGovernanceFlag.UNSAFE_URL, BrowserGovernanceFlag.LOCALHOST_BLOCKED})
        notes.append("Localhost URL metadata is blocked.")
    elif normalized_url.startswith("http://") or normalized_url.startswith("https://"):
        flags.add(BrowserGovernanceFlag.EXTERNAL_URL_REVIEW_REQUIRED)
        notes.append("External URL is metadata only and requires review.")
    else:
        flags.add(BrowserGovernanceFlag.SUSPICIOUS_URL)
        notes.append("Target URL shape is unknown or not yet governed.")
    if _credential_or_form_pattern(normalized_url):
        flags.add(BrowserGovernanceFlag.SECRET_OR_TOKEN_PATTERN)
        notes.append("URL contains login, credential, form, admin, payment, or token-like metadata.")
    if flags:
        flags.add(BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED)
    return flags, tuple(notes)


def _status_for(
    flags: set[BrowserGovernanceFlag],
    action_kind: BrowserActionKind,
    request_data: dict[str, Any],
) -> BrowserGovernanceStatus:
    if not request_data["normalized_target_url"]:
        return BrowserGovernanceStatus.MALFORMED_REQUEST
    if BrowserGovernanceFlag.INCONSISTENT_HASH_METADATA in flags:
        return BrowserGovernanceStatus.INCONSISTENT_METADATA
    if BrowserGovernanceFlag.UNSAFE_URL in flags:
        return BrowserGovernanceStatus.BLOCKED_UNSAFE_BROWSER_URL
    if BrowserGovernanceFlag.LOGIN_BLOCKED in flags or BrowserGovernanceFlag.CREDENTIAL_BLOCKED in flags:
        return BrowserGovernanceStatus.BLOCKED_LOGIN_OR_CREDENTIAL_RISK
    if BrowserGovernanceFlag.COOKIE_BLOCKED in flags or BrowserGovernanceFlag.SESSION_BLOCKED in flags:
        return BrowserGovernanceStatus.BLOCKED_COOKIE_OR_SESSION_RISK
    if BrowserGovernanceFlag.FORM_SUBMIT_BLOCKED in flags:
        return BrowserGovernanceStatus.BLOCKED_FORM_SUBMISSION
    if BrowserGovernanceFlag.DOWNLOAD_BLOCKED in flags or BrowserGovernanceFlag.UPLOAD_BLOCKED in flags:
        return BrowserGovernanceStatus.BLOCKED_DOWNLOAD_OR_UPLOAD
    if BrowserGovernanceFlag.ACTIVE_BROWSER_ACTION_BLOCKED in flags:
        return BrowserGovernanceStatus.BLOCKED_ACTIVE_BROWSER_ACTION
    if action_kind in {BrowserActionKind.READ_ONLY_VIEW, BrowserActionKind.URL_REVIEW}:
        return BrowserGovernanceStatus.READ_ONLY_BROWSER_REVIEW_REQUIRED
    if action_kind is BrowserActionKind.SCREENSHOT_REQUEST:
        return BrowserGovernanceStatus.NOT_YET_GOVERNED
    if action_kind is BrowserActionKind.UNKNOWN:
        return BrowserGovernanceStatus.NOT_YET_GOVERNED
    if BrowserGovernanceFlag.HUMAN_REVIEW_REQUIRED in flags:
        return BrowserGovernanceStatus.BROWSER_REVIEW_REQUIRED
    return BrowserGovernanceStatus.BROWSER_GOVERNANCE_CHECK_READY


def _source_metadata_not_yet_governed(request_data: dict[str, Any]) -> bool:
    terms = set(request_data["source_statuses"]) | set(request_data["source_flags"])
    return bool(terms & {"NOT_YET_GOVERNED", "UNKNOWN_TOOL", "UNKNOWN_INTENT", "UNSAFE_INTENT", "UNSAFE_URL"})


def _unsafe_metadata(text: str) -> bool:
    return _contains_any(
        text,
        (
            "login",
            "password",
            "credential",
            "cookie",
            "session",
            "csrf",
            "oauth",
            "checkout",
            "payment",
            "submit",
            "delete",
            "admin",
            "download",
            "upload",
            "download?token=",
            "api" + "_key",
            "secret",
            "token",
            "file:",
            "javascript:",
            "data:",
            "chrome:",
            "about:",
            "169.254.169.254",
            "metadata.google.internal",
            "localhost",
            "127.0.0.1",
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "browser_opened",
            "browser_action_performed",
            "page_fetched",
            "page_read",
            "screenshot_taken",
            "click_performed",
            "typing_performed",
            "form_submitted",
            "download_performed",
            "upload_performed",
            "cookie_accessed",
            "session_accessed",
            "credential_used",
            "network_called",
        ),
    )


def _credential_or_form_pattern(text: str) -> bool:
    return _contains_any(
        text,
        (
            "login",
            "password",
            "credential",
            "cookie",
            "session",
            "csrf",
            "oauth",
            "checkout",
            "payment",
            "submit",
            "delete",
            "admin",
            "download?token=",
            "api" + "_key",
            "secret",
            "token",
        ),
    )


def _authority_claims_present(values: Mapping[str, Any] | None) -> bool:
    if values is None:
        return False
    if not isinstance(values, Mapping):
        return True
    suspicious_keys = {
        "approval_granted",
        "can_access_network",
        "can_execute",
        "allowed",
        "permission",
        "tool_allowed",
        "gate_result",
        "browser_opened",
        "browser_action_performed",
        "page_fetched",
        "page_read",
        "screenshot_taken",
        "click_performed",
        "typing_performed",
        "form_submitted",
        "download_performed",
        "upload_performed",
        "cookie_accessed",
        "session_accessed",
        "credential_used",
        "network_called",
    }
    return any(bool(values.get(key)) for key in suspicious_keys)


def _inconsistent_hash_metadata(request_data: dict[str, Any]) -> bool:
    pairs = (
        ("source_action_proposal_id", "source_action_proposal_hash"),
        ("source_tool_call_preview_id", "source_tool_call_preview_hash"),
        ("source_intent_route_id", "source_intent_route_hash"),
        ("source_policy_check_id", "source_policy_check_hash"),
        ("source_test_runner_control_id", "source_test_runner_control_hash"),
        ("source_download_governance_id", "source_download_governance_hash"),
        ("source_statement_governance_id", "source_statement_governance_hash"),
    )
    for id_key, hash_key in pairs:
        source_id = request_data[id_key]
        source_hash = request_data[hash_key]
        if bool(source_id) != bool(source_hash):
            return True
        if source_hash and not _looks_like_hash(source_hash):
            return True
    return False


def _looks_like_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    hexdigits = set("0123456789abcdefABCDEF")
    return all(character in hexdigits for character in value)


def _provider_untrusted(source_trust: BrowserSourceTrust) -> bool:
    return source_trust in {
        BrowserSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        BrowserSourceTrust.PROVIDER_UNTRUSTED,
        BrowserSourceTrust.MODEL_UNTRUSTED,
    }


def _normalize_action_kind(value: BrowserActionKind | str) -> BrowserActionKind:
    if isinstance(value, BrowserActionKind):
        return value
    if not isinstance(value, str):
        return BrowserActionKind.UNKNOWN
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "VIEW": BrowserActionKind.READ_ONLY_VIEW,
        "READ_ONLY": BrowserActionKind.READ_ONLY_VIEW,
        "READ_ONLY_VIEW": BrowserActionKind.READ_ONLY_VIEW,
        "URL_REVIEW": BrowserActionKind.URL_REVIEW,
        "SCREENSHOT": BrowserActionKind.SCREENSHOT_REQUEST,
        "SCREENSHOT_REQUEST": BrowserActionKind.SCREENSHOT_REQUEST,
        "CLICK": BrowserActionKind.CLICK,
        "TYPE": BrowserActionKind.TYPE,
        "TYPING": BrowserActionKind.TYPE,
        "SCROLL": BrowserActionKind.SCROLL,
        "FORM_SUBMIT": BrowserActionKind.FORM_SUBMIT,
        "SUBMIT": BrowserActionKind.FORM_SUBMIT,
        "DOWNLOAD": BrowserActionKind.DOWNLOAD,
        "UPLOAD": BrowserActionKind.UPLOAD,
        "LOGIN": BrowserActionKind.LOGIN,
        "COOKIE_ACCESS": BrowserActionKind.COOKIE_ACCESS,
        "SESSION_ACCESS": BrowserActionKind.SESSION_ACCESS,
    }
    return aliases.get(normalized, BrowserActionKind.UNKNOWN)


def _normalize_source_trust(value: BrowserSourceTrust | str) -> BrowserSourceTrust:
    if isinstance(value, BrowserSourceTrust):
        return value
    if not isinstance(value, str):
        return BrowserSourceTrust.UNKNOWN
    normalized = value.strip().upper()
    aliases = {
        "UNTRUSTED": BrowserSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_OUTPUT_UNTRUSTED": BrowserSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": BrowserSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": BrowserSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": BrowserSourceTrust.MODEL_UNTRUSTED,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return BrowserSourceTrust(normalized)
    except ValueError:
        return BrowserSourceTrust.UNKNOWN


def _normalize_url(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _combined_text(request_data: dict[str, Any]) -> str:
    return _canonical_json(request_data).casefold()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _flag_tuple(values: Any) -> tuple[BrowserGovernanceFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("flags must be a tuple or list")
    return tuple(sorted((BrowserGovernanceFlag(value) for value in values), key=lambda flag: flag.value))


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


def _stable_json_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    stable = json.loads(_canonical_json(value))
    if not isinstance(stable, dict):
        raise TypeError("metadata must be a mapping")
    return stable


def _bounded_text(value: str) -> str:
    if len(value) <= _MAX_SUMMARY_CHARS:
        return value
    return value[: _MAX_SUMMARY_CHARS - 3] + "..."


def _summary(
    status: BrowserGovernanceStatus,
    action_kind: BrowserActionKind,
    human_review_required: bool,
) -> str:
    return _bounded_text(
        f"Browser governance metadata: status={status.value}; action_kind={action_kind.value}; "
        f"human_review_required={human_review_required}."
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
