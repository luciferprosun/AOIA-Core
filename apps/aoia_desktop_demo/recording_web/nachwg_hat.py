"""Deterministic NachwG audit used between the two Gemma calls.

This module is intentionally provider- and persistence-free.  It consumes the
versioned records already retrieved from CockroachDB, audits an untrusted model
response against their machine-readable oracle metadata, and emits a bounded
correction package.  It never answers the user's question itself.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


VERDICT_PASS = "PASS"
VERDICT_CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
VERDICT_INSUFFICIENT_KNOWLEDGE = "INSUFFICIENT_KNOWLEDGE"
_DEFAULT_PACK_PATH = (
    Path(__file__).resolve().parent
    / "data"
    / "german_nachwg_hard_knowledge_2026.json"
)

_DEMO_LABELS = (
    "CONTRACT STATUS",
    "NO EMPLOYMENT CONDITIONS DOCUMENT",
    "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED",
    "CAN A PDF OR EMAIL BE SUFFICIENT",
)
_ALLOWED_LABEL_VALUES = {
    "CONTRACT STATUS": frozenset({"VALID", "INVALID"}),
    "NO EMPLOYMENT CONDITIONS DOCUMENT": frozenset(
        {"PERMITTED", "NOT PERMITTED"}
    ),
    "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED": frozenset(
        {"YES", "NO"}
    ),
    "CAN A PDF OR EMAIL BE SUFFICIENT": frozenset({"YES", "NO", "DEPENDS"}),
}

# These are semantic recognizers, not answer text.  Pack-provided
# ``required_concepts`` metadata takes precedence.  The fallback keeps an
# atomic canonical record auditable even when an older projection omitted the
# optional recognizer metadata.
_FALLBACK_REQUIRED_CONCEPTS: dict[
    str, tuple[tuple[str, tuple[str, ...]], ...]
] = {
    "DE-EMPLOYMENT-FORM-2021-001": (
        ("ordinary contract validity", ("contract status valid", "generally valid", "contract is valid", "vertrag ist wirksam", "arbeitsvertrag ist gültig")),
        ("§105 GewO", ("§105 gewo", "section 105 gewo", "§ 105 gewo")),
        ("§611a BGB", ("§611a bgb", "section 611a bgb", "§ 611a bgb")),
    ),
    "DE-NACHWG-DUTY-2022-001": (
        ("separate evidence duty", ("separate evidence duty", "separate documentation duty", "separate duty", "nachweispflicht", "documentation obligation")),
    ),
    "DE-NACHWG-TEXTFORM-2025-001": (
        ("Textform", ("textform", "text form")),
        ("§126b BGB", ("§126b bgb", "section 126b bgb", "§ 126b bgb")),
        ("accessible", ("accessible", "can be accessed", "made available", "zugänglich")),
        ("storable", ("storable", "can be stored", "stored", "saved", "speicherbar")),
        ("printable", ("printable", "can be printed", "printed", "ausdruckbar")),
        ("receipt confirmation requested", ("receipt confirmation", "confirmation of receipt", "acknowledgement of receipt", "proof of receipt", "receipt proof", "empfangsbestätigung")),
    ),
    "DE-NACHWG-PAPER-DEMAND-2025-001": (
        ("employee demand", ("employee may demand", "employee can demand", "employee may request", "right to demand", "right to request", "on employee request", "arbeitnehmer kann verlangen")),
        ("written or signed record", ("written record", "signed record", "paper record", "paper version", "handwritten signature", "schriftliche niederschrift")),
    ),
    "DE-NACHWG-SECTOR-EXCLUSION-2025-001": (
        ("§2a SchwarzArbG sector", ("§2a schwarzarbg", "§ 2a schwarzarbg", "section 2a schwarzarbg", "schwarzarbg sector")),
        ("Textform exclusion", ("textform is unavailable", "text form is unavailable", "excluded from textform", "sector exclusion", "does not apply to", "not available for", "except for", "unless the employee", "unless in")),
    ),
    "DE-NACHWG-PDF-EMAIL-2025-001": (
        ("PDF or email", ("pdf or email", "pdf/email", "pdf", "email")),
        ("conditional sufficiency", ("depends", "can be sufficient if", "may be sufficient if", "only if", "provided that", "subject to")),
    ),
    "DE-NACHWG-QES-2025-001": (
        ("QES not required", ("qualified electronic signature is not required", "qes is not required", "qes not required", "no qualified electronic signature", "no qes", "without qes")),
    ),
    "DE-NACHWG-DEADLINE-DAY1-2022-001": (
        ("day-one deadline", ("first day of work", "day one", "day-one", "on the first day", "ersten arbeitstag")),
    ),
    "DE-NACHWG-DEADLINE-DAY7-2022-001": (
        ("seven-day deadline", ("seventh calendar day", "seven days", "7 days", "day seven", "day-seven", "siebten kalendertag")),
    ),
    "DE-NACHWG-DEADLINE-MONTH-2022-001": (
        ("one-month deadline", ("one month", "within a month", "month after", "einen monat")),
    ),
    "DE-NACHWG-FINE-2022-001": (
        ("administrative fine", ("fine", "administrative offence", "administrative offense", "bußgeld", "geldbuße")),
        ("EUR 2,000 ceiling", ("eur 2 000", "eur 2000", "€2 000", "€2000", "2 000 euro", "2000 euro")),
        ("§4 NachwG", ("§4 nachwg", "§ 4 nachwg", "section 4 nachwg")),
    ),
}

_LABEL_TOPIC_MARKERS = {
    "CONTRACT STATUS": ("validity/form", "contract validity", "employment contract"),
    "NO EMPLOYMENT CONDITIONS DOCUMENT": ("separate evidence duty", "evidence duty"),
    "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED": (
        "electronic textform",
        "written/signed record",
        "paper demand",
    ),
    "CAN A PDF OR EMAIL BE SUFFICIENT": ("pdf/email", "textform route"),
}
_CLAIM_ID_TO_LABEL = {
    "CONTRACT_VALIDITY": "CONTRACT STATUS",
    "MISSING_DOCUMENT_COMPLIANCE": "NO EMPLOYMENT CONDITIONS DOCUMENT",
    "HANDWRITTEN_SIGNATURE_ALWAYS_REQUIRED": "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED",
    "PDF_OR_EMAIL_SUFFICIENCY": "CAN A PDF OR EMAIL BE SUFFICIENT",
}
_ORACLE_KEY_ALIASES = {
    "CONTRACT STATUS": "CONTRACT STATUS",
    "NO EMPLOYMENT CONDITIONS DOCUMENT": "NO EMPLOYMENT CONDITIONS DOCUMENT",
    "PAPER WITH HANDWRITTEN SIGNATURE ALWAYS REQUIRED": "PAPER WITH A HANDWRITTEN SIGNATURE ALWAYS REQUIRED",
    "CAN PDF OR EMAIL BE SUFFICIENT": "CAN A PDF OR EMAIL BE SUFFICIENT",
}


@dataclass(frozen=True, slots=True)
class HatAuditResult:
    """Structured, JSON-projectable result of a deterministic HAT audit."""

    verdict: str
    claims: tuple[dict[str, object], ...]
    corrections: tuple[dict[str, object], ...]
    missing_information: tuple[str, ...]
    temporal_context: dict[str, object]
    finalization_instructions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    knowledge_scope: str = "German Law / NachwG"

    def as_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "claims": [dict(value) for value in self.claims],
            "corrections": [dict(value) for value in self.corrections],
            "missing_information": list(self.missing_information),
            "temporal_context": dict(self.temporal_context),
            "finalization_instructions": list(self.finalization_instructions),
            "evidence_ids": list(self.evidence_ids),
            "knowledge_scope": self.knowledge_scope,
        }


@dataclass(frozen=True, slots=True)
class _Record:
    knowledge_id: str
    topic: str
    rule: str
    statutory_basis: str
    valid_from: date | None
    valid_to: date | None
    status: str
    metadata: dict[str, object]
    source_references: tuple[str, ...]

    def applies_on(self, as_of: date) -> bool:
        if self.valid_from is not None and self.valid_from > as_of:
            return False
        return self.valid_to is None or as_of <= self.valid_to


@dataclass(frozen=True, slots=True)
class _OracleExpectation:
    label: str
    expected_value: str
    knowledge_ids: tuple[str, ...]


def load_pack(
    source: str | Path | Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Load and validate a local JSON hard-knowledge pack.

    ``source`` may also be an already-decoded mapping, which is useful for
    tests and for callers that verify a source fingerprint before parsing.
    No database, network, or provider operation is performed here.
    """

    if source is None:
        source = _DEFAULT_PACK_PATH
    if isinstance(source, Mapping):
        return validate_pack(source)
    path = Path(source).expanduser()
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("NACHWG_PACK_UNAVAILABLE") from error
    if len(raw.encode("utf-8")) > 8 * 1024 * 1024:
        raise ValueError("NACHWG_PACK_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("NACHWG_PACK_INVALID_JSON") from error
    return validate_pack(payload)


def validate_pack(raw_pack: Mapping[str, object]) -> dict[str, object]:
    """Validate the atomic, temporal pack and return a plain normalized copy."""

    if not isinstance(raw_pack, Mapping):
        raise ValueError("NACHWG_PACK_INVALID")
    raw_records = _first(raw_pack, "records", "knowledge_records", "hard_knowledge_records")
    if not _is_sequence(raw_records) or not raw_records:
        raise ValueError("NACHWG_PACK_RECORDS_INVALID")

    normalized_records: list[dict[str, object]] = []
    identifiers: set[str] = set()
    for raw_record in raw_records:
        if not isinstance(raw_record, Mapping):
            raise ValueError("NACHWG_PACK_RECORD_INVALID")
        record = dict(raw_record)
        knowledge_id = _required_text(record, "knowledge_id")
        if knowledge_id in identifiers:
            raise ValueError("NACHWG_PACK_DUPLICATE_ID")
        identifiers.add(knowledge_id)
        _required_text(record, "topic")
        jurisdiction = _required_text(record, "jurisdiction").casefold()
        if jurisdiction not in {"de", "germany", "deutschland"}:
            raise ValueError("NACHWG_PACK_JURISDICTION_INVALID")
        valid_from = _parse_date(_first(record, "valid_from", "effective_from"), required=True)
        valid_to = _parse_date(_first(record, "valid_to", "effective_to"), current_allowed=True)
        status = _required_text(record, "status").upper()
        if status not in {"CURRENT", "SUPERSEDED"}:
            raise ValueError("NACHWG_PACK_STATUS_INVALID")
        if valid_to is not None and valid_from > valid_to:
            raise ValueError("NACHWG_PACK_TEMPORAL_INTERVAL_INVALID")
        if status == "SUPERSEDED" and valid_to is None:
            raise ValueError("NACHWG_PACK_SUPERSEDED_INTERVAL_OPEN")
        _required_text(record, "rule")
        statutory_basis = _first(record, "statutory_basis", "legal_basis")
        if not _text(statutory_basis) and not _string_tuple(statutory_basis):
            raise ValueError("NACHWG_PACK_FIELD_MISSING")
        _required_text(record, "confidence")
        source_urls = _first(record, "source_urls", "sources")
        if not _is_sequence(source_urls) or not all(
            isinstance(value, str) and value.strip() for value in source_urls
        ):
            raise ValueError("NACHWG_PACK_PROVENANCE_INVALID")
        fingerprint = _first(record, "source_fingerprint", "source_sha256")
        if fingerprint is not None and not _is_sha256(fingerprint):
            raise ValueError("NACHWG_PACK_FINGERPRINT_INVALID")
        normalized_records.append(record)

    statuses = tuple(str(value["status"]).upper() for value in normalized_records)
    if (
        len(normalized_records) != 36
        or statuses.count("CURRENT") != 31
        or statuses.count("SUPERSEDED") != 5
    ):
        raise ValueError("NACHWG_PACK_ATOMIC_COUNT_INVALID")
    source_package = raw_pack.get("source_package")
    package_fingerprint = (
        source_package.get("pdf_sha256")
        if isinstance(source_package, Mapping)
        else None
    )
    record_fingerprints = {
        str(value.get("source_fingerprint")) for value in normalized_records
    }
    if (
        not _is_sha256(package_fingerprint)
        or record_fingerprints != {package_fingerprint}
    ):
        raise ValueError("NACHWG_PACK_FINGERPRINT_MISMATCH")

    scenario = _first(raw_pack, "demo_scenario", "recording_scenario")
    audit = raw_pack.get("audit")
    if not isinstance(scenario, Mapping) and isinstance(audit, Mapping):
        raw_audit_scenario = audit.get("scenario")
        raw_audit_oracle = audit.get("oracle")
        if isinstance(raw_audit_scenario, Mapping) and isinstance(raw_audit_oracle, Mapping):
            scenario = {
                **raw_audit_scenario,
                "oracle": raw_audit_oracle,
                "required_knowledge_ids": raw_audit_oracle.get(
                    "required_record_ids", ()
                ),
                "claim_checks": audit.get("claim_checks", ()),
            }
    if not isinstance(scenario, Mapping):
        raise ValueError("NACHWG_PACK_DEMO_SCENARIO_INVALID")
    scenario_copy = dict(scenario)
    _parse_date(_first(scenario_copy, "scenario_date", "as_of"), required=True)
    oracle = _parse_oracle(_first(scenario_copy, "oracle", "expected_output"))
    if set(oracle) != set(_DEMO_LABELS):
        raise ValueError("NACHWG_PACK_ORACLE_INCOMPLETE")
    raw_scenario_oracle = _mapping(scenario_copy.get("oracle"))
    required_ids = _string_tuple(
        _first(
            scenario_copy,
            "required_knowledge_ids",
            "required_evidence_ids",
            "required_record_ids",
        )
    ) or _string_tuple(raw_scenario_oracle.get("required_record_ids"))
    if not required_ids or not set(required_ids).issubset(identifiers):
        raise ValueError("NACHWG_PACK_REQUIRED_EVIDENCE_INVALID")

    result = dict(raw_pack)
    result["records"] = normalized_records
    result["demo_scenario"] = scenario_copy
    return result


def audit_response(
    primary_response: str,
    evidence: object,
    scenario_date: str | date | datetime,
    original_user_prompt: str,
) -> HatAuditResult:
    """Audit Gemma's actual primary response against retrieved evidence only."""

    return _audit_response(
        primary_response=primary_response,
        evidence=evidence,
        scenario_date=scenario_date,
        original_user_prompt=original_user_prompt,
        require_scope=True,
    )


def postcheck_final(
    final_response: str,
    original_audit: HatAuditResult | Mapping[str, object],
    evidence: object,
) -> bool:
    """Fail closed unless the final response satisfies the same evidence oracle."""

    if not isinstance(final_response, str) or not final_response.strip():
        return False
    if _explanation_word_count(final_response) > _maximum_explanation_words():
        return False
    verdict = _audit_value(original_audit, "verdict")
    if verdict == VERDICT_INSUFFICIENT_KNOWLEDGE:
        return _states_uncertainty(final_response)
    temporal = _audit_value(original_audit, "temporal_context")
    if not isinstance(temporal, Mapping):
        return False
    scenario_date = temporal.get("scenario_date")
    if scenario_date is None:
        return False
    try:
        check = _audit_response(
            primary_response=final_response,
            evidence=evidence,
            scenario_date=scenario_date,
            original_user_prompt="",
            require_scope=False,
        )
    except (TypeError, ValueError):
        return False
    return check.verdict == VERDICT_PASS


def _maximum_explanation_words() -> int:
    try:
        scenario = load_pack().get("demo_scenario")
    except ValueError:
        return 150
    oracle = scenario.get("oracle") if isinstance(scenario, Mapping) else None
    value = oracle.get("maximum_explanation_words") if isinstance(oracle, Mapping) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 150


def _explanation_word_count(response: str) -> int:
    explanation_lines = []
    for raw_line in response.splitlines():
        line = raw_line.strip().replace("**", "").replace("__", "")
        normalized = re.sub(r"^[#>*\-+\s]+", "", line).strip()
        if any(
            re.match(re.escape(label) + r"\s*:", normalized, re.IGNORECASE)
            for label in _DEMO_LABELS
        ):
            continue
        explanation_lines.append(normalized)
    return len(re.findall(r"\b[\w§€]+(?:[-’'][\w]+)*\b", " ".join(explanation_lines)))


def _audit_response(
    *,
    primary_response: str,
    evidence: object,
    scenario_date: str | date | datetime,
    original_user_prompt: str,
    require_scope: bool,
) -> HatAuditResult:
    if not isinstance(primary_response, str) or not primary_response.strip():
        raise ValueError("HAT_PRIMARY_RESPONSE_INVALID")
    if not isinstance(original_user_prompt, str):
        raise ValueError("HAT_ORIGINAL_PROMPT_INVALID")
    as_of = _parse_date(scenario_date, required=True)
    raw_records, scenario = _evidence_parts(evidence)
    if not scenario:
        try:
            default_pack = load_pack()
        except ValueError:
            default_pack = {}
        default_scenario = default_pack.get("demo_scenario")
        if isinstance(default_scenario, Mapping):
            scenario = default_scenario
    parsed: list[_Record] = []
    malformed_count = 0
    for value in raw_records:
        try:
            parsed.append(_record_from_evidence(value))
        except (TypeError, ValueError):
            malformed_count += 1

    applicable = tuple(record for record in parsed if record.applies_on(as_of))
    excluded = tuple(record for record in parsed if not record.applies_on(as_of))
    evidence_ids = tuple(sorted({record.knowledge_id for record in applicable}))
    temporal_context: dict[str, object] = {
        "scenario_date": as_of.isoformat(),
        "applicable_version": "as_of",
        "applicable_knowledge_ids": list(evidence_ids),
        "excluded_knowledge_ids": sorted({record.knowledge_id for record in excluded}),
    }
    missing_information: list[str] = []
    if malformed_count:
        missing_information.append(
            f"{malformed_count} retrieved evidence record(s) had invalid audit metadata."
        )

    if require_scope and not _is_nachwg_scope(
        original_user_prompt, primary_response, applicable
    ):
        return _result(
            verdict=VERDICT_INSUFFICIENT_KNOWLEDGE,
            claims=(),
            corrections=(),
            missing_information=(
                "The prompt and primary response are outside the retrieved NachwG scope.",
            ),
            temporal_context=temporal_context,
            evidence_ids=evidence_ids,
        )
    if not applicable:
        return _result(
            verdict=VERDICT_INSUFFICIENT_KNOWLEDGE,
            claims=(),
            corrections=(),
            missing_information=(
                "No temporally applicable authoritative evidence was supplied.",
            ),
            temporal_context=temporal_context,
            evidence_ids=(),
        )

    oracle = _oracle_from_evidence(evidence, scenario, applicable)
    required_ids = _required_ids_from_evidence(scenario, applicable)
    missing_ids = tuple(sorted(set(required_ids) - set(evidence_ids)))
    if missing_ids:
        missing_information.append(
            "Required authoritative records were not retrieved: " + ", ".join(missing_ids)
        )
    temporally_unknown = tuple(
        record.knowledge_id
        for record in applicable
        if record.knowledge_id in required_ids and record.valid_from is None
    )
    if temporally_unknown:
        missing_information.append(
            "Required records lack valid_from metadata: "
            + ", ".join(sorted(temporally_unknown))
        )
    if set(oracle) != set(_DEMO_LABELS):
        missing_information.append(
            "The four-label recording oracle was not present in retrieved metadata."
        )

    if missing_information:
        return _result(
            verdict=VERDICT_INSUFFICIENT_KNOWLEDGE,
            claims=(),
            corrections=(),
            missing_information=tuple(missing_information),
            temporal_context=temporal_context,
            evidence_ids=evidence_ids,
        )

    claims: list[dict[str, object]] = []
    corrections: list[dict[str, object]] = []
    observed_labels = _extract_label_values(primary_response)
    records_by_id = {record.knowledge_id: record for record in applicable}

    for label in _DEMO_LABELS:
        expectation = oracle[label]
        observed = observed_labels.get(label)
        supporting = _supporting_records(expectation, label, applicable)
        source_ids = tuple(record.knowledge_id for record in supporting)
        authoritative_rule = " ".join(record.rule for record in supporting)
        if observed == expectation.expected_value:
            claims.append(
                _claim(
                    claim=f"{label}: {observed}",
                    status="CORRECT",
                    reason="The required label value matches the retrieved oracle.",
                    authoritative_rule=authoritative_rule,
                    source_ids=source_ids,
                )
            )
            continue
        status = "OMITTED" if observed is None else "INCORRECT"
        reason = (
            "The required label is missing."
            if observed is None
            else f"Observed {observed}; authoritative value is {expectation.expected_value}."
        )
        claims.append(
            _claim(
                claim=f"{label}: {observed or 'MISSING'}",
                status=status,
                reason=reason,
                authoritative_rule=authoritative_rule,
                source_ids=source_ids,
            )
        )
        corrections.append(
            _correction(
                exact_point=label,
                corrected_proposition=f"{label}: {expectation.expected_value}",
                records=supporting,
            )
        )

    for citation, guardrail_id in (
        ("§630 BGB", "DE-BGB-630-IRRELEVANT-001"),
        ("§630a BGB", "DE-BGB-630A-IRRELEVANT-001"),
    ):
        guardrail = records_by_id.get(guardrail_id)
        if guardrail is None or not _citation_used_as_authority(primary_response, citation):
            continue
        claims.append(
            _claim(
                claim=f"Use of {citation} as the initial evidence-duty basis",
                status="INCORRECT",
                reason="The retrieved guardrail identifies this citation as irrelevant to the initial NachwG duty.",
                authoritative_rule=guardrail.rule,
                source_ids=(guardrail.knowledge_id,),
            )
        )
        corrections.append(
            _correction(
                exact_point=f"Remove {citation} as the statutory basis",
                corrected_proposition=guardrail.rule,
                records=(guardrail,),
            )
        )

    duty_record = records_by_id.get("DE-NACHWG-DUTY-2022-001")
    if duty_record is not None and not _mentions_section_2_nachwg(primary_response):
        claims.append(
            _claim(
                claim="Statutory basis for the employment-conditions evidence duty",
                status="OMITTED",
                reason="The response does not identify §2 NachwG.",
                authoritative_rule=duty_record.rule,
                source_ids=(duty_record.knowledge_id,),
            )
        )
        corrections.append(
            _correction(
                exact_point="Identify §2 NachwG as the controlling evidence statute",
                corrected_proposition=duty_record.rule,
                records=(duty_record,),
            )
        )

    audit_ids = set(required_ids) if required_ids else set(evidence_ids)
    normalized_response = _normalize(primary_response)
    for record in applicable:
        if record.knowledge_id not in audit_ids:
            continue
        groups = _required_concepts(record)
        if not groups:
            continue
        absent = tuple(
            name
            for name, alternatives in groups
            if not _contains_any(normalized_response, alternatives)
        )
        if not absent:
            continue
        claims.append(
            _claim(
                claim=record.topic,
                status="OMITTED",
                reason="Missing material concept(s): " + ", ".join(absent) + ".",
                authoritative_rule=record.rule,
                source_ids=(record.knowledge_id,),
            )
        )
        corrections.append(
            _correction(
                exact_point="Add the omitted verified point: " + record.topic,
                corrected_proposition=record.rule,
                records=(record,),
            )
        )

    claims = _dedupe_dicts(claims, ("claim", "status"))
    corrections = _dedupe_dicts(corrections, ("exact_point", "knowledge_ids"))
    verdict = VERDICT_CORRECTION_REQUIRED if corrections else VERDICT_PASS
    return _result(
        verdict=verdict,
        claims=tuple(claims),
        corrections=tuple(corrections),
        missing_information=(),
        temporal_context=temporal_context,
        evidence_ids=evidence_ids,
    )


def _result(
    *,
    verdict: str,
    claims: tuple[dict[str, object], ...],
    corrections: tuple[dict[str, object], ...],
    missing_information: tuple[str, ...],
    temporal_context: dict[str, object],
    evidence_ids: tuple[str, ...],
) -> HatAuditResult:
    if verdict == VERDICT_INSUFFICIENT_KNOWLEDGE:
        instructions = (
            "Preserve the original requested format where possible.",
            "State that the supplied authoritative knowledge is insufficient; do not manufacture authority.",
            "Do not mention internal HAT or Memory Patch machinery.",
        )
    elif verdict == VERDICT_CORRECTION_REQUIRED:
        instructions = (
            "Revise the primary response rather than answering a different question.",
            "Keep the original user's requested format and apply every verified correction.",
            "Use only the supplied authoritative records for corrected legal propositions.",
            "Do not mention internal HAT or Memory Patch machinery.",
        )
    else:
        instructions = (
            "No factual correction is required.",
            "Return the answer in the original requested format without introducing new claims.",
            "Do not mention internal HAT or Memory Patch machinery.",
        )
    return HatAuditResult(
        verdict=verdict,
        claims=claims,
        corrections=corrections,
        missing_information=missing_information,
        temporal_context=temporal_context,
        finalization_instructions=instructions,
        evidence_ids=evidence_ids,
    )


def _evidence_parts(evidence: object) -> tuple[list[object], Mapping[str, object]]:
    if isinstance(evidence, Mapping):
        raw_records = _first(evidence, "records", "knowledge_records", "hard_knowledge_records")
        if _is_sequence(raw_records):
            scenario = _first(evidence, "demo_scenario", "recording_scenario")
            return list(raw_records), scenario if isinstance(scenario, Mapping) else {}
        return [evidence], {}
    if _is_sequence(evidence):
        return list(evidence), {}
    raise TypeError("HAT_EVIDENCE_INVALID")


def _record_from_evidence(value: object) -> _Record:
    if isinstance(value, Mapping):
        direct: Mapping[str, object] = value
    else:
        projected: dict[str, object] = {}
        nested_metadata = getattr(value, "metadata", None)
        if isinstance(nested_metadata, Mapping):
            projected["metadata"] = nested_metadata
        for key in (
            "knowledge_id",
            "topic",
            "statutory_basis",
            "excerpt",
            "source_reference",
            "source_id",
            "official_identifier",
            "provision",
        ):
            attribute = getattr(value, key, None)
            if attribute is not None:
                projected[key] = attribute
        as_dict = getattr(value, "as_dict", None)
        plain = as_dict() if callable(as_dict) else vars(value) if hasattr(value, "__dict__") else {}
        if isinstance(plain, Mapping):
            for key, item in plain.items():
                projected.setdefault(key, item)
        direct = projected
    metadata: dict[str, object] = {}
    for key in ("metadata", "structured_metadata"):
        nested = direct.get(key)
        if isinstance(nested, Mapping):
            metadata.update(nested)
    metadata.update({key: raw for key, raw in direct.items() if key not in {"metadata", "structured_metadata"}})

    knowledge_id = _text(_first(metadata, "knowledge_id", "item_id", "record_id", "source_id"))
    topic = _text(_first(metadata, "topic", "subject"))
    rule = _text(_first(metadata, "rule", "excerpt", "content", "text"))
    raw_basis = _first(metadata, "statutory_basis", "provision", "legal_basis")
    statutory_basis = _joined_text(raw_basis)
    if not knowledge_id or not topic or not rule:
        raise ValueError("HAT_EVIDENCE_RECORD_INVALID")
    valid_from_raw = _first(metadata, "valid_from", "effective_from")
    valid_to_raw = _first(metadata, "valid_to", "effective_to")
    valid_from = _parse_date(valid_from_raw) if valid_from_raw is not None else None
    valid_to = _parse_date(valid_to_raw, current_allowed=True) if valid_to_raw is not None else None
    status = _text(_first(metadata, "status", "temporal_status")).upper() or "CURRENT"
    references = _source_references(metadata)
    return _Record(
        knowledge_id=knowledge_id,
        topic=topic,
        rule=rule,
        statutory_basis=statutory_basis,
        valid_from=valid_from,
        valid_to=valid_to,
        status=status,
        metadata=metadata,
        source_references=references,
    )


def _oracle_from_evidence(
    evidence: object,
    scenario: Mapping[str, object],
    records: Sequence[_Record],
) -> dict[str, _OracleExpectation]:
    raw_values: list[object] = []
    for key in ("oracle", "expected_output"):
        if key in scenario:
            raw_values.append(scenario[key])
    if isinstance(evidence, Mapping):
        for key in ("oracle", "demo_oracle", "oracle_assertions"):
            if key in evidence:
                raw_values.append(evidence[key])
    for record in records:
        for container in (record.metadata, _mapping(record.metadata.get("audit"))):
            for key in ("oracle", "demo_oracle", "oracle_assertions", "expected_output"):
                if key in container:
                    raw_values.append(container[key])
        label = _first(record.metadata, "oracle_label", "output_label")
        expected = _first(record.metadata, "oracle_value", "expected_value")
        if label is not None and expected is not None:
            raw_values.append(
                {
                    "label": label,
                    "expected_value": expected,
                    "knowledge_ids": [record.knowledge_id],
                }
            )

    result: dict[str, _OracleExpectation] = {}
    for raw in raw_values:
        for expectation in _parse_oracle(raw).values():
            previous = result.get(expectation.label)
            if previous is not None and previous.expected_value != expectation.expected_value:
                return {}
            ids = tuple(dict.fromkeys((*((previous.knowledge_ids) if previous else ()), *expectation.knowledge_ids)))
            result[expectation.label] = _OracleExpectation(
                expectation.label, expectation.expected_value, ids
            )
    raw_checks = scenario.get("claim_checks")
    if _is_sequence(raw_checks):
        for raw_check in raw_checks:
            if not isinstance(raw_check, Mapping):
                continue
            label = _CLAIM_ID_TO_LABEL.get(_text(raw_check.get("claim_id")).upper())
            previous = result.get(label) if label is not None else None
            if previous is None:
                continue
            ids = tuple(
                dict.fromkeys(
                    (*previous.knowledge_ids, *_string_tuple(raw_check.get("record_ids")))
                )
            )
            result[label] = _OracleExpectation(
                previous.label, previous.expected_value, ids
            )
    return result


def _parse_oracle(raw: object) -> dict[str, _OracleExpectation]:
    if raw is None:
        return {}
    entries: list[tuple[object, object, object]] = []
    if isinstance(raw, Mapping):
        if "label" in raw and ("expected_value" in raw or "expected" in raw or "value" in raw):
            entries.append(
                (
                    raw.get("label"),
                    _first(raw, "expected_value", "expected", "value"),
                    _first(raw, "knowledge_ids", "evidence_ids", "required_knowledge_ids"),
                )
            )
        else:
            for label, value in raw.items():
                if isinstance(value, Mapping):
                    entries.append(
                        (
                            label,
                            _first(value, "expected_value", "expected", "value"),
                            _first(value, "knowledge_ids", "evidence_ids", "required_knowledge_ids"),
                        )
                    )
                else:
                    entries.append((label, value, ()))
    elif _is_sequence(raw):
        for value in raw:
            if not isinstance(value, Mapping):
                continue
            entries.append(
                (
                    value.get("label"),
                    _first(value, "expected_value", "expected", "value"),
                    _first(value, "knowledge_ids", "evidence_ids", "required_knowledge_ids"),
                )
            )

    result: dict[str, _OracleExpectation] = {}
    for raw_label, raw_expected, raw_ids in entries:
        label = _normalize_label(raw_label)
        expected = _normalize_label_value(raw_expected)
        if label not in _ALLOWED_LABEL_VALUES or expected not in _ALLOWED_LABEL_VALUES[label]:
            continue
        result[label] = _OracleExpectation(label, expected, _string_tuple(raw_ids))
    return result


def _required_ids_from_evidence(
    scenario: Mapping[str, object], records: Sequence[_Record]
) -> tuple[str, ...]:
    scenario_oracle = _mapping(scenario.get("oracle"))
    result = list(
        _string_tuple(
            _first(
                scenario,
                "required_knowledge_ids",
                "required_evidence_ids",
                "required_record_ids",
            )
        )
        or _string_tuple(scenario_oracle.get("required_record_ids"))
    )
    raw_checks = scenario.get("claim_checks")
    if _is_sequence(raw_checks):
        for raw_check in raw_checks:
            if isinstance(raw_check, Mapping) and raw_check.get("required_for_scenario") is True:
                result.extend(_string_tuple(raw_check.get("record_ids")))
    for record in records:
        if record.metadata.get("required_for_demo") is True or record.metadata.get("required_for_audit") is True:
            result.append(record.knowledge_id)
        result.extend(
            _string_tuple(
                _first(record.metadata, "required_knowledge_ids", "required_evidence_ids")
            )
        )
    if not result:
        result.extend(
            record.knowledge_id
            for record in records
            if record.knowledge_id in _FALLBACK_REQUIRED_CONCEPTS
            or record.knowledge_id.startswith("DE-BGB-630")
        )
    return tuple(dict.fromkeys(result))


def _supporting_records(
    expectation: _OracleExpectation,
    label: str,
    records: Sequence[_Record],
) -> tuple[_Record, ...]:
    by_id = {record.knowledge_id: record for record in records}
    selected = tuple(
        by_id[value] for value in expectation.knowledge_ids if value in by_id
    )
    if selected:
        return selected
    markers = _LABEL_TOPIC_MARKERS[label]
    selected = tuple(
        record
        for record in records
        if any(marker in record.topic.casefold() for marker in markers)
    )
    return selected[:3]


def _required_concepts(
    record: _Record,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    for container in (record.metadata, _mapping(record.metadata.get("audit"))):
        raw = _first(container, "required_concepts", "required_terms", "audit_terms")
        parsed = _parse_concepts(raw)
        if parsed:
            return parsed
    return _FALLBACK_REQUIRED_CONCEPTS.get(record.knowledge_id, ())


def _parse_concepts(raw: object) -> tuple[tuple[str, tuple[str, ...]], ...]:
    result: list[tuple[str, tuple[str, ...]]] = []
    if isinstance(raw, Mapping):
        for name, alternatives in raw.items():
            values = _string_tuple(alternatives) or ((_text(alternatives),) if _text(alternatives) else ())
            if values:
                result.append((_text(name), values))
    elif _is_sequence(raw):
        for value in raw:
            if isinstance(value, Mapping):
                name = _text(_first(value, "name", "concept", "id"))
                alternatives = _string_tuple(_first(value, "any_of", "terms", "alternatives"))
                if name and alternatives:
                    result.append((name, alternatives))
            elif isinstance(value, str) and value.strip():
                result.append((value.strip(), (value.strip(),)))
    return tuple(result)


def _extract_label_values(response: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in response.splitlines():
        line = raw_line.strip().replace("**", "").replace("__", "")
        line = re.sub(r"^[#>*\-+\s]+", "", line).strip()
        for label in _DEMO_LABELS:
            match = re.match(re.escape(label) + r"\s*:\s*(.+)$", line, re.IGNORECASE)
            if match is None:
                continue
            raw_value = _normalize_label_value(match.group(1))
            allowed = sorted(_ALLOWED_LABEL_VALUES[label], key=len, reverse=True)
            for candidate in allowed:
                if raw_value == candidate or raw_value.startswith(candidate + " "):
                    result[label] = candidate
                    break
            break
    return result


def _citation_used_as_authority(response: str, citation: str) -> bool:
    suffix = "630a" if "630a" in citation.casefold() else "630"
    if suffix == "630a":
        pattern = re.compile(
            r"(?:§\s*630a|section\s+630a|bgb\s*§?\s*630a|630a\s+bgb)\b",
            re.IGNORECASE,
        )
    else:
        pattern = re.compile(
            r"(?:§\s*630(?!a)|section\s+630(?!a)|bgb\s*§?\s*630(?!a)|630(?!a)\s+bgb)\b",
            re.IGNORECASE,
        )
    for match in pattern.finditer(response):
        window = response[max(0, match.start() - 90) : min(len(response), match.end() + 120)]
        normalized = _normalize(window)
        rejection_markers = (
            "not the basis",
            "not a basis",
            "not relevant",
            "irrelevant",
            "incorrect",
            "wrong citation",
            "does not govern",
            "does not apply",
            "nicht einschlägig",
            "nicht die grundlage",
            "unmaßgeblich",
            "błędna podstawa",
            "nie stanowi podstawy",
        )
        if not any(marker in normalized for marker in rejection_markers):
            return True
    return False


def _mentions_section_2_nachwg(response: str) -> bool:
    compact = unicodedata.normalize("NFKC", response).casefold()
    forward = re.compile(
        r"(?:§|section\s+)\s*2(?!a)(?:\s*\([^)]*\))?(?:\s*(?:sentences?|satz)\s*[\d-]+)?\s*(?:of\s+the\s+)?(?:nachwg|nachweisgesetz)"
    )
    reverse = re.compile(
        r"(?:nachwg|nachweisgesetz).{0,80}(?:§|section\s+)\s*2(?!a)"
    )
    return forward.search(compact) is not None or reverse.search(compact) is not None


def _is_nachwg_scope(
    prompt: str, response: str, records: Sequence[_Record]
) -> bool:
    if not any(
        "nachwg" in record.knowledge_id.casefold()
        or "employment" in record.topic.casefold()
        or "arbeits" in record.topic.casefold()
        for record in records
    ):
        return False
    text = _normalize(prompt + "\n" + response)
    if "nachwg" in text or "nachweisgesetz" in text or "nachweispflicht" in text:
        return True
    employment = any(
        marker in text
        for marker in ("employment", "employee", "employer", "arbeitsvertrag", "arbeitnehmer", "arbeitgeber")
    )
    documentation = any(
        marker in text
        for marker in ("employment condition", "contract term", "document", "written contract", "textform", "schriftform", "nachweis")
    )
    return employment and documentation


def _claim(
    *,
    claim: str,
    status: str,
    reason: str,
    authoritative_rule: str,
    source_ids: Sequence[str],
) -> dict[str, object]:
    return {
        "claim": claim,
        "status": status,
        "reason": reason,
        "authoritative_rule": authoritative_rule,
        "source_ids": list(dict.fromkeys(source_ids)),
    }


def _correction(
    *, exact_point: str, corrected_proposition: str, records: Sequence[_Record]
) -> dict[str, object]:
    bases = tuple(
        dict.fromkeys(record.statutory_basis for record in records if record.statutory_basis)
    )
    references = tuple(
        dict.fromkeys(
            reference for record in records for reference in record.source_references
        )
    )
    return {
        "exact_point": exact_point,
        "corrected_proposition": corrected_proposition,
        "statutory_basis": "; ".join(bases),
        "knowledge_ids": [record.knowledge_id for record in records],
        "source_references": list(references),
    }


def _dedupe_dicts(
    values: Sequence[dict[str, object]], keys: Sequence[str]
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for value in values:
        identity = json.dumps(
            [value.get(key) for key in keys],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if identity not in seen:
            seen.add(identity)
            result.append(value)
    return result


def _contains_any(normalized_text: str, alternatives: Sequence[str]) -> bool:
    stopwords = {
        "a",
        "an",
        "and",
        "can",
        "for",
        "is",
        "may",
        "of",
        "on",
        "or",
        "the",
        "to",
    }
    text_tokens = set(normalized_text.split())
    for value in alternatives:
        normalized = _normalize(value)
        if not normalized:
            continue
        if normalized in normalized_text:
            return True
        required = {
            token
            for token in normalized.split()
            if token not in stopwords and len(token) > 1
        }
        if len(required) >= 2 and required.issubset(text_tokens):
            return True
    return False


def _states_uncertainty(value: str) -> bool:
    normalized = _normalize(value)
    return any(
        marker in normalized
        for marker in (
            "insufficient knowledge",
            "insufficient authoritative",
            "cannot verify",
            "cannot determine",
            "not enough information",
            "uncertain",
            "nicht ausreichend",
            "kann nicht verifizieren",
            "niewystarczająca wiedza",
            "nie mogę zweryfikować",
        )
    )


def _parse_date(
    value: object, *, required: bool = False, current_allowed: bool = False
) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        if required:
            raise ValueError("NACHWG_DATE_REQUIRED")
        return None
    if isinstance(value, str):
        text = value.strip()
        if current_allowed and text.upper() in {"CURRENT", "OPEN", "NULL", "NONE"}:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            except ValueError as error:
                raise ValueError("NACHWG_DATE_INVALID") from error
    raise ValueError("NACHWG_DATE_INVALID")


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", _text(value)).casefold()
    text = re.sub(r"[^\w§€]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _normalize_label(value: object) -> str:
    normalized = " ".join(
        _text(value).replace("_", " ").strip().upper().rstrip(":").split()
    )
    return _ORACLE_KEY_ALIASES.get(normalized, normalized)


def _normalize_label_value(value: object) -> str:
    text = _text(value).replace("_", " ").replace("-", " ").upper()
    text = re.sub(r"[^A-ZÄÖÜ ]+", " ", text)
    return " ".join(text.split())


def _source_references(record: Mapping[str, object]) -> tuple[str, ...]:
    result: list[str] = []
    for key in ("source_reference", "source_id", "official_identifier"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            result.append(value.strip())
    result.extend(_string_tuple(_first(record, "source_urls", "sources")))
    return tuple(dict.fromkeys(result))


def _audit_value(audit: HatAuditResult | Mapping[str, object], key: str) -> object:
    if isinstance(audit, HatAuditResult):
        return getattr(audit, key)
    if isinstance(audit, Mapping):
        return audit.get(key)
    return None


def _required_text(value: Mapping[str, object], key: str) -> str:
    result = _text(value.get(key))
    if not result:
        raise ValueError("NACHWG_PACK_FIELD_MISSING")
    return result


def _first(value: Mapping[str, object], *keys: str) -> object:
    for key in keys:
        if key in value:
            return value[key]
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _joined_text(value: object) -> str:
    direct = _text(value)
    if direct:
        return direct
    return "; ".join(_string_tuple(value))


def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not _is_sequence(value):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


__all__ = [
    "HatAuditResult",
    "VERDICT_CORRECTION_REQUIRED",
    "VERDICT_INSUFFICIENT_KNOWLEDGE",
    "VERDICT_PASS",
    "audit_response",
    "load_pack",
    "postcheck_final",
    "validate_pack",
]
