"""Dependency-free PEP 660 backend for the AOIA-Core editable handoff.

The backend creates only an editable wheel in pip's caller-selected temporary
directory. It performs no network access and writes nothing into the source
repository.
"""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Mapping, Sequence
import zipfile


NAME = "aoia-core"
DIST_NAME = "aoia_core"
VERSION = "0.1.0"
DIST_INFO = f"{DIST_NAME}-{VERSION}.dist-info"
WHEEL_NAME = f"{DIST_NAME}-{VERSION}-0.editable-py3-none-any.whl"
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _metadata_files() -> dict[str, bytes]:
    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {NAME}\n"
        f"Version: {VERSION}\n"
        "Summary: Local-first, human-controlled epistemic control system development prototype\n"
        "Requires-Python: >=3.12\n"
        "\n"
    ).encode("utf-8")
    wheel = (
        "Wheel-Version: 1.0\n"
        "Generator: aoia-build-backend-1a\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
        "\n"
    ).encode("utf-8")
    entry_points = (
        "[console_scripts]\n"
        "aoia-knowledge-hub = runtime.developer_entrypoints:knowledge_hub_main\n"
        "aoia-knowledge-query = runtime.developer_entrypoints:knowledge_query_main\n"
        "aoia-offline-prototype = runtime.developer_entrypoints:offline_prototype_main\n"
        "aoia-smoke-test = runtime.developer_entrypoints:smoke_test_main\n"
        "aoia-verify-artifacts = runtime.developer_entrypoints:verify_artifacts_main\n"
    ).encode("utf-8")
    return {
        f"{DIST_INFO}/METADATA": metadata,
        f"{DIST_INFO}/WHEEL": wheel,
        f"{DIST_INFO}/entry_points.txt": entry_points,
    }


def _record_line(path: str, payload: bytes) -> str:
    encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
    return f"{path},sha256={encoded},{len(payload)}"


def _wheel_payloads() -> dict[str, bytes]:
    root = _project_root()
    editable_paths = f"{root}\n{root / 'runtime'}\n".encode("utf-8")
    payloads = {"aoia_core_editable.pth": editable_paths, **_metadata_files()}
    record_path = f"{DIST_INFO}/RECORD"
    record = "\n".join(
        [*(_record_line(path, payload) for path, payload in sorted(payloads.items())), f"{record_path},,"]
    ) + "\n"
    return {**payloads, record_path: record.encode("utf-8")}


def _write_zip_member(archive: zipfile.ZipFile, path: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(path, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, payload)


def get_requires_for_build_editable(config_settings: Mapping[str, object] | None = None) -> list[str]:
    return []


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: Mapping[str, object] | None = None,
) -> str:
    destination = Path(metadata_directory) / DIST_INFO
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    for archive_path, payload in sorted(_metadata_files().items()):
        relative = Path(archive_path).relative_to(DIST_INFO)
        target = destination / relative
        with target.open("xb") as handle:
            handle.write(payload)
    return DIST_INFO


def build_editable(
    wheel_directory: str,
    config_settings: Mapping[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    destination = Path(wheel_directory)
    if not destination.is_dir() or destination.is_symlink():
        raise ValueError("wheel directory must be an existing regular directory")
    wheel_path = destination / WHEEL_NAME
    if wheel_path.exists() or wheel_path.is_symlink():
        raise ValueError("editable wheel path already exists")
    with zipfile.ZipFile(wheel_path, mode="x") as archive:
        for archive_path, payload in sorted(_wheel_payloads().items()):
            _write_zip_member(archive, archive_path, payload)
    return WHEEL_NAME


__all__: Sequence[str] = (
    "build_editable",
    "get_requires_for_build_editable",
    "prepare_metadata_for_build_editable",
)
