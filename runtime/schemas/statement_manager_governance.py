from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


STATEMENT_GOVERNANCE_SCHEMA_VERSION = "AOIA_STATEMENT_GOVERNANCE_1A"
_MAX_SUMMARY_CHARS = 420


class StatementGovernanceStatus(str, Enum):
    STATEMENT_GOVERNANCE_PREVIEW_READY = "STATEMENT_GOVERNANCE_PREVIEW_READY"
    DOCUMENT_REVIEW_REQUIRED = "DOCUMENT_REVIEW_REQUIRED"
    SENSITIVE_DOCUMENT_REVIEW_REQUIRED = "SENSITIVE_DOCUMENT_REVIEW_REQUIRED"
    BLOCKED_UNSAFE_DOCUMENT_METADATA = "BLOCKED_UNSAFE_DOCUMENT_METADATA"
    BLOCKED_FINANCIAL_DECISION_ATTEMPT = "BLOCKED_FINANCIAL_DECISION_ATTEMPT"
    BLOCKED_LEGAL_DECISION_ATTEMPT = "BLOCKED_LEGAL_DECISION_ATTEMPT"
    BLOCKED_AUTOMATIC_FACT_EXTRACTION = "BLOCKED_AUTOMATIC_FACT_EXTRACTION"
    NOT_YET_GOVERNED = "NOT_YET_GOVERNED"
    MALFORMED_REQUEST = "MALFORMED_REQUEST"
    INCONSISTENT_METADATA = "INCONSISTENT_METADATA"


class StatementGovernanceFlag(str, Enum):
    STATEMENT_GOVERNANCE_METADATA_ONLY = "STATEMENT_GOVERNANCE_METADATA_ONLY"
    NO_FILE_READ = "NO_FILE_READ"
    NO_FILE_OPENED = "NO_FILE_OPENED"
    NO_FILE_WRITTEN = "NO_FILE_WRITTEN"
    NO_PDF_PARSE = "NO_PDF_PARSE"
    NO_OCR = "NO_OCR"
    NO_TEXT_EXTRACTION = "NO_TEXT_EXTRACTION"
    NO_FACT_EXTRACTION = "NO_FACT_EXTRACTION"
    NO_FINANCIAL_DECISION = "NO_FINANCIAL_DECISION"
    NO_LEGAL_DECISION = "NO_LEGAL_DECISION"
    NO_BENEFIT_DECISION = "NO_BENEFIT_DECISION"
    NO_NETWORK = "NO_NETWORK"
    NO_PROVIDER_CALL = "NO_PROVIDER_CALL"
    NO_EXECUTION = "NO_EXECUTION"
    NO_ENV_ACCESS = "NO_ENV_ACCESS"
    NO_API_KEY_ACCESS = "NO_API_KEY_ACCESS"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PROVIDER_OUTPUT_UNTRUSTED = "PROVIDER_OUTPUT_UNTRUSTED"
    SENSITIVE_DOCUMENT = "SENSITIVE_DOCUMENT"
    FINANCIAL_DOCUMENT = "FINANCIAL_DOCUMENT"
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
    OFFICIAL_DOCUMENT = "OFFICIAL_DOCUMENT"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    MEDICAL_DOCUMENT = "MEDICAL_DOCUMENT"
    BANK_STATEMENT_REVIEW_REQUIRED = "BANK_STATEMENT_REVIEW_REQUIRED"
    BENEFIT_DECISION_REVIEW_REQUIRED = "BENEFIT_DECISION_REVIEW_REQUIRED"
    AUTOMATIC_DECISION_BLOCKED = "AUTOMATIC_DECISION_BLOCKED"
    AUTOMATIC_FACT_EXTRACTION_BLOCKED = "AUTOMATIC_FACT_EXTRACTION_BLOCKED"
    UNSAFE_DOCUMENT_METADATA = "UNSAFE_DOCUMENT_METADATA"
    SUSPICIOUS_FILENAME = "SUSPICIOUS_FILENAME"
    RISKY_FILE_EXTENSION = "RISKY_FILE_EXTENSION"
    MISSING_FILE_HASH_METADATA = "MISSING_FILE_HASH_METADATA"
    INCONSISTENT_HASH_METADATA = "INCONSISTENT_HASH_METADATA"
    SUSPICIOUS_AUTHORITY_CLAIM = "SUSPICIOUS_AUTHORITY_CLAIM"
    SECRET_OR_TOKEN_PATTERN = "SECRET_OR_TOKEN_PATTERN"
    ACTION_PROPOSAL_METADATA_ONLY = "ACTION_PROPOSAL_METADATA_ONLY"
    TOOL_CALL_PREVIEW_METADATA_ONLY = "TOOL_CALL_PREVIEW_METADATA_ONLY"
    TOOL_REGISTRY_METADATA_ONLY = "TOOL_REGISTRY_METADATA_ONLY"
    INTENT_ROUTE_METADATA_ONLY = "INTENT_ROUTE_METADATA_ONLY"
    LOCAL_POLICY_METADATA_ONLY = "LOCAL_POLICY_METADATA_ONLY"
    TEST_RUNNER_METADATA_ONLY = "TEST_RUNNER_METADATA_ONLY"
    DOWNLOAD_GOVERNANCE_METADATA_ONLY = "DOWNLOAD_GOVERNANCE_METADATA_ONLY"


