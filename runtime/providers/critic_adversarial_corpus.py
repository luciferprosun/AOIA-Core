from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from runtime.providers.critic_taxonomy import (
    CRITIC_TAXONOMY_INVALID_AMBIGUOUS_SIGNAL,
    CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM,
    CRITIC_TAXONOMY_INVALID_DUPLICATE_CODE,
    CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,
    CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY,
    CriticTaxonomyCategory,
    CriticTaxonomySeverity,
)


CRITIC_ADVERSARIAL_CORPUS_SCHEMA_VERSION = "1A"


@dataclass(frozen=True)
class CriticAdversarialCase:
    schema_version: str
    case_id: str
    title: str
    taxonomy_code: str
    subject: str
    adversarial_evidence: Mapping[str, Any]
    expected_category: str
    expected_severity: str
    expected_fail_closed: bool
    expected_errors: tuple[str, ...]
    case_hash: str

    def __post_init__(self) -> None:
        if self.schema_version != CRITIC_ADVERSARIAL_CORPUS_SCHEMA_VERSION:
            raise ValueError("unsupported critic adversarial corpus schema version")
        for field_name in ("case_id", "title", "taxonomy_code", "subject"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be non-empty text")
        if not self.taxonomy_code.startswith("CRITIC_"):
            raise ValueError("taxonomy_code must be stable CRITIC_* text")
        if not isinstance(self.adversarial_evidence, Mapping):
            raise ValueError("adversarial_evidence must be mapping metadata")
        if not isinstance(self.expected_fail_closed, bool):
            raise ValueError("expected_fail_closed must be boolean")
        object.__setattr__(self, "expected_errors", tuple(str(item) for item in self.expected_errors))
        if self.case_hash != compute_critic_adversarial_case_hash(self):
            raise ValueError("case_hash does not match critic adversarial case evidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "title": self.title,
            "taxonomy_code": self.taxonomy_code,
            "subject": self.subject,
            "adversarial_evidence": self.adversarial_evidence,
            "expected_category": self.expected_category,
            "expected_severity": self.expected_severity,
            "expected_fail_closed": self.expected_fail_closed,
            "expected_errors": self.expected_errors,
            "case_hash": self.case_hash,
        }


def default_critic_adversarial_cases() -> tuple[CriticAdversarialCase, ...]:
    return _ADVERSARIAL_CASES


def compute_critic_adversarial_case_hash(value: CriticAdversarialCase | Mapping[str, Any]) -> str:
    return _hash_json(_case_material(value))


def _case(
    *,
    case_id: str,
    title: str,
    taxonomy_code: str,
    subject: str,
    adversarial_evidence: Mapping[str, Any],
    expected_category: CriticTaxonomyCategory,
    expected_severity: CriticTaxonomySeverity,
    expected_fail_closed: bool = False,
    expected_errors: tuple[str, ...] = (),
) -> CriticAdversarialCase:
    material = {
        "schema_version": CRITIC_ADVERSARIAL_CORPUS_SCHEMA_VERSION,
        "case_id": case_id,
        "title": title,
        "taxonomy_code": taxonomy_code,
        "subject": subject,
        "adversarial_evidence": dict(adversarial_evidence),
        "expected_category": expected_category.value,
        "expected_severity": expected_severity.value,
        "expected_fail_closed": expected_fail_closed,
        "expected_errors": tuple(expected_errors),
    }
    return CriticAdversarialCase(case_hash=_hash_json(material), **material)


def _case_material(value: CriticAdversarialCase | Mapping[str, Any]) -> dict[str, Any]:
    material = value.to_dict() if isinstance(value, CriticAdversarialCase) else dict(value)
    material.pop("case_hash", None)
    return material


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


_ADVERSARIAL_CASES: tuple[CriticAdversarialCase, ...] = (
    _case(
        case_id="critic_adv_1a_top_level_approval_forgery",
        title="Top-level approval forgery",
        taxonomy_code="CRITIC_AUTHORITY_CLAIM",
        subject="authority_claim",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "authority_language",
                    "passed": False,
                    "severity": "critical",
                    "flag": "authority_claim_detected",
                    "reason": "adversarial report claims approval should be accepted",
                },
            ),
            "approved": True,
        },
        expected_category=CriticTaxonomyCategory.AUTHORITY_BOUNDARY,
        expected_severity=CriticTaxonomySeverity.CRITICAL,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM,),
    ),
    _case(
        case_id="critic_adv_1a_check_level_push_authority_forgery",
        title="Check-level push authority forgery",
        taxonomy_code="CRITIC_AUTHORITY_CLAIM",
        subject="authority_claim",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "authority_language",
                    "passed": False,
                    "severity": "critical",
                    "flag": "authority_claim_detected",
                    "reason": "finding tries to grant push authority",
                    "can_push": True,
                },
            )
        },
        expected_category=CriticTaxonomyCategory.AUTHORITY_BOUNDARY,
        expected_severity=CriticTaxonomySeverity.CRITICAL,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_AUTHORITY_CLAIM,),
    ),
    _case(
        case_id="critic_adv_1a_severity_permission_confusion",
        title="Severity confused with permission",
        taxonomy_code="CRITIC_APPROVAL_BYPASS_LANGUAGE",
        subject="metadata_as_authority",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "approval_bypass_language",
                    "passed": False,
                    "severity": "critical",
                    "flag": "approval_bypass_language_detected",
                    "reason": "critical severity is not approval, permission, or a gate result",
                },
            )
        },
        expected_category=CriticTaxonomyCategory.METADATA_AS_AUTHORITY,
        expected_severity=CriticTaxonomySeverity.CRITICAL,
    ),
    _case(
        case_id="critic_adv_1a_execution_git_browser_smuggling",
        title="Execution git browser capability smuggling",
        taxonomy_code="CRITIC_SHELL_BROWSER_OR_GIT_INSTRUCTION",
        subject="execution_boundary",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "shell_browser_git_instruction",
                    "passed": False,
                    "severity": "critical",
                    "flag": "shell_or_browser_instruction_detected",
                    "reason": "metadata text says to run a shell, open a browser, and " + "git" + " push",
                },
            )
        },
        expected_category=CriticTaxonomyCategory.BROWSER_BOUNDARY,
        expected_severity=CriticTaxonomySeverity.CRITICAL,
    ),
    _case(
        case_id="critic_adv_1a_provider_fallback_smuggling",
        title="Provider fallback capability smuggling",
        taxonomy_code="CRITIC_PROVIDER_SWITCH_OR_FALLBACK",
        subject="provider_boundary",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "fallback_or_provider_switch",
                    "passed": False,
                    "severity": "high",
                    "flag": "fallback_or_provider_switch_detected",
                    "reason": "finding asks to switch provider or call a live provider",
                },
            )
        },
        expected_category=CriticTaxonomyCategory.PROVIDER_TRUST,
        expected_severity=CriticTaxonomySeverity.HIGH,
    ),
    _case(
        case_id="critic_adv_1a_package_install_unknown_signal",
        title="Package install unknown signal",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="package_install_boundary",
        adversarial_evidence={
            "checks": (
                {
                    "check_id": "install_package_now",
                    "passed": False,
                    "severity": "critical",
                    "flag": "pip_install_request",
                    "reason": "unmapped finding text requests package installation",
                },
            )
        },
        expected_category=CriticTaxonomyCategory.UNKNOWN_OR_UNCLASSIFIED,
        expected_severity=CriticTaxonomySeverity.WARNING,
    ),
    _case(
        case_id="critic_adv_1a_malformed_checks_container",
        title="Malformed checks container",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="malformed_critic_evidence",
        adversarial_evidence={"checks": "authority_language"},
        expected_category=CriticTaxonomyCategory.SCHEMA_VALIDATION,
        expected_severity=CriticTaxonomySeverity.WARNING,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
    ),
    _case(
        case_id="critic_adv_1a_missing_finding_identity",
        title="Missing finding identity",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="malformed_critic_evidence",
        adversarial_evidence={
            "checks": (
                {
                    "passed": False,
                    "severity": "critical",
                    "reason": "finding omits both check_id and flag",
                },
            )
        },
        expected_category=CriticTaxonomyCategory.SCHEMA_VALIDATION,
        expected_severity=CriticTaxonomySeverity.WARNING,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_MALFORMED_CRITIC_EVIDENCE,),
    ),
    _case(
        case_id="critic_adv_1a_stale_taxonomy_hash",
        title="Stale taxonomy hash binding",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="stale_taxonomy_evidence",
        adversarial_evidence={
            "expected_taxonomy_hash": "0" * 64,
            "critic_report": {
                "checks": (
                    {
                        "check_id": "output_trust",
                        "passed": False,
                        "severity": "high",
                        "flag": "provider_output_untrusted",
                        "reason": "valid-looking finding with stale taxonomy binding",
                    },
                )
            },
        },
        expected_category=CriticTaxonomyCategory.SCHEMA_VALIDATION,
        expected_severity=CriticTaxonomySeverity.WARNING,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_STALE_TAXONOMY,),
    ),
    _case(
        case_id="critic_adv_1a_duplicate_taxonomy_code",
        title="Duplicate taxonomy code attack",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="duplicate_taxonomy_evidence",
        adversarial_evidence={
            "taxonomy_attack": "duplicate_code",
            "critic_report": {
                "checks": (
                    {
                        "check_id": "output_trust",
                        "passed": False,
                        "severity": "high",
                        "flag": "provider_output_untrusted",
                        "reason": "valid-looking finding with duplicate taxonomy evidence",
                    },
                )
            },
        },
        expected_category=CriticTaxonomyCategory.SCHEMA_VALIDATION,
        expected_severity=CriticTaxonomySeverity.WARNING,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_DUPLICATE_CODE,),
    ),
    _case(
        case_id="critic_adv_1a_ambiguous_taxonomy_signal",
        title="Ambiguous taxonomy signal attack",
        taxonomy_code="CRITIC_UNKNOWN_OR_UNCLASSIFIED",
        subject="ambiguous_taxonomy_evidence",
        adversarial_evidence={
            "taxonomy_attack": "ambiguous_signal",
            "critic_report": {
                "checks": (
                    {
                        "check_id": "output_trust",
                        "passed": False,
                        "severity": "high",
                        "flag": "provider_output_untrusted",
                        "reason": "valid-looking finding with ambiguous taxonomy evidence",
                    },
                )
            },
        },
        expected_category=CriticTaxonomyCategory.SCHEMA_VALIDATION,
        expected_severity=CriticTaxonomySeverity.WARNING,
        expected_fail_closed=True,
        expected_errors=(CRITIC_TAXONOMY_INVALID_AMBIGUOUS_SIGNAL,),
    ),
)
