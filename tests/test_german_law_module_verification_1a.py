from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from runtime.knowledge_modules.contracts import KnowledgeModuleConfiguration, KnowledgeModuleError
from runtime.knowledge_modules.external_gateway import ExternalCommandResult
from runtime.knowledge_modules import german_law as gl


GERMAN_REPOSITORY = Path("/home/l/AOIA_PRODUCTION/repos/AOIA-German-Law-Knowledge-Pack")
CORPUS_ROOT = Path("/home/l/AOIA_PRODUCTION/data/german-law-corpus")


def production_configuration(**changes):
    config = gl.production_german_law_configuration(
        module_repository_path=str(GERMAN_REPOSITORY),
        corpus_data_root=str(CORPUS_ROOT),
        expected_repository_head=gl.GERMAN_LAW_EXPECTED_HEAD,
    )
    return replace(config, **changes) if changes else config


def external_descriptor():
    value = gl.EXPECTED_GERMAN_LAW_DESCRIPTOR.to_dict()
    return {key: value[key] for key in gl._EXTERNAL_DESCRIPTOR_FIELDS}


def external_verification(configuration):
    corpus = Path(configuration.corpus_data_root).resolve()
    temporal = json.loads((corpus / "manifests/federal-temporal-graph-1a.json").read_text(encoding="utf-8"))
    selected = {
        relative: digest
        for relative, digest in configuration.expected_manifest_hashes
        if not relative.startswith("snapshots/eu/")
    }
    value = {
        "authority_status": "NON_AUTHORITATIVE",
        "can_approve": False,
        "can_call_provider": False,
        "can_execute": False,
        "can_provide_binding_legal_advice": False,
        "can_write": False,
        "corpus_snapshot_ids": list(configuration.expected_corpus_snapshot_ids),
        "counts": {
            "amendment_relationships": 0,
            "document_validity": 0,
            "documents": 0,
            "provision_validity": 0,
            "provisions": 0,
            "resolved_documents_at_evaluation_date": 0,
            "resolved_provisions_at_evaluation_date": 0,
            "temporal_events": 0,
            "temporal_records": 0,
            "unresolved": 0,
        },
        "data_root": str(corpus),
        "errors": [],
        "filesystem_read_only": True,
        "immutable_sqlite": True,
        "manifest_hash": temporal["manifest_hash"],
        "manifests_unchanged": True,
        "module_id": gl.GERMAN_LAW_MODULE_ID,
        "module_version": gl.GERMAN_LAW_MODULE_VERSION,
        "mutation_attempt_blocked": True,
        "network_calls": 0,
        "provider_calls": 0,
        "quick_checks": {"search": "ok", "temporal": "ok"},
        "sampled_source_objects": 3,
        "sampled_source_objects_verified": 3,
        "selected_manifest_hashes": selected,
        "sql_injection_inert": True,
        "sqlite_mode": "ro",
        "temporal_snapshot_id": configuration.expected_temporal_snapshot_id,
        "valid": True,
    }
    value["verification_hash"] = gl.GermanLawModuleAdapter._german_hash(value)
    return value


class FakeVerificationGateway:
    def __init__(self, configuration, *, descriptor=None, verification=None, returncode=0):
        self.configuration = configuration
        self.descriptor_value = external_descriptor() if descriptor is None else descriptor
        self.verification_value = (
            external_verification(configuration) if verification is None else verification
        )
        self.returncode = returncode

    def descriptor(self, configuration):
        self.assert_configuration(configuration)
        return dict(self.descriptor_value)

    def verify(self, configuration):
        self.assert_configuration(configuration)
        return ExternalCommandResult(
            operation="verify",
            command=("fixed-python", "-m", "german_law_corpus.cli", "hat-verify"),
            returncode=self.returncode,
            payload=dict(self.verification_value),
            stderr="",
        )

    def query(self, configuration, query):
        raise AssertionError("verification test must not query")

    def assert_configuration(self, configuration):
        if configuration != self.configuration:
            raise AssertionError("configuration changed")