class StatementDocumentKind(str, Enum):
    BANK_STATEMENT = "BANK_STATEMENT"
    PAYSLIP = "PAYSLIP"
    OFFICIAL_LETTER = "OFFICIAL_LETTER"
    BENEFIT_DECISION = "BENEFIT_DECISION"
    TAX_DOCUMENT = "TAX_DOCUMENT"
    INVOICE = "INVOICE"
    RECEIPT = "RECEIPT"
    CONTRACT = "CONTRACT"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    MEDICAL_DOCUMENT = "MEDICAL_DOCUMENT"
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
    PDF_DOCUMENT = "PDF_DOCUMENT"
    TEXT_DOCUMENT = "TEXT_DOCUMENT"
    IMAGE_DOCUMENT = "IMAGE_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class StatementSensitivityClass(str, Enum):
    PUBLIC = "PUBLIC"
    LOW = "LOW"
    PERSONAL = "PERSONAL"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    MEDICAL = "MEDICAL"
    IDENTITY = "IDENTITY"
    OFFICIAL = "OFFICIAL"
    HIGH_RISK = "HIGH_RISK"
    UNKNOWN = "UNKNOWN"


class StatementSourceTrust(str, Enum):
    USER_SUPPLIED = "USER_SUPPLIED"
    UNTRUSTED_PROVIDER_OUTPUT = "UNTRUSTED_PROVIDER_OUTPUT"
    PROVIDER_UNTRUSTED = "PROVIDER_UNTRUSTED"
    MODEL_UNTRUSTED = "MODEL_UNTRUSTED"
    CRITIC_METADATA = "CRITIC_METADATA"
    SYSTEM_METADATA = "SYSTEM_METADATA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class StatementGovernanceRequest:
    document_label: str
    source_filename: str | None = None
    source_file_hash: str | None = None
    source_file_hash_algorithm: str | None = None
    source_url_hash: str | None = None
    source_download_governance_id: str | None = None
    source_download_governance_hash: str | None = None
    source_trust: StatementSourceTrust | str = StatementSourceTrust.UNKNOWN
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
class StatementGovernancePreview:
    schema_version: str
    statement_governance_id: str
    statement_governance_hash: str
    status: StatementGovernanceStatus
    document_kind: StatementDocumentKind
    sensitivity_class: StatementSensitivityClass
    document_label: str
    normalized_document_label: str
    document_label_hash: str
    source_filename: str | None
    source_file_extension: str
    source_file_hash: str | None
    source_file_hash_algorithm: str | None
    source_url_hash: str | None
    source_download_governance_id: str | None
    source_download_governance_hash: str | None
    source_trust: StatementSourceTrust
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
    facts_extracted: bool
    ocr_performed: bool
    parsing_performed: bool
    flags: tuple[StatementGovernanceFlag, ...]
    risk_notes: tuple[str, ...]
    display_summary: str
    file_read: bool = False
    file_opened: bool = False
    file_written: bool = False
    pdf_parsed: bool = False
    document_text_extracted: bool = False
    financial_decision_made: bool = False
    legal_decision_made: bool = False
    benefit_decision_made: bool = False
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
        object.__setattr__(self, "statement_governance_id", _text("statement_governance_id", self.statement_governance_id))
        object.__setattr__(self, "statement_governance_hash", _text("statement_governance_hash", self.statement_governance_hash))
        object.__setattr__(self, "status", StatementGovernanceStatus(self.status))
        object.__setattr__(self, "document_kind", StatementDocumentKind(self.document_kind))
        object.__setattr__(self, "sensitivity_class", StatementSensitivityClass(self.sensitivity_class))
        object.__setattr__(self, "document_label", _text("document_label", self.document_label))
        object.__setattr__(self, "normalized_document_label", _text("normalized_document_label", self.normalized_document_label))
        object.__setattr__(self, "document_label_hash", _text("document_label_hash", self.document_label_hash))
        object.__setattr__(self, "source_filename", _optional_text(self.source_filename))
        object.__setattr__(self, "source_file_extension", _text("source_file_extension", self.source_file_extension))
        object.__setattr__(self, "source_file_hash", _optional_text(self.source_file_hash))
        object.__setattr__(self, "source_file_hash_algorithm", _optional_text(self.source_file_hash_algorithm))
        object.__setattr__(self, "source_url_hash", _optional_text(self.source_url_hash))
        object.__setattr__(self, "source_download_governance_id", _optional_text(self.source_download_governance_id))
        object.__setattr__(self, "source_download_governance_hash", _optional_text(self.source_download_governance_hash))
        object.__setattr__(self, "source_trust", StatementSourceTrust(self.source_trust))
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
            "facts_extracted",
            "ocr_performed",
            "parsing_performed",
            "file_read",
            "file_opened",
            "file_written",
            "pdf_parsed",
            "document_text_extracted",
            "financial_decision_made",
            "legal_decision_made",
            "benefit_decision_made",
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
            "statement_governance_id": self.statement_governance_id,
            "statement_governance_hash": self.statement_governance_hash,
            "status": self.status.value,
            "document_kind": self.document_kind.value,
            "sensitivity_class": self.sensitivity_class.value,
            "document_label": self.document_label,
            "normalized_document_label": self.normalized_document_label,
            "document_label_hash": self.document_label_hash,
            "source_filename": self.source_filename,
            "source_file_extension": self.source_file_extension,
            "source_file_hash": self.source_file_hash,
            "source_file_hash_algorithm": self.source_file_hash_algorithm,
            "source_url_hash": self.source_url_hash,
            "source_download_governance_id": self.source_download_governance_id,
            "source_download_governance_hash": self.source_download_governance_hash,
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
            "facts_extracted": self.facts_extracted,
            "ocr_performed": self.ocr_performed,
            "parsing_performed": self.parsing_performed,
            "flags": [flag.value for flag in self.flags],
            "risk_notes": list(self.risk_notes),
            "display_summary": self.display_summary,
            "file_read": self.file_read,
            "file_opened": self.file_opened,
            "file_written": self.file_written,
            "pdf_parsed": self.pdf_parsed,
            "document_text_extracted": self.document_text_extracted,
            "financial_decision_made": self.financial_decision_made,
            "legal_decision_made": self.legal_decision_made,
            "benefit_decision_made": self.benefit_decision_made,
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


