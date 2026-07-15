from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime.final_repository_freeze import (
    FINAL_FREEZE_ID,
    FINAL_REPOSITORY_FREEZE_PATH,
    FinalRepositoryFreezeError,
    build_final_repository_freeze,
    serialize_final_repository_freeze,
    verify_final_repository_freeze,
    verify_final_repository_freeze_data,
    verify_inventory_files,
)


ROOT = Path(__file__).resolve().parents[1]
BRANCH = "feature/m2-b0-provider-critic-inert-core"
PARENT_HEAD = "4c72724d94c71a9933f70839e07c0bcbe0e0606d"


class FinalRepositoryFreeze1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.materialized = json.loads(
            (ROOT / FINAL_REPOSITORY_FREEZE_PATH).read_text(encoding="utf-8", errors="strict")
        )
        suite = cls.materialized["test_suite"]
        cls.freeze = build_final_repository_freeze(
            ROOT,
            branch=BRANCH,
            parent_head=PARENT_HEAD,
            passed=suite["passed"],
            skipped=suite["skipped"],
        )

    def test_materialized_freeze_matches_complete_repository(self) -> None:
        result = verify_final_repository_freeze(
            ROOT / FINAL_REPOSITORY_FREEZE_PATH,
            repository_root=ROOT,
        )
        self.assertEqual(self.freeze["freeze_manifest_hash"], result)
        self.assertEqual(serialize_final_repository_freeze(self.freeze), (ROOT / FINAL_REPOSITORY_FREEZE_PATH).read_bytes())

    def test_freeze_build_and_serialization_are_deterministic(self) -> None:
        rebuilt = build_final_repository_freeze(
            ROOT,
            branch=BRANCH,
            parent_head=PARENT_HEAD,
            passed=self.materialized["test_suite"]["passed"],
            skipped=self.materialized["test_suite"]["skipped"],
        )
        self.assertEqual(self.freeze, rebuilt)
        self.assertEqual(serialize_final_repository_freeze(self.freeze), serialize_final_repository_freeze(rebuilt))

    def test_freeze_is_explicitly_non_authoritative(self) -> None:
        self.assertEqual(FINAL_FREEZE_ID, self.freeze["freeze_id"])
        self.assertEqual("NON_AUTHORITATIVE", self.freeze["authority_status"])
        for field in (
            "can_approve", "can_dispatch", "can_execute", "can_invoke_browser",
            "can_invoke_git", "can_invoke_network", "can_invoke_provider", "can_write",
        ):
            self.assertIs(self.freeze[field], False)

    def test_freeze_binds_handoff_unix_freeze_and_all_four_hats(self) -> None:
        self.assertEqual("9f5020095eb5d7d083ed837928198b9a05371766254a1e3ca61f2ff765d102e5", self.freeze["unix_r1_freeze_hash"])
        self.assertEqual("unix-knowledge-hat-1a", self.freeze["unix_hat_identity"]["hat_id"])
        self.assertEqual({"bash", "linux", "python"}, set(self.freeze["hat_identities"]))
        self.assertEqual(64, len(self.freeze["architect_handoff_manifest_hash"]))

    def test_inventory_is_portable_exact_and_excludes_forbidden_paths(self) -> None:
        paths = [item["path"] for item in self.freeze["files"]]
        self.assertEqual(paths, sorted(set(paths)))
        self.assertNotIn(FINAL_REPOSITORY_FREEZE_PATH, paths)
        for path in paths:
            parts = Path(path).parts
            self.assertFalse(Path(path).is_absolute())
            self.assertNotIn("..", parts)
            self.assertNotIn(".git", parts)
            self.assertNotIn("__pycache__", parts)
            self.assertNotEqual(".pyc", Path(path).suffix)

    def test_mutation_removal_addition_and_truncation_are_detected(self) -> None:
        with TemporaryDirectory(prefix="aoia-final-freeze-inventory-", dir="/tmp") as temporary:
            root = Path(temporary)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_bytes(b"alpha")
            second.write_bytes(b"bravo")
            records = [
                {"mode": 0o755 if stat.S_IMODE(path.stat().st_mode) & 0o111 else 0o644, "path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}
                for path in (first, second)
            ]
            verify_inventory_files(root, records)
            cases = ("mutation", "removal", "addition", "truncation")
            for case in cases:
                with self.subTest(case=case):
                    first.write_bytes(b"alpha")
                    second.write_bytes(b"bravo")
                    extra = root / "extra.txt"
                    if extra.exists():
                        extra.unlink()
                    if case == "mutation":
                        first.write_bytes(b"ALPHA")
                    elif case == "removal":
                        second.unlink()
                    elif case == "addition":
                        extra.write_bytes(b"extra")
                    else:
                        first.write_bytes(b"")
                    with self.assertRaises(FinalRepositoryFreezeError):
                        verify_inventory_files(root, records)

    def test_forged_hash_authority_and_unknown_fields_fail_closed(self) -> None:
        cases = []
        forged_hash = copy.deepcopy(self.freeze)
        forged_hash["freeze_manifest_hash"] = "0" * 64
        cases.append(forged_hash)
        forged_authority = copy.deepcopy(self.freeze)
        forged_authority["can_execute"] = True
        cases.append(forged_authority)
        unknown = copy.deepcopy(self.freeze)
        unknown["approved"] = True
        cases.append(unknown)
        for payload in cases:
            with self.subTest(keys=sorted(payload)), self.assertRaises(FinalRepositoryFreezeError):
                verify_final_repository_freeze_data(payload)

    def test_forged_upstream_binding_is_rejected_even_with_recomputed_hash(self) -> None:
        forged = copy.deepcopy(self.freeze)
        forged["corpus_manifest_hash"] = "0" * 64
        material = {key: value for key, value in forged.items() if key != "freeze_manifest_hash"}
        forged["freeze_manifest_hash"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with TemporaryDirectory(prefix="aoia-final-freeze-binding-", dir="/tmp") as temporary:
            path = Path(temporary) / "freeze.json"
            path.write_text(json.dumps(forged, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(FinalRepositoryFreezeError):
                verify_final_repository_freeze(path, repository_root=ROOT)

    def test_truncated_or_symlink_freeze_is_rejected_without_repair(self) -> None:
        with TemporaryDirectory(prefix="aoia-final-freeze-file-", dir="/tmp") as temporary:
            root = Path(temporary)
            truncated = root / "truncated.json"
            truncated.write_text("{", encoding="utf-8")
            with self.assertRaises(FinalRepositoryFreezeError):
                verify_final_repository_freeze(truncated, repository_root=ROOT)
            link = root / "link.json"
            link.symlink_to(ROOT / FINAL_REPOSITORY_FREEZE_PATH)
            with self.assertRaises(FinalRepositoryFreezeError):
                verify_final_repository_freeze(link, repository_root=ROOT)


if __name__ == "__main__":
    unittest.main()
