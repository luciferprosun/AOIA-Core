from __future__ import annotations

import json
import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.aoia_desktop_demo.knowledge.hats.bindings import (
    HatBindingError,
    load_bindings,
)
from apps.aoia_desktop_demo.knowledge.hats.canonical import (
    build_bundle,
    bundle_payload,
    canonical_sha256,
    passage_digest_payload,
    sha256_text,
    verify_attachment,
)
from apps.aoia_desktop_demo.knowledge.hats.catalog import (
    HatCatalogEntry,
    load_catalog,
    parse_catalog_entry,
)
from apps.aoia_desktop_demo.knowledge.hats.contracts import (
    HatBinding,
    HatDescriptor,
    HatEvidenceBundle,
    HatRetrievalLimits,
    HatStatus,
    HatValidationError,
)
from apps.aoia_desktop_demo.knowledge.hats.prompt_rendering import (
    render_evidence_bundle,
)
from apps.aoia_desktop_demo.knowledge.hats.registry import (
    NONE_HAT_ID,
    HatRegistry,
)
from apps.aoia_desktop_demo.knowledge.hats.service import (
    HatAttachmentService,
    HatServiceError,
)
from apps.aoia_desktop_demo.tests.knowledge_hat_test_support import (
    make_attachment,
    mutate_passage_excerpt,
)


REQUIRED_CAPABILITIES = (
    "local_read_only_retrieval",
    "stable_source_ids",
    "provenance",
    "deterministic_evidence_hash",
)


def _entry(descriptor: HatDescriptor, bundle: HatEvidenceBundle) -> HatCatalogEntry:
    return HatCatalogEntry(
        descriptor=descriptor,
        binding_key=f"{descriptor.hat_id}_local",
        corpus_committed=False,
        library_id=bundle.library_id,
        library_version=bundle.library_version,
        manifest_id=bundle.manifest_id,
        manifest_digest=bundle.manifest_digest,
        index_id=bundle.index_id,
        index_digest=bundle.index_digest,
        indexed_source_count=1,
        required_capabilities=REQUIRED_CAPABILITIES,
    )


def _status(entry: HatCatalogEntry, state: str = "ready") -> HatStatus:
    if state != "ready":
        return HatStatus(
            hat_id=entry.descriptor.hat_id,
            state=state,
            library_id=None,
            library_version=None,
            manifest_id=None,
            manifest_digest=None,
            index_id=None,
            index_digest=None,
            indexed_source_count=None,
            read_only=True,
            local_only=True,
            error_category=f"fixture_{state}",
        )
    return HatStatus(
        hat_id=entry.descriptor.hat_id,
        state="ready",
        library_id=entry.library_id,
        library_version=entry.library_version,
        manifest_id=entry.manifest_id,
        manifest_digest=entry.manifest_digest,
        index_id=entry.index_id,
        index_digest=entry.index_digest,
        indexed_source_count=entry.indexed_source_count,
        read_only=True,
        local_only=True,
        error_category=None,
    )


class _FixtureAdapter:
    def __init__(
        self,
        descriptor: HatDescriptor,
        entry: HatCatalogEntry,
        bundle: HatEvidenceBundle,
    ) -> None:
        self._descriptor = descriptor
        self._entry = entry
        self.bundle = bundle
        self.retrieve_count = 0
        self.inspect_count = 0
        self.statuses = [_status(entry)]

    def descriptor(self) -> HatDescriptor:
        return self._descriptor

    def inspect_status(self, _binding: HatBinding) -> HatStatus:
        self.inspect_count += 1
        return self.statuses[min(self.inspect_count - 1, len(self.statuses) - 1)]

    def retrieve(
        self,
        _binding: HatBinding,
        _query: str,
        *,
        limits: HatRetrievalLimits,
    ) -> HatEvidenceBundle:
        del limits
        self.retrieve_count += 1
        return self.bundle


