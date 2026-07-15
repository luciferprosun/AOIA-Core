from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from runtime.knowledge.unix_corpus_ingestion import (
    AUTHORITY_FLAGS,
    UnixCorpusSecurityError,
    read_unix_corpus_manifest,
    reconcile_unix_corpus,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = REPOSITORY_ROOT / "runtime/knowledge"
MATERIALIZATION_ROOT = REPOSITORY_ROOT / "data/unix_corpus_ingestion_1b"
INTAKE_ROOT = MATERIALIZATION_ROOT / "intake"
SELECTED_SOURCE = "extracted/linux_master_library_v1.txt"
CANONICAL_PDF_HASH = (
    "7eab9450dd15cc5e1607c29d9fe3b19c4cf9854bb702f113534b6ec34a34dc03"
)
LEGACY_PDF_HASH = (
    "b8092eeabbfd80489d9e5ce8b49ba4d822aa83cc360da0a8f3c76276ac21d6b7"
)
INERT_FIELDS = {"authority_status": "NON_AUTHORITATIVE", **AUTHORITY_FLAGS}


def _canonical_line(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_bytes(value: object) -> bytes:
    return _canonical_line(value)[:-1]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_canonical(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict) or _canonical_line(payload) != raw:
        raise AssertionError(f"not canonical JSON: {path}")
    return payload


def _inspect_zip_metadata(
    archive: Path,
    *,
    max_members: int = 32,
    max_member_bytes: int = 512 * 1024,
    max_total_bytes: int = 1024 * 1024,
    max_compression_ratio: float = 100.0,
) -> dict[str, object]:
    """Test-side bounded metadata inspection; it never extracts archive members."""

    seen: set[str] = set()
    total = 0
    members: list[dict[str, object]] = []
    with zipfile.ZipFile(archive, "r") as bundle:
        infos = bundle.infolist()
        if len(infos) > max_members:
            raise ValueError("archive member limit exceeded")
        for info in infos:
            name = info.filename
            normalized = PurePosixPath(name)
            if (
                not name
                or name.startswith("/")
                or "\\" in name
                or any(part in {"", ".", ".."} for part in normalized.parts)
            ):
                raise ValueError("unsafe archive member path")
            if name in seen:
                raise ValueError("duplicate archive member path")
            seen.add(name)
            unix_mode = info.external_attr >> 16
            if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
                raise ValueError("archive symbolic link rejected")
            if info.file_size > max_member_bytes:
                raise ValueError("archive member size limit exceeded")
            total += info.file_size
            if total > max_total_bytes:
                raise ValueError("archive total size limit exceeded")
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > max_compression_ratio:
                raise ValueError("archive compression ratio limit exceeded")
            members.append(
                {
                    "path": name,
                    "uncompressed_bytes": info.file_size,
                    "compressed_bytes": info.compress_size,
                }
            )
    return {
        "member_count": len(members),
        "uncompressed_bytes": total,
        "members": sorted(members, key=lambda item: str(item["path"])),
    }


class UnixFullCorpusMaterialization1ATests(unittest.TestCase):
    maxDiff = None

    def test_persistent_materialization_has_all_required_closure_artifacts(self) -> None:
        expected = {
            "approved_source_inventory.json",
            "source_inventory.json",
            "materialization_plan.json",
            "ingestion_state.json",
            "validation_report.json",
            "intake",
        }
        self.assertEqual(expected, {path.name for path in MATERIALIZATION_ROOT.iterdir()})
        self.assertEqual(
            {"corpus_manifest.json", "records", "quarantine"},
            {path.name for path in INTAKE_ROOT.iterdir()},
        )

    def test_project_manifest_defines_and_matches_canonical_source_relationship(self) -> None:
        manifest_text = (
            KNOWLEDGE_ROOT / "manifests/library_manifest.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("canonical_source: runtime/knowledge/source/linux_master_library_v1.pdf", manifest_text)
        self.assertIn(CANONICAL_PDF_HASH, manifest_text)
        self.assertIn(LEGACY_PDF_HASH, manifest_text)
        self.assertIn("runtime/knowledge/extracted/linux_master_library_v1.txt", manifest_text)
        self.assertIn("runtime/knowledge/extracted/linux_master_library_v1.md", manifest_text)
        self.assertEqual(
            CANONICAL_PDF_HASH,
            _sha256_file(KNOWLEDGE_ROOT / "source/linux_master_library_v1.pdf"),
        )
        self.assertEqual(
            LEGACY_PDF_HASH,
            _sha256_file(KNOWLEDGE_ROOT / "source/RHCSA_Command_Library (1).pdf"),
        )

    def test_discovery_inventory_is_canonical_hash_bound_and_complete(self) -> None:
        inventory = _read_canonical(MATERIALIZATION_ROOT / "source_inventory.json")
        recorded_hash = inventory.pop("discovery_inventory_hash")
        self.assertEqual(_sha256_bytes(_canonical_bytes(inventory)), recorded_hash)
        self.assertEqual("unix-corpus-discovery-inventory-1b1", inventory["schema_version"])
        paths = [str(row["path"]) for row in inventory["files"]]
        self.assertEqual(sorted(paths), paths)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual([], inventory["archives"])
        self.assertTrue(inventory["expected_corpus_defined"])
        self.assertTrue(inventory["expected_corpus_matched"])
        for row in inventory["files"]:
            self.assertEqual(INERT_FIELDS["authority_status"], row["authority_status"])
            for field, expected in AUTHORITY_FLAGS.items():
                self.assertIs(row[field], expected)
            if row["file_type"] == "regular":
                path = REPOSITORY_ROOT / str(row["path"])
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(_sha256_file(path), row["sha256"])

    def test_approved_source_inventory_contains_only_selected_corpus_identity(self) -> None:
        inventory = _read_canonical(MATERIALIZATION_ROOT / "approved_source_inventory.json")
        recorded_hash = inventory.pop("approved_inventory_hash")
        self.assertEqual(_sha256_bytes(_canonical_bytes(inventory)), recorded_hash)
        self.assertEqual("unix-approved-corpus-source-inventory-1b1", inventory["schema_version"])
        self.assertEqual(1, inventory["source_count"])
        self.assertEqual(797_025, inventory["total_source_bytes"])
        self.assertEqual(
            ["runtime/knowledge/extracted/linux_master_library_v1.txt"],
            [source["repository_relative_path"] for source in inventory["sources"]],
        )
        source = inventory["sources"][0]
        self.assertEqual(_sha256_file(KNOWLEDGE_ROOT / SELECTED_SOURCE), source["sha256"])
        self.assertEqual("NON_AUTHORITATIVE", source["authority_status"])

    def test_source_selection_excludes_indexes_fixtures_legacy_and_duplicates(self) -> None:
        inventory = _read_canonical(MATERIALIZATION_ROOT / "source_inventory.json")
        by_path = {str(row["path"]): row for row in inventory["files"]}
        selected = [row for row in inventory["files"] if row["selected"]]
        self.assertEqual(
            ["runtime/knowledge/extracted/linux_master_library_v1.txt"],
            [row["path"] for row in selected],
        )
        expected_classes = {
            "runtime/knowledge/extracted/linux_master_library_v1.md": "DUPLICATE",
            "runtime/knowledge/index/command_index.json": "GENERATED_INDEX",
            "runtime/knowledge/canonical/rhcsa_commands.json": "GENERATED_CANONICAL_RECORD",
            "runtime/knowledge/raw/rhcsa_raw.txt": "LEGACY_ARTIFACT",
            "corpus/shell_cases.jsonl": "FIXTURE",
            "knowledge/hats/hat_003_python/machine_readable/knowledge_cards.jsonl": "UNSUPPORTED",
            "archive/forensic_exports/reports_forensic_export/source_export/runtime/knowledge/extracted/linux_master_library_v1.txt": "DUPLICATE",
        }
        for path, classification in expected_classes.items():
            self.assertEqual(classification, by_path[path]["classification"])
            self.assertFalse(by_path[path]["selected"])
        self.assertNotIn("UNRESOLVED", {row["classification"] for row in inventory["files"]})

    def test_selected_duplicate_copies_have_one_hash_and_are_not_double_ingested(self) -> None:
        inventory = _read_canonical(MATERIALIZATION_ROOT / "source_inventory.json")
        selected = next(row for row in inventory["files"] if row["selected"])
        copies = [
            row
            for row in inventory["files"]
            if row.get("sha256") == selected["sha256"]
        ]
        self.assertEqual(4, len(copies))
        self.assertEqual(1, sum(bool(row["selected"]) for row in copies))
        self.assertEqual(3, sum(row["classification"] == "DUPLICATE" for row in copies))

    def test_full_dataset_exceeds_the_three_record_fixture_and_matches_physical_outputs(self) -> None:
        manifest = read_unix_corpus_manifest(INTAKE_ROOT)
        records = sorted((INTAKE_ROOT / "records").glob("*.json"))
        quarantine = sorted((INTAKE_ROOT / "quarantine").glob("*.json"))
        self.assertEqual(1, manifest.accepted_source_count)
        self.assertEqual(13, manifest.record_count)
        self.assertGreater(manifest.record_count, 3)
        self.assertEqual(manifest.record_count, len(records))
        self.assertEqual(0, manifest.quarantined_source_count)
        self.assertEqual([], quarantine)
        self.assertEqual(set(manifest.record_ids), {path.stem for path in records})

    def test_each_materialized_record_has_recalculable_hash_and_exact_provenance(self) -> None:
        selected = KNOWLEDGE_ROOT / SELECTED_SOURCE
        source_hash = _sha256_file(selected)
        with selected.open("rb") as stream:
            line_count = sum(1 for _ in stream)
        seen: dict[str, str] = {}
        total_bytes = 0
        for path in sorted((INTAKE_ROOT / "records").glob("*.json")):
            payload = _read_canonical(path)
            content = str(payload["content"])
            self.assertEqual(_sha256_bytes(content.encode("utf-8")), payload["content_hash"])
            material = dict(payload)
            record_id = material.pop("record_id")
            self.assertEqual(_sha256_bytes(_canonical_bytes(material)), record_id)
            self.assertEqual(path.stem, record_id)
            self.assertEqual(SELECTED_SOURCE, payload["source_path"])
            self.assertEqual(source_hash, payload["source_hash"])
            locator = str(payload["locator"]).split(";", 1)[0]
            start, end = (int(item) for item in locator.removeprefix("lines:").split("-"))
            self.assertGreaterEqual(start, 1)
            self.assertGreaterEqual(end, start)
            self.assertLessEqual(end, line_count)
            if record_id in seen:
                self.assertEqual(seen[record_id], content)
            seen[record_id] = content
            total_bytes += len(content.encode("utf-8"))
        report = _read_canonical(MATERIALIZATION_ROOT / "validation_report.json")
        self.assertEqual(total_bytes, report["total_normalized_bytes"])
        self.assertEqual(797008, total_bytes)

    def test_manifest_state_plan_and_report_verify_independently_and_are_inert(self) -> None:
        manifest = _read_canonical(INTAKE_ROOT / "corpus_manifest.json")
        recorded_manifest_hash = manifest.pop("manifest_hash")
        self.assertEqual(_sha256_bytes(_canonical_bytes(manifest)), recorded_manifest_hash)
        for filename, hash_field in (
            ("materialization_plan.json", "plan_hash"),
            ("ingestion_state.json", "state_hash"),
            ("validation_report.json", "validation_hash"),
        ):
            payload = _read_canonical(MATERIALIZATION_ROOT / filename)
            recorded = payload.pop(hash_field)
            self.assertEqual(_sha256_bytes(_canonical_line(payload)), recorded)
            self.assertEqual("NON_AUTHORITATIVE", payload["authority_status"])
            for field, expected in AUTHORITY_FLAGS.items():
                self.assertIs(payload[field], expected)
        report = _read_canonical(MATERIALIZATION_ROOT / "validation_report.json")
        self.assertTrue(report["manifest_independently_verified"])
        self.assertTrue(report["resume_without_duplicates"])
        self.assertTrue(report["deterministic_replay_match"])
        self.assertEqual(0, report["resume_replay_added_records"])
        self.assertEqual([], report["unresolved_candidate_files"])

    def test_actual_resume_is_byte_identical_and_adds_no_records(self) -> None:
        before = {
            path.relative_to(MATERIALIZATION_ROOT).as_posix(): path.read_bytes()
            for path in MATERIALIZATION_ROOT.rglob("*")
            if path.is_file()
        }
        result = reconcile_unix_corpus(
            KNOWLEDGE_ROOT,
            INTAKE_ROOT,
            source_paths=(SELECTED_SOURCE,),
        )
        after = {
            path.relative_to(MATERIALIZATION_ROOT).as_posix(): path.read_bytes()
            for path in MATERIALIZATION_ROOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual("UNCHANGED", result.status)
        self.assertEqual(0, result.created_record_count)
        self.assertEqual(0, result.created_quarantine_count)
        self.assertFalse(result.manifest_changed)
        self.assertEqual(before, after)

    def test_clean_replay_is_deterministically_identical(self) -> None:
        expected_manifest = (INTAKE_ROOT / "corpus_manifest.json").read_bytes()
        expected_records = {
            path.name: path.read_bytes()
            for path in sorted((INTAKE_ROOT / "records").glob("*.json"))
        }
        with tempfile.TemporaryDirectory(prefix="aoia-full-corpus-test-replay-") as temporary:
            replay_root = Path(temporary) / "intake"
            replay = reconcile_unix_corpus(
                KNOWLEDGE_ROOT,
                replay_root,
                source_paths=(SELECTED_SOURCE,),
            )
            replay_records = {
                path.name: path.read_bytes()
                for path in sorted((replay_root / "records").glob("*.json"))
            }
            self.assertEqual("CREATED", replay.status)
            self.assertEqual(expected_manifest, (replay_root / "corpus_manifest.json").read_bytes())
            self.assertEqual(expected_records, replay_records)

    def test_changed_source_fixture_creates_new_identity_without_mutating_actual_corpus(self) -> None:
        actual_hash = _sha256_file(KNOWLEDGE_ROOT / SELECTED_SOURCE)
        with tempfile.TemporaryDirectory(prefix="aoia-full-corpus-changed-") as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            fixture = source / "fixture.txt"
            fixture.write_text("first version\n", encoding="utf-8")
            first = reconcile_unix_corpus(source, root / "intake")
            fixture.write_text("changed version\n", encoding="utf-8")
            changed = reconcile_unix_corpus(source, root / "intake")
            self.assertEqual("UPDATED", changed.status)
            self.assertTrue(set(first.manifest.record_ids).isdisjoint(changed.manifest.record_ids))
            self.assertEqual(2, len(list((root / "intake/records").glob("*.json"))))
        self.assertEqual(actual_hash, _sha256_file(KNOWLEDGE_ROOT / SELECTED_SOURCE))

    def test_command_and_authority_looking_actual_content_remains_inert(self) -> None:
        source_text = (KNOWLEDGE_ROOT / SELECTED_SOURCE).read_text(encoding="utf-8").casefold()
        self.assertTrue(any(term in source_text for term in ("curl", "wget", "rm -rf")))
        self.assertTrue(any(term in source_text for term in ("write", "execute", "provider")))
        with tempfile.TemporaryDirectory(prefix="aoia-full-corpus-inert-") as temporary:
            with mock.patch.object(subprocess, "run", side_effect=AssertionError("no process")), mock.patch.object(
                os, "system", side_effect=AssertionError("no shell")
            ):
                result = reconcile_unix_corpus(
                    KNOWLEDGE_ROOT,
                    Path(temporary) / "intake",
                    source_paths=(SELECTED_SOURCE,),
                )
        self.assertEqual(13, result.manifest.record_count)
        self.assertEqual("NON_AUTHORITATIVE", result.manifest.authority_status)

    def test_output_root_escape_and_overlap_remain_blocked(self) -> None:
        with self.assertRaises(UnixCorpusSecurityError):
            reconcile_unix_corpus(
                KNOWLEDGE_ROOT,
                KNOWLEDGE_ROOT / "generated",
                source_paths=(SELECTED_SOURCE,),
            )
        self.assertFalse((KNOWLEDGE_ROOT / "generated").exists())

    def test_actual_discovery_found_no_compressed_corpus_archive(self) -> None:
        inventory = _read_canonical(MATERIALIZATION_ROOT / "source_inventory.json")
        self.assertEqual([], inventory["archives"])

    def test_bounded_archive_metadata_inventory_accepts_safe_members_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-archive-safe-") as temporary:
            archive = Path(temporary) / "corpus.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
                bundle.writestr("unix/one.txt", "one")
                bundle.writestr("unix/two.jsonl", '{"id":2}\n')
            metadata = _inspect_zip_metadata(archive)
            self.assertEqual(2, metadata["member_count"])
            self.assertEqual(12, metadata["uncompressed_bytes"])
            self.assertFalse((Path(temporary) / "unix").exists())

    def test_archive_traversal_absolute_duplicate_and_symlink_members_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-archive-reject-") as temporary:
            root = Path(temporary)
            cases: list[Path] = []
            for index, member in enumerate(("../escape.txt", "/absolute.txt", "windows\\escape.txt")):
                archive = root / f"unsafe-{index}.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    bundle.writestr(member, "unsafe")
                cases.append(archive)
            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as bundle:
                    bundle.writestr("same.txt", "one")
                    bundle.writestr("same.txt", "two")
            cases.append(duplicate)
            symlink = root / "symlink.zip"
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(symlink, "w") as bundle:
                bundle.writestr(info, "target")
            cases.append(symlink)
            for archive in cases:
                with self.subTest(archive=archive.name):
                    with self.assertRaises(ValueError):
                        _inspect_zip_metadata(archive)

    def test_archive_member_total_and_compression_ratio_limits_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aoia-archive-limits-") as temporary:
            root = Path(temporary)
            oversized = root / "oversized.zip"
            with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_STORED) as bundle:
                bundle.writestr("large.txt", b"x" * 128)
            with self.assertRaises(ValueError):
                _inspect_zip_metadata(oversized, max_member_bytes=64)
            bomb = root / "ratio.zip"
            with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
                bundle.writestr("compressible.txt", b"A" * 100_000)
            with self.assertRaises(ValueError):
                _inspect_zip_metadata(bomb, max_compression_ratio=2.0)

    def test_full_corpus_boundary_has_no_retrieval_routing_hat_provider_or_writer_integration(self) -> None:
        source = (
            REPOSITORY_ROOT / "runtime/knowledge/unix_corpus_ingestion.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "runtime.retrieval",
            "knowledge_router",
            "memory_hat",
            "runtime.providers",
            "human_decision",
            "sandbox_artifact_runner",
            "controlled_patch_apply",
            "subprocess",
            "socket",
            "requests",
        )
        self.assertEqual([], [token for token in forbidden if token in source])


if __name__ == "__main__":
    unittest.main()
