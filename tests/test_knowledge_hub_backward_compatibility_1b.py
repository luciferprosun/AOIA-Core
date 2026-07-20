from __future__ import annotations

import contextlib
import io
import json
import unittest

from runtime.knowledge_modules.cli import hub_main
from runtime.knowledge_modules.hub import KnowledgeHub1A, KnowledgeHub1B
from runtime.knowledge_modules.registry import KnowledgeModuleRegistration, KnowledgeModuleRegistry
from runtime.knowledge_modules.selection import KnowledgeModuleQuery, KnowledgeModuleSelection
from tests.knowledge_control_plane_test_support_1b import (
    SyntheticAdapter,
    configurations,
    instance_descriptor,
    module_descriptor,
    profile,
    query,
    registry_with,
    selection,
    synthetic_configuration,
)


class KnowledgeHubBackwardCompatibility1BTests(unittest.TestCase):
    def test_legacy_one_module_bundle_hash_is_preserved(self):
        descriptor = module_descriptor()
        configuration = synthetic_configuration(descriptor.module_id)
        legacy_query = KnowledgeModuleQuery(
            question="§ 1 SYN",
            retrieval_mode="SOURCE_DISCOVERY",
            max_results=10,
            max_excerpt_characters=4_000,
            max_total_context_characters=16_000,
        )
        legacy = KnowledgeHub1A(
            KnowledgeModuleRegistry((KnowledgeModuleRegistration(descriptor, SyntheticAdapter),))
        ).query(
            KnowledgeModuleSelection(module_ids=(descriptor.module_id,)),
            legacy_query,
            {descriptor.module_id: configuration},
        )
        instance = instance_descriptor(descriptor)
        modern = KnowledgeHub1B(
            registry_with((descriptor, SyntheticAdapter, instance))
        ).execute(
            profile(selection(descriptor, instance, max_results=10, max_context=16_000)),
            query(),
            configurations(descriptor),
        )
        self.assertEqual(
            legacy.evidence_bundles[0].bundle_hash,
            modern.composite_bundle.module_bundles[0].evidence_bundle.bundle_hash,
        )

    def test_new_cli_lists_modules_instances_and_zero_module_query(self):
        invocations = (
            (("list-modules",), "MODULES_LISTED"),
            (("list-instances", "--module", "de-law-federal-1a"), "INSTANCES_LISTED"),
        )
        for operation, expected in invocations:
            with self.subTest(operation=operation[0]):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    status = hub_main((*operation, "--repository-root", ".", "--format", "json"))
                self.assertEqual(status, 0)
                self.assertEqual(json.loads(stream.getvalue())["status"], expected)

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = hub_main((
                "validate-profile", "--repository-root", ".",
                "--enable-module", "de-law-federal-1a",
                "--instance", "de-law-federal-1a=de-law-federal-1a-local",
                "--format", "json",
            ))
        profile_payload = json.loads(stream.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(profile_payload["status"], "PROFILE_VALID")
        self.assertTrue(profile_payload["control_model"][0]["currently_selected"])
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = hub_main((
                "query", "--repository-root", ".", "--question",
                "Explain the difference between evidence and authority.", "--format", "json",
            ))
        payload = json.loads(stream.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "NO_KNOWLEDGE_MODULE_SELECTED")
        self.assertEqual(payload["composite_bundle"]["selected_module_ids"], [])


if __name__ == "__main__":
    unittest.main()
