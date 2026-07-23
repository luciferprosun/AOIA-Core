from __future__ import annotations

import hashlib
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.aoia_desktop_demo.knowledge.hats.adapters.german_federal_employment_worker_law import (
    BINDING_KEY,
    HAT_ID,
    GermanFederalEmploymentWorkerLawAdapter,
)
from apps.aoia_desktop_demo.knowledge.hats.canonical import verify_bundle
from apps.aoia_desktop_demo.knowledge.hats.contracts import (
    HatBinding,
    HatRetrievalLimits,
    HatValidationError,
)
from apps.aoia_desktop_demo.tests.knowledge_hat_test_support import (
    make_german_law_fixture,
)


NEUTRAL_QUESTION = (
    "Under current German law, can an employment contract be concluded orally, "
    "and what documentation of the essential working conditions must the employer "
    "provide? Please distinguish the validity of the employment contract from the "
    "employer's documentation obligations and mention relevant statutory provisions, "
    "form requirements and important exceptions. Do not browse the internet. State "
    "any remaining uncertainty."
)
DEFAULT_LIMITS = HatRetrievalLimits(
    max_results=6,
    max_excerpt_chars=2_400,
    max_total_chars=8_000,
)


def _file_snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    result: dict[str, tuple[int, int, str]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        metadata = path.stat()
        result[relative] = (
            metadata.st_size,
            metadata.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return result


class GermanLawAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary, self.root, identity = make_german_law_fixture()
        self.adapter = GermanFederalEmploymentWorkerLawAdapter(identity)
        self.binding = HatBinding(HAT_ID, BINDING_KEY, self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_ready_status_and_structured_retrieval_use_real_provenance(self) -> None:
        status = self.adapter.inspect_status(self.binding)
        self.assertEqual(status.state, "ready")
        self.assertTrue(status.local_only)
        self.assertTrue(status.read_only)
        self.assertEqual(status.indexed_source_count, 2)

        bundle = self.adapter.retrieve(
            self.binding,
            NEUTRAL_QUESTION,
            limits=DEFAULT_LIMITS,
        )
        verify_bundle(bundle)
        self.assertEqual(bundle.hat_id, HAT_ID)
        self.assertEqual(len(bundle.passages), 2)
        references = {
            reference
            for passage in bundle.passages
            for reference in passage.statutory_references
        }
        self.assertEqual(references, {"GewO § 105", "NachwG § 2"})
        for passage in bundle.passages:
            self.assertTrue(passage.source_id)
            self.assertTrue(passage.source_title)
            self.assertTrue(passage.source_locator.startswith("normalized/documents/"))
            self.assertFalse(Path(passage.source_locator.split("#", 1)[0]).is_absolute())
            self.assertTrue(passage.effective_dates)
            self.assertTrue(passage.content_digest)

    def test_retrieval_enforces_result_excerpt_and_total_bounds(self) -> None:
        one = self.adapter.retrieve(
            self.binding,
            NEUTRAL_QUESTION,
            limits=HatRetrievalLimits(1, 256, 1_024),
        )
        self.assertEqual(len(one.passages), 1)
        self.assertLessEqual(len(one.passages[0].excerpt), 256)

        bounded = self.adapter.retrieve(
            self.binding,
            NEUTRAL_QUESTION,
            limits=HatRetrievalLimits(6, 800, 1_024),
        )
        self.assertLessEqual(sum(len(item.excerpt) for item in bounded.passages), 1_024)
        self.assertTrue(all(len(item.excerpt) <= 800 for item in bounded.passages))

    def test_retrieval_does_not_modify_or_create_any_corpus_file(self) -> None:
        before = _file_snapshot(self.root)
        names_before = set(before)
        sys_path_before = tuple(sys.path)
        self.adapter.retrieve(self.binding, NEUTRAL_QUESTION, limits=DEFAULT_LIMITS)
        after = _file_snapshot(self.root)
        self.assertEqual(after, before)
        self.assertEqual(set(after), names_before)
        self.assertEqual(tuple(sys.path), sys_path_before)
        forbidden_suffixes = ("-journal", "-wal", "-shm", ".lock", ".cache")
        self.assertFalse(
            any(path.name.endswith(forbidden_suffixes) for path in self.root.rglob("*"))
        )

    def test_missing_root_and_required_control_file_are_unavailable(self) -> None:
        missing = HatBinding(HAT_ID, BINDING_KEY, self.root / "missing")
        self.assertEqual(self.adapter.inspect_status(missing).state, "unavailable")
        (self.root / "manifests" / "federal-temporal-graph-1a.json").unlink()
        self.assertEqual(self.adapter.inspect_status(self.binding).state, "unavailable")

    def test_malformed_manifest_and_index_fail_closed(self) -> None:
        manifest_path = self.root / "manifests" / "federal-temporal-graph-1a.json"
        manifest_path.write_text("{}", encoding="utf-8")
        self.assertEqual(self.adapter.inspect_status(self.binding).state, "invalid")

        self.temporary.cleanup()
        self.temporary, self.root, identity = make_german_law_fixture()
        self.binding = HatBinding(HAT_ID, BINDING_KEY, self.root)
        wrong_identity = replace(identity, search_index_sha256="0" * 64)
        self.assertEqual(
            GermanFederalEmploymentWorkerLawAdapter(wrong_identity)
            .inspect_status(self.binding)
            .state,
            "invalid",
        )

    def test_manifest_and_index_digest_mismatch_fail_closed(self) -> None:
        wrong_manifest = replace(self.adapter._identity, manifest_digest="0" * 64)
        wrong_index = replace(self.adapter._identity, index_digest="1" * 64)
        self.assertEqual(
            GermanFederalEmploymentWorkerLawAdapter(wrong_manifest)
            .inspect_status(self.binding)
            .state,
            "invalid",
        )
        self.assertEqual(
            GermanFederalEmploymentWorkerLawAdapter(wrong_index)
            .inspect_status(self.binding)
            .state,
            "invalid",
        )

    def test_missing_document_provenance_fails_retrieval(self) -> None:
        document_path = (
            self.root / "normalized" / "documents" / "de-bund-gii-gewo.json"
        )
        value = json.loads(document_path.read_text(encoding="utf-8"))
        value.pop("source_url")
        document_path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(HatValidationError):
            self.adapter.retrieve(self.binding, NEUTRAL_QUESTION, limits=DEFAULT_LIMITS)

    def test_control_file_symlink_substitution_fails_closed(self) -> None:
        manifest_path = self.root / "manifests" / "federal-temporal-graph-1a.json"
        outside = self.root.parent / f"{self.root.name}-outside-manifest.json"
        outside.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        manifest_path.symlink_to(outside)
        try:
            self.assertEqual(self.adapter.inspect_status(self.binding).state, "invalid")
        finally:
            outside.unlink()

    def test_source_object_digest_mismatch_fails_retrieval(self) -> None:
        document_path = (
            self.root / "normalized" / "documents" / "de-bund-gii-gewo.json"
        )
        document = json.loads(document_path.read_text(encoding="utf-8"))
        digest = document["object_sha256"]
        object_path = (
            self.root / "objects" / "sha256" / digest[:2] / digest[2:4] / digest
        )
        object_path.write_bytes(b"mutated fixture source")
        with self.assertRaises(HatValidationError):
            self.adapter.retrieve(self.binding, NEUTRAL_QUESTION, limits=DEFAULT_LIMITS)

    def test_empty_query_fails_and_unsearchable_query_returns_no_evidence(self) -> None:
        with self.assertRaises(HatValidationError):
            self.adapter.retrieve(self.binding, "", limits=DEFAULT_LIMITS)
        bundle = self.adapter.retrieve(
            self.binding,
            "unfindablefixtureterm",
            limits=DEFAULT_LIMITS,
        )
        self.assertEqual(bundle.passages, ())


class PathContractTests(unittest.TestCase):
    def test_required_relative_paths_cannot_escape_bound_root(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside-control"
            outside.write_text("outside", encoding="utf-8")
            try:
                with self.assertRaises(HatValidationError):
                    GermanFederalEmploymentWorkerLawAdapter._required_file(
                        root,
                        Path("../outside-control"),
                    )
            finally:
                outside.unlink()


if __name__ == "__main__":
    unittest.main()
