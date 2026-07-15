from __future__ import annotations

import ast
import json
import types
import unittest
from dataclasses import fields, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from runtime.human_decision_gate_integration import (
    validate_canonical_human_gate_authority,
)
from runtime.memory_hats.unix_hat import (
    EXECUTION_REQUEST_BLOCKED,
    NO_ROUTE,
    NON_AUTHORITATIVE,
    REVIEW_NEEDED,
    ROUTE_TO_UNIX_KNOWLEDGE,
    UnixHatRoutingError,
    create_unix_route_request,
    propose_unix_route,
)
from runtime.retrieval.unix_runtime_adapter import (
    UnixRetrievalResult,
    retrieve_unix_knowledge,
)
import runtime.unix_full_validation_freeze as freeze
from runtime.unix_full_validation_freeze import (
    EXPECTED_VISIBLE_DEMO_MANIFEST_HASH,
    FREEZE_ID,
    SUPERSEDES_FREEZE_MANIFEST_HASH,
    UnixFullValidationError,
    benchmark_unix_unit,
    build_adversarial_report,
    build_capability_boundary_report,
    build_determinism_report,
    build_unix_full_validation_freeze_payloads,
    build_validation_summary,
    build_worktree_snapshot,
    materialize_unix_full_validation_freeze,
    replay_unix_unit_artifacts,
    verify_unix_full_validation_freeze,
    verify_unix_unit_upstream,
)
from runtime.visible_unix_prototype import (
    build_visible_unix_review_model,
    render_visible_unix_html,
    render_visible_unix_text,
    verify_visible_unix_review_model,
    verify_visible_unix_upstream,
)
from tests.static_capability_boundary_support_1a import (
    PROTECTED_ZONE_NAMES,
    resolve_protected_runtime_files,
    scan_file_for_capabilities,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "runtime/unix_full_validation_freeze.py"
BRANCH = "feature/m2-b0-provider-critic-inert-core"
HEAD = "4c72724d94c71a9933f70839e07c0bcbe0e0606d"
EXPECTED_CORPUS_HASH = (
    "e7241f0d043d90bf79a3f1a9f2691691a1d87b719d39cc533c9a765d97a61768"
)
EXPECTED_INDEX_HASH = (
    "3703dce3476b9c482515c3454f41a563c19f0f9ad21723fc61945434e79f7745"
)
EXPECTED_HAT_HASH = (
    "24850bfb838488d8b7839a518cd2a8d702b8b266397edbbcb0fc5f7a4ba78a0c"
)
CASE_COUNTS = {
    "authority_attack_cases": 21,
    "corpus_poisoning_cases": 12,
    "hat_routing_forgery_cases": 10,
    "index_tampering_cases": 12,
    "path_symlink_cases": 12,
    "resource_limit_cases": 10,
    "visible_xss_tampering_cases": 12,
}


def _iter_values(value):
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _iter_values(getattr(value, field.name))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_values(key)
            yield from _iter_values(item)
        return
    if isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from _iter_values(item)
        return
    yield value


class UnixFullValidationAndFreeze1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.upstream = verify_unix_unit_upstream(PROJECT_ROOT)
        cls.visible_upstream = verify_visible_unix_upstream()
        cls.replay = replay_unix_unit_artifacts(
            PROJECT_ROOT,
            cls.root / "replay",
        )
        cls.benchmark = benchmark_unix_unit(
            PROJECT_ROOT,
            cls.root / "benchmark",
            repetitions=3,
        )
        cls.snapshot = build_worktree_snapshot(
            PROJECT_ROOT,
            (
                "runtime/unix_full_validation_freeze.py",
                "tests/static_capability_boundary_support_1a.py",
            ),
            branch=BRANCH,
            head=HEAD,
        )
        cls.test_summary = {
            "adversarial_tests": 20,
            "errors": 0,
            "failures": 0,
            "final_validation_tests": 20,
            "full_suite_total": 3_214,
            "non_interactive": True,
            "skipped": 4,
            "static_capability_tests": 38,
            "step12_regressions": 30,
            "step13_ledger_tests": 82,
            "upstream_unix_regressions": 178,
        }
        cls.validation = build_validation_summary(cls.test_summary)
        cls.determinism = build_determinism_report(cls.replay)
        cls.adversarial = build_adversarial_report(CASE_COUNTS)
        protected = resolve_protected_runtime_files(PROJECT_ROOT)
        zone_counts = {
            zone: sum(record.zone == zone for record in protected)
            for zone in PROTECTED_ZONE_NAMES
        }
        cls.capability = build_capability_boundary_report(zone_counts)
        cls.payloads = build_unix_full_validation_freeze_payloads(
            repository_root=PROJECT_ROOT,
            branch=BRANCH,
            head=HEAD,
            worktree_snapshot=cls.snapshot,
            validation_summary=cls.validation,
            determinism_report=cls.determinism,
            adversarial_report=cls.adversarial,
            capability_report=cls.capability,
            benchmark=cls.benchmark,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_independent_upstream_verification_binds_every_component(self) -> None:
        self.assertEqual(64, len(self.upstream.approved_source_inventory_hash))
        self.assertEqual(64, len(self.upstream.discovery_inventory_hash))
        self.assertEqual(EXPECTED_CORPUS_HASH, self.upstream.corpus_manifest_hash)
        self.assertEqual(13, self.upstream.corpus_record_count)
        self.assertEqual(797_008, self.upstream.normalized_bytes)
        self.assertEqual(EXPECTED_INDEX_HASH, self.upstream.retrieval_index_hash)
        self.assertEqual(13, self.upstream.indexed_record_count)
        self.assertEqual(EXPECTED_HAT_HASH, self.upstream.unix_hat_descriptor_hash)
        self.assertEqual(0, self.upstream.unix_hat_capability_count)
        self.assertEqual(
            EXPECTED_VISIBLE_DEMO_MANIFEST_HASH,
            self.upstream.visible_demo_manifest_hash,
        )
        self.assertEqual(16, self.upstream.visible_demo_file_count)

    def test_verified_upstream_is_inert_and_not_human_gate_authority(self) -> None:
        self.assertEqual(NON_AUTHORITATIVE, self.upstream.authority_status)
        for value in _iter_values(self.upstream):
            self.assertFalse(callable(value), repr(value))
            self.assertFalse(isinstance(value, types.ModuleType), repr(value))
        reason = validate_canonical_human_gate_authority(
            self.upstream,
            expected_artifact_hash="0" * 64,
            expected_approval_decision_id="decision",
            expected_audit_event_id="audit",
            expected_contract_audit_event_id="contract",
        )
        self.assertEqual("artifact write requires exact canonical human gate evidence", reason)

    def test_complete_corpus_index_hat_and_visible_replay_matches(self) -> None:
        self.assertTrue(self.replay.corpus_replay_match)
        self.assertTrue(self.replay.retrieval_index_replay_match)
        self.assertTrue(self.replay.hat_routing_replay_match)
        self.assertTrue(self.replay.visible_demo_replay_match)
        self.assertEqual(64, len(self.replay.report_hash))

    def test_replay_report_is_deterministic_across_clean_roots(self) -> None:
        second = replay_unix_unit_artifacts(PROJECT_ROOT, self.root / "second-replay")
        self.assertEqual(self.replay, second)

    def test_valid_knowledge_flow_keeps_every_stage_explicit_and_inert(self) -> None:
        request = create_unix_route_request("How do UNIX file permissions work?")
        proposal = propose_unix_route(request, self.visible_upstream.descriptor)
        self.assertEqual(ROUTE_TO_UNIX_KNOWLEDGE, proposal.route_status)
        self.assertIsNotNone(proposal.retrieval_request)
        retrieval_request = proposal.retrieval_request
        assert retrieval_request is not None
        self.assertTrue(retrieval_request.requires_explicit_caller)
        result = retrieve_unix_knowledge(
            PROJECT_ROOT / "data/unix_retrieval_adapter_1a/index",
            PROJECT_ROOT / "data/unix_corpus_ingestion_1b/intake/corpus_manifest.json",
            PROJECT_ROOT / "data/unix_corpus_ingestion_1b/intake/records",
            retrieval_request.normalized_query,
            expected_corpus_manifest_hash=EXPECTED_CORPUS_HASH,
        )
        self.assertIsInstance(result, UnixRetrievalResult)
        self.assertEqual(NON_AUTHORITATIVE, result.authority_status)
        model = build_visible_unix_review_model(
            request.raw_query,
            upstream=self.visible_upstream,
        )
        verify_visible_unix_review_model(model)
        self.assertEqual(proposal.proposal_hash, model.route_proposal_hash)
        self.assertEqual("NO_COMMAND_OR_ACTION_EXECUTED", model.execution_status)
        self.assertIn("NON_AUTHORITATIVE", render_visible_unix_text(model))
        self.assertNotIn("<script", render_visible_unix_html(model).casefold())

    def test_blocked_no_route_and_review_needed_never_gain_retrieval(self) -> None:
        cases = (
            ("Run sudo apt install curl.", EXECUTION_REQUEST_BLOCKED),
            ("Explain stellar nucleosynthesis.", NO_ROUTE),
            ("Fix my system.", REVIEW_NEEDED),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                proposal = propose_unix_route(
                    create_unix_route_request(query),
                    self.visible_upstream.descriptor,
                )
                self.assertEqual(expected, proposal.route_status)
                self.assertIsNone(proposal.retrieval_request)
                model = build_visible_unix_review_model(query, upstream=self.visible_upstream)
                self.assertEqual("NOT_PERFORMED", model.retrieval_status)
                self.assertEqual((), model.retrieval_candidates)

    def test_invalid_empty_and_oversized_requests_fail_closed(self) -> None:
        for query in ("", "   ", "unix " * 5_000):
            with self.subTest(length=len(query)):
                with self.assertRaises(UnixHatRoutingError):
                    create_unix_route_request(query)

    def test_worktree_snapshot_is_canonical_deterministic_and_local(self) -> None:
        reversed_snapshot = build_worktree_snapshot(
            PROJECT_ROOT,
            reversed(
                (
                    "runtime/unix_full_validation_freeze.py",
                    "tests/static_capability_boundary_support_1a.py",
                )
            ),
            branch=BRANCH,
            head=HEAD,
        )
        self.assertEqual(self.snapshot, reversed_snapshot)
        self.assertTrue(self.snapshot["local_worktree_freeze_not_git_release"])
        self.assertEqual(NON_AUTHORITATIVE, self.snapshot["authority_status"])

    def test_worktree_snapshot_rejects_empty_traversal_absolute_and_symlink(self) -> None:
        with self.assertRaises(UnixFullValidationError):
            build_worktree_snapshot(PROJECT_ROOT, (), branch=BRANCH, head=HEAD)
        for path in ("../escape", str(MODULE_PATH)):
            with self.subTest(path=path):
                with self.assertRaises(UnixFullValidationError):
                    build_worktree_snapshot(PROJECT_ROOT, (path,), branch=BRANCH, head=HEAD)
        link = self.root / "module-link.py"
        link.symlink_to(MODULE_PATH)
        with self.assertRaises(UnixFullValidationError):
            build_worktree_snapshot(self.root, (link.name,), branch=BRANCH, head=HEAD)

    def test_actual_machine_benchmark_is_measured_bounded_and_hash_bound(self) -> None:
        benchmark = self.benchmark
        self.assertEqual(NON_AUTHORITATIVE, benchmark["authority_status"])
        self.assertGreater(benchmark["corpus"]["ingestion_replay_wall_time_ns"], 0)
        self.assertGreater(benchmark["corpus"]["ingestion_replay_peak_memory_bytes"], 0)
        self.assertGreater(benchmark["retrieval_index"]["index_build_wall_time_ns"], 0)
        self.assertGreater(benchmark["retrieval_index"]["index_build_peak_memory_bytes"], 0)
        self.assertGreater(benchmark["query_performance"]["p95_latency_ns"], 0)
        self.assertGreater(benchmark["routing"]["p95_latency_ns"], 0)
        self.assertGreater(benchmark["visible_review"]["complete_demo_build_time_ns"], 0)
        self.assertEqual(EXPECTED_CORPUS_HASH, benchmark["hashes"]["corpus_manifest_hash"])
        self.assertEqual(EXPECTED_INDEX_HASH, benchmark["hashes"]["retrieval_index_hash"])
        self.assertEqual(64, len(benchmark["benchmark_hash"]))

    def test_benchmark_rejects_unbounded_or_insufficient_repetitions(self) -> None:
        for repetitions in (0, 2, 26, True):
            with self.subTest(repetitions=repetitions):
                with self.assertRaises(UnixFullValidationError):
                    benchmark_unix_unit(
                        PROJECT_ROOT,
                        self.root / f"bad-benchmark-{str(repetitions).lower()}",
                        repetitions=repetitions,
                    )

    def test_all_evidence_reports_are_canonical_non_authoritative_metadata(self) -> None:
        reports = (
            self.validation,
            self.determinism,
            self.adversarial,
            self.capability,
            self.benchmark,
        )
        for report in reports:
            with self.subTest(schema=report["schema_version"]):
                self.assertEqual(NON_AUTHORITATIVE, report["authority_status"])
                self.assertFalse(report["can_approve"])
                self.assertFalse(report["can_execute"])
                self.assertFalse(report["can_dispatch"])
                self.assertFalse(report["can_write"])

    def test_report_builders_reject_unclean_or_incomplete_evidence(self) -> None:
        bad_tests = dict(self.test_summary, failures=1)
        with self.assertRaises(UnixFullValidationError):
            build_validation_summary(bad_tests)
        with self.assertRaises(UnixFullValidationError):
            build_adversarial_report({"authority_attack_cases": 1})
        with self.assertRaises(UnixFullValidationError):
            build_capability_boundary_report({"freeze_evidence": 0})

    def test_freeze_payloads_are_byte_deterministic_and_strictly_manifested(self) -> None:
        second = build_unix_full_validation_freeze_payloads(
            repository_root=PROJECT_ROOT,
            branch=BRANCH,
            head=HEAD,
            worktree_snapshot=self.snapshot,
            validation_summary=self.validation,
            determinism_report=self.determinism,
            adversarial_report=self.adversarial,
            capability_report=self.capability,
            benchmark=self.benchmark,
        )
        self.assertEqual(self.payloads, second)
        manifest = json.loads(self.payloads["freeze_manifest.json"])
        self.assertEqual(FREEZE_ID, manifest["freeze_id"])
        self.assertEqual(
            SUPERSEDES_FREEZE_MANIFEST_HASH,
            manifest["supersedes_freeze_manifest_hash"],
        )
        self.assertTrue(manifest["local_worktree_freeze_not_git_release"])
        self.assertEqual(len(self.payloads) - 1, len(manifest["artifact_files"]))

    def test_freeze_materialization_and_independent_verifier_succeed(self) -> None:
        root = self.root / "materialized-freeze"
        verification = materialize_unix_full_validation_freeze(
            root,
            allowed_parent=self.root,
            repository_root=PROJECT_ROOT,
            branch=BRANCH,
            head=HEAD,
            worktree_snapshot=self.snapshot,
            validation_summary=self.validation,
            determinism_report=self.determinism,
            adversarial_report=self.adversarial,
            capability_report=self.capability,
            benchmark=self.benchmark,
        )
        self.assertTrue(verification.valid, verification.reason)
        second = verify_unix_full_validation_freeze(root, repository_root=PROJECT_ROOT)
        self.assertEqual(verification, second)

    def test_verifier_rejects_tampering_of_every_freeze_artifact(self) -> None:
        with patch.object(freeze, "verify_unix_unit_upstream", return_value=self.upstream):
            for index, relative in enumerate(sorted(self.payloads)):
                with self.subTest(relative=relative):
                    root = self.root / f"tamper-{index:02d}"
                    for path, payload in self.payloads.items():
                        destination = root / path
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(payload + (b"x" if path == relative else b""))
                    result = verify_unix_full_validation_freeze(
                        root,
                        repository_root=PROJECT_ROOT,
                    )
                    self.assertFalse(result.valid, relative)

    def test_verifier_rejects_unknown_removed_and_symlink_freeze_entries(self) -> None:
        for label in ("unknown", "removed", "symlink"):
            with self.subTest(label=label):
                root = self.root / f"file-set-{label}"
                for path, payload in self.payloads.items():
                    destination = root / path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(payload)
                if label == "unknown":
                    (root / "unknown.json").write_text("{}", encoding="utf-8")
                elif label == "removed":
                    (root / "limitations.json").unlink()
                else:
                    (root / "unknown-link").symlink_to(root / "limitations.json")
                result = verify_unix_full_validation_freeze(root, repository_root=PROJECT_ROOT)
                self.assertFalse(result.valid)

    def test_sponsor_bundle_is_offline_static_limited_and_control_free(self) -> None:
        html = self.payloads["sponsor_demo/index.html"].decode("utf-8")
        lowered = html.casefold()
        for forbidden in ("<script", "<iframe", "<button", "<form", "javascript:"):
            self.assertNotIn(forbidden, lowered)
        boundary = json.loads(self.payloads["sponsor_demo/authority_boundary.json"])
        self.assertEqual([], boundary["execution_controls"])
        self.assertEqual([], boundary["external_resources"])
        self.assertFalse(boundary["network_required"])
        limitations = json.loads(self.payloads["sponsor_demo/limitations.json"])
        self.assertEqual(list(freeze.REQUIRED_LIMITATIONS), limitations["limitations"])

    def test_freeze_output_root_must_be_a_new_exact_child_without_symlinks(self) -> None:
        existing = self.root / "already-exists"
        existing.mkdir()
        link_parent = self.root / "link-parent"
        link_parent.symlink_to(self.root, target_is_directory=True)
        cases = (
            (existing, self.root),
            (self.root / "nested/escape", self.root),
            (self.root / "other-parent", existing),
            (link_parent / "escape", link_parent),
        )
        for output, parent in cases:
            with self.subTest(output=output):
                with self.assertRaises(UnixFullValidationError):
                    materialize_unix_full_validation_freeze(
                        output,
                        allowed_parent=parent,
                        repository_root=PROJECT_ROOT,
                        branch=BRANCH,
                        head=HEAD,
                        worktree_snapshot=self.snapshot,
                        validation_summary=self.validation,
                        determinism_report=self.determinism,
                        adversarial_report=self.adversarial,
                        capability_report=self.capability,
                        benchmark=self.benchmark,
                    )

    def test_static_freeze_zone_is_exact_non_empty_and_violation_free(self) -> None:
        protected = resolve_protected_runtime_files(PROJECT_ROOT, ("freeze_evidence",))
        self.assertEqual(
            (
                ("runtime/final_repository_freeze.py", "freeze_evidence"),
                ("runtime/unix_full_validation_freeze.py", "freeze_evidence"),
            ),
            tuple((record.path, record.zone) for record in protected),
        )
        findings = tuple(
            finding
            for record in protected
            for finding in scan_file_for_capabilities(PROJECT_ROOT, record)
        )
        self.assertEqual((), findings)

    def test_freeze_module_imports_no_forbidden_external_capability(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden = (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "aiohttp",
            "urllib.request",
            "webbrowser",
            "selenium",
            "playwright",
            "git",
            "openai",
            "anthropic",
            "runtime.human_decision_gate_integration",
            "runtime.human_decision_gated_artifact_write",
            "runtime.patches.controlled_patch_apply",
        )
        self.assertFalse(
            {name for name in imported if any(name == root or name.startswith(root + ".") for root in forbidden)}
        )

    def test_direct_filesystem_writes_exist_only_in_explicit_build_boundaries(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"), filename=str(MODULE_PATH))
        allowed = {
            "benchmark_unix_unit",
            "materialize_unix_full_validation_freeze",
            "replay_unix_unit_artifacts",
            "_write_new_file",
        }
        writes = []
        for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                symbol = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else ""
                )
                if symbol in {"mkdir", "write_text", "write_bytes"}:
                    writes.append((function.name, symbol))
                elif symbol == "open":
                    modes = [
                        argument.value
                        for argument in node.args
                        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
                    ]
                    if any(any(flag in mode for flag in "wax+") for mode in modes):
                        writes.append((function.name, symbol))
        self.assertTrue(writes)
        self.assertTrue(all(function in allowed for function, _symbol in writes), writes)


if __name__ == "__main__":
    unittest.main()