def build_statement_governance_preview(request: StatementGovernanceRequest) -> StatementGovernancePreview:
    if not isinstance(request, StatementGovernanceRequest):
        return _build_preview(
            request_data=_empty_request_data(),
            status=StatementGovernanceStatus.MALFORMED_REQUEST,
            document_kind=StatementDocumentKind.UNKNOWN,
            sensitivity_class=StatementSensitivityClass.UNKNOWN,
            source_trust=StatementSourceTrust.UNKNOWN,
            flags={StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED, StatementGovernanceFlag.UNSAFE_DOCUMENT_METADATA},
            risk_notes=("Malformed StatementGovernanceRequest input.",),
        )

    source_trust = _normalize_source_trust(request.source_trust)
    try:
        request_data = _request_data(request, source_trust)
    except (TypeError, ValueError):
        return _build_preview(
            request_data=_empty_request_data(),
            status=StatementGovernanceStatus.MALFORMED_REQUEST,
            document_kind=StatementDocumentKind.UNKNOWN,
            sensitivity_class=StatementSensitivityClass.UNKNOWN,
            source_trust=source_trust,
            flags={StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED, StatementGovernanceFlag.UNSAFE_DOCUMENT_METADATA},
            risk_notes=("Request metadata was not deterministic JSON data.",),
        )

    document_kind, sensitivity_class, class_flags, class_notes = _classify_document(request_data)
    flags = set(class_flags)
    risk_notes = list(class_notes)
    combined_text = _combined_text(request_data)

    if _provider_untrusted(source_trust):
        flags.add(StatementGovernanceFlag.PROVIDER_OUTPUT_UNTRUSTED)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Provider or model output is untrusted metadata only.")
    if request_data["source_file_hash"] is None:
        flags.add(StatementGovernanceFlag.MISSING_FILE_HASH_METADATA)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source file hash is missing; no file hash was computed.")
    if _inconsistent_hash_metadata(request_data):
        flags.add(StatementGovernanceFlag.INCONSISTENT_HASH_METADATA)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source IDs and hashes are missing, malformed, or inconsistent.")
    if _risky_extension(request_data["source_file_extension"]):
        flags.add(StatementGovernanceFlag.RISKY_FILE_EXTENSION)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source filename extension is risky metadata only.")
    if _suspicious_filename(request_data["source_filename"]):
        flags.add(StatementGovernanceFlag.SUSPICIOUS_FILENAME)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source filename contains suspicious metadata.")
    if _automatic_fact_request(combined_text):
        flags.add(StatementGovernanceFlag.AUTOMATIC_FACT_EXTRACTION_BLOCKED)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Automatic parsing, OCR, file reading, or fact extraction request was blocked.")
    if _financial_decision_request(combined_text):
        flags.add(StatementGovernanceFlag.AUTOMATIC_DECISION_BLOCKED)
        flags.add(StatementGovernanceFlag.FINANCIAL_DOCUMENT)
        flags.add(StatementGovernanceFlag.BENEFIT_DECISION_REVIEW_REQUIRED)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Automatic financial or benefit decision request was blocked.")
    if _legal_decision_request(combined_text):
        flags.add(StatementGovernanceFlag.AUTOMATIC_DECISION_BLOCKED)
        flags.add(StatementGovernanceFlag.LEGAL_DOCUMENT)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Automatic legal decision request was blocked.")
    if _unsafe_metadata(combined_text):
        flags.add(StatementGovernanceFlag.UNSAFE_DOCUMENT_METADATA)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Unsafe parser, OCR, secret, or authority-looking metadata was ignored as authority.")
    if _authority_claims_present(request.authority_claims):
        flags.add(StatementGovernanceFlag.SUSPICIOUS_AUTHORITY_CLAIM)
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Authority, parsing, extraction, or decision-completion claims were ignored.")
    if _source_metadata_not_yet_governed(request_data):
        flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
        risk_notes.append("Source metadata is not yet governed.")

    status = _status_for(flags, document_kind, sensitivity_class, request_data)
    return _build_preview(
        request_data=request_data,
        status=status,
        document_kind=document_kind,
        sensitivity_class=sensitivity_class,
        source_trust=source_trust,
        flags=flags,
        risk_notes=tuple(risk_notes),
    )


