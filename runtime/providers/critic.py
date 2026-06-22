from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from runtime.providers.contracts import ProviderRuntimeResult, UNTRUSTED
from runtime.providers.redaction import REDACTED, redact_provider_text


class ProviderCriticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class ProviderCriticVerdict(str, Enum):
    REVIEW_ONLY = "review_only"
    WARNING = "warning"
    BLOCKED = "blocked"
    INVALID_INPUT = "invalid_input"


class ProviderCriticFlag(str, Enum):
    PROVIDER_OUTPUT_UNTRUSTED = "provider_output_untrusted"
    AUTHORITY_CLAIM_DETECTED = "authority_claim_detected"
    EXECUTION_INSTRUCTION_DETECTED = "execution_instruction_detected"
    SHELL_OR_BROWSER_INSTRUCTION_DETECTED = "shell_or_browser_instruction_detected"
    APPROVAL_BYPASS_LANGUAGE_DETECTED = "approval_bypass_language_detected"
    SECRET_LIKE_CONTENT_DETECTED = "secret_like_content_detected"
    FALLBACK_OR_PROVIDER_SWITCH_DETECTED = "fallback_or_provider_switch_detected"
    EMPTY_OR_MISSING_OUTPUT = "empty_or_missing_output"
    METADATA_MISSING = "metadata_missing"
    LIVE_OUTPUT_REQUIRES_REVIEW = "live_output_requires_review"
    DRY_RUN_OUTPUT_ONLY = "dry_run_output_only"
    MOCK_OUTPUT_ONLY = "mock_output_only"


_AUTHORITY_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|approval\s+granted|authorization\s+granted)\b"
)
_EXECUTION_PATTERN = re.compile(
    r"(?i)\b(?:execute\s+this|run\s+this|write\s+this\s+file|write\s+file)\b"
)
_SHELL_BROWSER_PATTERN = re.compile(
    r"(?i)(?:rm\s+-rf|\bsudo\b|curl\s+https?://|wget(?:\s+https?://)?|"
    r"\bbash\b|\bsubprocess\b|open\s+(?:the\s+)?browser|\bgit\s+push\b)"
)
_BYPASS_PATTERN = re.compile(
    r"(?i)\b(?:bypass\s+(?:policy|approval|safety)|ignore\s+safety|"
    r"skip\s+(?:approval|review))\b"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(?:\bsk-[A-Za-z0-9_-]{4,}|\bapi[_ -]?key\b|authorization\s*:|"
    r"\bbearer\s+[A-Za-z0-9._~+/=-]+)"
)
_FALLBACK_PATTERN = re.compile(
    r"(?i)\b(?:fallback|switch\s+(?:the\s+)?provider|use\s+another\s+provider)\b"
)
_MAX_EVIDENCE_CHARS = 160
_KNOWN_FLAGS = frozenset(item.value for item in ProviderCriticFlag)


@dataclass(frozen=True)
class ProviderCriticCheckResult:
    check_id: str
    passed: bool
    severity: str
    flag: str | None
    reason: str
    evidence_excerpt: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "check_id", _required_text(self.check_id, "check_id"))
        if not isinstance(self.passed, bool):
            raise ValueError("passed must be boolean")
        severity = _enum_value(self.severity, ProviderCriticSeverity, "severity")
        object.__setattr__(self, "severity", severity)
        if self.flag is not None:
            flag = str(self.flag)
            if flag not in _KNOWN_FLAGS:
                raise ValueError("unknown provider critic flag")
            object.__setattr__(self, "flag", flag)
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        if self.evidence_excerpt is not None:
            evidence = redact_provider_text(self.evidence_excerpt).strip()
            object.__setattr__(self, "evidence_excerpt", evidence[:_MAX_EVIDENCE_CHARS])

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "severity": self.severity,
            "flag": self.flag,
            "reason": self.reason,
            "evidence_excerpt": self.evidence_excerpt,
        }


