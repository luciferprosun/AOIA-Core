from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION = "AOIA_PACKAGE_INSTALL_PROPOSAL_1A"

PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY = "PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY"
PACKAGE_INSTALL_PROPOSAL_BLOCKED = "PACKAGE_INSTALL_PROPOSAL_BLOCKED"

PACKAGE_INSTALL_PROPOSAL_REASON_READY_METADATA_ONLY = "PACKAGE_INSTALL_PROPOSAL_REASON_READY_METADATA_ONLY"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNSUPPORTED_ECOSYSTEM = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNSUPPORTED_ECOSYSTEM"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_STALE_EVIDENCE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_STALE_EVIDENCE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_HASH_MISMATCH = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_HASH_MISMATCH"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_JSON_SERIALIZABLE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_JSON_SERIALIZABLE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_COMMAND_LIKE_EVIDENCE = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_COMMAND_LIKE_EVIDENCE"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM"
PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA = "PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA"

SUPPORTED_PACKAGE_ECOSYSTEMS = frozenset({"pip", "npm", "apt"})

_HEX = frozenset("0123456789abcdef")
_MAX_TEXT = 1024
_MAX_COLLECTION_ITEMS = 32
_MAX_DEPTH = 4
_ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "proposal_id",
        "ecosystem",
        "package_name",
        "version",
        "reason",
        "requested_by",
        "created_at_tick",
        "expires_at_tick",
        "toctou_evidence",
        "source_id",
        "source_hash",
        "metadata",
        "request_hash",
    }
)
_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approved",
        "authorized",
        "safe",
        "authority",
        "authority_granted",
        "human_approved",
        "can_install",
        "can_approve",
        "can_execute",
        "can_write",
        "can_push",
        "can_call_provider",
        "can_change_gate",
        "gate_satisfied",
        "install_allowed",
        "execution_allowed",
    }
)
_DANGEROUS_FIELD_NAMES = frozenset(
    {
        "command",
        "commands",
        "shell",
        "script",
        "tool",
        "tools",
        "url",
        "endpoint",
        "registry_url",
        "headers",
        "authorization",
        "secret",
        "token",
        "api" + "_key",
        "env",
        "get" + "env",
        "os." + "environ",
        "dependency_file_patch",
        "requirements_txt",
        "package_json",
        "lockfile",
    }
)
_COMMAND_TEXT_PATTERN = re.compile(
    r"(?i)(?:\b(?:python\s+-m\s+pip|pip|npm|apt|apt-get)\s+(?:install|i|add)\b|"
    r"\b(?:curl|wget|bash|sh|sudo|powershell|cmd\.exe)\b|"
    r"\b(?:eval|exec|compile|__import__|importlib|os\.system|" + ("sub" + "process") + r")\b|"
    r"(?:;|&&|\|\||`|\$\(|<\(|>\(|\n))"
)
_AUTHORITY_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:approved|authorized|human\s+approved|approval\s+granted|"
    r"safe\s+to\s+(?:install|execute|write|push)|can\s+(?:install|execute|write)|"
    r"gate\s+satisfied|authority\s+granted)\b"
)
_PIP_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_NPM_NAME_PATTERN = re.compile(
    r"^(?:@[a-z0-9][a-z0-9._~-]*/)?[a-z0-9][a-z0-9._~-]*$"
)
_APT_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+~-]*$")


@dataclass(frozen=True)
class PackageInstallProposalRequest:
    ecosystem: str
    package_name: str
    version: str
    reason: str
    requested_by: str
    created_at_tick: int
    expires_at_tick: int
    toctou_evidence: Mapping[str, Any]
    proposal_id: str = "package-install-proposal"
    source_id: str | None = None
    source_hash: str | None = None
    metadata: Mapping[str, Any] | None = None
    schema_version: str = PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION
    request_hash: str | None = None


