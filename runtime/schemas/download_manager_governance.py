from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


DOWNLOAD_GOVERNANCE_SCHEMA_VERSION = "AOIA_DOWNLOAD_GOVERNANCE_1A"
_MAX_SUMMARY_CHARS = 420


class DownloadGovernanceStatus(str, Enum):
    DOWNLOAD_PREVIEW_READY = "DOWNLOAD_PREVIEW_READY"
    DOWNLOAD_REVIEW_REQUIRED = "DOWNLOAD_REVIEW_REQUIRED"
    BLOCKED_UNSAFE_URL = "BLOCKED_UNSAFE_URL"
    BLOCKED_UNSAFE_TARGET_PATH = "BLOCKED_UNSAFE_TARGET_PATH"
    BLOCKED_RISKY_FILE_TYPE = "BLOCKED_RISKY_FILE_TYPE"
    BLOCKED_CREDENTIAL_OR_SECRET_RISK = "BLOCKED_CREDENTIAL_OR_SECRET_RISK"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"


class DownloadGovernanceFlag(str, Enum):
    DOWNLOAD_GOVERNANCE_METADATA_ONLY = "DOWNLOAD_GOVERNANCE_METADATA_ONLY"
    NO_DOWNLOAD = "NO_DOWNLOAD"
    NO_NETWORK = "NO_NETWORK"
    NO_URL_FETCH = "NO_URL_FETCH"
    NO_FILE_OPENED = "NO_FILE_OPENED"
    NO_FILE_WRITTEN = "NO_FILE_WRITTEN"
    NO_DIRECTORY_CREATED = "NO_DIRECTORY_CREATED"
    NO_QUARANTINE_CREATED = "NO_QUARANTINE_CREATED"
    NO_CONTENT_HASH_FROM_FILE = "NO_CONTENT_HASH_FROM_FILE"
    NO_EXECUTION = "NO_EXECUTION"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    QUARANTINE_REQUIRED_METADATA_ONLY = "QUARANTINE_REQUIRED_METADATA_ONLY"
    EXTERNAL_URL_REVIEW_REQUIRED = "EXTERNAL_URL_REVIEW_REQUIRED"
    UNSAFE_URL = "UNSAFE_URL"
    SUSPICIOUS_URL = "SUSPICIOUS_URL"
    UNSAFE_TARGET_PATH = "UNSAFE_TARGET_PATH"
    PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"
    ABSOLUTE_PATH_BLOCKED = "ABSOLUTE_PATH_BLOCKED"
    NULL_BYTE_BLOCKED = "NULL_BYTE_BLOCKED"
    RISKY_FILE_EXTENSION = "RISKY_FILE_EXTENSION"
    EXECUTABLE_FILE_BLOCKED = "EXECUTABLE_FILE_BLOCKED"
    SCRIPT_FILE_BLOCKED = "SCRIPT_FILE_BLOCKED"
    ARCHIVE_REVIEW_REQUIRED = "ARCHIVE_REVIEW_REQUIRED"
    PDF_REVIEW_REQUIRED = "PDF_REVIEW_REQUIRED"
    IMAGE_REVIEW_REQUIRED = "IMAGE_REVIEW_REQUIRED"
    SECRET_OR_TOKEN_PATTERN = "SECRET_OR_TOKEN_PATTERN"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    INCONSISTENT_HASH_METADATA = "INCONSISTENT_HASH_METADATA"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"
    TOOL_CALL_PREVIEW_METADATA_ONLY = "TOOL_CALL_PREVIEW_METADATA_ONLY"
    TOOL_REGISTRY_METADATA_ONLY = "TOOL_REGISTRY_METADATA_ONLY"
    INTENT_ROUTE_METADATA_ONLY = "INTENT_ROUTE_METADATA_ONLY"
    LOCAL_POLICY_METADATA_ONLY = "LOCAL_POLICY_METADATA_ONLY"
    TEST_RUNNER_METADATA_ONLY = "TEST_RUNNER_METADATA_ONLY"


class DownloadTargetKind(str, Enum):
    PDF_DOCUMENT = "PDF_DOCUMENT"
    TEXT_DOCUMENT = "TEXT_DOCUMENT"
    MARKDOWN_DOCUMENT = "MARKDOWN_DOCUMENT"
    CSV_DOCUMENT = "CSV_DOCUMENT"
    JSON_DOCUMENT = "JSON_DOCUMENT"
    IMAGE_FILE = "IMAGE_FILE"
    ARCHIVE_FILE = "ARCHIVE_FILE"
    EXECUTABLE_FILE = "EXECUTABLE_FILE"
    SCRIPT_FILE = "SCRIPT_FILE"
    UNKNOWN = "UNKNOWN"


class DownloadSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DownloadGovernanceRequest:
    source_url: str
    proposed_target_path: str
    expected_content_hash: str | None = None
    expected_content_hash_algorithm: str | None = None
    source_trust: DownloadSourceTrust | str = DownloadSourceTrust.UNKNOWN
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
    source_statuses: tuple[str, ...] | list[str] = ()
    source_flags: tuple[str, ...] | list[str] = ()
    metadata: Mapping[str, Any] | None = None
    authority_claims: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class DownloadGovernancePreview:
    schema_version: str
    download_governance_id: str
    download_governance_hash: str
    status: DownloadGovernanceStatus
    target_kind: DownloadTargetKind
    source_url: str
    normalized_source_url: str
    source_url_hash: str
    proposed_target_path: str
    normalized_target_path: str
    target_path_hash: str
    proposed_filename: str
    file_extension: str
    quarantine_required: bool
    quarantine_label: str
    expected_content_hash: str | None
    expected_content_hash_algorithm: str | None
    source_trust: DownloadSourceTrust
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
    human_review_required: bool
    flags: tuple[DownloadGovernanceFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    download_performed: bool = False
    network_called: bool = False
    url_fetched: bool = False
    file_opened: bool = False
    file_written: bool = False
    directory_created: bool = False
    quarantine_created: bool = False
    content_hash_computed_from_file: bool = False
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
        object.__setattr__(self, "download_governance_id", _text("download_governance_id", self.download_governance_id))
        object.__setattr__(self, "download_governance_hash", _text("download_governance_hash", self.download_governance_hash))
        object.__setattr__(self, "status", DownloadGovernanceStatus(self.status))
        object.__setattr__(self, "target_kind", DownloadTargetKind(self.target_kind))
        object.__setattr__(self, "source_url", _text("source_url", self.source_url))
        object.__setattr__(self, "normalized_source_url", _text("normalized_source_url", self.normalized_source_url))
        object.__setattr__(self, "source_url_hash", _text("source_url_hash", self.source_url_hash))
        object.__setattr__(self, "proposed_target_path", _text("proposed_target_path", self.proposed_target_path))
        object.__setattr__(self, "normalized_target_path", _text("normalized_target_path", self.normalized_target_path))
        object.__setattr__(self, "target_path_hash", _text("target_path_hash", self.target_path_hash))
        object.__setattr__(self, "proposed_filename", _text("proposed_filename", self.proposed_filename))
        object.__setattr__(self, "file_extension", _text("file_extension", self.file_extension))
        object.__setattr__(self, "quarantine_required", bool(self.quarantine_required))
        object.__setattr__(self, "quarantine_label", _text("quarantine_label", self.quarantine_label))
        object.__setattr__(self, "expected_content_hash", _optional_text(self.expected_content_hash))
        object.__setattr__(self, "expected_content_hash_algorithm", _optional_text(self.expected_content_hash_algorithm))
        object.__setattr__(self, "source_trust", DownloadSourceTrust(self.source_trust))
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
        object.__setattr__(self, "human_review_required", bool(self.human_review_required))
        object.__setattr__(self, "flags", _flag_tuple(self.flags))
        object.__setattr__(self, "risk_notes", _text_tuple("risk_notes", self.risk_notes))
        object.__setattr__(self, "display_summary", _bounded_text(_text("display_summary", self.display_summary)))
        for field_name in (
            "download_performed",
            "network_called",
            "url_fetched",
            "file_opened",
            "file_written",
            "directory_created",
            "quarantine_created",
            "content_hash_computed_from_file",
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
            "download_governance_id": self.download_governance_id,
            "download_governance_hash": self.download_governance_hash,
            "status": self.status.value,
            "target_kind": self.target_kind.value,
            "source_url": self.source_url,
            "normalized_source_url": self.normalized_source_url,
            "source_url_hash": self.source_url_hash,
            "proposed_target_path": self.proposed_target_path,
            "normalized_target_path": self.normalized_target_path,
            "target_path_hash": self.target_path_hash,
            "proposed_filename": self.proposed_filename,
            "file_extension": self.file_extension,
            "quarantine_required": self.quarantine_required,
            "quarantine_label": self.quarantine_label,
            "expected_content_hash": self.expected_content_hash,
            "expected_content_hash_algorithm": self.expected_content_hash_algorithm,
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
            "human_review_required": self.human_review_required,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "download_performed": self.download_performed,
            "network_called": self.network_called,
            "url_fetched": self.url_fetched,
            "file_opened": self.file_opened,
            "file_written": self.file_written,
            "directory_created": self.directory_created,
            "quarantine_created": self.quarantine_created,
            "content_hash_computed_from_file": self.content_hash_computed_from_file,
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


def build_download_governance_preview(request: DownloadGovernanceRequest) -> DownloadGovernancePreview:
    if not isinstance(request, DownloadGovernanceRequest):
        return _build_preview(
            request_data=_empty_request_data(),
            status=DownloadGovernanceStatus.MALFORMED_REQUEST,
            target_kind=DownloadTargetKind.UNKNOWN,
            source_trust=DownloadSourceTrust.UNKNOWN,
            flags={DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED, DownloadGovernanceFlag.SUSPICIOUS_URL},
            risk_notes=("Malformed DownloadGovernanceRequest input.",),
        )

    source_trust = _normalize_source_trust(request.source_trust)
    try:
        request_data = _request_data(request, source_trust)
    except (TypeError, ValueError):
        return _build_preview(
            request_data=_empty_request_data(),
            status=DownloadGovernanceStatus.MALFORMED_REQUEST,
            target_kind=DownloadTargetKind.UNKNOWN,
            source_trust=source_trust,
            flags={DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED, DownloadGovernanceFlag.SUSPICIOUS_URL},
            risk_notes=("Request metadata was not deterministic JSON data.",),
        )

    target_kind, kind_flags, kind_notes = _classify_target(request_data["normalized_target_path"])
    flags = set(kind_flags)
    risk_notes = list(kind_notes)
    source_text = _combined_text(request_data)

    url_flags, url_notes = _url_flags(request_data["normalized_source_url"])
    flags.update(url_flags)
    risk_notes.extend(url_notes)

    path_flags, path_notes = _path_flags(request_data["normalized_target_path"])
    flags.update(path_flags)
    risk_notes.extend(path_notes)

    if _provider_untrusted(source_trust):
        flags.add(DownloadGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Provider or model output is untrusted metadata only.")
    if request_data["expected_content_hash"] is not None:
        risk_notes.append("Expected content hash was preserved as metadata only and was not computed.")
    if request_data["quarantine_required"]:
        flags.add(DownloadGovernanceFlag.QUARANTINE_REQUIRED_METADATA_ONLY)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Quarantine requirement is metadata only; no quarantine location was created.")
    if _secret_or_authority_metadata_present(source_text):
        flags.add(DownloadGovernanceFlag.SECRET_OR_TOKEN_PATTERN)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Secret, credential, or authority-looking metadata was ignored as authority.")
    if _authority_claims_present(request.authority_claims):
        flags.add(DownloadGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Authority, network, or file-completion claims were ignored.")
    if _inconsistent_hash_metadata(request_data):
        flags.add(DownloadGovernanceFlag.INCONSISTENT_HASH_METADATA)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source IDs and hashes are missing, malformed, or inconsistent.")
    if _source_metadata_not_yet_governed(request_data):
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source metadata is not yet governed.")

    status = _status_for(flags, target_kind, request_data)
    return _build_preview(
        request_data=request_data,
        status=status,
        target_kind=target_kind,
        source_trust=source_trust,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _build_preview(
    *,
    request_data: dict[str, Any],
    status: DownloadGovernanceStatus,
    target_kind: DownloadTargetKind,
    source_trust: DownloadSourceTrust,
    flags: set[DownloadGovernanceFlag],
    risk_notes: tuple[str, ...],
) -> DownloadGovernancePreview:
    base_flags = {
        DownloadGovernanceFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY,
        DownloadGovernanceFlag.NO_DOWNLOAD,
        DownloadGovernanceFlag.NO_NETWORK,
        DownloadGovernanceFlag.NO_URL_FETCH,
        DownloadGovernanceFlag.NO_FILE_OPENED,
        DownloadGovernanceFlag.NO_FILE_WRITTEN,
        DownloadGovernanceFlag.NO_DIRECTORY_CREATED,
        DownloadGovernanceFlag.NO_QUARANTINE_CREATED,
        DownloadGovernanceFlag.NO_CONTENT_HASH_FROM_FILE,
        DownloadGovernanceFlag.NO_EXECUTION,
        DownloadGovernanceFlag.NO_ENV_ACCESS,
        DownloadGovernanceFlag.NO_API_KEY_ACCESS,
        DownloadGovernanceFlag.ACTION_PROPOSAL_METADATA_ONLY,
        DownloadGovernanceFlag.TOOL_CALL_PREVIEW_METADATA_ONLY,
        DownloadGovernanceFlag.TOOL_REGISTRY_METADATA_ONLY,
        DownloadGovernanceFlag.INTENT_ROUTE_METADATA_ONLY,
        DownloadGovernanceFlag.LOCAL_POLICY_METADATA_ONLY,
        DownloadGovernanceFlag.TEST_RUNNER_METADATA_ONLY,
    }
    all_flags = base_flags | set(flags)
    if status is not DownloadGovernanceStatus.DOWNLOAD_PREVIEW_READY:
        all_flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    source_url_hash = _hash_json({"normalized_source_url": request_data["normalized_source_url"]})
    target_path_hash = _hash_json({"normalized_target_path": request_data["normalized_target_path"]})
    human_review_required = DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED in all_flags
    stable_payload = {
        "schema_version": DOWNLOAD_GOVERNANCE_SCHEMA_VERSION,
        "status": status.value,
        "target_kind": target_kind.value,
        "source_url": request_data["source_url"],
        "normalized_source_url": request_data["normalized_source_url"],
        "source_url_hash": source_url_hash,
        "proposed_target_path": request_data["proposed_target_path"],
        "normalized_target_path": request_data["normalized_target_path"],
        "target_path_hash": target_path_hash,
        "proposed_filename": request_data["proposed_filename"],
        "file_extension": request_data["file_extension"],
        "quarantine_required": request_data["quarantine_required"],
        "quarantine_label": request_data["quarantine_label"],
        "expected_content_hash": request_data["expected_content_hash"],
        "expected_content_hash_algorithm": request_data["expected_content_hash_algorithm"],
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
        "source_statuses": request_data["source_statuses"],
        "source_flags": request_data["source_flags"],
        "metadata": request_data["metadata"],
        "flags": [flag.value for flag in ordered_flags],
        "risk_notes": list(ordered_notes),
        "human_review_required": human_review_required,
    }
    governance_hash = _hash_json(stable_payload)
    return DownloadGovernancePreview(
        schema_version=DOWNLOAD_GOVERNANCE_SCHEMA_VERSION,
        download_governance_id=f"download-governance-{governance_hash[:24]}",
        download_governance_hash=governance_hash,
        status=status,
        target_kind=target_kind,
        source_url=request_data["source_url"],
        normalized_source_url=request_data["normalized_source_url"],
        source_url_hash=source_url_hash,
        proposed_target_path=request_data["proposed_target_path"],
        normalized_target_path=request_data["normalized_target_path"],
        target_path_hash=target_path_hash,
        proposed_filename=request_data["proposed_filename"],
        file_extension=request_data["file_extension"],
        quarantine_required=request_data["quarantine_required"],
        quarantine_label=request_data["quarantine_label"],
        expected_content_hash=request_data["expected_content_hash"],
        expected_content_hash_algorithm=request_data["expected_content_hash_algorithm"],
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
        human_review_required=human_review_required,
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status, target_kind, request_data["file_extension"], human_review_required),
    )


def _request_data(request: DownloadGovernanceRequest, source_trust: DownloadSourceTrust) -> dict[str, Any]:
    source_url = _text("source_url", request.source_url)
    target_path = _text("proposed_target_path", request.proposed_target_path)
    normalized_target_path = _normalize_target_path(target_path)
    file_name = _filename(normalized_target_path)
    extension = _extension(file_name)
    return {
        "source_url": source_url,
        "normalized_source_url": _normalize_source_url(source_url),
        "proposed_target_path": target_path,
        "normalized_target_path": normalized_target_path,
        "proposed_filename": file_name,
        "file_extension": extension,
        "quarantine_required": _quarantine_required(extension),
        "quarantine_label": _quarantine_label(extension),
        "expected_content_hash": _optional_text(request.expected_content_hash),
        "expected_content_hash_algorithm": _optional_text(request.expected_content_hash_algorithm),
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
        "source_statuses": tuple(value.upper() for value in _text_tuple("source_statuses", request.source_statuses)),
        "source_flags": tuple(value.upper() for value in _text_tuple("source_flags", request.source_flags)),
        "metadata": _stable_json_mapping(request.metadata),
    }


def _empty_request_data() -> dict[str, Any]:
    return {
        "source_url": "",
        "normalized_source_url": "",
        "proposed_target_path": "",
        "normalized_target_path": "",
        "proposed_filename": "",
        "file_extension": "",
        "quarantine_required": False,
        "quarantine_label": "not_applicable",
        "expected_content_hash": None,
        "expected_content_hash_algorithm": None,
        "source_trust": DownloadSourceTrust.UNKNOWN.value,
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
        "source_statuses": (),
        "source_flags": (),
        "metadata": {},
    }


def _url_flags(normalized_url: str) -> tuple[set[DownloadGovernanceFlag], tuple[str, ...]]:
    flags: set[DownloadGovernanceFlag] = set()
    notes: list[str] = []
    if not normalized_url:
        flags.add(DownloadGovernanceFlag.SUSPICIOUS_URL)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Source URL is empty or malformed.")
        return flags, tuple(notes)
    if _unsafe_url(normalized_url):
        flags.add(DownloadGovernanceFlag.UNSAFE_URL)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Source URL uses an unsafe scheme, internal host, or browser-like target.")
    elif normalized_url.startswith("http://") or normalized_url.startswith("https://"):
        flags.add(DownloadGovernanceFlag.EXTERNAL_URL_REVIEW_REQUIRED)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("External URL is metadata only and requires review before any future governed transfer.")
    else:
        flags.add(DownloadGovernanceFlag.SUSPICIOUS_URL)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Source URL shape is unknown or not yet governed.")
    if _secret_pattern_present(normalized_url):
        flags.add(DownloadGovernanceFlag.SECRET_OR_TOKEN_PATTERN)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Source URL contains credential, payment, admin, or token-like text.")
    return flags, tuple(notes)


def _path_flags(normalized_target_path: str) -> tuple[set[DownloadGovernanceFlag], tuple[str, ...]]:
    flags: set[DownloadGovernanceFlag] = set()
    notes: list[str] = []
    if not normalized_target_path:
        flags.add(DownloadGovernanceFlag.UNSAFE_TARGET_PATH)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        notes.append("Target path is empty or malformed.")
        return flags, tuple(notes)
    if "\x00" in normalized_target_path:
        flags.add(DownloadGovernanceFlag.NULL_BYTE_BLOCKED)
        flags.add(DownloadGovernanceFlag.UNSAFE_TARGET_PATH)
        notes.append("Target path contains a null byte.")
    if _is_absolute_path(normalized_target_path):
        flags.add(DownloadGovernanceFlag.ABSOLUTE_PATH_BLOCKED)
        flags.add(DownloadGovernanceFlag.UNSAFE_TARGET_PATH)
        notes.append("Absolute target paths are blocked.")
    if _contains_path_traversal(normalized_target_path):
        flags.add(DownloadGovernanceFlag.PATH_TRAVERSAL_BLOCKED)
        flags.add(DownloadGovernanceFlag.UNSAFE_TARGET_PATH)
        notes.append("Parent traversal in target paths is blocked.")
    return flags, tuple(notes)


def _classify_target(normalized_target_path: str) -> tuple[DownloadTargetKind, set[DownloadGovernanceFlag], tuple[str, ...]]:
    extension = _extension(_filename(normalized_target_path))
    flags: set[DownloadGovernanceFlag] = set()
    notes: list[str] = []
    if extension == ".pdf":
        flags.add(DownloadGovernanceFlag.PDF_REVIEW_REQUIRED)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        return DownloadTargetKind.PDF_DOCUMENT, flags, ("PDF target is document-like metadata only.",)
    if extension == ".txt":
        return DownloadTargetKind.TEXT_DOCUMENT, flags, ("Text target is document-like metadata only.",)
    if extension == ".md":
        return DownloadTargetKind.MARKDOWN_DOCUMENT, flags, ("Markdown target is document-like metadata only.",)
    if extension == ".csv":
        return DownloadTargetKind.CSV_DOCUMENT, flags, ("CSV target is document-like metadata only.",)
    if extension == ".json":
        return DownloadTargetKind.JSON_DOCUMENT, flags, ("JSON target is document-like metadata only.",)
    if extension in {".png", ".jpg", ".jpeg", ".webp"}:
        flags.add(DownloadGovernanceFlag.IMAGE_REVIEW_REQUIRED)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        return DownloadTargetKind.IMAGE_FILE, flags, ("Image target is metadata only.",)
    if extension in {".zip", ".tar", ".gz", ".7z", ".rar", ".iso"}:
        flags.add(DownloadGovernanceFlag.ARCHIVE_REVIEW_REQUIRED)
        flags.add(DownloadGovernanceFlag.RISKY_FILE_EXTENSION)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        return DownloadTargetKind.ARCHIVE_FILE, flags, ("Archive target is high-risk metadata only.",)
    if extension in {".exe", ".bat", ".cmd", ".scr", ".app", ".deb", ".rpm", ".apk", ".dmg"}:
        flags.add(DownloadGovernanceFlag.EXECUTABLE_FILE_BLOCKED)
        flags.add(DownloadGovernanceFlag.RISKY_FILE_EXTENSION)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        return DownloadTargetKind.EXECUTABLE_FILE, flags, ("Executable target extensions are blocked.",)
    if extension in {".ps1", ".sh", ".py", ".js", ".mjs", ".vbs"}:
        flags.add(DownloadGovernanceFlag.SCRIPT_FILE_BLOCKED)
        flags.add(DownloadGovernanceFlag.RISKY_FILE_EXTENSION)
        flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        return DownloadTargetKind.SCRIPT_FILE, flags, ("Script target extensions are blocked.",)
    flags.add(DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED)
    notes.append("Target file type is unknown or not yet governed.")
    return DownloadTargetKind.UNKNOWN, flags, tuple(notes)


def _status_for(
    flags: set[DownloadGovernanceFlag],
    target_kind: DownloadTargetKind,
    request_data: dict[str, Any],
) -> DownloadGovernanceStatus:
    if not request_data["normalized_source_url"] or not request_data["normalized_target_path"]:
        return DownloadGovernanceStatus.MALFORMED_REQUEST
    if DownloadGovernanceFlag.INCONSISTENT_HASH_METADATA in flags:
        return DownloadGovernanceStatus.INCONSISTENT_METADATA
    if DownloadGovernanceFlag.UNSAFE_URL in flags:
        return DownloadGovernanceStatus.BLOCKED_UNSAFE_URL
    if DownloadGovernanceFlag.UNSAFE_TARGET_PATH in flags:
        return DownloadGovernanceStatus.BLOCKED_UNSAFE_TARGET_PATH
    if DownloadGovernanceFlag.SECRET_OR_TOKEN_PATTERN in flags:
        return DownloadGovernanceStatus.BLOCKED_CREDENTIAL_OR_SECRET_RISK
    if target_kind in {DownloadTargetKind.EXECUTABLE_FILE, DownloadTargetKind.SCRIPT_FILE}:
        return DownloadGovernanceStatus.BLOCKED_RISKY_FILE_TYPE
    if target_kind is DownloadTargetKind.UNKNOWN:
        return DownloadGovernanceStatus.NOT_YET_GOVERNED
    if DownloadGovernanceFlag.HUMAN_REVIEW_REQUIRED in flags:
        return DownloadGovernanceStatus.DOWNLOAD_REVIEW_REQUIRED
    return DownloadGovernanceStatus.DOWNLOAD_PREVIEW_READY


def _source_metadata_not_yet_governed(request_data: dict[str, Any]) -> bool:
    terms = set(request_data["source_statuses"]) | set(request_data["source_flags"])
    return bool(terms & {"NOT_YET_GOVERNED", "UNKNOWN_TOOL", "UNKNOWN_INTENT", "UNSAFE_INTENT", "UNSAFE_TOOL_NAME"})


def _unsafe_url(normalized_url: str) -> bool:
    unsafe_prefixes = (
        "javascript:",
        "data:",
        "file:",
        "about:",
        "chrome:",
        "ftp:",
    )
    unsafe_hosts_or_paths = (
        "169.254.169.254",
        "metadata.google.internal",
        "localhost",
        "127.0.0.1",
    )
    return normalized_url.startswith(unsafe_prefixes) or _contains_any(normalized_url, unsafe_hosts_or_paths)


def _secret_pattern_present(text: str) -> bool:
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
            "file:",
            "javascript:",
            "data:",
            "chrome:",
            "about:",
            "169.254.169.254",
            "metadata.google.internal",
            "localhost",
            "127.0.0.1",
            "rm -rf",
            "curl",
            "wget",
        ),
    )


def _secret_or_authority_metadata_present(combined_text: str) -> bool:
    return _contains_any(
        combined_text,
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
            "file:",
            "javascript:",
            "data:",
            "chrome:",
            "about:",
            "169.254.169.254",
            "metadata.google.internal",
            "localhost",
            "127.0.0.1",
            "rm -rf",
            "curl",
            "wget",
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "download_performed",
            "network_called",
            "url_fetched",
            "file_written",
            "directory_created",
            "quarantine_created",
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
        "download_performed",
        "network_called",
        "url_fetched",
        "file_written",
        "directory_created",
        "quarantine_created",
    }
    return any(bool(values.get(key)) for key in suspicious_keys)


def _inconsistent_hash_metadata(request_data: dict[str, Any]) -> bool:
    pairs = (
        ("source_action_proposal_id", "source_action_proposal_hash"),
        ("source_tool_call_preview_id", "source_tool_call_preview_hash"),
        ("source_intent_route_id", "source_intent_route_hash"),
        ("source_policy_check_id", "source_policy_check_hash"),
        ("source_test_runner_control_id", "source_test_runner_control_hash"),
    )
    for id_key, hash_key in pairs:
        source_id = request_data[id_key]
        source_hash = request_data[hash_key]
        if bool(source_id) != bool(source_hash):
            return True
        if source_hash and not _looks_like_hash(source_hash):
            return True
    expected_hash = request_data["expected_content_hash"]
    if expected_hash and not _looks_like_hash(expected_hash):
        return True
    return False


def _looks_like_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    hexdigits = set("0123456789abcdefABCDEF")
    return all(character in hexdigits for character in value)


def _provider_untrusted(source_trust: DownloadSourceTrust) -> bool:
    return source_trust in {
        DownloadSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        DownloadSourceTrust.PROVIDER_UNTRUSTED,
        DownloadSourceTrust.MODEL_UNTRUSTED,
    }


def _normalize_source_trust(value: DownloadSourceTrust | str) -> DownloadSourceTrust:
    if isinstance(value, DownloadSourceTrust):
        return value
    if not isinstance(value, str):
        return DownloadSourceTrust.UNKNOWN
    normalized = value.strip().upper()
    aliases = {
        "UNTRUSTED": DownloadSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_OUTPUT_UNTRUSTED": DownloadSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": DownloadSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": DownloadSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": DownloadSourceTrust.MODEL_UNTRUSTED,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return DownloadSourceTrust(normalized)
    except ValueError:
        return DownloadSourceTrust.UNKNOWN


def _normalize_source_url(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _normalize_target_path(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    normalized = "/".join(part for part in raw.split("/") if part != "")
    if raw.startswith("/"):
        return "/" + normalized
    return normalized


def _filename(value: str) -> str:
    if not value:
        return ""
    return value.rsplit("/", 1)[-1]


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].casefold()


def _quarantine_required(extension: str) -> bool:
    return extension in {
        ".exe",
        ".bat",
        ".cmd",
        ".ps1",
        ".sh",
        ".py",
        ".js",
        ".mjs",
        ".vbs",
        ".scr",
        ".app",
        ".deb",
        ".rpm",
        ".apk",
        ".dmg",
        ".iso",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
    }


def _quarantine_label(extension: str) -> str:
    if _quarantine_required(extension):
        return "quarantine_required_metadata_only"
    return "not_applicable"


def _is_absolute_path(value: str) -> bool:
    return value.startswith("/") or value.startswith("\\") or (len(value) > 1 and value[1] == ":")


def _contains_path_traversal(value: str) -> bool:
    return any(part == ".." for part in value.split("/"))


def _combined_text(request_data: dict[str, Any]) -> str:
    return _canonical_json(request_data).casefold()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _flag_tuple(values: Any) -> tuple[DownloadGovernanceFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("flags must be a tuple or list")
    return tuple(sorted((DownloadGovernanceFlag(value) for value in values), key=lambda flag: flag.value))


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
    status: DownloadGovernanceStatus,
    target_kind: DownloadTargetKind,
    extension: str,
    human_review_required: bool,
) -> str:
    return _bounded_text(
        f"Download governance metadata: status={status.value}; target_kind={target_kind.value}; "
        f"extension={extension or 'none'}; human_review_required={human_review_required}."
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
