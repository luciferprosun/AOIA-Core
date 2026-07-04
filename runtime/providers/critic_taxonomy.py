from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


CRITIC_TAXONOMY_SCHEMA_VERSION = "1A"
CRITIC_TAXONOMY_CLASSIFIED = "CLASSIFIED"
CRITIC_TAXONOMY_INVALID = "INVALID"

CRITIC_TAXONOMY_CLASSIFIED_METADATA_ONLY = "CRITIC_TAXONOMY_CLASSIFIED_METADATA_ONLY"
CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE = "CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE"
CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY = "CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY"
CRITIC_TAXONOMY_INVALID_DUPLICATE_CODE = "CRITIC_TAXONOMY_INVALID_DUPLICATE_CODE"
CRITIC_TAXONOMY_INVALID_AMBIGUOUS_SIGNAL = "CRITIC_TAXONOMY_INVALID_AMBIGUOUS_SIGNAL"
CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY = "CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY"
CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM = "CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM"

_HEX = frozenset("0123456789abcdef")
_CODE_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_AUTHORITY_FIELDS = (
    "approved",
    "authorized",
    "authority",
    "gate_satisfied",
    "can_approve",
    "can_execute",
    "can_write",
    "can_push",
    "can_call_provider",
    "can_change_gate",
    "approval_granted",
    "execution_authority_granted",
    "write_authority_granted",
    "push_authority_granted",
    "provider_authority_granted",
)


class CriticTaxonomyCategory(str, Enum):
    AUTHORITY_BOUNDARY = "AUTHORITY_BOUNDARY"
    EVIDENCE_INTEGRITY = "EVIDENCE_INTEGRITY"
    HASH_BINDING = "HASH_BINDING"
    PREVIEW_GOVERNANCE = "PREVIEW_GOVERNANCE"
    HUMAN_BARRIER = "HUMAN_BARRIER"
    METADATA_AS_AUTHORITY = "METADATA_AS_AUTHORITY"
    PROVIDER_TRUST = "PROVIDER_TRUST"
    WRITE_EXECUTION = "WRITE_EXECUTION"
    GIT_GOVERNANCE = "GIT_GOVERNANCE"
    PUSH_GOVERNANCE = "PUSH_GOVERNANCE"
    PATH_SANDBOX = "PATH_SANDBOX"
    TOCTOU = "TOCTOU"
    NETWORK_BOUNDARY = "NETWORK_BOUNDARY"
    PACKAGE_INSTALL_BOUNDARY = "PACKAGE_INSTALL_BOUNDARY"
    BROWSER_BOUNDARY = "BROWSER_BOUNDARY"
    DETERMINISM = "DETERMINISM"
    SCHEMA_VALIDATION = "SCHEMA_VALIDATION"
    UNKNOWN_OR_UNCLASSIFIED = "UNKNOWN_OR_UNCLASSIFIED"


class CriticTaxonomySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CriticTaxonomyEntry:
    schema_version: str
    code: str
    category: str
    severity: str
    title: str
    description: str
    match_flags: tuple[str, ...]
    match_check_ids: tuple[str, ...]
    entry_hash: str
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _required_text(self.schema_version))
        object.__setattr__(self, "code", _code(self.code))
        object.__setattr__(self, "category", _enum_value(self.category, CriticTaxonomyCategory))
        object.__setattr__(self, "severity", _enum_value(self.severity, CriticTaxonomySeverity))
        object.__setattr__(self, "title", _required_text(self.title))
        object.__setattr__(self, "description", _required_text(self.description))
        object.__setattr__(self, "match_flags", tuple(sorted(set(_signal(item) for item in self.match_flags))))
        object.__setattr__(self, "match_check_ids", tuple(sorted(set(_signal(item) for item in self.match_check_ids))))
        if self.entry_hash and not _sha256_like(self.entry_hash):
            raise ValueError("entry_hash must be a sha256 hex digest")
        for field_name in _AUTHORITY_FIELDS:
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "code": self.code,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "match_flags": self.match_flags,
            "match_check_ids": self.match_check_ids,
            "entry_hash": self.entry_hash,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
        }