def _build_preview(
    *,
    request_data: dict[str, Any],
    status: StatementGovernanceStatus,
    document_kind: StatementDocumentKind,
    sensitivity_class: StatementSensitivityClass,
    source_trust: StatementSourceTrust,
    flags: set[StatementGovernanceFlag],
    risk_notes: tuple[str, ...],
) -> StatementGovernancePreview:
    base_flags = {
        StatementGovernanceFlag.STATEMENT_GOVERNANCE_METADATA_ONLY,
        StatementGovernanceFlag.NO_FILE_READ,
        StatementGovernanceFlag.NO_FILE_OPENED,
        StatementGovernanceFlag.NO_FILE_WRITTEN,
        StatementGovernanceFlag.NO_PDF_PARSE,
        StatementGovernanceFlag.NO_OCR,
        StatementGovernanceFlag.NO_TEXT_EXTRACTION,
        StatementGovernanceFlag.NO_FACT_EXTRACTION,
        StatementGovernanceFlag.NO_FINANCIAL_DECISION,
        StatementGovernanceFlag.NO_LEGAL_DECISION,
        StatementGovernanceFlag.NO_BENEFIT_DECISION,
        StatementGovernanceFlag.NO_NETWORK,
        StatementGovernanceFlag.NO_PROVIDER_CALL,
        StatementGovernanceFlag.NO_EXECUTION,
        StatementGovernanceFlag.NO_ENV_ACCESS,
        StatementGovernanceFlag.NO_API_KEY_ACCESS,
        StatementGovernanceFlag.ACTION_PROPOSAL_METADATA_ONLY,
        StatementGovernanceFlag.TOOL_CALL_PREVIEW_METADATA_ONLY,
        StatementGovernanceFlag.TOOL_REGISTRY_METADATA_ONLY,
        StatementGovernanceFlag.INTENT_ROUTE_METADATA_ONLY,
        StatementGovernanceFlag.LOCAL_POLICY_METADATA_ONLY,
        StatementGovernanceFlag.TEST_RUNNER_METADATA_ONLY,
        StatementGovernanceFlag.DOWNLOAD_GOVERNANCE_METADATA_ONLY,
    }
    all_flags = base_flags | set(flags)
    if status is not StatementGovernanceStatus.STATEMENT_GOVERNANCE_PREVIEW_READY:
        all_flags.add(StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED)
    ordered_flags = tuple(sorted(all_flags, key=lambda flag: flag.value))
    ordered_notes = tuple(sorted(set(risk_notes)))
    document_label_hash = _hash_json({"normalized_document_label": request_data["normalized_document_label"]})
    human_review_required = StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED in all_flags
    stable_payload = {
        "schema_version": STATEMENT_GOVERNANCE_SCHEMA_VERSION,
        "status": status.value,
        "document_kind": document_kind.value,
        "sensitivity_class": sensitivity_class.value,
        "document_label": request_data["document_label"],
        "normalized_document_label": request_data["normalized_document_label"],
        "document_label_hash": document_label_hash,
        "source_filename": request_data["source_filename"],
        "source_file_extension": request_data["source_file_extension"],
        "source_file_hash": request_data["source_file_hash"],
        "source_file_hash_algorithm": request_data["source_file_hash_algorithm"],
        "source_url_hash": request_data["source_url_hash"],
        "source_download_governance_id": request_data["source_download_governance_id"],
        "source_download_governance_hash": request_data["source_download_governance_hash"],
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
    return StatementGovernancePreview(
        schema_version=STATEMENT_GOVERNANCE_SCHEMA_VERSION,
        statement_governance_id=f"statement-governance-{governance_hash[:24]}",
        statement_governance_hash=governance_hash,
        status=status,
        document_kind=document_kind,
        sensitivity_class=sensitivity_class,
        document_label=request_data["document_label"],
        normalized_document_label=request_data["normalized_document_label"],
        document_label_hash=document_label_hash,
        source_filename=request_data["source_filename"],
        source_file_extension=request_data["source_file_extension"],
        source_file_hash=request_data["source_file_hash"],
        source_file_hash_algorithm=request_data["source_file_hash_algorithm"],
        source_url_hash=request_data["source_url_hash"],
        source_download_governance_id=request_data["source_download_governance_id"],
        source_download_governance_hash=request_data["source_download_governance_hash"],
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
        facts_extracted=False,
        ocr_performed=False,
        parsing_performed=False,
        flags=ordered_flags,
        risk_notes=ordered_notes,
        display_summary=_summary(status, document_kind, sensitivity_class, human_review_required),
    )


def _request_data(request: StatementGovernanceRequest, source_trust: StatementSourceTrust) -> dict[str, Any]:
    document_label = _text("document_label", request.document_label)
    source_filename = _optional_text(request.source_filename)
    return {
        "document_label": document_label,
        "normalized_document_label": _normalize_text(document_label),
        "source_filename": source_filename,
        "source_file_extension": _extension(source_filename or ""),
        "source_file_hash": _optional_text(request.source_file_hash),
        "source_file_hash_algorithm": _optional_text(request.source_file_hash_algorithm),
        "source_url_hash": _optional_text(request.source_url_hash),
        "source_download_governance_id": _optional_text(request.source_download_governance_id),
        "source_download_governance_hash": _optional_text(request.source_download_governance_hash),
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
        "document_label": "",
        "normalized_document_label": "",
        "source_filename": None,
        "source_file_extension": "",
        "source_file_hash": None,
        "source_file_hash_algorithm": None,
        "source_url_hash": None,
        "source_download_governance_id": None,
        "source_download_governance_hash": None,
        "source_trust": StatementSourceTrust.UNKNOWN.value,
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


def _classify_document(
    request_data: dict[str, Any],
) -> tuple[StatementDocumentKind, StatementSensitivityClass, set[StatementGovernanceFlag], tuple[str, ...]]:
    text = (request_data["normalized_document_label"] + " " + _normalize_text(request_data["source_filename"] or "")).casefold()
    flags: set[StatementGovernanceFlag] = {StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED}
    if _contains_any(text, ("bank statement", "kontoauszug", "account statement", "sparkasse statement", "revolut statement")):
        flags.update({
            StatementGovernanceFlag.SENSITIVE_DOCUMENT,
            StatementGovernanceFlag.FINANCIAL_DOCUMENT,
            StatementGovernanceFlag.BANK_STATEMENT_REVIEW_REQUIRED,
        })
        return StatementDocumentKind.BANK_STATEMENT, StatementSensitivityClass.FINANCIAL, flags, ("Bank statement metadata requires human review.",)
    if _contains_any(text, ("payslip", "lohnabrechnung", "salary slip", "pay slip")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.FINANCIAL_DOCUMENT})
        return StatementDocumentKind.PAYSLIP, StatementSensitivityClass.FINANCIAL, flags, ("Payslip metadata is financial and personal.",)
    if _contains_any(text, ("bescheid", "official letter", "arbeitsagentur", "jobcenter")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.OFFICIAL_DOCUMENT})
        if _contains_any(text, ("benefit", "leistung", "arbeitslosengeld", "burgergeld", "buergergeld", "jobcenter")):
            flags.add(StatementGovernanceFlag.BENEFIT_DECISION_REVIEW_REQUIRED)
            return StatementDocumentKind.BENEFIT_DECISION, StatementSensitivityClass.OFFICIAL, flags, ("Benefit decision metadata requires human review.",)
        return StatementDocumentKind.OFFICIAL_LETTER, StatementSensitivityClass.OFFICIAL, flags, ("Official letter metadata requires human review.",)
    if _contains_any(text, ("tax", "steuer", "finanzamt")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.FINANCIAL_DOCUMENT, StatementGovernanceFlag.OFFICIAL_DOCUMENT})
        return StatementDocumentKind.TAX_DOCUMENT, StatementSensitivityClass.FINANCIAL, flags, ("Tax document metadata requires human review.",)
    if _contains_any(text, ("invoice", "rechnung")):
        flags.update({StatementGovernanceFlag.FINANCIAL_DOCUMENT})
        return StatementDocumentKind.INVOICE, StatementSensitivityClass.FINANCIAL, flags, ("Invoice metadata is financial.",)
    if _contains_any(text, ("receipt", "quittung")):
        flags.update({StatementGovernanceFlag.FINANCIAL_DOCUMENT})
        return StatementDocumentKind.RECEIPT, StatementSensitivityClass.FINANCIAL, flags, ("Receipt metadata is financial.",)
    if _contains_any(text, ("contract", "vertrag")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.LEGAL_DOCUMENT})
        return StatementDocumentKind.CONTRACT, StatementSensitivityClass.LEGAL, flags, ("Contract metadata is legal-sensitive.",)
    if _contains_any(text, ("passport", "id card", "identity", "ausweis", "personalausweis")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.IDENTITY_DOCUMENT})
        return StatementDocumentKind.IDENTITY_DOCUMENT, StatementSensitivityClass.IDENTITY, flags, ("Identity document metadata is high risk.",)
    if _contains_any(text, ("medical", "doctor", "arzt", "diagnosis", "patient")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.MEDICAL_DOCUMENT})
        return StatementDocumentKind.MEDICAL_DOCUMENT, StatementSensitivityClass.MEDICAL, flags, ("Medical document metadata is high risk.",)
    if _contains_any(text, ("legal", "court", "gericht", "lawyer", "anwalt")):
        flags.update({StatementGovernanceFlag.SENSITIVE_DOCUMENT, StatementGovernanceFlag.LEGAL_DOCUMENT})
        return StatementDocumentKind.LEGAL_DOCUMENT, StatementSensitivityClass.LEGAL, flags, ("Legal document metadata requires human review.",)
    extension = request_data["source_file_extension"]
    if extension == ".pdf":
        return StatementDocumentKind.PDF_DOCUMENT, StatementSensitivityClass.UNKNOWN, flags, ("PDF document label is generic metadata only.",)
    if extension in {".txt", ".md", ".csv", ".json"}:
        return StatementDocumentKind.TEXT_DOCUMENT, StatementSensitivityClass.UNKNOWN, flags, ("Text-like document label is generic metadata only.",)
    if extension in {".png", ".jpg", ".jpeg", ".webp"}:
        return StatementDocumentKind.IMAGE_DOCUMENT, StatementSensitivityClass.UNKNOWN, flags, ("Image document label is generic metadata only.",)
    return StatementDocumentKind.UNKNOWN, StatementSensitivityClass.UNKNOWN, flags, ("Document type is unknown or not yet governed.",)


