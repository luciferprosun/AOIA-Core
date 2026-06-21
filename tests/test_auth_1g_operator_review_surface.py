from __future__ import annotations

import ast
import io
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from runtime.execution_readiness_gate import (
    ExecutionReadinessRecord,
    ExecutionReadinessRejection,
    evaluate_execution_readiness,
)
from runtime.operator_review_surface import OperatorReviewSurface
from runtime.policy_profiles import PolicyProfileName
from tests.test_auth_1f_execution_readiness_gate import (
    Auth1FExecutionReadinessGateTests,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = REPO_ROOT / "runtime" / "operator_review_surface.py"


class Auth1GOperatorReviewSurfaceTests(unittest.TestCase):
    def test_render_readiness_record_returns_human_readable_string(self):
        rendered = OperatorReviewSurface.render(self._record())

        self.assertIsInstance(rendered, str)
        self.assertIn("operator_review_surface: REVIEWABLE", rendered)
        self.assertIn("object_type: EXECUTION_READINESS_RECORD", rendered)
        self.assertIn("execution_allowed: False", rendered)
        self.assertIn("dispatch_allowed: False", rendered)
        self.assertIn("artifact_write_allowed: False", rendered)
        self.assertIn("provider_call_allowed: False", rendered)
        self.assertIn("github_action_allowed: False", rendered)
        self.assertIn("not an execution instruction", rendered)
        self.assertIn("no authority granted", rendered)

    def test_render_rejection_returns_human_readable_string(self):
        rendered = OperatorReviewSurface.render(self._rejection())

        self.assertIsInstance(rendered, str)
        self.assertIn("object_type: EXECUTION_READINESS_REJECTION", rendered)
        self.assertIn("status: READINESS_REJECTED", rendered)
        self.assertIn("rejection_reason:", rendered)
        self.assertIn("not an execution instruction", rendered)
        self.assertIn("no authority granted", rendered)

    def test_summary_fields_for_record_is_flat_and_deterministic(self):
        record = self._record()

        first = OperatorReviewSurface.summary_fields(record)
        second = OperatorReviewSurface.summary_fields(record)

        self.assertEqual(first, second)
        self.assertTrue(first["reviewable"])
        self.assertEqual("EXECUTION_READINESS_RECORD", first["object_type"])
        self.assertTrue(all(isinstance(v, (bool, str)) for v in first.values()))

    def test_summary_fields_for_rejection_is_flat_and_deterministic(self):
        rejection = self._rejection()

        first = OperatorReviewSurface.summary_fields(rejection)
        second = OperatorReviewSurface.summary_fields(rejection)

        self.assertEqual(first, second)
        self.assertTrue(first["reviewable"])
        self.assertEqual("EXECUTION_READINESS_REJECTION", first["object_type"])
        self.assertTrue(all(isinstance(v, (bool, str)) for v in first.values()))

    def test_unknown_input_fails_closed(self):
        for value in (None, {}, "bad", object()):
            with self.subTest(value=type(value).__name__):
                summary = OperatorReviewSurface.summary_fields(value)
                rendered = OperatorReviewSurface.render(value)
                self.assertEqual(False, summary["reviewable"])
                self.assertEqual("NOT_REVIEWABLE", summary["status"])
                self.assertIn("NOT_REVIEWABLE", rendered)

        malformed = replace(self._record(), readiness_hash="")
        malformed_summary = OperatorReviewSurface.summary_fields(malformed)
        self.assertEqual(False, malformed_summary["reviewable"])

    def test_surface_does_not_mutate_inputs(self):
        record = self._record()
        rejection = self._rejection()
        record_before = deepcopy(record.to_dict())
        rejection_before = deepcopy(rejection.to_dict())

        OperatorReviewSurface.summary_fields(record)
        OperatorReviewSurface.render(record)
        OperatorReviewSurface.summary_fields(rejection)
        OperatorReviewSurface.render(rejection)

        self.assertEqual(record_before, record.to_dict())
        self.assertEqual(rejection_before, rejection.to_dict())

    def test_surface_is_deterministic(self):
        record = self._record()
        rejection = self._rejection()
        self.assertEqual(
            OperatorReviewSurface.render(record),
            OperatorReviewSurface.render(record),
        )
        self.assertEqual(
            OperatorReviewSurface.render(rejection),
            OperatorReviewSurface.render(rejection),
        )

    def test_surface_has_no_stdout_or_side_effects(self):
        record = self._record()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            OperatorReviewSurface.render(record)
            OperatorReviewSurface.summary_fields(record)
        self.assertEqual("", buffer.getvalue())

    def test_static_boundary_no_forbidden_runtime_calls(self):
        source = RUNTIME_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_modules = {
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "sqlite3",
            "webbrowser",
        }
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        for module_name in imports:
            self.assertFalse(
                any(
                    module_name == item or module_name.startswith(item + ".")
                    for item in forbidden_modules
                )
            )

        for value in (
            "print(",
            "open(",
            "write_text(",
            "write_bytes(",
            "subprocess",
            "os.system(",
            "Popen(",
            "eval(",
            "exec(",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "sqlite",
            "openrouter",
            "argparse",
            "__main__",
            "provider_live_adapter",
        ):
            self.assertNotIn(value.lower(), source.lower())

    def test_no_authority_or_dispatcher_language_in_new_runtime_names(self):
        tree = ast.parse(RUNTIME_FILE.read_text(encoding="utf-8"))
        banned = {
            "dispatcher",
            "instruction",
            "pending",
            "executor",
            "execute",
            "dispatch",
            "authorize",
            "permit",
            "grant",
            "gatekeeper",
            "actionable",
            "trigger",
            "payload",
            "display",
            "log",
            "write",
        }
        allowed = {"ExecutionReadinessRecord", "ExecutionReadinessRejection"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name not in allowed:
                    lowered = node.name.lower()
                    self.assertTrue(all(word not in lowered for word in banned))
            elif isinstance(node, ast.Name):
                if node.id not in allowed:
                    lowered = node.id.lower()
                    self.assertTrue(all(word not in lowered for word in banned))

    def _record(self) -> ExecutionReadinessRecord:
        source = Auth1FExecutionReadinessGateTests()
        return evaluate_execution_readiness(source.assemble())

    def _rejection(self) -> ExecutionReadinessRejection:
        source = Auth1FExecutionReadinessGateTests()
        return evaluate_execution_readiness(
            source.assemble(profile_name=PolicyProfileName.DENY_ALL)
        )