@dataclass(frozen=True)
class PackageInstallProposal:
    schema_version: str
    status: str
    reason_codes: tuple[str, ...]
    proposal_id: str | None
    ecosystem: str | None
    package_name: str | None
    version: str | None
    normalized_package_ref: str | None
    reason: str | None
    requested_by: str | None
    created_at_tick: int | None
    expires_at_tick: int | None
    source_id: str | None
    source_hash: str | None
    toctou_evidence_hash: str | None
    request_hash: str | None
    proposal_hash: str
    human_review_required: bool = True
    install_performed: bool = False
    package_manager_called: bool = False
    network_called: bool = False
    process_started: bool = False
    shell_called: bool = False
    provider_called: bool = False
    browser_opened: bool = False
    git_action_performed: bool = False
    dependency_file_modified: bool = False
    package_metadata_fetched: bool = False
    approval_created: bool = False
    gate_satisfied: bool = False
    human_barrier_satisfied: bool = False
    can_install: bool = False
    can_execute: bool = False
    can_write: bool = False
    can_push: bool = False
    can_call_provider: bool = False
    can_change_gate: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION)
        object.__setattr__(self, "reason_codes", tuple(sorted(set(self.reason_codes))))
        if self.status not in {PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY, PACKAGE_INSTALL_PROPOSAL_BLOCKED}:
            raise ValueError("unsupported package install proposal status")
        if not _sha256_like(self.proposal_hash):
            raise ValueError("proposal_hash must be a sha256 hex digest")
        object.__setattr__(self, "human_review_required", True)
        for field_name in (
            "install_performed",
            "package_manager_called",
            "network_called",
            "process_started",
            "shell_called",
            "provider_called",
            "browser_opened",
            "git_action_performed",
            "dependency_file_modified",
            "package_metadata_fetched",
            "approval_created",
            "gate_satisfied",
            "human_barrier_satisfied",
            "can_install",
            "can_execute",
            "can_write",
            "can_push",
            "can_call_provider",
            "can_change_gate",
        ):
            object.__setattr__(self, field_name, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "proposal_id": self.proposal_id,
            "ecosystem": self.ecosystem,
            "package_name": self.package_name,
            "version": self.version,
            "normalized_package_ref": self.normalized_package_ref,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "created_at_tick": self.created_at_tick,
            "expires_at_tick": self.expires_at_tick,
            "source_id": self.source_id,
            "source_hash": self.source_hash,
            "toctou_evidence_hash": self.toctou_evidence_hash,
            "request_hash": self.request_hash,
            "proposal_hash": self.proposal_hash,
            "human_review_required": True,
            "install_performed": False,
            "package_manager_called": False,
            "network_called": False,
            "process_started": False,
            "shell_called": False,
            "provider_called": False,
            "browser_opened": False,
            "git_action_performed": False,
            "dependency_file_modified": False,
            "package_metadata_fetched": False,
            "approval_created": False,
            "gate_satisfied": False,
            "human_barrier_satisfied": False,
            "can_install": False,
            "can_execute": False,
            "can_write": False,
            "can_push": False,
            "can_call_provider": False,
            "can_change_gate": False,
        }