def _service_fixture(
    temporary_root: Path,
    *,
    descriptor: HatDescriptor | None = None,
    attachment=None,
) -> tuple[HatAttachmentService, _FixtureAdapter, HatCatalogEntry]:
    descriptor = descriptor or HatDescriptor(
        hat_id="fixture_hat",
        display_name="Fixture HAT",
        domain="fixture_domain",
        adapter_id="fixture_hat_v1",
        descriptor_schema_version=1,
        evidence_schema_version=1,
        external_resource=True,
        authoritative=False,
    )
    attachment = attachment or make_attachment(descriptor)
    entry = _entry(descriptor, attachment.bundle)
    adapter = _FixtureAdapter(descriptor, entry, attachment.bundle)
    registry = HatRegistry((entry,), {descriptor.hat_id: lambda: adapter})
    resource_root = temporary_root / "resource"
    resource_root.mkdir()
    bindings_path = temporary_root / "bindings.json"
    bindings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "bindings": {
                    descriptor.hat_id: {
                        "binding_key": entry.binding_key,
                        "root": str(resource_root),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    os.chmod(bindings_path, 0o600)
    return (
        HatAttachmentService(registry, bindings_path=bindings_path),
        adapter,
        entry,
    )


class CatalogAndRegistryTests(unittest.TestCase):
    def test_default_registry_is_explicit_and_lists_none_and_german_law(self) -> None:
        descriptors = HatRegistry.default().list_descriptors()
        self.assertEqual(
            [descriptor.hat_id for descriptor in descriptors],
            [NONE_HAT_ID, "german_federal_employment_worker_law"],
        )
        self.assertTrue(all(not descriptor.authoritative for descriptor in descriptors))

    def test_catalog_metadata_cannot_supply_dynamic_code_loading_fields(self) -> None:
        path = next(
            (
                Path(__file__).resolve().parents[1]
                / "knowledge"
                / "hats"
                / "catalog_entries"
            ).glob("*.json")
        )
        value = json.loads(path.read_text(encoding="utf-8"))
        for forbidden in ("module", "class", "factory", "import", "entry_point", "python_path"):
            mutated = {**value, forbidden: "untrusted.module:Adapter"}
            with self.assertRaises(HatValidationError):
                parse_catalog_entry(mutated)

    def test_malformed_catalog_entries_and_duplicate_ids_fail_closed(self) -> None:
        with self.assertRaises(HatValidationError):
            parse_catalog_entry({"schema_version": 1})
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = next(
                (
                    Path(__file__).resolve().parents[1]
                    / "knowledge"
                    / "hats"
                    / "catalog_entries"
                ).glob("*.json")
            ).read_text(encoding="utf-8")
            (root / "a.json").write_text(source, encoding="utf-8")
            (root / "b.json").write_text(source, encoding="utf-8")
            with self.assertRaises(HatValidationError):
                load_catalog(root)

    def test_catalog_and_adapter_descriptor_mismatch_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            adapter._descriptor = replace(entry.descriptor, display_name="Drifted")
            with self.assertRaises(HatValidationError):
                service._registry.adapter(entry.descriptor.hat_id)

    def test_fake_future_hat_uses_generic_service_without_domain_branches(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            attachment = service.prepare_attachment(entry.descriptor.hat_id, "fixture query")
            self.assertIsNotNone(attachment)
            self.assertEqual(attachment.descriptor, entry.descriptor)
            self.assertEqual(adapter.retrieve_count, 1)
            service.verify_attachment(attachment)

    def test_unknown_hat_id_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, _entry_value = _service_fixture(Path(tmp))
            self.assertEqual(service.inspect("unknown_hat").state, "invalid")
            with self.assertRaises(HatServiceError):
                service.prepare_attachment("unknown_hat", "fixture query")
            self.assertEqual(adapter.retrieve_count, 0)

    def test_committed_catalog_and_registered_adapter_do_not_drift(self) -> None:
        registry = HatRegistry.default()
        entry = load_catalog()[0]
        adapter = registry.adapter(entry.descriptor.hat_id)
        self.assertEqual(adapter.descriptor(), entry.descriptor)
        self.assertEqual(entry.descriptor.authoritative, False)


class BindingAndServiceBoundaryTests(unittest.TestCase):
    def test_missing_binding_is_unavailable_and_never_retrieves(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            service._bindings_path = Path(tmp) / "missing.json"
            self.assertEqual(service.inspect(entry.descriptor.hat_id).state, "unavailable")
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query")
            self.assertEqual(adapter.retrieve_count, 0)

    def test_malformed_unknown_and_overexposed_binding_files_fail_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "bindings.json"
            known = {"fixture_hat": "fixture_hat_local"}
            path.write_text("{", encoding="utf-8")
            os.chmod(path, 0o600)
            with self.assertRaises(HatBindingError):
                load_bindings(known, path)
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "bindings": {
                            "unknown_hat": {
                                "binding_key": "unknown_local",
                                "root": str(root),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(HatBindingError):
                load_bindings(known, path)
            path.write_text(
                json.dumps({"schema_version": 1, "bindings": {}}),
                encoding="utf-8",
            )
            os.chmod(path, 0o644)
            with self.assertRaises(HatBindingError):
                load_bindings(known, path)

    def test_binding_rejects_relative_and_traversal_roots(self) -> None:
        with self.assertRaises(HatValidationError):
            HatBinding("fixture_hat", "fixture_hat_local", Path("relative"))
        with self.assertRaises(HatValidationError):
            HatBinding("fixture_hat", "fixture_hat_local", Path("/tmp/a/../outside"))

    def test_generic_service_enforces_all_retrieval_bounds(self) -> None:
        descriptor = HatDescriptor(
            hat_id="fixture_hat",
            display_name="Fixture HAT",
            domain="fixture_domain",
            adapter_id="fixture_hat_v1",
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=True,
            authoritative=False,
        )
        attachment = make_attachment(descriptor, excerpt="x" * 300)
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(
                Path(tmp),
                descriptor=descriptor,
                attachment=attachment,
            )
            limits = HatRetrievalLimits(1, 256, 1024)
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query", limits=limits)
            self.assertEqual(adapter.retrieve_count, 1)

    def test_empty_evidence_and_stale_query_fail_without_fallback(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            empty = build_bundle(
                schema_version=entry.descriptor.evidence_schema_version,
                hat_id=entry.descriptor.hat_id,
                normalized_query="fixture query",
                query_digest=sha256_text("fixture query"),
                library_id=entry.library_id,
                library_version=entry.library_version,
                manifest_id=entry.manifest_id,
                manifest_digest=entry.manifest_digest,
                index_id=entry.index_id,
                index_digest=entry.index_digest,
                passages=(),
            )
            adapter.bundle = empty
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query")
            adapter.bundle = make_attachment(entry.descriptor).bundle
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "different query")

    def test_control_identity_change_during_retrieval_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            adapter.statuses = [
                _status(entry),
                replace(_status(entry), state="invalid", library_id=None, library_version=None,
                        manifest_id=None, manifest_digest=None, index_id=None, index_digest=None,
                        indexed_source_count=None, error_category="changed"),
            ]
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query")

    def test_retrieval_never_mutates_global_sys_path(self) -> None:
        with TemporaryDirectory() as tmp:
            service, _adapter, entry = _service_fixture(Path(tmp))
            before = tuple(sys.path)
            service.prepare_attachment(entry.descriptor.hat_id, "fixture query")
            self.assertEqual(tuple(sys.path), before)

    def test_private_binding_root_in_evidence_fails_closed(self) -> None:
        descriptor = HatDescriptor(
            hat_id="fixture_hat",
            display_name="Fixture HAT",
            domain="fixture_domain",
            adapter_id="fixture_hat_v1",
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=True,
            authoritative=False,
        )
        with TemporaryDirectory() as tmp:
            temporary_root = Path(tmp)
            leaked = make_attachment(
                descriptor,
                excerpt=(temporary_root / "resource").as_posix(),
            )
            service, _adapter, entry = _service_fixture(
                temporary_root,
                descriptor=descriptor,
                attachment=leaked,
            )
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query")


class CanonicalHashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.descriptor = HatDescriptor(
            hat_id="fixture_hat",
            display_name="Fixture HAT",
            domain="fixture_domain",
            adapter_id="fixture_hat_v1",
            descriptor_schema_version=1,
            evidence_schema_version=1,
            external_resource=True,
            authoritative=False,
        )
        self.attachment = make_attachment(self.descriptor)

    def test_passage_digest_binds_excerpt_and_every_provenance_field(self) -> None:
        passage = self.attachment.bundle.passages[0]
        base = passage_digest_payload(
            hat_id=self.descriptor.hat_id,
            library_id=self.attachment.bundle.library_id,
            library_version=self.attachment.bundle.library_version,
            source_id=passage.source_id,
            source_title=passage.source_title,
            source_locator=passage.source_locator,
            statutory_references=passage.statutory_references,
            effective_dates=passage.effective_dates,
            excerpt=passage.excerpt,
        )
        base_digest = canonical_sha256(base)
        mutations = {
            "library_version": "2",
            "source_id": "other:record",
            "source_title": "Other source",
            "source_locator": "normalized/documents/other.json#record",
            "statutory_references": ("OtherG § 9",),
            "effective_dates": ("2030-01-01",),
            "excerpt": "Different exact evidence.",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.assertNotEqual(base_digest, canonical_sha256({**base, field: value}))

    def test_bundle_hash_binds_passages_and_control_identity(self) -> None:
        bundle = self.attachment.bundle
        for field, value in (
            ("manifest_digest", "a" * 64),
            ("index_digest", "b" * 64),
            ("library_version", "2"),
        ):
            with self.subTest(field=field):
                provisional = replace(bundle, **{field: value}, bundle_hash="0" * 64)
                self.assertNotEqual(
                    bundle.bundle_hash,
                    canonical_sha256(bundle_payload(provisional, include_hash=False)),
                )

    def test_volatile_time_and_absolute_root_are_not_hash_inputs(self) -> None:
        bundle_text = render_evidence_bundle(self.attachment.bundle)
        self.assertNotIn("timestamp", bundle_text.casefold())
        self.assertNotIn("mtime", bundle_text.casefold())
        self.assertNotIn(str(Path.home()), bundle_text)
        self.assertNotIn(str(Path("/tmp")), bundle_text)
        first = make_attachment(self.descriptor)
        second = make_attachment(self.descriptor)
        self.assertEqual(first.bundle.bundle_hash, second.bundle.bundle_hash)
        self.assertEqual(first.attachment_hash, second.attachment_hash)

    def test_mutated_evidence_and_stale_attachment_are_rejected(self) -> None:
        mutated = mutate_passage_excerpt(self.attachment, "Changed without re-hashing.")
        with self.assertRaises(HatValidationError):
            verify_attachment(mutated)
        stale = replace(
            make_attachment(self.descriptor, excerpt="new evidence"),
            attachment_hash=self.attachment.attachment_hash,
        )
        with self.assertRaises(HatValidationError):
            verify_attachment(stale)

    def test_manifest_or_index_digest_mismatch_fails_service_validation(self) -> None:
        with TemporaryDirectory() as tmp:
            service, adapter, entry = _service_fixture(Path(tmp))
            adapter.bundle = replace(adapter.bundle, manifest_digest="a" * 64)
            with self.assertRaises(HatServiceError):
                service.prepare_attachment(entry.descriptor.hat_id, "fixture query")


if __name__ == "__main__":
    unittest.main()