@dataclass(frozen=True)
class ProviderCriticReport:
    provider_id: str
    model_id: str | None
    source_mode: str
    source_status: str
    verdict: str
    flags: tuple[str, ...]
    checks: tuple[ProviderCriticCheckResult, ...]
    summary: str
    human_review_required: bool
    report_id: str = field(init=False)
    output_trust: str = UNTRUSTED
    can_approve: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        provider_id = _optional_text(self.provider_id) or "unknown"
        model_id = _optional_text(self.model_id)
        source_mode = _optional_text(self.source_mode) or "unknown"
        source_status = _optional_text(self.source_status) or "unknown"
        verdict = _enum_value(self.verdict, ProviderCriticVerdict, "verdict")
        checks = tuple(self.checks)
        if not all(isinstance(item, ProviderCriticCheckResult) for item in checks):
            raise ValueError("checks must contain ProviderCriticCheckResult values")
        flags = tuple(dict.fromkeys(str(item) for item in self.flags))
        if any(item not in _KNOWN_FLAGS for item in flags):
            raise ValueError("flags contain an unknown provider critic flag")
        summary = redact_provider_text(_required_text(self.summary, "summary"))[:512]
        material = {
            "provider_id": provider_id,
            "model_id": model_id,
            "source_mode": source_mode,
            "source_status": source_status,
            "output_trust": UNTRUSTED,
            "verdict": verdict,
            "flags": flags,
            "checks": [item.to_dict() for item in checks],
            "summary": summary,
            "human_review_required": bool(self.human_review_required),
        }
        digest = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "provider_id", provider_id)
        object.__setattr__(self, "model_id", model_id)
        object.__setattr__(self, "source_mode", source_mode)
        object.__setattr__(self, "source_status", source_status)
        object.__setattr__(self, "output_trust", UNTRUSTED)
        object.__setattr__(self, "verdict", verdict)
        object.__setattr__(self, "flags", flags)
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "human_review_required", True)
        object.__setattr__(self, "can_approve", False)
        object.__setattr__(self, "can_execute", False)
        object.__setattr__(self, "can_write", False)
        object.__setattr__(self, "can_change_gate", False)
        object.__setattr__(self, "report_id", "provider-critic-" + digest[:24])

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "source_mode": self.source_mode,
            "source_status": self.source_status,
            "output_trust": UNTRUSTED,
            "verdict": self.verdict,
            "flags": list(self.flags),
            "checks": [item.to_dict() for item in self.checks],
            "summary": self.summary,
            "human_review_required": True,
            "can_approve": False,
            "can_execute": False,
            "can_write": False,
            "can_change_gate": False,
        }


def critique_provider_result(source: object) -> ProviderCriticReport:
    mapping, structurally_valid = _source_mapping(source)
    provider_id = _optional_text(mapping.get("provider_id")) or "unknown"
    model_id = _optional_text(mapping.get("model_id"))
    source_mode = _optional_text(mapping.get("mode")) or "unknown"
    source_status = _optional_text(mapping.get("status")) or "unknown"
    declared_trust = _optional_text(
        mapping.get("trust_status", mapping.get("output_trust"))
    )
    metadata_complete = all(
        (
            provider_id != "unknown",
            source_mode != "unknown",
            source_status != "unknown",
            declared_trust is not None,
        )
    )
    text = _critic_text(mapping)
    checks: list[ProviderCriticCheckResult] = []

    checks.append(
        _check(
            "source_metadata",
            structurally_valid and metadata_complete,
            ProviderCriticSeverity.WARNING,
            (
                None
                if structurally_valid and metadata_complete
                else ProviderCriticFlag.METADATA_MISSING
            ),
            "provider result metadata is present"
            if structurally_valid and metadata_complete
            else "provider result metadata is missing or malformed",
        )
    )
    trust_passed = declared_trust == UNTRUSTED
    checks.append(
        _check(
            "output_trust",
            trust_passed,
            ProviderCriticSeverity.HIGH,
            ProviderCriticFlag.PROVIDER_OUTPUT_UNTRUSTED,
            "provider output remains explicitly UNTRUSTED"
            if trust_passed
            else "provider output did not declare UNTRUSTED trust",
        )
    )
    checks.append(
        _check(
            "output_present",
            bool(text),
            ProviderCriticSeverity.WARNING,
            None if text else ProviderCriticFlag.EMPTY_OR_MISSING_OUTPUT,
            "provider output or preview is present"
            if text
            else "provider output and preview are empty",
        )
    )
    checks.extend(
        (
            _pattern_check(
                "authority_language",
                text,
                _AUTHORITY_PATTERN,
                ProviderCriticSeverity.CRITICAL,
                ProviderCriticFlag.AUTHORITY_CLAIM_DETECTED,
                "authority language detected in untrusted provider output",
            ),
            _pattern_check(
                "execution_instruction",
                text,
                _EXECUTION_PATTERN,
                ProviderCriticSeverity.HIGH,
                ProviderCriticFlag.EXECUTION_INSTRUCTION_DETECTED,
                "execution or write instruction detected",
            ),
            _pattern_check(
                "shell_browser_git_instruction",
                text,
                _SHELL_BROWSER_PATTERN,
                ProviderCriticSeverity.CRITICAL,
                ProviderCriticFlag.SHELL_OR_BROWSER_INSTRUCTION_DETECTED,
                "shell, browser, or git instruction detected",
            ),
            _pattern_check(
                "approval_bypass_language",
                text,
                _BYPASS_PATTERN,
                ProviderCriticSeverity.CRITICAL,
                ProviderCriticFlag.APPROVAL_BYPASS_LANGUAGE_DETECTED,
                "approval or safety bypass language detected",
            ),
            _secret_check(text),
            _pattern_check(
                "fallback_or_provider_switch",
                text,
                _FALLBACK_PATTERN,
                ProviderCriticSeverity.HIGH,
                ProviderCriticFlag.FALLBACK_OR_PROVIDER_SWITCH_DETECTED,
                "fallback or provider-switch instruction detected",
            ),
        )
    )
    if source_mode == "live":
        checks.append(
            _check(
                "live_output_review",
                False,
                ProviderCriticSeverity.WARNING,
                ProviderCriticFlag.LIVE_OUTPUT_REQUIRES_REVIEW,
                "live provider output requires explicit human review",
            )
        )
    elif source_mode == "dry_run":
        checks.append(
            _check(
                "dry_run_boundary",
                True,
                ProviderCriticSeverity.INFO,
                ProviderCriticFlag.DRY_RUN_OUTPUT_ONLY,
                "source is a dry-run output or payload preview only",
            )
        )
    if provider_id == "mock_chat":
        checks.append(
            _check(
                "mock_output_boundary",
                True,
                ProviderCriticSeverity.INFO,
                ProviderCriticFlag.MOCK_OUTPUT_ONLY,
                "source is deterministic mock output only",
            )
        )

    invalid_input = not structurally_valid or not metadata_complete or not trust_passed
    verdict = _verdict(checks, invalid_input=invalid_input)
    flags = tuple(
        dict.fromkeys(item.flag for item in checks if item.flag is not None)
    )
    failed_count = sum(not item.passed for item in checks)
    summary = (
        f"Provider output critic completed with verdict {verdict.value}; "
        f"{failed_count} check(s) require attention. Output remains UNTRUSTED."
    )
    return ProviderCriticReport(
        provider_id=provider_id,
        model_id=model_id,
        source_mode=source_mode,
        source_status=source_status,
        verdict=verdict.value,
        flags=flags,
        checks=tuple(checks),
        summary=summary,
        human_review_required=True,
    )