@dataclass(frozen=True)
class CriticFindingClassification:
    schema_version: str
    finding_index: int
    source_check_id: str | None
    source_flag: str | None
    taxonomy_code: str
    category: str
    severity: str
    classification_hash: str
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.finding_index, int):
            raise ValueError("finding_index must be an integer")
        object.__setattr__(self, "taxonomy_code", _code(self.taxonomy_code))
        object.__setattr__(self, "category", _enum_value(self.category, CriticTaxonomyCategory))
        object.__setattr__(self, "severity", _enum_value(self.severity, CriticTaxonomySeverity))
        if not _sha256_like(self.classification_hash):
            raise ValueError("classification_hash must be a sha256 hex digest")
        for field_name in _AUTHORITY_FIELDS:
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "finding_index": self.finding_index,
            "source_check_id": self.source_check_id,
            "source_flag": self.source_flag,
            "taxonomy_code": self.taxonomy_code,
            "category": self.category,
            "severity": self.severity,
            "classification_hash": self.classification_hash,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
        }


@dataclass(frozen=True)
class CriticTaxonomyResult:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    taxonomy_hash: str | None
    classifications: tuple[CriticFindingClassification, ...]
    result_hash: str
    human_review_required: bool = True
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False
    gate_satisfied: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        object.__setattr__(self, "classifications", tuple(self.classifications))
        object.__setattr__(self, "human_review_required", True)
        for field_name in _AUTHORITY_FIELDS:
            if hasattr(self, field_name):
                object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "taxonomy_hash": self.taxonomy_hash,
            "classifications": tuple(item.to_dict() for item in self.classifications),
            "result_hash": self.result_hash,
            "human_review_required": True,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
            "gate_satisfied": False,
        }


def default_critic_taxonomy_entries() -> tuple[CriticTaxonomyEntry, ...]:
    return _DEFAULT_TAXONOMY


def compute_critic_taxonomy_hash(entries: tuple[CriticTaxonomyEntry, ...] | list[CriticTaxonomyEntry]) -> str:
    return _hash_json(tuple(_entry_material(item) for item in entries))


