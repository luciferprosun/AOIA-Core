"""Deterministic, non-authoritative AOIA-Core repository checkpoint evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from runtime.architect_handoff_manifest import (
    ARCHITECT_HANDOFF_MANIFEST_PATH,
    FINAL_REPOSITORY_FREEZE_PATH,
    verify_architect_handoff_manifest,
)


FINAL_FREEZE_SCHEMA_VERSION = "aoia-final-repository-freeze-1a"
FINAL_FREEZE_ID = "aoia-core-development-prototype-1a"
DEVELOPMENT_STATUS = "development-prototype"
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"

UNIX_R1_FREEZE_PATH = "data/unix_full_validation_freeze_1a_r1/freeze_manifest.json"
CORPUS_MANIFEST_PATH = "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json"
RETRIEVAL_INDEX_PATH = "data/unix_retrieval_adapter_1a/index/index_manifest.json"
UNIX_HAT_DESCRIPTOR_PATH = "data/unix_hat_routing_1a/unix_hat_descriptor.json"

_HAT_IDENTITY_PATHS = {
    "bash": ("runtime/safety/bash_parser.py", "runtime/safety/approval_gate.py"),
    "linux": (
        "runtime/knowledge/rhcsa_engine.py",
        "runtime/retrieval/facade.py",
        "runtime/retrieval/linux/__init__.py",
        "runtime/retrieval/linux/retrieval_engine.py",
    ),
    "python": ("knowledge/hats/hat_003_python/manifest/hat_003_manifest.json",),
}
_AUTHORITY_TEST_PATHS = (
    "tests/canonical_human_gate_support.py",
    "tests/test_authority_bypass_adversarial_1a.py",
    "tests/test_authority_bypass_adversarial_suite_1a.py",
    "tests/adversarial/test_durable_approval_binding.py",
)
_STATIC_TEST_PATHS = (
    "tests/static_capability_boundary_support_1a.py",
    "tests/test_static_capability_boundary_1a.py",
)
_SECRET_PATH_PARTS = {
    ".env",
    "credentials",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "private_key",
    "secrets",
}
_FIELDS = {
    "architect_handoff_manifest_hash",
    "authority_boundary_test_identity",
    "authority_status",
    "branch",
    "can_approve",
    "can_dispatch",
    "can_execute",
    "can_invoke_browser",
    "can_invoke_git",
    "can_invoke_network",
    "can_invoke_provider",
    "can_write",
    "checkpoint_file_count",
    "checkpoint_inventory_hash",
    "checkpoint_total_bytes",
    "corpus_manifest_hash",
    "development_status",
    "files",
    "freeze_id",
    "freeze_manifest_hash",
    "hat_identities",
    "parent_head",
    "retrieval_index_hash",
    "schema_version",
    "staged_candidate_hash",
    "static_capability_test_identity",
    "test_suite",
    "unix_r1_freeze_hash",
    "unix_hat_identity",
}


class FinalRepositoryFreezeError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    parsed = PurePosixPath(value)
    if not value or parsed.is_absolute() or ".." in parsed.parts or str(parsed) != value:
        raise FinalRepositoryFreezeError(f"unsafe repository path: {value!r}")
    return parsed


def _reject_forbidden_path(relative: str) -> None:
    parts = PurePosixPath(relative).parts
    lowered = {part.casefold() for part in parts}
    if "__pycache__" in parts or relative.endswith(".pyc"):
        raise FinalRepositoryFreezeError(f"cache or bytecode is forbidden: {relative}")
    if any(part in {".venv", "venv", "env"} or part.endswith(".egg-info") for part in lowered):
        raise FinalRepositoryFreezeError(f"virtual environment or local install metadata is forbidden: {relative}")
    if lowered & _SECRET_PATH_PARTS or any(part.endswith(".pem") or part.endswith(".key") for part in lowered):
        raise FinalRepositoryFreezeError(f"secret-like path is forbidden: {relative}")


def _file_record(root: Path, relative: str) -> dict[str, Any]:
    _safe_relative(relative)
    _reject_forbidden_path(relative)
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise FinalRepositoryFreezeError(f"checkpoint path is not a regular file: {relative}")
    info = path.stat()
    portable_mode = 0o755 if stat.S_IMODE(info.st_mode) & 0o111 else 0o644
    return {
        "mode": portable_mode,
        "path": relative,
        "sha256": _sha256_file(path),
        "size_bytes": info.st_size,
    }


def build_checkpoint_inventory(repository_root: str | Path) -> tuple[dict[str, Any], ...]:
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise FinalRepositoryFreezeError("repository root is invalid")
    records = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        parts = PurePosixPath(relative).parts
        if not parts or parts[0] == ".git" or relative == FINAL_REPOSITORY_FREEZE_PATH:
            continue
        if path.is_symlink():
            raise FinalRepositoryFreezeError(f"symbolic links are forbidden: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise FinalRepositoryFreezeError(f"special files are forbidden: {relative}")
        records.append(_file_record(root, relative))
    records.sort(key=lambda item: item["path"])
    if not records:
        raise FinalRepositoryFreezeError("checkpoint inventory is empty")
    return tuple(records)


def _load_json(root: Path, relative: str) -> Mapping[str, Any]:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise FinalRepositoryFreezeError(f"required evidence is missing: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FinalRepositoryFreezeError(f"required evidence is invalid JSON: {relative}") from exc
    if not isinstance(value, Mapping):
        raise FinalRepositoryFreezeError(f"required evidence is not an object: {relative}")
    return value


def _identity(root: Path, paths: Sequence[str]) -> str:
    records = [_file_record(root, path) for path in sorted(paths)]
    return _sha256_bytes(_canonical_bytes(records))


def build_final_repository_freeze(
    repository_root: str | Path,
    *,
    branch: str,
    parent_head: str,
    passed: int,
    skipped: int,
    failures: int = 0,
    errors: int = 0,
) -> dict[str, Any]:
    root = Path(repository_root).resolve(strict=True)
    if branch != "feature/m2-b0-provider-critic-inert-core":
        raise FinalRepositoryFreezeError("checkpoint branch differs")
    if len(parent_head) != 40 or any(char not in "0123456789abcdef" for char in parent_head):
        raise FinalRepositoryFreezeError("parent HEAD is malformed")
    for name, value in (("passed", passed), ("skipped", skipped), ("failures", failures), ("errors", errors)):
        if type(value) is not int or value < 0:
            raise FinalRepositoryFreezeError(f"test suite count is invalid: {name}")
    if failures or errors:
        raise FinalRepositoryFreezeError("failing test suite cannot be frozen")

    handoff_hash = verify_architect_handoff_manifest(
        root / ARCHITECT_HANDOFF_MANIFEST_PATH,
        repository_root=root,
    )
    unix_freeze = _load_json(root, UNIX_R1_FREEZE_PATH)
    corpus = _load_json(root, CORPUS_MANIFEST_PATH)
    index = _load_json(root, RETRIEVAL_INDEX_PATH)
    unix_hat = _load_json(root, UNIX_HAT_DESCRIPTOR_PATH)
    records = build_checkpoint_inventory(root)
    inventory_hash = _sha256_bytes(_canonical_bytes(records))
    hat_identities = {
        name: {"identity_hash": _identity(root, paths), "paths": list(paths)}
        for name, paths in sorted(_HAT_IDENTITY_PATHS.items())
    }
    material: dict[str, Any] = {
        "schema_version": FINAL_FREEZE_SCHEMA_VERSION,
        "freeze_id": FINAL_FREEZE_ID,
        "development_status": DEVELOPMENT_STATUS,
        "authority_status": NON_AUTHORITATIVE,
        "can_approve": False,
        "can_dispatch": False,
        "can_execute": False,
        "can_invoke_browser": False,
        "can_invoke_git": False,
        "can_invoke_network": False,
        "can_invoke_provider": False,
        "can_write": False,
        "branch": branch,
        "parent_head": parent_head,
        "architect_handoff_manifest_hash": handoff_hash,
        "unix_r1_freeze_hash": unix_freeze.get("freeze_manifest_hash"),
        "corpus_manifest_hash": corpus.get("manifest_hash"),
        "retrieval_index_hash": index.get("index_hash"),
        "unix_hat_identity": {
            "descriptor_hash": unix_hat.get("descriptor_hash"),
            "hat_id": unix_hat.get("hat_id"),
            "path": UNIX_HAT_DESCRIPTOR_PATH,
        },
        "hat_identities": hat_identities,
        "authority_boundary_test_identity": _identity(root, _AUTHORITY_TEST_PATHS),
        "static_capability_test_identity": _identity(root, _STATIC_TEST_PATHS),
        "test_suite": {
            "errors": errors,
            "failures": failures,
            "non_interactive": True,
            "passed": passed,
            "skipped": skipped,
        },
        "checkpoint_file_count": len(records),
        "checkpoint_total_bytes": sum(item["size_bytes"] for item in records),
        "checkpoint_inventory_hash": inventory_hash,
        "staged_candidate_hash": inventory_hash,
        "files": list(records),
    }
    return {**material, "freeze_manifest_hash": _sha256_bytes(_canonical_bytes(material))}


def serialize_final_repository_freeze(freeze: Mapping[str, Any]) -> bytes:
    verify_final_repository_freeze_data(freeze)
    return _canonical_bytes(freeze) + b"\n"


def verify_final_repository_freeze_data(freeze: Mapping[str, Any]) -> str:
    if not isinstance(freeze, Mapping) or set(freeze) != _FIELDS:
        raise FinalRepositoryFreezeError("final repository freeze fields differ")
    if (
        freeze.get("schema_version") != FINAL_FREEZE_SCHEMA_VERSION
        or freeze.get("freeze_id") != FINAL_FREEZE_ID
        or freeze.get("development_status") != DEVELOPMENT_STATUS
    ):
        raise FinalRepositoryFreezeError("final repository freeze identity differs")
    if freeze.get("authority_status") != NON_AUTHORITATIVE or any(
        freeze.get(field) is not False
        for field in (
            "can_approve",
            "can_dispatch",
            "can_execute",
            "can_invoke_browser",
            "can_invoke_git",
            "can_invoke_network",
            "can_invoke_provider",
            "can_write",
        )
    ):
        raise FinalRepositoryFreezeError("final repository freeze cannot carry authority")
    supplied = freeze.get("freeze_manifest_hash")
    material = {key: value for key, value in freeze.items() if key != "freeze_manifest_hash"}
    if not isinstance(supplied, str) or supplied != _sha256_bytes(_canonical_bytes(material)):
        raise FinalRepositoryFreezeError("final repository freeze hash differs")
    records = freeze.get("files")
    if not isinstance(records, list) or not records:
        raise FinalRepositoryFreezeError("checkpoint inventory is invalid")
    paths = []
    for item in records:
        if not isinstance(item, Mapping) or set(item) != {"mode", "path", "sha256", "size_bytes"}:
            raise FinalRepositoryFreezeError("checkpoint record is malformed")
        path = item.get("path")
        if not isinstance(path, str):
            raise FinalRepositoryFreezeError("checkpoint path is malformed")
        _safe_relative(path)
        _reject_forbidden_path(path)
        if path == FINAL_REPOSITORY_FREEZE_PATH:
            raise FinalRepositoryFreezeError("freeze cannot inventory itself")
        if type(item.get("mode")) is not int or item["mode"] < 0:
            raise FinalRepositoryFreezeError("checkpoint mode is malformed")
        if type(item.get("size_bytes")) is not int or item["size_bytes"] < 0:
            raise FinalRepositoryFreezeError("checkpoint size is malformed")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise FinalRepositoryFreezeError("checkpoint hash is malformed")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise FinalRepositoryFreezeError("checkpoint inventory ordering differs")
    inventory_hash = _sha256_bytes(_canonical_bytes(records))
    if (
        freeze.get("checkpoint_file_count") != len(records)
        or freeze.get("checkpoint_total_bytes") != sum(item["size_bytes"] for item in records)
        or freeze.get("checkpoint_inventory_hash") != inventory_hash
        or freeze.get("staged_candidate_hash") != inventory_hash
    ):
        raise FinalRepositoryFreezeError("checkpoint inventory totals differ")
    suite = freeze.get("test_suite")
    if not isinstance(suite, Mapping) or set(suite) != {"errors", "failures", "non_interactive", "passed", "skipped"}:
        raise FinalRepositoryFreezeError("test suite evidence is malformed")
    if suite.get("non_interactive") is not True or suite.get("failures") != 0 or suite.get("errors") != 0:
        raise FinalRepositoryFreezeError("test suite evidence is not clean")
    for name in ("passed", "skipped", "failures", "errors"):
        if type(suite.get(name)) is not int or suite[name] < 0:
            raise FinalRepositoryFreezeError("test suite count is malformed")
    if freeze.get("branch") != "feature/m2-b0-provider-critic-inert-core":
        raise FinalRepositoryFreezeError("checkpoint branch differs")
    parent_head = freeze.get("parent_head")
    if not isinstance(parent_head, str) or len(parent_head) != 40 or any(
        char not in "0123456789abcdef" for char in parent_head
    ):
        raise FinalRepositoryFreezeError("parent HEAD is malformed")
    if ARCHITECT_HANDOFF_MANIFEST_PATH not in paths:
        raise FinalRepositoryFreezeError("architect handoff manifest is not inventoried")
    return supplied


def verify_inventory_files(repository_root: str | Path, records: Sequence[Mapping[str, Any]]) -> None:
    root = Path(repository_root).resolve(strict=True)
    expected = {item["path"]: dict(item) for item in records}
    actual = {item["path"]: item for item in build_checkpoint_inventory(root)}
    if actual != expected:
        raise FinalRepositoryFreezeError("checkpoint inventory does not match repository files")


def verify_final_repository_freeze(
    freeze_path: str | Path,
    *,
    repository_root: str | Path,
) -> str:
    path = Path(freeze_path)
    if path.is_symlink() or not path.is_file():
        raise FinalRepositoryFreezeError("final freeze path is not a regular file")
    try:
        freeze = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FinalRepositoryFreezeError("final freeze is not strict UTF-8 JSON") from exc
    supplied = verify_final_repository_freeze_data(freeze)
    verify_inventory_files(repository_root, freeze["files"])
    root = Path(repository_root).resolve(strict=True)
    if freeze.get("architect_handoff_manifest_hash") != verify_architect_handoff_manifest(
        root / ARCHITECT_HANDOFF_MANIFEST_PATH,
        repository_root=root,
    ):
        raise FinalRepositoryFreezeError("architect handoff binding differs")
    unix_freeze = _load_json(root, UNIX_R1_FREEZE_PATH)
    corpus = _load_json(root, CORPUS_MANIFEST_PATH)
    index = _load_json(root, RETRIEVAL_INDEX_PATH)
    unix_hat = _load_json(root, UNIX_HAT_DESCRIPTOR_PATH)
    expected_bindings = {
        "corpus_manifest_hash": corpus.get("manifest_hash"),
        "retrieval_index_hash": index.get("index_hash"),
        "unix_r1_freeze_hash": unix_freeze.get("freeze_manifest_hash"),
    }
    if any(freeze.get(field) != value for field, value in expected_bindings.items()):
        raise FinalRepositoryFreezeError("upstream artifact binding differs")
    if freeze.get("unix_hat_identity") != {
        "descriptor_hash": unix_hat.get("descriptor_hash"),
        "hat_id": unix_hat.get("hat_id"),
        "path": UNIX_HAT_DESCRIPTOR_PATH,
    }:
        raise FinalRepositoryFreezeError("UNIX Hat identity differs")
    expected_hats = {
        name: {"identity_hash": _identity(root, paths), "paths": list(paths)}
        for name, paths in sorted(_HAT_IDENTITY_PATHS.items())
    }
    if freeze.get("hat_identities") != expected_hats:
        raise FinalRepositoryFreezeError("protected Hat identity differs")
    if freeze.get("authority_boundary_test_identity") != _identity(root, _AUTHORITY_TEST_PATHS):
        raise FinalRepositoryFreezeError("authority boundary test identity differs")
    if freeze.get("static_capability_test_identity") != _identity(root, _STATIC_TEST_PATHS):
        raise FinalRepositoryFreezeError("static capability test identity differs")
    return supplied


def materialize_final_repository_freeze(
    repository_root: str | Path,
    *,
    branch: str,
    parent_head: str,
    passed: int,
    skipped: int,
    failures: int = 0,
    errors: int = 0,
    replace: bool = False,
) -> Path:
    root = Path(repository_root).resolve(strict=True)
    destination = root / FINAL_REPOSITORY_FREEZE_PATH
    payload = serialize_final_repository_freeze(
        build_final_repository_freeze(
            root,
            branch=branch,
            parent_head=parent_head,
            passed=passed,
            skipped=skipped,
            failures=failures,
            errors=errors,
        )
    )
    if not destination.parent.exists():
        destination.parent.mkdir(mode=0o755)
    if destination.parent.is_symlink() or not destination.parent.is_dir():
        raise FinalRepositoryFreezeError("final freeze output root is invalid")
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_file():
            raise FinalRepositoryFreezeError("existing final freeze path is invalid")
        if destination.read_bytes() == payload:
            return destination
        if not replace:
            raise FinalRepositoryFreezeError("existing final freeze differs")
        with destination.open("wb") as handle:
            handle.write(payload)
        return destination
    with destination.open("xb") as handle:
        handle.write(payload)
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or verify the inert AOIA-Core repository freeze.")
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--branch")
    parser.add_argument("--parent-head")
    parser.add_argument("--passed", type=int)
    parser.add_argument("--skipped", type=int)
    parser.add_argument("--replace", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repository_root)
    if args.operation == "build":
        if args.branch is None or args.parent_head is None or args.passed is None or args.skipped is None:
            raise FinalRepositoryFreezeError("build requires branch, parent HEAD, passed, and skipped")
        path = materialize_final_repository_freeze(
            root,
            branch=args.branch,
            parent_head=args.parent_head,
            passed=args.passed,
            skipped=args.skipped,
            replace=args.replace,
        )
    else:
        path = root / FINAL_REPOSITORY_FREEZE_PATH
    freeze_hash = verify_final_repository_freeze(path, repository_root=root)
    print(json.dumps({"authority_status": NON_AUTHORITATIVE, "freeze_id": FINAL_FREEZE_ID, "freeze_manifest_hash": freeze_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