def _status_for(
    flags: set[StatementGovernanceFlag],
    document_kind: StatementDocumentKind,
    sensitivity_class: StatementSensitivityClass,
    request_data: dict[str, Any],
) -> StatementGovernanceStatus:
    if not request_data["normalized_document_label"]:
        return StatementGovernanceStatus.MALFORMED_REQUEST
    if StatementGovernanceFlag.INCONSISTENT_HASH_METADATA in flags:
        return StatementGovernanceStatus.INCONSISTENT_METADATA
    if StatementGovernanceFlag.AUTOMATIC_FACT_EXTRACTION_BLOCKED in flags:
        return StatementGovernanceStatus.BLOCKED_AUTOMATIC_FACT_EXTRACTION
    if StatementGovernanceFlag.AUTOMATIC_DECISION_BLOCKED in flags:
        if StatementGovernanceFlag.LEGAL_DOCUMENT in flags:
            return StatementGovernanceStatus.BLOCKED_LEGAL_DECISION_ATTEMPT
        return StatementGovernanceStatus.BLOCKED_FINANCIAL_DECISION_ATTEMPT
    if StatementGovernanceFlag.UNSAFE_DOCUMENT_METADATA in flags:
        return StatementGovernanceStatus.BLOCKED_UNSAFE_DOCUMENT_METADATA
    if document_kind is StatementDocumentKind.UNKNOWN:
        return StatementGovernanceStatus.NOT_YET_GOVERNED
    if sensitivity_class in {
        StatementSensitivityClass.FINANCIAL,
        StatementSensitivityClass.LEGAL,
        StatementSensitivityClass.MEDICAL,
        StatementSensitivityClass.IDENTITY,
        StatementSensitivityClass.OFFICIAL,
        StatementSensitivityClass.HIGH_RISK,
    }:
        return StatementGovernanceStatus.SENSITIVE_DOCUMENT_REVIEW_REQUIRED
    if StatementGovernanceFlag.HUMAN_REVIEW_REQUIRED in flags:
        return StatementGovernanceStatus.DOCUMENT_REVIEW_REQUIRED
    return StatementGovernanceStatus.STATEMENT_GOVERNANCE_PREVIEW_READY