def propose_package_install(request: object, *, now_tick: object) -> PackageInstallProposal:
    reason_codes: list[str] = []
    try:
        tick = _nonnegative_int("now_tick", now_tick)
    except (TypeError, ValueError):
        return _blocked((PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE,))

    try:
        data = _coerce_request_mapping(request)
        input_fingerprint = _json_fingerprint(data)
    except TypeError:
        return _blocked((PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_JSON_SERIALIZABLE,))

    unknown_fields = sorted(str(field) for field in data if field not in _ALLOWED_REQUEST_FIELDS)
    if unknown_fields:
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNKNOWN_FIELD)
    if data.get("schema_version") != PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION:
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE)

    try:
        proposal_id = _required_text("proposal_id", data.get("proposal_id"))
        ecosystem = _required_text("ecosystem", data.get("ecosystem")).casefold()
        package_name = _required_text("package_name", data.get("package_name"))
        version = _required_text("version", data.get("version"))
        reason = _required_text("reason", data.get("reason"))
        requested_by = _required_text("requested_by", data.get("requested_by"))
        created_at_tick = _nonnegative_int("created_at_tick", data.get("created_at_tick"))
        expires_at_tick = _nonnegative_int("expires_at_tick", data.get("expires_at_tick"))
        source_id = _optional_text("source_id", data.get("source_id"))
        source_hash = _optional_hash("source_hash", data.get("source_hash"))
        toctou_evidence = _required_mapping("toctou_evidence", data.get("toctou_evidence"))
        metadata = _optional_mapping("metadata", data.get("metadata"))
        request_hash = _optional_hash("request_hash", data.get("request_hash"))
        normalized_toctou = _json_fingerprint(toctou_evidence)
        normalized_metadata = _json_fingerprint(metadata or {})
    except (TypeError, ValueError):
        return _blocked(
            tuple(reason_codes or (PACKAGE_INSTALL_PROPOSAL_BLOCKED_MALFORMED_EVIDENCE,)),
            input_fingerprint=input_fingerprint,
        )

    if ecosystem not in SUPPORTED_PACKAGE_ECOSYSTEMS:
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNSUPPORTED_ECOSYSTEM)
    if ecosystem in SUPPORTED_PACKAGE_ECOSYSTEMS and not _canonical_package_name(ecosystem, package_name):
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_NON_CANONICAL_PACKAGE)
    if not _pinned_version(version):
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_UNPINNED_PACKAGE)
    if created_at_tick > tick or expires_at_tick < tick or expires_at_tick < created_at_tick:
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_STALE_EVIDENCE)
    if _has_key(data, _DANGEROUS_FIELD_NAMES):
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_DANGEROUS_METADATA)
    if _has_key(data, _AUTHORITY_FIELD_NAMES) or _has_authority_text(data):
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_AUTHORITY_CLAIM)
    command_scan_material = {
        "reason": reason,
        "requested_by": requested_by,
        "metadata": normalized_metadata,
        "toctou_evidence": normalized_toctou,
    }
    if _has_command_text(command_scan_material) or _has_command_separator(package_name) or _has_command_separator(version):
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_COMMAND_LIKE_EVIDENCE)

    material_for_request_hash = dict(input_fingerprint)
    material_for_request_hash.pop("request_hash", None)
    computed_request_hash = _stable_hash(material_for_request_hash)
    if request_hash is not None and request_hash != computed_request_hash:
        reason_codes.append(PACKAGE_INSTALL_PROPOSAL_BLOCKED_HASH_MISMATCH)
    request_hash = request_hash or computed_request_hash

    toctou_evidence_hash = _stable_hash(normalized_toctou)
    normalized_package_ref = None
    if ecosystem in SUPPORTED_PACKAGE_ECOSYSTEMS and _canonical_package_name(ecosystem, package_name) and _pinned_version(version):
        normalized_package_ref = f"{ecosystem}:{package_name}=={version}"

    status = PACKAGE_INSTALL_PROPOSAL_BLOCKED if reason_codes else PACKAGE_INSTALL_PROPOSAL_READY_METADATA_ONLY
    if not reason_codes:
        reason_codes = [PACKAGE_INSTALL_PROPOSAL_REASON_READY_METADATA_ONLY]

    proposal_material = {
        "schema_version": PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
        "status": status,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "proposal_id": proposal_id,
        "ecosystem": ecosystem,
        "package_name": package_name,
        "version": version,
        "normalized_package_ref": normalized_package_ref,
        "reason": reason,
        "requested_by": requested_by,
        "created_at_tick": created_at_tick,
        "expires_at_tick": expires_at_tick,
        "source_id": source_id,
        "source_hash": source_hash,
        "toctou_evidence_hash": toctou_evidence_hash,
        "metadata": normalized_metadata,
        "request_hash": request_hash,
        "now_tick": tick,
        "human_review_required": True,
    }
    return PackageInstallProposal(
        schema_version=PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
        status=status,
        reason_codes=tuple(reason_codes),
        proposal_id=proposal_id,
        ecosystem=ecosystem,
        package_name=package_name,
        version=version,
        normalized_package_ref=normalized_package_ref,
        reason=reason,
        requested_by=requested_by,
        created_at_tick=created_at_tick,
        expires_at_tick=expires_at_tick,
        source_id=source_id,
        source_hash=source_hash,
        toctou_evidence_hash=toctou_evidence_hash,
        request_hash=request_hash,
        proposal_hash=_stable_hash(proposal_material),
    )


def compute_package_install_request_hash(request: object) -> str:
    data = _coerce_request_mapping(request)
    fingerprint = _json_fingerprint(data)
    if isinstance(fingerprint, dict):
        fingerprint.pop("request_hash", None)
    return _stable_hash(fingerprint)


def compute_package_install_toctou_evidence_hash(toctou_evidence: Mapping[str, Any]) -> str:
    return _stable_hash(_json_fingerprint(_required_mapping("toctou_evidence", toctou_evidence)))


def _coerce_request_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, PackageInstallProposalRequest):
        return {
            "schema_version": value.schema_version,
            "proposal_id": value.proposal_id,
            "ecosystem": value.ecosystem,
            "package_name": value.package_name,
            "version": value.version,
            "reason": value.reason,
            "requested_by": value.requested_by,
            "created_at_tick": value.created_at_tick,
            "expires_at_tick": value.expires_at_tick,
            "toctou_evidence": value.toctou_evidence,
            "source_id": value.source_id,
            "source_hash": value.source_hash,
            "metadata": value.metadata or {},
            "request_hash": value.request_hash,
        }
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("package install proposal request must be mapping evidence")


