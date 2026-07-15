from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ARCHITECT_HANDOFF_SCHEMA_VERSION = "aoia-architect-handoff-manifest-1a"
ARCHITECT_HANDOFF_MANIFEST_PATH = "data/architect_handoff_manifest_1a.json"
FINAL_REPOSITORY_FREEZE_PATH = "data/final_repository_freeze_1a/freeze_manifest.json"
PROJECT_NAME = "AOIA-Core"
HANDOFF_TYPE = "complete-architect-development-handoff"
DEVELOPMENT_STATUS = "development-prototype"
CURRENT_FREEZE_ID = "aoia-unix-unit-1a-r1"
CURRENT_FREEZE_MANIFEST_HASH = "9f5020095eb5d7d083ed837928198b9a05371766254a1e3ca61f2ff765d102e5"
SUPERSEDED_FREEZE_MANIFEST_HASH = "59d058483d30ae60e290fa0a576920163eea0f7aef94ff28e4bf3671652dfa43"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"

_GENERATED_ROOTS = (
    "data/unix_corpus_ingestion_1b",
    "data/unix_retrieval_adapter_1a",
    "data/unix_hat_routing_1a",
    "data/visible_unix_prototype_1a",
    "data/unix_full_validation_freeze_1a",
    "data/unix_full_validation_freeze_1a_r1",
    "runtime/knowledge/raw",
    "runtime/knowledge/extracted",
    "runtime/knowledge/parsed",
    "runtime/knowledge/index",
    "runtime/knowledge/manifests",
    "runtime/knowledge/canonical",
    "runtime/knowledge/candidates",
)
_CORPUS_ROOTS = (
    "corpus",
    "runtime/knowledge/source",
    "runtime/knowledge/raw",
    "runtime/knowledge/extracted",
    "runtime/knowledge/candidates",
    "data/unix_corpus_ingestion_1b",
)
_OFFLINE_PROTOTYPE_ROOTS = (
    "data/unix_corpus_ingestion_1b",
    "data/unix_retrieval_adapter_1a",
    "data/unix_hat_routing_1a",
    "data/visible_unix_prototype_1a",
)
_OFFLINE_PROTOTYPE_MODULES = (
    "runtime/visible_unix_prototype.py",
    "runtime/retrieval/unix_runtime_adapter.py",
    "runtime/memory_hats/unix_hat.py",
    "runtime/memory_hat_registry.py",
    "runtime/orchestrator/knowledge_router.py",
)
_HAT_ROOTS = (
    "corpus",
    "knowledge/hats",
    "knowledge/languages",
    "runtime/knowledge",
    "runtime/memory_hats",
    "runtime/retrieval",
)
_HAT_MODULES = (
    "runtime/memory_hat_registry.py",
    "runtime/orchestrator/knowledge_router.py",
    "runtime/safety/bash_parser.py",
)
_MANIFEST_FIELDS = {
    "authority_status",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_write",
    "current_freeze_id",
    "current_freeze_manifest_hash",
    "development_status",
    "excluded_cache_categories",
    "excluded_local_machine_categories",
    "file_count",
    "files",
    "handoff_type",
    "manifest_hash",
    "project_name",
    "regenerable_but_included_paths",
    "required_corpus_paths",
    "required_generated_paths",
    "required_hat_paths",
    "required_offline_prototype_paths",
    "required_runtime_paths",
    "required_test_paths",
    "schema_version",
    "superseded_freeze_manifest_hash",
    "total_bytes",
}


class ArchitectHandoffManifestError(ValueError):
    pass


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _belongs_to(relative: str, roots: Sequence[str]) -> bool:
    return any(relative == root or relative.startswith(root + "/") for root in roots)