def _source_metadata_not_yet_governed(request_data: dict[str, Any]) -> bool:
    terms = set(request_data["source_statuses"]) | set(request_data["source_flags"])
    return bool(terms & {"NOT_YET_GOVERNED", "UNKNOWN_TOOL", "UNKNOWN_INTENT", "UNSAFE_INTENT", "UNSAFE_DOCUMENT_METADATA"})


def _automatic_fact_request(text: str) -> bool:
    return _contains_any(
        text,
        (
            "extract facts automatically",
            "parse now",
            "ocr now",
            "read file",
            "open file",
            "pdf" + "plumber",
            "pymu" + "pdf",
            "fi" + "tz",
            "pytess" + "eract",
            "file_read",
            "pdf_parsed",
            "ocr_performed",
            "facts_extracted",
        ),
    )


def _financial_decision_request(text: str) -> bool:
    return _contains_any(
        text,
        (
            "decide eligibility",
            "approve benefit",
            "reject benefit",
            "make financial decision",
            "benefit_decision_made",
            "financial_decision_made",
        ),
    )


def _legal_decision_request(text: str) -> bool:
    return _contains_any(text, ("calculate legal entitlement", "legal_decision_made"))


def _unsafe_metadata(text: str) -> bool:
    return _contains_any(
        text,
        (
            "send to arbeitsagentur",
            "auto reply",
            "api" + "_key",
            "secret",
            "token",
            "approval_granted",
            "can_execute",
            "allowed",
            "permission",
            "tool_allowed",
            "gate_result",
            "file_read",
            "pdf_parsed",
            "ocr_performed",
            "facts_extracted",
            "financial_decision_made",
            "legal_decision_made",
            "benefit_decision_made",
        ),
    )