def _blocked(
    reason_codes: tuple[str, ...],
    *,
    input_fingerprint: Any | None = None,
) -> PackageInstallProposal:
    material = {
        "schema_version": PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
        "status": PACKAGE_INSTALL_PROPOSAL_BLOCKED,
        "reason_codes": tuple(sorted(set(reason_codes))),
        "input_fingerprint": input_fingerprint,
        "human_review_required": True,
    }
    return PackageInstallProposal(
        schema_version=PACKAGE_INSTALL_PROPOSAL_SCHEMA_VERSION,
        status=PACKAGE_INSTALL_PROPOSAL_BLOCKED,
        reason_codes=reason_codes,
        proposal_id=None,
        ecosystem=None,
        package_name=None,
        version=None,
        normalized_package_ref=None,
        reason=None,
        requested_by=None,
        created_at_tick=None,
        expires_at_tick=None,
        source_id=None,
        source_hash=None,
        toctou_evidence_hash=None,
        request_hash=None,
        proposal_hash=_stable_hash(material),
    )


def _canonical_package_name(ecosystem: str, package_name: str) -> bool:
    if ecosystem == "pip":
        return bool(_PIP_NAME_PATTERN.fullmatch(package_name))
    if ecosystem == "npm":
        return bool(_NPM_NAME_PATTERN.fullmatch(package_name))
    if ecosystem == "apt":
        return bool(_APT_NAME_PATTERN.fullmatch(package_name))
    return False


def _pinned_version(version: str) -> bool:
    lowered = version.strip().casefold()
    if lowered in {"latest", "next", "stable", "*", "x"}:
        return False
    if any(item in version for item in (" ", "\t", "\n", ",", ";", "|", "&", "<", ">", "=", "^", "*")):
        return False
    return bool(_VERSION_PATTERN.fullmatch(version))


def _has_key(value: object, names: frozenset[str]) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and key.strip().casefold() in names:
                return True
            if _has_key(item, names):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_has_key(item, names) for item in value)
    return False


def _has_command_text(value: object) -> bool:
    return any(_COMMAND_TEXT_PATTERN.search(item) for item in _text_values(value))


def _has_authority_text(value: object) -> bool:
    return any(_AUTHORITY_TEXT_PATTERN.search(item) for item in _text_values(value))


def _has_command_separator(value: str) -> bool:
    lowered = value.casefold()
    return any(item in lowered for item in (";", "&&", "||", "`", "$(", "\n", "__import__", "eval(", "exec("))


def _text_values(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        values: list[str] = []
        for key, item in value.items():
            values.append(str(key))
            values.extend(_text_values(item))
        return tuple(values)
    if isinstance(value, (tuple, list)):
        values = []
        for item in value:
            values.extend(_text_values(item))
        return tuple(values)
    return ()


def _json_fingerprint(value: object, *, depth: int = 0) -> Any:
    if depth > _MAX_DEPTH:
        raise TypeError("package install proposal evidence is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 1_000_000_000:
            raise TypeError("integer evidence is excessive")
        return value
    if isinstance(value, float):
        raise TypeError("floating point package install proposal evidence is ambiguous")
    if isinstance(value, str):
        if len(value) > _MAX_TEXT:
            raise TypeError("text evidence is excessive")
        return value
    if isinstance(value, Mapping):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("mapping evidence is excessive")
        normalized: dict[str, Any] = {}
        for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
            if not isinstance(key, str) or not key.strip():
                raise TypeError("mapping evidence keys must be non-empty text")
            normalized[key.strip()] = _json_fingerprint(item, depth=depth + 1)
        return normalized
    if isinstance(value, (tuple, list)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise TypeError("sequence evidence is excessive")
        return tuple(_json_fingerprint(item, depth=depth + 1) for item in value)
    raise TypeError("package install proposal evidence must be JSON serializable")


def _required_mapping(name: str, value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a non-empty mapping")
    return dict(value)


def _optional_mapping(name: str, value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return dict(value)


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if len(value.strip()) > _MAX_TEXT:
        raise ValueError(f"{name} is too long")
    return value.strip()


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _optional_hash(name: str, value: object) -> str | None:
    if value is None:
        return None
    normalized = _required_text(name, value).lower()
    if not _sha256_like(normalized):
        raise ValueError(f"{name} must be a sha256 hex digest")
    return normalized


def _nonnegative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _sha256_like(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in _HEX for char in value.lower())


def _stable_hash(value: object) -> str:
    material = json.dumps(_json_fingerprint(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