class GermanLawModuleVerification1ATests(unittest.TestCase):
    def test_exact_repository_descriptor_corpus_and_snapshot_pins_verify(self):
        configuration = production_configuration()
        adapter = gl.GermanLawModuleAdapter(FakeVerificationGateway(configuration))
        result = adapter.verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertTrue(result.valid, result.to_dict())
        self.assertEqual(result.status, "VERIFIED")
        self.assertEqual(result.repository_head, gl.GERMAN_LAW_EXPECTED_HEAD)
        self.assertEqual(result.descriptor_hash, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR.descriptor_hash)
        self.assertEqual(result.resolved_corpus_path, gl.APPROVED_RESOLVED_CORPUS_PATH)
        self.assertEqual(result.temporal_snapshot_id, gl.GERMAN_LAW_TEMPORAL_SNAPSHOT)
        self.assertEqual(result.network_calls, 0)
        self.assertEqual(result.provider_calls, 0)

    def test_configuration_rejects_unknown_fields(self):
        value = production_configuration().to_dict()
        value["arbitrary_executable"] = "/bin/sh"
        with self.assertRaises(KnowledgeModuleError) as caught:
            KnowledgeModuleConfiguration.from_dict(value)
        self.assertEqual(caught.exception.status, "INVALID_MODULE_CONFIGURATION")

    def test_unexpected_actual_repository_head_blocks(self):
        with tempfile.TemporaryDirectory(prefix="aoia-german-head-") as temporary:
            root = Path(temporary)
            (root / ".git").mkdir()
            (root / ".git/HEAD").write_text("0" * 40 + "\n", encoding="ascii")
            (root / "src/german_law_corpus").mkdir(parents=True)
            (root / "src/german_law_corpus/cli.py").write_text("# fixture\n", encoding="utf-8")
            configuration = production_configuration(module_repository_path=str(root))
            result = gl.GermanLawModuleAdapter(
                FakeVerificationGateway(configuration, verification={})
            ).verify(
                configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR
            )
        self.assertFalse(result.valid)
        self.assertEqual(result.status, "MODULE_REPOSITORY_MISMATCH")

    def test_missing_repository_reports_module_unavailable_without_gateway_use(self):
        configuration = production_configuration(
            module_repository_path="/tmp/aoia-missing-german-law-repository"
        )
        result = gl.GermanLawModuleAdapter(
            FakeVerificationGateway(configuration, verification={})
        ).verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, "MODULE_NOT_AVAILABLE")

    def test_pin_mismatches_fail_with_stable_statuses(self):
        cases = (
            ({"expected_repository_head": "0" * 40}, "MODULE_REPOSITORY_MISMATCH"),
            ({"expected_module_version": "2a"}, "MODULE_VERSION_MISMATCH"),
            ({"expected_descriptor_hash": "0" * 64}, "MODULE_DESCRIPTOR_MISMATCH"),
            ({"expected_corpus_snapshot_id": "wrong-factory"}, "CORPUS_SNAPSHOT_MISMATCH"),
            ({"expected_corpus_snapshot_ids": ("wrong-source",)}, "CORPUS_SNAPSHOT_MISMATCH"),
            ({"expected_temporal_snapshot_id": "wrong-temporal"}, "TEMPORAL_SNAPSHOT_MISMATCH"),
            ({"approved_resolved_corpus_path": "/tmp/unreviewed"}, "CORPUS_PATH_MISMATCH"),
            (
                {
                    "expected_manifest_hashes": (
                        ("manifests/coverage.json", "0" * 64),
                    )
                },
                "CORPUS_VERIFICATION_FAILED",
            ),
        )
        for changes, status in cases:
            with self.subTest(changes=changes):
                configuration = production_configuration(**changes)
                result = gl.GermanLawModuleAdapter(FakeVerificationGateway(configuration)).verify(
                    configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR
                )
                self.assertFalse(result.valid)
                self.assertEqual(result.status, status)

    def test_corpus_path_and_symlink_escape_block(self):
        with tempfile.TemporaryDirectory(prefix="aoia-corpus-escape-") as temporary:
            outside = Path(temporary) / "outside"
            outside.mkdir()
            link = Path(temporary) / "corpus-link"
            link.symlink_to(outside, target_is_directory=True)
            configuration = production_configuration(corpus_data_root=str(link))
            result = gl.GermanLawModuleAdapter(
                FakeVerificationGateway(configuration, verification={})
            ).verify(
                configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR
            )
        self.assertFalse(result.valid)
        self.assertEqual(result.status, "CORPUS_PATH_MISMATCH")

    def test_external_descriptor_authority_and_shape_claims_are_blocked(self):
        configuration = production_configuration()
        authority = external_descriptor()
        authority["can_write"] = True
        malformed = external_descriptor()
        malformed["unexpected"] = "field"
        for descriptor, status in (
            (authority, "MODULE_AUTHORITY_CLAIM_BLOCKED"),
            (malformed, "MODULE_OUTPUT_MALFORMED"),
        ):
            with self.subTest(status=status):
                result = gl.GermanLawModuleAdapter(
                    FakeVerificationGateway(configuration, descriptor=descriptor)
                ).verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
                self.assertFalse(result.valid)
                self.assertEqual(result.status, status)

    def test_external_identity_and_snapshot_mismatches_fail_closed(self):
        configuration = production_configuration()
        wrong_version = external_descriptor()
        wrong_version["module_version"] = "2a"
        wrong_descriptor = external_descriptor()
        wrong_descriptor["display_name"] = "Unreviewed German Law"
        for descriptor, status in (
            (wrong_version, "MODULE_VERSION_MISMATCH"),
            (wrong_descriptor, "MODULE_DESCRIPTOR_MISMATCH"),
        ):
            with self.subTest(source="descriptor", status=status):
                result = gl.GermanLawModuleAdapter(
                    FakeVerificationGateway(configuration, descriptor=descriptor)
                ).verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
                self.assertFalse(result.valid)
                self.assertEqual(result.status, status)

        cases = (
            ("corpus_snapshot_ids", ["unreviewed-snapshot"], "CORPUS_SNAPSHOT_MISMATCH"),
            ("temporal_snapshot_id", "unreviewed-temporal", "TEMPORAL_SNAPSHOT_MISMATCH"),
            ("data_root", "/tmp/unreviewed-corpus", "CORPUS_PATH_MISMATCH"),
        )
        for field, value, status in cases:
            with self.subTest(source="verification", field=field):
                verification = external_verification(configuration)
                verification[field] = value
                verification["verification_hash"] = gl.GermanLawModuleAdapter._german_hash(
                    {
                        key: item
                        for key, item in verification.items()
                        if key != "verification_hash"
                    }
                )
                result = gl.GermanLawModuleAdapter(
                    FakeVerificationGateway(configuration, verification=verification)
                ).verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
                self.assertFalse(result.valid)
                self.assertEqual(result.status, status)

    def test_external_verification_failure_does_not_become_valid(self):
        configuration = production_configuration()
        verification = external_verification(configuration)
        verification["valid"] = False
        verification["verification_hash"] = gl.GermanLawModuleAdapter._german_hash(
            {key: value for key, value in verification.items() if key != "verification_hash"}
        )
        result = gl.GermanLawModuleAdapter(
            FakeVerificationGateway(configuration, verification=verification, returncode=1)
        ).verify(configuration, gl.EXPECTED_GERMAN_LAW_DESCRIPTOR)
        self.assertFalse(result.valid)
        self.assertEqual(result.status, "CORPUS_VERIFICATION_FAILED")


if __name__ == "__main__":
    unittest.main()
