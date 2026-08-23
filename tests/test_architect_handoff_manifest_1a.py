from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.architect_handoff_manifest import (
    ARCHITECT_HANDOFF_MANIFEST_PATH,
    FINAL_REPOSITORY_FREEZE_PATH,
    ArchitectHandoffManifestError,
    build_architect_handoff_manifest,
    serialize_architect_handoff_manifest,
    verify_architect_handoff_manifest,
    verify_architect_handoff_manifest_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / ARCHITECT_HANDOFF_MANIFEST_PATH


class ArchitectHandoffManifest1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = build_architect_handoff_manifest(PROJECT_ROOT)
        cls.serialized = serialize_architect_handoff_manifest(cls.manifest)

    def test_materialized_manifest_matches_complete_repository_handoff(self) -> None:
        manifest_hash = verify_architect_handoff_manifest(MANIFEST_PATH, repository_root=PROJECT_ROOT)

        self.assertEqual(self.manifest["manifest_hash"], manifest_hash)
        self.assertEqual(self.serialized, MANIFEST_PATH.read_bytes())

    def test_manifest_build_and_serialization_are_deterministic(self) -> None:
        rebuilt = build_architect_handoff_manifest(PROJECT_ROOT)

        self.assertEqual(self.manifest, rebuilt)
        self.assertEqual(self.serialized, serialize_architect_handoff_manifest(rebuilt))

    def test_manifest_is_explicitly_non_authoritative(self) -> None:
        self.assertEqual("NON_AUTHORITATIVE", self.manifest["authority_status"])
        for field in ("can_approve", "can_dispatch", "can_execute", "can_write"):
            with self.subTest(field=field):
                self.assertIs(self.manifest[field], False)

    def test_manifest_uses_only_portable_repository_relative_paths(self) -> None:
        decoded = self.serialized.decode("utf-8")
        self.assertNotIn("/home/l/", decoded)
        self.assertNotIn("/tmp/", decoded)
        for field in (
            "required_runtime_paths",
            "required_hat_paths",
            "required_corpus_paths",
            "required_generated_paths",
            "required_test_paths",
            "required_offline_prototype_paths",
            "regenerable_but_included_paths",
        ):
            for value in self.manifest[field]:
                with self.subTest(field=field, value=value):
                    self.assertFalse(Path(value).is_absolute())
                    self.assertNotIn("..", Path(value).parts)

    def test_all_protected_generated_roots_are_included(self) -> None:
        generated = set(self.manifest["required_generated_paths"])
        protected_roots = (
            "data/unix_corpus_ingestion_1b/",
            "data/unix_retrieval_adapter_1a/",
            "data/unix_hat_routing_1a/",
            "data/visible_unix_prototype_1a/",
            "data/unix_full_validation_freeze_1a/",
            "data/unix_full_validation_freeze_1a_r1/",
        )
        for prefix in protected_roots:
            with self.subTest(prefix=prefix):
                expected = {
                    path.relative_to(PROJECT_ROOT).as_posix()
                    for path in (PROJECT_ROOT / prefix).rglob("*")
                    if path.is_file()
                }
                self.assertTrue(expected)
                self.assertTrue(expected <= generated)
        self.assertIn(ARCHITECT_HANDOFF_MANIFEST_PATH, generated)
        self.assertIn(FINAL_REPOSITORY_FREEZE_PATH, generated)

    def test_runtime_hats_tests_corpus_and_offline_prototype_are_enumerated(self) -> None:
        self.assertIn("runtime/memory_hat_registry.py", self.manifest["required_runtime_paths"])
        self.assertIn("runtime/memory_hats/unix_hat.py", self.manifest["required_hat_paths"])
        self.assertIn("knowledge/hats/hat_003_python/README.md", self.manifest["required_hat_paths"])
        self.assertIn("runtime/knowledge/extracted/linux_master_library_v1.txt", self.manifest["required_corpus_paths"])
        self.assertIn("tests/test_unix_hat_and_routing_1a.py", self.manifest["required_test_paths"])
        self.assertIn("data/visible_unix_prototype_1a/index.html", self.manifest["required_offline_prototype_paths"])

    def test_r1_supersession_and_complete_r0_physical_evidence_are_retained(self) -> None:
        self.assertEqual("aoia-unix-unit-1a-r1", self.manifest["current_freeze_id"])
        self.assertEqual(
            "af5dcbb661fa7c48e1dc787f2ca556f09175e02a3a48911b6ced8b19c1405b00",
            self.manifest["current_freeze_manifest_hash"],
        )
        self.assertEqual(
            "59d058483d30ae60e290fa0a576920163eea0f7aef94ff28e4bf3671652dfa43",
            self.manifest["superseded_freeze_manifest_hash"],
        )
        generated = set(self.manifest["required_generated_paths"])
        self.assertIn("data/unix_full_validation_freeze_1a/freeze_manifest.json", generated)
        self.assertIn("data/unix_full_validation_freeze_1a_r1/freeze_manifest.json", generated)

        def artifact_hashes(root: Path) -> set[str]:
            return {
                hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob("*")
                if path.is_file()
            }

        r0_hashes = artifact_hashes(PROJECT_ROOT / "data/unix_full_validation_freeze_1a")
        r1_hashes = artifact_hashes(PROJECT_ROOT / "data/unix_full_validation_freeze_1a_r1")
        self.assertEqual(7, len(r0_hashes - r1_hashes))

    def test_file_inventory_totals_and_hashes_match(self) -> None:
        records = self.manifest["files"]
        self.assertEqual(len(records), self.manifest["file_count"])
        self.assertEqual(sum(item["size_bytes"] for item in records), self.manifest["total_bytes"])
        for item in records:
            with self.subTest(path=item["path"]):
                path = PROJECT_ROOT / item["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, item["size_bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
                self.assertNotEqual(ARCHITECT_HANDOFF_MANIFEST_PATH, item["path"])
                self.assertNotEqual(FINAL_REPOSITORY_FREEZE_PATH, item["path"])
                self.assertNotIn("__pycache__", Path(item["path"]).parts)
                self.assertNotEqual(".pyc", Path(item["path"]).suffix)

    def test_forged_hash_authority_and_unknown_fields_are_rejected(self) -> None:
        cases = []
        forged_hash = dict(self.manifest)
        forged_hash["manifest_hash"] = "0" * 64
        cases.append(forged_hash)
        forged_authority = dict(self.manifest)
        forged_authority["authority_status"] = "APPROVED"
        cases.append(forged_authority)
        unknown = dict(self.manifest)
        unknown["approved"] = True
        cases.append(unknown)
        for payload in cases:
            with self.subTest(keys=sorted(payload)), self.assertRaises(ArchitectHandoffManifestError):
                verify_architect_handoff_manifest_data(payload)

    def test_tampered_or_symlink_manifest_is_rejected_without_repair(self) -> None:
        with TemporaryDirectory(prefix="aoia-architect-handoff-test-", dir="/tmp") as temporary_root:
            root = Path(temporary_root)
            tampered = root / "tampered.json"
            payload = dict(self.manifest)
            payload["file_count"] += 1
            tampered.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            with self.assertRaises(ArchitectHandoffManifestError):
                verify_architect_handoff_manifest(tampered, repository_root=PROJECT_ROOT)

            link = root / "manifest-link.json"
            link.symlink_to(MANIFEST_PATH)
            with self.assertRaises(ArchitectHandoffManifestError):
                verify_architect_handoff_manifest(link, repository_root=PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
