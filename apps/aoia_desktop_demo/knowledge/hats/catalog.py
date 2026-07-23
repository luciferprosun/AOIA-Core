"""Strict committed HAT catalog parsing; catalog data never dispatches code."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .contracts import HatDescriptor, HatValidationError, is_sha256


CATALOG_DIR = Path(__file__).resolve().parent / "catalog_entries"
_REQUIRED_CAPABILITIES = (
    "local_read_only_retrieval",
    "stable_source_ids",
    "provenance",
    "deterministic_evidence_hash",
)
_CATALOG_KEYS = {
    "schema_version",
    "hat_id",
    "display_name",
    "domain",
    "adapter_id",
    "descriptor_schema_version",
    "evidence_schema_version",
    "external_resource",
    "corpus_committed",
    "authoritative",
    "binding_key",
    "library_id",
    "library_version",
    "manifest_id",
    "manifest_digest",
    "index_id",
    "index_digest",
    "indexed_source_count",
    "required_capabilities",
}


@dataclass(frozen=True, slots=True)
class HatCatalogEntry:
    descriptor: HatDescriptor
    binding_key: str
    corpus_committed: bool
    library_id: str
    library_version: str
    manifest_id: str
    manifest_digest: str
    index_id: str
    index_digest: str
    indexed_source_count: int
    required_capabilities: tuple[str, ...]


def parse_catalog_entry(value: object) -> HatCatalogEntry:
    if not isinstance(value, dict) or set(value) != _CATALOG_KEYS:
        raise HatValidationError("catalog entry has an unexpected shape")
    if value.get("schema_version") != 1:
        raise HatValidationError("unsupported HAT catalog schema")
    descriptor = HatDescriptor(
        hat_id=value["hat_id"],
        display_name=value["display_name"],
        domain=value["domain"],
        adapter_id=value["adapter_id"],
        descriptor_schema_version=value["descriptor_schema_version"],
        evidence_schema_version=value["evidence_schema_version"],
        external_resource=value["external_resource"],
        authoritative=value["authoritative"],
    )
    binding_key = value["binding_key"]
    if not isinstance(binding_key, str) or not binding_key.strip():
        raise HatValidationError("catalog binding key must be non-empty text")
    if value["corpus_committed"] is not False:
        raise HatValidationError("external HAT corpus must not be marked committed")
    for name in ("library_id", "library_version", "manifest_id", "index_id"):
        if not isinstance(value[name], str) or not value[name].strip():
            raise HatValidationError(f"catalog {name} must be non-empty text")
    for name in ("manifest_digest", "index_digest"):
        if not is_sha256(value[name]):
            raise HatValidationError(f"catalog {name} must be a SHA-256")
    count = value["indexed_source_count"]
    if type(count) is not int or count < 1:
        raise HatValidationError("catalog indexed source count must be positive")
    capabilities = value["required_capabilities"]
    if not isinstance(capabilities, list) or tuple(capabilities) != _REQUIRED_CAPABILITIES:
        raise HatValidationError("catalog required capabilities differ from the bounded contract")
    return HatCatalogEntry(
        descriptor=descriptor,
        binding_key=binding_key,
        corpus_committed=False,
        library_id=value["library_id"],
        library_version=value["library_version"],
        manifest_id=value["manifest_id"],
        manifest_digest=value["manifest_digest"],
        index_id=value["index_id"],
        index_digest=value["index_digest"],
        indexed_source_count=count,
        required_capabilities=tuple(capabilities),
    )


def load_catalog(directory: Path = CATALOG_DIR) -> tuple[HatCatalogEntry, ...]:
    try:
        root = directory.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HatValidationError("HAT catalog directory is unavailable") from exc
    entries: list[HatCatalogEntry] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.json"), key=lambda item: item.name):
        if path.is_symlink() or path.resolve(strict=True).parent != root:
            raise HatValidationError("catalog entry path is unsafe")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HatValidationError("catalog entry is malformed") from exc
        entry = parse_catalog_entry(value)
        if entry.descriptor.hat_id in seen:
            raise HatValidationError("duplicate catalog HAT id")
        seen.add(entry.descriptor.hat_id)
        entries.append(entry)
    if not entries:
        raise HatValidationError("HAT catalog is empty")
    return tuple(entries)