def _authority_claims_present(values: Mapping[str, Any] | None) -> bool:
    if values is None:
        return False
    if not isinstance(values, Mapping):
        return True
    suspicious_keys = {
        "approval_granted",
        "can_execute",
        "allowed",
        "permission",
        "tool_allowed",
        "gate_result",
        "file_read",
        "file_opened",
        "file_written",
        "pdf_parsed",
        "ocr_performed",
        "facts_extracted",
        "financial_decision_made",
        "legal_decision_made",
        "benefit_decision_made",
    }
    return any(bool(values.get(key)) for key in suspicious_keys)


def _inconsistent_hash_metadata(request_data: dict[str, Any]) -> bool:
    pairs = (
        ("source_download_governance_id", "source_download_governance_hash"),
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
    for hash_key in ("source_file_hash", "source_url_hash"):
        source_hash = request_data[hash_key]
        if source_hash and not _looks_like_hash(source_hash):
            return True
    return False


def _looks_like_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    hexdigits = set("0123456789abcdefABCDEF")
    return all(character in hexdigits for character in value)


def _risky_extension(extension: str) -> bool:
    return extension in {".exe", ".bat", ".cmd", ".ps1", ".sh", ".py", ".js", ".mjs", ".vbs", ".scr", ".app"}


def _suspicious_filename(value: str | None) -> bool:
    if value is None:
        return False
    text = _normalize_text(value)
    return "\x00" in value or _contains_any(text, ("../", "/..", "secret", "token", "api" + "_key"))


def _provider_untrusted(source_trust: StatementSourceTrust) -> bool:
    return source_trust in {
        StatementSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        StatementSourceTrust.PROVIDER_UNTRUSTED,
        StatementSourceTrust.MODEL_UNTRUSTED,
    }


def _normalize_source_trust(value: StatementSourceTrust | str) -> StatementSourceTrust:
    if isinstance(value, StatementSourceTrust):
        return value
    if not isinstance(value, str):
        return StatementSourceTrust.UNKNOWN
    normalized = value.strip().upper()
    aliases = {
        "UNTRUSTED": StatementSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_OUTPUT_UNTRUSTED": StatementSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "UNTRUSTED_PROVIDER_OUTPUT": StatementSourceTrust.UNTRUSTED_PROVIDER_OUTPUT,
        "PROVIDER_UNTRUSTED": StatementSourceTrust.PROVIDER_UNTRUSTED,
        "MODEL_UNTRUSTED": StatementSourceTrust.MODEL_UNTRUSTED,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return StatementSourceTrust(normalized)
    except ValueError:
        return StatementSourceTrust.UNKNOWN


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].casefold()


def _combined_text(request_data: dict[str, Any]) -> str:
    return _canonical_json(request_data).casefold()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _flag_tuple(values: Any) -> tuple[StatementGovernanceFlag, ...]:
    if not isinstance(values, (tuple, list)):
        raise TypeError("flags must be a tuple or list")
    return tuple(sorted((StatementGovernanceFlag(value) for value in values), key=lambda flag: flag.value))


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
    status: StatementGovernanceStatus,
    document_kind: StatementDocumentKind,
    sensitivity_class: StatementSensitivityClass,
    human_review_required: bool,
) -> str:
    return _bounded_text(
        f"Statement governance metadata: status={status.value}; document_kind={document_kind.value}; "
        f"sensitivity_class={sensitivity_class.value}; human_review_required={human_review_required}."
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
