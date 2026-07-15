from __future__ import annotations

import json
import types
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from runtime.human_decision_gated_artifact_write import (
    write_artifact_after_human_gate,
)
from runtime.memory_hat_registry import UnixHatRegistry
from runtime.memory_hats.unix_hat import (
    EXECUTION_REQUEST_BLOCKED,
    NO_ROUTE,
    NON_AUTHORITATIVE,
    REVIEW_NEEDED,
    ROUTE_TO_UNIX_KNOWLEDGE,
    ROUTING_POLICY_VERSION,
    UNIX_HAT_ID,
    UnixHatDescriptor,
    UnixHatRoutingError,
    UnixRouteProposal,
    actual_query_validation_payload,
    canonical_json_bytes,
    create_unix_hat_descriptor,
    create_unix_route_request,
    propose_unix_route,
    routing_policy_manifest_payload,
    unix_hat_descriptor_from_payload,
    unix_route_proposal_from_payload,
    unix_route_request_from_payload,
    validate_unix_hat_descriptor,
)
from runtime.orchestrator.knowledge_router import KnowledgeRouter
from runtime.retrieval.unix_runtime_adapter import (
    UnixRetrievalResult,
    retrieve_unix_knowledge,
)
from tests.static_capability_boundary_support_1a import (
    resolve_protected_runtime_files,
    scan_file_for_capabilities,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST_PATH = (
    PROJECT_ROOT / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json"
)
CORPUS_RECORDS_PATH = (
    PROJECT_ROOT / "data/unix_corpus_ingestion_1b/intake/records"
)
INDEX_ROOT = PROJECT_ROOT / "data/unix_retrieval_adapter_1a/index"
INDEX_MANIFEST_PATH = INDEX_ROOT / "index_manifest.json"
EXPECTED_CORPUS_HASH = (
    "e7241f0d043d90bf79a3f1a9f2691691a1d87b719d39cc533c9a765d97a61768"
)
EXPECTED_INDEX_HASH = (
    "3703dce3476b9c482515c3454f41a563c19f0f9ad21723fc61945434e79f7745"
)

ACTUAL_QUERY_SET: tuple[tuple[str, str], ...] = (
    ("How do UNIX file permissions work?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("Explain path traversal.", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What is shell injection?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("How do process signals work?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What are pipes?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What does sudo do?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("How does SSH authentication work?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What is systemd?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What are Linux namespaces?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What are control groups?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("How do containers isolate processes?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("What are package-management risks?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("How should an AI reason about network boundaries?", ROUTE_TO_UNIX_KNOWLEDGE),
    ("Run sudo apt install curl.", EXECUTION_REQUEST_BLOCKED),
    ("Execute rm -rf /tmp/example.", EXECUTION_REQUEST_BLOCKED),
    ("Use git push --force.", EXECUTION_REQUEST_BLOCKED),
    ("Open a shell and change permissions.", EXECUTION_REQUEST_BLOCKED),
    ("Install this package for me.", EXECUTION_REQUEST_BLOCKED),
    ("Explain stellar nucleosynthesis.", NO_ROUTE),
    ("Write a romantic poem.", NO_ROUTE),
    ("What is the capital of France?", NO_ROUTE),
    ("Fix my system.", REVIEW_NEEDED),
    ("Make Linux work.", REVIEW_NEEDED),
    ("Do the safe thing with the server.", REVIEW_NEEDED),
)


def iter_data_values(value):
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from iter_data_values(getattr(value, field.name))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from iter_data_values(key)
            yield from iter_data_values(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from iter_data_values(item)
        return
    yield value


class UnixHatAndRouting1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus_payload = json.loads(
            CORPUS_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        cls.index_payload = json.loads(
            INDEX_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        cls.descriptor = create_unix_hat_descriptor(
            cls.corpus_payload,
            cls.index_payload,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
            expected_index_manifest_hash=EXPECTED_INDEX_HASH,
        )

    def route(
        self,
        query: str,
        *,
        context_metadata=None,
        requested_limit: int = 5,
    ) -> UnixRouteProposal:
        request = create_unix_route_request(
            query,
            context_metadata=context_metadata,
            requested_limit=requested_limit,
        )
        return propose_unix_route(request, self.descriptor)

    def test_descriptor_is_immutable_stable_bound_and_non_authoritative(self) -> None:
        descriptor = self.descriptor
        self.assertIsInstance(descriptor, UnixHatDescriptor)
        self.assertEqual(UNIX_HAT_ID, descriptor.hat_id)
        self.assertEqual(NON_AUTHORITATIVE, descriptor.authority_status)
        self.assertEqual((), descriptor.capability_ids)
        self.assertEqual(EXPECTED_CORPUS_HASH, descriptor.corpus_manifest_hash)
        self.assertEqual(EXPECTED_INDEX_HASH, descriptor.retrieval_index_hash)
        self.assertEqual(ROUTING_POLICY_VERSION, descriptor.routing_policy_version)
        with self.assertRaises(FrozenInstanceError):
            descriptor.hat_id = "forged"  # type: ignore[misc]

    def test_descriptor_hash_is_deterministic_and_reconstructs_as_metadata(self) -> None:
        rebuilt = create_unix_hat_descriptor(
            dict(reversed(tuple(self.corpus_payload.items()))),
            dict(reversed(tuple(self.index_payload.items()))),
            expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
            expected_index_manifest_hash=EXPECTED_INDEX_HASH,
        )
        restored = unix_hat_descriptor_from_payload(
            self.descriptor.to_dict(),
            expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
            expected_index_manifest_hash=EXPECTED_INDEX_HASH,
        )
        self.assertEqual(self.descriptor, rebuilt)
        self.assertEqual(self.descriptor, restored)
        self.assertEqual(NON_AUTHORITATIVE, restored.authority_status)

    def test_descriptor_contains_no_callable_module_or_capability(self) -> None:
        for value in iter_data_values(self.descriptor):
            self.assertFalse(callable(value), repr(value))
            self.assertFalse(isinstance(value, types.ModuleType), repr(value))
        self.assertEqual((), self.descriptor.capability_ids)

    def test_descriptor_rejects_forgery_unknown_fields_and_stale_bindings(self) -> None:
        forged = self.descriptor.to_dict()
        forged["display_name"] = "Forged"
        with self.assertRaisesRegex(UnixHatRoutingError, "descriptor hash"):
            unix_hat_descriptor_from_payload(forged)

        unknown = self.descriptor.to_dict()
        unknown["approved"] = True
        with self.assertRaises(UnixHatRoutingError) as unknown_error:
            unix_hat_descriptor_from_payload(unknown)
        self.assertEqual("UNKNOWN_HAT_VERSION", unknown_error.exception.status)

        with self.assertRaises(UnixHatRoutingError) as corpus_error:
            validate_unix_hat_descriptor(
                self.descriptor,
                expected_corpus_manifest_hash="0" * 64,
            )
        self.assertEqual("CORPUS_MANIFEST_MISMATCH", corpus_error.exception.status)

        with self.assertRaises(UnixHatRoutingError) as index_error:
            validate_unix_hat_descriptor(
                self.descriptor,
                expected_index_manifest_hash="0" * 64,
            )
        self.assertEqual("INDEX_MANIFEST_MISMATCH", index_error.exception.status)

    def test_descriptor_rejects_changed_corpus_or_index_manifest(self) -> None:
        changed_corpus = dict(self.corpus_payload)
        changed_corpus["corpus_id"] = "forged-corpus"
        with self.assertRaises(UnixHatRoutingError) as corpus_error:
            create_unix_hat_descriptor(
                changed_corpus,
                self.index_payload,
                expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
                expected_index_manifest_hash=EXPECTED_INDEX_HASH,
            )
        self.assertEqual("CORPUS_MANIFEST_MISMATCH", corpus_error.exception.status)

        changed_index = dict(self.index_payload)
        changed_index["scoring_version"] = "forged"
        with self.assertRaises(UnixHatRoutingError) as index_error:
            create_unix_hat_descriptor(
                self.corpus_payload,
                changed_index,
                expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
                expected_index_manifest_hash=EXPECTED_INDEX_HASH,
            )
        self.assertEqual("INDEX_MANIFEST_MISMATCH", index_error.exception.status)

    def test_registry_is_immutable_deterministic_and_invokes_nothing(self) -> None:
        registry = UnixHatRegistry()
        with patch.object(
            Path,
            "write_text",
            side_effect=AssertionError("registry must not write"),
        ) as write_text:
            populated = registry.register(self.descriptor)
            resolved = populated.resolve(UNIX_HAT_ID)
            listed = populated.list_descriptors()

        write_text.assert_not_called()
        self.assertEqual((), registry.descriptors)
        self.assertIs(self.descriptor, resolved)
        self.assertEqual((self.descriptor,), listed)
        self.assertEqual(NON_AUTHORITATIVE, populated.authority_status)

    def test_registry_rejects_duplicate_and_forged_descriptors(self) -> None:
        registry = UnixHatRegistry().register(self.descriptor)
        with self.assertRaises(UnixHatRoutingError) as duplicate:
            registry.register(self.descriptor)
        self.assertEqual("DUPLICATE_HAT_ID", duplicate.exception.status)

        forged = replace(self.descriptor, descriptor_hash="0" * 64)
        with self.assertRaises(UnixHatRoutingError) as invalid:
            UnixHatRegistry().register(forged)
        self.assertEqual("STALE_HAT_DESCRIPTOR", invalid.exception.status)

    def test_request_normalization_hash_and_payload_are_deterministic(self) -> None:
        first = create_unix_route_request(
            "  HOW   do Unix permissions work?  ",
            context_metadata={"provider_output": {"route": "unix"}},
        )
        second = create_unix_route_request(
            "  HOW   do Unix permissions work?  ",
            context_metadata={"provider_output": {"route": "unix"}},
        )
        restored = unix_route_request_from_payload(first.to_dict())
        self.assertEqual(first, second)
        self.assertEqual(first, restored)
        self.assertEqual("how do unix permissions work", first.normalized_query)

    def test_request_rejects_empty_oversized_token_excess_and_invalid_limit(self) -> None:
        invalid = (
            ("", {}, 5),
            (" " * 4, {}, 5),
            ("x" * 2_049, {}, 5),
            (" ".join(["x"] * 65), {}, 5),
            ("unix", {}, 0),
            ("unix", {}, 21),
        )
        for query, context, limit in invalid:
            with self.subTest(query=query[:30], limit=limit):
                with self.assertRaises(UnixHatRoutingError) as error:
                    create_unix_route_request(
                        query,
                        context_metadata=context,
                        requested_limit=limit,
                    )
                self.assertEqual("INVALID_REQUEST", error.exception.status)

    def test_request_rejects_unknown_fields_and_executable_metadata(self) -> None:
        payload = create_unix_route_request("Explain UNIX.").to_dict()
        payload["human_approved"] = True
        with self.assertRaises(UnixHatRoutingError) as unknown:
            unix_route_request_from_payload(payload)
        self.assertEqual("INVALID_REQUEST", unknown.exception.status)

        for value in (lambda: None, types, object()):
            with self.subTest(value=repr(value)):
                with self.assertRaises(UnixHatRoutingError):
                    create_unix_route_request(
                        "Explain UNIX.",
                        context_metadata={"candidate": value},
                    )

    def test_actual_unix_knowledge_queries_route_deterministically(self) -> None:
        for query, expected in ACTUAL_QUERY_SET:
            if expected != ROUTE_TO_UNIX_KNOWLEDGE:
                continue
            with self.subTest(query=query):
                first = self.route(query)
                second = self.route(query)
                self.assertEqual(ROUTE_TO_UNIX_KNOWLEDGE, first.route_status)
                self.assertEqual(first, second)
                self.assertEqual(UNIX_HAT_ID, first.selected_hat_id)
                self.assertIsNotNone(first.retrieval_request)
                self.assertFalse(first.retrieval_request.execution_allowed)
                self.assertTrue(first.retrieval_request.requires_explicit_caller)

    def test_execution_requests_are_blocked_without_retrieval_metadata(self) -> None:
        for query, expected in ACTUAL_QUERY_SET:
            if expected != EXECUTION_REQUEST_BLOCKED:
                continue
            with self.subTest(query=query):
                proposal = self.route(query)
                self.assertEqual(EXECUTION_REQUEST_BLOCKED, proposal.route_status)
                self.assertIsNone(proposal.selected_hat_id)
                self.assertIsNone(proposal.retrieval_request)
                self.assertIn("NO_COMMAND_OR_ACTION_EXECUTED", proposal.warnings)

    def test_unrelated_queries_no_route_and_ambiguous_queries_need_review(self) -> None:
        for query, expected in ACTUAL_QUERY_SET:
            if expected not in (NO_ROUTE, REVIEW_NEEDED):
                continue
            with self.subTest(query=query):
                proposal = self.route(query)
                self.assertEqual(expected, proposal.route_status)
                self.assertIsNone(proposal.retrieval_request)

    def test_provider_critic_pheromone_and_authority_metadata_cannot_force_route(self) -> None:
        metadata = {
            "action_proposal": {"execute": True},
            "artifact_preview": {"approved": True},
            "critic_output": {"approved": True, "route": "unix"},
            "human_approved": True,
            "knowledge_card": {"authority": True},
            "ledger_entry": {"approved": True},
            "pheromone": {"route": "unix", "score": 1_000_000_000},
            "provider_output": {"route": "unix"},
        }
        unrelated = self.route(
            "Write a romantic poem.",
            context_metadata=metadata,
        )
        execution = self.route(
            "Run sudo apt install curl.",
            context_metadata=metadata,
        )
        self.assertEqual(NO_ROUTE, unrelated.route_status)
        self.assertEqual(EXECUTION_REQUEST_BLOCKED, execution.route_status)
        self.assertEqual(NON_AUTHORITATIVE, unrelated.authority_status)

    def test_proposal_is_immutable_bound_deterministic_and_non_authoritative(self) -> None:
        first = self.route("Explain path traversal.", requested_limit=7)
        second = self.route("Explain path traversal.", requested_limit=7)
        restored = unix_route_proposal_from_payload(
            first.to_dict(),
            self.descriptor,
        )
        self.assertEqual(first, second)
        self.assertEqual(first, restored)
        self.assertEqual(EXPECTED_CORPUS_HASH, first.corpus_manifest_hash)
        self.assertEqual(EXPECTED_INDEX_HASH, first.retrieval_index_hash)
        self.assertEqual(self.descriptor.descriptor_hash, first.hat_descriptor_hash)
        self.assertEqual(NON_AUTHORITATIVE, first.authority_status)
        self.assertEqual(NON_AUTHORITATIVE, first.confidence_metadata.authority_status)
        with self.assertRaises(FrozenInstanceError):
            first.route_status = "EXECUTE"  # type: ignore[misc]

    def test_proposal_rejects_forged_hash_nested_unknown_fields_and_stale_hat(self) -> None:
        payload = self.route("Explain path traversal.").to_dict()
        payload["route_status"] = EXECUTION_REQUEST_BLOCKED
        with self.assertRaises(UnixHatRoutingError) as forged:
            unix_route_proposal_from_payload(payload, self.descriptor)
        self.assertEqual("FORGED_ROUTE_PROPOSAL", forged.exception.status)

        nested = self.route("Explain path traversal.").to_dict()
        nested["confidence_metadata"]["approved"] = True
        with self.assertRaises(UnixHatRoutingError) as unknown:
            unix_route_proposal_from_payload(nested, self.descriptor)
        self.assertEqual("FORGED_ROUTE_PROPOSAL", unknown.exception.status)

        stale_descriptor = replace(self.descriptor, descriptor_hash="0" * 64)
        with self.assertRaises(UnixHatRoutingError) as stale:
            unix_route_proposal_from_payload(
                self.route("Explain path traversal.").to_dict(),
                stale_descriptor,
            )
        self.assertEqual("STALE_HAT_DESCRIPTOR", stale.exception.status)

    def test_proposal_contains_no_callable_module_path_writer_or_handler(self) -> None:
        proposal = self.route("How do UNIX file permissions work?")
        for value in iter_data_values(proposal):
            self.assertFalse(callable(value), repr(value))
            self.assertFalse(isinstance(value, types.ModuleType), repr(value))
            self.assertFalse(isinstance(value, Path), repr(value))

    def test_router_delegates_only_to_pure_metadata_classification(self) -> None:
        request = create_unix_route_request("What is systemd?")
        with TemporaryDirectory() as tmpdir:
            router = KnowledgeRouter(
                Path(tmpdir),
                engine=lambda: (_ for _ in ()).throw(AssertionError("engine called")),
                retriever=lambda: (_ for _ in ()).throw(AssertionError("retriever called")),
            )
            with (
                patch.object(Path, "write_text", side_effect=AssertionError("write")) as write_text,
                patch.object(Path, "write_bytes", side_effect=AssertionError("write")) as write_bytes,
                patch("builtins.open", side_effect=AssertionError("open")) as open_file,
            ):
                proposal = router.propose_unix_route(request, self.descriptor)

        write_text.assert_not_called()
        write_bytes.assert_not_called()
        open_file.assert_not_called()
        self.assertEqual(ROUTE_TO_UNIX_KNOWLEDGE, proposal.route_status)

    def test_retrieval_is_a_separate_explicit_caller_action(self) -> None:
        request = create_unix_route_request("How do UNIX file permissions work?")
        with patch(
            "runtime.retrieval.unix_runtime_adapter.retrieve_unix_knowledge",
            side_effect=AssertionError("routing called retrieval"),
        ) as guarded_retrieval:
            proposal = KnowledgeRouter.propose_unix_route(request, self.descriptor)
        guarded_retrieval.assert_not_called()
        self.assertIsNotNone(proposal.retrieval_request)

        result = retrieve_unix_knowledge(
            INDEX_ROOT,
            CORPUS_MANIFEST_PATH,
            CORPUS_RECORDS_PATH,
            proposal.retrieval_request.normalized_query,
            requested_limit=proposal.retrieval_request.requested_result_limit,
            evaluation_context="UNIX_HAT_ROUTING_1A_TEST",
            expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
        )
        self.assertIsInstance(result, UnixRetrievalResult)
        self.assertEqual(
            proposal.retrieval_request.normalized_query,
            result.query.normalized_query,
        )
        self.assertEqual(proposal.retrieval_index_hash, result.index_hash)
        self.assertEqual(NON_AUTHORITATIVE, result.authority_status)

    def test_route_proposal_cannot_serve_as_human_gate_evidence(self) -> None:
        artifact_writer = Mock(
            side_effect=AssertionError("writer must not run for route metadata")
        )
        with TemporaryDirectory() as tmpdir:
            result = write_artifact_after_human_gate(
                gate_result=self.route("What is systemd?"),
                artifact_request=object(),
                workspace_root=tmpdir,
                artifact_writer=artifact_writer,
            )
        self.assertFalse(result.write_attempted)
        self.assertFalse(result.artifact_write_occurred)
        artifact_writer.assert_not_called()

    def test_confidence_is_integer_bounded_deterministic_and_not_authority(self) -> None:
        for query, _expected in ACTUAL_QUERY_SET:
            first = self.route(query).confidence_metadata
            second = self.route(query).confidence_metadata
            self.assertEqual(first, second)
            for name in (
                "topic_match_score",
                "scope_match_score",
                "execution_risk_score",
                "excluded_domain_score",
                "ambiguity_score",
                "final_confidence",
            ):
                value = getattr(first, name)
                self.assertIs(type(value), int)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 10_000)
            self.assertEqual(NON_AUTHORITATIVE, first.authority_status)

    def test_actual_query_set_has_expected_statuses_and_stable_hashes(self) -> None:
        first = tuple(self.route(query) for query, _expected in ACTUAL_QUERY_SET)
        second = tuple(self.route(query) for query, _expected in ACTUAL_QUERY_SET)
        self.assertEqual(
            [expected for _query, expected in ACTUAL_QUERY_SET],
            [proposal.route_status for proposal in first],
        )
        self.assertEqual(
            [proposal.proposal_hash for proposal in first],
            [proposal.proposal_hash for proposal in second],
        )
        self.assertEqual(24, len({proposal.proposal_hash for proposal in first}))

    def test_policy_descriptor_and_validation_artifacts_are_canonical_and_replay(self) -> None:
        proposals = tuple(
            (query, self.route(query)) for query, _expected in ACTUAL_QUERY_SET
        )
        artifacts = {
            "actual_query_validation.json": canonical_json_bytes(
                actual_query_validation_payload(proposals)
            ),
            "routing_policy_manifest.json": canonical_json_bytes(
                routing_policy_manifest_payload(self.descriptor)
            ),
            "unix_hat_descriptor.json": canonical_json_bytes(
                self.descriptor.to_dict()
            ),
        }
        replay = {
            name: bytes(payload)
            for name, payload in reversed(tuple(artifacts.items()))
        }
        self.assertEqual(artifacts, replay)
        for payload in artifacts.values():
            self.assertEqual(payload, canonical_json_bytes(json.loads(payload)))
            self.assertNotIn(b"human_approved", payload)

    def test_static_zones_include_new_hat_and_router_and_are_clean(self) -> None:
        records = resolve_protected_runtime_files(
            PROJECT_ROOT,
            ("unix_hat", "knowledge_routing"),
        )
        by_path = {record.path: record for record in records}
        self.assertIn("runtime/memory_hats/unix_hat.py", by_path)
        self.assertIn("runtime/orchestrator/knowledge_router.py", by_path)
        findings = tuple(
            finding
            for record in records
            for finding in scan_file_for_capabilities(PROJECT_ROOT, record)
        )
        self.assertEqual((), findings)

    def test_router_and_hat_sources_do_not_import_retrieval_or_capabilities(self) -> None:
        router_source = (
            PROJECT_ROOT / "runtime/orchestrator/knowledge_router.py"
        ).read_text(encoding="utf-8")
        hat_source = (
            PROJECT_ROOT / "runtime/memory_hats/unix_hat.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("runtime.retrieval", router_source)
        self.assertNotIn("self.retrieve", router_source)
        forbidden_import_text = (
            "import subprocess",
            "import socket",
            "import requests",
            "import openai",
            "import anthropic",
            "import git",
        )
        for source in (router_source, hat_source):
            for text in forbidden_import_text:
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