def _source_mapping(source: object) -> tuple[dict[str, Any], bool]:
    if isinstance(source, ProviderRuntimeResult):
        return source.to_dict(), True
    if isinstance(source, Mapping):
        return dict(source), True
    names = (
        "provider_id",
        "model_id",
        "mode",
        "status",
        "response_text",
        "redacted_request_preview",
        "trust_status",
    )
    if any(hasattr(source, name) for name in names):
        return {name: getattr(source, name, None) for name in names}, True
    return {}, False


def _critic_text(mapping: Mapping[str, Any]) -> str:
    response_text = mapping.get("response_text")
    if isinstance(response_text, str) and response_text.strip():
        return response_text.strip()
    preview = mapping.get("redacted_request_preview", mapping.get("payload_preview"))
    return preview.strip() if isinstance(preview, str) else ""


def _pattern_check(
    check_id: str,
    text: str,
    pattern: re.Pattern[str],
    severity: ProviderCriticSeverity,
    flag: ProviderCriticFlag,
    failure_reason: str,
) -> ProviderCriticCheckResult:
    match = pattern.search(text)
    return _check(
        check_id,
        match is None,
        severity,
        None if match is None else flag,
        "no matching unsafe language detected" if match is None else failure_reason,
        evidence_excerpt=_excerpt(text, match) if match is not None else None,
    )


def _secret_check(text: str) -> ProviderCriticCheckResult:
    match = _SECRET_PATTERN.search(text)
    return _check(
        "secret_like_content",
        match is None,
        ProviderCriticSeverity.CRITICAL,
        None if match is None else ProviderCriticFlag.SECRET_LIKE_CONTENT_DETECTED,
        "no secret-like content detected"
        if match is None
        else "secret-like content detected and evidence redacted",
        evidence_excerpt=REDACTED if match is not None else None,
    )


def _check(
    check_id: str,
    passed: bool,
    severity: ProviderCriticSeverity,
    flag: ProviderCriticFlag | None,
    reason: str,
    evidence_excerpt: str | None = None,
) -> ProviderCriticCheckResult:
    return ProviderCriticCheckResult(
        check_id=check_id,
        passed=passed,
        severity=severity.value,
        flag=flag.value if flag is not None else None,
        reason=reason,
        evidence_excerpt=evidence_excerpt,
    )


def _verdict(
    checks: list[ProviderCriticCheckResult],
    *,
    invalid_input: bool,
) -> ProviderCriticVerdict:
    if invalid_input:
        return ProviderCriticVerdict.INVALID_INPUT
    failed = [item for item in checks if not item.passed]
    if any(item.severity in {"high", "critical"} for item in failed):
        return ProviderCriticVerdict.BLOCKED
    if failed:
        return ProviderCriticVerdict.WARNING
    return ProviderCriticVerdict.REVIEW_ONLY


def _excerpt(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + 40)
    return redact_provider_text(text[start:end])[:_MAX_EVIDENCE_CHARS]


def _enum_value(value: object, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, enum_type) else str(value)
    try:
        return str(enum_type(raw).value)
    except ValueError as error:
        raise ValueError(f"unsupported {field_name}") from error


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
