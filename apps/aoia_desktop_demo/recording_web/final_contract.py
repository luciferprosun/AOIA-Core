"""Structured Gemma Final contract for the bounded NachwG recording preset.

The model, not HAT and not the renderer, supplies every value in this object.
Validation is deterministic and fail-closed.  The renderer only maps validated
fields to the operator-requested display format.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping, Sequence


MAXIMUM_CONTRACT_BYTES = 32 * 1024
MAXIMUM_REASONING_WORDS = 150

FINAL_ANSWER_JSON_SCHEMA: dict[str, object] = {
    "name": "aioa_nachwg_final_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "contract_status": {
                "type": "string",
                "enum": ["VALID", "INVALID", "DEPENDS"],
            },
            "document_status": {
                "type": "string",
                "enum": ["PERMITTED", "NOT_PERMITTED", "DEPENDS"],
            },
            "paper_always_required": {"type": "boolean"},
            "pdf_or_email_acceptable": {
                "type": "string",
                "enum": ["YES", "NO", "DEPENDS"],
            },
            "qes_required": {"type": "boolean"},
            "evidence_duty_separate": {"type": "boolean"},
            "maximum_fine_eur": {"type": "integer", "minimum": 0},
            "statutory_basis": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {"type": "string", "minLength": 1, "maxLength": 80},
            },
            "deadlines": {
                "type": "object",
                "properties": {
                    "day_one_items": {
                        "type": "array",
                        "maxItems": 15,
                        "items": {"type": "integer", "minimum": 1, "maximum": 15},
                    },
                    "seventh_calendar_day_items": {
                        "type": "array",
                        "maxItems": 15,
                        "items": {"type": "integer", "minimum": 1, "maximum": 15},
                    },
                    "one_month_items": {
                        "type": "array",
                        "maxItems": 15,
                        "items": {"type": "integer", "minimum": 1, "maximum": 15},
                    },
                },
                "required": [
                    "day_one_items",
                    "seventh_calendar_day_items",
                    "one_month_items",
                ],
                "additionalProperties": False,
            },
            "textform_conditions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {"type": "string", "minLength": 1, "maxLength": 240},
            },
            "reasoning": {"type": "string", "minLength": 1, "maxLength": 800},
        },
        "required": [
            "contract_status",
            "document_status",
            "paper_always_required",
            "pdf_or_email_acceptable",
            "qes_required",
            "evidence_duty_separate",
            "maximum_fine_eur",
            "statutory_basis",
            "deadlines",
            "textform_conditions",
            "reasoning",
        ],
        "additionalProperties": False,
    },
}


@dataclass(frozen=True, slots=True)
class ContractIssue:
    field: str
    code: str
    expected: object | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"field": self.field, "code": self.code}
        if self.expected is not None:
            result["expected"] = self.expected
        return result


@dataclass(frozen=True, slots=True)
class FinalAnswerContract:
    contract_status: str
    document_status: str
    paper_always_required: bool
    pdf_or_email_acceptable: str
    qes_required: bool
    evidence_duty_separate: bool
    maximum_fine_eur: int
    statutory_basis: tuple[str, ...]
    day_one_items: tuple[int, ...]
    seventh_calendar_day_items: tuple[int, ...]
    one_month_items: tuple[int, ...]
    textform_conditions: tuple[str, ...]
    reasoning: str

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_status": self.contract_status,
            "document_status": self.document_status,
            "paper_always_required": self.paper_always_required,
            "pdf_or_email_acceptable": self.pdf_or_email_acceptable,
            "qes_required": self.qes_required,
            "evidence_duty_separate": self.evidence_duty_separate,
            "maximum_fine_eur": self.maximum_fine_eur,
            "statutory_basis": list(self.statutory_basis),
            "deadlines": {
                "day_one_items": list(self.day_one_items),
                "seventh_calendar_day_items": list(
                    self.seventh_calendar_day_items
                ),
                "one_month_items": list(self.one_month_items),
            },
            "textform_conditions": list(self.textform_conditions),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True, slots=True)
class ContractValidation:
    contract: FinalAnswerContract | None
    issues: tuple[ContractIssue, ...]

    @property
    def valid(self) -> bool:
        return self.contract is not None and not self.issues


def validate_final_contract(
    raw_response: str,
    requirements: Mapping[str, object],
) -> ContractValidation:
    """Parse and validate one provider-produced final contract."""

    if not isinstance(raw_response, str) or not raw_response.strip():
        return _invalid("$", "EMPTY_RESPONSE")
    if len(raw_response.encode("utf-8")) > MAXIMUM_CONTRACT_BYTES:
        return _invalid("$", "RESPONSE_TOO_LARGE")
    try:
        raw = json.loads(raw_response)
    except json.JSONDecodeError:
        return _invalid("$", "INVALID_JSON")
    if not isinstance(raw, dict):
        return _invalid("$", "OBJECT_REQUIRED")

    issues: list[ContractIssue] = []
    allowed_fields = set(FINAL_ANSWER_JSON_SCHEMA["schema"]["required"])
    for name in sorted(set(raw) - allowed_fields):
        issues.append(ContractIssue(name, "UNEXPECTED_FIELD"))
    for name in sorted(allowed_fields - set(raw)):
        issues.append(ContractIssue(name, "REQUIRED_FIELD_MISSING"))

    contract_status = _enum(
        raw.get("contract_status"),
        "contract_status",
        {"VALID", "INVALID", "DEPENDS"},
        issues,
    )
    document_status = _enum(
        raw.get("document_status"),
        "document_status",
        {"PERMITTED", "NOT_PERMITTED", "DEPENDS"},
        issues,
    )
    pdf_or_email = _enum(
        raw.get("pdf_or_email_acceptable"),
        "pdf_or_email_acceptable",
        {"YES", "NO", "DEPENDS"},
        issues,
    )
    paper_required = _boolean(
        raw.get("paper_always_required"), "paper_always_required", issues
    )
    qes_required = _boolean(raw.get("qes_required"), "qes_required", issues)
    separate_duty = _boolean(
        raw.get("evidence_duty_separate"), "evidence_duty_separate", issues
    )
    maximum_fine = _integer(
        raw.get("maximum_fine_eur"), "maximum_fine_eur", issues
    )
    statutory_basis = _strings(
        raw.get("statutory_basis"), "statutory_basis", issues
    )
    textform_conditions = _strings(
        raw.get("textform_conditions"), "textform_conditions", issues
    )
    reasoning = raw.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        issues.append(ContractIssue("reasoning", "NON_EMPTY_STRING_REQUIRED"))
        reasoning = ""
    else:
        reasoning = reasoning.strip()
        maximum_words = requirements.get(
            "maximum_explanation_words", MAXIMUM_REASONING_WORDS
        )
        if not isinstance(maximum_words, int) or isinstance(maximum_words, bool):
            maximum_words = MAXIMUM_REASONING_WORDS
        if reasoning_word_count(reasoning) > maximum_words:
            issues.append(
                ContractIssue("reasoning", "WORD_LIMIT_EXCEEDED", maximum_words)
            )
        normalized_reasoning = _text_key(reasoning)
        if (
            re.search(r"\bhat\b", normalized_reasoning) is not None
            or any(
                marker in normalized_reasoning
                for marker in ("memory patch", "cockroachdb", "unverified draft")
            )
        ):
            issues.append(ContractIssue("reasoning", "INTERNAL_PROCESS_DISCLOSURE"))

    deadlines = raw.get("deadlines")
    if not isinstance(deadlines, dict):
        issues.append(ContractIssue("deadlines", "OBJECT_REQUIRED"))
        deadlines = {}
    allowed_deadlines = {
        "day_one_items",
        "seventh_calendar_day_items",
        "one_month_items",
    }
    for name in sorted(set(deadlines) - allowed_deadlines):
        issues.append(ContractIssue(f"deadlines.{name}", "UNEXPECTED_FIELD"))
    day_one = _integers(deadlines.get("day_one_items"), "deadlines.day_one_items", issues)
    day_seven = _integers(
        deadlines.get("seventh_calendar_day_items"),
        "deadlines.seventh_calendar_day_items",
        issues,
    )
    one_month = _integers(
        deadlines.get("one_month_items"), "deadlines.one_month_items", issues
    )

    if not issues:
        contract = FinalAnswerContract(
            contract_status=contract_status,
            document_status=document_status,
            paper_always_required=paper_required,
            pdf_or_email_acceptable=pdf_or_email,
            qes_required=qes_required,
            evidence_duty_separate=separate_duty,
            maximum_fine_eur=maximum_fine,
            statutory_basis=statutory_basis,
            day_one_items=day_one,
            seventh_calendar_day_items=day_seven,
            one_month_items=one_month,
            textform_conditions=textform_conditions,
            reasoning=reasoning,
        )
        issues.extend(_semantic_issues(contract, requirements))
    else:
        contract = None
    return ContractValidation(
        contract=contract if not issues else None,
        issues=tuple(_dedupe_issues(issues)),
    )


def render_final_contract(contract: FinalAnswerContract) -> str:
    """Pure field mapping from a validated Gemma contract to chat text."""

    if not isinstance(contract, FinalAnswerContract):
        raise TypeError("validated FinalAnswerContract is required")
    paper = "YES" if contract.paper_always_required else "NO"
    qes_not_required = "NO" if contract.qes_required else "YES"
    separate = "YES" if contract.evidence_duty_separate else "NO"
    basis = "; ".join(contract.statutory_basis)
    conditions = "; ".join(contract.textform_conditions)
    return (
        f"CONTRACT STATUS: {contract.contract_status}\n"
        f"NO EMPLOYMENT CONDITIONS DOCUMENT: {contract.document_status.replace('_', ' ')}\n"
        f"PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED: {paper}\n"
        f"CAN A PDF OR EMAIL BE SUFFICIENT: {contract.pdf_or_email_acceptable}\n\n"
        f"Reasoning:\n{contract.reasoning}\n\n"
        f"Statutory basis: {basis}\n"
        f"Separate evidence duty: {separate}\n"
        f"QES is not required for Textform: {qes_not_required}\n"
        f"Deadlines: first day items {_items(contract.day_one_items)}; "
        f"seventh calendar day items {_items(contract.seventh_calendar_day_items)}; "
        f"one month items {_items(contract.one_month_items)}.\n"
        f"Textform conditions: {conditions}.\n"
        f"Maximum fine: EUR {contract.maximum_fine_eur:,} under §4 NachwG."
    )


_FIELD_EVIDENCE_IDS: dict[str, tuple[str, ...]] = {
    "contract_status": (
        "DE-EMPLOYMENT-FORM-2021-001",
        "DE-NACHWG-DUTY-2022-001",
    ),
    "document_status": (
        "DE-NACHWG-DUTY-2022-001",
        "DE-NACHWG-DEADLINE-DAY1-2022-001",
    ),
    "paper_always_required": (
        "DE-NACHWG-TEXTFORM-2025-001",
        "DE-NACHWG-PAPER-DEMAND-2025-001",
    ),
    "pdf_or_email_acceptable": (
        "DE-NACHWG-PDF-EMAIL-2025-001",
        "DE-NACHWG-TEXTFORM-2025-001",
    ),
    "qes_required": ("DE-NACHWG-QES-2025-001",),
    "evidence_duty_separate": ("DE-NACHWG-DUTY-2022-001",),
    "maximum_fine_eur": ("DE-NACHWG-FINE-2022-001",),
    "statutory_basis": (
        "DE-EMPLOYMENT-FORM-2021-001",
        "DE-NACHWG-DUTY-2022-001",
        "DE-NACHWG-TEXTFORM-2025-001",
        "DE-NACHWG-SECTOR-EXCLUSION-2025-001",
        "DE-NACHWG-FINE-2022-001",
    ),
    "deadlines": (
        "DE-NACHWG-DEADLINE-DAY1-2022-001",
        "DE-NACHWG-DEADLINE-DAY7-2022-001",
        "DE-NACHWG-DEADLINE-MONTH-2022-001",
    ),
    "textform_conditions": (
        "DE-NACHWG-TEXTFORM-2025-001",
        "DE-NACHWG-PAPER-DEMAND-2025-001",
        "DE-NACHWG-SECTOR-EXCLUSION-2025-001",
        "DE-NACHWG-QES-2025-001",
    ),
}


def targeted_evidence_ids(issues: Sequence[ContractIssue]) -> tuple[str, ...]:
    result: list[str] = []
    for issue in issues:
        root = issue.field.split(".", 1)[0]
        for value in _FIELD_EVIDENCE_IDS.get(root, ()):
            if value not in result:
                result.append(value)
    if not result:
        for values in _FIELD_EVIDENCE_IDS.values():
            for value in values:
                if value not in result:
                    result.append(value)
    return tuple(result)


def reasoning_word_count(value: str) -> int:
    return len(re.findall(r"\b[\w€]+(?:[-’'][\w]+)*\b", value))


def _semantic_issues(
    contract: FinalAnswerContract,
    requirements: Mapping[str, object],
) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    expected_values = {
        "contract_status": _enum_key(requirements.get("contract_status")),
        "document_status": _enum_key(
            requirements.get("no_employment_conditions_document")
        ),
        "paper_always_required": _yes_no_bool(
            requirements.get("paper_with_handwritten_signature_always_required")
        ),
        "pdf_or_email_acceptable": _enum_key(
            requirements.get("can_pdf_or_email_be_sufficient")
        ),
        "qes_required": requirements.get("qes_required"),
        "evidence_duty_separate": requirements.get("evidence_duty_separate"),
        "maximum_fine_eur": requirements.get("maximum_fine_eur"),
    }
    for field, expected in expected_values.items():
        actual = getattr(contract, field)
        if expected is None or actual != expected:
            issues.append(ContractIssue(field, "EXPECTED_VALUE_MISMATCH", expected))

    required_basis = _string_sequence(requirements.get("required_statutory_basis"))
    if {_citation_key(value) for value in contract.statutory_basis} != {
        _citation_key(value) for value in required_basis
    }:
        issues.append(
            ContractIssue("statutory_basis", "EXACT_SET_REQUIRED", list(required_basis))
        )
    forbidden = _string_sequence(
        requirements.get("forbidden_as_documentation_duty_basis")
    )
    combined_basis = " ".join(contract.statutory_basis)
    for citation in forbidden:
        if _citation_key(citation) in _citation_key(combined_basis):
            issues.append(
                ContractIssue("statutory_basis", "FORBIDDEN_CITATION", citation)
            )

    raw_deadlines = requirements.get("required_deadline_groups")
    expected_deadlines = raw_deadlines if isinstance(raw_deadlines, Mapping) else {}
    deadline_checks = (
        ("day_one_items", contract.day_one_items, expected_deadlines.get("first_day")),
        (
            "seventh_calendar_day_items",
            contract.seventh_calendar_day_items,
            expected_deadlines.get("seventh_calendar_day"),
        ),
        ("one_month_items", contract.one_month_items, expected_deadlines.get("one_month")),
    )
    for field, actual, raw_expected in deadline_checks:
        expected = _integer_sequence(raw_expected)
        if actual != expected:
            issues.append(
                ContractIssue(f"deadlines.{field}", "EXACT_SET_REQUIRED", list(expected))
            )

    required_conditions = _string_sequence(
        requirements.get("required_textform_conditions")
    )
    if {_text_key(value) for value in contract.textform_conditions} != {
        _text_key(value) for value in required_conditions
    }:
        issues.append(
            ContractIssue(
                "textform_conditions",
                "EXACT_SET_REQUIRED",
                list(required_conditions),
            )
        )
    return issues


def _enum(value, field, allowed, issues) -> str:
    normalized = _enum_key(value)
    if normalized not in allowed:
        issues.append(ContractIssue(field, "ENUM_INVALID", sorted(allowed)))
        return ""
    return normalized


def _boolean(value, field, issues) -> bool:
    if not isinstance(value, bool):
        issues.append(ContractIssue(field, "BOOLEAN_REQUIRED"))
        return False
    return value


def _integer(value, field, issues) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        issues.append(ContractIssue(field, "NON_NEGATIVE_INTEGER_REQUIRED"))
        return 0
    return value


def _strings(value, field, issues) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        issues.append(ContractIssue(field, "NON_EMPTY_STRING_ARRAY_REQUIRED"))
        return ()
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            issues.append(ContractIssue(field, "NON_EMPTY_STRING_ARRAY_REQUIRED"))
            return ()
        result.append(item.strip())
    if len({_text_key(item) for item in result}) != len(result):
        issues.append(ContractIssue(field, "DUPLICATE_VALUE"))
    return tuple(result)


def _integers(value, field, issues) -> tuple[int, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, int) or isinstance(item, bool) for item in value
    ):
        issues.append(ContractIssue(field, "INTEGER_ARRAY_REQUIRED"))
        return ()
    if any(item < 1 or item > 15 for item in value):
        issues.append(ContractIssue(field, "ITEM_OUT_OF_RANGE"))
    if len(set(value)) != len(value):
        issues.append(ContractIssue(field, "DUPLICATE_VALUE"))
    return tuple(sorted(value))


def _enum_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s-]+", "_", value.strip().upper())


def _yes_no_bool(value: object) -> bool | None:
    normalized = _enum_key(value)
    if normalized == "YES":
        return True
    if normalized == "NO":
        return False
    return None


def _citation_key(value: object) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)).casefold())


def _text_key(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return " ".join(re.findall(r"[\w§€]+", normalized))


def _string_sequence(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _integer_sequence(value: object) -> tuple[int, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        return ()
    return tuple(sorted(value))


def _items(values: Sequence[int]) -> str:
    return ", ".join(str(value) for value in values)


def _invalid(field: str, code: str) -> ContractValidation:
    return ContractValidation(None, (ContractIssue(field, code),))


def _dedupe_issues(values: Sequence[ContractIssue]) -> list[ContractIssue]:
    result: list[ContractIssue] = []
    seen: set[tuple[str, str]] = set()
    for value in values:
        key = (value.field, value.code)
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result


__all__ = [
    "ContractIssue",
    "ContractValidation",
    "FINAL_ANSWER_JSON_SCHEMA",
    "FinalAnswerContract",
    "reasoning_word_count",
    "render_final_contract",
    "targeted_evidence_ids",
    "validate_final_contract",
]