def _repository_files(repository_root: str | Path) -> tuple[Path, tuple[dict[str, Any], ...]]:
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ArchitectHandoffManifestError("repository root must be a directory")
    records: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        parts = PurePosixPath(relative).parts
        if not parts or parts[0] == ".git" or "__pycache__" in parts or path.suffix == ".pyc":
            continue
        if relative in (ARCHITECT_HANDOFF_MANIFEST_PATH, FINAL_REPOSITORY_FREEZE_PATH):
            continue
        if path.is_symlink():
            raise ArchitectHandoffManifestError(f"symbolic links are not supported in the handoff: {relative}")
        if not path.is_file():
            continue
        records.append(
            {
                "path": relative,
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    records.sort(key=lambda item: item["path"])
    if not records:
        raise ArchitectHandoffManifestError("repository handoff file inventory is empty")
    return root, tuple(records)


def build_architect_handoff_manifest(repository_root: str | Path) -> dict[str, Any]:
    _root, records = _repository_files(repository_root)
    paths = tuple(item["path"] for item in records)
    required_runtime_paths = tuple(path for path in paths if path.startswith("runtime/"))
    required_hat_paths = tuple(
        path for path in paths if _belongs_to(path, _HAT_ROOTS) or path in _HAT_MODULES
    )
    required_corpus_paths = tuple(path for path in paths if _belongs_to(path, _CORPUS_ROOTS))
    generated_paths = tuple(path for path in paths if _belongs_to(path, _GENERATED_ROOTS))
    required_generated_paths = tuple(
        sorted(
            (
                *generated_paths,
                ARCHITECT_HANDOFF_MANIFEST_PATH,
                FINAL_REPOSITORY_FREEZE_PATH,
            )
        )
    )
    required_test_paths = tuple(path for path in paths if path.startswith("tests/"))
    required_offline_prototype_paths = tuple(
        path
        for path in paths
        if _belongs_to(path, _OFFLINE_PROTOTYPE_ROOTS) or path in _OFFLINE_PROTOTYPE_MODULES
    )
    material: dict[str, Any] = {
        "schema_version": ARCHITECT_HANDOFF_SCHEMA_VERSION,
        "project_name": PROJECT_NAME,
        "handoff_type": HANDOFF_TYPE,
        "development_status": DEVELOPMENT_STATUS,
        "authority_status": NON_AUTHORITATIVE,
        "can_approve": False,
        "can_dispatch": False,
        "can_execute": False,
        "can_write": False,
        "required_runtime_paths": list(required_runtime_paths),
        "required_hat_paths": list(required_hat_paths),
        "required_corpus_paths": list(required_corpus_paths),
        "required_generated_paths": list(required_generated_paths),
        "required_test_paths": list(required_test_paths),
        "required_offline_prototype_paths": list(required_offline_prototype_paths),
        "current_freeze_id": CURRENT_FREEZE_ID,
        "current_freeze_manifest_hash": CURRENT_FREEZE_MANIFEST_HASH,
        "superseded_freeze_manifest_hash": SUPERSEDED_FREEZE_MANIFEST_HASH,
        "regenerable_but_included_paths": list(generated_paths),
        "excluded_cache_categories": [
            "Python bytecode (*.pyc)",
            "Python cache directories (__pycache__)",
            "test runner scratch caches",
            "coverage scratch output",
        ],
        "excluded_local_machine_categories": [
            "API credentials and secret files",
            "host virtual environments",
            "machine-local temporary directories",
            "operator home-directory state",
        ],
        "file_count": len(records),
        "total_bytes": sum(item["size_bytes"] for item in records),
        "files": list(records),
    }
    return {**material, "manifest_hash": _sha256_bytes(_canonical_bytes(material))}


def serialize_architect_handoff_manifest(manifest: Mapping[str, Any]) -> bytes:
    verify_architect_handoff_manifest_data(manifest)
    return _canonical_bytes(manifest) + b"\n"


def verify_architect_handoff_manifest_data(manifest: Mapping[str, Any]) -> str:
    if not isinstance(manifest, Mapping) or set(manifest) != _MANIFEST_FIELDS:
        raise ArchitectHandoffManifestError("architect handoff manifest fields differ")
    if (
        manifest.get("schema_version") != ARCHITECT_HANDOFF_SCHEMA_VERSION
        or manifest.get("project_name") != PROJECT_NAME
        or manifest.get("handoff_type") != HANDOFF_TYPE
        or manifest.get("development_status") != DEVELOPMENT_STATUS
    ):
        raise ArchitectHandoffManifestError("architect handoff manifest identity differs")
    if manifest.get("authority_status") != NON_AUTHORITATIVE or any(
        manifest.get(field) is not False for field in ("can_approve", "can_dispatch", "can_execute", "can_write")
    ):
        raise ArchitectHandoffManifestError("architect handoff manifest cannot carry authority")
    supplied_hash = manifest.get("manifest_hash")
    if not isinstance(supplied_hash, str) or len(supplied_hash) != 64:
        raise ArchitectHandoffManifestError("architect handoff manifest hash is malformed")
    material = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if supplied_hash != _sha256_bytes(_canonical_bytes(material)):
        raise ArchitectHandoffManifestError("architect handoff manifest hash differs")
    for field in (
        "required_runtime_paths",
        "required_hat_paths",
        "required_corpus_paths",
        "required_generated_paths",
        "required_test_paths",
        "required_offline_prototype_paths",
        "regenerable_but_included_paths",
    ):
        values = manifest.get(field)
        if not isinstance(values, list) or values != sorted(set(values)):
            raise ArchitectHandoffManifestError(f"architect handoff path list differs: {field}")
        for value in values:
            parsed = PurePosixPath(value)
            if not value or parsed.is_absolute() or ".." in parsed.parts or str(parsed) != value:
                raise ArchitectHandoffManifestError(f"architect handoff path is unsafe: {value!r}")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise ArchitectHandoffManifestError("architect handoff file inventory is invalid")
    if manifest.get("file_count") != len(records) or manifest.get("total_bytes") != sum(
        item.get("size_bytes", -1) for item in records if isinstance(item, dict)
    ):
        raise ArchitectHandoffManifestError("architect handoff file totals differ")
    paths = []
    for item in records:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise ArchitectHandoffManifestError("architect handoff file record is malformed")
        path = item["path"]
        parsed = PurePosixPath(path) if isinstance(path, str) else PurePosixPath("")
        if not path or parsed.is_absolute() or ".." in parsed.parts or str(parsed) != path:
            raise ArchitectHandoffManifestError("architect handoff file path is unsafe")
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise ArchitectHandoffManifestError("architect handoff file hash is malformed")
        if type(item["size_bytes"]) is not int or item["size_bytes"] < 0:
            raise ArchitectHandoffManifestError("architect handoff file size is invalid")
        paths.append(path)
    if paths != sorted(set(paths)) or any(
        excluded in paths
        for excluded in (ARCHITECT_HANDOFF_MANIFEST_PATH, FINAL_REPOSITORY_FREEZE_PATH)
    ):
        raise ArchitectHandoffManifestError("architect handoff file inventory ordering differs")
    if not {
        ARCHITECT_HANDOFF_MANIFEST_PATH,
        FINAL_REPOSITORY_FREEZE_PATH,
    } <= set(manifest["required_generated_paths"]):
        raise ArchitectHandoffManifestError("self-describing evidence paths are not required")
    return supplied_hash


def verify_architect_handoff_manifest(
    manifest_path: str | Path,
    *,
    repository_root: str | Path,
) -> str:
    path = Path(manifest_path)
    if path.is_symlink() or not path.is_file():
        raise ArchitectHandoffManifestError("architect handoff manifest path is not a regular file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArchitectHandoffManifestError("architect handoff manifest is not strict UTF-8 JSON") from exc
    supplied_hash = verify_architect_handoff_manifest_data(payload)
    if payload != build_architect_handoff_manifest(repository_root):
        raise ArchitectHandoffManifestError("architect handoff manifest does not match repository files")
    return supplied_hash


def materialize_architect_handoff_manifest(
    repository_root: str | Path,
    *,
    replace: bool = False,
) -> Path:
    root = Path(repository_root).resolve(strict=True)
    destination = root / ARCHITECT_HANDOFF_MANIFEST_PATH
    payload = serialize_architect_handoff_manifest(build_architect_handoff_manifest(root))
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_file():
            raise ArchitectHandoffManifestError("existing architect handoff manifest differs")
        if destination.read_bytes() == payload:
            return destination
        if not replace:
            raise ArchitectHandoffManifestError("existing architect handoff manifest differs")
        with destination.open("wb") as handle:
            handle.write(payload)
        return destination
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ArchitectHandoffManifestError("architect handoff data root is invalid")
    with destination.open("xb") as handle:
        handle.write(payload)
    return destination


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or verify the inert AOIA-Core architect handoff manifest.")
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--replace", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.repository_root)
    if args.operation == "build":
        path = materialize_architect_handoff_manifest(root, replace=args.replace)
        manifest_hash = verify_architect_handoff_manifest(path, repository_root=root)
    else:
        path = root / ARCHITECT_HANDOFF_MANIFEST_PATH
        manifest_hash = verify_architect_handoff_manifest(path, repository_root=root)
    print(json.dumps({"authority_status": NON_AUTHORITATIVE, "manifest_hash": manifest_hash, "path": ARCHITECT_HANDOFF_MANIFEST_PATH}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
