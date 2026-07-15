from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.unix_full_validation_freeze import (
    APPROVED_SOURCE_INVENTORY_SCHEMA_VERSION,
    DISCOVERY_INVENTORY_SCHEMA_VERSION,
    EXPECTED_VISIBLE_DEMO_MANIFEST_HASH,
    SUPERSEDES_FREEZE_MANIFEST_HASH,
    UnixFullValidationError,
    build_approved_corpus_source_inventory,
    build_corpus_discovery_inventory,
    verify_approved_corpus_source_inventory,
    verify_corpus_discovery_inventory,
    verify_unix_unit_upstream,
)
from runtime.visible_unix_prototype import (
    EXPECTED_CORPUS_MANIFEST_HASH,
    EXPECTED_HAT_DESCRIPTOR_HASH,
    EXPECTED_INDEX_MANIFEST_HASH,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data/unix_corpus_ingestion_1b"
SCANNER_PATH = (
    "knowledge/languages/python/audits/duplicate_conflict_scan/"
    "scan_python_knowledge_duplicates.py"
)
INERT = {
    "authority_status": "NON_AUTHORITATIVE",
    "can_approve": False,
    "can_dispatch": False,
    "can_execute": False,
    "can_write": False,
    "gate_satisfied": False,
}


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class CleanupCorpusInventoryBoundary1ATests(unittest.TestCase):
    def test_persistent_approved_inventory_contains_only_selected_source(self) -> None:
        inventory = read_json(DATA_ROOT / "approved_source_inventory.json")
        self.assertEqual(APPROVED_SOURCE_INVENTORY_SCHEMA_VERSION, inventory["schema_version"])
        self.assertEqual(1, inventory["source_count"])
        self.assertEqual(797_025, inventory["total_source_bytes"])
        self.assertEqual(
            ["runtime/knowledge/extracted/linux_master_library_v1.txt"],
            [source["repository_relative_path"] for source in inventory["sources"]],
        )
        self.assertEqual(
            inventory["approved_inventory_hash"],
            verify_approved_corpus_source_inventory(PROJECT_ROOT, inventory),
        )

    def test_scanner_is_non_selected_tooling_in_discovery_inventory(self) -> None:
        inventory = read_json(DATA_ROOT / "source_inventory.json")
        self.assertEqual(DISCOVERY_INVENTORY_SCHEMA_VERSION, inventory["schema_version"])
        scanner = [row for row in inventory["files"] if row["path"] == SCANNER_PATH]
        self.assertEqual(1, len(scanner))
        self.assertEqual("TOOLING", scanner[0]["classification"])
        self.assertFalse(scanner[0]["selected"])
        self.assertEqual(
            inventory["discovery_inventory_hash"],
            verify_corpus_discovery_inventory(inventory),
        )

    def test_changing_tooling_changes_discovery_but_not_approved_identity(self) -> None:
        source = {
            **INERT,
            "bytes": 4,
            "classification": "APPROVED_EXTRACTED_SOURCE",
            "extension": ".txt",
            "file_type": "regular",
            "path": "runtime/knowledge/extracted/source.txt",
            "reason": "selected fixture source",
            "root": "/fixture/runtime/knowledge",
            "selected": True,
            "sha256": "a" * 64,
        }
        tooling = {
            **INERT,
            "bytes": 4,
            "classification": "TOOLING",
            "extension": ".py",
            "file_type": "regular",
            "path": SCANNER_PATH,
            "reason": "fixture tooling",
            "root": "/fixture/knowledge",
            "selected": False,
            "sha256": "b" * 64,
        }
        first = build_corpus_discovery_inventory(
            candidate_roots=(),
            files=(source, tooling),
            expected_corpus_defined=True,
            expected_corpus_matched=True,
        )
        changed_tooling = dict(tooling, bytes=5, sha256="c" * 64)
        second = build_corpus_discovery_inventory(
            candidate_roots=(),
            files=(source, changed_tooling),
            expected_corpus_defined=True,
            expected_corpus_matched=True,
        )
        approved_before = build_approved_corpus_source_inventory(PROJECT_ROOT)
        approved_after = build_approved_corpus_source_inventory(PROJECT_ROOT)
        self.assertNotEqual(first["discovery_inventory_hash"], second["discovery_inventory_hash"])
        self.assertEqual(approved_before, approved_after)
        self.assertEqual(
            EXPECTED_CORPUS_MANIFEST_HASH,
            read_json(DATA_ROOT / "intake/corpus_manifest.json")["manifest_hash"],
        )

    def test_changed_approved_source_bytes_fail_closed(self) -> None:
        with TemporaryDirectory(prefix="aoia-approved-source-boundary-") as temporary:
            root = Path(temporary)
            source = root / "runtime/knowledge/extracted/linux_master_library_v1.txt"
            manifest = root / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json"
            source.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            source.write_bytes(
                (PROJECT_ROOT / "runtime/knowledge/extracted/linux_master_library_v1.txt").read_bytes()
            )
            manifest.write_bytes((DATA_ROOT / "intake/corpus_manifest.json").read_bytes())
            expected = build_approved_corpus_source_inventory(root)
            self.assertEqual(
                expected["approved_inventory_hash"],
                verify_approved_corpus_source_inventory(root, expected),
            )
            source.write_bytes(source.read_bytes() + b"changed\n")
            with self.assertRaises(UnixFullValidationError) as raised:
                build_approved_corpus_source_inventory(root)
            self.assertEqual("APPROVED_INVENTORY_INVALID", raised.exception.status)

    def test_legacy_broad_inventory_is_not_silently_approved(self) -> None:
        legacy = read_json(DATA_ROOT / "source_inventory.json")
        legacy["schema_version"] = "unix-full-corpus-source-inventory-1b"
        with self.assertRaises(UnixFullValidationError) as raised:
            verify_corpus_discovery_inventory(legacy)
        self.assertEqual("DISCOVERY_INVENTORY_INVALID", raised.exception.status)
        with self.assertRaises(UnixFullValidationError):
            verify_approved_corpus_source_inventory(PROJECT_ROOT, legacy)

    def test_upstream_semantic_bindings_remain_unchanged(self) -> None:
        upstream = verify_unix_unit_upstream(PROJECT_ROOT)
        self.assertEqual(EXPECTED_CORPUS_MANIFEST_HASH, upstream.corpus_manifest_hash)
        self.assertEqual(EXPECTED_INDEX_MANIFEST_HASH, upstream.retrieval_index_hash)
        self.assertEqual(EXPECTED_HAT_DESCRIPTOR_HASH, upstream.unix_hat_descriptor_hash)
        self.assertEqual(EXPECTED_VISIBLE_DEMO_MANIFEST_HASH, upstream.visible_demo_manifest_hash)
        self.assertEqual(13, upstream.corpus_record_count)
        self.assertEqual(13, upstream.indexed_record_count)

    def test_freeze_revision_explicitly_supersedes_historical_evidence(self) -> None:
        historical = read_json(
            PROJECT_ROOT / "data/unix_full_validation_freeze_1a/freeze_manifest.json"
        )
        self.assertEqual(historical["freeze_manifest_hash"], SUPERSEDES_FREEZE_MANIFEST_HASH)
        self.assertEqual("NON_AUTHORITATIVE", historical["authority_status"])

    def test_inventory_metadata_never_gains_authority(self) -> None:
        for filename in ("approved_source_inventory.json", "source_inventory.json"):
            inventory = read_json(DATA_ROOT / filename)
            self.assertEqual("NON_AUTHORITATIVE", inventory["authority_status"])
            for field in ("can_approve", "can_dispatch", "can_execute", "can_write", "gate_satisfied"):
                self.assertFalse(inventory[field])


if __name__ == "__main__":
    unittest.main()
