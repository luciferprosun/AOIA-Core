from __future__ import annotations

import ast
import builtins
import json
import os
import socket
import subprocess
import types
import unittest
import webbrowser
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from io import StringIO
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
)
import runtime.visible_unix_prototype as prototype
from runtime.visible_unix_prototype import (
    ACTUAL_DEMO_QUERIES,
    EXECUTION_STATUS,
    VisibleUnixPrototypeError,
    VisibleUnixReviewModel,
    build_visible_unix_demo_payloads,
    build_visible_unix_review_model,
    materialize_visible_unix_demo,
    render_visible_unix_html,
    render_visible_unix_text,
    verify_visible_unix_demo,
    verify_visible_unix_review_model,
    verify_visible_unix_upstream,
    visible_unix_review_model_from_payload,
    visible_unix_review_model_payload,
)
from tests.static_capability_boundary_support_1a import (
    resolve_protected_runtime_files,
    scan_file_for_capabilities,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE_PATH = PROJECT_ROOT / "runtime/visible_unix_prototype.py"


def _iter_data_values(value):
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _iter_data_values(getattr(value, field.name))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_data_values(key)
            yield from _iter_data_values(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from _iter_data_values(item)
        return
    yield value


class VisibleUnixPrototype1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.upstream = verify_visible_unix_upstream()
        cls.models = {
            slug: build_visible_unix_review_model(query, upstream=cls.upstream)
            for slug, query, _expected in ACTUAL_DEMO_QUERIES
        }

    def test_upstream_corpus_index_hat_and_routing_policy_verify(self) -> None:
        upstream = self.upstream
        self.assertEqual(13, upstream.corpus_record_count)
        self.assertEqual(
            prototype.EXPECTED_CORPUS_MANIFEST_HASH,
            upstream.descriptor.corpus_manifest_hash,
        )
        self.assertEqual(
            prototype.EXPECTED_INDEX_MANIFEST_HASH,
            upstream.descriptor.retrieval_index_hash,
        )
        self.assertEqual(
            prototype.EXPECTED_HAT_DESCRIPTOR_HASH,
            upstream.descriptor.descriptor_hash,
        )
        self.assertEqual((), upstream.descriptor.capability_ids)

    def test_upstream_mismatch_is_rejected_without_repair(self) -> None:
        original = self.upstream.paths.routing_policy_path.read_bytes()
        payload = json.loads(original)
        payload["routing_policy_version"] = "forged-policy"
        with TemporaryDirectory() as tmpdir:
            forged = Path(tmpdir) / "routing_policy_manifest.json"
            forged.write_bytes(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
            paths = replace(self.upstream.paths, routing_policy_path=forged)
            with self.assertRaises(VisibleUnixPrototypeError):
                verify_visible_unix_upstream(paths)
        self.assertEqual(original, self.upstream.paths.routing_policy_path.read_bytes())

    def test_review_model_is_frozen_deterministic_and_non_authoritative(self) -> None:
        first = build_visible_unix_review_model(
            "Explain stellar nucleosynthesis.", upstream=self.upstream
        )
        second = build_visible_unix_review_model(
            "Explain stellar nucleosynthesis.", upstream=self.upstream
        )
        self.assertEqual(first, second)
        self.assertEqual(first.review_model_hash, second.review_model_hash)
        self.assertEqual(NON_AUTHORITATIVE, first.authority_status)
        self.assertEqual(EXECUTION_STATUS, first.execution_status)
        with self.assertRaises(FrozenInstanceError):
            first.route_status = "APPROVED"  # type: ignore[misc]

    def test_review_model_contains_no_callable_module_provider_or_path(self) -> None:
        for model in self.models.values():
            for value in _iter_data_values(model):
                self.assertFalse(callable(value), repr(value))
                self.assertFalse(isinstance(value, types.ModuleType), repr(value))
                self.assertFalse(isinstance(value, Path), repr(value))

    def test_payload_round_trip_rejects_unknown_fields_and_forged_hash(self) -> None:
        model = self.models["unix_file_permissions"]
        payload = visible_unix_review_model_payload(model)
        self.assertEqual(model, visible_unix_review_model_from_payload(payload))

        unknown = dict(payload)
        unknown["human_approved"] = True
        with self.assertRaises(VisibleUnixPrototypeError):
            visible_unix_review_model_from_payload(unknown)

        forged = json.loads(json.dumps(payload))
        forged["raw_query"] = "forged"
        with self.assertRaises(VisibleUnixPrototypeError) as error:
            visible_unix_review_model_from_payload(forged)
        self.assertEqual("REVIEW_MODEL_HASH_MISMATCH", error.exception.status)

    def test_payload_rejects_callable_module_and_unsupported_object(self) -> None:
        payload = visible_unix_review_model_payload(self.models["no_route"])
        for value in (lambda: None, types, object()):
            with self.subTest(value=repr(value)):
                malformed = dict(payload)
                malformed["warnings"] = [value]
                with self.assertRaises(VisibleUnixPrototypeError):
                    visible_unix_review_model_from_payload(malformed)

    def test_actual_demo_queries_have_required_route_statuses(self) -> None:
        expected = [status for _slug, _query, status in ACTUAL_DEMO_QUERIES]
        actual = [self.models[slug].route_status for slug, _query, _status in ACTUAL_DEMO_QUERIES]
        self.assertEqual(expected, actual)
        self.assertEqual(
            [
                ROUTE_TO_UNIX_KNOWLEDGE,
                ROUTE_TO_UNIX_KNOWLEDGE,
                ROUTE_TO_UNIX_KNOWLEDGE,
                EXECUTION_REQUEST_BLOCKED,
                NO_ROUTE,
                REVIEW_NEEDED,
            ],
            actual,
        )

    def test_route_is_created_before_explicit_retrieval(self) -> None:
        calls: list[str] = []
        real_route = prototype.propose_unix_route
        real_retrieve = prototype.retrieve_unix_knowledge

        def routed(*args, **kwargs):
            calls.append("route")
            return real_route(*args, **kwargs)

        def retrieved(*args, **kwargs):
            calls.append("retrieve")
            return real_retrieve(*args, **kwargs)

        with (
            patch.object(prototype, "propose_unix_route", side_effect=routed),
            patch.object(prototype, "retrieve_unix_knowledge", side_effect=retrieved),
        ):
            model = build_visible_unix_review_model(
                "How do UNIX file permissions work?", upstream=self.upstream
            )
        self.assertEqual(["route", "retrieve"], calls)
        self.assertEqual(ROUTE_TO_UNIX_KNOWLEDGE, model.route_status)

    def test_blocked_no_route_and_review_needed_never_retrieve(self) -> None:
        cases = (
            ("Run sudo apt install curl.", EXECUTION_REQUEST_BLOCKED),
            ("Explain stellar nucleosynthesis.", NO_ROUTE),
            ("Fix my system.", REVIEW_NEEDED),
        )
        with patch.object(
            prototype,
            "retrieve_unix_knowledge",
            side_effect=AssertionError("non-route must not retrieve"),
        ) as retrieve:
            for query, status in cases:
                with self.subTest(query=query):
                    model = build_visible_unix_review_model(query, upstream=self.upstream)
                    self.assertEqual(status, model.route_status)
                    self.assertEqual("NOT_PERFORMED", model.retrieval_status)
                    self.assertIsNone(model.retrieval_request_summary)
        retrieve.assert_not_called()

    def test_retrieval_request_is_inert_and_result_bindings_are_exact(self) -> None:
        model = self.models["path_traversal"]
        request = model.retrieval_request_summary
        self.assertIsNotNone(request)
        self.assertFalse(request.routing_invoked_retrieval)
        self.assertTrue(request.requires_explicit_caller)
        self.assertFalse(request.execution_allowed)
        self.assertEqual(model.index_manifest_hash, request.index_manifest_hash)
        self.assertTrue(model.retrieval_candidates)
        for candidate in model.retrieval_candidates:
            self.assertEqual(model.corpus_manifest_hash, candidate.provenance.corpus_manifest_hash)
            self.assertEqual(model.index_manifest_hash, candidate.provenance.index_manifest_hash)
            self.assertEqual(candidate.record_id, candidate.provenance.record_id)
            self.assertEqual(candidate.final_score, candidate.score_breakdown.final_score)

    def test_review_model_cannot_serve_as_human_gate_authority(self) -> None:
        reason = validate_canonical_human_gate_authority(
            self.models["unix_file_permissions"],
            expected_artifact_hash="0" * 64,
            expected_approval_decision_id="decision",
            expected_audit_event_id="audit",
            expected_contract_audit_event_id="contract",
        )
        self.assertEqual("artifact write requires exact canonical human gate evidence", reason)

    def test_text_renderer_is_deterministic_and_shows_all_stages(self) -> None:
        model = self.models["unix_file_permissions"]
        first = render_visible_unix_text(model)
        second = render_visible_unix_text(model)
        self.assertEqual(first.encode("utf-8"), second.encode("utf-8"))
        for stage in range(1, 7):
            self.assertIn(f"Stage {stage}", first)
        for required in (
            "Authority status: NON_AUTHORITATIVE",
            "Execution status: NO_COMMAND_OR_ACTION_EXECUTED",
            "UNIX Hat capabilities: none",
            "Route rationale:",
            "Confidence breakdown:",
            "Source hash:",
            "Score breakdown:",
            "Staleness:",
            "Limitations:",
            "NO COMMAND OR ACTION WAS EXECUTED",
        ):
            self.assertIn(required, first)

    def test_route_specific_text_is_visible(self) -> None:
        blocked = render_visible_unix_text(self.models["execution_blocked"])
        no_route = render_visible_unix_text(self.models["no_route"])
        review = render_visible_unix_text(self.models["review_needed"])
        self.assertIn("EXECUTION REQUEST BLOCKED", blocked)
        self.assertIn("Route status: NO_ROUTE", no_route)
        self.assertIn("Retrieval request: none", no_route)
        self.assertIn("Route status: REVIEW_NEEDED", review)

    def test_html_is_static_accessible_and_has_no_external_resources(self) -> None:
        html = render_visible_unix_html(self.models["unix_file_permissions"])
        lower = html.lower()
        self.assertTrue(lower.startswith("<!doctype html>"))
        self.assertIn('<html lang="en">', lower)
        self.assertIn('<meta name="viewport"', lower)
        self.assertIn("<h1", lower)
        self.assertIn("<h2", lower)
        self.assertIn('scope="col"', lower)
        self.assertIn("prefers-reduced-motion", lower)
        self.assertNotIn("<script", lower)
        self.assertNotIn("<iframe", lower)
        self.assertNotIn(" src=", lower)
        self.assertNotIn(" href=", lower)
        self.assertNotIn("@import", lower)
        self.assertNotIn("url(", lower)

    def test_html_escapes_query_and_template_payloads_as_inert_text(self) -> None:
        malicious = (
            '<script>alert(1)</script> <img src=x onerror=alert(1)> '
            '<a href="javascript:alert(1)">test</a> {{ template_expression }}'
        )
        model = build_visible_unix_review_model(malicious, upstream=self.upstream)
        html = render_visible_unix_html(model)
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("<img src", html)
        self.assertNotIn('<a href="javascript:', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;img", html)
        self.assertIn("&lt;a href=&quot;javascript:", html)
        self.assertIn("{{ template_expression }}", html)

    def test_command_content_is_rendered_as_text_and_never_as_control(self) -> None:
        html = render_visible_unix_html(self.models["execution_blocked"])
        lower = html.lower()
        self.assertIn("run sudo apt install curl.", lower)
        self.assertIn("execution request blocked", lower)
        self.assertNotIn("<button", lower)
        self.assertNotIn("<form", lower)
        self.assertNotIn("<input", lower)

    def test_sponsor_explanation_is_evidence_bounded_and_limitations_visible(self) -> None:
        text = render_visible_unix_text(self.models["unix_file_permissions"])
        lower = text.lower()
        for forbidden_claim in (
            "perfect safety",
            "complete unix knowledge",
            "autonomous system administration",
            "guaranteed correctness",
            "result is approval",
        ):
            self.assertNotIn(forbidden_claim, lower)
        self.assertIn("local-first", lower)
        self.assertIn("limitations:", lower)
        self.assertIn("does not execute commands", lower)
        self.assertIn("does not grant authority", lower)

    def test_runtime_query_performs_no_mutating_io_or_external_action(self) -> None:
        original_path_open = Path.open
        original_builtin_open = builtins.open

        def guarded_path_open(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                raise AssertionError("runtime query attempted a write-mode Path.open")
            return original_path_open(path, mode, *args, **kwargs)

        def guarded_builtin_open(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                raise AssertionError("runtime query attempted a write-mode open")
            return original_builtin_open(file, mode, *args, **kwargs)

        with (
            patch.object(Path, "open", new=guarded_path_open),
            patch("builtins.open", new=guarded_builtin_open),
            patch.object(Path, "mkdir", side_effect=AssertionError("mkdir reached")),
            patch.object(Path, "write_text", side_effect=AssertionError("write_text reached")),
            patch.object(Path, "write_bytes", side_effect=AssertionError("write_bytes reached")),
            patch.object(os, "system", side_effect=AssertionError("shell reached")),
            patch.object(subprocess, "run", side_effect=AssertionError("process reached")),
            patch.object(socket, "socket", side_effect=AssertionError("network reached")),
            patch.object(webbrowser, "open", side_effect=AssertionError("browser reached")),
            patch.object(
                prototype,
                "materialize_visible_unix_demo",
                side_effect=AssertionError("materializer reached"),
            ),
        ):
            model = build_visible_unix_review_model(
                "How do process signals work?", upstream=self.upstream
            )
        self.assertEqual(ROUTE_TO_UNIX_KNOWLEDGE, model.route_status)
        self.assertEqual(EXECUTION_STATUS, model.execution_status)

    def test_cli_query_is_read_only_and_outputs_safety_boundary(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = prototype.main(
                [
                    "query",
                    "--query",
                    "Explain stellar nucleosynthesis.",
                    "--format",
                    "text",
                ]
            )
        self.assertEqual(0, code)
        self.assertIn("Route status: NO_ROUTE", output.getvalue())
        self.assertIn("NO COMMAND OR ACTION WAS EXECUTED", output.getvalue())

    def test_demo_payloads_are_canonical_complete_and_deterministic(self) -> None:
        first = build_visible_unix_demo_payloads()
        second = build_visible_unix_demo_payloads()
        self.assertEqual(first, second)
        self.assertEqual(16, len(first))
        self.assertIn("demo_manifest.json", first)
        self.assertIn("verification.json", first)
        self.assertIn("index.html", first)
        self.assertIn("demo.txt", first)
        self.assertEqual(first["demo_manifest.json"], json.dumps(
            json.loads(first["demo_manifest.json"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n")

    def test_demo_materialization_is_bounded_verifiable_and_tamper_evident(self) -> None:
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            destination = parent / "demo-a"
            result = materialize_visible_unix_demo(
                destination,
                allowed_parent=parent,
            )
            self.assertTrue(result.valid)
            self.assertEqual(16, result.file_count)
            self.assertEqual(16, len(tuple(path for path in destination.rglob("*") if path.is_file())))
            self.assertTrue(verify_visible_unix_demo(destination).valid)
            demo_text = destination / "demo.txt"
            demo_text.write_bytes(demo_text.read_bytes() + b"tamper\n")
            self.assertFalse(verify_visible_unix_demo(destination).valid)

    def test_demo_verifier_rejects_any_symbolic_link_entry(self) -> None:
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            destination = parent / "demo-links"
            materialize_visible_unix_demo(destination, allowed_parent=parent)
            (destination / "unexpected-link").symlink_to(destination / "demo.txt")
            result = verify_visible_unix_demo(destination)
            self.assertFalse(result.valid)
            self.assertEqual("DEMO_FILE_SET_MISMATCH", result.status)

    def test_materializer_rejects_existing_traversal_and_symlink_roots(self) -> None:
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            existing = parent / "existing"
            existing.mkdir()
            marker = existing / "marker"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaises(VisibleUnixPrototypeError):
                materialize_visible_unix_demo(existing, allowed_parent=parent)
            self.assertEqual("preserve", marker.read_text(encoding="utf-8"))

            with self.assertRaises(VisibleUnixPrototypeError):
                materialize_visible_unix_demo(
                    parent / "nested" / "escape",
                    allowed_parent=parent,
                )

            target = parent / "target"
            target.mkdir()
            link = parent / "linked-demo"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(VisibleUnixPrototypeError):
                materialize_visible_unix_demo(link, allowed_parent=parent)

    def test_materialized_demo_replay_is_byte_identical(self) -> None:
        with TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            first_root = parent / "demo-one"
            second_root = parent / "demo-two"
            materialize_visible_unix_demo(first_root, allowed_parent=parent)
            materialize_visible_unix_demo(second_root, allowed_parent=parent)
            first = {
                path.relative_to(first_root).as_posix(): path.read_bytes()
                for path in first_root.rglob("*")
                if path.is_file()
            }
            second = {
                path.relative_to(second_root).as_posix(): path.read_bytes()
                for path in second_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first, second)

    def test_static_protected_zone_contains_prototype_and_is_clean(self) -> None:
        records = resolve_protected_runtime_files(PROJECT_ROOT, ("visible_review",))
        self.assertEqual(
            ("runtime/visible_unix_prototype.py",),
            tuple(record.path for record in records),
        )
        findings = tuple(
            finding
            for record in records
            for finding in scan_file_for_capabilities(PROJECT_ROOT, record)
        )
        self.assertEqual((), findings)

    def test_source_has_no_forbidden_capability_or_server_imports(self) -> None:
        tree = ast.parse(PROTOTYPE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        forbidden = {
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
            "http.server",
            "runtime.control_write",
            "runtime.human_decision_gate_integration",
            "runtime.human_decision_gated_artifact_write",
            "runtime.patches.controlled_patch_apply",
        }
        self.assertFalse(imported.intersection(forbidden))

    def test_filesystem_writes_exist_only_in_explicit_demo_materializer(self) -> None:
        tree = ast.parse(PROTOTYPE_PATH.read_text(encoding="utf-8"))
        parent: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parent[child] = node

        allowed = {"materialize_visible_unix_demo", "_write_new_demo_file"}
        mutating_calls: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            terminal = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if terminal not in {"mkdir", "open", "write", "write_bytes", "write_text"}:
                continue
            owner = node
            while owner in parent and not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = parent[owner]
            owner_name = owner.name if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<module>"
            mutating_calls.append((terminal, owner_name))
        self.assertTrue(mutating_calls)
        self.assertTrue(all(owner in allowed for _call, owner in mutating_calls), mutating_calls)

    def test_module_has_no_import_time_writes_or_hidden_server(self) -> None:
        source = PROTOTYPE_PATH.read_text(encoding="utf-8").lower()
        for forbidden in (
            "http.server",
            "serve_forever",
            "flask",
            "fastapi",
            "django",
            "xdg-open",
            "start_server",
            "execute=true",
            "auto_retrieve=true",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