def classify_critic_findings(
    critic_report: Any,
    *,
    taxonomy_entries: tuple[CriticTaxonomyEntry, ...] | list[CriticTaxonomyEntry] | None = None,
    expected_taxonomy_hash: str | None = None,
) -> CriticTaxonomyResult:
    taxonomy = tuple(taxonomy_entries or _DEFAULT_TAXONOMY)
    validation = _validate_taxonomy(taxonomy)
    if validation is not None:
        return _result(
            status=CRITIC_TAXONOMY_INVALID,
            reason_codes=(validation,),
            taxonomy_hash=None,
            classifications=(),
        )

    taxonomy_hash = compute_critic_taxonomy_hash(taxonomy)
    if expected_taxonomy_hash is not None and expected_taxonomy_hash != taxonomy_hash:
        return _result(
            status=CRITIC_TAXONOMY_INVALID,
            reason_codes=(CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY,),
            taxonomy_hash=taxonomy_hash,
            classifications=(),
        )

    report = _mapping(critic_report)
    if report is None or _authority_claim_present(report):
        return _result(
            status=CRITIC_TAXONOMY_INVALID,
            reason_codes=(CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM if report else CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
            taxonomy_hash=taxonomy_hash,
            classifications=(),
        )

    checks = report.get("checks")
    if not isinstance(checks, (tuple, list)):
        return _result(
            status=CRITIC_TAXONOMY_INVALID,
            reason_codes=(CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
            taxonomy_hash=taxonomy_hash,
            classifications=(),
        )

    by_flag, by_check = _indexes(taxonomy)
    classifications: list[CriticFindingClassification] = []
    unknown = _unknown_entry(taxonomy)
    for index, raw_check in enumerate(checks):
        check = _mapping(raw_check)
        if check is None or _authority_claim_present(check):
            return _result(
                status=CRITIC_TAXONOMY_INVALID,
                reason_codes=(CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM if check else CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
                taxonomy_hash=taxonomy_hash,
                classifications=(),
            )
        check_id = _optional_signal(check.get("check_id"))
        flag = _optional_signal(check.get("flag"))
        if check_id is None and flag is None:
            return _result(
                status=CRITIC_TAXONOMY_INVALID,
                reason_codes=(CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
                taxonomy_hash=taxonomy_hash,
                classifications=(),
            )
        entry = by_flag.get(flag or "") or by_check.get(check_id or "") or unknown
        classifications.append(_classification(index, check_id, flag, entry))

    return _result(
        status=CRITIC_TAXONOMY_CLASSIFIED,
        reason_codes=(CRITIC_TAXONOMY_CLASSIFIED_METADATA_ONLY,),
        taxonomy_hash=taxonomy_hash,
        classifications=tuple(classifications),
    )


def _validate_taxonomy(entries: tuple[CriticTaxonomyEntry, ...]) -> str | None:
    if not entries:
        return CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY
    codes: set[str] = set()
    signals: dict[tuple[str, str], str] = {}
    for entry in entries:
        if not isinstance(entry, CriticTaxonomyEntry):
            return CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY
        if entry.schema_version != CRITIC_TAXONOMY_SCHEMA_VERSION:
            return CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY
        if entry.code in codes:
            return CRITIC_TAXONOMY_INVALID_DUPLICATE_CODE
        codes.add(entry.code)
        if entry.entry_hash != _hash_json(_entry_material(entry)):
            return CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY
        if _authority_claim_present(entry.to_dict()):
            return CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM
        for kind, values in (("flag", entry.match_flags), ("check", entry.match_check_ids)):
            for value in values:
                signal = (kind, value)
                if signal in signals and signals[signal] != entry.code:
                    return CRITIC_TAXONOMY_INVALID_AMBIGUOUS_SIGNAL
                signals[signal] = entry.code
    if "CRITIC_UNKNOWN_OR_UNCLASSIFIED" not in codes:
        return CRITIC_TAXONOMY_INVALID_MALFORMED_TAXONOMY
    return None


def _classification(index: int, check_id: str | None, flag: str | None, entry: CriticTaxonomyEntry) -> CriticFindingClassification:
    material = {
        "schema_version": CRITIC_TAXONOMY_SCHEMA_VERSION,
        "finding_index": index,
        "source_check_id": check_id,
        "source_flag": flag,
        "taxonomy_code": entry.code,
        "category": entry.category,
        "severity": entry.severity,
    }
    return CriticFindingClassification(classification_hash=_hash_json(material), **material)


def _result(
    *,
    status: str,
    reason_codes: tuple[str, ...],
    taxonomy_hash: str | None,
    classifications: tuple[CriticFindingClassification, ...],
) -> CriticTaxonomyResult:
    material = {
        "schema_version": CRITIC_TAXONOMY_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "taxonomy_hash": taxonomy_hash,
        "classifications": tuple(item.to_dict() for item in classifications),
        "human_review_required": True,
    }
    return CriticTaxonomyResult(
        schema_version=CRITIC_TAXONOMY_SCHEMA_VERSION,
        status=status,
        reason_codes=reason_codes,
        taxonomy_hash=taxonomy_hash,
        classifications=classifications,
        result_hash=_hash_json(material),
    )


def _indexes(entries: tuple[CriticTaxonomyEntry, ...]) -> tuple[dict[str, CriticTaxonomyEntry], dict[str, CriticTaxonomyEntry]]:
    by_flag: dict[str, CriticTaxonomyEntry] = {}
    by_check: dict[str, CriticTaxonomyEntry] = {}
    for entry in entries:
        for flag in entry.match_flags:
            by_flag[flag] = entry
        for check_id in entry.match_check_ids:
            by_check[check_id] = entry
    return by_flag, by_check


def _unknown_entry(entries: tuple[CriticTaxonomyEntry, ...]) -> CriticTaxonomyEntry:
    for entry in entries:
        if entry.code == "CRITIC_UNKNOWN_OR_UNCLASSIFIED":
            return entry
    raise ValueError("unknown taxonomy entry missing")


def _entry_material(entry: CriticTaxonomyEntry) -> dict[str, Any]:
    material = entry.to_dict()
    material.pop("entry_hash", None)
    for field_name in _AUTHORITY_FIELDS:
        material.pop(field_name, None)
    return material


def _mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        data = value.to_dict()
        if isinstance(data, Mapping):
            return dict(data)
    return None


def _authority_claim_present(value: Mapping[str, Any]) -> bool:
    return any(value.get(field_name) is True for field_name in _AUTHORITY_FIELDS)


def _entry(
    code: str,
    category: CriticTaxonomyCategory,
    severity: CriticTaxonomySeverity,
    title: str,
    description: str,
    *,
    flags: tuple[str, ...] = (),
    checks: tuple[str, ...] = (),
) -> CriticTaxonomyEntry:
    material = {
        "schema_version": CRITIC_TAXONOMY_SCHEMA_VERSION,
        "code": _code(code),
        "category": category.value,
        "severity": severity.value,
        "title": _required_text(title),
        "description": _required_text(description),
        "match_flags": tuple(sorted(set(_signal(item) for item in flags))),
        "match_check_ids": tuple(sorted(set(_signal(item) for item in checks))),
    }
    return CriticTaxonomyEntry(entry_hash=_hash_json(material), **material)


def _code(value: str) -> str:
    text = _required_text(value)
    if not text.startswith("CRITIC_") or any(char not in _CODE_CHARS for char in text):
        raise ValueError("taxonomy code must be stable uppercase CRITIC_* text")
    return text


def _signal(value: str) -> str:
    text = _required_text(value).strip().lower()
    if any(char.isspace() for char in text):
        raise ValueError("taxonomy signal must not contain whitespace")
    return text


def _optional_signal(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return _signal(value)


def _enum_value(value: Any, enum_type: type[Enum]) -> str:
    raw = value.value if isinstance(value, enum_type) else str(value)
    try:
        return str(enum_type(raw).value)
    except ValueError as error:
        raise ValueError("unsupported taxonomy enum value") from error


def _required_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("taxonomy text must be non-empty")
    return value.strip()


def _sha256_like(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


_DEFAULT_TAXONOMY: tuple[CriticTaxonomyEntry, ...] = (
    _entry(
        "CRITIC_PROVIDER_OUTPUT_UNTRUSTED",
        CriticTaxonomyCategory.PROVIDER_TRUST,
        CriticTaxonomySeverity.HIGH,
        "Provider output trust boundary",
        "Provider output is untrusted metadata and requires review.",
        flags=("provider_output_untrusted",),
        checks=("output_trust",),
    ),
    _entry(
        "CRITIC_AUTHORITY_CLAIM",
        CriticTaxonomyCategory.AUTHORITY_BOUNDARY,
        CriticTaxonomySeverity.CRITICAL,
        "Authority claim in critic input",
        "Critic finding identifies authority-like language or claims.",
        flags=("authority_claim_detected",),
        checks=("authority_language",),
    ),
    _entry(
        "CRITIC_EXECUTION_OR_WRITE_INSTRUCTION",
        CriticTaxonomyCategory.WRITE_EXECUTION,
        CriticTaxonomySeverity.HIGH,
        "Execution or write instruction",
        "Critic finding identifies execution or write instructions.",
        flags=("execution_instruction_detected",),
        checks=("execution_instruction",),
    ),
    _entry(
        "CRITIC_SHELL_BROWSER_OR_GIT_INSTRUCTION",
        CriticTaxonomyCategory.BROWSER_BOUNDARY,
        CriticTaxonomySeverity.CRITICAL,
        "Shell browser or git instruction",
        "Critic finding identifies shell, browser, or git instruction text.",
        flags=("shell_or_browser_instruction_detected",),
        checks=("shell_browser_git_instruction",),
    ),
    _entry(
        "CRITIC_APPROVAL_BYPASS_LANGUAGE",
        CriticTaxonomyCategory.METADATA_AS_AUTHORITY,
        CriticTaxonomySeverity.CRITICAL,
        "Approval bypass language",
        "Critic finding identifies language that attempts to bypass review or safety.",
        flags=("approval_bypass_language_detected",),
        checks=("approval_bypass_language",),
    ),
    _entry(
        "CRITIC_SECRET_LIKE_CONTENT",
        CriticTaxonomyCategory.EVIDENCE_INTEGRITY,
        CriticTaxonomySeverity.CRITICAL,
        "Secret-like content",
        "Critic finding identifies secret-like content that must remain redacted metadata.",
        flags=("secret_like_content_detected",),
        checks=("secret_like_content",),
    ),
    _entry(
        "CRITIC_PROVIDER_SWITCH_OR_FALLBACK",
        CriticTaxonomyCategory.PROVIDER_TRUST,
        CriticTaxonomySeverity.HIGH,
        "Provider fallback or switch",
        "Critic finding identifies provider fallback or switch language.",
        flags=("fallback_or_provider_switch_detected",),
        checks=("fallback_or_provider_switch",),
    ),
    _entry(
        "CRITIC_EMPTY_OR_MISSING_OUTPUT",
        CriticTaxonomyCategory.SCHEMA_VALIDATION,
        CriticTaxonomySeverity.WARNING,
        "Empty or missing output",
        "Critic finding identifies missing output evidence.",
        flags=("empty_or_missing_output",),
        checks=("output_present",),
    ),
    _entry(
        "CRITIC_METADATA_MISSING",
        CriticTaxonomyCategory.SCHEMA_VALIDATION,
        CriticTaxonomySeverity.WARNING,
        "Missing metadata",
        "Critic finding identifies missing or malformed metadata.",
        flags=("metadata_missing",),
        checks=("source_metadata",),
    ),
    _entry(
        "CRITIC_LIVE_OUTPUT_REQUIRES_REVIEW",
        CriticTaxonomyCategory.PROVIDER_TRUST,
        CriticTaxonomySeverity.WARNING,
        "Live output requires review",
        "Critic finding identifies live provider output requiring human review.",
        flags=("live_output_requires_review",),
        checks=("live_output_review",),
    ),
    _entry(
        "CRITIC_DRY_RUN_OUTPUT_ONLY",
        CriticTaxonomyCategory.DETERMINISM,
        CriticTaxonomySeverity.INFO,
        "Dry run output only",
        "Critic finding records dry-run metadata only.",
        flags=("dry_run_output_only",),
        checks=("dry_run_boundary",),
    ),
    _entry(
        "CRITIC_MOCK_OUTPUT_ONLY",
        CriticTaxonomyCategory.DETERMINISM,
        CriticTaxonomySeverity.INFO,
        "Mock output only",
        "Critic finding records deterministic mock metadata only.",
        flags=("mock_output_only",),
        checks=("mock_output_boundary",),
    ),
    _entry(
        "CRITIC_HASH_BINDING_REVIEW",
        CriticTaxonomyCategory.HASH_BINDING,
        CriticTaxonomySeverity.HIGH,
        "Hash binding review",
        "Critic taxonomy category reserved for hash-binding findings.",
    ),
    _entry(
        "CRITIC_PREVIEW_GOVERNANCE_REVIEW",
        CriticTaxonomyCategory.PREVIEW_GOVERNANCE,
        CriticTaxonomySeverity.HIGH,
        "Preview governance review",
        "Critic taxonomy category reserved for preview-governance findings.",
    ),
    _entry(
        "CRITIC_HUMAN_BARRIER_REVIEW",
        CriticTaxonomyCategory.HUMAN_BARRIER,
        CriticTaxonomySeverity.HIGH,
        "Human barrier review",
        "Critic taxonomy category reserved for human-barrier findings.",
    ),
    _entry(
        "CRITIC_GIT_GOVERNANCE_REVIEW",
        CriticTaxonomyCategory.GIT_GOVERNANCE,
        CriticTaxonomySeverity.HIGH,
        "Git governance review",
        "Critic taxonomy category reserved for git-governance findings.",
    ),
    _entry(
        "CRITIC_PUSH_GOVERNANCE_REVIEW",
        CriticTaxonomyCategory.PUSH_GOVERNANCE,
        CriticTaxonomySeverity.HIGH,
        "Push governance review",
        "Critic taxonomy category reserved for push-governance findings.",
    ),
    _entry(
        "CRITIC_PATH_SANDBOX_REVIEW",
        CriticTaxonomyCategory.PATH_SANDBOX,
        CriticTaxonomySeverity.HIGH,
        "Path sandbox review",
        "Critic taxonomy category reserved for path-sandbox findings.",
    ),
    _entry(
        "CRITIC_TOCTOU_REVIEW",
        CriticTaxonomyCategory.TOCTOU,
        CriticTaxonomySeverity.HIGH,
        "TOCTOU review",
        "Critic taxonomy category reserved for time-of-check/time-of-use findings.",
    ),
    _entry(
        "CRITIC_NETWORK_BOUNDARY_REVIEW",
        CriticTaxonomyCategory.NETWORK_BOUNDARY,
        CriticTaxonomySeverity.HIGH,
        "Network boundary review",
        "Critic taxonomy category reserved for network-boundary findings.",
    ),
    _entry(
        "CRITIC_PACKAGE_INSTALL_BOUNDARY_REVIEW",
        CriticTaxonomyCategory.PACKAGE_INSTALL_BOUNDARY,
        CriticTaxonomySeverity.HIGH,
        "Package install boundary review",
        "Critic taxonomy category reserved for package-install findings.",
    ),
    _entry(
        "CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        CriticTaxonomyCategory.UNKNOWN_OR_UNCLASSIFIED,
        CriticTaxonomySeverity.WARNING,
        "Unknown or unclassified finding",
        "Critic finding has no stable taxonomy mapping and remains review metadata.",
    ),
)
