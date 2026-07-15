from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator.knowledge_router import KnowledgeRouter
from retrieval.facade import retrieve_linux_knowledge
from retrieval.feature_flags import (
    LINUX_RETRIEVAL_V1_FLAG,
    linux_retrieval_boundary,
    linux_retrieval_v1_enabled,
    linux_retrieval_v1_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COORDINATOR_MODULES = (
    "runtime/main.py",
    "runtime/commands/local_commands.py",
    "runtime/adaptive_routing/epistemic_kernel.py",
    "runtime/orchestrator/knowledge_router.py",
    "runtime/memory/rhcsa_context.py",
)
BANNED_IMPORTS = (
    "from tools.rhcsa_search",
    "import tools.rhcsa_search",
    "from knowledge.rhcsa_engine",
    "import knowledge.rhcsa_engine",
)


class RuntimeRouterContractGuardTests(unittest.TestCase):
    def test_feature_flag_defaults_off(self) -> None:
        self.assertFalse(linux_retrieval_v1_enabled({}))
        self.assertIsNone(linux_retrieval_boundary({}))
        self.assertEqual(linux_retrieval_v1_status({})["default"], "off")

    def test_feature_flag_on_returns_facade_boundary_only(self) -> None:
        env = {LINUX_RETRIEVAL_V1_FLAG: "1"}

        self.assertTrue(linux_retrieval_v1_enabled(env))
        self.assertIs(linux_retrieval_boundary(env), retrieve_linux_knowledge)

    def test_feature_flag_invalid_value_does_not_activate(self) -> None:
        env = {LINUX_RETRIEVAL_V1_FLAG: "maybe"}

        self.assertFalse(linux_retrieval_v1_enabled(env))
        self.assertIsNone(linux_retrieval_boundary(env))

    def test_runtime_router_does_not_import_flag_or_facade_directly(self) -> None:
        source = (PROJECT_ROOT / "runtime" / "main.py").read_text(encoding="utf-8")

        self.assertNotIn(LINUX_RETRIEVAL_V1_FLAG, source)
        self.assertNotIn("retrieve_linux_knowledge", source)

    def test_knowledge_router_returns_request_metadata_without_using_facade(self) -> None:
        with patch("retrieval.facade.retrieve_linux_knowledge") as facade:
            with tempfile.TemporaryDirectory() as tmpdir:
                router = KnowledgeRouter(Path(tmpdir))
                decision = router.route("systemctl status")

        facade.assert_not_called()
        self.assertFalse(decision.should_handle_locally)
        self.assertEqual(decision.route_status, "ROUTE_PROPOSED")
        self.assertIsNotNone(decision.retrieval_request)
        self.assertFalse(decision.retrieval_request.execution_allowed)

    def test_legacy_engine_injection_is_inert(self) -> None:
        def forbidden_retrieval(_query):
            raise AssertionError("routing must not invoke legacy engine retrieval")

        class FakeEngine:
            retrieve_operational_memory = staticmethod(forbidden_retrieval)

        with tempfile.TemporaryDirectory() as tmpdir:
            router = KnowledgeRouter(Path(tmpdir), engine=FakeEngine())
            decision = router.route("systemctl status")

        self.assertEqual(decision.route_status, "ROUTE_PROPOSED")

    def test_refusal_behavior_preserved(self) -> None:
        response = retrieve_linux_knowledge("zzzz-not-a-linux-command-xyz", max_results=3)

        self.assertEqual(response.status, "refused")
        self.assertEqual(response.confidence, "none")
        self.assertFalse(response.answered)

    def test_provenance_preserved(self) -> None:
        response = retrieve_linux_knowledge("systemctl status", max_results=3)

        self.assertTrue(response.results)
        provenance = response.results[0].get("provenance", {})
        self.assertIn("source_file", provenance)
        self.assertIn("canonical_source", provenance)
        self.assertIn("confidence_score", provenance)

    def test_no_memory_or_evidence_writes_during_facade_retrieval(self) -> None:
        evidence_path = PROJECT_ROOT / "runtime" / "memory" / "evidence_memory.jsonl"
        before_exists = evidence_path.exists()
        before_size = evidence_path.stat().st_size if before_exists else None
        before_mtime = evidence_path.stat().st_mtime_ns if before_exists else None

        response = retrieve_linux_knowledge("ls", max_results=2)

        self.assertTrue(response.answered)
        self.assertEqual(evidence_path.exists(), before_exists)
        if before_exists:
            self.assertEqual(evidence_path.stat().st_size, before_size)
            self.assertEqual(evidence_path.stat().st_mtime_ns, before_mtime)

    def test_no_coordinator_imports_low_level_retrieval_modules(self) -> None:
        offenders: list[tuple[str, str]] = []
        for relative_path in COORDINATOR_MODULES:
            source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
            for pattern in BANNED_IMPORTS:
                if pattern in source:
                    offenders.append((relative_path, pattern))

        self.assertEqual(offenders, [])

    def test_import_scanner_passes_for_coordinators(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "runtime" / "tools" / "check_no_direct_retrieval_imports.py"),
            ],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
