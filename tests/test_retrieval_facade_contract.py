from __future__ import annotations

import os
import unittest
from pathlib import Path

from retrieval.facade import retrieve_linux_knowledge


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RetrievalFacadeContractTests(unittest.TestCase):
    def test_facade_exact_command_query_returns_structured_result(self) -> None:
        response = retrieve_linux_knowledge("ls", max_results=3)

        payload = response.to_dict()
        self.assertEqual(payload["status"], "answered")
        self.assertEqual(payload["match_type"], "exact")
        self.assertGreaterEqual(payload["confidence_score"], 30)
        self.assertIsInstance(payload["results"], list)
        self.assertLessEqual(len(payload["results"]), 3)
        self.assertIn("message", payload)

    def test_facade_invalid_query_refuses(self) -> None:
        response = retrieve_linux_knowledge("zzzz-not-a-linux-command-xyz", max_results=3)

        self.assertEqual(response.status, "refused")
        self.assertFalse(response.answered)
        self.assertEqual(response.confidence, "none")
        self.assertEqual(response.results, ())
        self.assertIn("clarify", response.message.lower())

    def test_facade_result_includes_provenance(self) -> None:
        response = retrieve_linux_knowledge("systemctl status", max_results=3)

        self.assertTrue(response.results)
        provenance = response.results[0].get("provenance", {})
        self.assertIn("source_file", provenance)
        self.assertIn("source_page", provenance)
        self.assertIn("canonical_source", provenance)
        self.assertIn("confidence_score", provenance)

    def test_facade_has_no_memory_or_evidence_write_side_effects(self) -> None:
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

    def test_local_commands_no_longer_imports_rhcsa_search_directly(self) -> None:
        source = (PROJECT_ROOT / "runtime" / "commands" / "local_commands.py").read_text(encoding="utf-8")

        self.assertNotIn("from tools.rhcsa_search", source)
        self.assertNotIn("import tools.rhcsa_search", source)
        self.assertIn("from retrieval.facade import", source)

    def test_epistemic_kernel_delegates_through_facade(self) -> None:
        source = (PROJECT_ROOT / "runtime" / "adaptive_routing" / "epistemic_kernel.py").read_text(encoding="utf-8")

        self.assertIn("retrieve_linux_knowledge", source)
        self.assertNotIn("from tools.rhcsa_search", source)
        self.assertNotIn("LinuxRetrievalEngine", source)

    def test_feature_flag_not_required_for_direct_facade_tests(self) -> None:
        previous = os.environ.pop("AIOA_ENABLE_LINUX_RETRIEVAL_V1", None)
        try:
            response = retrieve_linux_knowledge("pwd", max_results=2)
        finally:
            if previous is not None:
                os.environ["AIOA_ENABLE_LINUX_RETRIEVAL_V1"] = previous

        self.assertTrue(response.answered)

    def test_runtime_router_hook_not_activated(self) -> None:
        source = (PROJECT_ROOT / "runtime" / "main.py").read_text(encoding="utf-8")

        self.assertNotIn("AIOA_ENABLE_LINUX_RETRIEVAL_V1", source)
        self.assertNotIn("retrieve_linux_knowledge", source)


if __name__ == "__main__":
    unittest.main()
