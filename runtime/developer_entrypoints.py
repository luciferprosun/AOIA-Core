"""Stable, inert developer entrypoints for the AOIA-Core handoff."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Sequence

from runtime.architect_handoff_manifest import (
    ARCHITECT_HANDOFF_MANIFEST_PATH,
    verify_architect_handoff_manifest,
)
from runtime.final_repository_freeze import (
    FINAL_FREEZE_ID as FINAL_REPOSITORY_FREEZE_ID,
    FINAL_REPOSITORY_FREEZE_PATH,
    verify_final_repository_freeze,
)
from runtime.unix_full_validation_freeze import (
    verify_unix_full_validation_freeze,
    verify_unix_unit_upstream,
)
from runtime.visible_unix_prototype import (
    VisibleUnixPrototypeError,
    VisibleUnixUpstreamPaths,
    materialize_visible_unix_demo,
    verify_visible_unix_demo,
)

NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
CURRENT_FREEZE_ID = "aoia-unix-unit-1a-r1"
CURRENT_FREEZE_PATH = "data/unix_full_validation_freeze_1a_r1"
CURRENT_VISIBLE_DEMO_PATH = "data/visible_unix_prototype_1a"
_AUTHORITY_FLAGS = {
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
}


class DeveloperEntrypointError(ValueError):
    """Fail-closed entrypoint validation error."""


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    for component in (absolute, *absolute.parents):
        if component.exists() and component.is_symlink():
            raise DeveloperEntrypointError("symbolic-link path components are forbidden")


def _repository_root(value: str | Path) -> Path:
    supplied = Path(value)
    if not supplied.is_absolute():
        supplied = Path.cwd() / supplied
    _reject_symlink_components(supplied)
    try:
        root = supplied.resolve(strict=True)
    except OSError as exc:
        raise DeveloperEntrypointError("repository root does not exist") from exc
    if not root.is_dir() or root.is_symlink() or not (root / "pyproject.toml").is_file():
        raise DeveloperEntrypointError("repository root is invalid")
    return root


def _explicit_new_output_root(value: str | Path) -> tuple[Path, Path]:
    supplied = Path(value)
    if not supplied.is_absolute() or ".." in supplied.parts:
        raise DeveloperEntrypointError("output root must be absolute and traversal-free")
    _reject_symlink_components(supplied)
    try:
        parent = supplied.parent.resolve(strict=True)
    except OSError as exc:
        raise DeveloperEntrypointError("output parent must already exist") from exc
    if not parent.is_dir() or parent.is_symlink():
        raise DeveloperEntrypointError("output parent is invalid")
    candidate = parent / supplied.name
    if candidate.exists() or candidate.is_symlink():
        raise DeveloperEntrypointError("output root must not already exist")
    return candidate, parent


def _visible_paths(root: Path) -> VisibleUnixUpstreamPaths:
    return VisibleUnixUpstreamPaths(
        corpus_manifest_path=root / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
        records_path=root / "data/unix_corpus_ingestion_1b/intake/records",
        index_root=root / "data/unix_retrieval_adapter_1a/index",
        hat_descriptor_path=root / "data/unix_hat_routing_1a/unix_hat_descriptor.json",
        routing_policy_path=root / "data/unix_hat_routing_1a/routing_policy_manifest.json",
        benchmark_path=root / "data/unix_retrieval_adapter_1a/benchmark.json",
    )


def verify_current_artifacts(repository_root: str | Path) -> dict[str, Any]:
    """Verify retained artifacts without repairing or materializing them."""

    root = _repository_root(repository_root)
    handoff_hash = verify_architect_handoff_manifest(
        root / ARCHITECT_HANDOFF_MANIFEST_PATH,
        repository_root=root,
    )
    upstream = verify_unix_unit_upstream(root)
    demo = verify_visible_unix_demo(root / CURRENT_VISIBLE_DEMO_PATH, paths=_visible_paths(root))
    if not demo.valid:
        raise DeveloperEntrypointError(f"visible prototype verification failed: {demo.status}")
    freeze = verify_unix_full_validation_freeze(root / CURRENT_FREEZE_PATH, repository_root=root)
    if not freeze.valid:
        raise DeveloperEntrypointError(f"freeze verification failed: {freeze.status}")
    repository_freeze_hash = verify_final_repository_freeze(
        root / FINAL_REPOSITORY_FREEZE_PATH,
        repository_root=root,
    )
    return {
        "architect_handoff_manifest_hash": handoff_hash,
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "corpus_manifest_hash": upstream.corpus_manifest_hash,
        "freeze_id": CURRENT_FREEZE_ID,
        "freeze_manifest_hash": freeze.freeze_manifest_hash,
        "repository_freeze_id": FINAL_REPOSITORY_FREEZE_ID,
        "repository_freeze_manifest_hash": repository_freeze_hash,
        "retrieval_index_hash": upstream.retrieval_index_hash,
        "routing_policy_hash": upstream.routing_policy_hash,
        "sponsor_manifest_hash": freeze.sponsor_manifest_hash,
        "status": "VERIFIED",
        "unix_hat_descriptor_hash": upstream.unix_hat_descriptor_hash,
        "visible_demo_manifest_hash": demo.demo_manifest_hash,
    }


def run_developer_smoke_test(repository_root: str | Path) -> dict[str, Any]:
    """Import protected surfaces and verify the current handoff manifest."""

    root = _repository_root(repository_root)
    modules = (
        "runtime.artifact_preview",
        "runtime.retrieval.linux",
        "runtime.safety.bash_parser",
        "runtime.knowledge",
        "runtime.memory_hats.unix_hat",
        "runtime.developer_entrypoints",
    )
    for module_name in modules:
        importlib.import_module(module_name)
    handoff_hash = verify_architect_handoff_manifest(
        root / ARCHITECT_HANDOFF_MANIFEST_PATH,
        repository_root=root,
    )
    return {
        "architect_handoff_manifest_hash": handoff_hash,
        "authority_status": NON_AUTHORITATIVE,
        **_AUTHORITY_FLAGS,
        "entrypoints": [
            "aoia-knowledge-query",
            "aoia-offline-prototype",
            "aoia-smoke-test",
            "aoia-verify-artifacts",
        ],
        "imported_modules": list(modules),
        "status": "PASS",
    }


def _repository_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
    parser.add_argument("--repository-root", required=True)
    return parser


def offline_prototype_main(argv: Sequence[str] | None = None) -> int:
    parser = _repository_parser("Build the deterministic offline UNIX review prototype.")
    parser.add_argument("--output-root", required=True)
    try:
        args = parser.parse_args(argv)
        root = _repository_root(args.repository_root)
        output_root, allowed_parent = _explicit_new_output_root(args.output_root)
        result = materialize_visible_unix_demo(
            output_root,
            allowed_parent=allowed_parent,
            paths=_visible_paths(root),
        )
        print(_canonical_json({
            "authority_status": NON_AUTHORITATIVE,
            **_AUTHORITY_FLAGS,
            "demo_manifest_hash": result.demo_manifest_hash,
            "file_count": result.file_count,
            "output_root": str(output_root),
            "status": result.status,
            "total_bytes": result.total_bytes,
        }))
        return 0
    except (DeveloperEntrypointError, VisibleUnixPrototypeError, OSError, ValueError) as exc:
        print(_canonical_json({
            "authority_status": NON_AUTHORITATIVE,
            **_AUTHORITY_FLAGS,
            "reason": str(exc),
            "status": "FAILED_CLOSED",
        }))
        return 2


def verify_artifacts_main(argv: Sequence[str] | None = None) -> int:
    parser = _repository_parser("Read-only verification of retained AOIA-Core artifacts.")
    try:
        args = parser.parse_args(argv)
        print(_canonical_json(verify_current_artifacts(args.repository_root)))
        return 0
    except (DeveloperEntrypointError, OSError, UnicodeError, ValueError) as exc:
        print(_canonical_json({
            "authority_status": NON_AUTHORITATIVE,
            **_AUTHORITY_FLAGS,
            "reason": str(exc),
            "status": "FAILED_CLOSED",
        }))
        return 2


def smoke_test_main(argv: Sequence[str] | None = None) -> int:
    parser = _repository_parser("Bounded AOIA-Core import and handoff smoke test.")
    try:
        args = parser.parse_args(argv)
        print(_canonical_json(run_developer_smoke_test(args.repository_root)))
        return 0
    except (DeveloperEntrypointError, ImportError, OSError, UnicodeError, ValueError) as exc:
        print(_canonical_json({
            "authority_status": NON_AUTHORITATIVE,
            **_AUTHORITY_FLAGS,
            "reason": str(exc),
            "status": "FAILED_CLOSED",
        }))
        return 2


def knowledge_query_main(argv: Sequence[str] | None = None) -> int:
    """Enter the explicit Knowledge Hub without importing it for other CLIs."""

    from runtime.knowledge_modules.cli import main

    return main(argv)


__all__ = (
    "DeveloperEntrypointError",
    "knowledge_query_main",
    "offline_prototype_main",
    "run_developer_smoke_test",
    "smoke_test_main",
    "verify_artifacts_main",
    "verify_current_artifacts",
)
